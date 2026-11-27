#!/usr/bin/env python3
"""browse.py - Standalone headless browser runner for REVA Engineering Lab (web-browser harness)."""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT_CANDIDATES = [
    os.path.abspath(os.path.join(HERE, "..", "..", "kit")),
    os.path.abspath(os.path.join(HERE, "..", "..", "..", "lab", "kit")),
]
for kd in KIT_CANDIDATES:
    if os.path.isdir(kd) and kd not in sys.path:
        sys.path.insert(0, kd)

import web_capture


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url", help="URL (http/https/file) to render and inspect")
    ap.add_argument("--out-dir", default=HERE)
    ap.add_argument("--slug", default="page")
    ap.add_argument("--screenshot", action="store_true")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=1600)
    ap.add_argument("--wait-ms", type=int, default=4000)
    a = ap.parse_args(argv)

    res = web_capture.browse_url(
        a.url,
        out_dir=a.out_dir,
        screenshot=a.screenshot,
        width=a.width,
        height=a.height,
        wait_ms=a.wait_ms,
        slug=a.slug,
    )
    summary = {k: v for k, v in res.items() if k != "dom_html"}
    summary["dom_chars"] = len(res.get("dom_html") or "")
    print(json.dumps(summary, indent=2))
    if res.get("blocked_by_gate"):
        raise SystemExit(f"blocked by gate: {res.get('reason')}")
    if not res.get("ok"):
        raise SystemExit(f"browse failed: {res.get('reason')}")


if __name__ == "__main__":
    main()
