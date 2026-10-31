#!/usr/bin/env python3
"""technique.py - study ONE technique of a reference video and check your rebuild against it.

Subcommands (all write into --out):
  strip    frames of a time range at N fps, tiled into one sheet: see how things ENTER and MOVE
           python technique.py strip ref.mp4 --from 35 --to 59 --fps 5 --out lab\\linechart\\theirs
  stills   full-size PNG frames at chosen seconds: measure pixels, sizes, positions
           python technique.py stills ref.mp4 --at 44,56 --out lab\\linechart\\theirs
  palette  the main colours of a still (hex + share), to copy paper / ink / accent exactly
           python technique.py palette lab\\linechart\\theirs\\full_44.png --n 8
  compare  reference stills next to your render at matching moments, one sheet for the eye check
           python technique.py compare --ref lab\\linechart\\theirs\\full_44.png,lab\\linechart\\theirs\\full_56.png \\
                 --mine renders\\linechart.mp4 --mine-at 12.5,25 --out lab\\linechart
Stdlib + ffmpeg (+ Pillow for palette). Sheets are JPEGs you open with the image viewer.
"""
import argparse, glob, os, subprocess, sys

FF = r"C:\ffmpeg\bin\ffmpeg.exe"


def ff(args):
    r = subprocess.run([FF, "-hide_banner", "-v", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-800:])


def strip(a):
    os.makedirs(a.out, exist_ok=True)
    for f in glob.glob(os.path.join(a.out, "s*.jpg")):
        os.remove(f)
    ff(["-ss", str(a.from_), "-t", str(a.to - a.from_), "-i", a.video, "-vf", "fps=%s,scale=320:-2" % a.fps,
        "-q:v", "3", os.path.join(a.out, "s%04d.jpg")])
    n = len(glob.glob(os.path.join(a.out, "s*.jpg")))
    cols = 8
    rows = (n + cols - 1) // cols
    dst = os.path.join(a.out, "_strip_%g-%g.jpg" % (a.from_, a.to))
    ff(["-framerate", "1", "-i", os.path.join(a.out, "s%04d.jpg"), "-vf", "tile=%dx%d:padding=2" % (cols, rows),
        "-frames:v", "1", dst])
    print("%d frames (%.2f s apart) -> %s" % (n, 1 / float(a.fps), dst))
    print("read it row by row: each step is one frame; count frames to time an entry or a move.")


def stills(a):
    os.makedirs(a.out, exist_ok=True)
    for t in [x for x in a.at.split(",") if x]:
        dst = os.path.join(a.out, "full_%s.png" % t.replace(".", "_"))
        ff(["-ss", t, "-i", a.video, "-frames:v", "1", dst])
        print("still", t, "->", dst)


def palette(a):
    from PIL import Image
    import colorsys
    im = Image.open(a.image).convert("RGB").resize((480, 270))
    k = a.n * 4                                   # quantise finely, then report the biggest
    q = im.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: k * 3]
    counts = sorted(q.getcolors(), reverse=True)
    total = sum(c for c, _ in counts)
    rows = []
    for c, i in counts:
        r, g, b = pal[i * 3: i * 3 + 3]
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        rows.append((c / total, "#%02x%02x%02x" % (r, g, b), s, l))
    print("main colours (paper, ink, greys):")
    for share, hx, s, l in rows[: a.n]:
        print("  %s  %5.1f%%" % (hx, 100 * share))
    # accents: thin lines and small chips vanish in a merged palette, so scan every pixel instead
    full = Image.open(a.image).convert("RGB").resize((960, 540))
    buckets = {}
    for (r, g, b) in full.getdata():
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if s > 0.35 and 0.12 < l < 0.85:
            k = (r // 24, g // 24, b // 24)
            n, sr, sg, sb = buckets.get(k, (0, 0, 0, 0))
            buckets[k] = (n + 1, sr + r, sg + g, sb + b)
    px = 960 * 540
    print("accent colours (saturated, any size):")
    for n, sr, sg, sb in sorted(buckets.values(), reverse=True)[:4]:
        if n / px < 0.0005:
            break
        print("  #%02x%02x%02x  %5.2f%%" % (sr // n, sg // n, sb // n, 100 * n / px))


def compare(a):
    os.makedirs(a.out, exist_ok=True)
    refs = [x for x in a.ref.split(",") if x]
    mine = []
    for i, t in enumerate([x for x in a.mine_at.split(",") if x]):
        p = os.path.join(a.out, "_mine_%d.png" % i)
        ff(["-ss", t, "-i", a.mine, "-frames:v", "1", p])
        mine.append(p)
    if len(mine) != len(refs):
        sys.exit("give as many --mine-at times as --ref stills")
    rows = []
    for i, (r, m) in enumerate(zip(refs, mine)):
        row = os.path.join(a.out, "_row_%d.jpg" % i)
        ff(["-i", r, "-i", m, "-filter_complex", "[0]scale=960:-2[a];[1]scale=960:-2[b];[a][b]hstack", row])
        rows.append(row)
    dst = os.path.join(a.out, "compare.jpg")
    if len(rows) == 1:
        os.replace(rows[0], dst)
    else:
        args = []
        for r in rows:
            args += ["-i", r]
        ff(args + ["-filter_complex", "".join("[%d]" % i for i in range(len(rows))) + "vstack=inputs=%d" % len(rows), dst])
        for r in rows:
            os.remove(r)
    for m in mine:
        os.remove(m)
    print("reference LEFT, yours RIGHT ->", dst)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("strip"); p.add_argument("video"); p.add_argument("--from", dest="from_", type=float, required=True)
    p.add_argument("--to", type=float, required=True); p.add_argument("--fps", default="5"); p.add_argument("--out", required=True)
    p = sub.add_parser("stills"); p.add_argument("video"); p.add_argument("--at", required=True); p.add_argument("--out", required=True)
    p = sub.add_parser("palette"); p.add_argument("image"); p.add_argument("--n", type=int, default=8)
    p = sub.add_parser("compare"); p.add_argument("--ref", required=True); p.add_argument("--mine", required=True)
    p.add_argument("--mine-at", required=True); p.add_argument("--out", required=True)
    a = ap.parse_args()
    {"strip": strip, "stills": stills, "palette": palette, "compare": compare}[a.cmd](a)


if __name__ == "__main__":
    main()
