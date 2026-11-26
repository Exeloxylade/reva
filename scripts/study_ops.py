#!/usr/bin/env python3
"""Shared study orchestration helpers used by reva_code.py and reva_style.py."""
import glob
import json
import os
import shutil
import sys
import tempfile

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

try:
    from . import _common as C
    from . import research
    from . import style_kit
    from . import transcribe
except ImportError:
    import _common as C
    import research
    import style_kit
    import transcribe


def run_py(script, *args, quiet=False):
    cmd = [sys.executable, os.path.join(SCRIPTS_DIR, script), *map(str, args)]
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
        raise SystemExit(f"no study {study!r} (start one with scrape or start)")
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
        raise SystemExit("no reference video in ref/ - run scrape or start first")
    return hits[0]


def refresh_dossier(root, study, data=None, focus="all"):
    st = data if data is not None else load_study(root, study)
    return style_kit.write_dossier(sdir(root, study), st, focus=focus)


def run_doctor(root, check_app=True, title="REVA DOCTOR"):
    print(f"=== {title} ===")
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

    if check_app:
        node_bin = shutil.which("node")
        if node_bin:
            print(f"  node       OK    {node_bin}")
        else:
            print("  node       WARN  not found (needed for style-check)")

    print(f"  workspace  OK    {root}" + (" (exists)" if os.path.isdir(root) else " (will be created on first study)"))
    stt_ready = transcribe.ready_backend_names()
    print(f"  transcribe OK    {', '.join(stt_ready)}")

    if check_app:
        app = C.find_app()
        if app:
            print(f"  app        OK    {app}")
        else:
            print("  app        WARN  Automated-Lunch-Free not auto-detected (set REVA_APP or pass --app)")

    if missing_core:
        raise SystemExit(f"doctor failed: missing {', '.join(missing_core)}")
    print("  status     OK    ready")


def run_start(root, study, source, sps="1.0", focus="all"):
    ref_dir = sdir(root, study, "ref")
    os.makedirs(ref_dir, exist_ok=True)
    run_py("teardown.py", source, "--out", ref_dir, "--name", "ref", "--sps", sps)
    with open(os.path.join(ref_dir, "teardown.json"), encoding="utf-8") as fp:
        td = json.load(fp)
    prev = {}
    st_path = sdir(root, study, "study.json")
    if os.path.exists(st_path):
        with open(st_path, encoding="utf-8") as fp:
            prev = json.load(fp)
    t_status = "subtitles" if td["script"].get("has_script") else ("needed" if td["video"].get("has_audio") else "no-audio")
    st = {
        "study": study,
        "source": source,
        "title": td.get("title"),
        "duration": td["video"]["duration"],
        "aspect": td.get("aspect"),
        "aspect_ratio": td.get("aspect_ratio"),
        "lufs": td["sound"]["lufs"],
        "wpm": td["script"]["wpm"],
        "transcript_status": t_status,
        "transcript_source": td["script"].get("subtitle_file") or ("audio.mp3" if td["video"].get("has_audio") else ""),
        "techniques": prev.get("techniques", {}),
        "deliveries": prev.get("deliveries", {}),
    }
    save_study(root, study, st)
    brief = research.init_brief(sdir(root, study))
    st["research"] = {
        "status": brief.get("status", "draft"),
        "domain": (brief.get("subject") or {}).get("domain") or "",
        "what_is_it": (brief.get("subject") or {}).get("what_is_it") or "",
        "concepts_count": len(brief.get("concepts") or []),
        "sources_count": len(brief.get("sources") or []),
    }
    save_study(root, study, st)
    refresh_dossier(root, study, st, focus=focus)
    return st


def run_measure(root, study, subs=None, scene=0.15, max_samples=80, focus="all"):
    st_path = sdir(root, study, "study.json")
    st = load_study(root, study) if os.path.exists(st_path) else None
    sub_file = subs or C.pick_subtitle_file(sdir(root, study, "ref"))
    out = sdir(root, study, "ref", "measure.json")
    fdir = sdir(root, study, "ref", "frames")
    args = [ref_video(root, study), "--out", out, "--scene", scene, "--max-samples", max_samples]
    if os.path.isdir(fdir):
        args += ["--frames-dir", fdir]
    if sub_file:
        args += ["--subs", sub_file]
    run_py("measure.py", *args)
    with open(out, encoding="utf-8") as fp:
        m = json.load(fp)
    if st is not None:
        st["measure"] = {
            "cuts": m["cuts"],
            "motion": m["motion"],
            "palette": m.get("palette"),
            "wpm": m.get("words", {}).get("wpm"),
        }
        if m.get("words", {}).get("wpm"):
            st["wpm"] = m["words"]["wpm"]
        save_study(root, study, st)
        refresh_dossier(root, study, st, focus=focus)
    return m


def run_colors_whole(root, study, n=6):
    load_study(root, study)
    frames = sorted(glob.glob(sdir(root, study, "ref", "frames", "*.jpg")))
    if frames:
        step = max(1, len(frames) // 12)
        sample = frames[::step][:12]
        print(f"whole video ({len(sample)} frames):")
        run_py("technique.py", "palette", *sample, "--n", n)
        return
    with tempfile.TemporaryDirectory(prefix="reva_col_") as tmp:
        v = ref_video(root, study)
        dur = max(0.5, C.probe_media(v)["duration"])
        imgs = []
        for i in range(6):
            t = (i + 0.5) * dur / 6.0
            out = os.path.join(tmp, f"c{i}.jpg")
            C.run_cmd([C.find_ffmpeg(), "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", v, "-frames:v", "1", out])
            if os.path.exists(out):
                imgs.append(out)
        run_py("technique.py", "palette", *imgs, "--n", n)


def _sync_measure_on_transcript(study_dir):
    ms_path = os.path.join(study_dir, "ref", "measure.json")
    if not os.path.exists(ms_path):
        return
    with open(ms_path, encoding="utf-8-sig") as fp:
        ms = json.load(fp)
    st_path = os.path.join(study_dir, "study.json")
    st = json.load(open(st_path, encoding="utf-8-sig")) if os.path.exists(st_path) else None
    if isinstance(st, dict) and ms.get("words", {}).get("wpm"):
        st["wpm"] = ms["words"]["wpm"]
        with open(st_path, "w", encoding="utf-8") as fp:
            json.dump(st, fp, indent=2, ensure_ascii=False)
            fp.write("\n")


def run_transcribe(root, study, a, focus="all"):
    """Ensure `<study>/ref/transcript.{json,txt}` exists and feed updated signals into research + dossier."""
    s_dir = sdir(root, study)
    if getattr(a, "status", False):
        avail = transcribe.detect_backends()
        print("=== REVA TRANSCRIBE BACKENDS ===")
        for k, ok in avail.items():
            print(f"  {k:16} {'READY' if ok else 'not installed / no key'}")
        return {"ok": True, "status": "checked", "backends": avail}

    load_study(root, study)
    res = transcribe.transcribe_study(
        s_dir,
        backend=getattr(a, "backend", "auto"),
        lang=getattr(a, "lang", None),
        model=getattr(a, "model", None),
        from_file=getattr(a, "from_file", None),
        from_text=getattr(a, "from_text", None),
        force=getattr(a, "force", False),
        silent=getattr(a, "silent", False),
    )

    if res.get("status") == "needs_transcript":
        audio_path = res.get("audio_path") or os.path.join(s_dir, "ref", "audio.mp3")
        print(f"=== TRANSCRIPT NEEDED ({study}) ===")
        print(f"  audio extracted  -> {audio_path}")
        if res.get("error"):
            print(f"  last auto attempt -> {res['error']}")
        print("  options (pick any 1):")
        print(f"    1. Agent listen: open {audio_path} with read_file and save lines via:")
        print(f"       python reva.py transcribe {study} --from-file <transcript.txt|.srt|.json> [--lang id|en]")
        print("    2. Local STT:    pip install faster-whisper   then run: python reva.py transcribe " + study)
        print("    3. Cloud STT:    set GEMINI_API_KEY / GROQ_API_KEY / OPENAI_API_KEY and re-run")
        print(f"    4. No speech:    python reva.py transcribe {study} --silent")
        if getattr(a, "strict", False):
            raise SystemExit("transcript required (--strict)")
        return res

    if res.get("ok"):
        research.init_brief(s_dir)
        _sync_measure_on_transcript(s_dir)
        refresh_dossier(root, study, focus=focus)
        print(f"=== TRANSCRIPT READY ({study}) ===")
        print(f"  status   {res.get('status')} ({res.get('backend')})")
        print(f"  words    {res.get('words', 0)}  ({res.get('wpm', 0)} wpm)")
        print(f"  txt      {os.path.join(s_dir, 'ref', 'transcript.txt')}")
        print(f"  next     python reva.py research init {study} && inspect {research.brief_md_path(s_dir)}")
    return res


def run_research(root, study, a, focus="all"):
    """Manage Phase 2 subject understanding & web research (`<study>/research/brief.{json,md}`)."""
    st = load_study(root, study)
    s_dir = sdir(root, study)
    rcmd = a.res_cmd

    if rcmd == "init":
        brief = research.init_brief(s_dir, overwrite=getattr(a, "overwrite", False))
        refresh_dossier(root, study, focus=focus)
        print(f"research brief initialized -> {research.brief_md_path(s_dir)}")
        sigs = brief.get("auto_signals") or {}
        if sigs.get("suggested_queries"):
            print("suggested search queries:")
            for q in sigs["suggested_queries"]:
                print(f"  - {q}")
        return brief

    if rcmd == "show":
        brief = research.load_brief(s_dir) or research.init_brief(s_dir)
        if getattr(a, "json", False):
            print(json.dumps(brief, indent=2, ensure_ascii=False))
        else:
            print(research.render_brief_md(brief).rstrip())
        return brief

    if rcmd == "claims":
        claims = research.extract_claims(s_dir)
        print(f"=== VERIFIABLE TRANSCRIPT CLAIMS ({len(claims)}) ===")
        if not claims:
            print("  (no technical/causal claims extracted yet — transcribe first or add manual concepts)")
        for idx, c in enumerate(claims, 1):
            t_lbl = f"[{C.fmt_ts(c['t'])}] " if c.get("t") is not None else ""
            sp = f" | specs={', '.join(c['specs'])}" if c.get("specs") else ""
            print(f"  {idx}. {t_lbl}{c['claim']}{sp}")
            if c.get("query"):
                print(f"     query: {c['query']}")
        return claims

    if rcmd == "search":
        if not getattr(a, "no_save", False):
            research.record_search_query(s_dir, a.query)
            refresh_dossier(root, study, focus=focus)
        hits = research.web_search(a.query, max_results=a.max_results)
        print(f"=== WEB SEARCH RESULTS ({len(hits)}) ===")
        if not hits:
            print("  (no results from web APIs — use agent search_web or browser tools and save findings via `reva research add-source`)")
        for idx, h in enumerate(hits, 1):
            print(f"  {idx}. [{h['provider']}] {h['title']}")
            print(f"     {h['url']}")
            if h.get("snippet"):
                print(f"     {h['snippet']}")
        return hits

    if rcmd == "images":
        if not getattr(a, "no_save", False):
            research.record_search_query(s_dir, a.query)
        hits = research.search_images(
            a.query,
            max_results=getattr(a, "max_results", 6),
            include_pdf=getattr(a, "include_pdf", False),
        )
        print(f"=== WIKIMEDIA DIAGRAM / IMAGE RESULTS ({len(hits)}) ===")
        if not hits:
            print("  (no Wikimedia image hits — broaden query with English engineering terms)")
        dl_n = int(getattr(a, "download", 0) or 0)
        for idx, h in enumerate(hits, 1):
            dim = f"{h['width']}x{h['height']}" if h.get("width") else "?"
            print(f"  {idx}. {h['title']} [{h['mime']} {dim}]")
            print(f"     {h['url']}")
            if idx <= dl_n:
                try:
                    info = research.fetch_source(
                        s_dir, h["url"], title=h["title"], kind="image", query=a.query
                    )
                    print(f"     saved -> {info.get('local_asset')}")
                except Exception as exc:
                    print(f"     download warn -> {exc}")
        if dl_n > 0:
            refresh_dossier(root, study, focus=focus)
        return hits

    if rcmd == "fetch":
        res = research.fetch_source(
            s_dir,
            a.url,
            title=getattr(a, "title", ""),
            kind=getattr(a, "kind", "article"),
            query=getattr(a, "query", ""),
        )
        refresh_dossier(root, study, focus=focus)
        print(f"=== FETCHED SOURCE: {res['title']} ===")
        print(f"  url    {res['url']}")
        print(f"  asset  {res['local_asset']}")
        if res.get("specs"):
            print(f"  specs  {', '.join(res['specs'][:8])}")
        for idx, ex in enumerate(res.get("excerpts") or [], 1):
            print(f"  [{idx}] {ex}")
        return res

    if rcmd == "add-concept":
        brief = research.add_concept(
            s_dir,
            a.term,
            a.meaning,
            visual=getattr(a, "visual", ""),
            timestamps=getattr(a, "at", ""),
            anatomy=getattr(a, "anatomy", ""),
            must_show=getattr(a, "must_show", None),
            wrong_looks_like=getattr(a, "wrong", ""),
            mechanism=getattr(a, "mechanism", ""),
            specs=getattr(a, "specs", ""),
        )
        refresh_dossier(root, study, focus=focus)
        print(f"recorded concept '{a.term}' ({len(brief.get('concepts') or [])} total) -> {research.brief_md_path(s_dir)}")
        return brief

    if rcmd == "add-source":
        brief = research.add_source(
            s_dir,
            a.title,
            kind=a.kind,
            url=getattr(a, "url", ""),
            takeaway=getattr(a, "takeaway", ""),
            local_asset=getattr(a, "asset", ""),
            download=getattr(a, "download", False),
        )
        refresh_dossier(root, study, focus=focus)
        print(f"recorded [{a.kind}] source '{a.title}' ({len(brief.get('sources') or [])} total) -> {research.brief_md_path(s_dir)}")
        return brief

    if rcmd == "add-visual":
        brief = research.add_visual(
            s_dir, a.item, why=getattr(a, "why", ""), needs_ref=getattr(a, "needs_ref", False)
        )
        refresh_dossier(root, study, focus=focus)
        print(f"recorded visual item '{a.item}' ({len(brief.get('visual_inventory') or [])} total) -> {research.brief_md_path(s_dir)}")
        return brief

    if rcmd == "complete":
        brief = research.complete_brief(
            s_dir,
            what_is_it=a.what,
            domain=a.domain,
            core_thesis=getattr(a, "thesis", None),
            audience_goal=getattr(a, "goal", None),
            language=getattr(a, "lang", None),
            implications=getattr(a, "implication", None),
            open_questions=getattr(a, "question", None),
            force=getattr(a, "force", False),
        )
        st = load_study(root, study)
        refresh_dossier(root, study, st, focus=focus)
        print(f"research complete [{brief['subject']['domain']}] -> {research.brief_md_path(s_dir)}")
        return brief

    if rcmd == "auto":
        res = research.auto_research(
            s_dir,
            max_claims=getattr(a, "max_claims", 3),
            download_images=getattr(a, "download_images", 1),
            fetch_pages=getattr(a, "fetch_pages", 2),
            max_results=getattr(a, "max_results", 5),
        )
        refresh_dossier(root, study, focus=focus)
        print(f"=== AUTO INTERNET RESEARCH ({study}) ===")
        print(f"  claims={len(res['claims'])}  queries={len(res['queries_run'])}  hits={len(res['search_hits'])}  images={len(res['downloaded_images'])}  pages={len(res['fetched_pages'])}")
        for d in res["downloaded_images"]:
            print(f"  [image] {d['title']} -> {d['local_asset']}")
        for p in res["fetched_pages"]:
            sp = f" | specs: {', '.join(p['specs'][:4])}" if p.get("specs") else ""
            print(f"  [page ] {p['title']} -> {p['local_asset']}{sp}")
        for er in res["errors"][:4]:
            print(f"  [warn ] {er}")
        print(f"  next   inspect {research.brief_md_path(s_dir)}, add --mechanism/--specs/--must-show concepts, then `reva research complete {study}`")
        return res

    raise SystemExit(f"unknown research subcommand {rcmd!r}")


def add_brain_subparsers(sub):
    """Register shared `transcribe` and `research` CLI subcommands cleanly."""
    import argparse as _ap

    tr = sub.add_parser("transcribe", help="Step 1 (Brain): transcribe spoken audio or mark silent before measuring/cloning")
    tr.add_argument("study")
    tr.add_argument("--backend", default="auto", choices=["auto", "subs", "faster-whisper", "whisper", "gemini", "groq", "openai", "audio-only"])
    tr.add_argument("--lang")
    tr.add_argument("--model")
    tr.add_argument("--from-file", help="import existing .srt/.vtt/.txt/.json transcript (or timing.json)")
    tr.add_argument("--from-text", help="paste transcript text or `[MM:SS] line` lines")
    tr.add_argument("--silent", action="store_true", help="mark video as genuinely silent (ASMR / no speech)")
    tr.add_argument("--force", action="store_true", help="re-run even if transcript.json already exists")
    tr.add_argument("--status", action="store_true", help="show available STT backends on this machine")
    tr.add_argument("--strict", action="store_true", help="exit non-zero if audio still needs transcription")

    rs = sub.add_parser("research", help="Step 2 (Brain): learn what the video is about via search, docs, images & concepts")
    rsub = rs.add_subparsers(dest="res_cmd", required=True)

    p = rsub.add_parser("init", help="initialize/refresh research/brief.json + brief.md with extracted signals & queries")
    p.add_argument("study")
    p.add_argument("--overwrite", action="store_true")

    p = rsub.add_parser("show", help="print research/brief.md (or JSON with --json)")
    p.add_argument("study")
    p.add_argument("--json", action="store_true")

    p = rsub.add_parser("claims", help="extract verifiable factual/causal claims and search queries from transcript")
    p.add_argument("study")

    p = rsub.add_parser("auto", help="1-command internet learning: extract claims, search web, download diagrams, fetch pages")
    p.add_argument("study")
    p.add_argument("--max-claims", type=int, default=3)
    p.add_argument("--download-images", type=int, default=1)
    p.add_argument("--fetch-pages", type=int, default=2)
    p.add_argument("--max-results", type=int, default=5)

    p = rsub.add_parser("search", help="multi-provider web search (Tavily/Brave if set, Wikipedia fulltext, OpenAlex, DDG)")
    p.add_argument("study")
    p.add_argument("query")
    p.add_argument("--max-results", type=int, default=8)
    p.add_argument("--no-save", action="store_true")

    p = rsub.add_parser("images", help="search Wikimedia Commons for engineering diagrams & reference images")
    p.add_argument("study")
    p.add_argument("query")
    p.add_argument("--max-results", type=int, default=6)
    p.add_argument("--download", type=int, default=0, help="download top N matching files into research/assets/")
    p.add_argument("--include-pdf", action="store_true")
    p.add_argument("--no-save", action="store_true")

    p = rsub.add_parser("fetch", help="fetch a URL, strip HTML/cache text or binary into research/assets/, and log source")
    p.add_argument("study")
    p.add_argument("url")
    p.add_argument("--title", default="")
    p.add_argument("--kind", default="article", choices=list(research.VALID_KINDS))
    p.add_argument("--query", default="", help="rank extracted paragraphs by keyword relevance to this query")

    p = rsub.add_parser("add-concept", help="record learned term + physical mechanism/specs + visual anatomy & must-show rules")
    p.add_argument("study")
    p.add_argument("--term", required=True)
    p.add_argument("--meaning", required=True)
    p.add_argument("--visual", default="")
    p.add_argument("--mechanism", default="", help="physical cause-and-effect explanation (how/why it works or fails)")
    p.add_argument("--specs", default="", help="verified standard numbers, formulas, tolerances, or code tables")
    p.add_argument("--anatomy", default="", help="exact geometric/spatial relationships (who wraps/connects to what)")
    p.add_argument("--must-show", action="append", help="repeatable falsifiable visual requirement")
    p.add_argument("--wrong", default="", help="common visual bug/trap to guard against")
    p.add_argument("--at", default="", help="comma-separated timestamps (e.g. 16.5,21.5)")

    p = rsub.add_parser("add-source", help="record an article, document, standard, image, or footage source")
    p.add_argument("study")
    p.add_argument("--title", required=True)
    p.add_argument("--kind", default="article", choices=list(research.VALID_KINDS))
    p.add_argument("--url", default="")
    p.add_argument("--takeaway", default="")
    p.add_argument("--asset", default="", help="local file to copy into research/assets/")
    p.add_argument("--download", action="store_true", help="download --url into research/assets/")

    p = rsub.add_parser("add-visual", help="record a physical/visual element that needs accurate reference")
    p.add_argument("study")
    p.add_argument("--item", required=True)
    p.add_argument("--why", default="")
    p.add_argument("--needs-ref", action="store_true")

    p = rsub.add_parser("complete", help="mark research brief as researched with what/domain/implications")
    p.add_argument("study")
    p.add_argument("--what", required=True, help="concise identification of what the video/subject is")
    p.add_argument("--domain", required=True, help="subject domain (e.g. civil-engineering, culinary, macroeconomics)")
    p.add_argument("--thesis")
    p.add_argument("--goal")
    p.add_argument("--lang")
    p.add_argument("--implication", action="append", help="repeatable replication implication")
    p.add_argument("--question", action="append", help="repeatable remaining question")
    p.add_argument("--force", action="store_true")

    return _ap
