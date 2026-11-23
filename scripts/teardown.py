#!/usr/bin/env python3
"""teardown.py - tear any reference video apart into cuts, timestamped contact sheets, transcript, and loudness.

Usage:
  python teardown.py <url-or-file> --out <dir> [--name ref] [--sps auto|1] [--sheet-cols 6] [--sheet-rows 5]
"""
import argparse
import glob
import json
import math
import os
import re
import shutil
import sys

try:
    from . import _common as C
except ImportError:
    import _common as C


def is_url(s):
    return s.startswith("http://") or s.startswith("https://")


def download(url, outdir, name):
    """Download video + subtitles with yt-dlp. Returns (video_path, info_dict)."""
    base = os.path.join(outdir, name)
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bv*+ba/b", "-S", "res:1080,fps",
        "--merge-output-format", "mp4",
        "--write-info-json",
        "--write-auto-subs", "--write-subs", "--sub-langs", ".*-orig,en,id",
        "--convert-subs", "srt", "--ignore-errors",
        "-o", base + ".%(ext)s", url,
    ]
    print("  downloading ...")
    r = C.run_cmd(cmd)
    mp4 = base + ".mp4"
    if not os.path.exists(mp4):
        hits = glob.glob(base + ".*")
        mp4 = next((h for h in hits if h.lower().endswith((".mp4", ".mkv", ".webm", ".mov"))), None)
    if r.returncode != 0:
        if not mp4:
            print(r.stdout[-2000:])
            print(r.stderr[-2000:])
            raise SystemExit("yt-dlp failed")
        print("  yt-dlp warned (often a subtitle track hit HTTP 429); the video itself downloaded")
    info = {}
    ij = base + ".info.json"
    if os.path.exists(ij):
        with open(ij, encoding="utf-8") as fp:
            info = json.load(fp)
    return mp4, info


def resolve_sps(sps_arg, dur):
    """Resolve frames-per-second ('auto' adapts cleanly to long videos)."""
    if str(sps_arg).strip().lower() == "auto":
        if dur <= 180:
            return 1.0
        if dur <= 600:
            return 0.5
        return max(0.1, min(0.25, round(300.0 / max(dur, 1.0), 2)))
    val = float(sps_arg)
    if val <= 0:
        raise SystemExit("--sps must be > 0 or 'auto'")
    return val


def shot_list(cuts, dur):
    bounds = [0.0] + cuts + [dur]
    shots = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        if b - a < 0.15:
            continue
        shots.append({
            "i": len(shots) + 1,
            "start": round(a, 2),
            "end": round(b, 2),
            "len": round(b - a, 2),
        })
    return shots


def grab_frames(mp4, outdir, sps):
    fdir = os.path.join(outdir, "frames")
    os.makedirs(fdir, exist_ok=True)
    for old in glob.glob(os.path.join(fdir, "*.jpg")):
        os.remove(old)
    r = C.run_cmd([
        C.find_ffmpeg(), "-hide_banner", "-v", "error", "-y",
        "-i", mp4,
        "-vf", f"fps={sps},scale=480:-2",
        "-q:v", "3",
        os.path.join(fdir, "f%04d.jpg"),
    ])
    if r.returncode != 0:
        raise SystemExit(r.stderr[-800:] or "ffmpeg frame grab failed")
    return sorted(glob.glob(os.path.join(fdir, "*.jpg")))


def contact_sheets(frames, outdir, sps, cols=6, rows=5):
    """Tile frames into Pillow contact sheets with MM:SS timestamp badges."""
    from PIL import Image, ImageDraw

    for old in glob.glob(os.path.join(outdir, "contact-sheet-*.jpg")):
        os.remove(old)
    if not frames:
        return []

    with Image.open(frames[0]) as sample:
        w0, h0 = sample.size
    tw = 240 if h0 > w0 else 300
    th = max(100, int(round(tw * h0 / max(w0, 1))))
    pad = 4
    font = C.load_font(14, bold=True)

    sheets = []
    per = cols * rows
    for start_idx in range(0, len(frames), per):
        chunk = frames[start_idx:start_idx + per]
        used_rows = math.ceil(len(chunk) / cols)
        sheet_w = cols * tw + (cols + 1) * pad
        sheet_h = used_rows * th + (used_rows + 1) * pad
        canvas = Image.new("RGB", (sheet_w, sheet_h), (16, 16, 16))
        draw = ImageDraw.Draw(canvas)

        for offset, fpath in enumerate(chunk):
            r_idx, c_idx = divmod(offset, cols)
            x = pad + c_idx * (tw + pad)
            y = pad + r_idx * (th + pad)
            with Image.open(fpath) as im:
                tile = im.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
            canvas.paste(tile, (x, y))
            t_sec = (start_idx + offset) / float(sps)
            C.draw_badge(draw, (x + 4, y + 4), C.fmt_ts(t_sec), font, bg=(18, 18, 18), fg=(255, 255, 255), pad_x=5, pad_y=2)

        out = os.path.join(outdir, f"contact-sheet-{start_idx // per + 1}.jpg")
        canvas.save(out, quality=88)
        sheets.append(out)
    return sheets


def read_subs(outdir, name, dur):
    """Parse best available subtitle file and write transcript.json, transcript.txt, script.txt."""
    sub_path = C.pick_subtitle_file(outdir, name=name)
    if not sub_path:
        return {"words": 0, "wpm": 0, "wpm_talk_span": 0, "has_script": False, "subtitle_file": None}

    parsed = C.parse_subtitles(sub_path)
    words = parsed["words"]
    wpm = round(words / (dur / 60.0), 1) if dur > 0 and words else 0
    talk_span = parsed["talk_span_sec"]
    wpm_span = round(words / (talk_span / 60.0), 1) if talk_span > 1.0 and words else wpm

    with open(os.path.join(outdir, "transcript.json"), "w", encoding="utf-8") as fp:
        json.dump(
            {
                "subtitle_file": os.path.basename(sub_path),
                "words": words,
                "wpm": wpm,
                "wpm_talk_span": wpm_span,
                "talk_span_sec": talk_span,
                "cues": parsed["cues"],
            },
            fp,
            indent=2,
            ensure_ascii=False,
        )
    if parsed["cues"]:
        with open(os.path.join(outdir, "transcript.txt"), "w", encoding="utf-8") as fp:
            for c in parsed["cues"]:
                fp.write(f"[{C.fmt_ts(c['start'])}] {c['text']}\n")
    if parsed["text"]:
        with open(os.path.join(outdir, "script.txt"), "w", encoding="utf-8") as fp:
            fp.write(parsed["text"] + "\n")

    return {
        "words": words,
        "wpm": wpm,
        "wpm_talk_span": wpm_span,
        "has_script": bool(parsed["text"]),
        "subtitle_file": os.path.basename(sub_path),
    }


def measure_sound(mp4, has_audio):
    if not has_audio:
        return {"mean_db": None, "peak_db": None, "lufs": None, "true_peak": None}
    ff = C.find_ffmpeg()
    r = C.run_cmd([ff, "-hide_banner", "-i", mp4, "-af", "volumedetect", "-f", "null", "-"])
    mean = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", r.stderr)
    peak = re.search(r"max_volume:\s*(-?[0-9.]+) dB", r.stderr)
    lufs = tp = None
    r2 = C.run_cmd([ff, "-hide_banner", "-i", mp4, "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r2.stderr, re.S)
    if m:
        try:
            j = json.loads(m.group(0))
            lufs = j.get("input_i")
            tp = j.get("input_tp")
        except Exception:
            pass
    return {
        "mean_db": mean.group(1) if mean else None,
        "peak_db": peak.group(1) if peak else None,
        "lufs": lufs,
        "true_peak": tp,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="video URL or local file path")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="ref")
    ap.add_argument("--sps", default="1.0", help="frames per second or 'auto'")
    ap.add_argument("--sheet-cols", type=int, default=6)
    ap.add_argument("--sheet-rows", type=int, default=5)
    ap.add_argument("--scene", type=float, default=0.30, help="cut sensitivity 0-1")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    info = {}
    if is_url(a.input):
        mp4, info = download(a.input, a.out, a.name)
    else:
        src = os.path.abspath(a.input)
        if not os.path.exists(src):
            raise SystemExit(f"input file not found: {a.input}")
        ext = os.path.splitext(src)[1].lower() or ".mp4"
        dst = os.path.join(a.out, a.name + ext)
        if src != os.path.abspath(dst):
            shutil.copy2(src, dst)
        mp4 = dst
        stem = os.path.splitext(src)[0]
        for sub_ext in (".srt", ".vtt"):
            side = stem + sub_ext
            if os.path.exists(side):
                shutil.copy2(side, os.path.join(a.out, a.name + sub_ext))

    if not mp4 or not os.path.exists(mp4):
        raise SystemExit("no video file to work on")

    print("  probing ...")
    meta = C.probe_media(mp4)
    sps = resolve_sps(a.sps, meta["duration"])
    print("  finding cuts ...")
    cuts = C.detect_cuts(mp4, threshold=a.scene)
    shots = shot_list(cuts, meta["duration"])
    print(f"  grabbing frames ({sps} fps) ...")
    frames = grab_frames(mp4, a.out, sps)
    print("  tiling contact sheets ...")
    sheets = contact_sheets(frames, a.out, sps, a.sheet_cols, a.sheet_rows)
    print("  reading subtitles ...")
    subs = read_subs(a.out, a.name, meta["duration"])
    print("  measuring sound ...")
    sound = measure_sound(mp4, meta["has_audio"])

    shot_lens = [s["len"] for s in shots] or [0]
    report = {
        "source": a.input,
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "video": meta,
        "sps": sps,
        "shots": {
            "count": len(shots),
            "avg_len": round(sum(shot_lens) / len(shot_lens), 2),
            "min_len": min(shot_lens),
            "max_len": max(shot_lens),
            "list": shots,
        },
        "script": subs,
        "sound": sound,
        "frames": len(frames),
        "contact_sheets": [os.path.abspath(s) for s in sheets],
        "aspect": meta["aspect_label"],
        "aspect_ratio": meta["aspect_ratio"],
        "format_kind": meta["format_kind"],
    }
    out_json = os.path.join(a.out, "teardown.json")
    with open(out_json, "w", encoding="utf-8") as fp:
        json.dump(report, fp, indent=2, ensure_ascii=False)

    print("\n=== TEARDOWN ===")
    if report["title"]:
        print(f"  title    {report['title']}  ({report['uploader']})")
    print(f"  video    {report['aspect']}  {meta['fps']} fps  {meta['duration']}s  audio {meta['audio_channels']}ch")
    print(f"  shots    {len(shots)}  (avg {report['shots']['avg_len']}s, {report['shots']['min_len']}-{report['shots']['max_len']}s)")
    print(f"  script   {subs['words']} words  {subs['wpm']} wpm" + (f" ({subs['subtitle_file']})" if subs["has_script"] else "  (NO subtitles found)"))
    if sound["lufs"] is not None:
        print(f"  sound    {sound['lufs']} LUFS  peak {sound['true_peak']} dBTP  (mean {sound['mean_db']} dB)")
    else:
        print("  sound    no audio stream")
    print(f"  frames   {len(frames)} grabbed @ {sps} fps -> {len(sheets)} contact sheet(s)")
    print(f"  wrote    {out_json}")


if __name__ == "__main__":
    main()
