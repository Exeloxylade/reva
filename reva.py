#!/usr/bin/env python3
"""reva - Branch 2 (Reverse Engineering Video Anything) in one command.

A study lives in workspace\\reva\\<study>\\ :
  study.json          source, notes, technique list
  ref\\                teardown: video, frames, contact sheets, script, teardown.json
  <technique>\\theirs\\ strips + stills of the reference
  <technique>\\        compare.jpg (reference left, yours right) + notes.md (measured numbers)

  reva start <study> <url-or-file>                 tear the reference apart, list contact sheets
  reva add <study> <technique> --from 35 --to 59   add a technique: strip at 5 fps + 3 stills
  reva stills <study> <technique> --at 44,56       more full-size stills to measure
  reva colors <study> <technique> [--at 44]        paper / ink / accent hex from a still
  reva sound <study> [--at 7.4,16.5]               transition sound numbers (default: scene changes)
  reva compare <study> <technique> --mine <mp4> --mine-at 12.5,25 [--ref-at 44,56]
  reva status [<study>]                            studies, techniques, what is measured / compared
  reva measure <study> [--subs <file>]             style-file numbers: cuts, picture length, still vs moving, wpm
  reva deliver <study> [--app <folder>]            copy <study>\\style\\<id>\\ into the app's styles\\ and check it
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "scripts")
ROOT = os.path.join(os.path.expanduser("~"), ".kiro", "crew", "workspace", "reva")
# The app that reads delivered styles (Automated Lunch Free); REVA_APP or --app overrides it.
APP = os.environ.get("REVA_APP") or r"C:\Users\Ahmad\OneDrive\Documents\A AGENTIC AI WORKS\Agentic AI\Automated Lunch Free"


def py(script, *args, quiet=False):
    r = subprocess.run([sys.executable, os.path.join(S, script), *map(str, args)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode:
        sys.exit(f"FAIL {script}:\n{(r.stdout + r.stderr)[-1500:]}")
    if not quiet:
        print(r.stdout.rstrip())
    return r.stdout


def sdir(study, *p):
    return os.path.join(ROOT, study, *p)


def load(study):
    f = sdir(study, "study.json")
    if not os.path.exists(f):
        sys.exit(f"no study {study!r} (start one: reva start {study} <url-or-file>)")
    return json.load(open(f, encoding="utf-8"))


def save(study, data):
    json.dump(data, open(sdir(study, "study.json"), "w", encoding="utf-8"), indent=2)


def ref_video(study):
    v = [f for f in glob.glob(sdir(study, "ref", "ref.*")) if f.lower().endswith((".mp4", ".mkv", ".webm", ".mov"))]
    if not v:
        sys.exit("no reference video in ref\\ - run reva start first")
    return v[0]


def cmd_start(a):
    os.makedirs(sdir(a.study, "ref"), exist_ok=True)
    py("teardown.py", a.source, "--out", sdir(a.study, "ref"), "--name", "ref", "--sps", 1)
    t = json.load(open(sdir(a.study, "ref", "teardown.json"), encoding="utf-8"))
    save(a.study, {"study": a.study, "source": a.source, "title": t.get("title"), "duration": t["video"]["duration"],
                   "lufs": t["sound"]["lufs"], "wpm": t["script"]["wpm"], "techniques": {}})
    print(f"\nstudy {a.study}: read the contact sheets in {sdir(a.study, 'ref')}, write down each scene type,")
    print(f"then: reva add {a.study} <technique-name> --from <s> --to <s>")


def cmd_add(a):
    st = load(a.study)
    d = sdir(a.study, a.technique, "theirs")
    os.makedirs(d, exist_ok=True)
    v = ref_video(a.study)
    py("technique.py", "strip", v, "--from", a.from_, "--to", a.to, "--fps", a.fps, "--out", d)
    mid = [round(a.from_ + (a.to - a.from_) * k, 1) for k in (0.25, 0.6, 0.95)]
    py("technique.py", "stills", v, "--at", ",".join(map(str, mid)), "--out", d)
    st["techniques"][a.technique] = {"from": a.from_, "to": a.to, "stills": mid, "status": "measuring"}
    save(a.study, st)
    notes = sdir(a.study, a.technique, "notes.md")
    if not os.path.exists(notes):
        open(notes, "w", encoding="utf-8").write(
            f"# {a.technique}\n\nReference {a.from_}-{a.to} s.\n\n## Measured (px at 1920x1080, seconds)\n"
            "- Background:\n- Title (font, size, colour, x/y):\n- Main element box:\n- Line / bar sizes:\n"
            "- Cards (size, border, tilt, label):\n- Notes / chips:\n- Entry order and times (from the strip):\n"
            "- Motion (ease, distance, duration):\n- Sound:\n\n## Gaps after compare\n- \n")
    print(f"next: open the strip + stills in {d}, fill {notes}, build yours, then reva compare")


def cmd_stills(a):
    load(a.study)
    py("technique.py", "stills", ref_video(a.study), "--at", a.at, "--out", sdir(a.study, a.technique, "theirs"))


def cmd_colors(a):
    load(a.study)
    d = sdir(a.study, a.technique, "theirs")
    if a.at:
        py("technique.py", "stills", ref_video(a.study), "--at", a.at, "--out", d, quiet=True)
        img = os.path.join(d, "full_%s.png" % a.at.replace(".", "_"))
    else:
        imgs = sorted(glob.glob(os.path.join(d, "full_*.png")))
        if not imgs:
            sys.exit("no stills yet")
        img = imgs[len(imgs) // 2]
    print(os.path.basename(img)); py("technique.py", "palette", img, "--n", 6)


def cmd_sound(a):
    st = load(a.study)
    args = [ref_video(a.study), "--start", 0, "--dur", min(st.get("duration", 180), a.dur)]
    args += ["--at", a.at] if a.at else ["--auto"]
    py("sfx_probe.py", *args)


def cmd_compare(a):
    st = load(a.study)
    t = st["techniques"].get(a.technique) or sys.exit(f"no technique {a.technique!r}")
    d = sdir(a.study, a.technique)
    ref_at = a.ref_at.split(",") if a.ref_at else [str(x) for x in t["stills"]][: len(a.mine_at.split(","))]
    py("technique.py", "stills", ref_video(a.study), "--at", ",".join(ref_at), "--out", os.path.join(d, "theirs"), quiet=True)
    refs = ",".join(os.path.join(d, "theirs", "full_%s.png" % x.replace(".", "_")) for x in ref_at)
    py("technique.py", "compare", "--ref", refs, "--mine", a.mine, "--mine-at", a.mine_at, "--out", d)
    t["status"] = "compared"; t["mine"] = a.mine; save(a.study, st)
    print("now look at it, list every difference in notes.md, fix, compare again; show the user when close")


def cmd_status(a):
    if not os.path.isdir(ROOT):
        return print("no studies yet")
    for s in ([a.study] if a.study else sorted(os.listdir(ROOT))):
        f = sdir(s, "study.json")
        if not os.path.exists(f):
            continue
        st = json.load(open(f, encoding="utf-8"))
        print(f"{s}: {st.get('title') or st['source']}  ({st.get('duration')} s, {st.get('wpm')} wpm, {st.get('lufs')} LUFS)")
        for k, t in st["techniques"].items():
            if isinstance(t, dict):
                print(f"   {t.get('status', 'unknown'):10} {k:24} {t.get('from', '?')}-{t.get('to', '?')} s")
            else:
                print(f"   {'note':10} {k:24} {t}")
        if not st["techniques"]:
            print("   no techniques yet: reva add", s, "<name> --from <s> --to <s>")


def subs_for(study):
    """The reference's own-language subtitles: the video's language, else an -orig track, else any."""
    ref = sdir(study, "ref")
    found = [f for f in glob.glob(os.path.join(ref, "ref*.vtt")) + glob.glob(os.path.join(ref, "ref*.srt"))]
    if not found:
        return None
    lang = ""
    for ij in glob.glob(os.path.join(ref, "*.info.json")):
        try:
            lang = (json.load(open(ij, encoding="utf-8")).get("language") or "").split("-")[0]
        except Exception:
            pass
    pick = [f for f in found if lang and re.search(rf"\.{re.escape(lang)}\.(vtt|srt)$", f)]
    pick = pick or [f for f in found if "-orig" in f] or found
    return pick[0]


def cmd_measure(a):
    st = load(a.study) if os.path.exists(sdir(a.study, "study.json")) else None
    subs = a.subs or subs_for(a.study)
    out = sdir(a.study, "ref", "measure.json")
    args = [ref_video(a.study), "--out", out] + (["--subs", subs] if subs else [])
    py("measure.py", *args)
    if st is not None:
        m = json.load(open(out, encoding="utf-8"))
        st["measure"] = {"cuts": m["cuts"], "motion": m["motion"], "wpm": m.get("words", {}).get("wpm")}
        if m.get("words", {}).get("wpm"):
            st["wpm"] = m["words"]["wpm"]
        save(a.study, st)
    print(f"\nput the 'style' numbers into {sdir(a.study, 'style', '<id>', '<id>.style.json')} (template: <app>\\docs\\reference-style.template.json),")
    print(f"then: reva deliver {a.study}")


def cmd_deliver(a):
    app = a.app or APP
    files = glob.glob(sdir(a.study, "style", "*", "*.style.json"))
    if not files:
        sys.exit(f"no style yet: write {sdir(a.study, 'style', '<id>', '<id>.style.json')} "
                 f"(template: {os.path.join(app, 'docs', 'reference-style.template.json')})")
    if not os.path.isdir(os.path.join(app, "styles")):
        sys.exit(f"no app at {app} (set REVA_APP or --app)")
    for f in files:
        src = os.path.dirname(f)
        sid = os.path.basename(src)
        if os.path.basename(f) != f"{sid}.style.json":
            sys.exit(f"{f}: the file must be named {sid}.style.json (folder name = style id)")
        dst = os.path.join(app, "styles", sid)
        # The style file, its .md twin, an optional references\ board, and test\ (golden beats: git ignores it).
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.tmp", "__pycache__"))
        print(f"delivered {sid} -> {dst}")
        r = subprocess.run(["node", os.path.join(app, "scripts", "style-check.js"), sid], cwd=app, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        print(r.stdout.rstrip())
        if r.returncode:
            sys.exit("style-check failed: fix every ERROR above, then deliver again")
        print(f"next: cd \"{app}\" && npm.cmd run style-test -- --style {sid} --preset cinematic-story   (pass = 6 of 8 beats)")


def main():
    ap = argparse.ArgumentParser(prog="reva", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("study"); s.add_argument("source")
    s = sub.add_parser("add"); s.add_argument("study"); s.add_argument("technique")
    s.add_argument("--from", dest="from_", type=float, required=True); s.add_argument("--to", type=float, required=True); s.add_argument("--fps", default="5")
    s = sub.add_parser("stills"); s.add_argument("study"); s.add_argument("technique"); s.add_argument("--at", required=True)
    s = sub.add_parser("colors"); s.add_argument("study"); s.add_argument("technique"); s.add_argument("--at")
    s = sub.add_parser("sound"); s.add_argument("study"); s.add_argument("--at"); s.add_argument("--dur", type=float, default=180)
    s = sub.add_parser("compare"); s.add_argument("study"); s.add_argument("technique"); s.add_argument("--mine", required=True)
    s.add_argument("--mine-at", required=True); s.add_argument("--ref-at")
    s = sub.add_parser("status"); s.add_argument("study", nargs="?")
    s = sub.add_parser("measure"); s.add_argument("study"); s.add_argument("--subs")
    s = sub.add_parser("deliver"); s.add_argument("study"); s.add_argument("--app")
    a = ap.parse_args()
    {"start": cmd_start, "add": cmd_add, "stills": cmd_stills, "colors": cmd_colors, "sound": cmd_sound,
     "compare": cmd_compare, "status": cmd_status, "measure": cmd_measure, "deliver": cmd_deliver}[a.cmd](a)


if __name__ == "__main__":
    main()
