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

## 4-Step Coding Reverse-Engineering Loop

Isolate **one technique/rig at a time** — never attempt an entire multi-scene film in one blind pass.

1. **Scrape the whole video first:**
   ```cmd
   python reva_code.py scrape my-study <url-or-file>
   ```
   Produces `studies\my-study\dossier.md`, timestamped `ref\contact-sheet-*.jpg`, `ref\measure.json` (cuts, motion ratio, palette, WPM), `ref\sound.json` (stereo L-R SFX events), and `ref\transcript.txt`.
   Read `dossier.md` and the contact sheets to list distinct techniques with exact time ranges.

2. **Isolate & measure one technique (pixels, frames, colors, sound):**
   ```cmd
   python reva_code.py add my-study line-chart --from 35 --to 59 --grid
   python reva_code.py stills my-study line-chart --at 44,56 --grid
   python reva_code.py colors my-study line-chart --at 44
   python reva_code.py sound my-study --mode side --auto
   ```
   - `theirs\_strip_35-59.jpg`: 5 fps motion strip (count frames × `0.2 s` for entry delays, holds, and easing).
   - `theirs\grid_*.png`: 100px/200px coordinate ruler + center crosshair (`WxH` verified) for exact px layout measurement.
   - `notes.md`: record rendering stack hypothesis, exact px boxes, typography (identify & load free Google Fonts via `@font-face` — never system fonts), hex colors, entry timing, camera grammar, and SFX levels.
   - Use `python scripts\sfx_lab.py audition ...` when tuning synthesized/matched SFX against voice.

3. **Rebuild in Branch 1 with your own content, compare, and verify:**
   - Build the rig with your own topic, script, voice, real data (`finance-charts`), or real assets (`image_hunt.py`).
   - Run side-by-side comparison and iterate until the user's eye confirms a match:
   ```cmd
   python reva_code.py compare my-study line-chart --mine <your-render.mp4> --mine-at 12,24 --ref-at 44,56
   python reva_code.py verify my-study line-chart --note "Eye-checked; margins, font weight, and card stagger matched"
   ```
   *(Note: `verify` requires `compare.jpg` to exist first so uncompared code is never marked proven.)*

4. **Export proven skill brief for Branch 1:**
   ```cmd
   python reva_code.py skill my-study
   ```
   Writes `skill-export.md` listing `[VERIFIED]` / `[COMPARED]` / `[UNVERIFIED]` status per technique, all measured parameters, and remaining gaps before adding `## Technique: <name> (measured)` + template into `Exeloxylade/video-making-skills`.

---

## Commands Reference (`reva_code.py`)

| Command | Job |
|---|---|
| `doctor` | Check Python, FFmpeg/ffprobe, `yt-dlp`, NumPy, Pillow, workspace |
| `scrape <study> <source>` | Full code scrape: `start` + `measure` + `sound` (events) + `dossier.md` |
| `start` / `measure` | Run teardown or re-measure cuts, still/moving %, palette, WPM |
| `add <study> <tech> --from <s> --to <s> [--grid]` | 5 fps strip + 3 full stills (optional `grid_*.png`) + code `notes.md` |
| `stills <study> <tech> --at <t1,t2> [--grid]` | Extra full-res PNG stills with optional pixel coordinate overlay |
| `colors <study> [<tech>] [--at <t>]` | Extract main + saturated accent hex colors |
| `sound <study> [--mode events\|side\|analyze\|audition]` | Stereo L-R SFX events, cut side jumps, WAV metrics, or audition video |
| `compare <study> <tech> --mine <mp4> --mine-at ...` | Render `compare.jpg` (`REF` left vs `MINE` right) |
| `verify <study> <tech> [--note "..."]` | Mark compared technique as eye-checked proof |
| `skill <study> [--out <file>]` | Export `skill-export.md` with proof summary for Branch 1 |
| `status [<study>]` | Show studies and `[verified]` / `[compared]` / `[measuring]` status |

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
