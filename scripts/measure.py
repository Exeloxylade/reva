#!/usr/bin/env python3
"""measure.py - measure cut cadence, still-vs-moving shots, WPM, and color palette for a style file.

Usage:
  python measure.py <video> [--subs ref.id.vtt] [--out measure.json] [--scene 0.15] [--max-samples 80] [--frames-dir ref/frames]
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile

try:
    import numpy as np
except ImportError:
    np = None

try:
    from . import _common as C
except ImportError:
    import _common as C


def gray_frame(video, t, w=480):
    proc = subprocess.run(
        [
            C.find_ffmpeg(), "-v", "error",
            "-ss", f"{max(0.0, t):.3f}", "-i", video,
            "-frames:v", "1", "-vf", f"scale={w}:-2,format=gray",
            "-f", "rawvideo", "-",
        ],
        capture_output=True,
    )
    return proc.stdout


def frame_diff(a, b):
    n = min(len(a), len(b))
    if not n:
        return 0.0
    if np is not None:
        va = np.frombuffer(a[:n], dtype=np.uint8).astype(np.int16)
        vb = np.frombuffer(b[:n], dtype=np.uint8).astype(np.int16)
        return float(np.mean(np.abs(va - vb)))
    return sum(abs(a[i] - b[i]) for i in range(n)) / n


def pct(sorted_vals, p):
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * p))]


def pick_sample_frames(video, frames_dir, max_frames=12):
    """Gather up to max_frames evenly spaced frame paths (or extract into a temp dir)."""
    if frames_dir and os.path.isdir(frames_dir):
        all_frames = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))
        if all_frames:
            step = max(1, len(all_frames) // max_frames)
            return all_frames[::step][:max_frames], None

    tmp = tempfile.TemporaryDirectory(prefix="reva_pal_")
    meta = C.probe_media(video)
    dur = max(0.2, meta["duration"])
    count = min(6, max(1, int(dur)))
    paths = []
    ff = C.find_ffmpeg()
    for i in range(count):
        t = (i + 0.5) * dur / count
        out = os.path.join(tmp.name, f"p{i:02d}.jpg")
        r = C.run_cmd([ff, "-hide_banner", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-q:v", "3", out])
        if r.returncode == 0 and os.path.exists(out):
            paths.append(out)
    return paths, tmp


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--subs")
    ap.add_argument("--out")
    ap.add_argument("--frames-dir")
    ap.add_argument("--scene", type=float, default=0.15)
    ap.add_argument("--max-samples", type=int, default=80)
    a = ap.parse_args()

    meta = C.probe_media(a.video)
    dur = max(0.01, meta["duration"])
    print(f"  finding cuts (scene > {a.scene}) ...")
    c = C.detect_cuts(a.video, threshold=a.scene)
    bounds = [0.0] + c + [dur]
    shots = [(bounds[i - 1], bounds[i]) for i in range(1, len(bounds)) if bounds[i] - bounds[i - 1] > 0.05]
    if not shots:
        shots = [(0.0, dur)]
    lens = sorted(e - s for s, e in shots)
    third = dur / 3.0
    thirds = [sum(1 for t in c if k * third <= t < (k + 1) * third) for k in range(3)]

    # Sample shots for motion: prefer >= 2.2s shots, fall back to >= 0.5s shots for fast-cut edits.
    long_shots = [(s, e, 0.6) for s, e in shots if (e - s) >= 2.2]
    pool = long_shots if len(long_shots) >= 5 else [(s, e, min(0.6, (e - s) * 0.3)) for s, e in shots if (e - s) >= 0.5]
    step = max(1, len(pool) // max(1, a.max_samples)) if pool else 1
    sample = pool[::step][:a.max_samples]

    print(f"  still vs moving on {len(sample)} shots ...")
    kinds = {"still": 0, "subtle": 0, "moving": 0}
    still_lens = []
    for s, e, delta in sample:
        m = (s + e) / 2.0
        d = frame_diff(gray_frame(a.video, m - delta), gray_frame(a.video, m + delta))
        label = "still" if d < 0.3 else ("subtle" if d < 3.0 else "moving")
        kinds[label] += 1
        if label == "still":
            still_lens.append(e - s)

    n = len(sample)
    still_share = (kinds["still"] / n) if n else 0.0
    move_share = ((kinds["subtle"] + kinds["moving"]) / n) if n else 0.0
    max_static_sec = round(max(still_lens), 1) if still_lens else None

    sibling_frames = os.path.join(os.path.dirname(os.path.abspath(a.video)), "frames")
    fdir = a.frames_dir or (sibling_frames if os.path.isdir(sibling_frames) else None)
    pal_frames, pal_tmp = pick_sample_frames(a.video, fdir)
    try:
        palette = C.extract_palette(pal_frames, n=6) if pal_frames else {"main": [], "accents": []}
    finally:
        if pal_tmp is not None:
            pal_tmp.cleanup()

    med_len = round(pct(lens, 0.5), 2)
    p10_len = round(pct(lens, 0.1), 2)
    p90_len = round(pct(lens, 0.9), 2)
    max_len = round(lens[-1], 2)
    per_min = round(len(c) / dur * 60.0, 1)

    out = {
        "video": os.path.abspath(a.video),
        "duration_sec": round(dur, 2),
        "aspect_ratio": meta["aspect_ratio"],
        "cuts": {
            "count": len(c),
            "median_sec": med_len,
            "p10_sec": p10_len,
            "p90_sec": p90_len,
            "max_sec": max_len,
            "mean_sec": round(sum(lens) / len(lens), 2),
            "per_min": per_min,
            "thirds": thirds,
            "first": [round(t, 1) for t in c[:8]],
        },
        "motion": {
            "samples": n,
            **kinds,
            "still_share": round(still_share, 2),
            "moving_share": round(move_share, 2),
            "max_static_sec": max_static_sec,
        },
        "palette": palette,
    }

    if a.subs and os.path.exists(a.subs):
        parsed = C.parse_subtitles(a.subs)
        w = parsed["words"]
        span = parsed["talk_span_sec"]
        wpm = round(w / dur * 60.0) if dur > 0 and w else 0
        wpm_span = round(w / span * 60.0) if span > 1.0 and w else wpm
        first_line = parsed["cues"][0]["text"] if parsed["cues"] else ""
        out["words"] = {
            "subs": os.path.abspath(a.subs),
            "count": w,
            "wpm": wpm,
            "wpm_talk_span": wpm_span,
            "first_line": first_line,
        }

    smin = max(1.0, round(p10_len, 1))
    smax = max(smin, round(p90_len, 1))
    style = {
        "direction.scene_maker.avg_shot_sec": {
            "rule": "Average picture length",
            "value": med_len,
            "basis": "measured",
            "proof": [f"measure.py: {len(c)} changes, median {med_len} s, p10 {p10_len}, p90 {p90_len}, max {max_len}"],
        },
        "direction.scene_maker.shot_length_sec": {
            "min": smin,
            "max": smax,
            "mode": "flexible",
        },
        "direction.scene_maker.cuts_per_min": {
            "rule": "Picture changes per minute",
            "value": per_min,
            "basis": "measured",
            "proof": [f"thirds {'/'.join(map(str, thirds))}"],
        },
        "direction.resource_mix.types (shares)": {
            "generated-image": f"{round(still_share * 100)}%",
            "generated-video": f"{round(move_share * 100)}%",
            "proof": f"{kinds['still']} still, {kinds['subtle']} subtle, {kinds['moving']} moving of {n} sampled shots",
        },
        "look.can_do.camera_moves": (still_share < 0.8) if n else True,
    }
    if meta["aspect_ratio"] in ("9:16", "16:9"):
        style["direction.default_aspect"] = meta["aspect_ratio"]
    if max_static_sec is not None:
        style["direction.scene_maker.max_static_sec"] = {
            "value": max_static_sec,
            "basis": "measured",
            "proof": [f"longest still shot {max_static_sec} s"],
        }
    if palette["main"]:
        col = {"palette": [x["hex"] for x in palette["main"]]}
        if palette["accents"]:
            col["accent"] = palette["accents"][0]["hex"]
        style["look.colors"] = col
    if "words" in out:
        style["direction.narration.wpm"] = {
            "rule": "Speaking speed",
            "value": out["words"]["wpm"],
            "basis": "measured",
            "proof": [f"{out['words']['count']} words / {round(dur, 1)} s"],
        }
    out["style"] = style

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fp:
            json.dump(out, fp, indent=2, ensure_ascii=False)

    print("\n=== MEASURE ===")
    k = out["cuts"]
    print(f"  cuts     {k['count']}  median {k['median_sec']} s  p10 {k['p10_sec']}  p90 {k['p90_sec']}  max {k['max_sec']}  ({k['per_min']}/min, thirds {'/'.join(map(str, thirds))})")
    mo = out["motion"]
    print(f"  motion   {mo['still']} still, {mo['subtle']} subtle, {mo['moving']} moving of {mo['samples']} shots ({round(still_share * 100)}% still, max static {max_static_sec} s)")
    if palette["main"]:
        print("  colors   " + " ".join(x["hex"] for x in palette["main"][:5]) + ("  accent " + palette["accents"][0]["hex"] if palette["accents"] else ""))
    if "words" in out:
        print(f"  words    {out['words']['count']} words, {out['words']['wpm']} wpm ({out['words']['wpm_talk_span']} over the talk span)")
    else:
        print("  words    no subtitles given (--subs): words per minute not measured")
    if a.out:
        print(f"  wrote    {a.out}")


if __name__ == "__main__":
    sys.exit(main())
