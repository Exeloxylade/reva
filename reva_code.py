#!/usr/bin/env python3
"""reva-code - Pure Coding Video Reverse Engineering (Branch 1 / HyperFrames / Three.js / GSAP).

Isolate individual techniques, measure pixel layouts (--grid), timing (5 fps strips),
hex palettes, and stereo SFX, run multi-tool test-bench bake-offs, verify side-by-side,
promote reusable patterns, and export proven Branch 1 skill specifications.
"""
import argparse
import datetime
import glob
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "scripts")
if S not in sys.path:
    sys.path.insert(0, S)

import _common as C
import lab_engine
import lab_library
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
    print(f"  next     -> inspect dossier + contact sheets, or run: reva-lab recommend {a.study}")


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

    prev_tech = st.get("techniques", {}).get(a.technique)
    tech_entry = prev_tech if isinstance(prev_tech, dict) else {}
    tech_entry.update({
        "from": a.from_,
        "to": a.to,
        "stills": mid,
        "status": tech_entry.get("status") or "measuring",
    })
    st.setdefault("techniques", {})[a.technique] = tech_entry
    O.save_study(root, a.study, st)

    td_path = O.sdir(root, a.study, "ref", "teardown.json")
    res = "1920x1080"
    if os.path.exists(td_path):
        with open(td_path, encoding="utf-8") as fp:
            vid = json.load(fp).get("video") or {}
        if vid.get("width") and vid.get("height"):
            res = f"{vid['width']}x{vid['height']}"

    matches = lab_library.search_patterns(query=a.technique)[:3]
    if matches:
        match_lines = [
            f"- `{m['id']}` (engine `{m['winning_engine']}`, skill `{m.get('target_skill') or '-'}`): {m.get('summary')}"
            for m in matches
        ]
    else:
        match_lines = ["- (no matching pattern yet — check `reva-lab library list`)"]

    notes = O.sdir(root, a.study, a.technique, "notes.md")
    if not os.path.exists(notes):
        with open(notes, "w", encoding="utf-8") as fp:
            fp.write(
                f"# {a.technique}\n\nReference {a.from_}-{a.to} s.\n\n"
                f"## Reusable Patterns Found\n" + "\n".join(match_lines) + "\n\n"
                f"## Rendering Stack Hypothesis\n- Candidate engines to bake off (`reva-code bench {a.study} {a.technique} --tool <engine>`):\n\n"
                f"## Layout (px at {res})\n"
                "- Background / paper:\n- Main element / container box:\n- Cards / badges / borders:\n\n"
                f"## Typography & Colors\n- Fonts (family, weight, sizes):\n- Hex palette & accents:\n\n"
                f"## Entry Order, Timing & Easing (from 5 fps strip)\n- \n\n"
                f"## Camera & Explanatory Grammar (why it moves)\n- \n\n"
                f"## Sound & SFX\n- \n\n"
                f"## Bench Trials & Bake-Off Verdict\n- \n\n"
                f"## Gaps after compare\n- \n"
            )
    O.refresh_dossier(root, a.study, st, focus="code")
    if matches:
        print("matching reusable patterns:")
        for m in matches:
            print(f"  * {m['id']} (engine={m['winning_engine']}, skill={m.get('target_skill') or '-'}) -> reva-code reuse {a.study} {a.technique} --pattern {m['id']}")
    print(f"next: inspect strip + stills in {d}, or init a test bench: reva-code bench {a.study} {a.technique} --tool <engine>")


def cmd_bench(a, root):
    st = O.load_study(root, a.study)
    sdir = O.sdir(root, a.study)
    res = lab_engine.init_bench(sdir, a.technique, a.tool, aspect=a.aspect)
    tech = st.setdefault("techniques", {}).setdefault(a.technique, {"status": "measuring"})
    if isinstance(tech, dict):
        tech.setdefault("benches", {})[res["probe"]["id"]] = res["bench_dir"]
        O.save_study(root, a.study, st)
    print(f"bench ready [{res['probe']['status'].upper()}] -> {res['bench_dir']}")
    if res["copied_files"]:
        print(f"  harness files: {', '.join(res['copied_files'])}")
    print(f"  config:        {res['bench_json']}")
    if res["probe"]["callable_via"]:
        print(f"  callable via:  {res['probe']['callable_via']}")
    print(f"  next:          render test clip, then run: reva-code compare {a.study} {a.technique} --tool {res['probe']['id']} --mine <mp4> --mine-at ...")


def cmd_reuse(a, root):
    st = O.load_study(root, a.study)
    pat = lab_library.get_pattern(a.pattern)
    if not pat:
        raise SystemExit(f"pattern not found: {a.pattern!r}. Run 'reva-lab library list' to inspect available patterns.")

    tech_dir = O.sdir(root, a.study, a.technique)
    os.makedirs(tech_dir, exist_ok=True)
    tech = st.setdefault("techniques", {}).setdefault(a.technique, {"status": "measuring"})
    if isinstance(tech, dict):
        tech["reused_from"] = pat["id"]
        O.save_study(root, a.study, st)

    notes = os.path.join(tech_dir, "notes.md")
    rej = pat.get("rejected_engines") or []
    rej_str = ", ".join(
        f"{r.get('engine')} ({r.get('reason')})" if isinstance(r, dict) else str(r) for r in rej
    ) or "none recorded"
    block = (
        f"\n## Reused Baseline (from `{pat['id']}`) & Delta Checklist\n"
        f"- **Winning engine:** `{pat['winning_engine']}`\n"
        f"- **Rejected engines to skip:** {rej_str}\n"
        f"- **Branch 1 target skill / template:** `{pat.get('target_skill') or '-'}` | `{pat.get('template') or '-'}`\n"
        f"- **Prior studies:** {', '.join(pat.get('used_in') or []) or 'none'}\n"
        f"- **Baseline metrics:** `{json.dumps(pat.get('baseline') or {})}`\n"
        f"- [ ] Compare Video 2 measurements against baseline (layout px, palette, timing, WPM)\n"
        f"- [ ] Adapt existing template/rig rather than rebuilding from scratch\n"
    )
    existing = ""
    if os.path.exists(notes):
        with open(notes, encoding="utf-8") as fp:
            existing = fp.read()
    if f"from `{pat['id']}`" not in existing:
        with open(notes, "a" if existing else "w", encoding="utf-8") as fp:
            if not existing:
                fp.write(f"# {a.technique}\n")
            fp.write(block)

    O.refresh_dossier(root, a.study, st, focus="code")
    print(f"linked {a.study}/{a.technique} -> reusable pattern '{pat['id']}' (engine: {pat['winning_engine']})")
    print(f"  updated notes -> {notes}")


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
    if not isinstance(t, dict):
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

    out_name = f"compare_{a.tool}.jpg" if a.tool else "compare.jpg"
    cmp_args = ["compare", "--ref", refs, "--mine", a.mine, "--mine-at", a.mine_at, "--out", d, "--out-name", out_name]
    if a.tool:
        cmp_args += ["--label", a.tool]
    O.run_py("technique.py", *cmp_args)

    if a.tool:
        shutil.copy2(os.path.join(d, out_name), os.path.join(d, "compare.jpg"))
        t.setdefault("trials", {})[a.tool] = {
            "mine": os.path.abspath(a.mine),
            "compare": out_name,
            "compared_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        }

    t["status"] = "compared"
    t["mine"] = os.path.abspath(a.mine)
    O.save_study(root, a.study, st)
    O.refresh_dossier(root, a.study, st, focus="code")
    print(f"next: inspect {os.path.join(d, out_name)}, record verdict or verify: reva-code verify {a.study} {a.technique}")


def _parse_rejected(raw):
    out = []
    if not raw:
        return out
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            eng, reason = part.split(":", 1)
            out.append({"engine": eng.strip(), "reason": reason.strip()})
        else:
            out.append({"engine": part, "reason": "did not match reference"})
    return out


def cmd_verdict(a, root):
    st = O.load_study(root, a.study)
    t = st.get("techniques", {}).get(a.technique)
    if not isinstance(t, dict):
        raise SystemExit(f"no technique {a.technique!r}")

    rejected = _parse_rejected(a.rejected)
    t["winning_engine"] = a.winner
    if rejected:
        t["rejected_engines"] = rejected
    if a.note:
        t["verdict_note"] = a.note
    O.save_study(root, a.study, st)

    notes = O.sdir(root, a.study, a.technique, "notes.md")
    os.makedirs(os.path.dirname(notes), exist_ok=True)
    lines = [
        f"\n## Bake-Off Verdict",
        f"- **Winning engine:** `{a.winner}`",
    ]
    if rejected:
        lines.append("- **Rejected engines:** " + ", ".join(f"`{r['engine']}` ({r['reason']})" for r in rejected))
    if a.note:
        lines.append(f"- **Verdict note:** {a.note}")
    with open(notes, "a" if os.path.exists(notes) else "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")

    O.refresh_dossier(root, a.study, st, focus="code")
    print(f"verdict saved for {a.study}/{a.technique}: winner={a.winner}")


def cmd_verify(a, root):
    st = O.load_study(root, a.study)
    t = st.get("techniques", {}).get(a.technique)
    if not isinstance(t, dict):
        raise SystemExit(f"no technique {a.technique!r}")
    cmp_path = O.sdir(root, a.study, a.technique, "compare.jpg")
    tool_cmp = O.sdir(root, a.study, a.technique, f"compare_{a.tool}.jpg") if a.tool else None
    if not os.path.exists(cmp_path) and not (tool_cmp and os.path.exists(tool_cmp)) and not a.force:
        raise SystemExit(f"no compare.jpg at {cmp_path} - run 'reva-code compare' first (or pass --force)")
    if a.tool:
        t["winning_engine"] = a.tool
    t["status"] = "verified"
    t["verified_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    if a.note:
        t["verify_note"] = a.note

    promoted = None
    if a.promote:
        tags = [x.strip() for x in a.tags.split(",") if x.strip()] if a.tags else None
        promoted, _ = lab_library.promote_technique(
            O.sdir(root, a.study),
            st,
            a.technique,
            pattern_id=a.pattern_id,
            category=a.category,
            tags=tags,
            target_skill=a.target_skill,
            template=a.template,
            summary=a.summary,
        )

    O.save_study(root, a.study, st)
    O.refresh_dossier(root, a.study, st, focus="code")
    print(f"verified {a.study}/{a.technique}" + (f" ({a.note})" if a.note else ""))
    if promoted:
        print(f"promoted -> pattern '{promoted['id']}' (used_in: {', '.join(promoted['used_in'])})")
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
                win = f" [{t['winning_engine']}]" if t.get("winning_engine") else ""
                print(f"   [{t.get('status', 'unknown'):9}] {k:24} {t.get('from', '?')}-{t.get('to', '?')} s{win}")
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

    s = sub.add_parser("bench", help="initialize a test-bench folder for one candidate engine")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--tool", required=True, help="engine id from reva-lab engines")
    s.add_argument("--aspect", choices=["16:9", "9:16", "1:1"])

    s = sub.add_parser("reuse", help="link a proven pattern from lab/library.json and write delta checklist")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--pattern", required=True, help="pattern id from reva-lab library")

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

    s = sub.add_parser("compare", help="side-by-side reference vs rebuild -> compare.jpg (or compare_<tool>.jpg)")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--mine", required=True)
    s.add_argument("--mine-at", required=True)
    s.add_argument("--ref-at")
    s.add_argument("--tool", help="candidate engine id for multi-tool bake-off comparison")

    s = sub.add_parser("verdict", help="record bake-off winning and rejected engines for a technique")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--winner", required=True)
    s.add_argument("--rejected", help="semicolon-separated 'engine:reason' entries")
    s.add_argument("--note", default="")

    s = sub.add_parser("verify", help="mark a compared technique as verified proof (optionally --promote)")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--tool", help="winning engine id if verifying a candidate trial")
    s.add_argument("--note", default="")
    s.add_argument("--force", action="store_true")
    s.add_argument("--promote", action="store_true", help="promote verified technique into lab/library.json")
    s.add_argument("--id", "--pattern-id", dest="pattern_id")
    s.add_argument("--category")
    s.add_argument("--tags")
    s.add_argument("--target-skill")
    s.add_argument("--template")
    s.add_argument("--summary")

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
        "bench": cmd_bench,
        "reuse": cmd_reuse,
        "stills": cmd_stills,
        "colors": cmd_colors,
        "sound": cmd_sound,
        "compare": cmd_compare,
        "verdict": cmd_verdict,
        "verify": cmd_verify,
        "skill": cmd_skill,
        "status": cmd_status,
    }
    handlers[a.cmd](a, root)


if __name__ == "__main__":
    main()
