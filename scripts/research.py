#!/usr/bin/env python3
"""research.py - Step 2 of REVA Brain: understand what the video is actually about before replicating.

Maintains `<study>/research/brief.json` + `<study>/research/brief.md` + `<study>/research/assets/`:
extracts domain terms, standards/measurements, and suggested search queries from transcript + video metadata,
provides stdlib web lookup helpers, stores learned concepts & reference sources (articles, docs, images, footage),
and feeds subject context into dossier.md, technique notes.md, bench.json, skill-export.md, and lab recommendations.
"""
import argparse
import datetime
import html
import html.parser
import json
import mimetypes
import os
import re
import shutil
import urllib.parse
import urllib.request
from collections import Counter

try:
    from . import _common as C
except ImportError:
    import _common as C

VALID_KINDS = ("article", "document", "image", "footage", "standard", "paper", "dataset", "other")

_STOPWORDS = {
    # English
    "the", "and", "for", "with", "that", "this", "from", "are", "was", "were", "you", "your",
    "not", "but", "have", "has", "had", "into", "about", "what", "when", "where", "which",
    "who", "how", "why", "will", "would", "can", "could", "should", "just", "like", "more",
    "most", "some", "such", "than", "then", "them", "they", "their", "there", "these", "those",
    "very", "much", "also", "only", "even", "here", "make", "made", "been", "being", "its",
    # Indonesian
    "yang", "dan", "dari", "untuk", "dengan", "tidak", "bukan", "pada", "bisa", "dapat",
    "akan", "atau", "juga", "ini", "itu", "ada", "adalah", "jadi", "karena", "kalau", "jika",
    "saat", "ketika", "cuma", "hanya", "lagi", "sudah", "belum", "harus", "seperti", "cara",
    "buat", "supaya", "agar", "kita", "kami", "kamu", "mereka", "nya", "lebih", "paling",
    "sangat", "banget", "sama", "masuk", "keluar", "dalam", "luar", "atas", "bawah", "sekitar",
    "kira", "tiap", "setiap", "tetap", "lain", "masih", "mau", "biar",
    # Social / video filler
    "views", "reactions", "video", "reel", "shorts", "subscribe", "follow", "like", "share",
}

_HASHTAG_RE = re.compile(r"#([A-Za-z0-9_]{2,})")
_SPEC_PATTERNS = (
    re.compile(r"\b(?:SNI|ISO|ASTM|ACI|IEEE|DIN|EN|JIS|IEC|WHO|FDA|OSHA)\s*[-:]?\s*\d{2,6}(?:[-.:]\d+)*\b", re.I),
    re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:°|derajat|deg|cm|mm|km|mg|kg|ml|g|l|%|d\b|LUFS|dBTP|Hz|kHz|fps|WPM|USD|IDR|EUR)\b", re.I),
)


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


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def research_dir(study_dir):
    """Return `<study>/research` directory path."""
    return os.path.join(study_dir, "research")


def brief_json_path(study_dir):
    """Return `<study>/research/brief.json` path."""
    return os.path.join(research_dir(study_dir), "brief.json")


def brief_md_path(study_dir):
    """Return `<study>/research/brief.md` path."""
    return os.path.join(research_dir(study_dir), "brief.md")


def assets_dir(study_dir):
    """Return `<study>/research/assets` directory path."""
    return os.path.join(research_dir(study_dir), "assets")


def _clean_text(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _dedupe(seq):
    out = []
    seen = set()
    for x in seq or []:
        s = _clean_text(x)
        if not s:
            continue
        k = s.lower()
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out


_CLAIM_CUES = re.compile(
    r"\b(?:karena|sehingga|supaya|agar|minimal|min\.|maksimal|harus|jangan|akibat|fungsi|"
    r"mencegah|mengunci|terbuka|melengkung|terkelupas|tekuk|sengkang|begel|selimut|inti|"
    r"because|prevents|causes|minimum|must|never|rule|why|how|lock|spall|buckle|confined|"
    r"derajat|kali|diameter|ditekuk|cm|mm)\b",
    re.I,
)
_USER_AGENT = "REVA-Research/2.0 (https://github.com/Exeloxylade/REVA)"


class _HTMLTextExtractor(html.parser.HTMLParser):
    """Strip scripts/styles/nav boilerplate from HTML pages and emit clean readable paragraphs."""

    _SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header"}
    _BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "tr", "blockquote", "section", "article", "br"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._in_title = False
        self.title = ""
        self._chunks = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in self._SKIP_TAGS:
            self._skip_depth += 1
        elif t == "title":
            self._in_title = True
        elif self._skip_depth == 0 and t in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in self._SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif t == "title":
            self._in_title = False
        elif self._skip_depth == 0 and t in self._BLOCK_TAGS:
            self._chunks.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._skip_depth == 0:
            self._chunks.append(data)

    def extract(self):
        raw = "".join(self._chunks)
        lines = [_clean_text(ln) for ln in raw.splitlines()]
        paras = [ln for ln in lines if ln]
        return _clean_text(self.title), "\n\n".join(paras)


def _claim_to_query(text, specs):
    toks = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ0-9_-]{2,}", str(text or ""))
    words = []
    seen = set()
    for sp in specs[:2]:
        for part in sp.split():
            k = part.lower()
            if k not in seen:
                seen.add(k)
                words.append(part)
    for tok in toks:
        low = tok.lower().strip("_-")
        if len(low) < 3 or low in _STOPWORDS or low.isdigit() or low in seen:
            continue
        seen.add(low)
        words.append(tok)
        if len(words) >= 6:
            break
    if not words:
        return ""
    return f"{' '.join(words)} diagram explanation"


def extract_claims(study_dir, max_claims=12):
    """Extract verifiable factual/causal claims + suggested search queries from transcript/script."""
    tr = _read_json(os.path.join(study_dir, "ref", "transcript.json")) or {}
    td = _read_json(os.path.join(study_dir, "ref", "teardown.json")) or {}
    cues = tr.get("cues") or []

    units = []
    if cues:
        buf_text = []
        buf_t = None
        for c in cues:
            txt = _clean_text(c.get("text"))
            if not txt:
                continue
            if buf_t is None:
                buf_t = round(float(c.get("start") or 0), 1)
            buf_text.append(txt)
            joined = " ".join(buf_text)
            if txt.endswith((".", "!", "?")) or len(joined) >= 130:
                units.append((buf_t, joined))
                buf_text = []
                buf_t = None
        if buf_text:
            units.append((buf_t, " ".join(buf_text)))
    else:
        sp = os.path.join(study_dir, "ref", "script.txt")
        raw = ""
        if os.path.exists(sp):
            with open(sp, encoding="utf-8", errors="replace") as fp:
                raw = fp.read()
        if not raw:
            raw = td.get("title") or ""
        for sent in re.split(r"(?<=[.!?])\s+|\n+", raw):
            s = _clean_text(sent)
            if len(s) >= 20:
                units.append((None, s))

    claims = []
    seen_txt = set()
    for t_sec, sent in units:
        if len(sent) < 18:
            continue
        found_specs = _dedupe([m.group(0) for pat in _SPEC_PATTERNS for m in pat.finditer(sent)])
        has_cue = bool(_CLAIM_CUES.search(sent))
        if not found_specs and not has_cue:
            continue
        key = sent.lower()
        if key in seen_txt:
            continue
        seen_txt.add(key)
        claims.append({
            "t": t_sec,
            "claim": sent,
            "specs": found_specs[:5],
            "query": _claim_to_query(sent, found_specs),
        })
        if len(claims) >= max_claims:
            break
    return claims


def extract_signals(study_dir):
    """Extract hashtags, numeric/standard specs, top terms, verifiable claims, and search queries."""
    td = _read_json(os.path.join(study_dir, "ref", "teardown.json")) or {}
    info = _read_json(os.path.join(study_dir, "ref", "ref.info.json")) or {}
    tr = _read_json(os.path.join(study_dir, "ref", "transcript.json")) or {}
    st = _read_json(os.path.join(study_dir, "study.json")) or {}

    title = _clean_text(td.get("title") or info.get("title") or st.get("title") or "")
    uploader = _clean_text(td.get("uploader") or info.get("uploader") or "")
    desc = _clean_text(td.get("description") or info.get("description") or "")
    info_tags = [str(x).strip() for x in (td.get("tags") or info.get("tags") or []) if str(x).strip()]

    script_txt = ""
    sp = os.path.join(study_dir, "ref", "script.txt")
    if os.path.exists(sp):
        with open(sp, encoding="utf-8", errors="replace") as fp:
            script_txt = _clean_text(fp.read())
    if not script_txt and tr.get("cues"):
        script_txt = _clean_text(" ".join(c.get("text", "") for c in tr["cues"]))

    combined = "\n".join(x for x in (title, desc, script_txt) if x)
    # Strip social stats prefix like "3M views · 213K reactions |" from title before keyword mining.
    title_clean = re.sub(r"^\s*[\d.,]+[KMB]?\s+views\s*[·|]\s*[\d.,]+[KMB]?\s+reactions\s*\|\s*", "", title, flags=re.I)

    hashtags = _dedupe(info_tags + _HASHTAG_RE.findall(combined))

    specs = []
    for pat in _SPEC_PATTERNS:
        for m in pat.finditer(combined):
            specs.append(_clean_text(m.group(0)))
    specs = _dedupe(specs)[:12]

    tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ0-9_-]{2,}", f"{title_clean} {script_txt}")
    counts = Counter()
    display_form = {}
    for tok in tokens:
        low = tok.lower().strip("_-")
        if len(low) < 3 or low in _STOPWORDS or low.isdigit():
            continue
        counts[low] += 1
        display_form.setdefault(low, tok)
    top_terms = [display_form[k] for k, _ in counts.most_common(12)]

    claims = extract_claims(study_dir, max_claims=10)
    queries = []
    for c in claims[:3]:
        if c.get("query"):
            queries.append(c["query"])
    for sp_tok in specs[:2]:
        anchor = " ".join(top_terms[:2])
        queries.append(_clean_text(f"{sp_tok} {anchor} engineering standard"))
    if top_terms:
        queries.append(f"{' '.join(top_terms[:4])} explanation diagram")
    if hashtags:
        queries.append(f"{' '.join(hashtags[:3])} reference guide")
    elif title_clean and not queries:
        queries.append(f"{' '.join(title_clean.split()[:6])} technical reference")

    return {
        "title": title,
        "uploader": uploader,
        "transcript_available": bool(tr.get("cues")),
        "word_count": int(tr.get("words") or (len(script_txt.split()) if script_txt else 0)),
        "hashtags": hashtags[:12],
        "numeric_specs": specs,
        "top_terms": top_terms,
        "claims_to_verify": claims,
        "suggested_queries": _dedupe(queries)[:6],
    }


def render_brief_md(brief):
    """Render concise Markdown research brief for agents and human review."""
    subj = brief.get("subject") or {}
    sigs = brief.get("auto_signals") or {}
    concepts = brief.get("concepts") or []
    vis = brief.get("visual_inventory") or []
    sources = brief.get("sources") or []
    impls = brief.get("replication_implications") or []
    qs = brief.get("open_questions") or []
    s_queries = brief.get("search_queries") or sigs.get("suggested_queries") or []
    claims = sigs.get("claims_to_verify") or []

    lines = [
        f"# REVA Subject Research Brief: `{brief.get('study', '?')}`",
        "",
        f"- **Status:** `{brief.get('status', 'draft')}`" + (f" (updated {brief.get('updated_at')})" if brief.get("updated_at") else ""),
        f"- **What is it?** {subj.get('what_is_it') or '<TODO: identify the dish / subject / standard / core topic>'}",
        f"- **Domain:** {subj.get('domain') or '<TODO: e.g. civil-engineering, culinary, macroeconomics, biology>'}",
        f"- **Core thesis:** {subj.get('core_thesis') or '<TODO: 1-sentence takeaway of what the viewer learns>'}",
        f"- **Audience goal:** {subj.get('audience_goal') or '<TODO: why a viewer watches this>'}",
        f"- **Transcript:** {'available (' + str(sigs.get('word_count', 0)) + ' words)' if sigs.get('transcript_available') else 'missing/silent — run `reva transcribe <study>` first if audio exists'}",
        "",
        "## 1. Key Concepts, Physical Mechanism & Visual Anatomy",
    ]
    if concepts:
        for c in concepts:
            ts = f" `[{', '.join(map(str, c['timestamps']))}]`" if c.get("timestamps") else ""
            vis_note = f" | *Visual:* {c['visual']}" if c.get("visual") else ""
            lines.append(f"- **{c.get('term')}**{ts}: {c.get('meaning')}{vis_note}")
            if c.get("mechanism"):
                lines.append(f"  - *Mechanism:* {c['mechanism']}")
            if c.get("specs"):
                lines.append(f"  - *Verified specs:* {c['specs']}")
            if c.get("anatomy"):
                lines.append(f"  - *Anatomy:* {c['anatomy']}")
            if c.get("must_show"):
                for ms_item in c["must_show"]:
                    lines.append(f"  - *Must show:* {ms_item}")
            if c.get("wrong_looks_like"):
                lines.append(f"  - *Wrong looks like:* {c['wrong_looks_like']}")
    else:
        lines.append("- (none recorded yet — research unfamiliar terms via web search and run `reva research add-concept`)")

    lines += ["", "## 2. Visual & Physical Reference Inventory"]
    if vis:
        for v in vis:
            flag = " `[needs ref]`" if v.get("needs_ref") else ""
            why = f" — {v['why']}" if v.get("why") else ""
            lines.append(f"- **{v.get('item')}**{flag}{why}")
    else:
        lines.append("- (list what objects, dishes, mechanisms, or archival plates must look accurate before coding/prompting)")

    lines += ["", "## 3. External Sources & Saved Reference Assets (`research/assets/`)"]
    if sources:
        for s in sources:
            loc = f" | asset `{s['local_asset']}`" if s.get("local_asset") else ""
            url = f" | {s['url']}" if s.get("url") else ""
            take = f" — {s['takeaway']}" if s.get("takeaway") else ""
            lines.append(f"- `[{s.get('kind', 'article')}]` **{s.get('title')}**{url}{loc}{take}")
    else:
        lines.append("- (none saved yet — run `reva research search`, `images`, `fetch`, or agent `search_web`, then save sources)")

    lines += ["", "## 4. Replication Implications (Why Understanding Changes the Build)"]
    if impls:
        lines.extend(f"- {x}" for x in impls)
    else:
        lines.append("- (record physical proportions, causal sequences, terminology, or narration adjustments before coding/prompting)")

    lines += ["", "## 5. Claims to Verify, Search Queries & Open Questions"]
    if claims:
        for c in claims[:6]:
            t_lbl = f"`{C.fmt_ts(c['t'])}` " if c.get("t") is not None else ""
            lines.append(f"- **Claim** {t_lbl}{c['claim']} -> *query:* `{c.get('query', '')}`")
    if s_queries:
        lines.append("- **Suggested / executed queries:** " + " | ".join(f"`{q}`" for q in s_queries))
    if qs:
        lines.extend(f"- [ ] {q}" for q in qs)
    elif not s_queries and not claims:
        lines.append("- (add search queries once transcript is populated)")

    lines += ["", "## 6. Auto-Extracted Signals"]
    if sigs.get("numeric_specs"):
        lines.append("- **Numbers / standards detected:** " + ", ".join(f"`{x}`" for x in sigs["numeric_specs"]))
    if sigs.get("top_terms"):
        lines.append("- **Frequent domain terms:** " + ", ".join(f"`{x}`" for x in sigs["top_terms"][:10]))
    if sigs.get("hashtags"):
        lines.append("- **Tags / hashtags:** " + ", ".join(f"#{x.lstrip('#')}" for x in sigs["hashtags"][:10]))

    return "\n".join(lines) + "\n"


def _sync_study_json(study_dir, brief):
    st_path = os.path.join(study_dir, "study.json")
    st = _read_json(st_path)
    if not isinstance(st, dict):
        return
    subj = brief.get("subject") or {}
    st["research"] = {
        "status": brief.get("status") or "draft",
        "domain": subj.get("domain") or "",
        "what_is_it": subj.get("what_is_it") or "",
        "concepts_count": len(brief.get("concepts") or []),
        "sources_count": len(brief.get("sources") or []),
    }
    _write_json(st_path, st)


def _save_brief(study_dir, brief):
    brief["updated_at"] = _now_iso()
    os.makedirs(assets_dir(study_dir), exist_ok=True)
    _write_json(brief_json_path(study_dir), brief)
    with open(brief_md_path(study_dir), "w", encoding="utf-8") as fp:
        fp.write(render_brief_md(brief))
    _sync_study_json(study_dir, brief)
    return brief


def load_brief(study_dir):
    """Load `<study>/research/brief.json` if present."""
    return _read_json(brief_json_path(study_dir))


def init_brief(study_dir, overwrite=False):
    """Initialize or refresh auto-signals in `<study>/research/brief.{json,md}`."""
    os.makedirs(assets_dir(study_dir), exist_ok=True)
    existing = None if overwrite else load_brief(study_dir)
    sigs = extract_signals(study_dir)
    study_name = (_read_json(os.path.join(study_dir, "study.json")) or {}).get("study") or os.path.basename(os.path.abspath(study_dir))

    if isinstance(existing, dict):
        brief = existing
        brief["study"] = study_name
        brief["auto_signals"] = sigs
        if not brief.get("search_queries"):
            brief["search_queries"] = list(sigs.get("suggested_queries") or [])
    else:
        brief = {
            "schema": "reva-research-brief",
            "version": 1,
            "study": study_name,
            "status": "draft",
            "subject": {
                "what_is_it": "",
                "domain": "",
                "core_thesis": "",
                "audience_goal": "",
                "language": "",
            },
            "auto_signals": sigs,
            "search_queries": list(sigs.get("suggested_queries") or []),
            "concepts": [],
            "visual_inventory": [],
            "sources": [],
            "replication_implications": [],
            "open_questions": [],
            "updated_at": _now_iso(),
        }

    return _save_brief(study_dir, brief)


def _ensure_brief(study_dir):
    brief = load_brief(study_dir)
    return brief if isinstance(brief, dict) else init_brief(study_dir)


def add_concept(
    study_dir,
    term,
    meaning,
    visual="",
    timestamps=None,
    anatomy="",
    must_show=None,
    wrong_looks_like="",
    mechanism="",
    specs="",
):
    """Upsert a learned domain term/concept + mechanism/specs + visual anatomy checklist into brief.json + brief.md."""
    clean_term = _clean_text(term)
    clean_meaning = _clean_text(meaning)
    if not clean_term or not clean_meaning:
        raise ValueError("concept requires non-empty --term and --meaning")

    brief = _ensure_brief(study_dir)
    concepts = brief.setdefault("concepts", [])
    ts_list = _dedupe(timestamps if isinstance(timestamps, (list, tuple)) else ([x.strip() for x in str(timestamps).split(",") if x.strip()] if timestamps else []))
    must_list = _dedupe(must_show if isinstance(must_show, (list, tuple)) else ([must_show] if must_show else []))

    hit = next((c for c in concepts if (c.get("term") or "").strip().lower() == clean_term.lower()), None)
    row = {
        "term": clean_term,
        "meaning": clean_meaning,
        "visual": _clean_text(visual),
        "timestamps": ts_list,
        "mechanism": _clean_text(mechanism),
        "specs": _clean_text(specs),
        "anatomy": _clean_text(anatomy),
        "must_show": must_list,
        "wrong_looks_like": _clean_text(wrong_looks_like),
    }
    if hit is None:
        concepts.append(row)
    else:
        hit["meaning"] = row["meaning"]
        if row["visual"]:
            hit["visual"] = row["visual"]
        if row["timestamps"]:
            hit["timestamps"] = _dedupe((hit.get("timestamps") or []) + row["timestamps"])
        if row["mechanism"]:
            hit["mechanism"] = row["mechanism"]
        if row["specs"]:
            hit["specs"] = row["specs"]
        if row["anatomy"]:
            hit["anatomy"] = row["anatomy"]
        if row["must_show"]:
            hit["must_show"] = _dedupe((hit.get("must_show") or []) + row["must_show"])
        if row["wrong_looks_like"]:
            hit["wrong_looks_like"] = row["wrong_looks_like"]
    return _save_brief(study_dir, brief)


def _download_asset(url, out_dir, slug_hint):
    req = urllib.request.Request(url, headers={"User-Agent": "REVA-Research/1.0"})
    parsed = urllib.parse.urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower()
    if not ext or len(ext) > 8:
        ext = ".bin"
    safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug_hint).strip("-").lower() or "asset"
    dst = os.path.join(out_dir, f"{safe_slug}{ext}")
    max_bytes = 25 * 1024 * 1024
    with urllib.request.urlopen(req, timeout=20) as resp:
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ext == ".bin":
            ext_map = {
                "text/html": ".html",
                "application/pdf": ".pdf",
                "image/png": ".png",
                "image/jpeg": ".jpg",
                "image/webp": ".webp",
                "image/svg+xml": ".svg",
                "text/plain": ".txt",
                "application/json": ".json",
            }
            dst = os.path.join(out_dir, f"{safe_slug}{ext_map.get(ctype, '.dat')}")
        total = 0
        with open(dst, "wb") as fp:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"download exceeded {max_bytes // (1024 * 1024)} MB limit")
                fp.write(chunk)
    return dst


def add_source(study_dir, title, kind="article", url="", takeaway="", local_asset="", download=False):
    """Record an external research source (article, doc, image, footage, standard) and optional asset."""
    clean_title = _clean_text(title)
    clean_kind = (kind or "article").strip().lower()
    if clean_kind not in VALID_KINDS:
        raise ValueError(f"unsupported source kind {kind!r}; choose from {', '.join(VALID_KINDS)}")
    if not clean_title:
        raise ValueError("source requires non-empty --title")

    brief = _ensure_brief(study_dir)
    adir = assets_dir(study_dir)
    os.makedirs(adir, exist_ok=True)
    rel_asset = ""

    if local_asset:
        src_path = os.path.abspath(os.path.expanduser(local_asset))
        if not os.path.exists(src_path):
            raise SystemExit(f"local asset not found: {local_asset}")
        dst_path = os.path.join(adir, os.path.basename(src_path))
        if os.path.abspath(dst_path) != src_path:
            shutil.copy2(src_path, dst_path)
        rel_asset = os.path.relpath(dst_path, study_dir).replace("\\", "/")
    elif download and url and url.startswith(("http://", "https://")):
        dst_path = _download_asset(url, adir, clean_title[:48])
        rel_asset = os.path.relpath(dst_path, study_dir).replace("\\", "/")

    clean_url = _clean_text(url)
    row = {
        "title": clean_title,
        "kind": clean_kind,
        "url": clean_url,
        "takeaway": _clean_text(takeaway),
        "local_asset": rel_asset,
    }
    sources = brief.setdefault("sources", [])
    hit = next(
        (
            s for s in sources
            if (clean_url and (s.get("url") or "").strip().lower() == clean_url.lower())
            or (s.get("title") or "").strip().lower() == clean_title.lower()
        ),
        None,
    )
    if hit is None:
        sources.append(row)
    else:
        for k, v in row.items():
            if v:
                hit[k] = v
    return _save_brief(study_dir, brief)


def add_visual(study_dir, item, why="", needs_ref=False):
    """Record a visual/physical element that needs accurate reference understanding."""
    clean_item = _clean_text(item)
    if not clean_item:
        raise ValueError("visual item requires non-empty --item")
    brief = _ensure_brief(study_dir)
    vis = brief.setdefault("visual_inventory", [])
    hit = next((v for v in vis if (v.get("item") or "").strip().lower() == clean_item.lower()), None)
    row = {"item": clean_item, "why": _clean_text(why), "needs_ref": bool(needs_ref)}
    if hit is None:
        vis.append(row)
    else:
        hit.update(row)
    return _save_brief(study_dir, brief)


def has_verified_source(study_dir, brief=None):
    """Return True if research/brief.json contains at least one external URL or existing local asset."""
    br = brief if isinstance(brief, dict) else load_brief(study_dir)
    if not isinstance(br, dict):
        return False
    for s in br.get("sources") or []:
        url = _clean_text(s.get("url"))
        loc = _clean_text(s.get("local_asset"))
        if url.startswith(("http://", "https://", "file://")):
            return True
        if loc and os.path.exists(os.path.join(study_dir, loc)):
            return True
    return False


def complete_brief(
    study_dir,
    *,
    what_is_it=None,
    domain=None,
    core_thesis=None,
    audience_goal=None,
    language=None,
    implications=None,
    open_questions=None,
    force=False,
):
    """Mark the subject research brief as researched once subject understanding & internet evidence are recorded."""
    brief = _ensure_brief(study_dir)
    subj = brief.setdefault("subject", {})
    if what_is_it is not None:
        subj["what_is_it"] = _clean_text(what_is_it)
    if domain is not None:
        subj["domain"] = _clean_text(domain)
    if core_thesis is not None:
        subj["core_thesis"] = _clean_text(core_thesis)
    if audience_goal is not None:
        subj["audience_goal"] = _clean_text(audience_goal)
    if language is not None:
        subj["language"] = _clean_text(language)

    if implications:
        brief["replication_implications"] = _dedupe((brief.get("replication_implications") or []) + list(implications))
    if open_questions is not None:
        brief["open_questions"] = _dedupe(list(open_questions))

    if not subj.get("what_is_it") or not subj.get("domain"):
        raise SystemExit("cannot complete research brief without --what and --domain")
    if not force and not (brief.get("concepts") or brief.get("sources")):
        raise SystemExit(
            "add at least one learned concept (`reva research add-concept ...`) or external source "
            "(`reva research add-source ...`) before completing, or pass --force"
        )
    if not force and not has_verified_source(study_dir, brief):
        raise SystemExit(
            "internet evidence gate: add at least one verified external source with a real URL or saved local asset "
            "(`reva research search / images / fetch / add-source --url ...`) before completing, or pass --force"
        )

    brief["status"] = "researched"
    return _save_brief(study_dir, brief)


def _fetch_json(url, timeout=12, headers=None, data=None):
    hdrs = {"User-Agent": _USER_AGENT}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, headers=hdrs, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _reconstruct_openalex_abstract(inv_idx):
    if not isinstance(inv_idx, dict) or not inv_idx:
        return ""
    pairs = []
    for word, positions in inv_idx.items():
        if isinstance(positions, list):
            for p in positions:
                pairs.append((int(p), word))
    pairs.sort(key=lambda x: x[0])
    return _clean_text(" ".join(w for _, w in pairs[:60]))


def web_search(query, max_results=8):
    """Multi-provider web lookup using optional Tavily/Brave keys, Wikipedia fulltext search, OpenAlex works, and DDG IA."""
    q = _clean_text(query)
    if not q:
        return []
    results = []
    seen_urls = set()

    def _add(title, url, snippet, provider):
        u = (url or "").strip()
        if not u or u in seen_urls:
            return
        seen_urls.add(u)
        results.append({
            "title": _clean_text(title) or u,
            "url": u,
            "snippet": _clean_text(snippet)[:300],
            "provider": provider,
        })

    # 1. Optional API-key web search providers (Tavily / Brave) if user configured them.
    tavily_key = (os.environ.get("TAVILY_API_KEY") or "").strip()
    if tavily_key:
        try:
            payload = json.dumps({"api_key": tavily_key, "query": q, "max_results": max_results}).encode("utf-8")
            tv = _fetch_json("https://api.tavily.com/search", headers={"Content-Type": "application/json"}, data=payload)
            for item in (tv or {}).get("results") or []:
                _add(item.get("title"), item.get("url"), item.get("content"), "tavily")
        except Exception:
            pass

    brave_key = (os.environ.get("BRAVE_API_KEY") or "").strip()
    if brave_key and len(results) < max_results:
        try:
            u = f"https://api.search.brave.com/res/v1/web/search?q={urllib.parse.quote(q)}&count={min(max_results, 10)}"
            bv = _fetch_json(u, headers={"Accept": "application/json", "X-Subscription-Token": brave_key})
            for item in ((bv or {}).get("web") or {}).get("results") or []:
                _add(item.get("title"), item.get("url"), item.get("description"), "brave")
        except Exception:
            pass

    # 2. Wikipedia full-text search (EN + ID).
    for lang_host in ("en.wikipedia.org", "id.wikipedia.org"):
        if len(results) >= max_results:
            break
        try:
            u = (
                f"https://{lang_host}/w/api.php?action=query&list=search"
                f"&srsearch={urllib.parse.quote(q)}&srlimit={min(max_results, 4)}&format=json"
            )
            data = _fetch_json(u)
            for hit in ((data or {}).get("query") or {}).get("search") or []:
                title = hit.get("title") or ""
                if not title:
                    continue
                snip = html.unescape(re.sub(r"<[^>]+>", "", hit.get("snippet") or ""))
                link = f"https://{lang_host}/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                _add(title, link, snip or f"Wikipedia ({lang_host.split('.')[0]})", lang_host)
        except Exception:
            pass

    # 3. OpenAlex scholarly/engineering works.
    if len(results) < max_results:
        try:
            u = f"https://api.openalex.org/works?search={urllib.parse.quote(q)}&per-page=4"
            oa = _fetch_json(u)
            for w in (oa or {}).get("results") or []:
                ploc = w.get("primary_location") or {}
                link = ploc.get("landing_page_url") or w.get("doi") or w.get("id") or ""
                abst = _reconstruct_openalex_abstract(w.get("abstract_inverted_index"))
                yr = w.get("publication_year") or ""
                snip = abst or f"OpenAlex engineering publication ({yr})"
                _add(w.get("title") or link, link, snip, "openalex")
        except Exception:
            pass

    # 4. DuckDuckGo Instant Answer fallback.
    if len(results) < max_results:
        try:
            u = f"https://api.duckduckgo.com/?q={urllib.parse.quote(q)}&format=json&no_html=1&skip_disambig=1"
            ddg = _fetch_json(u)
            if isinstance(ddg, dict):
                if ddg.get("AbstractURL") and ddg.get("AbstractText"):
                    _add(ddg.get("Heading") or q, ddg["AbstractURL"], ddg["AbstractText"], "duckduckgo")
                for topic in ddg.get("RelatedTopics") or []:
                    if len(results) >= max_results:
                        break
                    if isinstance(topic, dict) and topic.get("FirstURL") and topic.get("Text"):
                        _add(topic["Text"].split(" - ")[0][:80], topic["FirstURL"], topic["Text"], "duckduckgo")
        except Exception:
            pass

    return results[:max_results]


def search_images(query, max_results=6, include_pdf=False):
    """Search Wikimedia Commons API for technical diagrams, schematics, and reference photos."""
    q = _clean_text(query)
    if not q:
        return []
    u = (
        "https://commons.wikimedia.org/w/api.php?action=query&generator=search&gsrnamespace=6"
        f"&gsrsearch={urllib.parse.quote(q)}&gsrlimit={max(max_results * 2, 10)}"
        "&prop=imageinfo&iiprop=url|mime|size|extmetadata&format=json"
    )
    try:
        data = _fetch_json(u)
    except Exception:
        return []
    pages = ((data or {}).get("query") or {}).get("pages") or {}
    out = []
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]
        mime = (ii.get("mime") or "").lower()
        width = int(ii.get("width") or 0)
        height = int(ii.get("height") or 0)
        is_img = mime.startswith("image/")
        is_pdf = mime == "application/pdf"
        if not is_img and not (include_pdf and is_pdf):
            continue
        if is_img and mime != "image/svg+xml" and width and width < 120:
            continue
        url = (ii.get("url") or "").strip()
        if not url:
            continue
        ext = ii.get("extmetadata") or {}
        desc_raw = (ext.get("ImageDescription") or {}).get("value") or ""
        desc = html.unescape(re.sub(r"<[^>]+>", "", desc_raw))
        out.append({
            "title": (p.get("title") or "").replace("File:", "").strip() or os.path.basename(url),
            "url": url,
            "mime": mime,
            "width": width,
            "height": height,
            "description": _clean_text(desc)[:240],
            "provider": "wikimedia-commons",
        })
        if len(out) >= max_results:
            break
    return out


def fetch_source(study_dir, url, *, title="", kind="article", query="", max_chars=24000):
    """Fetch an external URL (or file:// page/asset), cache readable text/binary in research/assets/, and log source."""
    clean_url = (url or "").strip()
    if not clean_url:
        raise ValueError("fetch requires non-empty URL")
    adir = assets_dir(study_dir)
    os.makedirs(adir, exist_ok=True)

    req = urllib.request.Request(clean_url, headers={"User-Agent": _USER_AGENT})
    parsed = urllib.parse.urlparse(clean_url)
    url_base = os.path.basename(urllib.parse.unquote(parsed.path or ""))
    url_ext = os.path.splitext(url_base)[1].lower()
    raw_slug = os.path.splitext(url_base)[0] or parsed.netloc or "source"
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", title or raw_slug).strip("-").lower()[:48] or "source"

    max_bytes = 15 * 1024 * 1024
    with urllib.request.urlopen(req, timeout=20) as resp:
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if not ctype and url_ext:
            ctype = mimetypes.guess_type("x" + url_ext)[0] or ""
        chunks = []
        total = 0
        while True:
            blk = resp.read(65536)
            if not blk:
                break
            total += len(blk)
            if total > max_bytes:
                raise ValueError("fetched source exceeded 15 MB limit")
            chunks.append(blk)
    raw = b"".join(chunks)

    is_binary = ctype.startswith("image/") or ctype == "application/pdf" or url_ext in (
        ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".pdf",
    )
    if is_binary:
        ext_map = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/webp": ".webp",
            "image/svg+xml": ".svg",
            "application/pdf": ".pdf",
        }
        ext = url_ext if url_ext in (".png", ".jpg", ".jpeg", ".webp", ".svg", ".pdf") else ext_map.get(ctype, ".bin")
        dst_path = os.path.join(adir, f"{slug}{ext}")
        with open(dst_path, "wb") as fp:
            fp.write(raw)
        final_title = _clean_text(title) or url_base or slug
        final_kind = kind if kind != "article" else ("document" if ext == ".pdf" else "image")
        rel_asset = os.path.relpath(dst_path, study_dir).replace("\\", "/")
        add_source(study_dir, final_title, kind=final_kind, url=clean_url, takeaway=f"Cached {ctype or ext} asset ({total} bytes).", local_asset=dst_path)
        return {
            "url": clean_url,
            "title": final_title,
            "kind": final_kind,
            "content_type": ctype or ext,
            "local_asset": rel_asset,
            "is_binary": True,
            "excerpts": [],
            "specs": [],
        }

    decoded = raw.decode("utf-8", errors="replace")
    looks_html = "html" in ctype or url_ext in (".html", ".htm") or "<html" in decoded[:400].lower() or "<!doctype" in decoded[:400].lower()
    if looks_html:
        parser = _HTMLTextExtractor()
        parser.feed(decoded)
        parser.close()
        page_title, clean_body = parser.extract()
    else:
        page_title = ""
        clean_body = "\n\n".join(filter(None, (_clean_text(ln) for ln in decoded.splitlines())))

    if len(clean_body) > max_chars:
        clean_body = clean_body[:max_chars]

    dst_path = os.path.join(adir, f"{slug}.txt")
    with open(dst_path, "w", encoding="utf-8") as fp:
        fp.write(f"URL: {clean_url}\nTitle: {page_title or title or slug}\n\n{clean_body}\n")

    specs = _dedupe([m.group(0) for pat in _SPEC_PATTERNS for m in pat.finditer(clean_body)])[:12]
    paras = [p.strip() for p in re.split(r"\n{2,}", clean_body) if len(p.strip()) >= 35]
    q_tokens = {w.lower() for w in re.findall(r"[A-Za-z0-9]{3,}", query or "") if w.lower() not in _STOPWORDS}
    if q_tokens and paras:
        scored = sorted(
            enumerate(paras),
            key=lambda iv: (-sum(1 for t in q_tokens if t in iv[1].lower()), iv[0]),
        )
        excerpts = [_clean_text(p)[:340] for _, p in scored[:5]]
    else:
        excerpts = [_clean_text(p)[:340] for p in paras[:5]]
    if not excerpts and clean_body:
        excerpts = [_clean_text(clean_body)[:340]]

    final_title = _clean_text(title) or page_title or url_base or slug
    takeaway = excerpts[0][:240] if excerpts else "Fetched text resource."
    if specs and len(takeaway) < 180:
        takeaway += f" [Specs: {', '.join(specs[:5])}]"
    rel_asset = os.path.relpath(dst_path, study_dir).replace("\\", "/")
    add_source(study_dir, final_title, kind=kind, url=clean_url, takeaway=takeaway, local_asset=dst_path)
    return {
        "url": clean_url,
        "title": final_title,
        "kind": kind,
        "content_type": ctype or "text/plain",
        "local_asset": rel_asset,
        "is_binary": False,
        "excerpts": excerpts,
        "specs": specs,
    }


def record_search_query(study_dir, query):
    """Append a search query to brief.json for provenance."""
    q = _clean_text(query)
    if not q:
        return
    brief = _ensure_brief(study_dir)
    brief["search_queries"] = _dedupe((brief.get("search_queries") or []) + [q])
    _save_brief(study_dir, brief)


def transcript_window_excerpt(study_dir, start_sec, end_sec):
    """Return formatted `[MM:SS] text` transcript lines overlapping `[start_sec, end_sec]`."""
    tr = _read_json(os.path.join(study_dir, "ref", "transcript.json")) or {}
    cues = tr.get("cues") or []
    if not cues:
        return []
    lo = float(start_sec) - 0.5
    hi = float(end_sec) + 0.5
    hits = [c for c in cues if float(c.get("end", 0)) >= lo and float(c.get("start", 0)) <= hi]
    if not hits:
        mid = (float(start_sec) + float(end_sec)) / 2.0
        nearest = min(cues, key=lambda c: abs((float(c.get("start", 0)) + float(c.get("end", 0))) / 2.0 - mid))
        hits = [nearest]
    return [f"[{C.fmt_ts(c.get('start', 0))}] {c.get('text', '').strip()}" for c in hits if c.get("text", "").strip()]


def _parse_ts_num(tok):
    m = re.match(r"^\s*(?:(\d+):)?(\d+(?:\.\d+)?)\s*$", str(tok or ""))
    if not m:
        return None
    if m.group(1) is not None:
        return int(m.group(1)) * 60 + float(m.group(2))
    return float(m.group(2))


def collect_must_show(study_dir, technique_name="", start_sec=None, end_sec=None):
    """Collect matching mechanism, specs, visual anatomy & must-show checklist specs for a technique."""
    brief = load_brief(study_dir)
    if not isinstance(brief, dict):
        return []
    concepts = brief.get("concepts") or []
    t_tokens = {x for x in re.split(r"[^a-z0-9]+", (technique_name or "").lower()) if len(x) >= 2}

    matched = []
    fallback = []
    for c in concepts:
        must = list(c.get("must_show") or [])
        if not must and not c.get("anatomy") and not c.get("wrong_looks_like") and not c.get("mechanism"):
            continue
        item_pack = {
            "source": c.get("term") or "concept",
            "mechanism": c.get("mechanism") or "",
            "specs": c.get("specs") or "",
            "anatomy": c.get("anatomy") or "",
            "wrong_looks_like": c.get("wrong_looks_like") or "",
            "must_show": must,
        }
        fallback.append(item_pack)

        hit = False
        if start_sec is not None and end_sec is not None and c.get("timestamps"):
            lo, hi = float(start_sec) - 2.0, float(end_sec) + 2.0
            for raw_ts in c["timestamps"]:
                tv = _parse_ts_num(raw_ts)
                if tv is not None and lo <= tv <= hi:
                    hit = True
                    break
        if not hit and t_tokens:
            hay = " ".join([c.get("term") or "", c.get("meaning") or "", c.get("visual") or ""]).lower()
            if any(tok in hay for tok in t_tokens):
                hit = True
        if hit:
            matched.append(item_pack)

    chosen = matched if matched else fallback
    out = []
    for pack in chosen:
        if pack["must_show"]:
            for chk in pack["must_show"]:
                out.append({
                    "check": chk,
                    "source": pack["source"],
                    "mechanism": pack["mechanism"],
                    "specs": pack["specs"],
                    "anatomy": pack["anatomy"],
                    "wrong_looks_like": pack["wrong_looks_like"],
                })
        elif pack["anatomy"] or pack["mechanism"]:
            out.append({
                "check": pack["anatomy"] or pack["mechanism"],
                "source": pack["source"],
                "mechanism": pack["mechanism"],
                "specs": pack["specs"],
                "anatomy": pack["anatomy"],
                "wrong_looks_like": pack["wrong_looks_like"],
            })
    return out


def checklist_path(tech_dir):
    """Return `<study>/<technique>/checklist.json` path."""
    return os.path.join(tech_dir, "checklist.json")


def load_checklist(tech_dir):
    """Load `<technique>/checklist.json` or return empty audit skeleton."""
    data = _read_json(checklist_path(tech_dir))
    if not isinstance(data, dict):
        return {"schema": "reva-visual-audit", "version": 1, "items": []}
    data.setdefault("schema", "reva-visual-audit")
    data.setdefault("version", 1)
    data.setdefault("items", [])
    return data


def save_checklist(tech_dir, data):
    """Persist `<technique>/checklist.json` as UTF-8 without BOM."""
    _write_json(checklist_path(tech_dir), data)
    return data


def seed_checklist(study_dir, tech_dir, technique_name="", start_sec=None, end_sec=None):
    """Seed/merge `must_show` items from research/brief.json into `<technique>/checklist.json`."""
    os.makedirs(tech_dir, exist_ok=True)
    ck = load_checklist(tech_dir)
    items = ck.setdefault("items", [])
    seen = {_clean_text(it.get("check")).lower() for it in items if it.get("check")}
    next_id = max((int(it.get("id") or 0) for it in items), default=0) + 1

    specs = collect_must_show(study_dir, technique_name=technique_name, start_sec=start_sec, end_sec=end_sec)
    for sp in specs:
        txt = _clean_text(sp["check"])
        if not txt or txt.lower() in seen:
            continue
        seen.add(txt.lower())
        items.append({
            "id": next_id,
            "check": txt,
            "source": sp.get("source") or "research",
            "status": "pending",
            "note": "",
        })
        next_id += 1
    return save_checklist(tech_dir, ck)


def add_checklist_item(tech_dir, check_text, source="manual"):
    """Append a manual visual audit checkpoint to `<technique>/checklist.json`."""
    txt = _clean_text(check_text)
    if not txt:
        raise ValueError("checklist item text cannot be empty")
    os.makedirs(tech_dir, exist_ok=True)
    ck = load_checklist(tech_dir)
    items = ck.setdefault("items", [])
    if any(_clean_text(it.get("check")).lower() == txt.lower() for it in items):
        return ck
    next_id = max((int(it.get("id") or 0) for it in items), default=0) + 1
    items.append({
        "id": next_id,
        "check": txt,
        "source": _clean_text(source) or "manual",
        "status": "pending",
        "note": "",
    })
    return save_checklist(tech_dir, ck)


def set_checklist_status(tech_dir, item_id, status, note=""):
    """Update status ('pass'|'fail'|'pending') of 1-based visual audit item id."""
    clean_stat = (status or "").strip().lower()
    if clean_stat not in ("pass", "fail", "pending"):
        raise ValueError(f"invalid checklist status {status!r}")
    ck = load_checklist(tech_dir)
    target_id = int(item_id)
    hit = next((it for it in ck.get("items", []) if int(it.get("id") or 0) == target_id), None)
    if hit is None:
        raise SystemExit(f"checklist item #{target_id} not found in {checklist_path(tech_dir)}")
    hit["status"] = clean_stat
    if note:
        hit["note"] = _clean_text(note)
    hit["audited_at"] = _now_iso()
    return save_checklist(tech_dir, ck)


def checklist_summary(tech_dir):
    """Return compact audit status counts for a technique."""
    ck = load_checklist(tech_dir)
    items = list(ck.get("items") or [])
    passed = sum(1 for it in items if it.get("status") == "pass")
    failed = sum(1 for it in items if it.get("status") == "fail")
    pending = sum(1 for it in items if it.get("status") not in ("pass", "fail"))
    total = len(items)
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "all_passed": (total > 0 and failed == 0 and pending == 0),
        "items": items,
    }


def research_summary(study_dir):
    """Return compact research context dict for downstream dossiers, benches, notes, and exports."""
    brief = load_brief(study_dir)
    if not isinstance(brief, dict):
        return None
    subj = brief.get("subject") or {}
    sigs = brief.get("auto_signals") or {}
    return {
        "status": brief.get("status") or "draft",
        "what_is_it": subj.get("what_is_it") or "",
        "domain": subj.get("domain") or "",
        "core_thesis": subj.get("core_thesis") or "",
        "concepts": list(brief.get("concepts") or []),
        "sources": list(brief.get("sources") or []),
        "replication_implications": list(brief.get("replication_implications") or []),
        "suggested_queries": list(brief.get("search_queries") or sigs.get("suggested_queries") or []),
        "numeric_specs": list(sigs.get("numeric_specs") or []),
    }


def auto_research(study_dir, max_claims=3, download_images=1, fetch_pages=2, max_results=5):
    """Run claims extraction -> web search -> Wikimedia diagrams -> page fetch in one workflow step."""
    brief = init_brief(study_dir)
    sigs = brief.get("auto_signals") or {}
    claims = extract_claims(study_dir)

    raw_queries = [c.get("query") for c in claims if c.get("query")] + list(sigs.get("suggested_queries") or [])
    queries_run = _dedupe(raw_queries)[:max(1, int(max_claims))]

    search_hits = []
    seen_urls = set()
    errors = []
    for q in queries_run:
        record_search_query(study_dir, q)
        try:
            for h in web_search(q, max_results=max_results):
                u = (h.get("url") or "").strip()
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    search_hits.append(h)
        except Exception as exc:
            errors.append(f"web_search({q}): {exc}")

    downloaded_images = []
    if int(download_images) > 0:
        img_q = queries_run[0] if queries_run else (sigs.get("title") or brief.get("study") or "")
        try:
            imgs = search_images(img_q, max_results=max(3, int(download_images)))
            for im in imgs[:int(download_images)]:
                try:
                    downloaded_images.append(
                        fetch_source(study_dir, im["url"], title=im.get("title") or "", kind="image", query=img_q)
                    )
                except Exception as exc:
                    errors.append(f"image_fetch({im.get('url')}): {exc}")
        except Exception as exc:
            errors.append(f"search_images({img_q}): {exc}")

    fetched_pages = []
    if int(fetch_pages) > 0:
        rank_q = queries_run[0] if queries_run else ""
        for h in search_hits:
            if len(fetched_pages) >= int(fetch_pages):
                break
            u = (h.get("url") or "").strip()
            if not u:
                continue
            try:
                fetched_pages.append(
                    fetch_source(study_dir, u, title=h.get("title") or "", kind="article", query=rank_q)
                )
            except Exception as exc:
                errors.append(f"page_fetch({u}): {exc}")

    return {
        "claims": claims,
        "queries_run": queries_run,
        "search_hits": search_hits,
        "downloaded_images": downloaded_images,
        "fetched_pages": fetched_pages,
        "errors": errors,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("study_dir", help="path to studies/<study>")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--overwrite", action="store_true")
    sub.add_parser("show")
    a = ap.parse_args(argv)
    if a.cmd == "init":
        b = init_brief(a.study_dir, overwrite=a.overwrite)
        print(json.dumps(b, indent=2, ensure_ascii=False))
    else:
        b = _ensure_brief(a.study_dir)
        print(render_brief_md(b))


if __name__ == "__main__":
    main()
