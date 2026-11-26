#!/usr/bin/env python3
"""render_bench.py - Fast schematic still / MP4 renderer for REVA HyperFrames 2D bench."""
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
    raise SystemExit("no Edge/Chrome browser found for headless bench capture")


def find_hyperframes():
    for c in ("hyperframes.cmd", "hyperframes", "npx.cmd", "npx"):
        hit = shutil.which(c)
        if hit:
            return hit
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--at", default="0,1,2", help="comma-separated t values passed via ?t= (default: 0,1,2)")
    ap.add_argument("--scene", default="index.html", help="HTML scene filename in this bench dir")
    ap.add_argument("--out-prefix", default="out", help="PNG prefix (default: out_0.png ...)")
    ap.add_argument("--mp4", action="store_true", help="render full out.mp4 via HyperFrames CLI instead of fast stills")
    a = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(here, "bench.json")
    cfg = json.load(open(cfg_path, encoding="utf-8-sig")) if os.path.exists(cfg_path) else {}
    w = int(cfg.get("width") or 1080)
    h = int(cfg.get("height") or 1920)
    fps = int(round(float(cfg.get("fps") or 30)))

    scene_path = os.path.join(here, a.scene)
    if not os.path.exists(scene_path):
        raise SystemExit(f"HTML file not found: {scene_path}")

    if a.mp4:
        hf = find_hyperframes()
        if not hf:
            raise SystemExit("hyperframes / npx CLI not found on PATH")
        out_mp4 = os.path.join(here, "out.mp4")
        prefix = [hf] if os.path.basename(hf).lower().startswith("hyperframes") else [hf, "hyperframes"]
        cmd = prefix + ["render", scene_path, "--out", out_mp4, "--width", str(w), "--height", str(h), "--fps", str(fps)]
        r = subprocess.run(cmd, cwd=here)
        if r.returncode != 0 or not os.path.exists(out_mp4):
            raise SystemExit(f"HyperFrames render failed ({r.returncode})")
        print(f"rendered mp4 -> {out_mp4}")
        return

    browser = find_browser()
    times = [x.strip() for x in a.at.split(",") if x.strip()]
    base_url = "file:///" + scene_path.replace("\\", "/")
    for idx, tok in enumerate(times):
        out_png = os.path.join(here, f"{a.out_prefix}_{idx}.png")
        url = f"{base_url}?t={tok}&w={w}&h={h}"
        prof = tempfile.mkdtemp(prefix="reva_hf_")
        try:
            cmd = [
                browser, "--headless=new", "--no-first-run", "--no-default-browser-check",
                "--disable-extensions", "--hide-scrollbars", "--force-device-scale-factor=1",
                f"--window-size={w},{h}", f"--user-data-dir={prof}", "--virtual-time-budget=3000",
                f"--screenshot={out_png}", url,
            ]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90)
            if r.returncode != 0 or not os.path.exists(out_png):
                raise SystemExit(f"headless capture failed at t={tok}:\n{(r.stderr or r.stdout)[-600:]}")
            print(f"rendered t={tok} ({w}x{h}) -> {out_png}")
        finally:
            shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    main()
