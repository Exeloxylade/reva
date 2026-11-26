#!/usr/bin/env python3
"""render_bench.py - Fast schematic still / MP4 renderer for REVA headless Blender bench."""
import argparse
import glob
import json
import os
import shutil
import subprocess


def find_blender():
    for c in (os.environ.get("REVA_BLENDER"), shutil.which("blender"), shutil.which("blender.exe")):
        if c and os.path.exists(c):
            return c
    patterns = [
        r"C:\Program Files\Blender Foundation\Blender*\blender.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender*\blender.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Blender*\*\blender.exe"),
    ]
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    raise SystemExit("blender.exe not found (run `winget install BlenderFoundation.Blender` or install portable zip under %LOCALAPPDATA%\\Programs\\Blender)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--at", default="0,1,2", help="comma-separated t timestamps (e.g. 0,1,2)")
    ap.add_argument("--scene", default="render.py", help="Blender Python scene script")
    ap.add_argument("--out-prefix", default="out", help="PNG filename prefix (default: out_0.png ...)")
    ap.add_argument("--mp4", action="store_true", help="render animated out.mp4 instead of PNG stills")
    a = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(here, "bench.json")
    cfg = json.load(open(cfg_path, encoding="utf-8-sig")) if os.path.exists(cfg_path) else {}
    script_path = os.path.join(here, a.scene)
    if not os.path.exists(script_path):
        raise SystemExit(f"Blender script not found: {script_path}")

    blender = find_blender()
    extra = ["--mp4"] if a.mp4 else ["--at", a.at, "--out-prefix", a.out_prefix]
    cmd = [blender, "-b", "-P", script_path, "--", *extra]
    r = subprocess.run(cmd, cwd=here, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    if r.returncode != 0:
        raise SystemExit(f"Blender render failed ({r.returncode}):\n{(r.stderr or r.stdout)[-1000:]}")
    for line in (r.stdout or "").splitlines():
        if line.startswith("rendered "):
            print(line)
    if not a.mp4:
        times = [x.strip() for x in a.at.split(",") if x.strip()]
        for i in range(len(times)):
            p = os.path.join(here, f"{a.out_prefix}_{i}.png")
            if not os.path.exists(p):
                raise SystemExit(f"Blender exited 0 but missing expected {p}")


if __name__ == "__main__":
    main()
