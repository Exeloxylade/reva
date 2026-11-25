#!/usr/bin/env python3
"""Code-callable runner for Automated-Lunch-Free CLI operations."""
import json
import os
import subprocess
import sys


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(here, "bench.json")
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as fp:
            cfg = json.load(fp)
    app = cfg.get("app_dir") or os.environ.get("REVA_APP")
    if not app or not os.path.isdir(app):
        raise SystemExit("Automated-Lunch-Free app_dir not found in bench.json or REVA_APP")

    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    npm = "npm.cmd" if os.name == "nt" else "npm"
    if action == "check":
        sid = sys.argv[2]
        cmd = ["node", os.path.join(app, "scripts", "style-check.js"), sid]
    elif action == "style-test":
        sid = sys.argv[2]
        cmd = [npm, "run", "style-test", "--", "--style", sid, "--preset", "cinematic-story"]
    elif action == "map":
        cmd = [npm, "run", "map", "--", *sys.argv[2:]]
    else:
        raise SystemExit(f"unknown action {action!r} (use check <id> | style-test <id> | map ...)")
    raise SystemExit(subprocess.call(cmd, cwd=app))


if __name__ == "__main__":
    main()
