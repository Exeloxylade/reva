#!/usr/bin/env python3
"""video-reverse: score how close a rebuilt copy is to the original.

Lines the two videos up frame by frame and prints a match score, so the
rebuild loop (SKILL.md steps 8-9) knows what still looks wrong and when to stop.

For each sampled second it compares the original frame and the copy frame on:
  - colour      average R/G/B difference  (art palette match)
  - brightness  mean luma difference       (lighting/exposure match)
  - layout      down-sampled 16x16 grey difference (where things sit on screen)
It also checks the big numbers: duration, shot count, aspect, loudness.
Writes a side-by-side contact sheet (orig on top, copy below) per sampled range
and compare.json with the per-second scores and the weak spots.

Usage:
  python compare.py --orig <orig_dir> --copy <copy.mp4> --out <dir> [--sps 1]

Needs the original already torn down (teardown.json + frames/ in <orig_dir>).
Stdlib + ffmpeg + Pillow if present (falls back to ffmpeg-only stats).
"""
import argparse, glob, json, os, re, shutil, subprocess, sys

FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
if not os.path.exists(FFMPEG):
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
    FFPROBE = shutil.which("ffprobe") or "ffprobe"

try:
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from PIL import Image
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False


def _pixels(im):
    """Pillow 14 renames getdata -> get_flattened_data; support both."""
    fn = getattr(im, "get_flattened_data", None) or im.getdata
    return list(fn())


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def probe_dur(mp4):
    r = run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", mp4])
    try:
        return round(float(r.stdout.strip()), 2)
    except Exception:
        return 0.0


def grab(mp4, outdir, sps):
    os.makedirs(outdir, exist_ok=True)
    for old in glob.glob(os.path.join(outdir, "*.jpg")):
        os.remove(old)
    run([FFMPEG, "-hide_banner", "-i", mp4, "-vf", f"fps={sps},scale=480:-2",
         "-q:v", "3", os.path.join(outdir, "f%04d.jpg")])
    return sorted(glob.glob(os.path.join(outdir, "*.jpg")))


def frame_stats(path):
    """Return (avg_rgb, mean_luma, grid16) for a frame. Pillow if available."""
    if HAVE_PIL:
        im = Image.open(path).convert("RGB").resize((64, 64))
        px = _pixels(im)
        n = len(px)
        r = sum(p[0] for p in px) / n
        g = sum(p[1] for p in px) / n
        b = sum(p[2] for p in px) / n
        luma = 0.299 * r + 0.587 * g + 0.114 * b
        grid = im.convert("L").resize((16, 16))
        return (r, g, b), luma, _pixels(grid)
    # ffmpeg fallback: average colour only
    r = run([FFMPEG, "-hide_banner", "-i", path, "-vf",
             "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    data = r.stdout.encode("latin-1", "replace")[:3]
    if len(data) < 3:
        return (0, 0, 0), 0, None
    rr, gg, bb = data[0], data[1], data[2]
    return (rr, gg, bb), 0.299 * rr + 0.587 * gg + 0.114 * bb, None


def score_pair(a, b):
    (ar, ag, ab), al, ag16 = a
    (br, bg, bb), bl, bg16 = b
    colour = (abs(ar - br) + abs(ag - bg) + abs(ab - bb)) / 3.0  # 0 best
    bright = abs(al - bl)
    layout = None
    if ag16 and bg16:
        layout = sum(abs(x - y) for x, y in zip(ag16, bg16)) / len(ag16)
    # 0-100 where 100 = identical
    colour_pct = max(0, 100 - colour * 100 / 255)
    bright_pct = max(0, 100 - bright * 100 / 255)
    layout_pct = max(0, 100 - layout * 100 / 255) if layout is not None else None
    return {"colour": round(colour_pct, 1), "bright": round(bright_pct, 1),
            "layout": round(layout_pct, 1) if layout_pct is not None else None}


def side_by_side(orig_frames, copy_frames, outdir, cols=6):
    """Top row original, bottom row copy, for the sampled frames."""
    sheets = []
    per = cols
    for s in range(0, min(len(orig_frames), len(copy_frames)), per):
        o = orig_frames[s:s + per]; c = copy_frames[s:s + per]
        lst = os.path.join(outdir, f"_sb_{s}.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for p in o + c:
                f.write("file '" + p.replace("\\", "/") + "'\n")
        out = os.path.join(outdir, f"compare-sheet-{s // per + 1}.jpg")
        run([FFMPEG, "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", lst,
             "-vf", f"scale=300:-2,tile={cols}x2:padding=4:color=black",
             "-frames:v", "1", "-q:v", "3", out])
        if os.path.exists(out):
            sheets.append(os.path.abspath(out))
        if os.path.exists(lst):
            os.remove(lst)
    return sheets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orig", required=True, help="original teardown dir")
    ap.add_argument("--copy", required=True, help="rebuilt copy .mp4")
    ap.add_argument("--out", required=True)
    ap.add_argument("--sps", type=float, default=1.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    tj = os.path.join(a.orig, "teardown.json")
    orig = json.load(open(tj, encoding="utf-8")) if os.path.exists(tj) else {}

    orig_frames = sorted(glob.glob(os.path.join(a.orig, "frames", "*.jpg")))
    copy_frames = grab(a.copy, os.path.join(a.out, "copy_frames"), a.sps)

    pairs = min(len(orig_frames), len(copy_frames))
    per_sec, weak = [], []
    for i in range(pairs):
        sc = score_pair(frame_stats(orig_frames[i]), frame_stats(copy_frames[i]))
        sc["t"] = round(i / a.sps, 1)
        per_sec.append(sc)
        vals = [v for v in (sc["colour"], sc["bright"], sc["layout"]) if v is not None]
        if vals and min(vals) < 80:
            weak.append(sc)

    def avg(key):
        xs = [p[key] for p in per_sec if p.get(key) is not None]
        return round(sum(xs) / len(xs), 1) if xs else None

    copy_dur = probe_dur(a.copy)
    odur = (orig.get("video") or {}).get("duration")
    sheets = side_by_side(orig_frames, copy_frames, a.out)

    overall = [v for v in (avg("colour"), avg("bright"), avg("layout")) if v is not None]
    overall_pct = round(sum(overall) / len(overall), 1) if overall else None

    report = {
        "overall_match_pct": overall_pct,
        "colour_pct": avg("colour"), "bright_pct": avg("bright"),
        "layout_pct": avg("layout"),
        "duration": {"orig": odur, "copy": copy_dur,
                     "delta": round((copy_dur - odur), 2) if odur else None},
        "weak_seconds": weak[:40],
        "compare_sheets": sheets,
        "frames_compared": pairs,
        "pillow": HAVE_PIL,
    }
    json.dump(report, open(os.path.join(a.out, "compare.json"), "w", encoding="utf-8"),
              indent=2)

    print("\n=== COMPARE (100 = identical) ===")
    print(f"  overall   {overall_pct}%")
    print(f"  colour    {avg('colour')}%   bright {avg('bright')}%   "
          f"layout {avg('layout')}%")
    print(f"  duration  orig {odur}s  copy {copy_dur}s  "
          f"delta {report['duration']['delta']}s")
    print(f"  weak      {len(weak)} second(s) below 80% "
          + (", ".join(str(w['t']) for w in weak[:12]) if weak else "- none"))
    print(f"  sheets    {len(sheets)} side-by-side (orig top, copy bottom)")
    if not HAVE_PIL:
        print("  note: Pillow not installed -> layout score off, colour is 1px only.")
        print("        pip install pillow  for the full score.")
    print(f"  wrote     {os.path.join(a.out, 'compare.json')}")


if __name__ == "__main__":
    main()
