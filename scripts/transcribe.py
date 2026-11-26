#!/usr/bin/env python3
"""transcribe.py - Step 1 of REVA Brain: ensure every study has an accurate timestamped transcript.

Supports existing captions (.srt/.vtt), compact ref/audio.mp3 extraction for direct agent listening
(--from-file / --from-text), optional local/cloud STT backends (faster-whisper, whisper, gemini,
groq, openai), and explicit silent video marking (--silent).
"""
import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile

try:
    from . import _common as C
except ImportError:
    import _common as C

_LINE_TS_RE = re.compile(r"^\s*\[(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d+))?\]\s*(.+?)\s*$")


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


def _fmt_srt_ts(sec):
    ms_total = max(0, int(round(float(sec) * 1000.0)))
    h, rem = divmod(ms_total, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _find_ref_video(ref_dir):
    for name in sorted(os.listdir(ref_dir)) if os.path.isdir(ref_dir) else []:
        if name.startswith("ref.") and name.lower().endswith((".mp4", ".mkv", ".webm", ".mov")):
            return os.path.join(ref_dir, name)
    return None


def _study_duration(study_dir, cues=None):
    td = _read_json(os.path.join(study_dir, "ref", "teardown.json")) or {}
    dur = float((td.get("video") or {}).get("duration") or 0)
    if dur <= 0:
        st = _read_json(os.path.join(study_dir, "study.json")) or {}
        dur = float(st.get("duration") or 0)
    if dur <= 0:
        v = _find_ref_video(os.path.join(study_dir, "ref"))
        if v:
            try:
                dur = float(C.probe_media(v).get("duration") or 0)
            except Exception:
                dur = 0.0
    if dur <= 0 and cues:
        dur = max(float(c.get("end") or 0) for c in cues)
    return round(dur, 2)


def detect_backends():
    """Probe available transcription backends without requiring heavy optional installs."""
    has_genai = importlib.util.find_spec("google.genai") is not None
    gemini_key = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    return {
        "faster-whisper": importlib.util.find_spec("faster_whisper") is not None,
        "whisper": (importlib.util.find_spec("whisper") is not None) or bool(shutil.which("whisper")),
        "whisper-cli": bool(shutil.which("whisper-cli") or shutil.which("whisper-ctranslate2")),
        "gemini": bool(has_genai and gemini_key),
        "groq": bool(os.environ.get("GROQ_API_KEY")),
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "agent-listen": True,
    }


def ready_backend_names(backends=None):
    """Return list of ready automatic/manual backend names."""
    b = backends or detect_backends()
    order = ("faster-whisper", "whisper", "whisper-cli", "gemini", "groq", "openai", "agent-listen")
    return [k for k in order if b.get(k)]


def extract_audio(video_path, out_dir, name="audio", force=False):
    """Extract compact mono 16kHz MP3 audio stream for speech listening/STT, or None if silent."""
    if not video_path or not os.path.exists(video_path):
        return None
    meta = C.probe_media(video_path)
    if not meta.get("has_audio"):
        return None

    os.makedirs(out_dir, exist_ok=True)
    out_mp3 = os.path.join(out_dir, f"{name}.mp3")
    if os.path.exists(out_mp3) and os.path.getsize(out_mp3) > 0 and not force:
        return out_mp3

    r = C.run_cmd([
        C.find_ffmpeg(),
        "-hide_banner", "-v", "error", "-y",
        "-i", video_path,
        "-vn", "-ac", "1", "-ar", "16000", "-b:a", "48k",
        out_mp3,
    ])
    if r.returncode != 0 or not os.path.exists(out_mp3) or os.path.getsize(out_mp3) == 0:
        raise RuntimeError(r.stderr[-800:] or f"ffmpeg audio extraction failed on {video_path}")
    return out_mp3


def write_srt(cues, path):
    """Write normalized timestamped cues to UTF-8 SRT (no BOM)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = []
    for idx, c in enumerate(cues, 1):
        txt = re.sub(r"\s+", " ", str(c.get("text") or "")).strip()
        if not txt:
            continue
        t0 = max(0.0, float(c.get("start") or 0.0))
        t1 = max(t0 + 0.05, float(c.get("end") or (t0 + 1.0)))
        lines.append(f"{idx}\n{_fmt_srt_ts(t0)} --> {_fmt_srt_ts(t1)}\n{txt}\n")
    with open(path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines))
    return path


def _normalize_cues(raw_cues):
    norm = []
    for item in raw_cues or []:
        if not isinstance(item, dict):
            continue
        txt = re.sub(r"\s+", " ", str(item.get("text") or "")).strip()
        if not txt:
            continue
        start_val = next(
            (item[k] for k in ("start", "s", "t0", "from") if item.get(k) is not None),
            0.0,
        )
        end_val = next(
            (item[k] for k in ("end", "e", "t1", "to") if item.get(k) is not None),
            None,
        )
        t0 = max(0.0, float(start_val))
        t1 = max(t0 + 0.05, float(end_val)) if end_val is not None else round(t0 + max(0.8, len(txt.split()) * 0.4), 3)
        norm.append({"start": round(t0, 3), "end": round(t1, 3), "text": txt})
    return norm


def parse_import_text(raw_text, dur=0.0):
    """Parse pasted `[MM:SS] text` lines or plain prose text into timestamped cues."""
    clean = str(raw_text or "").lstrip("\ufeff").replace("\r", "").strip()
    if not clean:
        return []

    raw_lines = [ln.strip() for ln in clean.split("\n") if ln.strip()]
    ts_hits = []
    for ln in raw_lines:
        m = _LINE_TS_RE.match(ln)
        if m:
            h = int(m.group(1) or 0)
            mi = int(m.group(2))
            s = int(m.group(3))
            ms = int((m.group(4) or "0").ljust(3, "0")[:3])
            t0 = h * 3600 + mi * 60 + s + ms / 1000.0
            ts_hits.append((t0, m.group(5).strip()))

    if ts_hits and len(ts_hits) >= max(1, len(raw_lines) // 2):
        cues = []
        for i, (t0, txt) in enumerate(ts_hits):
            if i + 1 < len(ts_hits):
                t1 = max(t0 + 0.1, ts_hits[i + 1][0])
            else:
                fallback_end = t0 + max(1.0, len(txt.split()) * 0.42)
                t1 = float(dur) if dur and float(dur) > t0 else fallback_end
            cues.append({"start": round(t0, 3), "end": round(t1, 3), "text": txt})
        return _normalize_cues(cues)

    # Distribute plain prose sentences proportionally by word count across video duration.
    parts = [ln for ln in raw_lines if ln]
    if len(parts) == 1:
        parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", parts[0]) if p.strip()]
    if not parts:
        return []

    total_words = sum(max(1, len(p.split())) for p in parts)
    span = max(float(dur or 0.0), float(len(parts)) * 1.5, 1.0)
    cursor = 0.0
    cues = []
    for p in parts:
        w = max(1, len(p.split()))
        seg_len = span * (w / total_words)
        cues.append({"start": round(cursor, 3), "end": round(cursor + seg_len, 3), "text": p})
        cursor += seg_len
    return _normalize_cues(cues)


def parse_import_file(path, dur=0.0):
    """Parse an imported transcript file (.srt, .vtt, .json, or .txt) into cues."""
    if not os.path.exists(path):
        raise SystemExit(f"transcript file not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext in (".srt", ".vtt"):
        parsed = C.parse_subtitles(path)
        return _normalize_cues(parsed.get("cues") or [])
    if ext == ".json":
        with open(path, encoding="utf-8-sig") as fp:
            data = json.load(fp)
        if isinstance(data, list):
            return _normalize_cues(data)
        if isinstance(data, dict):
            if isinstance(data.get("cues"), list):
                return _normalize_cues(data["cues"])
            if isinstance(data.get("segments"), list):
                return _normalize_cues(data["segments"])
        raise SystemExit(f"unsupported transcript JSON schema in {path} (expected list, 'cues', or 'segments')")
    with open(path, encoding="utf-8-sig", errors="replace") as fp:
        raw = fp.read()
    return parse_import_text(raw, dur=dur)


def save_transcript(
    study_dir,
    cues,
    *,
    source_kind,
    backend,
    language=None,
    dur=None,
    subtitle_filename=None,
):
    """Persist transcript.json, transcript.txt, script.txt, optional .srt, and sync study metrics."""
    ref_dir = os.path.join(study_dir, "ref")
    os.makedirs(ref_dir, exist_ok=True)

    norm_cues = _normalize_cues(cues)
    effective_dur = float(dur) if dur else _study_duration(study_dir, cues=norm_cues)
    full_text = " ".join(c["text"] for c in norm_cues).strip()
    words = len(full_text.split()) if full_text else 0
    talk_span = round(max(0.0, norm_cues[-1]["end"] - norm_cues[0]["start"]), 2) if norm_cues else 0.0
    wpm = round(words / (effective_dur / 60.0), 1) if effective_dur > 0 and words else 0
    wpm_span = round(words / (talk_span / 60.0), 1) if talk_span > 1.0 and words else wpm

    sub_name = subtitle_filename
    if sub_name is None and source_kind != "subtitles" and norm_cues:
        sub_name = "ref.transcribed.srt"
        write_srt(norm_cues, os.path.join(ref_dir, sub_name))

    tr_payload = {
        "subtitle_file": sub_name,
        "source": source_kind,
        "backend": backend,
        "language": language,
        "words": words,
        "wpm": wpm,
        "wpm_talk_span": wpm_span,
        "talk_span_sec": talk_span,
        "cues": norm_cues,
    }
    _write_json(os.path.join(ref_dir, "transcript.json"), tr_payload)

    with open(os.path.join(ref_dir, "transcript.txt"), "w", encoding="utf-8") as fp:
        for c in norm_cues:
            fp.write(f"[{C.fmt_ts(c['start'])}] {c['text']}\n")
    with open(os.path.join(ref_dir, "script.txt"), "w", encoding="utf-8") as fp:
        fp.write((full_text + "\n") if full_text else "")

    td_path = os.path.join(ref_dir, "teardown.json")
    td = _read_json(td_path)
    if isinstance(td, dict):
        script_meta = dict(td.get("script") or {})
        script_meta.update({
            "words": words,
            "wpm": wpm,
            "wpm_talk_span": wpm_span,
            "has_script": bool(full_text),
            "subtitle_file": sub_name or script_meta.get("subtitle_file"),
            "source": source_kind,
            "backend": backend,
        })
        td["script"] = script_meta
        _write_json(td_path, td)

    ms_path = os.path.join(ref_dir, "measure.json")
    ms = _read_json(ms_path)
    if isinstance(ms, dict):
        first_line = norm_cues[0]["text"] if norm_cues else ""
        ms["words"] = {
            "subs": os.path.join(ref_dir, sub_name) if sub_name else None,
            "count": words,
            "wpm": int(round(wpm)) if wpm else 0,
            "wpm_talk_span": int(round(wpm_span)) if wpm_span else 0,
            "first_line": first_line,
        }
        ms.setdefault("style", {})["direction.narration.wpm"] = {
            "rule": "Speaking speed",
            "value": int(round(wpm)) if wpm else 0,
            "basis": "measured",
            "proof": [f"transcribe ({backend}): {words} words / {round(effective_dur, 1)} s"],
        }
        _write_json(ms_path, ms)

    st_path = os.path.join(study_dir, "study.json")
    st = _read_json(st_path)
    if isinstance(st, dict):
        st["wpm"] = wpm
        st["transcript_status"] = "subtitles" if source_kind == "subtitles" else ("silent" if source_kind == "silent" else "transcribed")
        st["transcript_source"] = backend
        if language:
            st["language"] = language
        _write_json(st_path, st)

    return tr_payload


def _run_faster_whisper(audio_path, lang=None, model="base"):
    from faster_whisper import WhisperModel

    wm = WhisperModel(model or "base", device="auto", compute_type="int8")
    segments, info = wm.transcribe(audio_path, language=lang or None, vad_filter=True)
    cues = [{"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()} for seg in segments if seg.text.strip()]
    return cues, getattr(info, "language", lang)


def _run_whisper(audio_path, lang=None, model="base"):
    if importlib.util.find_spec("whisper") is not None:
        import whisper

        wm = whisper.load_model(model or "base")
        kwargs = {"language": lang} if lang else {}
        res = wm.transcribe(audio_path, **kwargs)
        cues = [{"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip()} for s in res.get("segments", []) if s.get("text", "").strip()]
        return cues, res.get("language") or lang

    cli = shutil.which("whisper") or shutil.which("whisper-ctranslate2")
    if not cli:
        raise RuntimeError("whisper CLI/module not available")
    with tempfile.TemporaryDirectory(prefix="reva_wh_") as tmp:
        cmd = [cli, audio_path, "--model", model or "base", "--output_format", "json", "--output_dir", tmp]
        if lang:
            cmd += ["--language", lang]
        r = C.run_cmd(cmd)
        if r.returncode != 0:
            raise RuntimeError(r.stderr[-600:] or "whisper CLI failed")
        stem = os.path.splitext(os.path.basename(audio_path))[0]
        jpath = os.path.join(tmp, stem + ".json")
        res = _read_json(jpath) or {}
        cues = [{"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip()} for s in res.get("segments", []) if s.get("text", "").strip()]
        return cues, res.get("language") or lang


def _run_gemini(audio_path, lang=None, model="gemini-2.5-flash"):
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key) if api_key else genai.Client()
    prompt = (
        "Transcribe the spoken audio accurately in its original language"
        + (f" (language hint: {lang})" if lang else "")
        + ". Return strict JSON only with shape: "
        '{"language":"<iso>","cues":[{"start":0.0,"end":2.5,"text":"..."}]}.'
    )
    if os.path.getsize(audio_path) <= 18 * 1024 * 1024:
        with open(audio_path, "rb") as fp:
            part = types.Part.from_bytes(data=fp.read(), mime_type="audio/mpeg")
        contents = [prompt, part]
    else:
        uploaded = client.files.upload(file=audio_path)
        contents = [prompt, uploaded]

    resp = client.models.generate_content(
        model=model or "gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    payload = json.loads(resp.text)
    cues = _normalize_cues(payload.get("cues") or [])
    return cues, payload.get("language") or lang


def _run_openai_compat(audio_path, api_key, endpoint, model, lang=None):
    if importlib.util.find_spec("requests") is None:
        raise RuntimeError("Python 'requests' package is required for OpenAI/Groq transcription endpoint")
    import requests

    data = {"model": model, "response_format": "verbose_json"}
    if lang:
        data["language"] = lang
    with open(audio_path, "rb") as fp:
        resp = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files={"file": (os.path.basename(audio_path), fp, "audio/mpeg")},
            timeout=180,
        )
    if resp.status_code >= 400:
        raise RuntimeError(f"STT HTTP {resp.status_code}: {resp.text[:400]}")
    payload = resp.json()
    segs = payload.get("segments") or []
    if segs:
        cues = [{"start": float(s["start"]), "end": float(s["end"]), "text": s["text"].strip()} for s in segs if s.get("text", "").strip()]
    else:
        cues = parse_import_text(payload.get("text") or "")
    return cues, payload.get("language") or lang


def transcribe_study(
    study_dir,
    *,
    backend="auto",
    lang=None,
    model=None,
    from_file=None,
    from_text=None,
    force=False,
    silent=False,
):
    """Ensure `<study>/ref/transcript.{json,txt}` exists using subs, imports, STT, or audio extraction."""
    ref_dir = os.path.join(study_dir, "ref")
    os.makedirs(ref_dir, exist_ok=True)
    dur = _study_duration(study_dir)

    if silent:
        tr = save_transcript(
            study_dir, [], source_kind="silent", backend="marked-silent", language=lang, dur=dur, subtitle_filename=""
        )
        return {"ok": True, "status": "silent", **tr}

    if from_file or from_text:
        cues = parse_import_file(from_file, dur=dur) if from_file else parse_import_text(from_text, dur=dur)
        if not cues:
            raise SystemExit("imported transcript produced 0 cues")
        tr = save_transcript(study_dir, cues, source_kind="import", backend="agent-import", language=lang, dur=dur)
        return {"ok": True, "status": "imported", **tr}

    if backend in ("auto", "subs") and not force:
        tr_existing = _read_json(os.path.join(ref_dir, "transcript.json"))
        if isinstance(tr_existing, dict) and tr_existing.get("cues"):
            tr = save_transcript(
                study_dir,
                tr_existing["cues"],
                source_kind=tr_existing.get("source") or "subtitles",
                backend=tr_existing.get("backend") or "existing",
                language=tr_existing.get("language") or lang,
                dur=dur,
                subtitle_filename=tr_existing.get("subtitle_file"),
            )
            return {"ok": True, "status": "existing", **tr}

        sub_file = C.pick_subtitle_file(ref_dir)
        if sub_file:
            parsed = C.parse_subtitles(sub_file)
            if parsed.get("cues"):
                tr = save_transcript(
                    study_dir,
                    parsed["cues"],
                    source_kind="subtitles",
                    backend="yt-dlp-subs",
                    language=lang,
                    dur=dur,
                    subtitle_filename=os.path.basename(sub_file),
                )
                return {"ok": True, "status": "subtitles", **tr}

    video_path = _find_ref_video(ref_dir)
    audio_path = extract_audio(video_path, ref_dir) if video_path else None
    if not audio_path:
        st_path = os.path.join(study_dir, "study.json")
        st = _read_json(st_path)
        if isinstance(st, dict):
            st["transcript_status"] = "no-audio"
            _write_json(st_path, st)
        return {"ok": True, "status": "no-audio", "words": 0, "cues": []}

    avail = detect_backends()
    if backend == "audio-only":
        chosen = []
    elif backend == "auto":
        chosen = [b for b in ("faster-whisper", "whisper", "gemini", "groq", "openai") if avail.get(b)]
    else:
        if not avail.get(backend):
            raise SystemExit(
                f"transcription backend {backend!r} is not ready on this machine "
                f"(ready backends: {', '.join(ready_backend_names(avail))})"
            )
        chosen = [backend]

    last_err = None
    for b in chosen:
        try:
            if b == "faster-whisper":
                cues, det_lang = _run_faster_whisper(audio_path, lang=lang, model=model or "base")
            elif b == "whisper":
                cues, det_lang = _run_whisper(audio_path, lang=lang, model=model or "base")
            elif b == "gemini":
                cues, det_lang = _run_gemini(audio_path, lang=lang, model=model or "gemini-2.5-flash")
            elif b == "groq":
                cues, det_lang = _run_openai_compat(
                    audio_path,
                    os.environ["GROQ_API_KEY"],
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    model or "whisper-large-v3-turbo",
                    lang=lang,
                )
            elif b == "openai":
                cues, det_lang = _run_openai_compat(
                    audio_path,
                    os.environ["OPENAI_API_KEY"],
                    "https://api.openai.com/v1/audio/transcriptions",
                    model or "whisper-1",
                    lang=lang,
                )
            else:
                continue

            if not cues:
                last_err = f"{b} returned 0 cues"
                continue
            tr = save_transcript(study_dir, cues, source_kind="stt", backend=b, language=det_lang or lang, dur=dur)
            return {"ok": True, "status": "transcribed", **tr}
        except Exception as exc:
            last_err = f"{b}: {exc}"

    st_path = os.path.join(study_dir, "study.json")
    st = _read_json(st_path)
    if isinstance(st, dict):
        st["transcript_status"] = "needed"
        _write_json(st_path, st)

    return {
        "ok": False,
        "status": "needs_transcript",
        "audio_path": audio_path,
        "backends": avail,
        "error": last_err,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("study_dir", help="path to studies/<study>")
    ap.add_argument("--backend", default="auto", choices=["auto", "subs", "faster-whisper", "whisper", "gemini", "groq", "openai", "audio-only"])
    ap.add_argument("--lang")
    ap.add_argument("--model")
    ap.add_argument("--from-file")
    ap.add_argument("--from-text")
    ap.add_argument("--silent", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    res = transcribe_study(
        a.study_dir,
        backend=a.backend,
        lang=a.lang,
        model=a.model,
        from_file=a.from_file,
        from_text=a.from_text,
        force=a.force,
        silent=a.silent,
    )
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
