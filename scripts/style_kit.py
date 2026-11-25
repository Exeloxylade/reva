#!/usr/bin/env python3
"""style_kit.py - dossier generation, golden beats, style scaffolding, placeholder check, and Branch 1 skill export."""
import copy
import glob
import json
import math
import os
import re
import shutil
import textwrap

try:
    from . import _common as C
    from . import lab_engine
except ImportError:
    import _common as C
    import lab_engine

_PLACEHOLDER_RE = re.compile(r"<[^>\n]{2,}>")

_BUILTIN_TEMPLATE = {
    "schema": "video-style",
    "version": 1,
    "id": "<style-id>",
    "name": "<Short name>",
    "info": {
        "title": "<reference title>",
        "creator": "<channel>",
        "url": "<url>",
        "references": [],
        "genre": "<TODO: one-line genre summary>",
        "duration_sec": 0,
        "format": "long",
        "inspected": [],
        "audio_heard": False,
    },
    "direction": {
        "purpose": "<TODO: one sentence explaining what this video format does and when to reuse it>",
        "story": {
            "order": ["hook", "problem", "explanation", "payoff"],
            "rules": [
                {"rule": "<TODO: pacing/story structure rule observed in contact sheets>", "value": "<TODO: timing>", "basis": "observed", "proof": ["<00:00>"]}
            ],
        },
        "hook_0_5s": [
            {"from": 0, "to": 3.0, "narration": "<TODO: what the opening line does>", "visual_kind": "scene", "shot": "<TODO: opening picture>", "sound": "<TODO: voice/SFX in first 3s>", "basis": "observed", "proof": ["00:00"]}
        ],
        "narration": {
            "wpm": {"rule": "Speaking speed", "value": 150, "basis": "measured", "proof": ["reva measure"]},
            "rules": [
                {"rule": "<TODO: writing/tone rule from transcript>", "value": "<TODO: cadence>", "basis": "observed", "proof": ["00:00"]}
            ],
            "line_templates": ["<TODO: sentence pattern with [BLANK] for new topics>"],
        },
        "scene_maker": {
            "avg_shot_sec": {"rule": "Average picture length", "value": 3.0, "basis": "measured", "proof": ["reva measure"]},
            "cuts_per_min": {"rule": "Picture changes per minute", "value": 15.0, "basis": "measured", "proof": ["reva measure"]},
            "transitions": [{"rule": "<TODO: hard cuts only vs dissolves/wipes>", "value": "all cuts", "basis": "observed", "proof": ["contact sheets"]}],
            "motion": [],
            "text_on_screen": [{"rule": "<TODO: where on-screen labels/numbers appear>", "value": "<TODO: frequency>", "basis": "observed", "proof": ["contact sheets"]}],
        },
        "scene_cards": [
            {
                "type": "hook",
                "purpose": "<TODO: purpose of opening scene type>",
                "length_sec": [3, 6],
                "narration": "<TODO: what is spoken over this card>",
                "visual_kind": "scene",
                "shot": "<TODO: subject, composition, framing, text placement>",
                "cut": "<TODO: hold time>",
                "motion": "<TODO: still or subtle motion>",
                "text": "None",
                "sfx": "<TODO: sound cue>",
                "sfx_basis": "proposed",
                "basis": "observed",
                "proof": ["00:00"],
                "resource": "generated-image",
            }
        ],
        "resource_mix": {"dominant": "generated-image", "types": []},
    },
    "look": {
        "look_id": "<style-id>",
        "art_style": "<TODO: medium, line weight, shading, texture — one paragraph a painter/model can follow>",
        "character": "<TODO: character proportions, outfit/markers, consistency rules>",
        "background": "<TODO: environment types and clean diagram backgrounds>",
        "lighting": "<TODO: calm vs dramatic lighting>",
        "colors": {"palette": ["#1A1A1A", "#FFFFFF"], "accent": "#8B1A2B"},
        "font_look": "<TODO: lettering style and placement>",
        "picture_rules": [
            "<TODO: 1 idea per frame + subject scale>",
            "<TODO: camera height/angle>",
            "<TODO: background simplicity>",
            "<TODO: visual symbols (arrows, X, check, badges)>",
            "<TODO: where drawn text/numbers sit, if any>",
        ],
        "framing": "flat",
        "text_in_image": {"allowed": False, "max_items": 3, "max_words": 3, "font": "<TODO: font description if allowed>"},
        "kinds": {
            "scene": {"supported": True, "render": "<TODO: how a general scene is rendered>"},
            "photo": {"supported": False, "render": "Not used", "fallback": "scene"},
            "footage": {"supported": False, "render": "Not used", "fallback": "scene"},
        },
        "can_do": {"limbs_move": False, "face_change": False, "lip_sync": False, "camera_moves": False},
        "basis": "observed",
        "proof": ["contact sheets"],
    },
    "do_not_copy": [
        "exact lines from the narration",
        "frames or screenshots",
        "music and sound effects",
        "the reference's characters and logos",
    ],
    "limitations": ["audio_heard is false until manually auditioned"],
}


def _read_json(path):
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as fp:
            return json.load(fp)
    return None


def find_placeholders(obj, prefix=""):
    """Return list of (json_path, value) for any leftover <...> template placeholders."""
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            hits.extend(find_placeholders(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(find_placeholders(v, f"{prefix}[{i}]"))
    elif isinstance(obj, str) and _PLACEHOLDER_RE.search(obj):
        hits.append((prefix, obj))
    return hits


def resolve_style_file(study_dir, style_id=None):
    """Locate <study>/style/<id>/<id>.style.json cleanly."""
    if style_id:
        p = os.path.join(study_dir, "style", style_id, f"{style_id}.style.json")
        if not os.path.exists(p):
            raise SystemExit(f"style not found: {p} (run scaffold first)")
        return p
    hits = sorted(glob.glob(os.path.join(study_dir, "style", "*", "*.style.json")))
    if not hits:
        raise SystemExit(f"no style files in {os.path.join(study_dir, 'style')} (run scaffold first)")
    if len(hits) > 1:
        names = ", ".join(os.path.basename(os.path.dirname(h)) for h in hits)
        raise SystemExit(f"multiple styles found ({names}); pass --style <id>")
    return hits[0]


def check_style_local(style_json_path, app_dir=None):
    """Validate UTF-8 BOM, leftover <...> placeholders, and Automated-Lunch-Free style-check.js."""
    with open(style_json_path, "rb") as fp:
        has_bom = fp.read(3).startswith(b"\xef\xbb\xbf")
    with open(style_json_path, encoding="utf-8-sig") as fp:
        data = json.load(fp)
    sid = data.get("id") or os.path.basename(os.path.dirname(style_json_path))
    placeholders = find_placeholders(data)

    ran = False
    ok = True
    output = ""
    node_bin = shutil.which("node")
    if app_dir and node_bin:
        ran = True
        r = C.run_cmd([node_bin, os.path.join(app_dir, "scripts", "style-check.js"), style_json_path], cwd=app_dir)
        ok = (r.returncode == 0)
        output = "\n".join(x for x in (r.stdout.strip(), r.stderr.strip()) if x)

    return {
        "style_id": sid,
        "style_file": style_json_path,
        "bom": has_bom,
        "placeholders": placeholders,
        "style_check_ran": ran,
        "style_check_ok": ok,
        "style_check_output": output,
    }


def write_dossier(study_dir, study_data=None, focus="all"):
    """Compile ref/teardown.json, measure.json, sound.json, transcript.json into dossier.md."""
    study = study_data or _read_json(os.path.join(study_dir, "study.json")) or {}
    td = _read_json(os.path.join(study_dir, "ref", "teardown.json")) or {}
    ms = _read_json(os.path.join(study_dir, "ref", "measure.json")) or {}
    snd = _read_json(os.path.join(study_dir, "ref", "sound.json")) or {}
    tr = _read_json(os.path.join(study_dir, "ref", "transcript.json")) or {}

    meta = td.get("video") or {}
    td_sound = td.get("sound") or {}
    td_script = td.get("script") or {}
    cuts = ms.get("cuts") or {}
    motion = ms.get("motion") or {}
    pal = ms.get("palette") or {}
    words_info = ms.get("words") or {}

    name = study.get("study") or os.path.basename(os.path.abspath(study_dir))
    lines = [
        f"# REVA Study Dossier: `{name}`",
        "",
        "## 1. Source & Media Specs",
        f"- **Source:** {study.get('source') or td.get('source') or 'unknown'}",
        f"- **Title:** {td.get('title') or study.get('title') or '(local file)'} ({td.get('uploader') or 'unknown uploader'})",
        f"- **Picture:** {td.get('aspect') or 'unknown'} | aspect `{td.get('aspect_ratio') or ms.get('aspect_ratio') or '?'}` | format `{td.get('format_kind') or '?'}` | {meta.get('fps', '?')} fps | {meta.get('duration', study.get('duration', '?'))} s",
        f"- **Audio:** {meta.get('audio_channels', '?')} ch @ {meta.get('audio_sample_rate', '?')} Hz | loudness {td_sound.get('lufs', '?')} LUFS | true peak {td_sound.get('true_peak', '?')} dBTP",
        "",
        "## 2. Pacing & Motion (Measured)",
    ]

    if cuts:
        lines += [
            f"- **Cuts:** {cuts.get('count', 0)} changes ({cuts.get('per_min', 0)}/min) | thirds `{'/'.join(map(str, cuts.get('thirds', [])))}`",
            f"- **Shot lengths:** median `{cuts.get('median_sec')} s` | p10 `{cuts.get('p10_sec')} s` | p90 `{cuts.get('p90_sec')} s` | max `{cuts.get('max_sec')} s`",
        ]
    elif td.get("shots"):
        sh = td["shots"]
        lines.append(f"- **Shots (teardown):** {sh.get('count')} shots | avg `{sh.get('avg_len')} s` | range `{sh.get('min_len')}-{sh.get('max_len')} s`")

    if motion:
        lines.append(
            f"- **Motion:** {motion.get('still', 0)} still, {motion.get('subtle', 0)} subtle, {motion.get('moving', 0)} moving "
            f"(of {motion.get('samples', 0)} sampled) -> **{round(motion.get('still_share', 0) * 100)}% still** | max static `{motion.get('max_static_sec')} s`"
        )

    wpm_val = words_info.get("wpm") or td_script.get("wpm") or 0
    word_cnt = words_info.get("count") or td_script.get("words") or 0
    lines.append(f"- **Narration speed:** {word_cnt} words -> **{wpm_val} WPM**" + (f" (talk-span {words_info.get('wpm_talk_span')} WPM)" if words_info.get("wpm_talk_span") else ""))

    lines += ["", "## 3. Measured Color Palette"]
    if pal.get("main"):
        lines.append("- **Main colors:** " + ", ".join(f"`{c['hex']}` ({c['share']}%)" for c in pal["main"]))
    else:
        lines.append("- **Main colors:** not measured yet (`measure` or `colors`)")
    if pal.get("accents"):
        lines.append("- **Saturated accents:** " + ", ".join(f"`{c['hex']}` ({c['share']}%)" for c in pal["accents"]))

    if focus in ("all", "code") or snd:
        lines += ["", "## 4. Sound & SFX Profile"]
        if not snd:
            lines.append("- Not probed yet (`reva-code sound <study>`).")
        elif not snd.get("stereo_separation"):
            lines.append(f"- **Note:** {snd.get('note') or 'Stereo L-R separation unavailable (mono/dual-mono)'}")
        else:
            lines.append(
                f"- **Stereo events:** {snd.get('event_count')} events in {snd.get('duration_sec')} s = **{snd.get('events_per_min')}/min** "
                f"(mid/side ratio {snd.get('mid_to_side_db')} dB)"
            )
            for kind, row in (snd.get("summary_by_kind") or {}).items():
                lines.append(
                    f"  - `{kind}`: n={row['count']}, rise {row['median_rise_ms']} ms, tail {row['median_tail_ms']} ms, "
                    f"bright {row['median_centroid_hz']} Hz, harsh {row['median_harsh_pct']}%, vs voice {row['median_vs_voice_db']:+.1f} dB"
                )

    lines += ["", "## 5. Visual Artifacts & Outputs"]
    sheets = sorted(glob.glob(os.path.join(study_dir, "ref", "contact-sheet-*.jpg")))
    if sheets:
        lines.append(f"- **Contact sheets ({len(sheets)}):** " + ", ".join(f"`ref/{os.path.basename(s)}`" for s in sheets))

    techs = study.get("techniques") or {}
    if focus in ("all", "code") or techs:
        if techs:
            for k, t in techs.items():
                if isinstance(t, dict):
                    cmp_exists = os.path.exists(os.path.join(study_dir, k, "compare.jpg"))
                    extras = []
                    if t.get("reused_from"):
                        extras.append(f"reused `{t['reused_from']}`")
                    if t.get("winning_engine"):
                        extras.append(f"winner `{t['winning_engine']}`")
                    elif t.get("trials"):
                        extras.append(f"trials `{','.join(sorted(t['trials'].keys()))}`")
                    if t.get("promoted_pattern"):
                        extras.append(f"promoted `{t['promoted_pattern']}`")
                    tail = (" | " + " | ".join(extras)) if extras else ""
                    lines.append(
                        f"- **Technique `{k}`:** status `{t.get('status', 'unknown')}` | {t.get('from', '?')}-{t.get('to', '?')} s | "
                        f"compare.jpg: {'yes' if cmp_exists else 'no'}{tail}"
                    )
        elif focus in ("all", "code"):
            lines.append("- No isolated techniques yet (`reva-code add <study> <name> --from <s> --to <s> --grid`).")

    styles = sorted(glob.glob(os.path.join(study_dir, "style", "*", "*.style.json")))
    if focus in ("all", "style") or styles:
        if styles:
            for sf in styles:
                sid = os.path.basename(os.path.dirname(sf))
                sdata = _read_json(sf) or {}
                ph_cnt = len(find_placeholders(sdata))
                b_path = os.path.join(os.path.dirname(sf), "test", "beats.json")
                beats = _read_json(b_path) if os.path.exists(b_path) else []
                lines.append(f"- **Prompt style `{sid}`:** {ph_cnt} placeholders left | {len(beats)} golden beats")
        elif focus == "style":
            lines.append("- No prompt style scaffolded yet (`reva-style scaffold <study>`).")

    lines += ["", "## 6. Lab Engine Recommendations & Reusable Patterns"]
    try:
        rec = lab_engine.recommend_for_study(study_dir)
        pats = rec.get("matching_patterns") or []
        cands = rec.get("ready_candidates") or []
        ups = rec.get("upgrade_candidates") or []
        if pats:
            lines.append("- **Matching reusable patterns:** " + ", ".join(
                f"`{p['id']}` (`{p['winning_engine']}`)" for p in pats[:3]
            ))
        if cands:
            lines.append("- **Ready candidate engines:** " + ", ".join(
                f"`{e['id']}`" + (f" ({e['_reasons'][0]})" if e.get("_reasons") else "") for e in cands[:3]
            ))
        if ups:
            lines.append("- **Optional upgrade engines:** " + ", ".join(
                f"`{e['id']}` [{e['status']}]" for e in ups[:2]
            ))
        if not pats and not cands:
            lines.append("- Run `reva-lab engines` and `reva-lab recommend <study>` to inspect lab capabilities.")
    except Exception:
        lines.append("- Lab registry unavailable.")

    cues = tr.get("cues") or []
    lines += ["", "## 7. Transcript Preview"]
    if cues:
        for c in cues[:20]:
            lines.append(f"- `[{C.fmt_ts(c['start'])}]` {c['text']}")
        if len(cues) > 20:
            lines.append(f"- ... ({len(cues) - 20} more cues in `ref/transcript.txt`)")
    else:
        lines.append("- No subtitles extracted.")

    out_path = os.path.join(study_dir, "dossier.md")
    with open(out_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")
    return out_path


def _auto_beat_times(study_dir, dur, count):
    td = _read_json(os.path.join(study_dir, "ref", "teardown.json")) or {}
    shots = (td.get("shots") or {}).get("list") or []
    lo = 1.0 if dur > 4.0 else min(0.2, dur * 0.1)
    hi = max(lo + 0.1, dur - (1.0 if dur > 4.0 else min(0.2, dur * 0.1)))

    mids = [round((s["start"] + s["end"]) / 2.0, 1) for s in shots if lo <= (s["start"] + s["end"]) / 2.0 <= hi]
    if len(mids) >= count:
        if count == 1:
            return [mids[len(mids) // 2]]
        picked = []
        for i in range(count):
            idx = int(round(i * (len(mids) - 1) / (count - 1)))
            t = mids[idx]
            if t not in picked:
                picked.append(t)
        if len(picked) == count:
            return picked

    if count == 1:
        return [round((lo + hi) / 2.0, 1)]
    return [round(lo + i * (hi - lo) / (count - 1), 1) for i in range(count)]


def build_beats(study_dir, style_id, ref_video_path, times=None, auto=False, count=8):
    """Extract N golden beat frames + aligned narration into style/<id>/test/."""
    from PIL import Image, ImageDraw

    meta = C.probe_media(ref_video_path)
    dur = max(0.2, meta["duration"])
    if times:
        beat_times = [round(max(0.0, min(dur - 0.05, float(t))), 2) for t in times]
    else:
        beat_times = _auto_beat_times(study_dir, dur, max(1, int(count)))

    tr = _read_json(os.path.join(study_dir, "ref", "transcript.json")) or {}
    cues = tr.get("cues") or []

    test_dir = os.path.join(study_dir, "style", style_id, "test")
    ref_dir = os.path.join(test_dir, "ref")
    os.makedirs(ref_dir, exist_ok=True)
    for old in glob.glob(os.path.join(ref_dir, "b*.jpg")):
        os.remove(old)

    ff = C.find_ffmpeg()
    beats = []
    frame_paths = []
    for idx, t in enumerate(beat_times, 1):
        bid = f"b{idx}"
        rel_ref = f"ref/{bid}.jpg"
        dst = os.path.join(ref_dir, f"{bid}.jpg")
        r = C.run_cmd([ff, "-hide_banner", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", ref_video_path, "-frames:v", "1", "-q:v", "2", dst])
        if r.returncode != 0 or not os.path.exists(dst):
            raise RuntimeError(r.stderr[-600:] or f"failed extracting beat frame at {t}s")
        nar = C.narration_at(cues, t, window=3.5) or "(no subtitles -- write spoken line here)"
        beats.append({
            "id": bid,
            "scene": f"sc{idx:02d}",
            "t": t,
            "ref": rel_ref,
            "narration": nar,
        })
        frame_paths.append(dst)

    beats_json = os.path.join(test_dir, "beats.json")
    with open(beats_json, "w", encoding="utf-8") as fp:
        json.dump(beats, fp, indent=2, ensure_ascii=False)

    # Render 2-column visual preview sheet of the beats + narration.
    with Image.open(frame_paths[0]) as sample:
        w0, h0 = sample.size
    tw = 280 if h0 > w0 else 440
    th = max(120, int(round(tw * h0 / max(w0, 1))))
    cap_h = 56
    pad = 12
    cols = min(2, len(beats))
    rows = math.ceil(len(beats) / cols)
    canvas = Image.new("RGB", (cols * tw + (cols + 1) * pad, rows * (th + cap_h) + (rows + 1) * pad), (20, 20, 20))
    draw = ImageDraw.Draw(canvas)
    f_badge = C.load_font(14, bold=True)
    f_cap = C.load_font(13, bold=False)
    wrap_chars = max(28, tw // 8)

    for idx, (beat, fpath) in enumerate(zip(beats, frame_paths)):
        r_idx, c_idx = divmod(idx, cols)
        x = pad + c_idx * (tw + pad)
        y = pad + r_idx * (th + cap_h + pad)
        with Image.open(fpath) as im:
            tile = im.convert("RGB").resize((tw, th), Image.Resampling.LANCZOS)
        canvas.paste(tile, (x, y))
        C.draw_badge(draw, (x + 6, y + 6), f"{beat['id']}  {C.fmt_ts(beat['t'])}", f_badge, bg=(139, 26, 43), fg=(255, 255, 255))
        wrapped = textwrap.wrap(beat["narration"], width=wrap_chars)[:2]
        for li, line in enumerate(wrapped):
            draw.text((x + 2, y + th + 6 + li * 18), line, font=f_cap, fill=(225, 225, 225))

    preview_jpg = os.path.join(test_dir, "beats-preview.jpg")
    canvas.save(preview_jpg, quality=88)
    return beats_json, preview_jpg, beats


def _apply_measured_metrics(style, td, ms, snd):
    """Populate/refresh all measured metrics inside a style dict."""
    meta = td.get("video") or {}
    td_sound = td.get("sound") or {}
    cuts = ms.get("cuts") or {}
    motion = ms.get("motion") or {}
    pal = ms.get("palette") or {}
    words = ms.get("words") or {}
    td_script = td.get("script") or {}

    dur = meta.get("duration") or ms.get("duration_sec") or 0
    aspect = td.get("aspect_ratio") or ms.get("aspect_ratio")
    fmt_kind = td.get("format_kind") or ("vertical" if aspect == "9:16" else ("short" if dur <= 90 else "long"))

    info = style.setdefault("info", {})
    if td.get("title"):
        info["title"] = td["title"]
    if td.get("uploader"):
        info["creator"] = td["uploader"]
    if td.get("source"):
        info["url"] = td["source"]
    info["duration_sec"] = round(float(dur), 1) if dur else 0
    info["format"] = fmt_kind
    inspected = []
    if td:
        inspected.append(f"teardown: {td.get('frames', 0)} frames @ {td.get('sps', '?')} fps, {meta.get('width', '?')}x{meta.get('height', '?')}")
    if cuts:
        inspected.append(f"measure: {cuts.get('count', 0)} cuts, {motion.get('samples', 0)} motion-sampled shots")
    if snd:
        inspected.append(f"sfx_lab: {snd.get('event_count', 0)} stereo events (stereo={snd.get('stereo_separation')})")
    if inspected:
        info["inspected"] = inspected

    D = style.setdefault("direction", {})
    if aspect in ("9:16", "16:9"):
        D["default_aspect"] = aspect

    wpm = words.get("wpm") or td_script.get("wpm")
    if wpm:
        D.setdefault("narration", {})["wpm"] = {
            "rule": "Speaking speed",
            "value": int(round(wpm)),
            "basis": "measured",
            "proof": [f"reva measure: {words.get('count') or td_script.get('words', 0)} words / {dur} s"],
        }

    SM = D.setdefault("scene_maker", {})
    if cuts:
        SM["avg_shot_sec"] = {
            "rule": "Average picture length",
            "value": cuts["median_sec"],
            "basis": "measured",
            "proof": [f"measure.py: {cuts['count']} cuts, median {cuts['median_sec']} s, p10 {cuts['p10_sec']}, p90 {cuts['p90_sec']}, max {cuts['max_sec']}"],
        }
        smin = max(1.0, round(cuts["p10_sec"], 1))
        smax = max(smin, round(cuts["p90_sec"], 1))
        SM["shot_length_sec"] = {"min": smin, "max": smax, "mode": "flexible"}
        SM["cuts_per_min"] = {
            "rule": "Picture changes per minute",
            "value": cuts["per_min"],
            "basis": "measured",
            "proof": [f"thirds {'/'.join(map(str, cuts.get('thirds', [])))}"],
        }
    if motion.get("max_static_sec") is not None:
        SM["max_static_sec"] = {
            "value": motion["max_static_sec"],
            "basis": "measured",
            "proof": [f"longest still shot {motion['max_static_sec']} s"],
        }
    if motion:
        still_pct = round(motion.get("still_share", 0) * 100)
        move_pct = round(motion.get("moving_share", 0) * 100)
        SM["motion"] = [
            {
                "rule": "Measured still vs moving shot ratio",
                "value": f"{still_pct}% still / {move_pct}% moving",
                "basis": "measured",
                "proof": [f"{motion.get('still', 0)} still, {motion.get('subtle', 0)} subtle, {motion.get('moving', 0)} moving of {motion.get('samples', 0)} sampled"],
            }
        ]
        D["resource_mix"] = {
            "dominant": "generated-image" if still_pct >= move_pct else "generated-video",
            "types": [
                {
                    "resource": "generated-image",
                    "used_for": "still narrative & diagram shots",
                    "share": f"{still_pct}%",
                    "basis": "measured",
                    "proof": [f"reva measure: {motion.get('still', 0)}/{motion.get('samples', 0)} still"],
                },
                {
                    "resource": "generated-video",
                    "used_for": "subtle or moving action shots",
                    "share": f"{move_pct}%",
                    "basis": "measured",
                    "proof": [f"reva measure: {motion.get('subtle', 0) + motion.get('moving', 0)}/{motion.get('samples', 0)} moving"],
                },
            ],
        }

    sound_rules = []
    if td_sound.get("lufs") is not None:
        sound_rules.append({
            "rule": "Final mix level",
            "value": f"{td_sound['lufs']} LUFS, peak {td_sound.get('true_peak')} dBTP",
            "basis": "measured",
            "proof": ["teardown.json"],
        })
    if snd and snd.get("stereo_separation"):
        sound_rules.append({
            "rule": "Stereo SFX cadence (centered voice removed)",
            "value": f"{snd.get('events_per_min')}/min",
            "basis": "measured",
            "proof": [f"sfx_lab events: {snd.get('event_count')} in {snd.get('duration_sec')} s"],
        })
    if sound_rules:
        SM["sound"] = sound_rules

    L = style.setdefault("look", {})
    if pal.get("main"):
        L["colors"] = {
            "palette": [x["hex"].upper() for x in pal["main"]],
            "accent": (pal["accents"][0]["hex"].upper() if pal.get("accents") else pal["main"][0]["hex"].upper()),
        }
    if motion.get("samples"):
        L.setdefault("can_do", {})["camera_moves"] = motion.get("still_share", 1.0) < 0.8


def scaffold_style(study_dir, style_id, app_dir=None, name=None, framing=None, refresh_metrics=False):
    """Create (or refresh metrics in) style/<id>/<id>.style.json + <id>.md."""
    clean_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", style_id.strip()).strip("-")
    if not clean_id:
        raise ValueError("style id must contain alphanumeric characters")

    td = _read_json(os.path.join(study_dir, "ref", "teardown.json")) or {}
    ms = _read_json(os.path.join(study_dir, "ref", "measure.json")) or {}
    snd = _read_json(os.path.join(study_dir, "ref", "sound.json")) or {}

    style_dir = os.path.join(study_dir, "style", clean_id)
    os.makedirs(style_dir, exist_ok=True)
    json_path = os.path.join(style_dir, f"{clean_id}.style.json")
    md_path = os.path.join(style_dir, f"{clean_id}.md")

    if refresh_metrics and os.path.exists(json_path):
        style = _read_json(json_path)
    else:
        tmpl_path = os.path.join(app_dir, "docs", "reference-style.template.json") if app_dir else None
        base = _read_json(tmpl_path) if tmpl_path and os.path.exists(tmpl_path) else copy.deepcopy(_BUILTIN_TEMPLATE)
        base.pop("_how_to", None)
        style = base
        style["id"] = clean_id
        style["name"] = name or td.get("title") or clean_id
        style.setdefault("look", {})["look_id"] = clean_id
        if framing in ("flat", "film"):
            style["look"]["framing"] = framing
        elif ms.get("motion", {}).get("samples"):
            style["look"]["framing"] = "film" if ms["motion"].get("moving_share", 0) > 0.5 else "flat"

    _apply_measured_metrics(style, td, ms, snd)

    # Always write UTF-8 WITHOUT BOM (style-check.js rejects 0xFEFF).
    with open(json_path, "w", encoding="utf-8") as fp:
        json.dump(style, fp, indent=2, ensure_ascii=False)
        fp.write("\n")

    placeholders = find_placeholders(style)
    D = style.get("direction", {})
    L = style.get("look", {})
    SM = D.get("scene_maker", {})
    md_lines = [
        f"# Style: {style.get('name', clean_id)} (`{clean_id}`)",
        "",
        f"- **Reference:** {style.get('info', {}).get('title', '?')} ({style.get('info', {}).get('url', '?')})",
        f"- **Format / Aspect:** `{style.get('info', {}).get('format', '?')}` / `{D.get('default_aspect', '?')}` | `{style.get('info', {}).get('duration_sec', '?')} s`",
        f"- **WPM:** {D.get('narration', {}).get('wpm', {}).get('value', '?')}",
        f"- **Avg Shot / Range:** {SM.get('avg_shot_sec', {}).get('value', '?')} s | range {SM.get('shot_length_sec', {})}",
        f"- **Colors:** `{L.get('colors', {})}`",
        f"- **Framing / Camera Moves:** `{L.get('framing', 'flat')}` | `camera_moves={L.get('can_do', {}).get('camera_moves')}`",
        "",
        "## Purpose",
        str(D.get("purpose", "")),
        "",
        "## Picture Rules",
        *[f"- {r}" for r in (L.get("picture_rules") or [])],
        "",
        "## Remaining Placeholders Before `reva deliver`",
        f"- Count: **{len(placeholders)}**" + (" (ready for delivery check)" if not placeholders else ""),
        *[f"- `{p}`: {v}" for p, v in placeholders[:15]],
    ]
    with open(md_path, "w", encoding="utf-8") as fp:
        fp.write("\n".join(md_lines) + "\n")

    return json_path, md_path


def export_skill(study_dir, study_data=None, out_path=None):
    """Export a proven, evidence-backed skill brief ready for Branch 1 (video-making-skills)."""
    study = study_data or _read_json(os.path.join(study_dir, "study.json")) or {}
    td = _read_json(os.path.join(study_dir, "ref", "teardown.json")) or {}
    ms = _read_json(os.path.join(study_dir, "ref", "measure.json")) or {}
    snd = _read_json(os.path.join(study_dir, "ref", "sound.json")) or {}

    name = study.get("study") or os.path.basename(os.path.abspath(study_dir))
    techs = study.get("techniques") or {}
    deliveries = study.get("deliveries") or {}

    verified_count = 0
    compared_count = 0
    tech_sections = []
    gaps = []

    for k, t in techs.items():
        t_dict = t if isinstance(t, dict) else {"status": "note", "note": str(t)}
        status = t_dict.get("status", "unknown")
        cmp_path = os.path.join(study_dir, k, "compare.jpg")
        notes_path = os.path.join(study_dir, k, "notes.md")
        has_cmp = os.path.exists(cmp_path)

        if status == "verified":
            badge = "VERIFIED"
            verified_count += 1
        elif status == "compared" or has_cmp:
            badge = "COMPARED"
            compared_count += 1
            gaps.append(f"Technique `{k}` has `compare.jpg` but is not marked verified yet (`reva verify {name} {k}`).")
        else:
            badge = "UNVERIFIED"
            gaps.append(f"Technique `{k}` needs rebuild + side-by-side comparison (`reva compare {name} {k} --mine ...`).")

        notes_body = "(notes.md not found)"
        if os.path.exists(notes_path):
            with open(notes_path, encoding="utf-8") as fp:
                notes_body = fp.read().strip()

        cmp_files = sorted(glob.glob(os.path.join(study_dir, k, "compare*.jpg")))
        tech_sections.append({
            "name": k,
            "badge": badge,
            "range": f"{t_dict.get('from', '?')}-{t_dict.get('to', '?')} s",
            "verify_note": t_dict.get("verify_note", ""),
            "reused_from": t_dict.get("reused_from", ""),
            "winning_engine": t_dict.get("winning_engine", ""),
            "rejected_engines": t_dict.get("rejected_engines") or [],
            "promoted_pattern": t_dict.get("promoted_pattern", ""),
            "compare_files": [os.path.basename(c) for c in cmp_files],
            "has_cmp": has_cmp,
            "notes": notes_body,
        })

    if not techs:
        gaps.append(f"No isolated techniques measured yet (`reva add {name} <technique> --from <s> --to <s>`).")
    if not ms:
        gaps.append(f"Run `reva measure {name}` to lock pacing, motion ratio, and color palette.")
    if not snd:
        gaps.append(f"Run `reva sound {name}` to inspect stereo SFX cadence.")

    meta = td.get("video") or {}
    cuts = ms.get("cuts") or {}
    motion = ms.get("motion") or {}
    pal = ms.get("palette") or {}
    td_sound = td.get("sound") or {}

    lines = [
        f"# Branch 1 Skill Export: `{name}`",
        "",
        "## Proof Summary",
        f"- **Reference:** {td.get('title') or study.get('source', '?')} ({meta.get('width', '?')}x{meta.get('height', '?')}, {meta.get('fps', '?')} fps, {meta.get('duration', '?')} s)",
        f"- **Techniques:** {len(techs)} total | **{verified_count} VERIFIED** | {compared_count} COMPARED",
        f"- **App Style Deliveries:** {len(deliveries)}" + (
            " (" + ", ".join(f"`{sid}`={d.get('status')}" for sid, d in deliveries.items()) + ")"
            if deliveries else " (none yet)"
        ),
        "",
        "## Measured Specification",
        f"- **Pacing:** {cuts.get('count', '?')} cuts ({cuts.get('per_min', '?')}/min) | median shot `{cuts.get('median_sec', '?')} s` | p10–p90 `{cuts.get('p10_sec', '?')}-{cuts.get('p90_sec', '?')} s`",
        f"- **Motion:** {round(motion.get('still_share', 0) * 100)}% still / {round(motion.get('moving_share', 0) * 100)}% moving | max static `{motion.get('max_static_sec', '?')} s`",
        f"- **Voice & Mix:** {study.get('wpm', '?')} WPM | {td_sound.get('lufs', '?')} LUFS | peak {td_sound.get('true_peak', '?')} dBTP",
    ]
    if pal.get("main"):
        lines.append("- **Palette:** " + ", ".join(f"`{c['hex']}` ({c['share']}%)" for c in pal["main"]))
    if pal.get("accents"):
        lines.append("- **Accents:** " + ", ".join(f"`{c['hex']}` ({c['share']}%)" for c in pal["accents"]))
    if snd.get("stereo_separation"):
        lines.append(f"- **Stereo SFX:** {snd.get('events_per_min')}/min across {snd.get('event_count')} events")

    lines += ["", "## Technique Notes & Verification"]
    if tech_sections:
        for ts in tech_sections:
            lines.append(f"### [{ts['badge']}] {ts['name']} ({ts['range']})")
            if ts.get("reused_from"):
                lines.append(f"- **Reused baseline pattern:** `{ts['reused_from']}`")
            if ts.get("winning_engine"):
                lines.append(f"- **Winning engine:** `{ts['winning_engine']}`")
            if ts.get("rejected_engines"):
                rej_txt = ", ".join(
                    f"`{r.get('engine')}` ({r.get('reason')})" if isinstance(r, dict) else f"`{r}`"
                    for r in ts["rejected_engines"]
                )
                lines.append(f"- **Rejected engines:** {rej_txt}")
            if ts.get("promoted_pattern"):
                lines.append(f"- **Promoted to library:** `{ts['promoted_pattern']}`")
            if ts["verify_note"]:
                lines.append(f"- **Verification note:** {ts['verify_note']}")
            if ts.get("compare_files"):
                lines.append("- **Compare sheets:** " + ", ".join(f"`{ts['name']}/{f}`" for f in ts["compare_files"]))
            else:
                lines.append("- **Compare sheet:** missing")
            lines += ["", "```markdown", ts["notes"], "```", ""]
    else:
        lines.append("- No techniques added yet.")

    lines += ["", "## Gaps Before Promoting to Branch 1"]
    if gaps:
        lines += [f"- [ ] {g}" for g in gaps]
    else:
        lines.append("- [x] All techniques measured, compared, and verified with real outputs.")

    dst = out_path or os.path.join(study_dir, "skill-export.md")
    with open(dst, "w", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")
    return dst
