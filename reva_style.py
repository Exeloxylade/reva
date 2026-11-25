#!/usr/bin/env python3
"""reva-style - Prompt-Style Scraping & Cloning for Automated-Lunch-Free.

Measure a reference channel's pacing, still-vs-video ratio, WPM, and palette,
extract 8 aligned golden beats, scaffold <id>.style.json + <id>.md, dry-run check,
and deliver directly into Automated-Lunch-Free/styles/<id>/.
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
import lab_library
import study_ops as O
import style_kit


def _resolve_style_id(root, study, explicit=None):
    if explicit:
        return explicit
    hits = sorted(glob.glob(O.sdir(root, study, "style", "*", "*.style.json")))
    if len(hits) == 1:
        return os.path.basename(os.path.dirname(hits[0]))
    if len(hits) > 1:
        names = ", ".join(os.path.basename(os.path.dirname(h)) for h in hits)
        raise SystemExit(f"multiple styles in {study} ({names}); pass explicit style id")
    return study


def cmd_doctor(a, root):
    O.run_doctor(root, check_app=True, title="REVA STYLE DOCTOR")


def cmd_measure(a, root):
    O.run_measure(root, a.study, subs=a.subs, scene=a.scene, max_samples=a.max_samples, focus="style")
    print(f"next: reva-style scaffold {a.study} --refresh-metrics")


def cmd_colors(a, root):
    O.run_colors_whole(root, a.study, n=a.n)


def cmd_beats(a, root):
    O.load_study(root, a.study)
    sid = _resolve_style_id(root, a.study, a.style_id)
    times = [float(x.strip()) for x in a.at.split(",") if x.strip()] if a.at else None
    bjson, bprev, beats = style_kit.build_beats(
        O.sdir(root, a.study), sid, O.ref_video(root, a.study),
        times=times, auto=a.auto or not times, count=a.count,
    )
    O.refresh_dossier(root, a.study, focus="style")
    print(f"beats ({len(beats)}): {bjson}")
    print(f"preview:    {bprev}")


def cmd_scaffold(a, root):
    O.load_study(root, a.study)
    sid = a.style_id or a.study
    app = C.find_app(a.app)
    jpath, mpath = style_kit.scaffold_style(
        O.sdir(root, a.study), sid, app_dir=app, name=a.name,
        framing=a.framing, refresh_metrics=a.refresh_metrics,
    )
    O.refresh_dossier(root, a.study, focus="style")
    print(f"style json -> {jpath}")
    print(f"style md   -> {mpath}")


def cmd_scrape(a, root):
    O.run_start(root, a.study, a.source, sps=a.sps, focus="style")
    O.run_measure(root, a.study, focus="style")
    sid = a.style or a.study
    app = C.find_app(a.app)
    jpath, mpath = style_kit.scaffold_style(
        O.sdir(root, a.study), sid, app_dir=app, framing=a.framing, refresh_metrics=True,
    )
    bjson, bprev, beats = style_kit.build_beats(
        O.sdir(root, a.study), sid, O.ref_video(root, a.study), auto=True, count=a.beats,
    )
    dossier = O.refresh_dossier(root, a.study, focus="style")
    print(f"\n=== STYLE SCRAPE COMPLETE ({a.study} -> {sid}) ===")
    print(f"  dossier  -> {dossier}")
    print(f"  sheets   -> {O.sdir(root, a.study, 'ref')}\\contact-sheet-*.jpg")
    print(f"  style    -> {jpath}")
    print(f"  twin md  -> {mpath}")
    print(f"  beats    -> {bjson} ({len(beats)} beats)")
    print(f"  preview  -> {bprev}")
    print(f"  next     -> inspect dossier + contact sheets + beats-preview.jpg, replace <TODO:...> in {os.path.basename(jpath)}, then: reva-style check {a.study}")


def cmd_check(a, root):
    O.load_study(root, a.study)
    style_file = style_kit.resolve_style_file(O.sdir(root, a.study), a.style)
    app = C.find_app(a.app)
    res = style_kit.check_style_local(style_file, app_dir=app)

    print(f"=== STYLE CHECK ({res['style_id']}) ===")
    print(f"  file         {res['style_file']}")
    print(f"  utf8-no-bom  {'FAIL' if res['bom'] else 'OK'}")
    print(f"  placeholders {len(res['placeholders'])}" + (" (OK)" if not res["placeholders"] else " (unresolved):"))
    for p, v in res["placeholders"][:10]:
        print(f"    - {p}: {v}")
    if res["style_check_ran"]:
        print(f"  app check    {'OK' if res['style_check_ok'] else 'FAIL'} ({app})")
        if res["style_check_output"]:
            for ln in res["style_check_output"].splitlines():
                print(f"    {ln}")
    else:
        print("  app check    WARN  Automated-Lunch-Free or node not available (skipped JS schema check)")

    if res["bom"] or res["placeholders"] or (res["style_check_ran"] and not res["style_check_ok"]):
        raise SystemExit("style check failed: fix the items above, then run reva-style check again")
    print(f"  next         reva-style deliver {a.study}")


def cmd_deliver(a, root):
    st = O.load_study(root, a.study)
    app = C.find_app(a.app)
    if not app:
        raise SystemExit("Automated-Lunch-Free app folder not found (pass --app <folder> or set REVA_APP)")

    if a.style:
        files = [style_kit.resolve_style_file(O.sdir(root, a.study), a.style)]
    else:
        pattern = O.sdir(root, a.study, "style", "*", "*.style.json")
        files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"no style found in {O.sdir(root, a.study, 'style')} (run: reva-style scaffold {a.study})")

    for f in files:
        src = os.path.dirname(f)
        sid = os.path.basename(src)
        if os.path.basename(f) != f"{sid}.style.json":
            raise SystemExit(f"{f}: file must be named {sid}.style.json (folder name = style id)")
        with open(f, encoding="utf-8-sig") as fp:
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
        O.save_study(root, a.study, st)
        if r.returncode != 0:
            raise SystemExit("style-check failed: fix every ERROR above, then deliver again")
        if getattr(a, "promote", False):
            tags = [x.strip() for x in a.tags.split(",") if x.strip()] if getattr(a, "tags", None) else None
            entry, _ = lab_library.promote_style(
                O.sdir(root, a.study), st, f, pattern_id=getattr(a, "pattern_id", None), tags=tags
            )
            print(f"promoted -> pattern '{entry['id']}' in {lab_library.library_path()}")
        print(f"next: cd \"{app}\" && npm.cmd run style-test -- --style {sid} --preset cinematic-story   (pass = 6 of 8 beats)")
    O.refresh_dossier(root, a.study, st, focus="style")


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
        extra = [st.get("aspect_ratio") or "?"]
        if cuts:
            extra.append(f"{cuts.get('per_min')}/min med {cuts.get('median_sec')}s")
        if motion.get("samples"):
            extra.append(f"{round(motion.get('still_share', 0) * 100)}% still")
        print(f"{s}: {st.get('title') or st['source']}  ({st.get('duration')}s, {st.get('wpm')} wpm | {', '.join(extra)})")

        styles = sorted(glob.glob(O.sdir(root, s, "style", "*", "*.style.json")))
        deliveries = st.get("deliveries") or {}
        for sf in styles:
            sid = os.path.basename(os.path.dirname(sf))
            with open(sf, encoding="utf-8-sig") as fp:
                sdata = json.load(fp)
            ph = len(style_kit.find_placeholders(sdata))
            ph_txt = "ready" if ph == 0 else f"{ph} placeholders"
            deliv = deliveries.get(sid)
            d_txt = f"delivered:{deliv.get('status')}" if deliv else "not delivered"
            print(f"   [style] {sid:24} {ph_txt:18} {d_txt}")
        if not styles:
            print(f"   next: reva-style scaffold {s}")
    if not shown:
        print(f"no studies found in {root}")


def build_parser():
    ap = argparse.ArgumentParser(prog="reva-style", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="override workspace root (default: ./studies or REVA_WORKSPACE)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="check tools, node, workspace, and Automated-Lunch-Free")

    s = sub.add_parser("scrape", help="1-command style scrape: teardown + measure + dossier + scaffold + 8 golden beats")
    s.add_argument("study")
    s.add_argument("source")
    s.add_argument("--style", help="style id (defaults to <study>)")
    s.add_argument("--beats", type=int, default=8)
    s.add_argument("--framing", choices=["flat", "film"])
    s.add_argument("--sps", default="auto")
    s.add_argument("--app")

    s = sub.add_parser("measure", help="re-measure cuts, still vs moving ratio, WPM, and palette")
    s.add_argument("study")
    s.add_argument("--subs")
    s.add_argument("--scene", type=float, default=0.15)
    s.add_argument("--max-samples", type=int, default=80)

    s = sub.add_parser("colors", help="extract whole-video color palette")
    s.add_argument("study")
    s.add_argument("--n", type=int, default=6)

    s = sub.add_parser("beats", help="extract N golden beat frames + narration into style/<id>/test/")
    s.add_argument("study")
    s.add_argument("style_id", nargs="?")
    s.add_argument("--at")
    s.add_argument("--auto", action="store_true")
    s.add_argument("--count", type=int, default=8)

    s = sub.add_parser("scaffold", help="generate or refresh <id>.style.json + <id>.md")
    s.add_argument("study")
    s.add_argument("style_id", nargs="?")
    s.add_argument("--name")
    s.add_argument("--framing", choices=["flat", "film"])
    s.add_argument("--app")
    s.add_argument("--refresh-metrics", action="store_true")

    s = sub.add_parser("check", help="dry-run placeholder check + Automated-Lunch-Free style-check.js without copying")
    s.add_argument("study")
    s.add_argument("--style")
    s.add_argument("--app")

    s = sub.add_parser("deliver", help="validate & copy style/<id>/ into Automated-Lunch-Free and run style-check")
    s.add_argument("study")
    s.add_argument("--style")
    s.add_argument("--app")
    s.add_argument("--allow-draft", action="store_true")
    s.add_argument("--promote", action="store_true", help="promote delivered style into lab/library.json")
    s.add_argument("--id", "--pattern-id", dest="pattern_id")
    s.add_argument("--tags")

    s = sub.add_parser("status", help="show style studies, remaining placeholders, and delivery status")
    s.add_argument("study", nargs="?")
    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    root = C.workspace_root(a.root)
    handlers = {
        "doctor": cmd_doctor,
        "scrape": cmd_scrape,
        "measure": cmd_measure,
        "colors": cmd_colors,
        "beats": cmd_beats,
        "scaffold": cmd_scaffold,
        "check": cmd_check,
        "deliver": cmd_deliver,
        "status": cmd_status,
    }
    handlers[a.cmd](a, root)


if __name__ == "__main__":
    main()
