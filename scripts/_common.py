#!/usr/bin/env python3
"""Shared path, FFmpeg, subtitle, color, and Pillow utilities for REVA."""
import colorsys
import json
import os
import re
import shutil
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LEGACY_APP = r"C:\Users\Ahmad\OneDrive\Documents\A AGENTIC AI WORKS\Agentic AI\Automated Lunch Free"


def workspace_root(override=None):
    """Return the active REVA study workspace root directory."""
    raw = override or os.environ.get("REVA_WORKSPACE") or os.environ.get("REVA_ROOT")
    if raw:
        return os.path.abspath(os.path.expanduser(raw))
    return os.path.join(REPO_ROOT, "studies")


def lab_dir(override=None):
    """Return the active REVA Engineering Lab root directory."""
    raw = override or os.environ.get("REVA_LAB_DIR")
    if raw:
        return os.path.abspath(os.path.expanduser(raw))
    return os.path.join(REPO_ROOT, "lab")


def find_branch1_roots():
    """Return existing directories that hold Branch 1 video-making skills."""
    home = os.path.expanduser("~")
    parent = os.path.dirname(REPO_ROOT)
    candidates = []
    env_b1 = os.environ.get("REVA_BRANCH1")
    if env_b1:
        for part in env_b1.split(os.pathsep):
            if part.strip():
                candidates.append(os.path.abspath(os.path.expanduser(part.strip())))
    candidates.extend([
        os.path.join(parent, "video-making-skills"),
        os.path.join(home, ".kiro", "crew", "skills"),
        os.path.join(home, ".codex", "skills"),
        os.path.join(home, ".gemini", "config", "plugins"),
    ])
    seen = set()
    roots = []
    for cand in candidates:
        norm = os.path.abspath(cand)
        key = norm.lower()
        if key not in seen and os.path.isdir(norm):
            seen.add(key)
            roots.append(norm)
    return roots


def find_skill_dir(skill_names):
    """Locate Branch 1 skill folders across discovered skill roots."""
    if isinstance(skill_names, str):
        skill_names = [skill_names]
    found = {}
    roots = find_branch1_roots()
    for sname in skill_names:
        for root in roots:
            direct = os.path.join(root, sname)
            if os.path.isdir(direct):
                found[sname] = direct
                break
            if os.path.basename(root).lower() == "plugins":
                for entry in sorted(os.listdir(root)):
                    nested = os.path.join(root, entry, "skills", sname)
                    if os.path.isdir(nested):
                        found[sname] = nested
                        break
                if sname in found:
                    break
    return found


def is_app_dir(path):
    """Return True if path looks like an Automated-Lunch-Free checkout."""
    if not path:
        return False
    return os.path.isdir(os.path.join(path, "styles")) and os.path.exists(
        os.path.join(path, "scripts", "style-check.js")
    )


def find_app(override=None):
    """Locate Automated-Lunch-Free via override, REVA_APP, or sibling folders."""
    if override:
        p = os.path.abspath(os.path.expanduser(override))
        return p if is_app_dir(p) else None
    env_app = os.environ.get("REVA_APP")
    if env_app:
        p = os.path.abspath(os.path.expanduser(env_app))
        return p if is_app_dir(p) else None
    parent = os.path.dirname(REPO_ROOT)
    candidates = [
        os.path.join(parent, "Automated-Lunch-Free"),
        os.path.join(parent, "Automated Lunch Free"),
        _LEGACY_APP,
    ]
    for cand in candidates:
        if is_app_dir(cand):
            return os.path.abspath(cand)
    return None


def _find_bin(name, env_key, default_win):
    candidates = [
        os.environ.get(env_key),
        default_win,
        shutil.which(name),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    raise RuntimeError(f"{name} not found (install {name} on PATH or set {env_key})")


def find_ffmpeg():
    """Return path to ffmpeg executable or raise RuntimeError."""
    return _find_bin("ffmpeg", "REVA_FFMPEG", r"C:\ffmpeg\bin\ffmpeg.exe")


def find_ffprobe():
    """Return path to ffprobe executable or raise RuntimeError."""
    return _find_bin("ffprobe", "REVA_FFPROBE", r"C:\ffmpeg\bin\ffprobe.exe")


def run_cmd(cmd, **kw):
    """Run subprocess with UTF-8 output decoding."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        **kw,
    )


def fmt_ts(sec):
    """Format seconds as MM:SS (or H:MM:SS for >= 1h)."""
    total = max(0, int(float(sec) + 1e-3))
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def norm_ts(raw):
    """Normalize a timestamp string like ' 44.0 ' -> '44'."""
    val = float(str(raw).strip())
    if abs(val) < 1e-6:
        return "0"
    txt = f"{val:.3f}".rstrip("0").rstrip(".")
    return txt or "0"


def ts_token(raw):
    """Normalize timestamp into filename-safe token ('44.5' -> '44_5')."""
    return norm_ts(raw).replace(".", "_")


def probe_media(path):
    """Return video & audio stream metadata via ffprobe."""
    r = run_cmd([
        find_ffprobe(),
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        path,
    ])
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip() or f"ffprobe failed on {path}")
    data = json.loads(r.stdout or "{}")
    fmt = data.get("format", {})
    dur = float(fmt.get("duration", 0) or 0)
    w = h = fps = None
    has_audio = False
    audio_channels = 0
    audio_sr = None

    for s in data.get("streams", []):
        ctype = s.get("codec_type")
        if ctype == "video" and w is None:
            w, h = s.get("width"), s.get("height")
            if not dur and s.get("duration"):
                try:
                    dur = float(s["duration"])
                except (TypeError, ValueError):
                    pass
            fr = s.get("avg_frame_rate") or s.get("r_frame_rate") or "0/1"
            try:
                num, den = fr.split("/")
                fps = round(float(num) / float(den), 3) if float(den) else None
            except Exception:
                fps = None
        elif ctype == "audio" and not has_audio:
            has_audio = True
            audio_channels = int(s.get("channels") or 0)
            try:
                audio_sr = int(s.get("sample_rate")) if s.get("sample_rate") else None
            except (TypeError, ValueError):
                audio_sr = None

    aspect_ratio = None
    aspect_label = None
    format_kind = "long" if dur > 90 else "short"
    if w and h:
        if h > w:
            aspect_ratio = "9:16"
            aspect_label = f"{w}x{h} (vertical)"
            format_kind = "vertical"
        elif w == h:
            aspect_ratio = "1:1"
            aspect_label = f"{w}x{h} (square)"
        else:
            aspect_ratio = "16:9"
            aspect_label = f"{w}x{h} (wide)"

    return {
        "duration": round(dur, 2),
        "width": w,
        "height": h,
        "fps": fps,
        "aspect_ratio": aspect_ratio,
        "aspect_label": aspect_label,
        "format_kind": format_kind,
        "has_audio": has_audio,
        "audio_channels": audio_channels,
        "audio_sample_rate": audio_sr,
    }


def detect_cuts(video, threshold=0.30, start=None, dur=None, min_gap=0.0):
    """Detect scene cuts via ffmpeg showinfo on stderr (safe for Windows paths)."""
    ff = find_ffmpeg()
    vf_parts = []
    if start is not None or dur is not None:
        t0 = float(start or 0.0)
        if dur is not None:
            vf_parts.append(f"trim=start={t0}:duration={float(dur)}")
        else:
            vf_parts.append(f"trim=start={t0}")
    vf_parts.append(f"select='gt(scene,{threshold})'")
    vf_parts.append("showinfo")
    cmd = [ff, "-hide_banner", "-i", video, "-vf", ",".join(vf_parts), "-an", "-f", "null", "-"]
    r = run_cmd(cmd)
    if r.returncode != 0 and "pts_time:" not in r.stderr:
        raise RuntimeError(r.stderr[-800:] or f"ffmpeg scene detection failed on {video}")
    raw = sorted({round(float(m), 3) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)})
    if not min_gap or min_gap <= 0:
        return raw
    kept = []
    for t in raw:
        if not kept or (t - kept[-1]) >= min_gap:
            kept.append(t)
    return kept


def pick_subtitle_file(ref_dir, name="ref"):
    """Select best matching subtitle file (.vtt or .srt) in ref_dir."""
    if not os.path.isdir(ref_dir):
        return None
    files = sorted(
        os.path.join(ref_dir, f)
        for f in os.listdir(ref_dir)
        if f.startswith(name) and f.lower().endswith((".vtt", ".srt"))
    )
    if not files:
        return None

    lang = ""
    for f in os.listdir(ref_dir):
        if f.endswith(".info.json"):
            try:
                with open(os.path.join(ref_dir, f), encoding="utf-8") as fp:
                    lang = (json.load(fp).get("language") or "").split("-")[0].lower()
                if lang:
                    break
            except Exception:
                pass

    if lang:
        lang_hits = [f for f in files if re.search(rf"\.{re.escape(lang)}(?:-orig)?\.(vtt|srt)$", f, re.I)]
        if lang_hits:
            return lang_hits[0]
    orig_hits = [f for f in files if "-orig." in os.path.basename(f).lower()]
    if orig_hits:
        return orig_hits[0]
    common_hits = [f for f in files if re.search(r"\.(en|id)\.(vtt|srt)$", f, re.I)]
    if common_hits:
        return common_hits[0]
    return files[0]


_STAMP_RE = re.compile(
    r"(?:(\d+):)?(\d{2}):(\d{2})[.,](\d+)\s*-->\s*(?:(\d+):)?(\d{2}):(\d{2})[.,](\d+)"
)


def _to_sec(h, m, s, ms):
    ms_val = int(ms.ljust(3, "0")[:3])
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + ms_val / 1000.0


def parse_subtitles(path):
    """Parse .srt or .vtt (including rolling YouTube auto-captions) into clean cues."""
    with open(path, encoding="utf-8", errors="replace") as fp:
        raw = fp.read().lstrip("\ufeff").replace("\r", "")

    blocks = re.split(r"\n\s*\n", raw)
    cues = []
    last_line = None

    for block in blocks:
        rows = [r.strip() for r in block.split("\n") if r.strip()]
        if not rows:
            continue
        head = rows[0].upper()
        if head.startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue
        m = next((_STAMP_RE.search(r) for r in rows if _STAMP_RE.search(r)), None)
        if not m:
            continue
        g = m.groups()
        t0 = _to_sec(g[0], g[1], g[2], g[3])
        t1 = _to_sec(g[4], g[5], g[6], g[7])

        body = []
        for r in rows:
            if _STAMP_RE.search(r) or r.isdigit():
                continue
            cleaned = re.sub(r"<[^>]+>", "", r)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if cleaned:
                body.append(cleaned)
        if not body:
            continue

        # Handle progressive word-by-word captions vs 2-line rolling captions.
        kept_lines = []
        for ln in body:
            if last_line and ln == last_line:
                continue
            if last_line and ln.startswith(last_line + " ") and cues and (t0 - cues[-1]["start"]) < 5.0:
                # Progressive extension of the previous cue line: update in place.
                cues[-1]["text"] = ln
                cues[-1]["end"] = round(max(cues[-1]["end"], t1), 3)
                last_line = ln
                continue
            kept_lines.append(ln)
            last_line = ln

        if kept_lines:
            text_piece = " ".join(kept_lines)
            if cues and text_piece == cues[-1]["text"]:
                cues[-1]["end"] = round(max(cues[-1]["end"], t1), 3)
            else:
                cues.append({
                    "start": round(t0, 3),
                    "end": round(t1, 3),
                    "text": text_piece,
                })

    full_text = " ".join(c["text"] for c in cues).strip()
    words = len(full_text.split()) if full_text else 0
    talk_span = (cues[-1]["end"] - cues[0]["start"]) if cues else 0.0
    return {
        "cues": cues,
        "words": words,
        "text": full_text,
        "talk_span_sec": round(max(0.0, talk_span), 2),
    }


def narration_at(cues, t, window=3.5):
    """Return spoken line(s) overlapping [t - window/2, t + window/2], or nearest cue."""
    if not cues:
        return ""
    half = window / 2.0
    lo, hi = t - half, t + half
    hits = [c for c in cues if c["end"] >= lo and c["start"] <= hi]
    if not hits:
        nearest = min(cues, key=lambda c: abs((c["start"] + c["end"]) / 2.0 - t))
        mid = (nearest["start"] + nearest["end"]) / 2.0
        if abs(mid - t) <= window * 2.5:
            hits = [nearest]
    seen = []
    for c in hits:
        if not seen or c["text"] != seen[-1]:
            seen.append(c["text"])
    return " ".join(seen).strip()


def pixels_of(im):
    """Pillow 10-14+ compatible flat pixel list."""
    fn = getattr(im, "get_flattened_data", None) or im.getdata
    return list(fn())


def load_font(size=16, bold=False):
    """Load a crisp Windows TTF font with fallback to Pillow default."""
    from PIL import ImageFont

    names = (
        ["segoeuib.ttf", "arialbd.ttf", "consolab.ttf"]
        if bold
        else ["segoeui.ttf", "arial.ttf", "consola.ttf"]
    )
    for name in names:
        p = os.path.join(r"C:\Windows\Fonts", name)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def draw_badge(draw, xy, text, font, bg=(18, 18, 18), fg=(255, 255, 255), pad_x=6, pad_y=3):
    """Draw a readable text badge at (x, y)."""
    x, y = xy
    box = draw.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.rectangle([x, y, x + tw + pad_x * 2, y + th + pad_y * 2], fill=bg)
    draw.text((x + pad_x - box[0], y + pad_y - box[1]), text, font=font, fill=fg)


def extract_palette(image_paths, n=6):
    """Extract main hex colors and saturated accent hex colors from 1+ images."""
    from PIL import Image

    if isinstance(image_paths, str):
        image_paths = [image_paths]
    thumbs = []
    hi_samples = []
    for p in image_paths:
        if not p or not os.path.exists(p):
            continue
        with Image.open(p) as im:
            rgb = im.convert("RGB")
            thumbs.append(rgb.resize((240, 135)))
            hi_samples.append(rgb.resize((480, 270)))
    if not thumbs:
        return {"main": [], "accents": []}

    comp_lo = Image.new("RGB", (240 * len(thumbs), 135))
    for i, t in enumerate(thumbs):
        comp_lo.paste(t, (i * 240, 0))

    k = max(n * 4, 16)
    q = comp_lo.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: k * 3]
    counts = sorted(q.getcolors() or [], reverse=True)
    total = sum(c for c, _ in counts) or 1

    main = []
    seen_rgb = []
    for c, idx in counts:
        r, g, b = pal[idx * 3: idx * 3 + 3]
        if any(abs(r - sr) + abs(g - sg) + abs(b - sb) < 28 for sr, sg, sb in seen_rgb):
            continue
        seen_rgb.append((r, g, b))
        main.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "share": round(100.0 * c / total, 1)})
        if len(main) >= n:
            break

    # Scan full pixels for saturated accents that small median-cut areas drop.
    buckets = {}
    total_px = 0
    for hi in hi_samples:
        px = pixels_of(hi)
        total_px += len(px)
        for r, g, b in px:
            _, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
            if s > 0.35 and 0.12 < l < 0.85:
                key = (r // 24, g // 24, b // 24)
                cnt, sr, sg, sb = buckets.get(key, (0, 0, 0, 0))
                buckets[key] = (cnt + 1, sr + r, sg + g, sb + b)

    accents = []
    accent_rgb = []
    for cnt, sr, sg, sb in sorted(buckets.values(), reverse=True):
        if not total_px or cnt / total_px < 0.0005:
            break
        r, g, b = sr // cnt, sg // cnt, sb // cnt
        if any(abs(r - ar) + abs(g - ag) + abs(b - ab) < 42 for ar, ag, ab in accent_rgb):
            continue
        accent_rgb.append((r, g, b))
        accents.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "share": round(100.0 * cnt / total_px, 2)})
        if len(accents) >= 4:
            break

    return {"main": main, "accents": accents}
