#!/usr/bin/env python3
"""technique.py - inspect one reference technique (strip, stills, palette, side-by-side compare).

Subcommands:
  strip    frames of a time range at N fps, tiled with timestamps into _strip_<from>-<to>.jpg
  stills   full-size PNG frames at chosen seconds (full_<t>.png)
  palette  main hex colors + saturated accent hex colors from 1+ stills
  compare  reference stills (left) next to your render (right) -> compare.jpg
"""
import argparse
import glob
import json
import math
import os

try:
    from . import _common as C
except ImportError:
    import _common as C


def ff(args):
    r = C.run_cmd([C.find_ffmpeg(), "-hide_banner", "-v", "error", "-y"] + args)
    if r.returncode != 0:
        raise SystemExit(r.stderr[-800:] or "ffmpeg command failed")


def strip(a):
    from PIL import Image, ImageDraw

    if a.to <= a.from_:
        raise SystemExit(f"--to ({a.to}) must be greater than --from ({a.from_})")
    fps_val = float(a.fps)
    if fps_val <= 0:
        raise SystemExit("--fps must be > 0")

    os.makedirs(a.out, exist_ok=True)
    for f in glob.glob(os.path.join(a.out, "s*.jpg")):
        os.remove(f)

    ff([
        "-ss", str(a.from_), "-t", str(a.to - a.from_), "-i", a.video,
        "-vf", f"fps={a.fps},scale=360:-2", "-q:v", "3",
        os.path.join(a.out, "s%04d.jpg"),
    ])
    frames = sorted(glob.glob(os.path.join(a.out, "s*.jpg")))
    if not frames:
        raise SystemExit("no frames extracted for strip range")

    try:
        with Image.open(frames[0]) as sample:
            w0, h0 = sample.size
        tw = 240 if h0 > w0 else 320
        th = max(90, int(round(tw * h0 / max(w0, 1))))
        cols = min(8, len(frames))
        rows = math.ceil(len(frames) / cols)
        pad = 4
        canvas = Image.new("RGB", (cols * tw + (cols + 1) * pad, rows * th + (rows + 1) * pad), (16, 16, 16))
        draw = ImageDraw.Draw(canvas)
        font = C.load_font(13, bold=True)

        for idx, fpath in enumerate(frames):
            r_idx, c_idx = divmod(idx, cols)
            x = pad + c_idx * (tw + pad)
            y = pad + r_idx * (th + pad)
            with Image.open(fpath) as im:
                tile = im.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
            canvas.paste(tile, (x, y))
            t_sec = a.from_ + idx / fps_val
            C.draw_badge(draw, (x + 4, y + 4), f"{t_sec:.1f}s", font, bg=(18, 18, 18), fg=(255, 255, 255), pad_x=4, pad_y=2)

        dst = os.path.join(a.out, f"_strip_{C.norm_ts(a.from_)}-{C.norm_ts(a.to)}.jpg")
        canvas.save(dst, quality=88)
        print(f"{len(frames)} frames ({1.0 / fps_val:.2f} s apart) -> {dst}")
        print("read it row by row: each step is one frame; count frames to time an entry or move.")
    finally:
        if not a.keep_frames:
            for f in frames:
                if os.path.exists(f):
                    os.remove(f)


def render_grid_still(src_png, dst_png):
    """Overlay a 100px/200px pixel coordinate grid and center crosshair onto src_png."""
    from PIL import Image, ImageDraw

    with Image.open(src_png) as im:
        base = im.convert("RGBA")
    w, h = base.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = C.load_font(12, bold=True)

    for x in range(100, w, 100):
        major = (x % 200 == 0)
        draw.line([(x + 1, 0), (x + 1, h)], fill=(0, 0, 0, 95 if major else 50), width=1)
        draw.line([(x, 0), (x, h)], fill=(255, 255, 255, 135 if major else 70), width=1)
        if major or w <= 900:
            C.draw_badge(draw, (x + 3, 4), str(x), font, bg=(18, 18, 18, 190), fg=(255, 255, 255, 240), pad_x=3, pad_y=1)

    for y in range(100, h, 100):
        major = (y % 200 == 0)
        draw.line([(0, y + 1), (w, y + 1)], fill=(0, 0, 0, 95 if major else 50), width=1)
        draw.line([(0, y), (w, y)], fill=(255, 255, 255, 135 if major else 70), width=1)
        if major or h <= 900:
            C.draw_badge(draw, (4, y + 3), str(y), font, bg=(18, 18, 18, 190), fg=(255, 255, 255, 240), pad_x=3, pad_y=1)

    cx, cy = w // 2, h // 2
    draw.line([(cx, 0), (cx, h)], fill=(200, 50, 62, 165), width=1)
    draw.line([(0, cy), (w, cy)], fill=(200, 50, 62, 165), width=1)

    res_label = f"{w}x{h}"
    rbox = draw.textbbox((0, 0), res_label, font=font)
    rw = (rbox[2] - rbox[0]) + 10
    C.draw_badge(draw, (max(4, w - rw - 6), 4), res_label, font, bg=(139, 26, 43, 220), fg=(255, 255, 255, 255), pad_x=5, pad_y=2)

    Image.alpha_composite(base, overlay).convert("RGB").save(dst_png)
    return dst_png


def stills(a):
    os.makedirs(a.out, exist_ok=True)
    raw_times = [x.strip() for x in a.at.split(",") if x.strip()]
    if not raw_times:
        raise SystemExit("provide at least one timestamp with --at")
    out_paths = []
    for raw in raw_times:
        norm = C.norm_ts(raw)
        tok = C.ts_token(raw)
        dst = os.path.join(a.out, f"full_{tok}.png")
        ff(["-ss", norm, "-i", a.video, "-frames:v", "1", dst])
        print(f"still {norm} -> {dst}")
        out_paths.append(dst)
        if getattr(a, "grid", False):
            gdst = os.path.join(a.out, f"grid_{tok}.png")
            render_grid_still(dst, gdst)
            print(f"grid  {norm} -> {gdst}")
    return out_paths


def palette(a):
    pal = C.extract_palette(a.images, n=a.n)
    if not pal["main"]:
        raise SystemExit("no readable images found for palette")
    print("main colours (paper, ink, greys):")
    for row in pal["main"]:
        print(f"  {row['hex']}  {row['share']:5.1f}%")
    print("accent colours (saturated, any size):")
    for row in pal["accents"]:
        print(f"  {row['hex']}  {row['share']:5.2f}%")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fp:
            json.dump(pal, fp, indent=2)
        print("palette ->", a.json)


def _scale_to_width(im, target_w):
    from PIL import Image

    w, h = im.size
    if w == target_w:
        return im
    new_h = max(2, int(round(h * target_w / max(w, 1))))
    return im.resize((target_w, new_h), Image.Resampling.LANCZOS)


def compare(a):
    from PIL import Image, ImageDraw

    os.makedirs(a.out, exist_ok=True)
    refs = [x.strip() for x in a.ref.split(",") if x.strip()]
    mine_times = [C.norm_ts(x) for x in a.mine_at.split(",") if x.strip()]
    if len(mine_times) != len(refs):
        raise SystemExit(f"give as many --mine-at times ({len(mine_times)}) as --ref stills ({len(refs)})")

    mine_imgs = []
    try:
        for i, t in enumerate(mine_times):
            p = os.path.join(a.out, f"_mine_{i}.png")
            ff(["-ss", t, "-i", a.mine, "-frames:v", "1", p])
            mine_imgs.append(p)

        col_w = 960
        hdr_h = 34
        gap = 8
        font = C.load_font(16, bold=True)
        row_imgs = []

        for r_path, m_path, mt in zip(refs, mine_imgs, mine_times):
            if not os.path.exists(r_path):
                raise SystemExit(f"reference still not found: {r_path}")
            with Image.open(r_path) as rim:
                r_scaled = _scale_to_width(rim.convert("RGB"), col_w)
            with Image.open(m_path) as mim:
                m_scaled = _scale_to_width(mim.convert("RGB"), col_w)

            body_h = max(r_scaled.height, m_scaled.height)
            row_w = col_w * 2 + gap
            row_canvas = Image.new("RGB", (row_w, hdr_h + body_h), (20, 20, 20))
            draw = ImageDraw.Draw(row_canvas)
            C.draw_badge(draw, (8, 5), f"REF  {os.path.basename(r_path)}", font, bg=(36, 36, 36), fg=(240, 240, 240))
            C.draw_badge(draw, (col_w + gap + 8, 5), f"MINE  @{mt}s", font, bg=(139, 26, 43), fg=(255, 255, 255))

            r_y = hdr_h + (body_h - r_scaled.height) // 2
            m_y = hdr_h + (body_h - m_scaled.height) // 2
            row_canvas.paste(r_scaled, (0, r_y))
            row_canvas.paste(m_scaled, (col_w + gap, m_y))
            row_imgs.append(row_canvas)

        total_h = sum(r.height for r in row_imgs) + gap * max(0, len(row_imgs) - 1)
        out_canvas = Image.new("RGB", (col_w * 2 + gap, total_h), (12, 12, 12))
        y = 0
        for row in row_imgs:
            out_canvas.paste(row, (0, y))
            y += row.height + gap

        dst = os.path.join(a.out, "compare.jpg")
        out_canvas.save(dst, quality=90)
        print("reference LEFT, yours RIGHT ->", dst)
        return dst
    finally:
        for m in mine_imgs:
            if os.path.exists(m):
                os.remove(m)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("strip")
    p.add_argument("video")
    p.add_argument("--from", dest="from_", type=float, required=True)
    p.add_argument("--to", type=float, required=True)
    p.add_argument("--fps", default="5")
    p.add_argument("--out", required=True)
    p.add_argument("--keep-frames", action="store_true")

    p = sub.add_parser("stills")
    p.add_argument("video")
    p.add_argument("--at", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--grid", action="store_true")

    p = sub.add_parser("palette")
    p.add_argument("images", nargs="+")
    p.add_argument("--n", type=int, default=6)
    p.add_argument("--json")

    p = sub.add_parser("compare")
    p.add_argument("--ref", required=True)
    p.add_argument("--mine", required=True)
    p.add_argument("--mine-at", required=True)
    p.add_argument("--out", required=True)

    a = ap.parse_args()
    {"strip": strip, "stills": stills, "palette": palette, "compare": compare}[a.cmd](a)


if __name__ == "__main__":
    main()
