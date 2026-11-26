#!/usr/bin/env python3
"""Cross-study Reusable Pattern Library for REVA Engineering Lab."""
import ast
import datetime
import json
import os
import re
import shutil

try:
    from . import _common as C
except ImportError:
    import _common as C

_CODE_EXTS = (".py", ".js", ".jsx", ".tsx", ".html", ".css")
_SKIP_DIRS = {"__pycache__", "_manim_media", "node_modules", ".git"}
_SKIP_SNAPSHOT_FILES = {"three.min.js", "threejs_schematic.js", "manim_schematic.py", "bench.json", "pattern.json", "out.mp4"}


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


def library_path(lab_root=None):
    """Return path to lab/library.json."""
    return os.path.join(C.lab_dir(lab_root), "library.json")


def patterns_dir(lab_root=None):
    """Return directory storing verified pattern code snapshots (<lab>/patterns/)."""
    return os.path.join(C.lab_dir(lab_root), "patterns")


def kit_dir(lab_root=None):
    """Return directory storing shared modular bench primitives (<lab>/kit/)."""
    d = os.path.join(C.lab_dir(lab_root), "kit")
    if os.path.isdir(d):
        return d
    repo_kit = os.path.join(C.REPO_ROOT, "lab", "kit")
    return repo_kit if os.path.isdir(repo_kit) else d


def analyze_code_structure(code_dir):
    """Extract source files, defined classes/functions, and imported/used libraries from a code directory."""
    if not code_dir or not os.path.isdir(code_dir):
        return {"files": [], "symbols": [], "libraries": [], "total_lines": 0}

    files = []
    symbols = []
    libraries = []
    total_lines = 0

    for name in sorted(os.listdir(code_dir)):
        if name in _SKIP_DIRS or name in ("pattern.json", "bench.json", "three.min.js"):
            continue
        p = os.path.join(code_dir, name)
        if not os.path.isfile(p):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext not in _CODE_EXTS and name != "README.md":
            continue
        files.append(name)
        if name == "README.md":
            continue
        try:
            with open(p, encoding="utf-8", errors="replace") as fp:
                src = fp.read()
        except OSError:
            continue
        total_lines += src.count("\n") + (1 if src else 0)

        if ext == ".py":
            try:
                tree = ast.parse(src, filename=name)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        args_txt = ", ".join(b.id for b in node.bases if isinstance(b, ast.Name))
                        symbols.append(f"class {node.name}({args_txt})" if args_txt else f"class {node.name}")
                    elif isinstance(node, ast.FunctionDef):
                        arg_names = [a.arg for a in node.args.args][:5]
                        symbols.append(f"def {node.name}({', '.join(arg_names)})")
                    elif isinstance(node, ast.Import):
                        for al in node.names:
                            libraries.append(al.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom) and node.module:
                        libraries.append(node.module.split(".")[0])
            except SyntaxError:
                pass
        else:
            for m in re.finditer(r"\bfunction\s+([A-Za-z_$][\w$]*)\s*\(([^)]*)\)", src):
                args_txt = ", ".join(x.strip().split("=")[0].strip() for x in m.group(2).split(",") if x.strip())
                symbols.append(f"function {m.group(1)}({args_txt})")
            for m in re.finditer(r"(?:export\s+)?const\s+([A-Za-z_$][\w$]*)\s*=\s*(?:\(([^)]*)\)|([A-Za-z_$][\w$]*))\s*=>", src):
                params = m.group(2) if m.group(2) is not None else m.group(3)
                symbols.append(f"const {m.group(1)}({params.strip()})")
            for m in re.finditer(r"<script[^>]+src=[\"']([^\"']+)[\"']", src, re.I):
                libraries.append(os.path.basename(m.group(1)))
            for m in re.finditer(r"import\s+.+?\s+from\s+[\"']([^\"']+)[\"']", src):
                libraries.append(m.group(1))
            if "RevaCAD." in src:
                libraries.append("RevaCAD")
            if "THREE." in src:
                libraries.append("three.js")

    return {
        "files": _dedupe_list(files),
        "symbols": _dedupe_list(symbols)[:30],
        "libraries": _dedupe_list(libraries)[:20],
        "total_lines": total_lines,
    }


def snapshot_bench_code(study_dir, technique, winner, pattern_id, lab_root=None, meta=None):
    """Copy verified bench source code into `<lab>/patterns/<pattern_id>/` and index structure."""
    bench_dir = os.path.join(study_dir, technique, "bench", winner)
    if not os.path.isdir(bench_dir):
        return None

    pid = re.sub(r"[^a-zA-Z0-9_-]+", "-", (pattern_id or "").strip()).strip("-").lower()
    if not pid:
        return None

    dst_dir = os.path.join(patterns_dir(lab_root), pid)
    os.makedirs(dst_dir, exist_ok=True)
    copied = []
    for fname in sorted(os.listdir(bench_dir)):
        if fname in _SKIP_SNAPSHOT_FILES or fname.startswith(("out_", "reva_")):
            continue
        src = os.path.join(bench_dir, fname)
        if not os.path.isfile(src):
            continue
        ext = os.path.splitext(fname)[1].lower()
        if ext not in _CODE_EXTS and fname != "README.md":
            continue
        shutil.copy2(src, os.path.join(dst_dir, fname))
        copied.append(fname)

    if not copied:
        return None

    struct = analyze_code_structure(dst_dir)
    manifest = {
        "schema": "reva-pattern-code",
        "version": 1,
        "id": pid,
        "winning_engine": winner,
        "source_study": os.path.basename(os.path.abspath(study_dir)),
        "source_technique": technique,
        "code_structure": struct,
    }
    if isinstance(meta, dict):
        manifest.update(meta)
    _write_json(os.path.join(dst_dir, "pattern.json"), manifest)
    rel_dir = f"patterns/{pid}"
    return {
        "code_dir": rel_dir,
        "code_files": struct["files"],
        "code_symbols": struct["symbols"],
        "code_libraries": struct["libraries"],
        "abs_dir": dst_dir,
    }


def load_library(lab_root=None):
    """Load the cross-study reusable pattern library."""
    p = library_path(lab_root)
    data = _read_json(p)
    if not isinstance(data, dict):
        return {"schema": "reva-lab-library", "version": 1, "patterns": []}
    data.setdefault("schema", "reva-lab-library")
    data.setdefault("version", 1)
    data.setdefault("patterns", [])
    return data


def save_library(data, lab_root=None):
    """Persist library.json cleanly (UTF-8 without BOM)."""
    _write_json(library_path(lab_root), data)


def _tokenize(raw):
    if not raw:
        return []
    if isinstance(raw, (list, tuple, set)):
        text = " ".join(str(x) for x in raw if x)
    else:
        text = str(raw)
    text = text.lower().strip()
    if not text:
        return []
    parts = [p for p in re.split(r"[\s,;/|]+", text) if p]
    sub = [p for p in re.split(r"[^a-z0-9]+", text) if len(p) >= 2]
    out = []
    for tok in parts + sub:
        if tok not in out:
            out.append(tok)
    return out


def _dedupe_list(items):
    out = []
    seen = set()
    for x in items or []:
        s = str(x).strip()
        if not s:
            continue
        k = s.lower()
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


def get_pattern(pattern_id, lab_root=None):
    """Fetch a single pattern by exact id (case-insensitive)."""
    target = (pattern_id or "").strip().lower()
    if not target:
        return None
    for pat in load_library(lab_root).get("patterns", []):
        if (pat.get("id") or "").lower() == target:
            return pat
    return None


def search_patterns(query=None, tags=None, category=None, engine=None, lab_root=None):
    """Search and rank proven patterns across past REVA studies (including extracted code symbols)."""
    patterns = load_library(lab_root).get("patterns", [])
    q_tokens = _tokenize(query)
    t_tokens = _tokenize(tags)
    all_tokens = _dedupe_list(q_tokens + t_tokens)
    cat_f = (category or "").strip().lower()
    eng_f = (engine or "").strip().lower()

    results = []
    for pat in patterns:
        p_cat = (pat.get("category") or "").lower()
        p_win = (pat.get("winning_engine") or "").lower()
        p_sec = [s.lower() for s in (pat.get("secondary_engines") or [])]
        if cat_f and p_cat != cat_f:
            continue
        if eng_f and eng_f != p_win and eng_f not in p_sec:
            continue

        if not all_tokens:
            item = dict(pat)
            item["_score"] = 1
            results.append(item)
            continue

        pid = (pat.get("id") or "").lower()
        p_tags = [t.lower() for t in (pat.get("tags") or [])]
        p_tag_words = _tokenize(p_tags)
        hay_text = " ".join([
            pid,
            p_cat,
            pat.get("summary") or "",
            pat.get("target_skill") or "",
            pat.get("template") or "",
            p_win,
            " ".join(pat.get("code_symbols") or []),
            " ".join(pat.get("code_libraries") or []),
            " ".join(pat.get("code_files") or []),
        ]).lower()

        score = 0
        for tok in all_tokens:
            if tok == pid:
                score += 10
            elif tok in pid:
                score += 4
            if tok == p_cat:
                score += 6
            if tok in p_tags:
                score += 5
            elif tok in p_tag_words:
                score += 2
            elif tok in hay_text:
                score += 2

        if score > 0:
            item = dict(pat)
            item["_score"] = score
            results.append(item)

    results.sort(key=lambda r: (-r["_score"], -len(r.get("used_in") or []), r.get("id") or ""))
    return results


def upsert_pattern(entry, lab_root=None):
    """Insert or update a reusable pattern in lab/library.json."""
    pid = re.sub(r"[^a-zA-Z0-9_-]+", "-", (entry.get("id") or "").strip()).strip("-").lower()
    if not pid:
        raise ValueError("pattern id must contain alphanumeric characters")

    lib = load_library(lab_root)
    patterns = lib["patterns"]
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    existing = None
    for p in patterns:
        if (p.get("id") or "").lower() == pid:
            existing = p
            break

    if existing is None:
        new_entry = {
            "id": pid,
            "category": entry.get("category") or "general",
            "tags": _dedupe_list(entry.get("tags") or []),
            "winning_engine": entry.get("winning_engine") or "unknown",
            "secondary_engines": _dedupe_list(entry.get("secondary_engines") or []),
            "rejected_engines": list(entry.get("rejected_engines") or []),
            "target_skill": entry.get("target_skill") or "",
            "template": entry.get("template") or "",
            "summary": entry.get("summary") or "",
            "code_dir": entry.get("code_dir") or "",
            "code_files": _dedupe_list(entry.get("code_files") or []),
            "code_symbols": _dedupe_list(entry.get("code_symbols") or []),
            "code_libraries": _dedupe_list(entry.get("code_libraries") or []),
            "baseline": entry.get("baseline") or {},
            "used_in": _dedupe_list(entry.get("used_in") or []),
            "updated_at": today,
        }
        patterns.append(new_entry)
        save_library(lib, lab_root)
        return new_entry, True

    if entry.get("category"):
        existing["category"] = entry["category"]
    if entry.get("tags"):
        existing["tags"] = _dedupe_list(list(existing.get("tags") or []) + list(entry["tags"]))
    if entry.get("winning_engine"):
        existing["winning_engine"] = entry["winning_engine"]
    if entry.get("secondary_engines"):
        existing["secondary_engines"] = _dedupe_list(
            list(existing.get("secondary_engines") or []) + list(entry["secondary_engines"])
        )
    if entry.get("rejected_engines"):
        prev_rej = list(existing.get("rejected_engines") or [])
        seen_rej = {json.dumps(x, sort_keys=True) if isinstance(x, dict) else str(x) for x in prev_rej}
        for r in entry["rejected_engines"]:
            sig = json.dumps(r, sort_keys=True) if isinstance(r, dict) else str(r)
            if sig not in seen_rej:
                seen_rej.add(sig)
                prev_rej.append(r)
        existing["rejected_engines"] = prev_rej
    for field in ("target_skill", "template", "summary", "code_dir"):
        if entry.get(field):
            existing[field] = entry[field]
    for list_field in ("code_files", "code_symbols", "code_libraries"):
        if entry.get(list_field):
            existing[list_field] = _dedupe_list(entry[list_field])
    if entry.get("baseline"):
        merged_base = dict(existing.get("baseline") or {})
        merged_base.update(entry["baseline"])
        existing["baseline"] = merged_base
    if entry.get("used_in"):
        existing["used_in"] = _dedupe_list(list(existing.get("used_in") or []) + list(entry["used_in"]))
    existing["updated_at"] = today
    save_library(lib, lab_root)
    return existing, False


def promote_technique(
    study_dir,
    study_data,
    technique,
    pattern_id=None,
    category=None,
    tags=None,
    target_skill=None,
    template=None,
    summary=None,
    force=False,
    lab_root=None,
):
    """Promote a verified coding technique + structured bench code snapshot into lab/library.json."""
    techs = study_data.get("techniques") or {}
    t = techs.get(technique)
    if not isinstance(t, dict):
        raise SystemExit(f"no technique {technique!r} in study")
    if t.get("status") != "verified" and not force:
        study_name = study_data.get("study") or os.path.basename(os.path.abspath(study_dir))
        raise SystemExit(
            f"technique {technique!r} is status {t.get('status')!r}; verify it first with "
            f"'reva-code verify {study_name} {technique}' (or pass --force)"
        )

    study_name = study_data.get("study") or os.path.basename(os.path.abspath(study_dir))
    pid = pattern_id or t.get("promoted_pattern") or t.get("reused_from") or technique
    trials = t.get("trials") or {}
    winner = t.get("winning_engine")
    if not winner and len(trials) == 1:
        winner = next(iter(trials.keys()))
    winner = winner or "hyperframes-2d"

    td = _read_json(os.path.join(study_dir, "ref", "teardown.json")) or {}
    ms = _read_json(os.path.join(study_dir, "ref", "measure.json")) or {}
    meta = td.get("video") or {}
    pal = ms.get("palette") or {}
    baseline = {
        "window_sec": f"{t.get('from', '?')}-{t.get('to', '?')}",
    }
    if td.get("aspect_ratio") or ms.get("aspect_ratio"):
        baseline["aspect_ratio"] = td.get("aspect_ratio") or ms.get("aspect_ratio")
    if meta.get("fps"):
        baseline["fps"] = meta["fps"]
    if study_data.get("wpm"):
        baseline["wpm"] = study_data["wpm"]
    if pal.get("main"):
        baseline["palette"] = [c["hex"] for c in pal["main"][:4]]
    if t.get("verify_note"):
        baseline["verify_note"] = t["verify_note"]

    notes_summary = summary
    if not notes_summary:
        notes_summary = f"Verified {technique} technique from {study_name} using {winner}"
        if t.get("verify_note"):
            notes_summary += f" ({t['verify_note']})"

    snap = snapshot_bench_code(
        study_dir, technique, winner, pid, lab_root=lab_root, meta={"audit": t.get("audit") or {}}
    )
    auto_tags = _dedupe_list(
        list(tags or [])
        + ([category] if category else [])
        + _tokenize(technique)
        + _tokenize(pid)
        + [winner]
        + (["structured-code"] if snap else [])
    )

    entry, created = upsert_pattern(
        {
            "id": pid,
            "category": category or (get_pattern(pid, lab_root=lab_root) or {}).get("category") or "technique",
            "tags": auto_tags,
            "winning_engine": winner,
            "rejected_engines": t.get("rejected_engines") or [],
            "target_skill": target_skill or "",
            "template": template or (snap["code_dir"] if snap else ""),
            "summary": notes_summary,
            "code_dir": snap["code_dir"] if snap else "",
            "code_files": snap["code_files"] if snap else [],
            "code_symbols": snap["code_symbols"] if snap else [],
            "code_libraries": snap["code_libraries"] if snap else [],
            "baseline": baseline,
            "used_in": [study_name],
        },
        lab_root=lab_root,
    )
    t["promoted_pattern"] = entry["id"]
    return entry, created


def promote_style(
    study_dir,
    study_data,
    style_json_path,
    pattern_id=None,
    tags=None,
    summary=None,
    lab_root=None,
):
    """Promote a completed prompt style from reva-style into lab/library.json."""
    style = _read_json(style_json_path)
    if not isinstance(style, dict):
        raise SystemExit(f"unable to read style JSON: {style_json_path}")
    sid = style.get("id") or os.path.basename(os.path.dirname(style_json_path))
    study_name = study_data.get("study") or os.path.basename(os.path.abspath(study_dir))
    D = style.get("direction") or {}
    L = style.get("look") or {}
    SM = D.get("scene_maker") or {}

    pid = pattern_id or f"prompt-style-{sid}"
    baseline = {
        "aspect_ratio": D.get("default_aspect") or study_data.get("aspect_ratio") or "?",
        "framing": L.get("framing") or "flat",
    }
    wpm = (D.get("narration") or {}).get("wpm", {}).get("value")
    if wpm:
        baseline["wpm"] = wpm
    avg_shot = SM.get("avg_shot_sec", {}).get("value")
    if avg_shot:
        baseline["avg_shot_sec"] = avg_shot

    auto_tags = _dedupe_list(
        ["prompt-style", "automated-lunch-free", L.get("framing") or "flat"]
        + list(tags or [])
        + _tokenize(sid)
    )
    desc = summary or D.get("purpose") or f"Prompt style {sid} delivered to Automated-Lunch-Free."

    entry, created = upsert_pattern(
        {
            "id": pid,
            "category": "prompt-style",
            "tags": auto_tags,
            "winning_engine": "automated-lunch-free",
            "target_skill": f"Automated-Lunch-Free/styles/{sid}",
            "template": f"styles/{sid}/{sid}.style.json",
            "summary": str(desc),
            "baseline": baseline,
            "used_in": [study_name],
        },
        lab_root=lab_root,
    )
    return entry, created


def sync_app_styles(app_dir=None, lab_root=None):
    """Scan Automated-Lunch-Free/styles/* and upsert validated reference styles into lab/library.json."""
    import glob
    import style_kit

    app = C.find_app(app_dir)
    if not app:
        raise SystemExit("Automated-Lunch-Free app folder not found (pass --app <folder> or set REVA_APP)")

    files = sorted(glob.glob(os.path.join(app, "styles", "*", "*.style.json")))
    synced = []
    skipped = []
    for sf in files:
        sid = os.path.basename(os.path.dirname(sf))
        if os.path.basename(sf) != f"{sid}.style.json":
            skipped.append({"id": sid, "reason": "filename mismatch"})
            continue
        chk = style_kit.check_style_local(sf, app_dir=app)
        if chk["bom"] or chk["placeholders"] or (chk["style_check_ran"] and not chk["style_check_ok"]):
            skipped.append({"id": sid, "reason": "failed style-check or unresolved placeholders"})
            continue

        style = _read_json(sf) or {}
        D = style.get("direction") or {}
        L = style.get("look") or {}
        if not isinstance(D, dict) or not D:
            skipped.append({"id": sid, "reason": "look-only style (no direction)"})
            continue
        SM = D.get("scene_maker") or {}
        framing = L.get("framing") or "flat"
        aspect = D.get("default_aspect") or "16:9"
        wpm = (D.get("narration") or {}).get("wpm", {}).get("value")
        avg_shot = SM.get("avg_shot_sec", {}).get("value")
        is_silent = (D.get("voice") == "off") or ((D.get("sound_design") or {}).get("voice") == "off")

        tags = ["prompt-style", "automated-lunch-free", framing, aspect]
        if is_silent:
            tags.extend(["asmr", "foley", "silent-voice"])
        if D.get("domain"):
            tags.append(str(D["domain"]))
        if D.get("story", {}).get("loop_ending"):
            tags.append("loop-ending")
        if L.get("overlay_layout"):
            tags.append("overlay-layout")
        tags.extend(_tokenize(sid))

        baseline = {"aspect_ratio": aspect, "framing": framing}
        if wpm:
            baseline["wpm"] = wpm
        if avg_shot:
            baseline["avg_shot_sec"] = avg_shot
        if is_silent:
            baseline["voice"] = "off"

        pid = f"prompt-style-{sid}"
        existing = get_pattern(pid, lab_root=lab_root)
        entry, created = upsert_pattern(
            {
                "id": pid,
                "category": "prompt-style",
                "tags": _dedupe_list(tags),
                "winning_engine": "automated-lunch-free",
                "target_skill": f"Automated-Lunch-Free/styles/{sid}",
                "template": f"styles/{sid}/{sid}.style.json",
                "summary": str(D.get("purpose") or style.get("name") or sid),
                "baseline": baseline,
                "used_in": (existing.get("used_in") if existing else None) or [f"alf:{sid}"],
            },
            lab_root=lab_root,
        )
        synced.append({"id": entry["id"], "created": created})

    return {"app_dir": app, "synced": synced, "skipped": skipped}
