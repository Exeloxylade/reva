#!/usr/bin/env python3
"""reva - Reverse Engineering Video Anything (Branch 2).

Study folders live in ./studies/<study>/ (or REVA_WORKSPACE / --root):
  study.json          source metadata, technique log, measurements, deliveries
  dossier.md          scannable reference breakdown (specs, pacing, colors, SFX, transcript)
  ref/                video, teardown.json, measure.json, sound.json, contact sheets, transcript
  <technique>/        theirs/ (strip + stills), notes.md, compare.jpg
  style/<id>/         <id>.style.json, <id>.md, test/beats.json + ref/*.jpg + beats-preview.jpg
  skill-export.md     proven Branch 1 skill specification with verification proof
"""
import argparse
import datetime
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(HERE, "scripts")
if S not in sys.path:
    sys.path.insert(0, S)

import _common as C
import style_kit


def run_py(script, *args, quiet=False):
    cmd = [sys.executable, os.path.join(S, script), *map(str, args)]
    r = C.run_cmd(cmd)
    if r.returncode != 0:
        raise SystemExit(f"FAIL {script}:\n{(r.stdout + r.stderr)[-1500:]}")
    if not quiet and r.stdout.strip():
        print(r.stdout.rstrip())
    return r.stdout


def sdir(root, study, *parts):
    return os.path.join(root, study, *parts)


def load_study(root, study):
    f = sdir(root, study, "study.json")
    if not os.path.exists(f):
        raise SystemExit(f"no study {study!r} (start one: reva scrape {study} <url-or-file>)")
    with open(f, encoding="utf-8") as fp:
        return json.load(fp)


def save_study(root, study, data):
    path = sdir(root, study, "study.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)
        fp.write("\n")


def ref_video(root, study):
    hits = [
        f for f in glob.glob(sdir(root, study, "ref", "ref.*"))
        if f.lower().endswith((".mp4", ".mkv", ".webm", ".mov"))
    ]
    if not hits:
        raise SystemExit("no reference video in ref/ - run reva start or reva scrape first")
    return hits[0]


def _refresh_dossier(root, study, data=None):
    st = data if data is not None else load_study(root, study)
    return style_kit.write_dossier(sdir(root, study), st)


def cmd_doctor(a, root):
    print("=== REVA DOCTOR ===")
    print(f"  python     OK    {sys.version.split()[0]} ({sys.executable})")
    missing_core = []

    for label, fn in (("ffmpeg", C.find_ffmpeg), ("ffprobe", C.find_ffprobe)):
        try:
            print(f"  {label:10} OK    {fn()}")
        except RuntimeError as exc:
            print(f"  {label:10} FAIL  {exc}")
            missing_core.append(label)

    for label, mod in (("yt-dlp", "yt_dlp"), ("numpy", "numpy"), ("Pillow", "PIL")):
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", None) or getattr(getattr(m, "version", None), "__version__", "installed")
            print(f"  {label:10} OK    {ver}")
        except Exception as exc:
            print(f"  {label:10} FAIL  {exc}")
            missing_core.append(label)

    node_bin = shutil.which("node")
    if node_bin:
        print(f"  node       OK    {node_bin}")
    else:
        print("  node       WARN  not found (needed only for 'reva deliver' style-check)")

    print(f"  workspace  OK    {root}" + (" (exists)" if os.path.isdir(root) else " (will be created on first study)"))
    app = C.find_app()
    if app:
        print(f"  app        OK    {app}")
    else:
        print("  app        WARN  Automated-Lunch-Free not auto-detected (set REVA_APP or pass --app)")

    if missing_core:
        raise SystemExit(f"doctor failed: missing {', '.join(missing_core)}")
    print("  status     OK    ready")


def cmd_start(a, root):
    ref_dir = sdir(root, a.study, "ref")
    os.makedirs(ref_dir, exist_ok=True)
    run_py("teardown.py", a.source, "--out", ref_dir, "--name", "ref", "--sps", a.sps)
    with open(os.path.join(ref_dir, "teardown.json"), encoding="utf-8") as fp:
        td = json.load(fp)
    prev = {}
    st_path = sdir(root, a.study, "study.json")
    if os.path.exists(st_path):
        with open(st_path, encoding="utf-8") as fp:
            prev = json.load(fp)
    st = {
        "study": a.study,
        "source": a.source,
        "title": td.get("title"),
        "duration": td["video"]["duration"],
        "aspect": td.get("aspect"),
        "aspect_ratio": td.get("aspect_ratio"),
        "lufs": td["sound"]["lufs"],
        "wpm": td["script"]["wpm"],
        "techniques": prev.get("techniques", {}),
        "deliveries": prev.get("deliveries", {}),
    }
    save_study(root, a.study, st)
    dossier = _refresh_dossier(root, a.study, st)
    print(f"\nstudy {a.study}:")
    print(f"  dossier  -> {dossier}")
    print(f"  sheets   -> {ref_dir}\\contact-sheet-*.jpg")
    print(f"  next     -> reva measure {a.study}  (or add a technique: reva add {a.study} <name> --from <s> --to <s>)")
    return st


def cmd_measure(a, root):
    st_path = sdir(root, a.study, "study.json")
    st = load_study(root, a.study) if os.path.exists(st_path) else None
    subs = a.subs or C.pick_subtitle_file(sdir(root, a.study, "ref"))
    out = sdir(root, a.study, "ref", "measure.json")
    fdir = sdir(root, a.study, "ref", "frames")
    args = [ref_video(root, a.study), "--out", out, "--scene", a.scene, "--max-samples", a.max_samples]
    if os.path.isdir(fdir):
        args += ["--frames-dir", fdir]
    if subs:
        args += ["--subs", subs]
    run_py("measure.py", *args)
    with open(out, encoding="utf-8") as fp:
        m = json.load(fp)
    if st is not None:
        st["measure"] = {"cuts": m["cuts"], "motion": m["motion"], "palette": m.get("palette"), "wpm": m.get("words", {}).get("wpm")}
        if m.get("words", {}).get("wpm"):
            st["wpm"] = m["words"]["wpm"]
        save_study(root, a.study, st)
        _refresh_dossier(root, a.study, st)
    print(f"next: reva scaffold {a.study} <style-id>  and  reva beats {a.study} <style-id> --auto")


def cmd_sound(a, root):
    mode = a.mode
    if mode == "analyze":
        if not a.files:
            raise SystemExit("pass audio files via --files a.wav b.wav for --mode analyze")
        run_py("sfx_lab.py", "analyze", *a.files)
        return

    if mode == "audition":
        if not a.files or not a.out:
            raise SystemExit("pass --files ... and --out <x.mp4> for --mode audition")
        args = ["audition", *a.files, "--out", a.out, "--voice-at", a.voice_at, "--gain", a.gain]
        if a.voice:
            args += ["--voice", a.voice]
        if a.gains:
            args += ["--gains", a.gains]
        run_py("sfx_lab.py", *args)
        return

    st = load_study(root, a.study)
    video = ref_video(root, a.study)
    dur = min(float(st.get("duration") or a.dur), float(a.dur)) if st.get("duration") else float(a.dur)
    if mode == "side":
        args = ["side", video, "--start", 0, "--dur", dur]
        args += ["--at", a.at] if a.at else ["--auto"]
        run_py("sfx_lab.py", *args)
        return

    out_json = sdir(root, a.study, "ref", "sound.json")
    run_py("sfx_lab.py", "events", video, "--start", 0, "--dur", dur, "--thr", a.thr, "--json", out_json)
    with open(out_json, encoding="utf-8") as fp:
        snd = json.load(fp)
    st["sound_events"] = {
        "stereo_separation": snd.get("stereo_separation"),
        "event_count": snd.get("event_count"),
        "events_per_min": snd.get("events_per_min"),
        "duration_sec": snd.get("duration_sec"),
    }
    save_study(root, a.study, st)
    _refresh_dossier(root, a.study, st)


def cmd_scrape(a, root):
    cmd_start(argparse.Namespace(study=a.study, source=a.source, sps=a.sps), root)
    cmd_measure(argparse.Namespace(study=a.study, subs=None, scene=0.15, max_samples=80), root)
    try:
        cmd_sound(argparse.Namespace(study=a.study, mode="events", at=None, dur=180.0, thr=7.0, files=None, out=None, voice=None, voice_at=40.0, gain=0.2, gains=None), root)
    except SystemExit as exc:
        print(f"  sound probe skipped: {exc}")

    st = load_study(root, a.study)
    dossier = _refresh_dossier(root, a.study, st)
    print(f"\n=== SCRAPE COMPLETE ({a.study}) ===")
    print(f"  dossier  -> {dossier}")
    if a.style:
        app = C.find_app(a.app)
        jpath, mpath = style_kit.scaffold_style(
            sdir(root, a.study), a.style, app_dir=app, framing=a.framing, refresh_metrics=True
        )
        bjson, bprev, beats = style_kit.build_beats(
            sdir(root, a.study), a.style, ref_video(root, a.study), auto=True, count=a.beats
        )
        print(f"  style    -> {jpath}")
        print(f"  twin md  -> {mpath}")
        print(f"  beats    -> {bjson} ({len(beats)} beats)")
        print(f"  preview  -> {bprev}")
        print(f"  next     -> inspect dossier + contact sheets + beats-preview.jpg, replace <TODO:...> fields in {os.path.basename(jpath)}, then: reva deliver {a.study}")
    else:
        print(f"  next     -> inspect {dossier}, then run 'reva scaffold {a.study} <style-id>' or 'reva add {a.study} <tech> --from <s> --to <s>'")


def cmd_add(a, root):
    st = load_study(root, a.study)
    d = sdir(root, a.study, a.technique, "theirs")
    os.makedirs(d, exist_ok=True)
    v = ref_video(root, a.study)

    strip_args = ["strip", v, "--from", a.from_, "--to", a.to, "--fps", a.fps, "--out", d]
    if a.keep_frames:
        strip_args.append("--keep-frames")
    run_py("technique.py", *strip_args)

    mid = [round(a.from_ + (a.to - a.from_) * k, 1) for k in (0.25, 0.6, 0.95)]
    run_py("technique.py", "stills", v, "--at", ",".join(map(str, mid)), "--out", d)
    st.setdefault("techniques", {})[a.technique] = {
        "from": a.from_, "to": a.to, "stills": mid, "status": "measuring",
    }
    save_study(root, a.study, st)

    td_path = sdir(root, a.study, "ref", "teardown.json")
    res = "1920x1080"
    if os.path.exists(td_path):
        with open(td_path, encoding="utf-8") as fp:
            vid = json.load(fp).get("video") or {}
        if vid.get("width") and vid.get("height"):
            res = f"{vid['width']}x{vid['height']}"

    notes = sdir(root, a.study, a.technique, "notes.md")
    if not os.path.exists(notes):
        with open(notes, "w", encoding="utf-8") as fp:
            fp.write(
                f"# {a.technique}\n\nReference {a.from_}-{a.to} s.\n\n"
                f"## Measured (px at {res}, seconds)\n"
                "- Background:\n- Title (font, size, colour, x/y):\n- Main element box:\n- Line / bar sizes:\n"
                "- Cards (size, border, tilt, label):\n- Notes / chips:\n- Entry order and times (from the strip):\n"
                "- Motion (ease, distance, duration):\n- Sound:\n\n## Gaps after compare\n- \n"
            )
    _refresh_dossier(root, a.study, st)
    print(f"next: inspect strip + stills in {d}, fill {notes}, rebuild, then reva compare {a.study} {a.technique} --mine <mp4> --mine-at ...")


def cmd_stills(a, root):
    load_study(root, a.study)
    run_py("technique.py", "stills", ref_video(root, a.study), "--at", a.at, "--out", sdir(root, a.study, a.technique, "theirs"))


def cmd_colors(a, root):
    load_study(root, a.study)
    if not a.technique:
        frames = sorted(glob.glob(sdir(root, a.study, "ref", "frames", "*.jpg")))
        if frames:
            step = max(1, len(frames) // 12)
            sample = frames[::step][:12]
            print(f"whole video ({len(sample)} frames):")
            run_py("technique.py", "palette", *sample, "--n", a.n)
            return
        with tempfile.TemporaryDirectory(prefix="reva_col_") as tmp:
            v = ref_video(root, a.study)
            dur = max(0.5, C.probe_media(v)["duration"])
            imgs = []
            for i in range(6):
                t = (i + 0.5) * dur / 6.0
                out = os.path.join(tmp, f"c{i}.jpg")
                C.run_cmd([C.find_ffmpeg(), "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", v, "-frames:v", "1", out])
                if os.path.exists(out):
                    imgs.append(out)
            run_py("technique.py", "palette", *imgs, "--n", a.n)
        return

    d = sdir(root, a.study, a.technique, "theirs")
    if a.at:
        run_py("technique.py", "stills", ref_video(root, a.study), "--at", a.at, "--out", d, quiet=True)
        img = os.path.join(d, f"full_{C.ts_token(a.at)}.png")
    else:
        imgs = sorted(glob.glob(os.path.join(d, "full_*.png")))
        if not imgs:
            raise SystemExit(f"no stills yet in {d} (run reva stills or pass --at)")
        img = imgs[len(imgs) // 2]
    print(os.path.basename(img))
    run_py("technique.py", "palette", img, "--n", a.n)


def cmd_compare(a, root):
    st = load_study(root, a.study)
    t = st.get("techniques", {}).get(a.technique)
    if not t:
        raise SystemExit(f"no technique {a.technique!r}")
    d = sdir(root, a.study, a.technique)
    theirs = os.path.join(d, "theirs")
    mine_count = len([x for x in a.mine_at.split(",") if x.strip()])
    if a.ref_at:
        ref_times = [C.norm_ts(x) for x in a.ref_at.split(",") if x.strip()]
    else:
        ref_times = [C.norm_ts(x) for x in t["stills"]][:mine_count]

    run_py("technique.py", "stills", ref_video(root, a.study), "--at", ",".join(ref_times), "--out", theirs, quiet=True)
    refs = ",".join(os.path.join(theirs, f"full_{C.ts_token(x)}.png") for x in ref_times)
    run_py("technique.py", "compare", "--ref", refs, "--mine", a.mine, "--mine-at", a.mine_at, "--out", d)
    t["status"] = "compared"
    t["mine"] = os.path.abspath(a.mine)
    save_study(root, a.study, st)
    _refresh_dossier(root, a.study, st)
    print(f"next: inspect {os.path.join(d, 'compare.jpg')}, log gaps in notes.md, fix & re-compare, then: reva verify {a.study} {a.technique}")


def cmd_verify(a, root):
    st = load_study(root, a.study)
    t = st.get("techniques", {}).get(a.technique)
    if not isinstance(t, dict):
        raise SystemExit(f"no technique {a.technique!r}")
    cmp_path = sdir(root, a.study, a.technique, "compare.jpg")
    if not os.path.exists(cmp_path) and not a.force:
        raise SystemExit(f"no compare.jpg at {cmp_path} — run 'reva compare' first (or pass --force)")
    t["status"] = "verified"
    t["verified_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    if a.note:
        t["verify_note"] = a.note
    save_study(root, a.study, st)
    _refresh_dossier(root, a.study, st)
    print(f"verified {a.study}/{a.technique}" + (f" ({a.note})" if a.note else ""))
    print(f"next: reva skill {a.study}")


def cmd_beats(a, root):
    load_study(root, a.study)
    times = [float(x.strip()) for x in a.at.split(",") if x.strip()] if a.at else None
    bjson, bprev, beats = style_kit.build_beats(
        sdir(root, a.study), a.style_id, ref_video(root, a.study),
        times=times, auto=a.auto or not times, count=a.count,
    )
    print(f"beats ({len(beats)}): {bjson}")
    print(f"preview:    {bprev}")


def cmd_scaffold(a, root):
    load_study(root, a.study)
    app = C.find_app(a.app)
    jpath, mpath = style_kit.scaffold_style(
        sdir(root, a.study), a.style_id, app_dir=app, name=a.name,
        framing=a.framing, refresh_metrics=a.refresh_metrics,
    )
    print(f"style json -> {jpath}")
    print(f"style md   -> {mpath}")


def cmd_deliver(a, root):
    st = load_study(root, a.study)
    app = C.find_app(a.app)
    if not app:
        raise SystemExit("Automated-Lunch-Free app folder not found (pass --app <folder> or set REVA_APP)")
    pattern = sdir(root, a.study, "style", a.style or "*", "*.style.json")
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"no style found matching {pattern} (run: reva scaffold {a.study} <style-id>)")

    for f in files:
        src = os.path.dirname(f)
        sid = os.path.basename(src)
        if os.path.basename(f) != f"{sid}.style.json":
            raise SystemExit(f"{f}: file must be named {sid}.style.json (folder name = style id)")
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
        placeholders = style_kit.find_placeholders(data)
        if placeholders and not a.allow_draft:
            sample = "\n".join(f"  - {p}: {v}" for p, v in placeholders[:10])
            raise SystemExit(
                f"{sid}.style.json still has {len(placeholders)} <...> template placeholder(s):\n{sample}\n"
                "Fill these in from your dossier/contact sheets first (or pass --allow-draft to bypass)."
            )

        dst = os.path.join(app, "styles", sid)
        shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.tmp", "__pycache__"))
        print(f"delivered {sid} -> {dst}")
        r = C.run_cmd(["node", os.path.join(app, "scripts", "style-check.js"), sid], cwd=app)
        if r.stdout.strip():
            print(r.stdout.rstrip())
        if r.stderr.strip():
            print(r.stderr.rstrip())

        st.setdefault("deliveries", {})[sid] = {
            "app": app,
            "status": "passed" if r.returncode == 0 else "failed",
            "delivered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        }
        save_study(root, a.study, st)
        if r.returncode != 0:
            raise SystemExit("style-check failed: fix every ERROR above, then deliver again")
        print(f"next: cd \"{app}\" && npm.cmd run style-test -- --style {sid} --preset cinematic-story   (pass = 6 of 8 beats)")
    _refresh_dossier(root, a.study, st)


def cmd_skill(a, root):
    st = load_study(root, a.study)
    out = style_kit.export_skill(sdir(root, a.study), st, out_path=a.out)
    print(f"skill export -> {out}")


def cmd_status(a, root):
    if not os.path.isdir(root):
        print(f"no studies yet in {root}")
        return
    names = [a.study] if a.study else sorted(os.listdir(root))
    shown = 0
    for s in names:
        f = sdir(root, s, "study.json")
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
        deliveries = st.get("deliveries") or {}
        for sid, d in deliveries.items():
            print(f"   [style:{d.get('status', '?'):6}] {sid:24} -> {d.get('app')}")
        if not techs and not deliveries:
            print(f"   next: reva scaffold {s} <style-id>  OR  reva add {s} <tech> --from <s> --to <s>")
    if not shown:
        print(f"no studies found in {root}")


def build_parser():
    ap = argparse.ArgumentParser(prog="reva", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="override workspace root (default: ./studies or REVA_WORKSPACE)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="check FFmpeg, Python modules, workspace, and Automated-Lunch-Free")

    s = sub.add_parser("scrape", help="1-command full style scrape: start + measure + sound + dossier (+ scaffold/beats)")
    s.add_argument("study")
    s.add_argument("source")
    s.add_argument("--style", help="also scaffold style/<id> and extract auto golden beats")
    s.add_argument("--sps", default="auto")
    s.add_argument("--beats", type=int, default=8)
    s.add_argument("--framing", choices=["flat", "film"])
    s.add_argument("--app")

    s = sub.add_parser("start", help="tear down reference video into ref/")
    s.add_argument("study")
    s.add_argument("source")
    s.add_argument("--sps", default="1.0")

    s = sub.add_parser("measure", help="measure cuts, motion, WPM, and palette into ref/measure.json")
    s.add_argument("study")
    s.add_argument("--subs")
    s.add_argument("--scene", type=float, default=0.15)
    s.add_argument("--max-samples", type=int, default=80)

    s = sub.add_parser("add", help="isolate one technique window (5 fps strip + 3 stills + notes.md)")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--from", dest="from_", type=float, required=True)
    s.add_argument("--to", type=float, required=True)
    s.add_argument("--fps", default="5")
    s.add_argument("--keep-frames", action="store_true")

    s = sub.add_parser("stills", help="grab extra full-size PNG stills for a technique")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--at", required=True)

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

    s = sub.add_parser("beats", help="extract N golden beat frames + narration into style/<id>/test/")
    s.add_argument("study")
    s.add_argument("style_id")
    s.add_argument("--at")
    s.add_argument("--auto", action="store_true")
    s.add_argument("--count", type=int, default=8)

    s = sub.add_parser("scaffold", help="generate or refresh <id>.style.json + <id>.md from measured study data")
    s.add_argument("study")
    s.add_argument("style_id")
    s.add_argument("--name")
    s.add_argument("--framing", choices=["flat", "film"])
    s.add_argument("--app")
    s.add_argument("--refresh-metrics", action="store_true")

    s = sub.add_parser("deliver", help="validate & copy style/<id>/ into Automated-Lunch-Free and run style-check")
    s.add_argument("study")
    s.add_argument("--style")
    s.add_argument("--app")
    s.add_argument("--allow-draft", action="store_true")

    s = sub.add_parser("skill", help="export a Branch 1 skill specification with verification proof")
    s.add_argument("study")
    s.add_argument("--out")

    s = sub.add_parser("status", help="show studies, techniques, and deliveries")
    s.add_argument("study", nargs="?")
    return ap


def main():
    ap = build_parser()
    a = ap.parse_args()
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
        "beats": cmd_beats,
        "scaffold": cmd_scaffold,
        "deliver": cmd_deliver,
        "skill": cmd_skill,
        "status": cmd_status,
    }
    handlers[a.cmd](a, root)


if __name__ == "__main__":
    main()
