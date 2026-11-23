#!/usr/bin/env python3
"""sfx_lab.py - measure sound effects, separate stereo side SFX from centered voice, and audition by ear.

Subcommands:
  analyze <file...>                    per sound: length, attack, brightness, harsh share, peak, verdict
  side <video> --at t1,t2 | --auto     stereo L-R side jump at cuts vs centered voice
  events <video> [--json out.json]     every stereo sound event in the mix (with mono/dual-mono guard)
  audition <file...> --out x.mp4       audition video (Pillow title cards: alone, then under voice)
"""
import argparse
import json
import os
import shutil
import statistics
import subprocess

import numpy as np

try:
    from . import _common as C
except ImportError:
    import _common as C

SR = 48000


def load_pcm(path, stereo=False, start=None, dur=None):
    cmd = [C.find_ffmpeg(), "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(max(0.0, float(start)))]
    if dur is not None:
        cmd += ["-t", str(float(dur))]
    cmd += ["-i", path, "-vn", "-ac", "2" if stereo else "1", "-ar", str(SR), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if stereo:
        n = (len(x) // 2) * 2
        return x[:n].reshape(-1, 2)
    return x


def env(x, ms=5):
    n = max(1, int(SR * ms / 1000))
    k = len(x) // n
    if k == 0:
        return np.zeros(1, dtype=np.float32)
    return np.sqrt(np.mean(x[: k * n].reshape(k, n) ** 2, axis=1) + 1e-12)


def spectrum_stats(x):
    if len(x) < 256:
        return 0.0, 0.0, 0.0, 0.0
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    tot = float(X.sum()) + 1e-18
    cen = float((f * X).sum() / tot)
    band = lambda lo, hi: float(X[(f >= lo) & (f < hi)].sum() / tot)
    return cen, band(2000, 5000), band(5000, 14000), band(0, 200)


def describe(x):
    e = env(x)
    pk = float(np.max(np.abs(x))) + 1e-9 if len(x) else 1e-9
    emax = float(e.max()) + 1e-9
    above = np.where(e > emax * 0.1)[0]
    a0 = int(above[0]) if len(above) else 0
    a1 = int(np.argmax(e >= emax * 0.9))
    attack = max(0, (a1 - a0)) * 5
    db = 20.0 * np.log10(e / emax)
    live = np.where(db > -30.0)[0]
    length = (int(live[-1]) - int(live[0]) + 1) * 0.005 if len(live) else 0.0
    seg = x[a0 * 240: (int(live[-1]) + 1) * 240] if len(live) else x
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
    return {
        "len_s": round(float(length), 2),
        "attack_ms": int(attack),
        "centroid_hz": int(cen),
        "harsh_2_5k": round(float(harsh), 2),
        "air_5k_up": round(float(air), 2),
        "low_200": round(float(low), 2),
        "peak_dbfs": round(float(20.0 * np.log10(pk)), 1),
        "verdict": verdict,
    }


def cmd_analyze(a):
    print("  %-26s %6s %8s %9s %7s %6s %6s %7s  %s" % (
        "sound", "len s", "attack", "bright Hz", "harsh", "air", "low", "peak", "verdict"
    ))
    for f in a.files:
        d = describe(load_pcm(f))
        print("  %-26s %6.2f %6d ms %9d %6.0f%% %5.0f%% %5.0f%% %6.1f  %s" % (
            os.path.basename(f)[:26], d["len_s"], d["attack_ms"], d["centroid_hz"],
            100 * d["harsh_2_5k"], 100 * d["air_5k_up"], 100 * d["low_200"], d["peak_dbfs"], d["verdict"]
        ))


def _check_stereo(meta, x):
    if not meta["has_audio"] or len(x) == 0:
        return False, None
    side = (x[:, 0] - x[:, 1]) / 2.0
    mid = (x[:, 0] + x[:, 1]) / 2.0
    side_rms = float(np.sqrt(np.mean(side ** 2)))
    mid_rms = float(np.sqrt(np.mean(mid ** 2)))
    if meta["audio_channels"] < 2 or side_rms < 1e-5:
        return False, None
    mid_to_side_db = round(float(20.0 * np.log10((mid_rms + 1e-9) / (side_rms + 1e-9))), 1)
    return True, mid_to_side_db


def cmd_side(a):
    meta = C.probe_media(a.video)
    if not meta["has_audio"]:
        print("  no audio stream in video")
        return
    probe_x = load_pcm(a.video, stereo=True, start=a.start, dur=min(a.dur, 30.0))
    ok_stereo, mid_to_side_db = _check_stereo(meta, probe_x)
    if not ok_stereo:
        print(f"  mono / dual-mono audio ({meta['audio_channels']}ch): stereo L-R voice cancellation is not applicable")
        return

    if a.auto:
        times = C.detect_cuts(a.video, threshold=0.15, start=a.start, dur=a.dur, min_gap=1.5)
    elif a.at:
        times = [float(t.strip()) for t in a.at.split(",") if t.strip()]
    else:
        raise SystemExit("pass --auto or --at t1,t2,...")

    rows = []
    print("   time  side jump  level vs voice  bright Hz  harsh  attack  len   verdict")
    for t in times:
        x = load_pcm(a.video, stereo=True, start=t - 2.0, dur=4.0)
        if len(x) < SR * 3:
            continue
        mid, side = (x[:, 0] + x[:, 1]) / 2.0, (x[:, 0] - x[:, 1]) / 2.0
        es, em = env(side, 20), env(mid, 20)
        i0, i1 = int(1.7 / 0.02), int(2.5 / 0.02)
        ctx = np.concatenate([es[: i0 - 5], es[i1 + 5:]])
        jump = float(20.0 * np.log10(es[i0:i1].max() / (float(np.median(ctx)) + 1e-9)))
        k = i0 + int(np.argmax(es[i0:i1]))
        ev_pcm = side[max(0, (k - 10) * 960): (k + 20) * 960]
        voice = float(20.0 * np.log10(float(np.median(em)) + 1e-9))
        lvl = float(20.0 * np.log10(es[k] + 1e-9)) - voice
        d = describe(ev_pcm) if jump > 4.0 else None
        rows.append((t, jump, lvl, d))
        if d:
            print("  %6.2f  %+6.1f dB   %+6.1f dB     %6d   %4.0f%%  %4d ms %4.2f  %s" % (
                t, jump, lvl, d["centroid_hz"], 100 * d["harsh_2_5k"], d["attack_ms"], d["len_s"], d["verdict"]
            ))
        else:
            print("  %6.2f  %+6.1f dB   (no stereo sound effect at this cut)" % (t, jump))

    hits = [r for r in rows if r[3]]
    if hits:
        print(f"\n  stereo SFX at {len(hits)} of {len(rows)} cuts")
        print("  median: level %+.1f dB vs voice, brightness %d Hz, harsh %.0f%%, attack %d ms, length %.2f s" % (
            statistics.median(r[2] for r in hits),
            statistics.median(r[3]["centroid_hz"] for r in hits),
            100 * statistics.median(r[3]["harsh_2_5k"] for r in hits),
            statistics.median(r[3]["attack_ms"] for r in hits),
            statistics.median(r[3]["len_s"] for r in hits),
        ))
    print(f"  whole mix: side is {mid_to_side_db:.1f} dB under mid")


def _classify_event(d):
    if d["centroid_hz"] > 3500:
        return "sparkle / hiss"
    if d["rise_ms"] >= 120:
        return "swell (slow whoosh)"
    if d["len_s"] < 0.25:
        return "pop / tick"
    return "hit / short whoosh"


def cmd_events(a):
    """Find every stereo sound event in the mix (centered voice removed)."""
    meta = C.probe_media(a.video)
    x = load_pcm(a.video, stereo=True, start=a.start, dur=a.dur) if meta["has_audio"] else np.zeros((0, 2), dtype=np.float32)
    actual_dur = round(len(x) / float(SR), 2)
    ok_stereo, mid_to_side_db = _check_stereo(meta, x)

    if not ok_stereo or actual_dur <= 2.0:
        reason = "no audio stream" if not meta["has_audio"] else (
            "audio too short for event window" if actual_dur <= 2.0
            else f"mono / dual-mono audio ({meta['audio_channels']}ch): stereo L-R voice cancellation is not applicable"
        )
        print(f"  {reason}")
        payload = {
            "video": os.path.abspath(a.video),
            "duration_sec": actual_dur,
            "audio_channels": meta["audio_channels"],
            "stereo_separation": False,
            "mid_to_side_db": None,
            "event_count": 0,
            "events_per_min": None,
            "summary_by_kind": {},
            "events": [],
            "note": reason,
        }
        if a.json:
            with open(a.json, "w", encoding="utf-8") as fp:
                json.dump(payload, fp, indent=2)
            print("  events ->", a.json)
        return

    side = (x[:, 0] - x[:, 1]) / 2.0
    mid = (x[:, 0] + x[:, 1]) / 2.0
    es, em = env(side, 20), env(mid, 20)
    db = 20.0 * np.log10(es + 1e-9)
    n = len(db)
    ev, last = [], -99

    for i in range(50, max(50, n - 50)):
        base = float(np.median(db[i - 50: i - 5]))
        if db[i] > base + a.thr and db[i] == db[max(0, i - 6): i + 7].max() and (i - last) > 20:
            s0 = i
            while s0 > max(0, i - 60) and db[s0 - 1] > base + 2.0:
                s0 -= 1
            s1 = i
            while s1 < min(n - 1, i + 150) and db[s1 + 1] > base + 2.0:
                s1 += 1
            seg = side[s0 * 960: (s1 + 1) * 960]
            d = describe(seg)
            d["t"] = round(a.start + i * 0.02, 2)
            d["rise_ms"] = int(i - s0) * 20
            d["tail_ms"] = int(s1 - i) * 20
            d["jump_db"] = round(float(db[i] - base), 1)
            d["vs_voice_db"] = round(
                float(db[i] - 20.0 * np.log10(float(np.median(em[max(0, i - 100): i + 100])) + 1e-9)), 1
            )
            d["kind"] = _classify_event(d)
            ev.append(d)
            last = i

    per_min = round(len(ev) / (actual_dur / 60.0), 1)
    kinds = {}
    for d in ev:
        kinds.setdefault(d["kind"], []).append(d)

    summary = {}
    print(f"  {len(ev)} stereo sound events in {actual_dur:.1f} s = {per_min:.1f} per minute (mid/side {mid_to_side_db:.1f} dB)")
    if kinds:
        print("  %-22s %4s  %8s %8s %8s %8s %8s" % ("kind", "n", "rise ms", "tail ms", "bright", "harsh", "vs voice"))
    for k, ds in sorted(kinds.items(), key=lambda kv: -len(kv[1])):
        med = lambda key: statistics.median(d[key] for d in ds)
        row = {
            "count": len(ds),
            "median_rise_ms": int(round(med("rise_ms"))),
            "median_tail_ms": int(round(med("tail_ms"))),
            "median_centroid_hz": int(round(med("centroid_hz"))),
            "median_harsh_pct": int(round(100 * med("harsh_2_5k"))),
            "median_vs_voice_db": round(float(med("vs_voice_db")), 1),
        }
        summary[k] = row
        print("  %-22s %4d  %8d %8d %7dHz %7d%% %+7.1fdB" % (
            k, row["count"], row["median_rise_ms"], row["median_tail_ms"],
            row["median_centroid_hz"], row["median_harsh_pct"], row["median_vs_voice_db"],
        ))

    if a.json:
        payload = {
            "video": os.path.abspath(a.video),
            "duration_sec": actual_dur,
            "audio_channels": meta["audio_channels"],
            "stereo_separation": True,
            "mid_to_side_db": mid_to_side_db,
            "event_count": len(ev),
            "events_per_min": per_min,
            "summary_by_kind": summary,
            "events": ev,
        }
        with open(a.json, "w", encoding="utf-8") as fp:
            json.dump(payload, fp, indent=1)
        print("  events ->", a.json)


def _render_audition_card(path, title, sub_line, legend):
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (1280, 720), (233, 232, 230))
    draw = ImageDraw.Draw(img)
    f_title = C.load_font(68, bold=True)
    f_sub = C.load_font(30, bold=False)
    f_leg = C.load_font(26, bold=True)

    draw.rectangle([0, 0, 1280, 14], fill=(139, 26, 43))
    draw.text((80, 230), title, font=f_title, fill=(139, 26, 43))
    draw.text((80, 340), sub_line, font=f_sub, fill=(58, 56, 53))
    draw.text((80, 445), legend, font=f_leg, fill=(107, 107, 107))
    img.save(path)


def cmd_audition(a):
    if a.gains:
        gains = [float(g.strip()) for g in a.gains.split(",") if g.strip()]
        if len(gains) != len(a.files):
            raise SystemExit(f"--gains count ({len(gains)}) must match input file count ({len(a.files)})")
    else:
        gains = [a.gain] * len(a.files)

    out_abs = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out_abs) or ".", exist_ok=True)
    tmp = os.path.join(os.path.dirname(out_abs) or ".", "_audition")
    os.makedirs(tmp, exist_ok=True)
    ff = C.find_ffmpeg()
    parts = []

    try:
        for i, f in enumerate(a.files, 1):
            gain = gains[i - 1]
            name = os.path.splitext(os.path.basename(f))[0]
            d = describe(load_pcm(f))
            card = os.path.join(tmp, f"card_{i:02d}.png")
            sub = f"{d['verdict']}  |  bright {d['centroid_hz']} Hz  |  attack {d['attack_ms']} ms  |  {d['len_s']} s"
            legend = f"A: alone    B: under voice (gain {gain})" if a.voice else "A: sound preview (alone)"
            _render_audition_card(card, f"{i}. {name}", sub, legend)

            one = os.path.join(tmp, f"{i:02d}.mp4")
            if a.voice:
                fc = (
                    "[1]volume=1.0,aformat=channel_layouts=stereo[s1];"
                    f"[2]atrim={a.voice_at}:{a.voice_at + 2.6},asetpts=PTS-STARTPTS,aformat=channel_layouts=stereo[v];"
                    f"[1]volume={gain},adelay=1300|1300,aformat=channel_layouts=stereo[s2];"
                    "[s1]adelay=300|300,apad=whole_dur=1.6[a1];"
                    "[v][s2]amix=inputs=2:normalize=0:duration=first,apad=whole_dur=2.8[a2];"
                    "[a1][a2]concat=n=2:v=0:a=1[aout]"
                )
                ins = ["-i", f, "-i", a.voice]
                dur = 4.4
            else:
                fc = "[1]adelay=300|300,aformat=channel_layouts=stereo,apad=whole_dur=1.8[aout]"
                ins = ["-i", f]
                dur = 1.8

            cmd = [
                ff, "-v", "error", "-y",
                "-loop", "1", "-framerate", "30", "-t", str(dur), "-i", card,
                *ins,
                "-filter_complex", fc,
                "-map", "0:v", "-map", "[aout]",
                "-t", str(dur),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                one,
            ]
            r = C.run_cmd(cmd)
            if r.returncode != 0:
                raise SystemExit(r.stderr[-1200:] or "ffmpeg audition render failed")
            parts.append(one)

        lst = os.path.join(tmp, "list.txt")
        with open(lst, "w", encoding="utf-8") as fp:
            for p in parts:
                fp.write(f"file '{p.replace(os.sep, '/')}'\n")
        r = C.run_cmd([ff, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out_abs])
        if r.returncode != 0:
            raise SystemExit(r.stderr[-1200:] or "ffmpeg audition concat failed")
        print(f"audition: {len(parts)} sounds -> {out_abs}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("analyze")
    s.add_argument("files", nargs="+")

    s = sub.add_parser("side")
    s.add_argument("video")
    s.add_argument("--at")
    s.add_argument("--auto", action="store_true")
    s.add_argument("--start", type=float, default=0.0)
    s.add_argument("--dur", type=float, default=180.0)

    s = sub.add_parser("events")
    s.add_argument("video")
    s.add_argument("--start", type=float, default=0.0)
    s.add_argument("--dur", type=float, default=180.0)
    s.add_argument("--thr", type=float, default=7.0)
    s.add_argument("--json")

    s = sub.add_parser("audition")
    s.add_argument("files", nargs="+")
    s.add_argument("--out", required=True)
    s.add_argument("--voice")
    s.add_argument("--voice-at", type=float, default=40.0)
    s.add_argument("--gain", type=float, default=0.2)
    s.add_argument("--gains", help="one volume per file, comma separated")

    a = ap.parse_args()
    {"analyze": cmd_analyze, "side": cmd_side, "events": cmd_events, "audition": cmd_audition}[a.cmd](a)


if __name__ == "__main__":
    main()
