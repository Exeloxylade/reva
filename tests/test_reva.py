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

    def test_09_silent_asmr_scaffold_and_sync_app(self):
        run_cli(
            REVA_STYLE_PY, self.ws, "scrape", "asmr-cook", self.short_mp4,
            "--beats", "2", "--framing", "fixed-tabletop", "--silent-asmr", "--domain", "culinary",
            lab_dir=self.lab_dir,
        )
        sf = os.path.join(self.ws, "asmr-cook", "style", "asmr-cook", "asmr-cook.style.json")
        with open(sf, encoding="utf-8") as fp:
            sdata = json.load(fp)
        self.assertEqual(sdata["look"]["framing"], "fixed-tabletop")
        self.assertEqual(sdata["direction"]["voice"], "off")
        self.assertEqual(sdata["direction"]["prompt_profile"], "silent-process-asmr")
        self.assertEqual(sdata["direction"]["domain"], "culinary")
        self.assertFalse(sdata["direction"]["graphics"])

        completed = _fill_placeholders(sdata)
        with open(sf, "w", encoding="utf-8") as fp:
            json.dump(completed, fp, indent=2)
        chk = run_cli(REVA_STYLE_PY, self.ws, "check", "asmr-cook", lab_dir=self.lab_dir)
        self.assertIn("placeholders 0 (OK)", chk.stdout)

        # Build a mock_app with one validated silent-ASMR style and sync into isolated lab_dir.
        mock_app = os.path.join(self.tmp.name, "mock_app_sync")
        os.makedirs(os.path.join(mock_app, "styles", "asmr-cook"), exist_ok=True)
        os.makedirs(os.path.join(mock_app, "scripts"), exist_ok=True)
        with open(os.path.join(mock_app, "scripts", "style-check.js"), "w", encoding="utf-8") as fp:
            fp.write("console.log('MOCK OK');\n")
        shutil.copy2(sf, os.path.join(mock_app, "styles", "asmr-cook", "asmr-cook.style.json"))

        sync_res = run_cli(REVA_LAB_PY, self.ws, "sync-app", "--app", mock_app, lab_dir=self.lab_dir)
        self.assertIn("prompt-style-asmr-cook", sync_res.stdout)

        s_asmr = run_cli(REVA_LAB_PY, self.ws, "library", "search", "asmr", lab_dir=self.lab_dir)
        self.assertIn("prompt-style-asmr-cook", s_asmr.stdout)
        s_tab = run_cli(REVA_LAB_PY, self.ws, "library", "search", "fixed-tabletop", lab_dir=self.lab_dir)
        self.assertIn("prompt-style-asmr-cook", s_tab.stdout)

    def test_10_transcribe_and_research_brain_e2e(self):
        # 1. Scraping video with audio + no subs auto-extracts ref/audio.mp3 and seeds research/brief.{json,md}.
        run_cli(REVA_PY, self.ws, "code", "scrape", "brain-short", self.short_mp4, lab_dir=self.lab_dir)
        sdir = os.path.join(self.ws, "brain-short")
        self.assertTrue(os.path.exists(os.path.join(sdir, "ref", "audio.mp3")))
        self.assertTrue(os.path.exists(os.path.join(sdir, "research", "brief.json")))
        self.assertTrue(os.path.exists(os.path.join(sdir, "research", "brief.md")))

        with open(os.path.join(sdir, "study.json"), encoding="utf-8") as fp:
            st0 = json.load(fp)
        self.assertEqual(st0["transcript_status"], "needed")
        self.assertEqual(st0["research"]["status"], "draft")

        # 2. --from-file works with Whisper/timing.json segments schema AND updates measure/dossier/beats.
        seg_json = os.path.join(self.tmp.name, "timing_segments.json")
        with open(seg_json, "w", encoding="utf-8") as fp:
            json.dump({
                "segments": [
                    {"start": 0.2, "end": 2.3, "text": "Reinforced concrete hooks need 135 degree bends per SNI 2847."},
                    {"start": 2.6, "end": 4.8, "text": "Minimum 4 cm indoor concrete cover prevents rebar corrosion."},
                ]
            }, fp)
        run_cli(REVA_PY, self.ws, "transcribe", "brain-short", "--from-file", seg_json, "--lang", "en", lab_dir=self.lab_dir)
        self.assertTrue(os.path.exists(os.path.join(sdir, "ref", "transcript.json")))
        self.assertTrue(os.path.exists(os.path.join(sdir, "ref", "transcript.txt")))
        self.assertTrue(os.path.exists(os.path.join(sdir, "ref", "script.txt")))
        self.assertTrue(os.path.exists(os.path.join(sdir, "ref", "ref.transcribed.srt")))

        run_cli(REVA_STYLE_PY, self.ws, "scaffold", "brain-short", lab_dir=self.lab_dir)
        run_cli(REVA_STYLE_PY, self.ws, "beats", "brain-short", "--auto", "--count", "2", lab_dir=self.lab_dir)
        with open(os.path.join(sdir, "style", "brain-short", "test", "beats.json"), encoding="utf-8") as fp:
            beats = json.load(fp)
        self.assertNotIn("no subtitles", beats[0]["narration"])
        self.assertIn("Reinforced concrete hooks", beats[0]["narration"])

        # Re-importing from .srt via --force also works cleanly.
        srt_path = os.path.join(self.tmp.name, "reimport.srt")
        with open(srt_path, "w", encoding="utf-8") as fp:
            fp.write(
                "1\n00:00:00,200 --> 00:00:02,400\nStirrup hook 135 degrees per SNI 2847.\n\n"
                "2\n00:00:02,600 --> 00:00:04,900\nConcrete cover stays 4 cm indoors.\n"
            )
        run_cli(REVA_PY, self.ws, "transcribe", "brain-short", "--from-file", srt_path, "--lang", "en", "--force", lab_dir=self.lab_dir)

        # Strict research check fails while research is still draft.
        sf = os.path.join(sdir, "style", "brain-short", "brain-short.style.json")
        with open(sf, encoding="utf-8") as fp:
            sdata = _fill_placeholders(json.load(fp))
        with open(sf, "w", encoding="utf-8") as fp:
            json.dump(sdata, fp, indent=2)
        strict_bad = run_cli(REVA_STYLE_PY, self.ws, "check", "brain-short", "--strict-research", lab_dir=self.lab_dir, check=False)
        self.assertNotEqual(strict_bad.returncode, 0)

        # 3. Silent mode works cleanly on ASMR/silent clips.
        run_cli(REVA_PY, self.ws, "code", "scrape", "brain-silent", self.short_mp4, lab_dir=self.lab_dir)
        run_cli(REVA_PY, self.ws, "transcribe", "brain-silent", "--silent", lab_dir=self.lab_dir)
        with open(os.path.join(self.ws, "brain-silent", "study.json"), encoding="utf-8") as fp:
            self.assertEqual(json.load(fp)["transcript_status"], "silent")

        # 4. Research complete refuses empty brief unless concepts/sources exist.
        empty_comp = run_cli(
            REVA_PY, self.ws, "research", "complete", "brain-short",
            "--what", "Concrete stirrup rules", "--domain", "civil-engineering",
            lab_dir=self.lab_dir, check=False,
        )
        self.assertNotEqual(empty_comp.returncode, 0)

        # Add concept, local source asset, visual item, and complete brief.
        ref_note_file = os.path.join(self.tmp.name, "sni2847-notes.txt")
        with open(ref_note_file, "w", encoding="utf-8") as fp:
            fp.write("SNI 2847 135-degree seismic hook >= 6d and >= 75mm.\n")

        run_cli(
            REVA_PY, self.ws, "research", "add-concept", "brain-short",
            "--term", "3d-explainer cutaway",
            "--meaning", "135-degree seismic hoop confinement inside concrete core",
            "--visual", "Bent bar around corner longitudinal rebar with angle arc",
            "--at", "0.5,1.8",
            lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_PY, self.ws, "research", "add-source", "brain-short",
            "--title", "SNI 2847 Stirrup Hook Provision",
            "--kind", "standard",
            "--url", "https://example.org/sni-2847",
            "--takeaway", "135 deg hook prevents stirrup opening under lateral seismic spalling",
            "--asset", ref_note_file,
            lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_PY, self.ws, "research", "add-visual", "brain-short",
            "--item", "Corner rebar stirrup bend",
            "--why", "Must show inner bend diameter + 6d leg extension",
            "--needs-ref",
            lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_PY, self.ws, "research", "complete", "brain-short",
            "--what", "Reinforced concrete seismic stirrup hook and cover explainer",
            "--domain", "civil-engineering",
            "--thesis", "Concrete failure happens when confinement hooks open at 90 degrees or cover is too thin",
            "--implication", "Use 3D structural cutaway showing concrete spalling and 135-degree hook angle gauge",
            lab_dir=self.lab_dir,
        )
        self.assertTrue(os.path.exists(os.path.join(sdir, "research", "assets", "sni2847-notes.txt")))

        # 5. add + bench inherit transcript excerpt & research context.
        run_cli(REVA_CODE_PY, self.ws, "add", "brain-short", "stirrup-hook", "--from", "0", "--to", "2.5", lab_dir=self.lab_dir)
        with open(os.path.join(sdir, "stirrup-hook", "notes.md"), encoding="utf-8") as fp:
            notes = fp.read()
        self.assertIn("Subject Context & Spoken Narration", notes)
        self.assertIn("Stirrup hook 135 degrees per SNI 2847.", notes)
        self.assertIn("civil-engineering", notes)

        run_cli(REVA_CODE_PY, self.ws, "bench", "brain-short", "stirrup-hook", "--tool", "ffmpeg-compositor", lab_dir=self.lab_dir)
        with open(os.path.join(sdir, "stirrup-hook", "bench", "ffmpeg-compositor", "bench.json"), encoding="utf-8") as fp:
            bcfg = json.load(fp)
        self.assertTrue(bcfg["transcript_excerpt"])
        self.assertEqual(bcfg["research_context"]["status"], "researched")

        # 6. recommend picks up researched domain & concept tokens.
        rec = json.loads(run_cli(REVA_LAB_PY, self.ws, "recommend", "brain-short", "--json", lab_dir=self.lab_dir).stdout)
        self.assertIn("civil-engineering", rec["signals"])

        # 7. skill-export.md includes research section & has no missing transcript/research gaps.
        run_cli(REVA_CODE_PY, self.ws, "skill", "brain-short", lab_dir=self.lab_dir)
        with open(os.path.join(sdir, "skill-export.md"), encoding="utf-8") as fp:
            exp = fp.read()
        self.assertIn("## Subject Understanding & Research Sources", exp)
        self.assertIn("SNI 2847 Stirrup Hook Provision", exp)
        self.assertNotIn("Transcript missing", exp)
        self.assertNotIn("Subject research brief is still", exp)

        # 8. Strict research check now passes cleanly.
        ok_strict = run_cli(REVA_STYLE_PY, self.ws, "check", "brain-short", "--strict-research", lab_dir=self.lab_dir)
        self.assertIn("transcript   OK", ok_strict.stdout)
        self.assertIn("research     OK", ok_strict.stdout)

    def test_11_visual_anatomy_bench_and_audit_gate_e2e(self):
        from PIL import Image, ImageDraw

        run_cli(REVA_PY, self.ws, "code", "scrape", "brain-audit", self.short_mp4, lab_dir=self.lab_dir)
        run_cli(REVA_PY, self.ws, "transcribe", "brain-audit", "--silent", lab_dir=self.lab_dir)
        run_cli(
            REVA_PY, self.ws, "research", "add-concept", "brain-audit",
            "--term", "Stirrup 135 hook",
            "--meaning", "Continuous closed hoop wrapping 4 corner bars with 135-deg parallel tails into core",
            "--mechanism", "Cover spalling exposes 90-deg tails, whereas 135-deg tails stay locked in core",
            "--specs", "D_bend >= 4*db; l_ext = max(6*db, 75 mm)",
            "--anatomy", "Single TubeGeometry path wraps outside corner bars then folds both ends 135-deg inward",
            "--must-show", "Single continuous loop wraps outside all 4 corner bars",
            "--must-show", "Parallel 135-deg tails penetrate core inside hoop",
            "--wrong", "Floating detached sticks or unbent outward tail",
            "--at", "0,3",
            lab_dir=self.lab_dir,
        )
        # Internet evidence gate blocks complete until a verified external URL or local asset exists.
        no_ev = run_cli(
            REVA_PY, self.ws, "research", "complete", "brain-audit",
            "--what", "SNI 2847 stirrup hook anatomy check", "--domain", "civil-engineering",
            lab_dir=self.lab_dir, check=False,
        )
        self.assertNotEqual(no_ev.returncode, 0)
        self.assertIn("internet evidence gate", no_ev.stdout + no_ev.stderr)

        run_cli(
            REVA_PY, self.ws, "research", "add-source", "brain-audit",
            "--title", "SNI 2847 Table 25.3.2", "--kind", "standard",
            "--url", "https://en.wikipedia.org/wiki/Rebar",
            "--takeaway", "135-deg hook extension max(6db, 75 mm)",
            lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_PY, self.ws, "research", "complete", "brain-audit",
            "--what", "SNI 2847 stirrup hook anatomy check", "--domain", "civil-engineering",
            lab_dir=self.lab_dir,
        )

        # 1. add & bench seed checklist.json + anatomy_specs in bench.json
        run_cli(REVA_CODE_PY, self.ws, "add", "brain-audit", "stirrup-rig", "--from", "0", "--to", "3", lab_dir=self.lab_dir)
        sdir = os.path.join(self.ws, "brain-audit")
        tech_dir = os.path.join(sdir, "stirrup-rig")
        with open(os.path.join(tech_dir, "notes.md"), encoding="utf-8") as fp:
            notes = fp.read()
        self.assertIn("Anatomy (Stirrup 135 hook)", notes)
        self.assertIn("Avoid trap", notes)

        run_cli(REVA_CODE_PY, self.ws, "bench", "brain-audit", "stirrup-rig", "--tool", "threejs-webgl", lab_dir=self.lab_dir)
        bench_dir = os.path.join(tech_dir, "bench", "threejs-webgl")
        self.assertTrue(os.path.exists(os.path.join(bench_dir, "bench_scene.html")))
        self.assertTrue(os.path.exists(os.path.join(bench_dir, "render_bench.py")))
        with open(os.path.join(bench_dir, "bench.json"), encoding="utf-8") as fp:
            bcfg = json.load(fp)
        self.assertEqual(bcfg["checklist_items"], 2)
        self.assertGreaterEqual(len(bcfg["anatomy_specs"]), 2)

        # 2. compare supports direct PNG stills + --crop zoom + schematic banner
        p1 = os.path.join(self.tmp.name, "mine_0.png")
        p2 = os.path.join(self.tmp.name, "mine_1.png")
        schem = os.path.join(self.tmp.name, "schem.png")
        for idx, dst in enumerate((p1, p2, schem)):
            im = Image.new("RGB", (240, 320), (220 - idx * 20, 225, 230))
            d = ImageDraw.Draw(im)
            d.rectangle([50, 70, 190, 250], outline=(139, 26, 43), width=6)
            im.save(dst)

        run_cli(
            REVA_CODE_PY, self.ws, "compare", "brain-audit", "stirrup-rig",
            "--tool", "threejs-webgl", "--mine", f"{p1},{p2}", "--ref-at", "0.5,2.5",
            lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_CODE_PY, self.ws, "compare", "brain-audit", "stirrup-rig",
            "--tool", "threejs-webgl", "--mine", f"{p1},{p2}", "--ref-at", "0.5,2.5",
            "--crop", "0.2,0.2,0.6,0.6", "--schematic", schem,
            lab_dir=self.lab_dir,
        )
        self.assertTrue(os.path.exists(os.path.join(tech_dir, "compare_threejs-webgl.jpg")))
        self.assertTrue(os.path.exists(os.path.join(tech_dir, "compare_threejs-webgl_zoom.jpg")))
        self.assertTrue(os.path.exists(p1))

        # 3. Hard visual audit gate blocks verify while pending or failing
        blk1 = run_cli(
            REVA_CODE_PY, self.ws, "verify", "brain-audit", "stirrup-rig",
            "--tool", "threejs-webgl", lab_dir=self.lab_dir, check=False,
        )
        self.assertNotEqual(blk1.returncode, 0)
        self.assertIn("visual audit gate blocked verify", blk1.stdout + blk1.stderr)

        run_cli(REVA_CODE_PY, self.ws, "audit", "brain-audit", "stirrup-rig", "--pass", "1", "--fail", "2", "--note", "needs fix", lab_dir=self.lab_dir)
        blk2 = run_cli(
            REVA_CODE_PY, self.ws, "verify", "brain-audit", "stirrup-rig",
            "--tool", "threejs-webgl", lab_dir=self.lab_dir, check=False,
        )
        self.assertNotEqual(blk2.returncode, 0)

        # 4. Passing all items unblocks verify and records 2/2 PASS in skill-export.md
        aud_ok = run_cli(REVA_CODE_PY, self.ws, "audit", "brain-audit", "stirrup-rig", "--pass", "2", "--note", "Verified in zoom", lab_dir=self.lab_dir)
        self.assertIn("2/2 pass", aud_ok.stdout)
        run_cli(REVA_CODE_PY, self.ws, "verify", "brain-audit", "stirrup-rig", "--tool", "threejs-webgl", lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "skill", "brain-audit", lab_dir=self.lab_dir)
        with open(os.path.join(sdir, "skill-export.md"), encoding="utf-8") as fp:
            exp = fp.read()
        self.assertIn("Visual audit:** `2/2 PASS`", exp)
        self.assertNotIn("unfinished visual audit checkpoint", exp)

    def test_12_internet_research_claims_fetch_and_evidence_gate(self):
        run_cli(REVA_PY, self.ws, "code", "scrape", "net-brain", self.short_mp4, lab_dir=self.lab_dir)
        sdir = os.path.join(self.ws, "net-brain")

        srt_path = os.path.join(self.tmp.name, "net_claims.srt")
        with open(srt_path, "w", encoding="utf-8") as fp:
            fp.write(
                "1\n00:00:00,200 --> 00:00:02,200\nKait sengkang 135 derajat minimal 6d atau 75 mm karena mencegah begel terbuka.\n\n"
                "2\n00:00:02,400 --> 00:00:04,500\nSelimut beton yang terkelupas membuat kait 90 derajat lepas dan besi utama buckling.\n"
            )
        run_cli(REVA_PY, self.ws, "transcribe", "net-brain", "--from-file", srt_path, "--lang", "id", lab_dir=self.lab_dir)

        cl_out = run_cli(REVA_PY, self.ws, "research", "claims", "net-brain", lab_dir=self.lab_dir)
        self.assertIn("VERIFIABLE TRANSCRIPT CLAIMS", cl_out.stdout)
        self.assertIn("135 derajat", cl_out.stdout)
        self.assertIn("query:", cl_out.stdout)

        # Offline fetch against a local HTML engineering standard page via file:// URL.
        html_path = os.path.join(self.tmp.name, "sni_2847_extract.html")
        with open(html_path, "w", encoding="utf-8") as fp:
            fp.write(
                "<!doctype html><html><head><title>SNI 2847 Seismic Hook Rule</title>"
                "<script>window.noise='skip me';</script></head><body>"
                "<p>Nav noise skipped here.</p>"
                "<p>Per SNI 2847 Tabel 25.3.2, a 135 degree seismic stirrup hook needs inside bend diameter 4db and extension max(6db, 75 mm) anchored inside the confined concrete core.</p>"
                "<p>When outer concrete cover spalls under seismic drift, a 90 degree hook loses support and pops open, causing longitudinal rebar buckling.</p>"
                "</body></html>"
            )
        from pathlib import Path
        file_url = Path(html_path).resolve().as_uri()
        f_out = run_cli(
            REVA_PY, self.ws, "research", "fetch", "net-brain", file_url,
            "--kind", "standard", "--query", "135 degree hook confined core", lab_dir=self.lab_dir,
        )
        self.assertIn("SNI 2847 Seismic Hook Rule", f_out.stdout)
        self.assertIn("135 degree seismic stirrup hook", f_out.stdout)
        self.assertNotIn("skip me", f_out.stdout)

        cached_txt = os.path.join(sdir, "research", "assets", "sni_2847_extract.txt")
        self.assertTrue(os.path.exists(cached_txt))

        # Test internet-evidence gate independently on a fresh study whose source lacks URL/asset.
        run_cli(REVA_PY, self.ws, "code", "scrape", "net-gate", self.short_mp4, lab_dir=self.lab_dir)
        run_cli(REVA_PY, self.ws, "transcribe", "net-gate", "--silent", lab_dir=self.lab_dir)
        run_cli(
            REVA_PY, self.ws, "research", "add-source", "net-gate",
            "--title", "Memory note without URL or file", "--kind", "standard",
            "--takeaway", "Not yet backed by external URL", lab_dir=self.lab_dir,
        )
        blocked = run_cli(
            REVA_PY, self.ws, "research", "complete", "net-gate",
            "--what", "Gate check", "--domain", "civil-engineering",
            lab_dir=self.lab_dir, check=False,
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn("internet evidence gate", blocked.stdout + blocked.stderr)

        # Complete net-brain (has fetched source + mechanism + specs) and propagate downstream.
        run_cli(
            REVA_PY, self.ws, "research", "add-concept", "net-brain",
            "--term", "Seismic 135 hook",
            "--meaning", "Stirrup hook anchored into confined concrete core",
            "--mechanism", "Cover spalling unbraces 90-deg hooks while 135-deg tails stay locked in core concrete",
            "--specs", "D_bend >= 4db (D10-D16); l_ext = max(6db, 75 mm)",
            "--anatomy", "Closed stirrup wraps 4 corner bars; both tails fold 135-deg inward",
            "--must-show", "Outer cover spall exposes 90-deg failure while 135-deg stays anchored in core",
            "--at", "0,4", lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_PY, self.ws, "research", "complete", "net-brain",
            "--what", "SNI 2847 seismic stirrup confinement mechanism",
            "--domain", "civil-engineering", lab_dir=self.lab_dir,
        )
        run_cli(REVA_CODE_PY, self.ws, "add", "net-brain", "stirrup-mech", "--from", "0", "--to", "4", lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "bench", "net-brain", "stirrup-mech", "--tool", "threejs-webgl", lab_dir=self.lab_dir)

        with open(os.path.join(sdir, "stirrup-mech", "notes.md"), encoding="utf-8") as fp:
            notes = fp.read()
        self.assertIn("Mechanism (Seismic 135 hook)", notes)
        self.assertIn("Verified specs:** D_bend >= 4db", notes)

        with open(os.path.join(sdir, "stirrup-mech", "bench", "threejs-webgl", "bench.json"), encoding="utf-8") as fp:
            bcfg = json.load(fp)
        self.assertEqual(bcfg["render_mode"], "schematic-clay-first")
        self.assertEqual(bcfg["anatomy_specs"][0]["specs"], "D_bend >= 4db (D10-D16); l_ext = max(6db, 75 mm)")

        run_cli(REVA_CODE_PY, self.ws, "compare", "net-brain", "stirrup-mech", "--tool", "threejs-webgl", "--mine", self.rebuild_mp4, "--mine-at", "1", "--ref-at", "1", lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "audit", "net-brain", "stirrup-mech", "--pass", "1", "--note", "schematic ok", lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "verify", "net-brain", "stirrup-mech", "--tool", "threejs-webgl", lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "skill", "net-brain", lab_dir=self.lab_dir)
        with open(os.path.join(sdir, "skill-export.md"), encoding="utf-8") as fp:
            exp = fp.read()
        self.assertIn("SNI 2847 Seismic Hook Rule", exp)
        self.assertIn("specs: D_bend >= 4db", exp)

    def test_13_research_auto_and_run_bench_workflow(self):
        from pathlib import Path
        from PIL import Image, ImageDraw

        run_cli(REVA_PY, self.ws, "code", "scrape", "auto-flow", self.short_mp4, lab_dir=self.lab_dir)
        sdir = os.path.join(self.ws, "auto-flow")

        srt_path = os.path.join(self.tmp.name, "auto_claims.srt")
        with open(srt_path, "w", encoding="utf-8") as fp:
            fp.write("1\n00:00:00,200 --> 00:00:02,500\nKait sengkang 135 derajat minimal 6d mencegah begel terbuka.\n")
        run_cli(REVA_PY, self.ws, "transcribe", "auto-flow", "--from-file", srt_path, "--lang", "id", lab_dir=self.lab_dir)

        # Prepare offline HTML + PNG fixtures for research.auto_research
        local_html = os.path.join(self.tmp.name, "auto_ref.html")
        with open(local_html, "w", encoding="utf-8") as fp:
            fp.write("<html><head><title>Offline SNI Ref</title></head><body><p>SNI 2847 requires 135 degree hook >= 6d and 75 mm inside core concrete.</p></body></html>")
        local_png = os.path.join(self.tmp.name, "auto_diag.png")
        Image.new("RGB", (320, 200), (240, 244, 248)).save(local_png)

        import research as mod_research

        orig_ws = mod_research.web_search
        orig_si = mod_research.search_images
        try:
            mod_research.web_search = lambda q, max_results=5: [
                {"title": "Offline SNI Ref", "url": Path(local_html).resolve().as_uri(), "snippet": "135 deg hook", "provider": "mock"}
            ]
            mod_research.search_images = lambda q, max_results=3, include_pdf=False: [
                {"title": "auto-diagram.png", "url": Path(local_png).resolve().as_uri(), "mime": "image/png", "width": 320, "height": 200, "description": "diag", "provider": "mock"}
            ]
            ares = mod_research.auto_research(sdir, max_claims=1, download_images=1, fetch_pages=1, max_results=3)
        finally:
            mod_research.web_search = orig_ws
            mod_research.search_images = orig_si

        self.assertEqual(len(ares["downloaded_images"]), 1)
        self.assertEqual(len(ares["fetched_pages"]), 1)
        self.assertTrue(mod_research.has_verified_source(sdir))

        run_cli(
            REVA_PY, self.ws, "research", "add-concept", "auto-flow",
            "--term", "Auto Hook 135", "--meaning", "Stirrup hook in core",
            "--must-show", "Stub schematic square passes full and zoom compare",
            "--at", "0,2", lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_PY, self.ws, "research", "complete", "auto-flow",
            "--what", "Offline auto research smoke study", "--domain", "civil-engineering",
            lab_dir=self.lab_dir,
        )

        run_cli(REVA_CODE_PY, self.ws, "add", "auto-flow", "auto-rig", "--from", "0", "--to", "3", lab_dir=self.lab_dir)
        # Stage fast deterministic render_bench.py stub in bench/threejs-webgl
        bench_dir = os.path.join(sdir, "auto-flow" if False else "auto-rig", "bench", "threejs-webgl")
        run_cli(REVA_CODE_PY, self.ws, "bench", "auto-flow", "auto-rig", "--tool", "threejs-webgl", lab_dir=self.lab_dir)
        stub_runner = os.path.join(bench_dir, "render_bench.py")
        with open(stub_runner, "w", encoding="utf-8") as fp:
            fp.write(
                "import argparse, os\n"
                "from PIL import Image, ImageDraw\n"
                "ap = argparse.ArgumentParser(); ap.add_argument('--at', default='0,1')\n"
                "a = ap.parse_args()\n"
                "here = os.path.dirname(os.path.abspath(__file__))\n"
                "for i, _ in enumerate(a.at.split(',')):\n"
                "    im = Image.new('RGB', (360, 240), (238, 243, 247))\n"
                "    ImageDraw.Draw(im).rectangle([80, 50, 280, 190], outline=(224, 122, 20), width=8)\n"
                "    im.save(os.path.join(here, f'out_{i}.png'))\n"
            )

        rb = run_cli(
            REVA_CODE_PY, self.ws, "run-bench", "auto-flow", "auto-rig",
            "--tool", "threejs-webgl", "--at", "0,1", "--ref-at", "0.5,2.5",
            lab_dir=self.lab_dir,
        )
        self.assertIn("AUDIT STATUS:", rb.stdout)
        tech_dir = os.path.join(sdir, "auto-rig")
        self.assertTrue(os.path.exists(os.path.join(tech_dir, "compare_threejs-webgl.jpg")))
        self.assertTrue(os.path.exists(os.path.join(tech_dir, "compare_threejs-webgl_zoom.jpg")))

    def test_14_structured_code_kit_promote_and_reuse_bootstrap(self):
        from PIL import Image, ImageDraw

        # Video 1 builds a custom structured RevaCAD bench, verifies, and promotes it.
        run_cli(REVA_PY, self.ws, "code", "scrape", "vid1-struct", self.short_mp4, lab_dir=self.lab_dir)
        run_cli(REVA_PY, self.ws, "transcribe", "vid1-struct", "--silent", lab_dir=self.lab_dir)
        run_cli(
            REVA_PY, self.ws, "research", "add-concept", "vid1-struct",
            "--term", "Beam Stirrup Rig", "--meaning", "Structured beam rig",
            "--must-show", "Beam rig renders cleanly", "--at", "0,2", lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_PY, self.ws, "research", "add-source", "vid1-struct",
            "--title", "Beam Ref", "--kind", "standard", "--url", "https://en.wikipedia.org/wiki/Rebar",
            lab_dir=self.lab_dir,
        )
        run_cli(
            REVA_PY, self.ws, "research", "complete", "vid1-struct",
            "--what", "Beam structural study", "--domain", "civil-engineering", lab_dir=self.lab_dir,
        )
        run_cli(REVA_CODE_PY, self.ws, "add", "vid1-struct", "beam-rig", "--from", "0", "--to", "3", lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "bench", "vid1-struct", "beam-rig", "--tool", "threejs-webgl", lab_dir=self.lab_dir)

        sdir1 = os.path.join(self.ws, "vid1-struct")
        bdir1 = os.path.join(sdir1, "beam-rig", "bench", "threejs-webgl")
        # Lab kit primitive was auto-staged into Video 1's bench.
        self.assertTrue(os.path.exists(os.path.join(bdir1, "threejs_schematic.js")))

        scene1 = os.path.join(bdir1, "bench_scene.html")
        with open(scene1, "w", encoding="utf-8") as fp:
            fp.write(
                "<!doctype html><html><script src='./three.min.js'></script>"
                "<script src='./threejs_schematic.js'></script><body><script>\n"
                "function buildCustomBeamRig(span, depth) { return { span, depth }; }\n"
                "const ctx = RevaCAD.boot({ headerNum: 1, headerTitle: 'Beam' });\n"
                "</script></body></html>\n"
            )

        p0 = os.path.join(self.tmp.name, "s14_0.png")
        im = Image.new("RGB", (320, 200), (238, 243, 247))
        ImageDraw.Draw(im).rectangle([40, 40, 280, 160], outline=(224, 122, 20), width=6)
        im.save(p0)
        run_cli(REVA_CODE_PY, self.ws, "compare", "vid1-struct", "beam-rig", "--tool", "threejs-webgl", "--mine", p0, "--ref-at", "1", lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "audit", "vid1-struct", "beam-rig", "--pass", "1", "--note", "ok", lab_dir=self.lab_dir)
        run_cli(
            REVA_CODE_PY, self.ws, "verify", "vid1-struct", "beam-rig",
            "--tool", "threejs-webgl", "--promote", "--id", "test-beam-rig",
            "--category", "3d-explainer", "--tags", "beam,revacad", lab_dir=self.lab_dir,
        )

        # Pattern code snapshot + extracted AST/JS symbol structure exist in isolated lab_dir.
        snap_scene = os.path.join(self.lab_dir, "patterns", "test-beam-rig", "bench_scene.html")
        snap_meta = os.path.join(self.lab_dir, "patterns", "test-beam-rig", "pattern.json")
        self.assertTrue(os.path.exists(snap_scene))
        self.assertTrue(os.path.exists(snap_meta))

        code_cmd = run_cli(REVA_LAB_PY, self.ws, "library", "code", "test-beam-rig", lab_dir=self.lab_dir)
        self.assertIn("buildCustomBeamRig", code_cmd.stdout)
        self.assertIn("RevaCAD", code_cmd.stdout)

        srch_sym = run_cli(REVA_LAB_PY, self.ws, "library", "search", "buildCustomBeamRig", lab_dir=self.lab_dir)
        self.assertIn("test-beam-rig", srch_sym.stdout)

        kit_out = run_cli(REVA_LAB_PY, self.ws, "kit", lab_dir=self.lab_dir)
        self.assertIn("threejs_schematic.js", kit_out.stdout)

        # Video 2 reuses test-beam-rig and gets Video 1's proven bench_scene.html automatically!
        run_cli(REVA_PY, self.ws, "code", "scrape", "vid2-struct", self.short_mp4, lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "add", "vid2-struct", "beam-copy", "--from", "0", "--to", "3", lab_dir=self.lab_dir)
        run_cli(REVA_CODE_PY, self.ws, "reuse", "vid2-struct", "beam-copy", "--pattern", "test-beam-rig", lab_dir=self.lab_dir)
        b_out = run_cli(REVA_CODE_PY, self.ws, "bench", "vid2-struct", "beam-copy", "--tool", "threejs-webgl", lab_dir=self.lab_dir)
        self.assertIn("bootstrapped from: test-beam-rig", b_out.stdout)

        sdir2 = os.path.join(self.ws, "vid2-struct")
        scene2 = os.path.join(sdir2, "beam-copy", "bench", "threejs-webgl", "bench_scene.html")
        with open(scene2, encoding="utf-8") as fp:
            self.assertIn("buildCustomBeamRig", fp.read())
        with open(os.path.join(sdir2, "beam-copy", "bench", "threejs-webgl", "bench.json"), encoding="utf-8") as fp:
            bcfg2 = json.load(fp)
        self.assertEqual(bcfg2["bootstrapped_from_pattern"], "test-beam-rig")
        self.assertIn("threejs_schematic.js", bcfg2["kit_files"])

    def test_15_web_browser_browse_and_ingredient_shop(self):
        from pathlib import Path
        from PIL import Image

        # 1. Lab engine registry lists web-browser [READY] and kit includes web_capture.py.
        eng_out = run_cli(REVA_LAB_PY, self.ws, "engines", lab_dir=self.lab_dir)
        self.assertIn("[READY  ] web-browser", eng_out.stdout)
        kit_out = run_cli(REVA_LAB_PY, self.ws, "kit", lab_dir=self.lab_dir)
        self.assertIn("web_capture.py", kit_out.stdout)

        # 2. web_capture gate & media link extractor work cleanly.
        kit_dir = os.path.join(REPO, "lab", "kit")
        if kit_dir not in sys.path:
            sys.path.insert(0, kit_dir)
        import web_capture

        self.assertTrue(web_capture.detect_captcha_or_gate("<html><title>Just a moment...</title><div class='cf-turnstile'></div></html>"))
        self.assertEqual(web_capture.detect_captcha_or_gate("<html><body>Clean Engineering Docs</body></html>"), "")
        links = web_capture.extract_media_links(
            '<img src="img/hook.svg"><a href="spec.pdf">Spec</a><a href="part.glb">3D</a><a href="data.csv">CSV</a>',
            base_url="https://example.org/docs/page.html",
        )
        self.assertIn("https://example.org/docs/img/hook.svg", links["images"])
        self.assertIn("https://example.org/docs/spec.pdf", links["documents"])
        self.assertIn("https://example.org/docs/part.glb", links["models3d"])
        self.assertIn("https://example.org/docs/data.csv", links["datasets"])

        # 3. Live headless Edge/Chrome JS DOM + screenshot via `reva research browse`.
        run_cli(REVA_PY, self.ws, "code", "scrape", "browse-study", self.short_mp4, lab_dir=self.lab_dir)
        run_cli(REVA_PY, self.ws, "transcribe", "browse-study", "--silent", lab_dir=self.lab_dir)
        sdir = os.path.join(self.ws, "browse-study")

        js_html = os.path.join(self.tmp.name, "dynamic_sni.html")
        with open(js_html, "w", encoding="utf-8") as fp:
            fp.write(
                "<!doctype html><html><head><title>Dynamic Spec Page</title></head>"
                "<body><div id='app'>Loading...</div>"
                "<script>"
                "document.getElementById('app').innerHTML = "
                "'<p>SNI 2847 dynamic 135 deg hook requires 6d and 75 mm inside core concrete.</p>"
                "<img src=\"diagram.svg\"><a href=\"model.glb\">GLB</a><a href=\"metrics.csv\">CSV</a>';"
                "</script></body></html>"
            )
        file_url = Path(js_html).resolve().as_uri()
        br_out = run_cli(
            REVA_PY, self.ws, "research", "browse", "browse-study", file_url,
            "--query", "135 deg hook core concrete", "--discover-links", lab_dir=self.lab_dir,
        )
        self.assertIn("SNI 2847 dynamic 135 deg hook", br_out.stdout)
        self.assertIn("screenshot", br_out.stdout)
        self.assertIn("links[models3d]", br_out.stdout)
        self.assertTrue(os.path.exists(os.path.join(sdir, "research", "assets", "dynamic_sni.txt")))
        self.assertTrue(os.path.exists(os.path.join(sdir, "research", "assets", "dynamic_sni.png")))

        # 4. 6-aisle ingredient shop offline + optional asset download.
        import research as mod_research
        dl_png = os.path.join(self.tmp.name, "shop_diag.png")
        Image.new("RGB", (200, 140), (230, 240, 245)).save(dl_png)
        dl_uri = Path(dl_png).resolve().as_uri()
        orig_map = dict(mod_research._AISLE_MAP)
        try:
            mod_research._AISLE_MAP.update({
                "docs": lambda q, max_results=5: [{"aisle": "docs", "kind": "paper", "title": "arXiv RC Hook", "url": "https://arxiv.org/abs/1", "download_url": "", "license": "arXiv", "provider": "arxiv", "snippet": "hook paper"}],
                "images": lambda q, max_results=5: [{"aisle": "images", "kind": "image", "title": "Shop Diagram", "url": dl_uri, "download_url": dl_uri, "license": "CC0", "provider": "wikimedia", "snippet": "diagram"}],
                "footage": lambda q, max_results=5: [{"aisle": "footage", "kind": "footage", "title": "Archive Pour Clip", "url": "https://archive.org/details/x", "download_url": "", "license": "PD", "provider": "internet-archive", "snippet": "clip"}],
                "audio": lambda q, max_results=5: [{"aisle": "audio", "kind": "audio", "title": "Hammer CC", "url": "https://openverse.org/a", "download_url": "", "license": "CC-BY", "provider": "openverse-audio", "snippet": "sfx"}],
                "models3d": lambda q, max_results=5: [{"aisle": "models3d", "kind": "model3d", "title": "Column GLB", "url": "https://sketchfab.com/m", "download_url": "", "license": "CC-BY", "provider": "sketchfab", "snippet": "3d"}],
                "data": lambda q, max_results=5: [{"aisle": "data", "kind": "dataset", "title": "Jakarta OSM", "url": "https://osm.org/r/1", "download_url": "", "license": "ODbL", "provider": "nominatim", "snippet": "lat/lon"}],
            })
            sh_res = mod_research.shop_ingredients(sdir, "stirrup concrete", aisle="all", max_results=2, download=1)
        finally:
            mod_research._AISLE_MAP.update(orig_map)

        self.assertEqual(len(sh_res["items"]), 6)
        self.assertEqual(len(sh_res["downloaded"]), 1)
        self.assertTrue(os.path.exists(os.path.join(sdir, sh_res["downloaded"][0]["local_asset"])))


if __name__ == "__main__":
    unittest.main()
