#!/usr/bin/env python3
"""video-reverse: take any video apart and write down how it was made.

One command does the measurable half of a video teardown:
  1. get the video      (yt-dlp, if the input is a URL)
  2. find cuts          (ffmpeg scene-change detector -> shot list + lengths)
  3. grab frames        (1 frame/sec, tiled into contact sheets for the eye)
  4. read the words      (subtitles / auto-captions -> script.txt + words-per-min)
  5. measure the sound   (ffmpeg loudnorm + volumedetect -> LUFS, peak, music vs voice)
It writes everything into one output folder, then prints a short summary.
The HUMAN half (art style, colours, captions, camera) is done by reading the
contact sheets this makes -- see SKILL.md step 6.

Usage:
  python teardown.py <url-or-file> --out <dir> [--name ref] [--sps 1] [--sheet-cols 6]

Stdlib + ffmpeg (C:\\ffmpeg\\bin) + yt-dlp (python -m yt_dlp). No numpy.
"""
import argparse, json, math, os, re, subprocess, sys, shutil, glob

FFMPEG = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE = r"C:\ffmpeg\bin\ffprobe.exe"
if not os.path.exists(FFMPEG):
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"
    FFPROBE = shutil.which("ffprobe") or "ffprobe"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", **kw)


def is_url(s):
    return s.startswith("http://") or s.startswith("https://")


def download(url, outdir, name):
    """Download the video + subtitles with yt-dlp. Returns (mp4_path, info_dict)."""
    base = os.path.join(outdir, name)
    # -S res:1080 = up to 1080 on the SHORT side, so a vertical Short comes as 1080x1920 (not 608x1080)
    # subtitles: original-language tracks first; a 429 on a translated track must not stop the video download
    cmd = [sys.executable, "-m", "yt_dlp",
           "-f", "bv*+ba/b", "-S", "res:1080,fps",
           "--merge-output-format", "mp4",
           "--write-info-json",
           "--write-auto-subs", "--write-subs", "--sub-langs", ".*-orig,en,id",
           "--convert-subs", "srt", "--ignore-errors",
           "-o", base + ".%(ext)s", url]
    print("  downloading ...")
    r = run(cmd)
    mp4 = base + ".mp4"
    if not os.path.exists(mp4):
        hits = glob.glob(base + ".*")
        mp4 = next((h for h in hits if h.lower().endswith((".mp4", ".mkv", ".webm"))), None)
    if r.returncode != 0:
        if not mp4:
            print(r.stdout[-2000:]); print(r.stderr[-2000:])
            raise SystemExit("yt-dlp failed")
        print("  yt-dlp warned (often a subtitle track hit HTTP 429); the video itself downloaded")
    info = {}
    ij = base + ".info.json"
    if os.path.exists(ij):
        with open(ij, encoding="utf-8") as f:
            info = json.load(f)
    return mp4, info


def probe(mp4):
    r = run([FFPROBE, "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", mp4])
    data = json.loads(r.stdout or "{}")
    dur = float(data.get("format", {}).get("duration", 0) or 0)
    w = h = fps = None
    for s in data.get("streams", []):
        if s.get("codec_type") == "video":
            w, h = s.get("width"), s.get("height")
            fr = s.get("avg_frame_rate", "0/1")
            try:
                n, d = fr.split("/"); fps = round(float(n) / float(d), 3) if float(d) else None
            except Exception:
                fps = None
            break
    return {"duration": round(dur, 2), "width": w, "height": h, "fps": fps}


def find_cuts(mp4, outdir, threshold=0.30):
    """Scene-change times via ffmpeg select=gt(scene). Returns list of cut seconds."""
    logp = os.path.join(outdir, "_scene.txt")
    cmd = [FFMPEG, "-hide_banner", "-i", mp4,
           "-filter_complex", f"select='gt(scene,{threshold})',metadata=print:file={logp}",
           "-an", "-f", "null", "-"]
    run(cmd)
    cuts = []
    if os.path.exists(logp):
        with open(logp, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.search(r"pts_time:([0-9.]+)", line)
                if m:
                    cuts.append(round(float(m.group(1)), 3))
    return sorted(set(cuts))


def shot_list(cuts, dur):
    bounds = [0.0] + cuts + [dur]
    shots = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        if b - a < 0.15:
            continue
        shots.append({"i": len(shots) + 1, "start": round(a, 2),
                      "end": round(b, 2), "len": round(b - a, 2)})
    return shots


def grab_frames(mp4, outdir, sps=1):
    fdir = os.path.join(outdir, "frames")
    os.makedirs(fdir, exist_ok=True)
    for old in glob.glob(os.path.join(fdir, "*.jpg")):
        os.remove(old)
    cmd = [FFMPEG, "-hide_banner", "-i", mp4,
           "-vf", f"fps={sps},scale=480:-2",
           "-q:v", "3", os.path.join(fdir, "f%04d.jpg")]
    run(cmd)
    return sorted(glob.glob(os.path.join(fdir, "*.jpg")))


def contact_sheets(frames, outdir, cols=6, rows=5):
    """Tile frames into contact sheets of cols x rows for quick eyeballing."""
    if not frames:
        return []
    sheets = []
    per = cols * rows
    for s in range(0, len(frames), per):
        chunk = frames[s:s + per]
        lst = os.path.join(outdir, f"_sheet_{s // per}.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for c in chunk:
                f.write("file '" + c.replace("\\", "/") + "'\n")
        out = os.path.join(outdir, f"contact-sheet-{s // per + 1}.jpg")
        cmd = [FFMPEG, "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", lst,
               "-vf", f"scale=300:-2,tile={cols}x{rows}:padding=4:color=black",
               "-frames:v", "1", "-q:v", "3", out]
        run(cmd)
        if os.path.exists(out):
            sheets.append(out)
        if os.path.exists(lst):
            os.remove(lst)
    return sheets


def read_subs(outdir, name, info, dur):
    """Pull the script text + words-per-minute from any .srt yt-dlp wrote."""
    srts = glob.glob(os.path.join(outdir, name + "*.srt"))
    text = ""
    if srts:
        with open(srts[0], encoding="utf-8", errors="replace") as f:
            raw = f.read()
        lines = []
        for ln in raw.splitlines():
            ln = ln.strip()
            if not ln or ln.isdigit() or "-->" in ln:
                continue
            ln = re.sub(r"<[^>]+>", "", ln)
            lines.append(ln)
        seen, out = set(), []
        for ln in lines:
            if ln not in seen:
                out.append(ln); seen.add(ln)
        text = " ".join(out)
    words = len(text.split())
    wpm = round(words / (dur / 60), 1) if dur else 0
    if text:
        with open(os.path.join(outdir, "script.txt"), "w", encoding="utf-8") as f:
            f.write(text)
    return {"words": words, "wpm": wpm, "has_script": bool(text)}


def measure_sound(mp4, outdir):
    r = run([FFMPEG, "-hide_banner", "-i", mp4, "-af", "volumedetect",
             "-f", "null", "-"])
    log = r.stderr
    mean = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", log)
    peak = re.search(r"max_volume:\s*(-?[0-9.]+) dB", log)
    lufs = tp = None
    r2 = run([FFMPEG, "-hide_banner", "-i", mp4,
              "-af", "loudnorm=print_format=json", "-f", "null", "-"])
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", r2.stderr, re.S)
    if m:
        try:
            j = json.loads(m.group(0))
            lufs = j.get("input_i"); tp = j.get("input_tp")
        except Exception:
            pass
    return {"mean_db": mean.group(1) if mean else None,
            "peak_db": peak.group(1) if peak else None,
            "lufs": lufs, "true_peak": tp}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="video URL or local file path")
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="ref")
    ap.add_argument("--sps", type=float, default=1.0, help="frames grabbed per second")
    ap.add_argument("--sheet-cols", type=int, default=6)
    ap.add_argument("--sheet-rows", type=int, default=5)
    ap.add_argument("--scene", type=float, default=0.30, help="cut sensitivity 0-1")
    a = ap.parse_args()

    os.makedirs(a.out, exist_ok=True)
    info = {}
    if is_url(a.input):
        mp4, info = download(a.input, a.out, a.name)
    else:
        mp4 = a.input
        dst = os.path.join(a.out, a.name + os.path.splitext(mp4)[1].lower())
        if os.path.abspath(mp4) != os.path.abspath(dst):
            shutil.copy(mp4, dst); mp4 = dst
        # if a sidecar .srt sits next to the source, bring it in
        side = os.path.splitext(a.input)[0] + ".srt"
        if os.path.exists(side):
            shutil.copy(side, os.path.join(a.out, a.name + ".srt"))
    if not mp4 or not os.path.exists(mp4):
        raise SystemExit("no video file to work on")

    print("  probing ...")
    meta = probe(mp4)
    print("  finding cuts ...")
    cuts = find_cuts(mp4, a.out, a.scene)
    shots = shot_list(cuts, meta["duration"])
    print("  grabbing frames ...")
    frames = grab_frames(mp4, a.out, a.sps)
    print("  tiling contact sheets ...")
    sheets = contact_sheets(frames, a.out, a.sheet_cols, a.sheet_rows)
    print("  reading subtitles ...")
    subs = read_subs(a.out, a.name, info, meta["duration"])
    print("  measuring sound ...")
    sound = measure_sound(mp4, a.out)

    shot_lens = [s["len"] for s in shots] or [0]
    report = {
        "source": a.input,
        "title": info.get("title"),
        "uploader": info.get("uploader"),
        "video": meta,
        "shots": {"count": len(shots),
                  "avg_len": round(sum(shot_lens) / len(shot_lens), 2),
                  "min_len": min(shot_lens), "max_len": max(shot_lens),
                  "list": shots},
        "script": subs,
        "sound": sound,
        "frames": len(frames),
        "contact_sheets": [os.path.abspath(s) for s in sheets],
        "aspect": (f"{meta['width']}x{meta['height']}"
                   + (" (vertical)" if (meta["height"] or 0) > (meta["width"] or 0) else " (wide)"))
        if meta["width"] else None,
    }
    with open(os.path.join(a.out, "teardown.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=== TEARDOWN ===")
    if report["title"]:
        print(f"  title    {report['title']}  ({report['uploader']})")
    print(f"  video    {report['aspect']}  {meta['fps']} fps  {meta['duration']}s")
    print(f"  shots    {len(shots)}  (avg {report['shots']['avg_len']}s, "
          f"{report['shots']['min_len']}-{report['shots']['max_len']}s)")
    print(f"  script   {subs['words']} words  {subs['wpm']} wpm"
          + ("" if subs["has_script"] else "  (NO subtitles found)"))
    print(f"  sound    {sound['lufs']} LUFS  peak {sound['true_peak']} dBTP  "
          f"(mean {sound['mean_db']} dB)")
    print(f"  frames   {len(frames)} grabbed -> {len(sheets)} contact sheet(s)")
    print(f"  wrote    {os.path.join(a.out, 'teardown.json')}")
    print("\n  NEXT: read the contact sheet(s) with your eyes (SKILL.md step 6),")
    print("        then write recipe.md (step 7).")


if __name__ == "__main__":
    main()
