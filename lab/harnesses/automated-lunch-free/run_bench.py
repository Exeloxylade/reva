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
    extra = sys.argv[2:]
    npm = "npm.cmd" if os.name == "nt" else "npm"
    if action == "check":
        cmd = ["node", os.path.join(app, "scripts", "style-check.js"), *extra]
    elif action == "style-test":
        if not extra:
            raise SystemExit("pass <style-id> for style-test")
        sid, rest = extra[0], extra[1:]
        cmd = [npm, "run", "style-test", "--", "--style", sid, "--preset", "cinematic-story", *rest]
    elif action == "make":
        cmd = [npm, "run", "make", "--", *extra]
    elif action == "map":
        cmd = [npm, "run", "map", "--", *extra]
    elif action == "gfx":
        cmd = [npm, "run", "gfx", "--", *extra]
    elif action == "list-styles":
        cmd = [npm, "run", "make", "--", "--list-styles"]
    elif action == "list-presets":
        cmd = [npm, "run", "make", "--", "--list-presets"]
    else:
        raise SystemExit(
            f"unknown action {action!r} "
            "(use check | style-test <id> | make ... | map ... | gfx ... | list-styles | list-presets)"
        )
    raise SystemExit(subprocess.call(cmd, cwd=app))


if __name__ == "__main__":
    main()
