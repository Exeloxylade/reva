#!/usr/bin/env python3
"""sfx_lab.py - judge sound effects by numbers, learn them from a reference mix, audition them by ear.

  analyze <file...>                    per sound: length, attack, brightness, harsh-band share, peak, verdict
  side <video> --at t1,t2 | --auto     a stereo reference mix with the centred voice removed (L-R):
                                       what jumps at each cut, how bright, how long, how loud vs the voice
  audition <file...> --out x.mp4       one short video: each sound alone, then under a voice line at film level,
     [--voice voice.wav --voice-at 40 --gain 0.2]   with its number and name on screen - for the user's ear

Soft = low brightness (centroid < 1800 Hz), little 2-5 kHz "harsh" energy (< 25%), no click
(attack >= 5 ms), not too long (0.08-1.6 s). These numbers are this tool's rule of thumb, not a standard.
Needs ffmpeg + numpy.
"""
import argparse
import json
import os
import statistics
import subprocess
import sys

import numpy as np

FF = r"C:\ffmpeg\bin\ffmpeg.exe"
SR = 48000


def load(path, stereo=False, start=None, dur=None):
    cmd = [FF, "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(max(0, start))]
    if dur is not None:
        cmd += ["-t", str(dur)]
    cmd += ["-i", path, "-vn", "-ac", "2" if stereo else "1", "-ar", str(SR), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    return x.reshape(-1, 2) if stereo else x


def env(x, ms=5):
    n = max(1, int(SR * ms / 1000))
    k = len(x) // n
    if k == 0:
        return np.zeros(1)
    return np.sqrt(np.mean(x[: k * n].reshape(k, n) ** 2, axis=1) + 1e-12)


def spectrum_stats(x):
    if len(x) < 256:
        return 0, 0, 0, 0
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1 / SR)
    tot = X.sum() + 1e-18
    cen = float((f * X).sum() / tot)
    band = lambda a, b: float(X[(f >= a) & (f < b)].sum() / tot)
    return cen, band(2000, 5000), band(5000, 14000), band(0, 200)


def describe(x):
    e = env(x)
    pk = float(np.max(np.abs(x))) + 1e-9
    emax = float(e.max())
    above = np.where(e > emax * 0.1)[0]
    a0 = above[0] if len(above) else 0
    a1 = int(np.argmax(e >= emax * 0.9))
    attack = max(0, (a1 - a0)) * 5
    db = 20 * np.log10(e / emax)
    live = np.where(db > -30)[0]
    length = (live[-1] - live[0] + 1) * 0.005 if len(live) else 0
    seg = x[a0 * 240: (live[-1] + 1) * 240] if len(live) else x
    cen, harsh, air, low = spectrum_stats(seg)
    if cen > 3000 or harsh > 0.35:
        verdict = "BRIGHT / harsh"
    elif attack < 5 and harsh > 0.15:
        verdict = "CLICKY"
    elif cen < 1800 and harsh < 0.25 and attack >= 5 and 0.08 <= length <= 1.6:
        verdict = "soft"
    elif cen < 1800 and harsh < 0.25:
        verdict = "soft-ish"
    else:
        verdict = "medium"
    return {"len_s": round(length, 2), "attack_ms": attack, "centroid_hz": int(cen), "harsh_2_5k": round(harsh, 2),
            "air_5k_up": round(air, 2), "low_200": round(low, 2), "peak_dbfs": round(20 * np.log10(pk), 1), "verdict": verdict}


def cmd_analyze(a):
    print("  %-26s %6s %8s %9s %7s %6s %6s %7s  %s" % ("sound", "len s", "attack", "bright Hz", "harsh", "air", "low", "peak", "verdict"))
    for f in a.files:
        d = describe(load(f))
        print("  %-26s %6.2f %6d ms %9d %6.0f%% %5.0f%% %5.0f%% %6.1f  %s" % (os.path.basename(f)[:26], d["len_s"], d["attack_ms"],
              d["centroid_hz"], 100 * d["harsh_2_5k"], 100 * d["air_5k_up"], 100 * d["low_200"], d["peak_dbfs"], d["verdict"]))


def cmd_side(a):
    if a.auto:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from sfx_probe import scene_times
        times = scene_times(a.video, a.start, a.dur, 0.15)
    else:
        times = [float(t) for t in a.at.split(",") if t]
    rows = []
    print("   time  side jump  level vs voice  bright Hz  harsh  attack  len   verdict")
    for t in times:
        x = load(a.video, stereo=True, start=t - 2.0, dur=4.0)
        if len(x) < SR * 3:
            continue
        mid, side = (x[:, 0] + x[:, 1]) / 2, (x[:, 0] - x[:, 1]) / 2
        es, em = env(side, 20), env(mid, 20)
        i0, i1 = int(1.7 / 0.02), int(2.5 / 0.02)              # -0.3 .. +0.5 s around the cut
        ctx = np.concatenate([es[: i0 - 5], es[i1 + 5:]])
        jump = 20 * np.log10(es[i0:i1].max() / (np.median(ctx) + 1e-9))
        k = i0 + int(np.argmax(es[i0:i1]))
        ev = side[max(0, (k - 10) * 960): (k + 20) * 960]
        voice = 20 * np.log10(np.median(em) + 1e-9)
        lvl = 20 * np.log10(es[k] + 1e-9) - voice
        d = describe(ev) if jump > 4 else None
        rows.append((t, jump, lvl, d))
        if d:
            print("  %6.2f  %+6.1f dB   %+6.1f dB     %6d   %4.0f%%  %4d ms %4.2f  %s" % (t, jump, lvl, d["centroid_hz"],
                  100 * d["harsh_2_5k"], d["attack_ms"], d["len_s"], d["verdict"]))
        else:
            print("  %6.2f  %+6.1f dB   (no stereo sound effect at this cut)" % (t, jump))
    hits = [r for r in rows if r[3]]
    if hits:
        print("\n  stereo SFX at %d of %d cuts" % (len(hits), len(rows)))
        print("  median: level %+.1f dB vs voice, brightness %d Hz, harsh %.0f%%, attack %d ms, length %.2f s" % (
            statistics.median(r[2] for r in hits), statistics.median(r[3]["centroid_hz"] for r in hits),
            100 * statistics.median(r[3]["harsh_2_5k"] for r in hits), statistics.median(r[3]["attack_ms"] for r in hits),
            statistics.median(r[3]["len_s"] for r in hits)))
    w = load(a.video, stereo=True, start=a.start, dur=min(a.dur, 120))
    m, s = (w[:, 0] + w[:, 1]) / 2, (w[:, 0] - w[:, 1]) / 2
    print("  whole mix: side is %.1f dB under mid (a centred voice makes this large)" % (20 * np.log10((np.sqrt((m ** 2).mean()) + 1e-9) / (np.sqrt((s ** 2).mean()) + 1e-9))))


def cmd_events(a):
    """Every stereo sound event in the mix (voice removed), not only at cuts: density and kinds."""
    x = load(a.video, stereo=True, start=a.start, dur=a.dur)
    side = (x[:, 0] - x[:, 1]) / 2
    mid = (x[:, 0] + x[:, 1]) / 2
    es = env(side, 20)
    em = env(mid, 20)
    db = 20 * np.log10(es + 1e-9)
    n = len(db)
    ev, last = [], -99
    for i in range(50, n - 50):
        base = np.median(db[i - 50:i - 5])                     # the 1 s before
        if db[i] > base + a.thr and db[i] == db[max(0, i - 6): i + 7].max() and i - last > 20:
            # walk back to where it started rising, forward to where it fell back
            s0 = i
            while s0 > i - 60 and db[s0 - 1] > base + 2:
                s0 -= 1
            s1 = i
            while s1 < min(n - 1, i + 150) and db[s1 + 1] > base + 2:
                s1 += 1
            seg = side[s0 * 960: (s1 + 1) * 960]
            d = describe(seg)
            d["t"] = round(a.start + i * 0.02, 2)
            d["rise_ms"] = int(i - s0) * 20
            d["tail_ms"] = int(s1 - i) * 20
            d["jump_db"] = round(float(db[i] - base), 1)
            d["vs_voice_db"] = round(float(db[i] - 20 * np.log10(np.median(em[max(0, i - 100): i + 100]) + 1e-9)), 1)
            ev.append(d)
            last = i
    def kind(d):
        if d["centroid_hz"] > 3500:
            return "sparkle / hiss"
        if d["rise_ms"] >= 120:
            return "swell (slow whoosh)"
        if d["len_s"] < 0.25:
            return "pop / tick"
        return "hit / short whoosh"
    kinds = {}
    for d in ev:
        kinds.setdefault(kind(d), []).append(d)
    mins = a.dur / 60
    print(f"  {len(ev)} stereo sound events in {a.dur:.0f} s = {len(ev) / mins:.1f} per minute")
    print("  %-22s %4s  %8s %8s %8s %8s %8s" % ("kind", "n", "rise ms", "tail ms", "bright", "harsh", "vs voice"))
    for k, ds in sorted(kinds.items(), key=lambda kv: -len(kv[1])):
        med = lambda key: statistics.median(d[key] for d in ds)
        print("  %-22s %4d  %8.0f %8.0f %7.0fHz %7.0f%% %+7.1fdB" % (k, len(ds), med("rise_ms"), med("tail_ms"), med("centroid_hz"),
              100 * med("harsh_2_5k"), med("vs_voice_db")))
    if a.json:
        num = lambda o: o.item() if hasattr(o, "item") else str(o)    # numpy numbers -> plain numbers
        txt = json.dumps(ev, indent=1, default=num)                   # build first: a failed dump never leaves half a file
        open(a.json, "w").write(txt)
        print("  events ->", a.json)


def font():
    for p in [os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tscs-finance-explainer", "fonts", "Poppins-Bold.ttf"),
              r"C:\Windows\Fonts\arialbd.ttf"]:
        if os.path.exists(p):
            return os.path.abspath(p).replace("\\", "/").replace(":", "\\:")
    return None


def cmd_audition(a):
    tmp = os.path.join(os.path.dirname(os.path.abspath(a.out)), "_audition")
    os.makedirs(tmp, exist_ok=True)
    fnt = font()
    parts = []
    gains = [float(g) for g in a.gains.split(",")] if a.gains else [a.gain] * len(a.files)
    for i, f in enumerate(a.files, 1):
        gain = gains[i - 1]
        name = os.path.splitext(os.path.basename(f))[0]
        d = describe(load(f))
        label = f"{i}  {name}"
        sub = f"{d['verdict']}   bright {d['centroid_hz']} Hz   attack {d['attack_ms']} ms   {d['len_s']} s"
        dt = lambda text, y, size, col: (f"drawtext=fontfile='{fnt}':text='{text}':x=80:y={y}:fontsize={size}:fontcolor={col}")
        vf = ",".join([dt(label, 260, 72, "0x8b1a2b"), dt(sub, 370, 30, "0x3a3835"), dt("A  alone          B  under the voice", 470, 28, "0x6b6b6b")])
        one = os.path.join(tmp, f"{i:02d}.mp4")
        if a.voice:
            fc = (f"[1]volume=1.0,aformat=channel_layouts=stereo[s1];"
                  f"[2]atrim={a.voice_at}:{a.voice_at + 2.6},asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo[v];"
                  f"[1]volume={gain},adelay=1300|1300,aformat=channel_layouts=stereo[s2];"
                  f"[s1]adelay=300|300,apad=whole_dur=1.6[a1];[v][s2]amix=inputs=2:normalize=0:duration=first,apad=whole_dur=2.8[a2];"
                  f"[a1][a2]concat=n=2:v=0:a=1[aout]")
            ins = ["-i", f, "-i", a.voice]
            dur = 4.4
        else:
            fc = "[1]adelay=300|300,aformat=channel_layouts=stereo,apad=whole_dur=1.8[aout]"
            ins = ["-i", f]
            dur = 1.8
        cmd = [FF, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c=0xe9e8e6:s=1280x720:d={dur}:r=30", *ins,
               "-filter_complex", fc, "-map", "0:v", "-map", "[aout]", "-vf", vf, "-t", str(dur),
               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", one]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode:
            sys.exit(r.stderr[-1200:])
        parts.append(one)
    lst = os.path.join(tmp, "list.txt")
    open(lst, "w").write("".join(f"file '{p.replace(os.sep, '/')}'\n" for p in parts))
    subprocess.run([FF, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", a.out], check=True)
    for p in parts:
        os.remove(p)
    print(f"audition: {len(parts)} sounds -> {a.out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("analyze"); s.add_argument("files", nargs="+")
    s = sub.add_parser("side"); s.add_argument("video"); s.add_argument("--at"); s.add_argument("--auto", action="store_true")
    s.add_argument("--start", type=float, default=0); s.add_argument("--dur", type=float, default=180)
    s = sub.add_parser("events"); s.add_argument("video"); s.add_argument("--start", type=float, default=0)
    s.add_argument("--dur", type=float, default=180); s.add_argument("--thr", type=float, default=7.0); s.add_argument("--json")
    s = sub.add_parser("audition"); s.add_argument("files", nargs="+"); s.add_argument("--out", required=True)
    s.add_argument("--voice"); s.add_argument("--voice-at", type=float, default=40); s.add_argument("--gain", type=float, default=0.2)
    s.add_argument("--gains", help="one volume per file, comma separated (film level for the B part)")
    a = ap.parse_args()
    {"analyze": cmd_analyze, "side": cmd_side, "events": cmd_events, "audition": cmd_audition}[a.cmd](a)


if __name__ == "__main__":
    main()
