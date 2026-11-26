#!/usr/bin/env python3
"""render_bench.py - Fast headless Chromium screenshot renderer for a REVA Three.js bench.

Reads sibling bench.json for exact width/height, launches headless Edge/Chrome with
SwiftShader WebGL for each `--at` timestamp, verifies non-empty PNGs, and prints the
matching `reva-code compare` command for immediate full + zoomed visual inspection.
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile


def find_browser():
    for c in (
        os.environ.get("REVA_BROWSER"),
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ):
        if c and os.path.exists(c):
            return c
    raise SystemExit("no Edge/Chrome browser found for headless WebGL bench capture")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--at", default="0,1,2", help="comma-separated t values passed to ?t= (e.g. 0,1,2)")
    ap.add_argument("--scene", default="bench_scene.html", help="HTML scene filename in this bench dir")
    ap.add_argument("--out-prefix", default="out", help="PNG filename prefix (default: out_0.png ...)")
    a = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(here, "bench.json")
    cfg = json.load(open(cfg_path, encoding="utf-8-sig")) if os.path.exists(cfg_path) else {}
    w = int(cfg.get("width") or 1080)
    h = int(cfg.get("height") or 1920)

    scene_path = os.path.join(here, a.scene)
    if not os.path.exists(scene_path):
        raise SystemExit(f"scene file not found: {scene_path}")
    three_js = os.path.join(here, "three.min.js")
    if not os.path.exists(three_js):
        raise SystemExit(f"three.min.js missing next to {a.scene}; re-run reva-code bench or copy three.min.js here")

    browser = find_browser()
    times = [x.strip() for x in a.at.split(",") if x.strip()]
    base_url = "file:///" + scene_path.replace("\\", "/")
    out_files = []

    for idx, tok in enumerate(times):
        out_png = os.path.join(here, f"{a.out_prefix}_{idx}.png")
        url = f"{base_url}?t={tok}&w={w}&h={h}"
        prof = tempfile.mkdtemp(prefix="reva_bench_")
        try:
            cmd = [
                browser,
                "--headless=new",
                "--enable-webgl",
                "--ignore-gpu-blocklist",
                "--use-gl=angle",
                "--use-angle=swiftshader",
                "--enable-unsafe-swiftshader",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-extensions",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                f"--window-size={w},{h}",
                f"--user-data-dir={prof}",
                "--virtual-time-budget=4000",
                f"--screenshot={out_png}",
                url,
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
            if r.returncode != 0 or not os.path.exists(out_png) or os.path.getsize(out_png) < 1000:
                raise SystemExit(
                    f"headless WebGL capture failed at t={tok} ({r.returncode}):\n{(r.stderr or r.stdout)[-800:]}"
                )
            print(f"rendered t={tok} ({w}x{h}) -> {out_png}")
            out_files.append(out_png)
        finally:
            shutil.rmtree(prof, ignore_errors=True)

    study = cfg.get("study") or "<study>"
    tech = cfg.get("technique") or "<technique>"
    eng = cfg.get("engine_id") or "threejs-webgl"
    joined = ",".join(out_files)
    print("\nnext compare:")
    print(f"  python reva_code.py compare {study} {tech} --tool {eng} --mine \"{joined}\" --ref-at ...")
    print(f"  python reva_code.py compare {study} {tech} --tool {eng} --mine \"{joined}\" --ref-at ... --crop 0.15,0.22,0.70,0.52")


if __name__ == "__main__":
    main()
