#!/usr/bin/env python3
"""reva - Unified dispatcher for REVA (Reverse Engineering Video Anything).

Two dedicated tools share one measurement engine:
  reva code <cmd> ...     (or reva_code.py / reva-code.cmd)   Pure coding skills -> Branch 1
  reva style <cmd> ...    (or reva_style.py / reva-style.cmd) Prompt-style cloning -> Automated-Lunch-Free

Direct top-level shortcuts also work:
  Coding:  start, add, stills, colors, sound, compare, verify, skill
  Style:   beats, scaffold, check, deliver
  Shared:  doctor, scrape, measure, status
"""
import argparse
import sys

import reva_code
import reva_style

_STYLE_CMDS = {"doctor", "beats", "scaffold", "check", "deliver"}
_CODE_CMDS = {"start", "measure", "add", "stills", "colors", "sound", "compare", "verify", "skill", "status"}
_STYLE_SCRAPE_FLAGS = ("--style", "--beats", "--framing", "--app")


def _split_root(argv):
    root_args = []
    rest = []
    i = 0
    while i < len(argv):
        tok = argv[i]
        if tok == "--root" and i + 1 < len(argv):
            root_args = ["--root", argv[i + 1]]
            i += 2
        elif tok.startswith("--root="):
            root_args = [tok]
            i += 1
        else:
            rest.append(tok)
            i += 1
    return root_args, rest


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    root_args, rest = _split_root(args)

    if not rest or rest[0] in ("-h", "--help"):
        ap = argparse.ArgumentParser(prog="reva", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("--root", help="override workspace root (default: ./studies or REVA_WORKSPACE)")
        ap.add_argument("target", nargs="?", help="code | style | <subcommand>")
        ap.print_help()
        return

    cmd = rest[0]
    if cmd == "code":
        return reva_code.main(root_args + rest[1:])
    if cmd == "style":
        return reva_style.main(root_args + rest[1:])
    if cmd == "scrape":
        has_style_flag = any(
            t == f or t.startswith(f + "=")
            for t in rest[1:]
            for f in _STYLE_SCRAPE_FLAGS
        )
        target = reva_style if has_style_flag else reva_code
        return target.main(root_args + rest)
    if cmd in _STYLE_CMDS:
        return reva_style.main(root_args + rest)
    if cmd in _CODE_CMDS:
        return reva_code.main(root_args + rest)

    raise SystemExit(
        f"unknown command {cmd!r}. Run 'reva code --help', 'reva style --help', or 'reva --help'."
    )


if __name__ == "__main__":
    main()
