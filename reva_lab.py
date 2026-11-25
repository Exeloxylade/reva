#!/usr/bin/env python3
"""reva-lab - REVA Engineering Lab (Engine Registry, Starter Harnesses, Recommendations & Reusable Pattern Library)."""
import argparse
import json
import os
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


def _split_csv(raw):
    if not raw:
        return []
    return [x.strip() for x in str(raw).split(",") if x.strip()]


def cmd_engines(a, root):
    inv = lab_engine.probe_all(lab_root=a.lab_dir)
    engines = inv["engines"]
    if a.kind:
        engines = [e for e in engines if (e.get("kind") or "").lower() == a.kind.lower()]
    if a.ready_only:
        engines = [e for e in engines if e["status"] == "ready"]

    if a.json:
        print(json.dumps({**inv, "engines": engines}, indent=2))
        return

    print("=== REVA ENGINEERING LAB: ENGINE REGISTRY ===")
    print(f"  lab dir      {inv['lab_dir']}")
    if inv["branch1_roots"]:
        print(f"  branch1      {', '.join(inv['branch1_roots'])}")
    else:
        print("  branch1      (none auto-detected; set REVA_BRANCH1 or clone sibling video-making-skills)")
    print("")
    for e in engines:
        tag = f"[{e['status'].upper():7}]"
        harness_note = " | harness:yes" if e["harness_exists"] else ""
        print(f"  {tag} {e['id']:22} ({e['kind']}) — {e['name']}{harness_note}")
        print(f"            strengths: {', '.join(e['strengths'])}")
        if e["resolved_skills"]:
            print(f"            skills:    {', '.join(sorted(e['resolved_skills'].keys()))}")
        if e["app_dir"]:
            print(f"            app:       {e['app_dir']}")
        if e["status"] != "ready" and e["install_hint"]:
            print(f"            install:   {e['install_hint']}")


def cmd_register(a, root):
    strengths = _split_csv(a.strengths)
    if not strengths:
        raise SystemExit("pass at least one strength via --strengths \"tag1,tag2\"")
    probes = {}
    if a.bin:
        probes["bin"] = _split_csv(a.bin)
    if a.python_module:
        probes["python_module"] = a.python_module
    if a.skill_names:
        probes["skill_names"] = _split_csv(a.skill_names)
    if a.env_var:
        probes["env_var"] = a.env_var

    entry = {
        "id": a.id,
        "name": a.name or a.id,
        "kind": a.kind,
        "callable_via": a.callable_via or "",
        "probes": probes,
        "strengths": strengths,
        "limitations": _split_csv(a.limitations) if a.limitations else [],
        "harness": a.harness or "",
        "install_hint": a.install_hint or "",
    }
    rec, created = lab_engine.register_engine(entry, lab_root=a.lab_dir)
    probed = lab_engine.probe_engine(rec, lab_root=a.lab_dir)
    verb = "registered" if created else "updated"
    print(f"{verb} engine '{rec['id']}' [{probed['status'].upper()}] -> {lab_engine.engines_path(a.lab_dir)}")


def cmd_harnesses(a, root):
    inv = lab_engine.probe_all(lab_root=a.lab_dir)
    print("=== REVA ENGINEERING LAB: STARTER HARNESSES ===")
    shown = 0
    for e in inv["engines"]:
        if not e.get("harness"):
            continue
        shown += 1
        state = "OK" if e["harness_exists"] else "MISSING"
        print(f"  {e['id']:22} [{e['status']:7}] {state:7} {e['harness']}")
        if e["harness_dir"]:
            files = sorted(f for f in os.listdir(e["harness_dir"]) if os.path.isfile(os.path.join(e["harness_dir"], f)))
            print(f"                         files: {', '.join(files)}")
    if not shown:
        print("  (no harnesses configured)")


def cmd_recommend(a, root):
    O.load_study(root, a.study)
    rec = lab_engine.recommend_for_study(O.sdir(root, a.study), tags=a.tags, lab_root=a.lab_dir)
    if a.json:
        print(json.dumps(rec, indent=2))
        return

    print(f"=== LAB RECOMMENDATIONS FOR '{rec['study']}' ===")
    print(f"  signals: {', '.join(rec['signals']) or '(none)'}")

    print("\n-- Matching Reusable Patterns (check before building from scratch) --")
    if rec["matching_patterns"]:
        for p in rec["matching_patterns"]:
            print(f"  * {p['id']:30} engine={p['winning_engine']} | skill={p.get('target_skill') or '-'} | used_in={','.join(p.get('used_in') or [])}")
            print(f"    {p.get('summary')}")
    else:
        print("  (no exact pattern matches yet)")

    print("\n-- Candidate Ready Engines for Test Bench --")
    for e in rec["ready_candidates"]:
        why = "; ".join(e["_reasons"]) if e["_reasons"] else "general ready engine"
        print(f"  + {e['id']:22} ({e['kind']}) — {why}")

    if rec["upgrade_candidates"]:
        print("\n-- Optional Upgrade Engines (not installed/ready) --")
        for e in rec["upgrade_candidates"]:
            hint = f" | install: {e['install_hint']}" if e.get("install_hint") else ""
            print(f"  ? {e['id']:22} [{e['status']}] — {'; '.join(e['_reasons'])}{hint}")


def cmd_library(a, root):
    if a.lib_cmd == "list":
        rows = lab_library.search_patterns(category=a.category, engine=a.engine, lab_root=a.lab_dir)
        print(f"=== REUSABLE PATTERN LIBRARY ({len(rows)}) ===")
        for p in rows:
            print(f"  * {p['id']:32} [{p['category']}] engine={p['winning_engine']} | used_in={len(p.get('used_in') or [])}")
            print(f"    {p.get('summary')}")
        return

    if a.lib_cmd == "search":
        rows = lab_library.search_patterns(
            query=a.query, tags=a.tags, category=a.category, engine=a.engine, lab_root=a.lab_dir
        )
        print(f"=== PATTERN SEARCH ({len(rows)} match(es)) ===")
        for p in rows:
            print(f"  * {p['id']:32} score={p['_score']} engine={p['winning_engine']} | target={p.get('target_skill') or '-'}")
            print(f"    {p.get('summary')}")
        return

    if a.lib_cmd == "show":
        pat = lab_library.get_pattern(a.pattern_id, lab_root=a.lab_dir)
        if not pat:
            raise SystemExit(f"pattern not found: {a.pattern_id!r}")
        print(json.dumps(pat, indent=2))


def cmd_promote(a, root):
    st = O.load_study(root, a.study)
    sdir = O.sdir(root, a.study)
    entry, created = lab_library.promote_technique(
        sdir,
        st,
        a.technique,
        pattern_id=a.pattern_id,
        category=a.category,
        tags=_split_csv(a.tags),
        target_skill=a.target_skill,
        template=a.template,
        summary=a.summary,
        force=a.force,
        lab_root=a.lab_dir,
    )
    O.save_study(root, a.study, st)
    O.refresh_dossier(root, a.study, st, focus="code")
    verb = "added" if created else "updated"
    print(f"{verb} pattern '{entry['id']}' in {lab_library.library_path(a.lab_dir)}")
    print(f"  winning_engine: {entry['winning_engine']} | used_in: {', '.join(entry['used_in'])}")


def cmd_promote_style(a, root):
    st = O.load_study(root, a.study)
    sdir = O.sdir(root, a.study)
    style_file = style_kit.resolve_style_file(sdir, a.style)
    chk = style_kit.check_style_local(style_file, app_dir=None)
    if chk["placeholders"]:
        raise SystemExit(f"{chk['style_id']}.style.json still has {len(chk['placeholders'])} unresolved placeholder(s)")
    entry, created = lab_library.promote_style(
        sdir,
        st,
        style_file,
        pattern_id=a.pattern_id,
        tags=_split_csv(a.tags),
        summary=a.summary,
        lab_root=a.lab_dir,
    )
    verb = "added" if created else "updated"
    print(f"{verb} style pattern '{entry['id']}' in {lab_library.library_path(a.lab_dir)}")


def build_parser():
    ap = argparse.ArgumentParser(prog="reva-lab", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", help="override workspace root (default: ./studies or REVA_WORKSPACE)")
    ap.add_argument("--lab-dir", help="override lab directory (default: ./lab or REVA_LAB_DIR)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("engines", help="probe all registered engines and Branch 1 skills on this machine")
    s.add_argument("--kind")
    s.add_argument("--ready-only", action="store_true")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("register", help="register or update an engine in lab/engines.json")
    s.add_argument("id")
    s.add_argument("--name")
    s.add_argument("--kind", default="custom")
    s.add_argument("--strengths", required=True, help="comma-separated capability tags")
    s.add_argument("--callable-via", default="")
    s.add_argument("--bin", help="comma-separated CLI executables to probe")
    s.add_argument("--python-module")
    s.add_argument("--skill-names", help="comma-separated Branch 1 skill folder names")
    s.add_argument("--env-var")
    s.add_argument("--limitations")
    s.add_argument("--harness")
    s.add_argument("--install-hint")

    sub.add_parser("harnesses", help="list starter test-bench harnesses in lab/harnesses/")

    s = sub.add_parser("recommend", help="recommend matching library patterns and candidate engines for a study")
    s.add_argument("study")
    s.add_argument("--tags", help="comma-separated technique/style tags (e.g. animated-map,route)")
    s.add_argument("--json", action="store_true")

    lib = sub.add_parser("library", help="browse, search, or inspect reusable cross-study patterns")
    lsub = lib.add_subparsers(dest="lib_cmd", required=True)
    ls = lsub.add_parser("list", help="list all patterns in lab/library.json")
    ls.add_argument("--category")
    ls.add_argument("--engine")
    ls = lsub.add_parser("search", help="search patterns by keyword or tags")
    ls.add_argument("query", nargs="?")
    ls.add_argument("--tags")
    ls.add_argument("--category")
    ls.add_argument("--engine")
    ls = lsub.add_parser("show", help="show full JSON for one pattern")
    ls.add_argument("pattern_id")

    s = sub.add_parser("promote", help="promote a verified coding technique into lab/library.json")
    s.add_argument("study")
    s.add_argument("technique")
    s.add_argument("--id", "--pattern-id", dest="pattern_id")
    s.add_argument("--category")
    s.add_argument("--tags")
    s.add_argument("--target-skill")
    s.add_argument("--template")
    s.add_argument("--summary")
    s.add_argument("--force", action="store_true")

    s = sub.add_parser("promote-style", help="promote a completed prompt style into lab/library.json")
    s.add_argument("study")
    s.add_argument("--style")
    s.add_argument("--id", "--pattern-id", dest="pattern_id")
    s.add_argument("--tags")
    s.add_argument("--summary")

    return ap


def main(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    root = C.workspace_root(a.root)
    handlers = {
        "engines": cmd_engines,
        "register": cmd_register,
        "harnesses": cmd_harnesses,
        "recommend": cmd_recommend,
        "library": cmd_library,
        "promote": cmd_promote,
        "promote-style": cmd_promote_style,
    }
    handlers[a.cmd](a, root)


if __name__ == "__main__":
    main()
