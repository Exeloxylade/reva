#!/usr/bin/env python3
"""render_bench.py - Fast schematic Manim frame / MP4 renderer reading REVA bench.json."""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--at", default="0,1,2", help="comma-separated t values passed via REVA_BENCH_T (e.g. 0,1,2)")
    ap.add_argument("--scene", default="scene.py", help="Manim Python scene file")
    ap.add_argument("--class-name", default="BenchScene", help="Scene class name inside scene.py")
    ap.add_argument("--out-prefix", default="out", help="PNG filename prefix (default: out_0.png ...)")
    ap.add_argument("--mp4", action="store_true", help="render full animated out.mp4 instead of static keyframes")
    a = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(here, "bench.json")
    cfg = json.load(open(cfg_path, encoding="utf-8-sig")) if os.path.exists(cfg_path) else {}
    w = int(cfg.get("width") or 1080)
    h = int(cfg.get("height") or 1920)
    fps = int(round(float(cfg.get("fps") or 30)))

    scene_path = os.path.join(here, a.scene)
    if not os.path.exists(scene_path):
        raise SystemExit(f"Manim scene not found: {scene_path}")

    media_dir = os.path.join(here, "_manim_media")
    if a.mp4:
        cmd = [
            sys.executable, "-m", "manim", "render",
            "-r", f"{w},{h}", "--fps", str(fps),
            "--media_dir", media_dir, "-o", "out.mp4",
            scene_path, a.class_name,
        ]
        r = subprocess.run(cmd, cwd=here, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        if r.returncode != 0:
            raise SystemExit(f"manim mp4 render failed ({r.returncode}):\n{(r.stderr or r.stdout)[-1000:]}")
        hits = glob.glob(os.path.join(media_dir, "**", "out.mp4"), recursive=True)
        if not hits:
            raise SystemExit("manim completed but out.mp4 was not found under _manim_media")
        dst = os.path.join(here, "out.mp4")
        shutil.copy2(hits[0], dst)
        print(f"rendered mp4 -> {dst}")
        return

    times = [x.strip() for x in a.at.split(",") if x.strip()]
    out_files = []
    for idx, tok in enumerate(times):
        sub_media = os.path.join(media_dir, f"t_{idx}")
        os.makedirs(sub_media, exist_ok=True)
        env = os.environ.copy()
        env["REVA_BENCH_T"] = tok
        cmd = [
            sys.executable, "-m", "manim", "render",
            "-s", "--format", "png", "-r", f"{w},{h}",
            "--media_dir", sub_media, "-o", f"{a.out_prefix}_{idx}.png",
            scene_path, a.class_name,
        ]
        r = subprocess.run(cmd, cwd=here, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        if r.returncode != 0:
            raise SystemExit(f"manim render failed at t={tok} ({r.returncode}):\n{(r.stderr or r.stdout)[-1000:]}")
        hits = sorted(glob.glob(os.path.join(sub_media, "**", f"{a.out_prefix}_{idx}*.png"), recursive=True))
        if not hits:
            hits = sorted(glob.glob(os.path.join(sub_media, "**", "*.png"), recursive=True))
        if not hits:
            raise SystemExit(f"manim completed at t={tok} but produced no PNG under {sub_media}")
        dst_png = os.path.join(here, f"{a.out_prefix}_{idx}.png")
        shutil.copy2(hits[0], dst_png)
        print(f"rendered t={tok} ({w}x{h}) -> {dst_png}")
        out_files.append(dst_png)


if __name__ == "__main__":
    main()
