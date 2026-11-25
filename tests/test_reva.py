#!/usr/bin/env python3
"""Automated unit + FFmpeg end-to-end tests for reva_code, reva_style, and unified reva."""
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
REVA_CODE_PY = os.path.join(REPO, "reva_code.py")
REVA_LAB_PY = os.path.join(REPO, "reva_lab.py")
REVA_STYLE_PY = os.path.join(REPO, "reva_style.py")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import _common as C
import style_kit


def run_cli(entry, workspace, *args, lab_dir=None, check=True):
    env = os.environ.copy()
    env["REVA_WORKSPACE"] = workspace
    if lab_dir:
        env["REVA_LAB_DIR"] = lab_dir
    r = subprocess.run(
        [sys.executable, entry, *map(str, args)],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and r.returncode != 0:
        raise AssertionError(
            f"{os.path.basename(entry)} {' '.join(map(str, args))} failed ({r.returncode}):\n"
            f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
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

    def test_find_placeholders(self):
        obj = {"a": "clean", "b": ["<TODO: fill>", {"c": "value <ok>"}]}
        hits = style_kit.find_placeholders(obj)
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0][0], "b[0]")


class TestRevaSplitTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="reva_e2e_")
        cls.ws = os.path.join(cls.tmp.name, "studies")
        cls.media = os.path.join(cls.tmp.name, "media")
        cls.lab_dir = os.path.join(cls.tmp.name, "lab")
        os.makedirs(cls.ws, exist_ok=True)
        os.makedirs(cls.media, exist_ok=True)
        shutil.copytree(os.path.join(REPO, "lab"), cls.lab_dir)
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

    def test_01_doctors_and_isolation(self):
        rc = run_cli(REVA_CODE_PY, self.ws, "doctor")
        self.assertIn("REVA CODE DOCTOR", rc.stdout)
        self.assertNotIn("Automated-Lunch-Free", rc.stdout)
        self.assertIn("status     OK", rc.stdout)

        rs = run_cli(REVA_STYLE_PY, self.ws, "doctor")
        self.assertIn("REVA STYLE DOCTOR", rs.stdout)
        self.assertIn("status     OK", rs.stdout)

        # CLI isolation: coding tool must reject style-only cmds, and vice versa.
        self.assertNotEqual(run_cli(REVA_CODE_PY, self.ws, "deliver", "x", check=False).returncode, 0)
        self.assertNotEqual(run_cli(REVA_STYLE_PY, self.ws, "add", "x", "tech", "--from", "0", "--to", "1", check=False).returncode, 0)

    def test_02_reva_code_e2e_with_grid_and_skill(self):
        from PIL import Image

        run_cli(REVA_CODE_PY, self.ws, "scrape", "code-wide", self.wide_mp4)
        sdir = os.path.join(self.ws, "code-wide")
        for rel in ("study.json", "dossier.md", "ref/teardown.json", "ref/measure.json", "ref/sound.json", "ref/transcript.json", "ref/contact-sheet-1.jpg"):
            self.assertTrue(os.path.exists(os.path.join(sdir, rel)), f"missing {rel}")
        self.assertFalse(os.path.exists(os.path.join(sdir, "style")))

        with open(os.path.join(sdir, "ref", "sound.json"), encoding="utf-8") as fp:
            snd = json.load(fp)
        self.assertTrue(snd["stereo_separation"])
        self.assertLess(snd["duration_sec"], 12.0)
        self.assertGreaterEqual(snd["event_count"], 2)

        with open(os.path.join(sdir, "ref", "measure.json"), encoding="utf-8") as fp:
            ms = json.load(fp)
        self.assertEqual(ms["aspect_ratio"], "16:9")
        self.assertGreaterEqual(ms["motion"]["still"], 1)
        self.assertGreaterEqual(ms["motion"]["moving"], 1)

        # Isolate 1 technique with --grid pixel coordinate overlays.
        run_cli(REVA_CODE_PY, self.ws, "add", "code-wide", "card-scene", "--from", "0", "--to", "3", "--grid")
        theirs = os.path.join(sdir, "card-scene", "theirs")
        self.assertTrue(os.path.exists(os.path.join(theirs, "_strip_0-3.jpg")))
        self.assertEqual([f for f in os.listdir(theirs) if re.match(r"^s\d+\.jpg$", f)], [])

        run_cli(REVA_CODE_PY, self.ws, "stills", "code-wide", "card-scene", "--at", "1.5", "--grid")
        full_png = os.path.join(theirs, "full_1_5.png")
        grid_png = os.path.join(theirs, "grid_1_5.png")
        self.assertTrue(os.path.exists(full_png))
        self.assertTrue(os.path.exists(grid_png))
        with Image.open(grid_png) as gim:
            self.assertEqual(gim.size, (640, 360))

        with open(os.path.join(sdir, "card-scene", "notes.md"), encoding="utf-8") as fp:
            notes = fp.read()
        self.assertIn("640x360", notes)
        self.assertIn("Rendering Stack Hypothesis", notes)

        run_cli(REVA_CODE_PY, self.ws, "colors", "code-wide", "card-scene", "--at", "1.5")
        run_cli(REVA_CODE_PY, self.ws, "colors", "code-wide")

        run_cli(
            REVA_CODE_PY, self.ws, "compare", "code-wide", "card-scene",
            "--mine", self.rebuild_mp4, "--mine-at", "1,2", "--ref-at", "0.5,2.5",
        )
        self.assertTrue(os.path.exists(os.path.join(sdir, "card-scene", "compare.jpg")))
        self.assertFalse(os.path.exists(os.path.join(sdir, "card-scene", "_mine_0.png")))

        run_cli(REVA_CODE_PY, self.ws, "verify", "code-wide", "card-scene", "--note", "Eye-checked synthetic match")
        run_cli(REVA_CODE_PY, self.ws, "skill", "code-wide")
        with open(os.path.join(sdir, "skill-export.md"), encoding="utf-8") as fp:
            self.assertIn("[VERIFIED] card-scene", fp.read())

        st_out = run_cli(REVA_CODE_PY, self.ws, "status")
        self.assertIn("[verified ]", st_out.stdout)

    def test_03_reva_style_e2e_with_check_and_deliver(self):
        # Style scrape defaults style_id = study name when --style is omitted.
        run_cli(REVA_STYLE_PY, self.ws, "scrape", "demo-style", self.wide_mp4, "--beats", "4")
        sdir = os.path.join(self.ws, "demo-style")
        style_file = os.path.join(sdir, "style", "demo-style", "demo-style.style.json")
        self.assertTrue(os.path.exists(style_file))
        self.assertTrue(os.path.exists(os.path.join(sdir, "style", "demo-style", "demo-style.md")))
        self.assertTrue(os.path.exists(os.path.join(sdir, "style", "demo-style", "test", "beats.json")))
        self.assertTrue(os.path.exists(os.path.join(sdir, "style", "demo-style", "test", "beats-preview.jpg")))

        with open(style_file, "rb") as fp:
            self.assertFalse(fp.read(3).startswith(b"\xef\xbb\xbf"), "style json must not have UTF-8 BOM")
        with open(style_file, encoding="utf-8") as fp:
            st = json.load(fp)
        self.assertEqual(st["direction"]["default_aspect"], "16:9")

        with open(os.path.join(sdir, "style", "demo-style", "test", "beats.json"), encoding="utf-8") as fp:
            beats = json.load(fp)
        self.assertEqual(len(beats), 4)
        for b in beats:
            self.assertTrue(os.path.exists(os.path.join(sdir, "style", "demo-style", "test", b["ref"])))
            self.assertNotIn("no subtitles", b["narration"])

        # Dry-run check MUST fail while <TODO:...> placeholders remain.
        bad_chk = run_cli(REVA_STYLE_PY, self.ws, "check", "demo-style", check=False)
        self.assertNotEqual(bad_chk.returncode, 0)
        self.assertIn("placeholders", bad_chk.stdout)

        # Fill placeholders & test dry-run check against REAL Automated-Lunch-Free style-check.js!
        completed = _fill_placeholders(st)
        with open(style_file, "w", encoding="utf-8") as fp:
            json.dump(completed, fp, indent=2)
        ok_chk = run_cli(REVA_STYLE_PY, self.ws, "check", "demo-style")
        self.assertIn("placeholders 0 (OK)", ok_chk.stdout)
        if C.find_app():
            self.assertIn("app check    OK", ok_chk.stdout)

        # Deliver into isolated mock_app (never touching real Automated-Lunch-Free/styles/).
        mock_app = os.path.join(self.tmp.name, "mock_app")
        os.makedirs(os.path.join(mock_app, "styles"), exist_ok=True)
        os.makedirs(os.path.join(mock_app, "scripts"), exist_ok=True)
        with open(os.path.join(mock_app, "scripts", "style-check.js"), "w", encoding="utf-8") as fp:
            fp.write("console.log('MOCK OK');\n")

        run_cli(REVA_STYLE_PY, self.ws, "deliver", "demo-style", "--app", mock_app)
        self.assertTrue(os.path.exists(os.path.join(mock_app, "styles", "demo-style", "demo-style.style.json")))

        st_out = run_cli(REVA_STYLE_PY, self.ws, "status")
        self.assertIn("ready", st_out.stdout)
        self.assertIn("delivered:passed", st_out.stdout)

    def test_04_vertical_mono_fast_cuts_and_router(self):
        run_cli(REVA_PY, self.ws, "code", "scrape", "code-short", self.short_mp4)
        sdir = os.path.join(self.ws, "code-short")
        with open(os.path.join(sdir, "ref", "measure.json"), encoding="utf-8") as fp:
            ms = json.load(fp)
        self.assertEqual(ms["aspect_ratio"], "9:16")
        self.assertGreater(ms["motion"]["samples"], 0)
        with open(os.path.join(sdir, "ref", "sound.json"), encoding="utf-8") as fp:
            snd = json.load(fp)
        self.assertFalse(snd["stereo_separation"])
        self.assertIsNone(snd["events_per_min"])

        r_doc = run_cli(REVA_PY, self.ws, "doctor")
        self.assertIn("status     OK", r_doc.stdout)
        r_cs = run_cli(REVA_PY, self.ws, "code", "status")
        self.assertIn("code-short", r_cs.stdout)
        r_ss = run_cli(REVA_PY, self.ws, "style", "status")
        self.assertIn("demo-style", r_ss.stdout)

    def test_05_sfx_analyze_and_audition(self):
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

    def test_06_lab_engines_register_and_library_search(self):
        eng_res = run_cli(REVA_LAB_PY, self.ws, "engines", "--json", lab_dir=self.lab_dir)
        inv = json.loads(eng_res.stdout)
        by_id = {e["id"]: e for e in inv["engines"]}
        self.assertIn("ffmpeg-compositor", by_id)
        self.assertEqual(by_id["ffmpeg-compositor"]["status"], "ready")
        self.assertIn("automated-lunch-free", by_id)

        srch = run_cli(REVA_LAB_PY, self.ws, "library", "search", "animated map", lab_dir=self.lab_dir)
        self.assertIn("animated-route-map", srch.stdout)

        # Register a brand-new code-callable engine dynamically and confirm discovery.
        run_cli(
            REVA_LAB_PY, self.ws, "register", "nextgen-volumetrics",
            "--name", "NextGen Volumetrics CLI",
            "--kind", "code-3d",
            "--strengths", "volumetrics,fog,3d-explainer",
            "--callable-via", "python -V",
            "--bin", "python",
            "--install-hint", "pip install nextgen-vol",
            lab_dir=self.lab_dir,
        )
        eng_after = json.loads(run_cli(REVA_LAB_PY, self.ws, "engines", "--json", lab_dir=self.lab_dir).stdout)
        new_eng = next(e for e in eng_after["engines"] if e["id"] == "nextgen-volumetrics")
        self.assertEqual(new_eng["status"], "ready")

        har = run_cli(REVA_LAB_PY, self.ws, "harnesses", lab_dir=self.lab_dir)
        self.assertIn("ffmpeg-compositor", har.stdout)

    def test_07_multi_tool_bakeoff_and_cross_video_reuse_e2e(self):
        # --- Video 1: scrape, isolate, bench trial, bake-off compare, verdict, verify + promote ---
        run_cli(REVA_CODE_PY, self.ws, "scrape", "v1-map", self.wide_mp4, lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "add", "v1-map", "route-map", "--from", "0", "--to", "3", "--grid", lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "bench", "v1-map", "route-map", "--tool", "ffmpeg-compositor", lab_dir=self.lab_dir)

        bench_dir = os.path.join(self.ws, "v1-map", "route-map", "bench", "ffmpeg-compositor")
        render_py = os.path.join(bench_dir, "render.py")
        self.assertTrue(os.path.exists(render_py))
        self.assertTrue(os.path.exists(os.path.join(bench_dir, "bench.json")))

        # Actually run the copied starter harness to render an MP4 clip.
        bench_out = os.path.join(bench_dir, "out.mp4")
        rr = C.run_cmd([sys.executable, render_py, bench_out])
        self.assertEqual(rr.returncode, 0, rr.stderr)
        self.assertTrue(os.path.exists(bench_out))

        # Multi-tool bake-off comparisons.
        run_cli(
            REVA_CODE_PY, self.ws, "compare", "v1-map", "route-map",
            "--tool", "ffmpeg-compositor", "--mine", bench_out, "--mine-at", "1,2", "--ref-at", "0.5,2.5",
            lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_CODE_PY, self.ws, "compare", "v1-map", "route-map",
            "--tool", "hyperframes-2d", "--mine", self.rebuild_mp4, "--mine-at", "1,2", "--ref-at", "0.5,2.5",
            lab_dir=self.lab_dir,
        )
        tech_dir = os.path.join(self.ws, "v1-map", "route-map")
        self.assertTrue(os.path.exists(os.path.join(tech_dir, "compare_ffmpeg-compositor.jpg")))
        self.assertTrue(os.path.exists(os.path.join(tech_dir, "compare_hyperframes-2d.jpg")))
        self.assertTrue(os.path.exists(os.path.join(tech_dir, "compare.jpg")))

        run_cli(
            REVA_CODE_PY, self.ws, "verdict", "v1-map", "route-map",
            "--winner", "ffmpeg-compositor",
            "--rejected", "hyperframes-2d:overkill for test",
            "--note", "Matched palette and layout",
            lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_CODE_PY, self.ws, "verify", "v1-map", "route-map",
            "--tool", "ffmpeg-compositor", "--promote",
            "--id", "test-route-map", "--category", "animated-map",
            "--tags", "map,route,trail", "--note", "Eye-checked bake-off winner",
            lab_dir=self.lab_dir,
        )
        run_cli(REVA_CODE_PY, self.ws, "skill", "v1-map", lab_dir=self.lab_dir)
        with open(os.path.join(self.ws, "v1-map", "skill-export.md"), encoding="utf-8") as fp:
            exp = fp.read()
        self.assertIn("Winning engine:** `ffmpeg-compositor`", exp)
        self.assertIn("`hyperframes-2d` (overkill for test)", exp)
        self.assertIn("Promoted to library:** `test-route-map`", exp)

        # --- Video 2: recommend discovers Video 1 pattern, reuse links it, promote appends v2-geo ---
        run_cli(REVA_CODE_PY, self.ws, "scrape", "v2-geo", self.wide_mp4, lab_dir=self.lab_dir)
        rec_out = run_cli(REVA_LAB_PY, self.ws, "recommend", "v2-geo", "--tags", "animated-map,route", lab_dir=self.lab_dir)
        self.assertIn("test-route-map", rec_out.stdout)

        add_out = run_cli(REVA_CODE_PY, self.ws, "add", "v2-geo", "geo-route", "--from", "0", "--to", "3", lab_dir=self.lab_dir)
        self.assertIn("route", add_out.stdout.lower())

        run_cli(REVA_CODE_PY, self.ws, "reuse", "v2-geo", "geo-route", "--pattern", "test-route-map", lab_dir=self.lab_dir)
        with open(os.path.join(self.ws, "v2-geo", "geo-route", "notes.md"), encoding="utf-8") as fp:
            v2_notes = fp.read()
        self.assertIn("Reused Baseline (from `test-route-map`)", v2_notes)
        self.assertIn("hyperframes-2d (overkill for test)", v2_notes)

        run_cli(
            REVA_CODE_PY, self.ws, "compare", "v2-geo", "geo-route",
            "--tool", "ffmpeg-compositor", "--mine", self.rebuild_mp4, "--mine-at", "1,2", "--ref-at", "0.5,2.5",
            lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_CODE_PY, self.ws, "verify", "v2-geo", "geo-route",
            "--tool", "ffmpeg-compositor", "--promote", "--pattern-id", "test-route-map",
            lab_dir=self.lab_dir,
        )
        with open(os.path.join(self.lab_dir, "library.json"), encoding="utf-8") as fp:
            lib = json.load(fp)
        pat = next(p for p in lib["patterns"] if p["id"] == "test-route-map")
        self.assertEqual(pat["used_in"], ["v1-map", "v2-geo"])

    def test_08_router_lab_and_style_promote(self):
        r1 = run_cli(REVA_PY, self.ws, "lab", "engines", lab_dir=self.lab_dir)
        self.assertIn("REVA ENGINEERING LAB", r1.stdout)
        r2 = run_cli(REVA_PY, self.ws, "library", "search", "animated map", lab_dir=self.lab_dir)
        self.assertIn("animated-route-map", r2.stdout)

        # Ensure demo-style from test_03 (or create one if test_08 runs standalone) can be promoted.
        if not os.path.exists(os.path.join(self.ws, "demo-style", "study.json")):
            run_cli(REVA_STYLE_PY, self.ws, "scrape", "demo-style", self.wide_mp4, "--beats", "2", lab_dir=self.lab_dir)
            sf = os.path.join(self.ws, "demo-style", "style", "demo-style", "demo-style.style.json")
            with open(sf, encoding="utf-8") as fp:
                sdata = _fill_placeholders(json.load(fp))
            with open(sf, "w", encoding="utf-8") as fp:
                json.dump(sdata, fp, indent=2)

        rp = run_cli(REVA_LAB_PY, self.ws, "promote-style", "demo-style", "--tags", "clean,cards", lab_dir=self.lab_dir)
        self.assertIn("prompt-style-demo-style", rp.stdout)


if __name__ == "__main__":
    unittest.main()
