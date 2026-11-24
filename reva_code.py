#!/usr/bin/env python3
"""reva-code - Pure Coding Video Reverse Engineering (Branch 1 / HyperFrames / Three.js / GSAP).

Isolate individual techniques, measure pixel layouts (--grid), timing (5 fps strips),
hex palettes, and stereo SFX, rebuild with your own content, verify side-by-side, and export
proven Branch 1 skill specifications.
"""
import argparse
import datetime
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "scripts")
if S not in sys.path:
    sys.path.insert(0, S)

import _common as C
import study_ops as O
import style_kit


def cmd_doctor(a, root):
    O.run_doctor(root, check_app=False, title="REVA CODE DOCTOR")


def cmd_start(a, root):
    st = O.run_start(root, a.study, a.source, sps=a.sps, focus="code")
    ref_dir = O.sdir(root, a.study, "ref")
    print(f"\nstudy {a.study} (code):")
    print(f"  dossier  -> {O.sdir(root, a.study, 'dossier.md')}")
    print(f"  sheets   -> {ref_dir}\\contact-sheet-*.jpg")
    print(f"  next     -> reva-code measure {a.study}  OR  reva-code add {a.study} <tech> --from <s> --to <s> --grid")
    return st


def cmd_measure(a, root):
    O.run_measure(root, a.study, subs=a.subs, scene=a.scene, max_samples=a.max_samples, focus="code")
    print(f"next: reva-code add {a.study} <technique> --from <s> --to <s> --grid")


def cmd_sound(a, root):
    mode = a.mode
    if mode == "analyze":
        if not a.files:
            raise SystemExit("pass audio files via --files a.wav b.wav for --mode analyze")
        O.run_py("sfx_lab.py", "analyze", *a.files)
        return

    if mode == "audition":
        if not a.files or not a.out:
            raise SystemExit("pass --files ... and --out <x.mp4> for --mode audition")
        args = ["audition", *a.files, "--out", a.out, "--voice-at", a.voice_at, "--gain", a.gain]
        if a.voice:
            args += ["--voice", a.voice]
        if a.gains:
            args += ["--gains", a.gains]
        O.run_py("sfx_lab.py", *args)
        return

    st = O.load_study(root, a.study)
    video = O.ref_video(root, a.study)
    dur = min(float(st.get("duration") or a.dur), float(a.dur)) if st.get("duration") else float(a.dur)
    if mode == "side":
        args = ["side", video, "--start", 0, "--dur", dur]
        args += ["--at", a.at] if a.at else ["--auto"]
        O.run_py("sfx_lab.py", *args)
        return

    out_json = O.sdir(root, a.study, "ref", "sound.json")
    O.run_py("sfx_lab.py", "events", video, "--start", 0, "--dur", dur, "--thr", a.thr, "--json", out_json)
    with open(out_json, encoding="utf-8") as fp:
        snd = json.load(fp)
    st["sound_events"] = {
        "stereo_separation": snd.get("stereo_separation"),
        "event_count": snd.get("event_count"),
        "events_per_min": snd.get("events_per_min"),
        "duration_sec": snd.get("duration_sec"),
    }
    O.save_study(root, a.study, st)
    O.refresh_dossier(root, a.study, st, focus="code")


def cmd_scrape(a, root):
    O.run_start(root, a.study, a.source, sps=a.sps, focus="code")
    O.run_measure(root, a.study, focus="code")
    try:
        cmd_sound(
            argparse.Namespace(
                study=a.study, mode="events", at=None, dur=180.0, thr=7.0,
                files=None, out=None, voice=None, voice_at=40.0, gain=0.2, gains=None,
            ),
            root,
        )
    except SystemExit as exc:
        print(f"  sound probe skipped: {exc}")

    st = O.load_study(root, a.study)
    dossier = O.refresh_dossier(root, a.study, st, focus="code")
    print(f"\n=== CODE SCRAPE COMPLETE ({a.study}) ===")
    print(f"  dossier  -> {dossier}")
    print(f"  sheets   -> {O.sdir(root, a.study, 'ref')}\\contact-sheet-*.jpg")
    print(f"  next     -> inspect dossier + contact sheets, then isolate 1 rig: reva-code add {a.study} <tech> --from <s> --to <s> --grid")


def cmd_add(a, root):
    st = O.load_study(root, a.study)
    d = O.sdir(root, a.study, a.technique, "theirs")
    os.makedirs(d, exist_ok=True)
    v = O.ref_video(root, a.study)

    strip_args = ["strip", v, "--from", a.from_, "--to", a.to, "--fps", a.fps, "--out", d]
    if a.keep_frames:
        strip_args.append("--keep-frames")
    O.run_py("technique.py", *strip_args)

    mid = [round(a.from_ + (a.to - a.from_) * k, 1) for k in (0.25, 0.6, 0.95)]
    still_args = ["stills", v, "--at", ",".join(map(str, mid)), "--out", d]
    if a.grid:
        still_args.append("--grid")
    O.run_py("technique.py", *still_args)

    st.setdefault("techniques", {})[a.technique] = {
        "from": a.from_, "to": a.to, "stills": mid, "status": "measuring",
    }
    O.save_study(root, a.study, st)

    td_path = O.sdir(root, a.study, "ref", "teardown.json")
    res = "1920x1080"
    if os.path.exists(td_path):
        with open(td_path, encoding="utf-8") as fp:
            vid = json.load(fp).get("video") or {}
        if vid.get("width") and vid.get("height"):
            res = f"{vid['width']}x{vid['height']}"

    notes = O.sdir(root, a.study, a.technique, "notes.md")
    if not os.path.exists(notes):
        with open(notes, "w", encoding="utf-8") as fp:
            fp.write(
                f"# {a.technique}\n\nReference {a.from_}-{a.to} s.\n\n"
                f"## Rendering Stack Hypothesis\n- Engine / libraries (Three.js, HyperFrames, GSAP, D3, shaders):\n\n"
                f"## Layout (px at {res})\n"
                "- Background / paper:\n- Main element / container box:\n- Cards / badges / borders:\n\n"
                f"## Typography & Colors\n- Fonts (family, weight, sizes):\n- Hex palette & accents:\n\n"
                f"## Entry Order, Timing & Easing (from 5 fps strip)\n- \n\n"
                f"## Camera & Explanatory Grammar (why it moves)\n- \n\n"
                f"## Sound & SFX\n- \n\n"
                f"## Gaps after compare\n- \n"
            )
    O.refresh_dossier(root, a.study, st, focus="code")
    print(f"next: inspect strip + stills in {d}, fill {notes}, rebuild in Branch 1, then reva-code compare {a.study} {a.technique} --mine <mp4> --mine-at ...")


def cmd_stills(a, root):
    O.load_study(root, a.study)
    args = ["stills", O.ref_video(root, a.study), "--at", a.at, "--out", O.sdir(root, a.study, a.technique, "theirs")]
    if a.grid:
        args.append("--grid")
    O.run_py("technique.py", *args)


def cmd_colors(a, root):
    if not a.technique:
        O.run_colors_whole(root, a.study, n=a.n)
        return
    O.load_study(root, a.study)
    d = O.sdir(root, a.study, a.technique, "theirs")
    if a.at:
        O.run_py("technique.py", "stills", O.ref_video(root, a.study), "--at", a.at, "--out", d, quiet=True)
        img = os.path.join(d, f"full_{C.ts_token(a.at)}.png")
    else:
        imgs = sorted(glob.glob(os.path.join(d, "full_*.png")))
        if not imgs:
            raise SystemExit(f"no stills yet in {d} (run reva-code stills or pass --at)")
        img = imgs[len(imgs) // 2]
    print(os.path.basename(img))
    O.run_py("technique.py", "palette", img, "--n", a.n)


def cmd_compare(a, root):
    st = O.load_study(root, a.study)
    t = st.get("techniques", {}).get(a.technique)
    if not t:
        raise SystemExit(f"no technique {a.technique!r}")
    d = O.sdir(root, a.study, a.technique)
    theirs = os.path.join(d, "theirs")
    mine_count = len([x for x in a.mine_at.split(",") if x.strip()])
    if a.ref_at:
        ref_times = [C.norm_ts(x) for x in a.ref_at.split(",") if x.strip()]
    else:
        ref_times = [C.norm_ts(x) for x in t["stills"]][:mine_count]

    O.run_py("technique.py", "stills", O.ref_video(root, a.study), "--at", ",".join(ref_times), "--out", theirs, quiet=True)
    refs = ",".join(os.path.join(theirs, f"full_{C.ts_token(x)}.png") for x in ref_times)
    O.run_py("technique.py", "compare", "--ref", refs, "--mine", a.mine, "--mine-at", a.mine_at, "--out", d)
    t["status"] = "compared"
    t["mine"] = os.path.abspath(a.mine)
    O.save_study(root, a.study, st)
    O.refresh_dossier(root, a.study, st, focus="code")
    print(f"next: inspect {os.path.join(d, 'compare.jpg')}, log gaps in notes.md, fix & re-compare, then: reva-code verify {a.study} {a.technique}")


def cmd_verify(a, root):
    st = O.load_study(root, a.study)
    t = st.get("techniques", {}).get(a.technique)
    if not isinstance(t, dict):
        raise SystemExit(f"no technique {a.technique!r}")
    cmp_path = O.sdir(root, a.study, a.technique, "compare.jpg")
    if not os.path.exists(cmp_path) and not a.force:
        raise SystemExit(f"no compare.jpg at {cmp_path} - run 'reva-code compare' first (or pass --force)")
    t["status"] = "verified"
    t["verified_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    if a.note:
        t["verify_note"] = a.note
    O.save_study(root, a.study, st)
    O.refresh_dossier(root, a.study, st, focus="code")
    print(f"verified {a.study}/{a.technique}" + (f" ({a.note})" if a.note else ""))
    print(f"next: reva-code skill {a.study}")


def cmd_skill(a, root):
    st = O.load_study(root, a.study)
    out = style_kit.export_skill(O.sdir(root, a.study), st, out_path=a.out)
    print(f"skill export -> {out}")


def cmd_status(a, root):
    if not os.path.isdir(root):
        print(f"no studies yet in {root}")
        return
    names = [a.study] if a.study else sorted(os.listdir(root))
    shown = 0
    for s in names:
        f = O.sdir(root, s, "study.json")
        if not os.path.exists(f):
            continue
        shown += 1
        with open(f, encoding="utf-8") as fp:
            st = json.load(fp)
        ms = st.get("measure") or {}
        cuts = ms.get("cuts") or {}
        motion = ms.get("motion") or {}
        snd = st.get("sound_events") or {}
        extra = []
        if cuts:
            extra.append(f"{cuts.get('per_min')}/min med {cuts.get('median_sec')}s")
        if motion.get("samples"):
            extra.append(f"{round(motion.get('still_share', 0) * 100)}% still")
        if snd.get("stereo_separation"):
            extra.append(f"SFX {snd.get('events_per_min')}/min")
        info_tail = ("  | " + ", ".join(extra)) if extra else ""
        print(f"{s}: {st.get('title') or st['source']}  ({st.get('duration')}s, {st.get('wpm')} wpm, {st.get('lufs')} LUFS{info_tail})")

        techs = st.get("techniques") or {}
        for k, t in techs.items():
            if isinstance(t, dict):
                print(f"   [{t.get('status', 'unknown'):9}] {k:24} {t.get('from', '?')}-{t.get('to', '?')} s")
            else:
                print(f"   [{'note':9}] {k:24} {t}")
        if not techs:
            print(f"   next: reva-code add {s} <technique> --from <s> --to <s> --grid")
    if not shown:
        print(f"no studies found in {root}")


def build_parser():
    ap = argparse.ArgumentParser(prog="reva-code", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="override workspace root (default: ./studies or REVA_WORKSPACE)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="check Python, FFmpeg, yt-dlp, numpy, Pillow, and workspace")

    s = sub.add_parser("scrape", help="teardown + measure + SFX events + dossier.md")
    s.add_argument("study")
    s.add_argument("source")
    s.add_argument("--sps", default="auto")

    s = sub.add_parser("start", help="tear down reference video into ref/")
    s.add_argument("study")
    s.add_argument("source")
    s.add_argument("--sps", default="1.0")

    s = sub.add_parser("measure", help="measure cuts, motion, WPM, and palette into ref/measure.json")
    s.add_argument("study")
    s.add_argument("--subs")
    s.add_argument("--scene", type=float, default=0.15)
    s.add_argument("--max-samples", type=int, default=80)

    s = sub.add_parser("add", help="isolate 1 technique window (5 fps strip + 3 stills + code notes.md)")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--from", dest="from_", type=float, required=True)
    s.add_argument("--to", type=float, required=True)
    s.add_argument("--fps", default="5")
    s.add_argument("--grid", action="store_true", help="also write grid_<t>.png pixel coordinate overlays")
    s.add_argument("--keep-frames", action="store_true")

    s = sub.add_parser("stills", help="grab extra full-size PNG stills (optional --grid pixel ruler)")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--at", required=True)
    s.add_argument("--grid", action="store_true")

    s = sub.add_parser("colors", help="extract main + accent hex colors (for a technique or whole video)")
    s.add_argument("study")
    s.add_argument("technique", nargs="?")
    s.add_argument("--at")
    s.add_argument("--n", type=int, default=6)

    s = sub.add_parser("sound", help="inspect SFX via sfx_lab.py (events, side, analyze, audition)")
    s.add_argument("study")
    s.add_argument("--mode", choices=["events", "side", "analyze", "audition"], default="events")
    s.add_argument("--at")
    s.add_argument("--dur", type=float, default=180.0)
    s.add_argument("--thr", type=float, default=7.0)
    s.add_argument("--files", nargs="+")
    s.add_argument("--out")
    s.add_argument("--voice")
    s.add_argument("--voice-at", type=float, default=40.0)
    s.add_argument("--gain", type=float, default=0.2)
    s.add_argument("--gains")

    s = sub.add_parser("compare", help="side-by-side reference vs rebuild -> compare.jpg")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--mine", required=True)
    s.add_argument("--mine-at", required=True)
    s.add_argument("--ref-at")

    s = sub.add_parser("verify", help="mark a compared technique as verified proof")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--note", default="")
    s.add_argument("--force", action="store_true")

    s = sub.add_parser("skill", help="export a proven Branch 1 skill brief (skill-export.md)")
    s.add_argument("study")
    s.add_argument("--out")

    s = sub.add_parser("status", help="show coding studies and verified technique status")
    s.add_argument("study", nargs="?")
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    root = C.workspace_root(a.root)
    handlers = {
        "doctor": cmd_doctor,
        "scrape": cmd_scrape,
        "start": cmd_start,
        "measure": cmd_measure,
        "add": cmd_add,
        "stills": cmd_stills,
        "colors": cmd_colors,
        "sound": cmd_sound,
        "compare": cmd_compare,
        "verify": cmd_verify,
        "skill": cmd_skill,
        "status": cmd_status,
    }
    handlers[a.cmd](a, root)


if __name__ == "__main__":
    main()
