---
name: reva-code
description: "BRANCH 2A - REVA Code (Pure Coding Video Reverse Engineering). Deconstruct reference videos into exact pixel layouts (--grid), 5 fps timing & easing strips, hex palettes, explanatory 3D camera grammar, and stereo SFX measurements; rebuild each technique with your own script/data/code (HyperFrames, Three.js, GSAP, D3, Remotion), verify side-by-side (compare + verify), and export proven skills to Branch 1 (video-making-skills). Use for 'reverse engineer this animation', 'how is this coded/rendered', 'learn this 3D/chart/map technique', 'export Branch 1 video skill'."
---

# REVA Code: Pure Coding Video Reverse Engineering

**Target:** Branch 1 (`Exeloxylade/video-making-skills` — `video-automation`, `tscs-finance-explainer`, `finance-charts`, `map-video`, `gem-3d-world`).
**CLI:** `python reva_code.py ...` (or `reva-code` / `reva code ...`).

## The 3 Fundamental Goals

1. **Stack & Technical Research (How is it built?):**
   - Identify the rendering stack and libraries (Three.js, WebGL, Blender, GSAP, Remotion, HyperFrames, D3, animated maps, shaders).
   - Prove our code stack can achieve the same visual fidelity and smoothness.
2. **Explanatory & Dynamic Grammar (Why does it move?):**
   - Deconstruct camera movement grammar (context overview, detail mechanism, orthogonal plan dive, A/B failure shake), pacing, and apparatus staging.
   - **The Explanatory Test:** If the 3D scene or graphic sits static while narration plays, the explainer has failed.
3. **Extract Reusable Skills, Not Just Scene Assets:**
   - Never blindly clone scene assets or rebuild a whole reference film over its own narration.
   - Capture the underlying script-driven capability (dynamic apparatus switching, spatial dimensioning, failure simulation) so it works on any topic.

---

## The 3-Phase Brain + Coding Reverse-Engineering Loop

Never reverse-engineer pixels blindly without knowing what the narrator is explaining:

1. **Scrape & Transcribe First (`reva transcribe`):**
   ```cmd
   python reva_code.py scrape my-study <url-or-file> [--transcribe]
   python reva.py transcribe my-study
   ```
   Produces `dossier.md`, `ref\contact-sheet-*.jpg`, `ref\measure.json`, `ref\sound.json`, and `ref\transcript.{json,txt}` (or `ref\audio.mp3` if no subtitles exist so you can listen directly with `read_file` and save via `--from-file` / `--from-text`, or mark `--silent`).

2. **Learn & Research from the Internet (`reva research`):**
   Extract claims (`reva research claims my-study`), search authoritative specs, engineering articles & Wikimedia diagrams (`search_web`, `reva research search`, `reva research images --download`, `reva research fetch <url>`), and lock **physical cause-effect mechanism + verified standard specs + geometric anatomy + `must_show` checkpoints** before writing any 3D/2D code (`research complete` requires at least one real external URL or saved asset):
   ```cmd
   python reva.py research auto my-study
   python reva.py research add-concept my-study --term "<term>" --meaning "<definition>" --mechanism "<cause -> effect physics>" --specs "<exact standard numbers>" --anatomy "<exact geometry>" --must-show "<falsifiable check>" --wrong "<common bug>" --at 16.5,21.5
   python reva.py research complete my-study --what "<what the video is>" --domain "<domain>" --implication "<how understanding shapes the schematic>"
   python reva_lab.py recommend my-study
   ```
   *(Or step manually: `research claims` -> `search` -> `images --download 1` -> `fetch <url>`.)*

3. **Check Lab & Isolate One Technique (`reva-code add`, `reuse`):**
   ```cmd
   python reva_lab.py library search "animated map"
   python reva_code.py add my-study stirrup-hook --from 16 --to 37 --grid
   python reva_code.py stills my-study stirrup-hook --at 22.5,27.5 --grid
   python reva_code.py colors my-study stirrup-hook --at 22.5
   python reva_code.py sound my-study --mode side --auto
   ```
   - `add` seeds `checklist.json` from `must_show`, injects the `[from..to]` spoken excerpt + mechanism + specs + anatomy + traps into `notes.md`, and checks `lab/library.json`.
   - `theirs\_strip_*.jpg`: 5 fps motion strip (`0.2 s` per frame); `theirs\grid_*.png`: 100px/200px ruler (`WxH` verified).

4. **Schematic / Clay-First Test Bench, Zoomed Compare & Hard Audit Gate (`bench`, `compare --crop`, `audit`, `verify`):**
   - **Zero texture waste rule:** Never spend cycles on bump maps, concrete speckles, wood grain, or foliage inside the bench! Use flat/clay role-coded CAD colors so 100% of your effort goes into **exact geometry, true proportions, cross-sections, and clear causal explanation**.
   - Initialize the bench, render target stills, inspect BOTH full-frame and **cropped close-up zoom**, then pass every `must_show` check (`verify` **blocks** until `checklist.json` passes 100%):
   ```cmd
   python reva_code.py run-bench my-study stirrup-hook --tool threejs-webgl --at 0,1,2 --ref-at 22.5,27.5,37.0
   python reva_code.py verdict my-study stirrup-hook --winner threejs-webgl --note "Continuous TubeGeometry 135-deg hook"
   ```
   *(Or run steps individually: `bench` -> `render_bench.py --at 0,1,2` -> `compare` -> `compare --crop ...`.)*
   - Visually inspect BOTH `compare_<tool>.jpg` and `compare_<tool>_zoom.jpg`. Record pass/fail per `must_show` checkpoint — `verify` **blocks** until every visual audit item passes:
   ```cmd
   python reva_code.py audit my-study stirrup-hook --show
   python reva_code.py audit my-study stirrup-hook --pass 1 --pass 2 --note "Verified on _zoom.jpg"
   python reva_code.py verify my-study stirrup-hook --tool threejs-webgl --note "Eye-checked" --promote --category 3d-explainer --tags "3d,cutaway"
   ```

5. **Export Proven Skill Brief for Branch 1 (`skill`):**
   ```cmd
   python reva_code.py skill my-study
   ```
   Writes `skill-export.md` listing subject research sources, `[VERIFIED]` / `[COMPARED]` / `[UNVERIFIED]` status, winning/rejected engines, candidate compare sheets, and promoted pattern IDs before adding `## Technique: <name> (measured)` + template into `Exeloxylade/video-making-skills`.

---

## Commands Reference (`reva_code.py`)

| Command | Job |
|---|---|
| `doctor` | Check Python, FFmpeg/ffprobe, `yt-dlp`, NumPy, Pillow, workspace |
| `scrape <study> <source>` | Full code scrape: `start` + `measure` + `sound` (events) + `dossier.md` |
| `start` / `measure` | Run teardown or re-measure cuts, still/moving %, palette, WPM |
| `add <study> <tech> --from <s> --to <s> [--grid]` | 5 fps strip + 3 full stills (optional `grid_*.png`) + pattern check + `notes.md` |
| `bench <study> <tech> --tool <engine>` | Initialize `bench/<engine>/` with starter harness and measured `bench.json` |
| `run-bench <study> <tech> [--tool <e>] [--at ...]` | 1-command auto-init (if needed) + `render_bench.py` + full & zoomed `compare` + audit status |
| `reuse <study> <tech> --pattern <id>` | Link proven library pattern and append baseline + delta checklist to `notes.md` |
| `stills <study> <tech> --at <t1,t2> [--grid]` | Extra full-res PNG stills with optional pixel coordinate overlay |
| `colors <study> [<tech>] [--at <t>]` | Extract main + saturated accent hex colors |
| `sound <study> [--mode events\|side\|analyze\|audition]` | Stereo L-R SFX events, cut side jumps, WAV metrics, or audition video |
| `compare <study> <tech> --mine <mp4|imgs> [--crop x,y,w,h] [--schematic <img>]` | Full-frame or zoomed side-by-side comparison (accepts MP4 or direct PNG stills) |
| `audit <study> <tech> [--add ...] [--pass <id>] [--fail <id>] [--show]` | Inspect and pass/fail visual anatomy checkpoints in `checklist.json` |
| `verdict <study> <tech> --winner <engine>` | Record winning and rejected candidate engines in `study.json` & `notes.md` |
| `verify <study> <tech> [--tool ...] [--promote]` | Hard visual audit gate + mark verified proof (optionally promote to `lab/library.json`) |
| `skill <study> [--out <file>]` | Export `skill-export.md` with proof summary for Branch 1 |
| `status [<study>]` | Show studies, winning engines, and `[verified]` / `[compared]` / `[measuring]` status |

---

## Past Code Studies & Learned Techniques

| Study | Reference | Went into (Branch 1) | Status |
|---|---|---|---|
| `finance-doc` | TSCS-style finance documentary (1920×1080) | `tscs-finance-explainer`, `finance-charts`, `video-automation` (`sfx_kit.py`, `QUALITY.md`) | 6 techniques matched |
| `davin-kopdes` | Davin Azhar "strategi kelas dunia kopdes" Short (87.9 s) | `gem-3d-world`, style `warung`; 16 techniques | rebuilt, 35 s test film |
| `davin-lele` | Davin Azhar "bisnis ternak lele" Short (133.1 s) | `gem-3d-world`, style `kolam` | rebuilt in full (2m 16s nila film) |
| `redha-beton` | Puckerman Facts / Redha Maulana 3D civil Short (122.8 s) | `gem-3d-world`, style `konstruksi`; `lib/construct3d.js` | 8 techniques measured, 94.3 s test film |

| Technique (Finance & Maps) | Where it lives now | Status |
|---|---|---|
| Data line chart with photo cards | `tscs-finance-explainer` + `templates\technique-linechart.html` | matched, eye-checked |
| Topographic paper background | `tscs.js` -> `TSCS.topo` | matched |
| Transition sound v2: soft kit (swell / pop / hit) | `video-automation\tools\sfx_kit.py`; `QUALITY.md` sec 8 | matched by numbers |
| Full-bleed b-roll (drone shot, chip, name plates) | `tscs-finance-explainer`; `footage_hunt.py` | rebuilt 4x in indo-crash v3 |
| Coastline map opener | `tscs-finance-explainer` -> real-media A | rebuilt |
| Document card + highlighter | `tscs-finance-explainer` + `templates\technique-document.html` | matched, eye-checked |
| Route story map (glowing route, lat/lon stops, bait opener) | `map-video` -> `templates\route-short`, `templates\route-long` | rebuilt (`odyssey-route`, `nutmeg-war`) |

| Technique (3D Shorts) | Where it lives now | Status |
|---|---|---|
| Single low-poly world, single camera, no cuts | `gem-3d-world` -> `W3.camPath` | rebuilt, both styles |
| Toon outline (`W3.boot({ssaa: 2})`) & soft shadows | `gem-3d-world` (`warung` / `kolam`) | matched / rebuilt |
| Header band, speech bubbles, pills, leader-line tags | `templates\warung`, `cards.js`, `W3.Tags` | matched / rebuilt |
| Glass cards, boxed-number captions, dollhouse & cutaway pond rigs | `cards.js`, `W3.Captions`, `W3.shop.setCut`, `F3.pond` | rebuilt |

**Measured reference benchmarks:**
- **Finance doc (1920×1080, 30 fps):** paper `#e9e8e6`, accent `#8b1a2b`, card `#c8323e`, ink `#1c1c1c`; ~155 WPM; -16 LUFS; 42.7 stereo SFX/min (pops 20 ms rise / 395 Hz / -22.4 dB vs voice; swells 160 ms rise / 332 Hz / -13.8 dB; hits 40 ms rise / 392 Hz / -18.2 dB).
- **Davin Azhar 3D Shorts (1080×1920, 30 fps, 0 cuts):** 178–186 WPM; -14.1 / -13.6 LUFS; 76–77 SFX/min (pops 278–291 Hz, 7–10 dB under voice); kopdes header `#e3ecf1` top 392 px, pill `#d98a1a`; lele sky `#a8c8af`, water `#38736b`, accent box `#fc6428`.
