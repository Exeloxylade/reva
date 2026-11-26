#!/usr/bin/env python3
"""reva - Unified dispatcher for REVA (Reverse Engineering Video Anything).

Three specialized tools share one measurement engine and Engineering Lab:
  reva lab <cmd> ...      (or reva_lab.py / reva-lab.cmd)     Engine registry, test bench & reusable library
  reva code <cmd> ...     (or reva_code.py / reva-code.cmd)   Pure coding skills -> Branch 1
  reva style <cmd> ...    (or reva_style.py / reva-style.cmd) Prompt-style cloning -> Automated-Lunch-Free

Direct top-level shortcuts also work:
  Lab:     engines, register, harnesses, recommend, library, promote, promote-style, sync-app
  Coding:  start, add, bench, reuse, stills, colors, sound, compare, verdict, verify, skill
  Style:   beats, scaffold, check, deliver
  Shared:  doctor, scrape, measure, status
"""
import argparse
import sys

import reva_code
import reva_lab
import reva_style

_LAB_CMDS = {"engines", "register", "harnesses", "recommend", "library", "promote", "promote-style", "sync-app"}
_STYLE_CMDS = {"doctor", "beats", "scaffold", "check", "deliver"}
_CODE_CMDS = {"start", "measure", "add", "bench", "reuse", "stills", "colors", "sound", "compare", "verdict", "verify", "skill", "status"}
_STYLE_SCRAPE_FLAGS = ("--style", "--beats", "--framing", "--app")


def _split_global_flags(argv):
    root_args = []
    lab_args = []
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
        elif tok == "--lab-dir" and i + 1 < len(argv):
            lab_args = ["--lab-dir", argv[i + 1]]
            i += 2
        elif tok.startswith("--lab-dir="):
            lab_args = [tok]
            i += 1
        else:
            rest.append(tok)
            i += 1
    return root_args, lab_args, rest


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    root_args, lab_args, rest = _split_global_flags(args)

    if not rest or rest[0] in ("-h", "--help"):
        ap = argparse.ArgumentParser(prog="reva", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("--root", help="override workspace root (default: ./studies or REVA_WORKSPACE)")
        ap.add_argument("--lab-dir", help="override lab directory (default: ./lab or REVA_LAB_DIR)")
        ap.add_argument("target", nargs="?", help="lab | code | style | <subcommand>")
        ap.print_help()
        return

    cmd = rest[0]
    if cmd == "lab":
        return reva_lab.main(root_args + lab_args + rest[1:])
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
    if cmd in _LAB_CMDS:
        return reva_lab.main(root_args + lab_args + rest)
    if cmd in _STYLE_CMDS:
        return reva_style.main(root_args + rest)
    if cmd in _CODE_CMDS:
        return reva_code.main(root_args + rest)

    raise SystemExit(
        f"unknown command {cmd!r}. Run 'reva lab --help', 'reva code --help', 'reva style --help', or 'reva --help'."
    )


if __name__ == "__main__":
    main()
