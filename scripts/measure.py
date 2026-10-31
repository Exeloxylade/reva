#!/usr/bin/env python3
"""measure.py - the numbers a style file needs, measured on the reference (no guessing).

    python measure.py <video> [--subs ref.id.vtt] [--out measure.json] [--scene 0.15] [--max-samples 80]

Reports:
  cuts       picture changes (ffmpeg scene > 0.15), shot length median / p10 / p90 / max, cuts per minute,
             and how the cuts spread over the three thirds of the video (same pace = steady)
  motion     still / subtle / moving shots: mean frame difference 0.6 s either side of each shot's middle
             (< 0.3 still, < 3 subtle, >= 3 moving). Fast cuts look like motion; this tells them apart.
  words      words per minute from the subtitles (rolling auto-captions deduped: last line of each cue)
  style      the matching style-file values (direction.scene_maker, narration.wpm, look.can_do,
             resource_mix shares) to paste into <id>.style.json

Needs ffmpeg (C:\\ffmpeg\\bin or PATH). No Pillow, no numpy.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

FF = r"C:\ffmpeg\bin\ffmpeg.exe" if os.path.exists(r"C:\ffmpeg\bin\ffmpeg.exe") else (shutil.which("ffmpeg") or "ffmpeg")
FP = r"C:\ffmpeg\bin\ffprobe.exe" if os.path.exists(r"C:\ffmpeg\bin\ffprobe.exe") else (shutil.which("ffprobe") or "ffprobe")


def duration(video):
    r = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video], capture_output=True, text=True)
    return float(r.stdout.strip())


def cuts(video, scene):
    r = subprocess.run([FF, "-hide_banner", "-i", video, "-vf", f"select='gt(scene,{scene})',showinfo", "-an", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [float(m) for m in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def gray(video, t, w=480):
    r = subprocess.run([FF, "-v", "error", "-ss", f"{max(0, t):.3f}", "-i", video, "-frames:v", "1",
                        "-vf", f"scale={w}:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True)
    return r.stdout


def diff(a, b):
    n = min(len(a), len(b))
    return sum(abs(a[i] - b[i]) for i in range(n)) / n if n else 0.0


def pct(sorted_vals, p):
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * p))]


def words_from_subs(path):
    """Rolling auto-captions repeat lines: keep the last line of each cue, drop repeats in a row."""
    text = open(path, encoding="utf-8", errors="replace").read().replace("\r", "")
    stamp = re.compile(r"(\d+):(\d\d):(\d\d)[.,](\d+)\s*-->\s*(\d+):(\d\d):(\d\d)[.,](\d+)")
    lines, last, first_t, last_t = [], None, None, None
    for block in re.split(r"\n\s*\n", text):
        rows = [r for r in block.split("\n") if r.strip()]
        m = next((stamp.search(r) for r in rows if stamp.search(r)), None)
        if not m:
            continue
        g = list(map(int, m.groups()))
        t0, t1 = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
        body = [re.sub(r"<[^>]+>", "", r).strip() for r in rows if not stamp.search(r) and not r.strip().isdigit()]
        body = [b for b in body if b]
        if not body:
            continue
        line = body[-1]
        if line != last:
            lines.append(line)
            last = line
            first_t = t0 if first_t is None else first_t
            last_t = t1
    words = sum(len(l.split()) for l in lines)
    return words, (first_t or 0.0), (last_t or 0.0), lines


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--subs")
    ap.add_argument("--out")
    ap.add_argument("--scene", type=float, default=0.15)
    ap.add_argument("--max-samples", type=int, default=80)
    a = ap.parse_args()

    dur = duration(a.video)
    print(f"  finding cuts (scene > {a.scene}) ...")
    c = cuts(a.video, a.scene)
    bounds = [0.0] + c + [dur]
    shots = [(bounds[i - 1], bounds[i]) for i in range(1, len(bounds))]
    lens = sorted(e - s for s, e in shots)
    third = dur / 3
    thirds = [sum(1 for t in c if k * third <= t < (k + 1) * third) for k in range(3)]

    # Still vs moving: shots long enough to sample, spread evenly over the video.
    long = [(s, e) for s, e in shots if e - s >= 2.2]
    step = max(1, len(long) // max(1, a.max_samples))
    sample = long[::step][: a.max_samples]
    print(f"  still vs moving on {len(sample)} shots ...")
    kinds = {"still": 0, "subtle": 0, "moving": 0}
    for s, e in sample:
        m = (s + e) / 2
        d = diff(gray(a.video, m - 0.6), gray(a.video, m + 0.6))
        kinds["still" if d < 0.3 else "subtle" if d < 3 else "moving"] += 1
    n = max(1, len(sample))
    still_share = kinds["still"] / n
    move_share = (kinds["subtle"] + kinds["moving"]) / n

    out = {
        "video": os.path.abspath(a.video), "duration_sec": round(dur, 2),
        "cuts": {"count": len(c), "median_sec": round(pct(lens, 0.5), 2), "p10_sec": round(pct(lens, 0.1), 2),
                 "p90_sec": round(pct(lens, 0.9), 2), "max_sec": round(lens[-1], 2), "mean_sec": round(sum(lens) / len(lens), 2),
                 "per_min": round(len(c) / dur * 60, 1), "thirds": thirds, "first": [round(t, 1) for t in c[:8]]},
        "motion": {"samples": len(sample), **kinds, "still_share": round(still_share, 2), "moving_share": round(move_share, 2)},
    }
    if a.subs and os.path.exists(a.subs):
        w, t0, t1, lines = words_from_subs(a.subs)
        out["words"] = {"subs": os.path.abspath(a.subs), "count": w, "wpm": round(w / dur * 60) if dur else 0,
                        "wpm_talk_span": round(w / max(1, t1 - t0) * 60), "first_line": lines[0] if lines else ""}
    # The style-file values, ready to paste.
    style = {
        "direction.scene_maker.avg_shot_sec": {"rule": "Average picture length", "value": out["cuts"]["median_sec"], "basis": "measured",
                                               "proof": [f"measure.py: {len(c)} changes, median {out['cuts']['median_sec']} s, p10 {out['cuts']['p10_sec']}, p90 {out['cuts']['p90_sec']}, max {out['cuts']['max_sec']}"]},
        "direction.scene_maker.cuts_per_min": {"rule": "Picture changes per minute", "value": out["cuts"]["per_min"], "basis": "measured", "proof": [f"thirds {'/'.join(map(str, thirds))}"]},
        "direction.resource_mix.types (shares)": {"generated-image": f"{round(still_share * 100)}%", "generated-video": f"{round(move_share * 100)}%",
                                                  "proof": f"{kinds['still']} still, {kinds['subtle']} subtle, {kinds['moving']} moving of {len(sample)} sampled shots"},
        "look.can_do.camera_moves": still_share < 0.8,
    }
    if "words" in out:
        style["direction.narration.wpm"] = {"rule": "Speaking speed", "value": out["words"]["wpm"], "basis": "measured",
                                            "proof": [f"{out['words']['count']} words / {round(dur, 1)} s"]}
    out["style"] = style
    if a.out:
        json.dump(out, open(a.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)

    print("\n=== MEASURE ===")
    k = out["cuts"]
    print(f"  cuts     {k['count']}  median {k['median_sec']} s  p10 {k['p10_sec']}  p90 {k['p90_sec']}  max {k['max_sec']}  ({k['per_min']}/min, thirds {'/'.join(map(str, thirds))})")
    mo = out["motion"]
    print(f"  motion   {mo['still']} still, {mo['subtle']} subtle, {mo['moving']} moving of {mo['samples']} shots ({round(still_share * 100)}% still)")
    if "words" in out:
        print(f"  words    {out['words']['count']} words, {out['words']['wpm']} wpm ({out['words']['wpm_talk_span']} over the talk span)")
    else:
        print("  words    no subtitles given (--subs): words per minute not measured")
    print("  style    " + json.dumps(style, ensure_ascii=False)[:600])
    if a.out:
        print(f"  wrote    {a.out}")


if __name__ == "__main__":
    sys.exit(main())
