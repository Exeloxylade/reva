#!/usr/bin/env python3
"""Engine Registry probing, test-bench setup, and capability recommendations for REVA Engineering Lab."""
import glob
import json
import importlib.util
import os
import re
import shutil

try:
    from . import _common as C
    from . import lab_library
    from . import research
except ImportError:
    import _common as C
    import lab_library
    import research


def _read_json(path):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8-sig") as fp:
            return json.load(fp)
    return None


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, ensure_ascii=False)
        fp.write("\n")


def engines_path(lab_root=None):
    """Return path to lab/engines.json."""
    return os.path.join(C.lab_dir(lab_root), "engines.json")


def load_engines(lab_root=None):
    """Load engine registry definitions."""
    data = _read_json(engines_path(lab_root))
    if not isinstance(data, dict):
        return {"schema": "reva-lab-engines", "version": 1, "engines": []}
    data.setdefault("schema", "reva-lab-engines")
    data.setdefault("version", 1)
    data.setdefault("engines", [])
    return data


def save_engines(data, lab_root=None):
    """Persist engines.json cleanly (UTF-8 without BOM)."""
    _write_json(engines_path(lab_root), data)


def resolve_harness_dir(rel_path, lab_root=None):
    """Resolve a starter harness path relative to lab root parent or REPO_ROOT."""
    if not rel_path:
        return None
    if os.path.isabs(rel_path) and os.path.isdir(rel_path):
        return rel_path
    lab_parent = os.path.dirname(C.lab_dir(lab_root))
    for base in (lab_parent, C.REPO_ROOT):
        cand = os.path.join(base, rel_path)
        if os.path.isdir(cand):
            return cand
    return None


def _check_npm_pkg(pkg):
    local_mod = os.path.join(C.REPO_ROOT, "node_modules", pkg)
    if os.path.isdir(local_mod):
        return True
    appdata = os.environ.get("APPDATA")
    if appdata and os.path.isdir(os.path.join(appdata, "npm", "node_modules", pkg)):
        return True
    return False


def probe_engine(eng, lab_root=None):
    """Probe live machine availability for one registered engine."""
    probes = eng.get("probes") or {}
    checks = []

    resolved_bins = []
    bin_names = probes.get("bin") or []
    win_globs = probes.get("win_globs") or []
    if bin_names or win_globs:
        for b in bin_names:
            hit = shutil.which(b)
            if not hit and b in ("ffmpeg", "ffprobe"):
                try:
                    hit = C.find_ffmpeg() if b == "ffmpeg" else C.find_ffprobe()
                except RuntimeError:
                    hit = None
            if hit and hit not in resolved_bins:
                resolved_bins.append(hit)
        for pat in win_globs:
            for hit in sorted(glob.glob(os.path.expandvars(pat))):
                if os.path.exists(hit) and hit not in resolved_bins:
                    resolved_bins.append(hit)
        checks.append(bool(resolved_bins))

    if probes.get("ffmpeg"):
        try:
            ff = C.find_ffmpeg()
            if ff not in resolved_bins:
                resolved_bins.append(ff)
            checks.append(True)
        except RuntimeError:
            checks.append(False)

    py_mod = probes.get("python_module")
    py_ok = None
    if py_mod:
        try:
            py_ok = importlib.util.find_spec(py_mod) is not None
        except (ModuleNotFoundError, ValueError):
            py_ok = False
        checks.append(py_ok)

    app_dir = None
    if probes.get("app_check") == "automated-lunch-free":
        app_dir = C.find_app()
        checks.append(bool(app_dir))

    npm_pkg = probes.get("npm_global_or_local")
    if npm_pkg:
        checks.append(_check_npm_pkg(npm_pkg))

    env_var = probes.get("env_var")
    if env_var:
        checks.append(bool(os.environ.get(env_var)))

    skill_names = probes.get("skill_names") or []
    resolved_skills = C.find_skill_dir(skill_names) if skill_names else {}
    if not checks and skill_names:
        checks.append(bool(resolved_skills))

    if checks and all(checks):
        status = "ready"
    elif checks and any(checks):
        status = "partial"
    else:
        status = "missing"

    h_dir = resolve_harness_dir(eng.get("harness"), lab_root=lab_root)
    return {
        "id": eng.get("id"),
        "name": eng.get("name"),
        "kind": eng.get("kind"),
        "status": status,
        "callable_via": eng.get("callable_via") or "",
        "resolved_bins": resolved_bins,
        "resolved_skills": resolved_skills,
        "app_dir": app_dir,
        "harness": eng.get("harness"),
        "harness_dir": h_dir,
        "harness_exists": bool(h_dir),
        "strengths": list(eng.get("strengths") or []),
        "limitations": list(eng.get("limitations") or []),
        "install_hint": eng.get("install_hint") or "",
    }


def probe_all(lab_root=None):
    """Probe every engine in lab/engines.json plus discovered Branch 1 roots."""
    reg = load_engines(lab_root)
    probed = [probe_engine(eng, lab_root=lab_root) for eng in reg.get("engines", [])]
    return {
        "lab_dir": C.lab_dir(lab_root),
        "branch1_roots": C.find_branch1_roots(),
        "engines": probed,
    }


def get_engine(engine_id, lab_root=None):
    """Look up raw engine definition by id."""
    target = (engine_id or "").strip().lower()
    for eng in load_engines(lab_root).get("engines", []):
        if (eng.get("id") or "").lower() == target:
            return eng
    return None


def register_engine(entry, lab_root=None):
    """Register a new engine (or update an existing one) in lab/engines.json."""
    eid = re.sub(r"[^a-zA-Z0-9_-]+", "-", (entry.get("id") or "").strip()).strip("-").lower()
    if not eid:
        raise ValueError("engine id must contain alphanumeric characters")
    name = (entry.get("name") or "").strip() or eid
    kind = (entry.get("kind") or "").strip() or "custom"
    strengths = [s.strip().lower() for s in (entry.get("strengths") or []) if s and s.strip()]
    if not strengths:
        raise ValueError("provide at least one strength tag for the engine")

    reg = load_engines(lab_root)
    engines = reg["engines"]
    existing = next((e for e in engines if (e.get("id") or "").lower() == eid), None)

    record = {
        "id": eid,
        "name": name,
        "kind": kind,
        "callable_via": entry.get("callable_via") or "",
        "probes": entry.get("probes") or {},
        "strengths": strengths,
        "limitations": list(entry.get("limitations") or []),
    }
    if entry.get("harness"):
        record["harness"] = entry["harness"]
    if entry.get("install_hint"):
        record["install_hint"] = entry["install_hint"]

    if existing is None:
        engines.append(record)
        save_engines(reg, lab_root)
        return record, True

    existing.update(record)
    save_engines(reg, lab_root)
    return existing, False


def _find_three_js():
    """Locate a local three.min.js build for offline headless Three.js benches."""
    home = os.path.expanduser("~")
    appdata = os.environ.get("APPDATA") or ""
    cands = [
        os.environ.get("REVA_THREE_JS"),
        os.path.join(C.REPO_ROOT, "lab", "harnesses", "threejs-webgl", "three.min.js"),
        os.path.join(home, ".kiro", "crew", "skills", "gem-3d-world", "lib", "three.min.js"),
        os.path.join(C.REPO_ROOT, "node_modules", "three", "build", "three.min.js"),
    ]
    if appdata:
        cands.append(os.path.join(appdata, "npm", "node_modules", "three", "build", "three.min.js"))
    cands.extend(sorted(glob.glob(os.path.join(home, ".kiro", "crew", "workspace", "videos", "*", "lib", "three.min.js"))))
    for c in cands:
        if c and os.path.exists(c):
            return os.path.abspath(c)
    return None


def _stage_kit_files(engine_id, bench_dir, lab_root=None):
    """Copy matching shared starter primitives from lab/kit/ into a bench directory."""
    kit_map = {
        "threejs-webgl": ("threejs_schematic.js",),
        "manim": ("manim_schematic.py",),
    }
    needed = kit_map.get(engine_id) or ()
    k_dir = lab_library.kit_dir(lab_root=lab_root)
    staged = []
    for fname in needed:
        src = os.path.join(k_dir, fname)
        dst = os.path.join(bench_dir, fname)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            staged.append(fname)
    return staged


def init_bench(study_dir, technique, engine_id, aspect=None, lab_root=None, from_pattern=None):
    """Initialize <study>/<technique>/bench/<engine_id>/ with shared kit, proven pattern code, or starter harness."""
    eng = get_engine(engine_id, lab_root=lab_root)
    if not eng:
        raise SystemExit(
            f"unknown engine {engine_id!r}. Run 'reva-lab engines' to list or 'reva-lab register' to add it."
        )
    probed = probe_engine(eng, lab_root=lab_root)

    bench_dir = os.path.join(study_dir, technique, "bench", eng["id"])
    os.makedirs(bench_dir, exist_ok=True)

    st = _read_json(os.path.join(study_dir, "study.json")) or {}
    t_info = (st.get("techniques") or {}).get(technique) or {}
    chosen_pat = from_pattern or t_info.get("reused_from") or ""

    kit_files = _stage_kit_files(eng["id"], bench_dir, lab_root=lab_root)

    reused_code = []
    bootstrapped_from = ""
    if chosen_pat:
        pat = lab_library.get_pattern(chosen_pat, lab_root=lab_root)
        if pat and pat.get("code_dir") and (pat.get("winning_engine") == eng["id"]):
            cdir_raw = pat["code_dir"]
            pat_dir = cdir_raw if os.path.isabs(cdir_raw) else os.path.join(C.lab_dir(lab_root), cdir_raw)
            if os.path.isdir(pat_dir):
                bootstrapped_from = pat["id"]
                for fname in sorted(os.listdir(pat_dir)):
                    if fname == "pattern.json":
                        continue
                    src = os.path.join(pat_dir, fname)
                    dst = os.path.join(bench_dir, fname)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        shutil.copy2(src, dst)
                        reused_code.append(fname)

    copied = list(kit_files) + list(reused_code)
    h_dir = probed.get("harness_dir")
    if h_dir and os.path.isdir(h_dir):
        for fname in sorted(os.listdir(h_dir)):
            src = os.path.join(h_dir, fname)
            dst = os.path.join(bench_dir, fname)
            if os.path.isfile(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
                copied.append(fname)

    three_dst = ""
    if eng["id"] == "threejs-webgl":
        three_target = os.path.join(bench_dir, "three.min.js")
        if os.path.exists(three_target):
            three_dst = three_target
        else:
            three_src = _find_three_js()
            if three_src:
                shutil.copy2(three_src, three_target)
                copied.append("three.min.js")
                three_dst = three_target

    td = _read_json(os.path.join(study_dir, "ref", "teardown.json")) or {}
    ms = _read_json(os.path.join(study_dir, "ref", "measure.json")) or {}
    meta = td.get("video") or {}

    chosen_aspect = aspect or td.get("aspect_ratio") or ms.get("aspect_ratio") or st.get("aspect_ratio") or "16:9"
    w = meta.get("width") or (1080 if chosen_aspect == "9:16" else 1920)
    h = meta.get("height") or (1920 if chosen_aspect == "9:16" else 1080)
    t_from = t_info.get("from", 0)
    t_to = t_info.get("to", 3)
    dur_sec = max(1.0, round(float(t_to) - float(t_from), 2)) if isinstance(t_from, (int, float)) and isinstance(t_to, (int, float)) else 3.0

    tech_dir = os.path.join(study_dir, technique)
    ck = research.seed_checklist(
        study_dir,
        tech_dir,
        technique_name=technique,
        start_sec=float(t_from) if isinstance(t_from, (int, float)) else None,
        end_sec=float(t_to) if isinstance(t_to, (int, float)) else None,
    )
    specs = research.collect_must_show(
        study_dir,
        technique_name=technique,
        start_sec=float(t_from) if isinstance(t_from, (int, float)) else None,
        end_sec=float(t_to) if isinstance(t_to, (int, float)) else None,
    )

    bench_cfg = {
        "study": st.get("study") or os.path.basename(os.path.abspath(study_dir)),
        "technique": technique,
        "engine_id": eng["id"],
        "engine_name": eng["name"],
        "status": probed["status"],
        "callable_via": eng.get("callable_via") or "",
        "aspect_ratio": chosen_aspect,
        "width": w,
        "height": h,
        "fps": meta.get("fps") or 30,
        "from_sec": t_from,
        "to_sec": t_to,
        "duration_sec": dur_sec,
        "palette": ms.get("palette") or {},
        "transcript_excerpt": research.transcript_window_excerpt(study_dir, float(t_from or 0), float(t_to or dur_sec)),
        "research_context": research.research_summary(study_dir),
        "anatomy_specs": specs,
        "render_mode": "schematic-clay-first",
        "kit_files": kit_files,
        "bootstrapped_from_pattern": bootstrapped_from,
        "reused_code_files": reused_code,
        "checklist_path": research.checklist_path(tech_dir),
        "checklist_items": len(ck.get("items") or []),
        "three_js": three_dst,
        "app_dir": probed.get("app_dir") or C.find_app(),
    }
    bench_json = os.path.join(bench_dir, "bench.json")
    _write_json(bench_json, bench_cfg)

    return {
        "bench_dir": bench_dir,
        "bench_json": bench_json,
        "copied_files": copied,
        "kit_files": kit_files,
        "bootstrapped_from_pattern": bootstrapped_from,
        "reused_code_files": reused_code,
        "probe": probed,
        "config": bench_cfg,
    }


def recommend_for_study(study_dir, tags=None, lab_root=None):
    """Recommend matching reusable patterns and candidate test-bench engines for a study."""
    st = _read_json(os.path.join(study_dir, "study.json")) or {}
    ms = _read_json(os.path.join(study_dir, "ref", "measure.json")) or {}
    td = _read_json(os.path.join(study_dir, "ref", "teardown.json")) or {}

    cuts = ms.get("cuts") or {}
    motion = ms.get("motion") or {}
    still_share = motion.get("still_share")
    moving_share = motion.get("moving_share")
    cuts_per_min = cuts.get("per_min") or 0
    aspect = td.get("aspect_ratio") or ms.get("aspect_ratio") or st.get("aspect_ratio")

    signals = []
    if tags:
        for t in (tags if isinstance(tags, (list, tuple)) else str(tags).split(",")):
            tok = t.strip().lower()
            if tok and tok not in signals:
                signals.append(tok)
    for tech_name in (st.get("techniques") or {}).keys():
        for tok in re.split(r"[^a-z0-9]+", tech_name.lower()):
            if len(tok) >= 2 and tok not in signals:
                signals.append(tok)

    r_sum = research.research_summary(study_dir)
    if r_sum:
        domain_terms = [r_sum.get("domain") or ""] + [c.get("term") or "" for c in (r_sum.get("concepts") or [])]
        added_research = 0
        for raw_term in domain_terms:
            for tok in re.split(r"[^a-z0-9-]+", str(raw_term).lower()):
                tok = tok.strip("-")
                if len(tok) >= 3 and tok not in signals:
                    signals.append(tok)
                    added_research += 1
                    if added_research >= 12:
                        break
            if added_research >= 12:
                break

    if still_share is not None:
        if still_share >= 0.60:
            signals.extend(["prompt-style", "illustration", "document-card"])
        elif moving_share is not None and moving_share >= 0.45 and cuts_per_min <= 3:
            signals.extend(["3d-explainer", "continuous-camera"])
    if cuts_per_min >= 10:
        signals.append("high-cut-pace")
    if aspect == "9:16":
        signals.append("shorts")

    # Deduplicate signals preserving order.
    dedup_signals = []
    for s in signals:
        if s not in dedup_signals:
            dedup_signals.append(s)

    patterns = lab_library.search_patterns(tags=dedup_signals, lab_root=lab_root)[:5] if dedup_signals else lab_library.search_patterns(lab_root=lab_root)[:5]

    inv = probe_all(lab_root=lab_root)
    sig_words = set()
    for s in dedup_signals:
        sig_words.add(s)
        for p in re.split(r"[^a-z0-9]+", s):
            if len(p) >= 2:
                sig_words.add(p)

    scored = []
    for eng in inv["engines"]:
        strengths = [s.lower() for s in eng["strengths"]]
        strength_words = set()
        for s in strengths:
            strength_words.add(s)
            for p in re.split(r"[^a-z0-9]+", s):
                if len(p) >= 2:
                    strength_words.add(p)

        score = 0
        reasons = []
        exact_hits = [s for s in strengths if s in sig_words]
        word_hits = sorted(strength_words & sig_words)
        if exact_hits:
            score += 6 * len(exact_hits)
            reasons.append("strength match: " + ", ".join(exact_hits[:3]))
        elif word_hits:
            score += 2 * len(word_hits)
            reasons.append("tag match: " + ", ".join(word_hits[:3]))

        eid = eng["id"]
        if still_share is not None:
            if still_share >= 0.60 and eid in ("automated-lunch-free", "hyperframes-2d", "ffmpeg-compositor"):
                score += 3
                reasons.append(f"fits {round(still_share * 100)}% still cadence")
            if moving_share is not None and moving_share >= 0.45 and cuts_per_min <= 3 and eid in ("threejs-webgl", "blender-bpy"):
                score += 3
                reasons.append("fits continuous motion")
        if cuts_per_min >= 10 and eid in ("automated-lunch-free", "ffmpeg-compositor"):
            score += 2
            reasons.append(f"fits {cuts_per_min}/min cut pace")
        if not dedup_signals and eng["status"] == "ready":
            score += 1

        # Boost if a top matching reusable pattern recommends this engine.
        for pat in patterns[:3]:
            if pat.get("winning_engine") == eid:
                score += 4
                reasons.append(f"won pattern '{pat['id']}'")
                break

        row = dict(eng)
        row["_score"] = score
        row["_reasons"] = reasons
        scored.append(row)

    scored.sort(key=lambda r: (-r["_score"], 0 if r["status"] == "ready" else 1, r["id"]))
    ready_candidates = [e for e in scored if e["status"] == "ready"][:4]
    upgrade_candidates = [e for e in scored if e["status"] != "ready" and e["_score"] > 0][:3]

    return {
        "study": st.get("study") or os.path.basename(os.path.abspath(study_dir)),
        "signals": dedup_signals,
        "matching_patterns": patterns,
        "ready_candidates": ready_candidates,
        "upgrade_candidates": upgrade_candidates,
    }
