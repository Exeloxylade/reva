#!/usr/bin/env python3
"""Starter test-bench harness for ffmpeg-compositor.

Reads bench.json in the current directory and renders a short synthetic MP4
using the study's measured dimensions, fps, and palette colors so REVA can
verify filtergraph compositing and compare.jpg alignment.
"""
import json
import os
import shutil
import subprocess
import sys


def _find_ffmpeg():
    for cand in (os.environ.get("REVA_FFMPEG"), r"C:\ffmpeg\bin\ffmpeg.exe", shutil.which("ffmpeg")):
        if cand and os.path.exists(cand):
            return cand
    raise SystemExit("ffmpeg not found")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(here, "bench.json")
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as fp:
            cfg = json.load(fp)

    w = int(cfg.get("width") or 640)
    h = int(cfg.get("height") or 360)
    fps = int(round(float(cfg.get("fps") or 24)))
    dur = float(cfg.get("duration_sec") or 3.0)
    dur = max(1.0, min(dur, 10.0))
    pal = cfg.get("palette") or {}
    main_cols = pal.get("main") or []
    accents = pal.get("accents") or []
    bg = (main_cols[0]["hex"] if main_cols else "#e9e8e6").lstrip("#")
    accent = (accents[0]["hex"] if accents else "#8b1a2b").lstrip("#")

    out_mp4 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "out.mp4")
    bw = max(60, w // 3)
    bh = max(40, h // 3)
    bx = max(10, w // 8)
    by = max(10, h // 6)
    cmd = [
        _find_ffmpeg(), "-hide_banner", "-v", "error", "-y",
        "-f", "lavfi", "-i", f"color=c=0x{bg}:s={w}x{h}:d={dur:.2f}:r={fps}",
        "-vf", f"drawbox=x={bx}:y={by}:w={bw}:h={bh}:color=0x{accent}:t=fill",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", out_mp4,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(r.stderr[-600:] or "ffmpeg render failed")
    print(f"rendered {w}x{h} @ {fps}fps ({dur:.2f}s) -> {out_mp4}")


if __name__ == "__main__":
    main()
