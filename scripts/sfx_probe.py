#!/usr/bin/env python3
"""sfx_probe.py - measure how loud and how bright transition sounds are, in any video.

For each transition time it reports, relative to the 4 s of audio around it:
  full  - jump in overall level (dB) in the 0.6 s around the transition
  air   - jump in the 4-8 kHz band (dB): hiss/whoosh energy, the "annoying" part
  low   - jump in the 40-200 Hz band (dB): thumps / soft hits
Transition times: pass --at a,b,c, or let it find scene changes in the picture (--auto).

Usage:
  python sfx_probe.py <video> --start 0 --dur 180 --auto
  python sfx_probe.py <video> --at 14.0,18.4,35.6
Stdlib + ffmpeg only.
"""
import argparse, math, re, struct, subprocess, statistics

FF = r"C:\ffmpeg\bin\ffmpeg.exe"
SR, HOP = 16000, 0.05


def pcm(path, start, dur, af):
    cmd = [FF, "-v", "error", "-ss", str(start), "-t", str(dur), "-i", path, "-vn", "-ac", "1", "-ar", str(SR)]
    if af:
        cmd += ["-af", af]
    cmd += ["-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    return struct.unpack("<%dh" % (len(raw) // 2), raw)


def env_db(x):
    n = int(SR * HOP); out = []
    for i in range(0, len(x) - n, n):
        s = sum(v * v for v in x[i:i + n]) / n
        out.append(10 * math.log10(s / 32768.0 ** 2 + 1e-12))
    return out


def scene_times(path, start, dur, thr):
    cmd = [FF, "-v", "error", "-ss", str(start), "-t", str(dur), "-i", path, "-an",
           "-vf", "scale=320:-2,select='gte(scene,0)',metadata=print:file=-", "-f", "null", "-"]
    txt = subprocess.run(cmd, capture_output=True, text=True).stdout
    t, s, pts = None, [], []
    for line in txt.splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m: t = float(m.group(1))
        m = re.search(r"scene_score=([0-9.]+)", line)
        if m and t is not None: pts.append((t, float(m.group(1))))
    # peaks above thr, at least 1.5 s apart
    out = []
    for i, (tt, sc) in enumerate(pts):
        if sc < thr: continue
        if out and tt - out[-1][0] < 1.5:
            if sc > out[-1][1]: out[-1] = (tt, sc)
            continue
        out.append((tt, sc))
    return [round(tt, 2) for tt, _ in out]


def jump(env, t, start):
    i = int((t - start) / HOP)
    near = env[max(0, i - 6): i + 7]                       # +-0.3 s
    ctx = env[max(0, i - 40): max(0, i - 8)] + env[i + 9: i + 41]  # 0.4-2 s either side
    if not near or len(ctx) < 5: return None
    return round(max(near) - statistics.median(ctx), 1)


def length(env, t, start, over=6.0):
    """seconds the band stays more than `over` dB above its surroundings, around t"""
    i = int((t - start) / HOP)
    ctx = env[max(0, i - 40): max(0, i - 8)] + env[i + 9: i + 41]
    if len(ctx) < 5: return None
    base = statistics.median(ctx) + over
    win = env[max(0, i - 10): i + 30]
    if not win or max(win) < base: return 0.0
    k = max(range(len(win)), key=lambda j: win[j])
    a = b = k
    while a > 0 and win[a - 1] >= base: a -= 1
    while b < len(win) - 1 and win[b + 1] >= base: b += 1
    return round((b - a + 1) * HOP, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--start", type=float, default=0); ap.add_argument("--dur", type=float, default=180)
    ap.add_argument("--at"); ap.add_argument("--auto", action="store_true"); ap.add_argument("--thr", type=float, default=0.12)
    a = ap.parse_args()
    times = [float(x) for x in a.at.split(",")] if a.at else scene_times(a.video, a.start, a.dur, a.thr)
    full = env_db(pcm(a.video, a.start, a.dur, None))
    air = env_db(pcm(a.video, a.start, a.dur, "highpass=f=4000,highpass=f=4000,lowpass=f=8000"))
    low = env_db(pcm(a.video, a.start, a.dur, "lowpass=f=200,lowpass=f=200,highpass=f=40"))
    rows = []
    print("   time   full   air    low   airLen(s)   (dB jump vs. the 4 s around it)")
    for t in times:
        r = (t, jump(full, t, a.start), jump(air, t, a.start), jump(low, t, a.start), length(air, t, a.start))
        if None in r: continue
        rows.append(r); print("  %6.2f  %+5.1f  %+5.1f  %+5.1f   %4.2f" % r)
    if rows:
        med = lambda k: statistics.median(r[k] for r in rows)
        print("  median  %+5.1f  %+5.1f  %+5.1f   %4.2f   over %d transitions" % (med(1), med(2), med(3), med(4), len(rows)))
    # how bright is the whole mix: share of energy above 4 kHz
    fa = sum(10 ** (v / 10) for v in full); aa = sum(10 ** (v / 10) for v in air)
    print("  air share of the whole mix: %.1f dB below full band" % (10 * math.log10(fa / max(aa, 1e-12))))


if __name__ == "__main__":
    main()
