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
    from . import style_kit
except ImportError:
    import _common as C
    import style_kit


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
    st = {
        "study": study,
        "source": source,
        "title": td.get("title"),
        "duration": td["video"]["duration"],
        "aspect": td.get("aspect"),
        "aspect_ratio": td.get("aspect_ratio"),
        "lufs": td["sound"]["lufs"],
        "wpm": td["script"]["wpm"],
        "techniques": prev.get("techniques", {}),
        "deliveries": prev.get("deliveries", {}),
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
