#!/usr/bin/env python3
"""render_bench.py - Fast Remotion React still / MP4 renderer reading REVA bench.json."""
import argparse
import json
import os
import shutil
import subprocess


def find_remotion_cli():
    for c in ("remotion.cmd", "remotion", "npx.cmd", "npx"):
        hit = shutil.which(c)
        if hit:
            return hit
    raise SystemExit("remotion / npx CLI not found on PATH; run: npm.cmd install -g remotion @remotion/cli")


def _build_env():
    env = os.environ.copy()
    appdata = env.get("APPDATA") or ""
    global_nm = os.path.join(appdata, "npm", "node_modules")
    if os.path.isdir(global_nm):
        cur = env.get("NODE_PATH") or ""
        env["NODE_PATH"] = f"{global_nm}{os.pathsep}{cur}" if cur else global_nm
    return env


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--at", default="0,1,2", help="comma-separated t values (e.g. 0,1,2)")
    ap.add_argument("--entry", default="index.jsx", help="Remotion entry filename")
    ap.add_argument("--comp", default="BenchComp", help="Composition id")
    ap.add_argument("--out-prefix", default="out", help="PNG filename prefix (default: out_0.png ...)")
    ap.add_argument("--mp4", action="store_true", help="render full animated out.mp4")
    a = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(here, "bench.json")
    cfg = json.load(open(cfg_path, encoding="utf-8-sig")) if os.path.exists(cfg_path) else {}
    w = int(cfg.get("width") or 1080)
    h = int(cfg.get("height") or 1920)
    fps = float(cfg.get("fps") or 30)
    props = json.dumps({
        "study": cfg.get("study") or "study",
        "technique": cfg.get("technique") or "technique",
    })

    cli = find_remotion_cli()
    prefix = [cli] if os.path.basename(cli).lower().startswith("remotion") else [cli, "remotion"]
    env = _build_env()

    if a.mp4:
        out_mp4 = os.path.join(here, "out.mp4")
        cmd = prefix + [
            "render", a.entry, a.comp, out_mp4,
            "--width", str(w), "--height", str(h), "--props", props,
        ]
        r = subprocess.run(cmd, cwd=here, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        if r.returncode != 0 or not os.path.exists(out_mp4):
            raise SystemExit(f"remotion render failed ({r.returncode}):\n{(r.stderr or r.stdout)[-1000:]}")
        print(f"rendered mp4 -> {out_mp4}")
        return

    times = [x.strip() for x in a.at.split(",") if x.strip()]
    for idx, tok in enumerate(times):
        frame = max(0, int(round(float(tok) * fps)))
        out_png = os.path.join(here, f"{a.out_prefix}_{idx}.png")
        cmd = prefix + [
            "still", a.entry, a.comp, out_png,
            "--frame", str(frame), "--width", str(w), "--height", str(h), "--props", props,
        ]
        r = subprocess.run(cmd, cwd=here, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        if r.returncode != 0 or not os.path.exists(out_png):
            raise SystemExit(f"remotion still failed at t={tok} ({r.returncode}):\n{(r.stderr or r.stdout)[-1000:]}")
        print(f"rendered t={tok} frame={frame} ({w}x{h}) -> {out_png}")


if __name__ == "__main__":
    main()
