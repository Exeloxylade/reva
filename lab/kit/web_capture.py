#!/usr/bin/env python3
"""web_capture.py - Shared REVA Lab headless browser kit for JS DOM rendering, screenshots, and asset discovery.

Uses the local Chromium/Edge executable via `--headless=new` (`--dump-dom` + `--screenshot`)
and NEVER bypasses CAPTCHA or anti-bot walls (returns blocked_by_gate=True cleanly).
"""
import html.parser
import os
import re
import shutil
import subprocess
import tempfile
import urllib.parse

_GATE_MARKERS = (
    ("cf-challenge", "Cloudflare challenge"),
    ("cf_chl_opt", "Cloudflare challenge"),
    ("verify you are human", "Human verification gate"),
    ("are you a robot", "Bot verification gate"),
    ("i am not a robot", "CAPTCHA challenge"),
    ("g-recaptcha", "reCAPTCHA gate"),
    ("hcaptcha", "hCaptcha gate"),
    ("cf-turnstile", "Cloudflare Turnstile gate"),
    ("attention required! | cloudflare", "Cloudflare block page"),
)

_MEDIA_EXTS = {
    "images": (".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif"),
    "documents": (".pdf",),
    "videos": (".mp4", ".webm", ".mov", ".m4v"),
    "models3d": (".glb", ".gltf", ".obj", ".stl", ".fbx"),
    "datasets": (".csv", ".json", ".geojson", ".tsv", ".xlsx"),
    "audio": (".mp3", ".wav", ".ogg", ".flac", ".m4a"),
}


def find_browser():
    """Locate Edge/Chrome binary on this machine (or REVA_BROWSER override)."""
    cands = [
        os.environ.get("REVA_BROWSER"),
        shutil.which("msedge"),
        shutil.which("msedge.exe"),
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        shutil.which("google-chrome"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in cands:
        if c and os.path.exists(c):
            return os.path.abspath(c)
    return None


def detect_captcha_or_gate(html_text):
    """Return gate reason string if HTML appears gated by a CAPTCHA/anti-bot wall, else ''."""
    low = (html_text or "").lower()
    if not low:
        return ""
    for needle, reason in _GATE_MARKERS:
        if needle in low:
            return reason
    if "<title>just a moment..." in low or "checking your browser before accessing" in low:
        return "Cloudflare browser check"
    return ""


class _LinkHarvester(html.parser.HTMLParser):
    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.links = {k: [] for k in _MEDIA_EXTS}
        self._seen = set()

    def _classify(self, raw_url):
        if not raw_url:
            return
        u = raw_url.strip()
        if not u or u.startswith(("data:", "javascript:", "mailto:", "#")):
            return
        abs_u = urllib.parse.urljoin(self.base_url, u)
        path = urllib.parse.urlparse(abs_u).path.lower()
        for bucket, exts in _MEDIA_EXTS.items():
            if any(path.endswith(ext) for ext in exts):
                if abs_u not in self._seen:
                    self._seen.add(abs_u)
                    self.links[bucket].append(abs_u)
                return

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        ad = dict(attrs)
        if t in ("img", "source", "video", "audio", "embed"):
            self._classify(ad.get("src"))
            srcset = ad.get("srcset") or ""
            if srcset:
                first = srcset.split(",")[0].strip().split(" ")[0]
                self._classify(first)
        elif t in ("a", "link"):
            self._classify(ad.get("href"))


def extract_media_links(html_text, base_url=""):
    """Extract categorized media, document, 3D model, dataset, and audio links from rendered HTML."""
    p = _LinkHarvester(base_url or "")
    try:
        p.feed(html_text or "")
        p.close()
    except Exception:
        pass
    return {k: v[:25] for k, v in p.links.items()}


def browse_url(
    url,
    *,
    out_dir=None,
    screenshot=False,
    width=1440,
    height=1600,
    wait_ms=4000,
    slug="page",
):
    """Render URL with headless Edge/Chrome, return rendered DOM HTML, optional screenshot PNG, and discovered assets."""
    target = (url or "").strip()
    if not target:
        raise ValueError("browse_url requires non-empty URL")
    browser = find_browser()
    if not browser:
        raise RuntimeError("no Edge/Chrome browser executable found for headless browse")

    safe_slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", slug or "page").strip("-").lower()[:48] or "page"
    prof = tempfile.mkdtemp(prefix="reva_browse_")
    common_flags = [
        browser,
        "--headless=new",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-gpu-sandbox",
        "--hide-scrollbars",
        f"--user-data-dir={prof}",
        f"--virtual-time-budget={int(wait_ms)}",
    ]

    try:
        dom_cmd = common_flags + ["--dump-dom", target]
        r_dom = subprocess.run(
            dom_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90
        )
        if r_dom.returncode != 0:
            return {
                "ok": False,
                "blocked_by_gate": False,
                "reason": (r_dom.stderr or r_dom.stdout or f"exit {r_dom.returncode}").strip()[-500:],
                "url": target,
                "dom_html": "",
                "screenshot_path": "",
                "media_links": {k: [] for k in _MEDIA_EXTS},
                "browser": browser,
            }

        dom_html = r_dom.stdout or ""
        gate = detect_captcha_or_gate(dom_html)
        if gate:
            return {
                "ok": False,
                "blocked_by_gate": True,
                "reason": gate,
                "url": target,
                "dom_html": "",
                "screenshot_path": "",
                "media_links": {k: [] for k in _MEDIA_EXTS},
                "browser": browser,
            }

        png_path = ""
        if screenshot:
            if not out_dir:
                raise ValueError("out_dir required when screenshot=True")
            os.makedirs(out_dir, exist_ok=True)
            png_path = os.path.join(out_dir, f"{safe_slug}.png")
            shot_cmd = common_flags + [
                "--force-device-scale-factor=1",
                f"--window-size={int(width)},{int(height)}",
                f"--screenshot={png_path}",
                target,
            ]
            r_shot = subprocess.run(
                shot_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=90
            )
            if r_shot.returncode != 0 or not os.path.exists(png_path):
                png_path = ""

        links = extract_media_links(dom_html, base_url=target)
        return {
            "ok": True,
            "blocked_by_gate": False,
            "reason": "",
            "url": target,
            "dom_html": dom_html,
            "screenshot_path": png_path,
            "media_links": links,
            "browser": browser,
        }
    finally:
        shutil.rmtree(prof, ignore_errors=True)
