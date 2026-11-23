#!/usr/bin/env python3
"""Automated unit + FFmpeg end-to-end tests for REVA."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")
REVA_PY = os.path.join(REPO, "reva.py")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import _common as C
import style_kit


def run_reva(workspace, *args, check=True):
    env = os.environ.copy()
    env["REVA_WORKSPACE"] = workspace
    r = subprocess.run(
        [sys.executable, REVA_PY, *map(str, args)],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and r.returncode != 0:
        raise AssertionError(
            f"reva {' '.join(map(str, args))} failed ({r.returncode}):\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
        )
    return r


def _fill_placeholders(obj):
    if isinstance(obj, dict):
        return {k: _fill_placeholders(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_fill_placeholders(v) for v in obj]
    if isinstance(obj, str) and re.search(r"<[^>\n]{2,}>", obj):
        return "Sample clean rule for automated verification"
    return obj


class TestCommonUnit(unittest.TestCase):
    def test_timestamp_helpers(self):
        self.assertEqual(C.norm_ts(" 44.0 "), "44")
        self.assertEqual(C.norm_ts("44.500"), "44.5")
        self.assertEqual(C.norm_ts("-0.0"), "0")
        self.assertEqual(C.ts_token("44.50"), "44_5")
        self.assertEqual(C.fmt_ts(0), "00:00")
        self.assertEqual(C.fmt_ts(65.2), "01:05")
        self.assertEqual(C.fmt_ts(3661), "1:01:01")

    def test_parse_rolling_vtt_preserves_later_repeats(self):
        vtt = (
            "WEBVTT\nKind: captions\nLanguage: en\n\n"
            "00:00.000 --> 00:02.000\n"
            "Hello world\n\n"
            "00:02.000 --> 00:04.000\n"
            "Hello world\n"
            "second line here\n\n"
            "00:04.000 --> 00:06.000\n"
            "second line here\n"
            "third line\n\n"
            "00:12.000 --> 00:14.000\n"
            "Hello world\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "ref.en.vtt")
            with open(p, "w", encoding="utf-8") as fp:
                fp.write(vtt)
            parsed = C.parse_subtitles(p)
            texts = [c["text"] for c in parsed["cues"]]
            self.assertEqual(texts, ["Hello world", "second line here", "third line", "Hello world"])
            self.assertEqual(parsed["words"], 9)
            self.assertIn("second line here", C.narration_at(parsed["cues"], 3.0))

    def test_parse_progressive_vtt_and_srt(self):
        vtt = (
            "WEBVTT\n\n"
            "00:01.000 --> 00:01.500\n<c>First</c>\n\n"
            "00:01.500 --> 00:02.500\n<c>First</c> <c>sentence</c>\n\n"
            "00:02.500 --> 00:03.500\nFirst sentence complete\n"
        )
        srt = (
            "1\n00:00:00,500 --> 00:00:02,000\nLine one.\n\n"
            "2\n00:00:02,500 --> 00:00:04,500\nLine two.\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            pv = os.path.join(tmp, "prog.vtt")
            ps = os.path.join(tmp, "sub.srt")
            with open(pv, "w", encoding="utf-8") as fp:
                fp.write(vtt)
            with open(ps, "w", encoding="utf-8") as fp:
                fp.write(srt)
            p1 = C.parse_subtitles(pv)
            self.assertEqual([c["text"] for c in p1["cues"]], ["First sentence complete"])
            p2 = C.parse_subtitles(ps)
            self.assertEqual([c["text"] for c in p2["cues"]], ["Line one.", "Line two."])


class TestRevaEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="reva_e2e_")
        cls.ws = os.path.join(cls.tmp.name, "studies")
        cls.media = os.path.join(cls.tmp.name, "media")
        os.makedirs(cls.ws, exist_ok=True)
        os.makedirs(cls.media, exist_ok=True)
        ff = C.find_ffmpeg()

        # 1. sample_wide.mp4: 9s 640x360 stereo video with 3 cuts (static -> moving -> static) + 2 stereo SFX bursts.
        cls.wide_mp4 = os.path.join(cls.media, "sample_wide.mp4")
        r = C.run_cmd([
            ff, "-hide_banner", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=0xe9e8e6:s=640x360:d=3:r=24",
            "-f", "lavfi", "-i", "color=c=0x1976d2:s=640x360:d=3:r=24",
            "-f", "lavfi", "-i", "color=c=0xffffff:s=120x120:d=3:r=24",
            "-f", "lavfi", "-i", "color=c=0x1c1c1c:s=640x360:d=3:r=24",
            "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=48000:duration=9",
            "-f", "lavfi", "-i", "sine=frequency=650:sample_rate=48000:duration=0.4",
            "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=0.4",
            "-filter_complex", (
                "[0]drawbox=x=80:y=60:w=220:h=160:color=0x8b1a2b:t=fill[v0];"
                "[1][2]overlay=x='40+120*t':y=120[v1];"
                "[3]drawbox=x=200:y=100:w=200:h=140:color=0xfc6428:t=fill[v2];"
                "[v0][v1][v2]concat=n=3:v=1:a=0[vout];"
                "[4]volume=0.25,asplit=2[vl][vr];"
                "[5]adelay=3000|3000,volume=0.8,apad=whole_dur=9[s1];"
                "[6]adelay=6000|6000,volume=0.8,apad=whole_dur=9[s2];"
                "[vl][s1]amix=inputs=2:normalize=0:duration=first[left];"
                "[vr][s2]amix=inputs=2:normalize=0:duration=first[right];"
                "[left][right]join=inputs=2:channel_layout=stereo[aout]"
            ),
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            cls.wide_mp4,
        ])
        if r.returncode != 0:
            raise RuntimeError(f"failed creating sample_wide.mp4: {r.stderr}")

        with open(os.path.join(cls.media, "sample_wide.vtt"), "w", encoding="utf-8") as fp:
            fp.write(
                "WEBVTT\n\n"
                "00:00.200 --> 00:02.800\n"
                "Welcome to the first cream card scene.\n\n"
                "00:03.100 --> 00:05.800\n"
                "Now the white square moves across blue.\n\n"
                "00:06.100 --> 00:08.800\n"
                "Finally the dark card ends the example.\n"
            )

        # 2. sample_short_mono.mp4: 5s 360x640 vertical mono video with 4 fast 1.25s shots.
        cls.short_mp4 = os.path.join(cls.media, "sample_short_mono.mp4")
        r = C.run_cmd([
            ff, "-hide_banner", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=0xa8c8af:s=360x640:d=1.25:r=24",
            "-f", "lavfi", "-i", "color=c=0xd98a1a:s=360x640:d=1.25:r=24",
            "-f", "lavfi", "-i", "color=c=0x215d98:s=360x640:d=1.25:r=24",
            "-f", "lavfi", "-i", "color=c=0xfc6428:s=360x640:d=1.25:r=24",
            "-f", "lavfi", "-i", "sine=frequency=330:sample_rate=48000:duration=5",
            "-filter_complex", "[0][1][2][3]concat=n=4:v=1:a=0[vout]",
            "-map", "[vout]", "-map", "4:a", "-ac", "1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k",
            cls.short_mp4,
        ])
        if r.returncode != 0:
            raise RuntimeError(f"failed creating sample_short_mono.mp4: {r.stderr}")

        # 3. sample_rebuild.mp4: 4s 480x360 (different aspect ratio for compare test).
        cls.rebuild_mp4 = os.path.join(cls.media, "sample_rebuild.mp4")
        r = C.run_cmd([
            ff, "-hide_banner", "-v", "error", "-y",
            "-f", "lavfi", "-i", "color=c=0xe9e8e6:s=480x360:d=4:r=24",
            "-vf", "drawbox=x=60:y=50:w=180:h=140:color=0x8b1a2b:t=fill",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
            cls.rebuild_mp4,
        ])
        if r.returncode != 0:
            raise RuntimeError(f"failed creating sample_rebuild.mp4: {r.stderr}")

        # 4. WAVs for sfx_lab analyze & audition.
        cls.sfx_wav = os.path.join(cls.media, "pop.wav")
        cls.voice_wav = os.path.join(cls.media, "voice.wav")
        r1 = C.run_cmd([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=450:r=48000:d=0.35", "-af", "afade=t=in:d=0.02,afade=t=out:st=0.1:d=0.25", cls.sfx_wav])
        r2 = C.run_cmd([ff, "-v", "error", "-y", "-f", "lavfi", "-i", "sine=f=180:r=48000:d=3.5", cls.voice_wav])
        if r1.returncode != 0 or r2.returncode != 0:
            raise RuntimeError("failed creating sample WAV fixtures")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_01_doctor(self):
        r = run_reva(self.ws, "doctor")
        self.assertIn("ffmpeg", r.stdout)
        self.assertIn("yt-dlp", r.stdout)
        self.assertIn("status     OK", r.stdout)

    def test_02_scrape_wide_and_workflow(self):
        run_reva(self.ws, "scrape", "demo-wide", self.wide_mp4, "--style", "demo-style", "--beats", "4")
        sdir = os.path.join(self.ws, "demo-wide")

        for rel in (
            "study.json",
            "dossier.md",
            "ref/teardown.json",
            "ref/measure.json",
            "ref/sound.json",
            "ref/transcript.json",
            "ref/transcript.txt",
            "ref/script.txt",
            "ref/contact-sheet-1.jpg",
            "style/demo-style/demo-style.style.json",
            "style/demo-style/demo-style.md",
            "style/demo-style/test/beats.json",
            "style/demo-style/test/beats-preview.jpg",
        ):
            self.assertTrue(os.path.exists(os.path.join(sdir, rel)), f"missing {rel}")

        with open(os.path.join(sdir, "ref", "sound.json"), encoding="utf-8") as fp:
            snd = json.load(fp)
        self.assertTrue(snd["stereo_separation"])
        self.assertLess(snd["duration_sec"], 12.0)
        self.assertGreaterEqual(snd["event_count"], 2)
        self.assertGreater(snd["events_per_min"], 10.0)

        with open(os.path.join(sdir, "ref", "measure.json"), encoding="utf-8") as fp:
            ms = json.load(fp)
        self.assertEqual(ms["aspect_ratio"], "16:9")
        self.assertGreaterEqual(ms["cuts"]["count"], 2)
        self.assertGreaterEqual(ms["motion"]["still"], 1)
        self.assertGreaterEqual(ms["motion"]["moving"], 1)

        style_file = os.path.join(sdir, "style", "demo-style", "demo-style.style.json")
        with open(style_file, "rb") as fp:
            self.assertFalse(fp.read(3).startswith(b"\xef\xbb\xbf"), "style json must not have UTF-8 BOM")
        with open(style_file, encoding="utf-8") as fp:
            st = json.load(fp)
        self.assertEqual(st["direction"]["default_aspect"], "16:9")
        self.assertGreater(st["direction"]["narration"]["wpm"]["value"], 0)
        self.assertTrue(len(st["look"]["colors"]["palette"]) >= 2)

        with open(os.path.join(sdir, "style", "demo-style", "test", "beats.json"), encoding="utf-8") as fp:
            beats = json.load(fp)
        self.assertEqual(len(beats), 4)
        for b in beats:
            self.assertTrue(os.path.exists(os.path.join(sdir, "style", "demo-style", "test", b["ref"])))
            self.assertNotIn("no subtitles", b["narration"])

        # Add technique, grab stills & colors, compare with mismatched aspect, verify, export skill.
        run_reva(self.ws, "add", "demo-wide", "card-scene", "--from", "0", "--to", "3")
        theirs = os.path.join(sdir, "card-scene", "theirs")
        self.assertTrue(os.path.exists(os.path.join(theirs, "_strip_0-3.jpg")))
        leftover_strip_frames = [f for f in os.listdir(theirs) if re.match(r"^s\d+\.jpg$", f)]
        self.assertEqual(leftover_strip_frames, [])

        with open(os.path.join(sdir, "card-scene", "notes.md"), encoding="utf-8") as fp:
            notes = fp.read()
        self.assertIn("640x360", notes)

        run_reva(self.ws, "stills", "demo-wide", "card-scene", "--at", "1.5")
        self.assertTrue(os.path.exists(os.path.join(theirs, "full_1_5.png")))
        run_reva(self.ws, "colors", "demo-wide", "card-scene", "--at", "1.5")
        run_reva(self.ws, "colors", "demo-wide")

        run_reva(
            self.ws, "compare", "demo-wide", "card-scene",
            "--mine", self.rebuild_mp4, "--mine-at", "1,2", "--ref-at", "0.5,2.5",
        )
        self.assertTrue(os.path.exists(os.path.join(sdir, "card-scene", "compare.jpg")))
        self.assertFalse(os.path.exists(os.path.join(sdir, "card-scene", "_mine_0.png")))

        run_reva(self.ws, "verify", "demo-wide", "card-scene", "--note", "Eye-checked synthetic match")
        run_reva(self.ws, "skill", "demo-wide")
        with open(os.path.join(sdir, "skill-export.md"), encoding="utf-8") as fp:
            skill_md = fp.read()
        self.assertIn("[VERIFIED] card-scene", skill_md)

        # Placeholder guard must reject unfinished <TODO:...> template on deliver.
        mock_app = os.path.join(self.tmp.name, "mock_app")
        os.makedirs(os.path.join(mock_app, "styles"), exist_ok=True)
        os.makedirs(os.path.join(mock_app, "scripts"), exist_ok=True)
        with open(os.path.join(mock_app, "scripts", "style-check.js"), "w", encoding="utf-8") as fp:
            fp.write("console.log('MOCK OK');\n")

        blocked = run_reva(self.ws, "deliver", "demo-wide", "--app", mock_app, check=False)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("placeholder", blocked.stderr + blocked.stdout)

        # Fill placeholders cleanly in style file & verify against REAL Automated-Lunch-Free style-check.js!
        completed = _fill_placeholders(st)
        completed_path = os.path.join(self.tmp.name, "completed.style.json")
        with open(completed_path, "w", encoding="utf-8") as fp:
            json.dump(completed, fp, indent=2)
        real_app = C.find_app()
        if real_app:
            chk = C.run_cmd(["node", os.path.join(real_app, "scripts", "style-check.js"), completed_path], cwd=real_app)
            self.assertEqual(chk.returncode, 0, f"real style-check failed:\n{chk.stdout}\n{chk.stderr}")
            self.assertIn("reference style", chk.stdout)

        # Also test reva deliver end-to-end into isolated mock_app.
        with open(style_file, "w", encoding="utf-8") as fp:
            json.dump(completed, fp, indent=2)
        run_reva(self.ws, "deliver", "demo-wide", "--app", mock_app)
        self.assertTrue(os.path.exists(os.path.join(mock_app, "styles", "demo-style", "demo-style.style.json")))

        st_out = run_reva(self.ws, "status")
        self.assertIn("demo-wide", st_out.stdout)

    def test_03_scrape_vertical_mono_fast_cuts(self):
        run_reva(self.ws, "scrape", "demo-short", self.short_mp4)
        sdir = os.path.join(self.ws, "demo-short")
        with open(os.path.join(sdir, "ref", "measure.json"), encoding="utf-8") as fp:
            ms = json.load(fp)
        self.assertEqual(ms["aspect_ratio"], "9:16")
        self.assertGreater(ms["motion"]["samples"], 0)
        with open(os.path.join(sdir, "ref", "sound.json"), encoding="utf-8") as fp:
            snd = json.load(fp)
        self.assertFalse(snd["stereo_separation"])
        self.assertIsNone(snd["events_per_min"])

    def test_04_sfx_analyze_and_audition(self):
        sfx_script = os.path.join(SCRIPTS, "sfx_lab.py")
        r = C.run_cmd([sys.executable, sfx_script, "analyze", self.sfx_wav])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("pop.wav", r.stdout)

        out_mp4 = os.path.join(self.tmp.name, "audition.mp4")
        r2 = C.run_cmd([
            sys.executable, sfx_script, "audition", self.sfx_wav,
            "--voice", self.voice_wav, "--voice-at", "0", "--out", out_mp4,
        ])
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertTrue(os.path.exists(out_mp4))
        self.assertFalse(os.path.exists(os.path.join(self.tmp.name, "_audition")))


if __name__ == "__main__":
    unittest.main()
