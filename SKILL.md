---
name: reva
description: "BRANCH 2 - REVA (Reverse Engineering Video Anything). Scrape any reference video's layout, pacing, motion ratio, palette, script/WPM, and SFX; clone it as an Automated-Lunch-Free style (reva scrape / scaffold / beats / deliver) OR isolate, rebuild, verify, and export reusable video-making skills into Branch 1 (reva add / compare / verify / skill). Use for 'reverse engineer this video', 'scrape this style', 'clone this channel style', 'how is this made', 'learn this technique'."
---

# REVA: Reverse Engineering Video Anything

## The 3 Fundamental Goals of REVA

1. **Stack & Technical Research (How is it built?):**
   - Identify the rendering stack and libraries (Three.js, WebGL, Blender, GSAP, Remotion, HyperFrames, animated maps, charts, shaders).
   - Prove our code stack can achieve the same visual fidelity and smoothness.
2. **Explanatory & Dynamic Grammar (Why does it move?):**
   - Deconstruct camera movement grammar (context overview, detail mechanism, orthogonal plan dive, A/B failure shake), pacing, and apparatus staging.
   - **The Explanatory Test:** If the 3D scene sits static while narration plays, the explainer has failed.
3. **Extract Reusable Skills, Not Just Scene Assets:**
   - Never blindly clone scene assets or whole reference films over their own audio.
   - Capture the underlying script-driven capability (dynamic apparatus switching, spatial dimensioning, failure simulation) so it works on any topic.

Two branches:
- **Branch 1, Video Making** (`Exeloxylade/video-making-skills`, head `video-automation` + `gem-3d-world`): builds videos.
- **Branch 2, REVA** (this skill, `Exeloxylade/reva`): scrapes references, validates rebuilds, and delivers styles or proven skills.

---

## Track A: Style Scraping & Cloning (`Automated-Lunch-Free`)

Use this fast 4-step loop to clone a channel's format, pacing, look, and rules into `<app>\styles\<id>\`:

1. **Scrape & auto-scaffold in one command:**
   ```cmd
   reva scrape my-study <url-or-file> --style my-style --beats 8
   ```
   Produces `studies\my-study\dossier.md`, timestamped `ref\contact-sheet-*.jpg`, `ref\measure.json`, `ref\sound.json`, `ref\transcript.json`, pre-populated `style\my-style\my-style.style.json` + `.md`, and 8 aligned frames in `style\my-style\test\beats.json` + `beats-preview.jpg`.
2. **Inspect the reference & author the rules:**
   - Read `dossier.md`, `ref\contact-sheet-*.jpg`, and `style\my-style\test\beats-preview.jpg`.
   - Replace every `<TODO:...>` placeholder in `<id>.style.json`:
     - `look.art_style`, `character`, `background`, `lighting`
     - `look.picture_rules` (5–8 rules a stranger could draw from: subject size, camera height, background, symbols, text placement, panel layouts)
     - `look.framing`: `"flat"` (comic/diagram panels) or `"film"` (real camera); `look.text_in_image.allowed`: `false` for photo-real styles
     - `direction.story.order` + `direction.scene_cards` + `direction.hook_0_5s` + `direction.narration.rules` / `line_templates`
   - Adjust `test\beats.json` timestamps (`reva beats my-study my-style --at 2,14,35,...`) if you want specific signature shots.
3. **Validate & deliver:**
   ```cmd
   reva deliver my-study
   ```
   Blocks leftover `<...>` placeholders, copies `style\<id>\` into `<app>\styles\<id>\`, and runs `node scripts/style-check.js <id>`. Fix every `ERROR` and review `WARNING`s.
4. **Prove visually (`style-test` + test render):**
   ```cmd
   cd "<app>"
   npm.cmd run style-test -- --style my-style --preset cinematic-story
   ```
   Open `projects\_style-tests\my-style-*\compare.jpg`. **Pass = 6 of 8 beats** match the reference's idea, layout, symbols, and drawn words. If it fails, fix `<id>.style.json` (never the beats) and re-deliver. Finish with a 45 s render (`npm run make -- --topic "..." --length 45 --style my-style --no-export`) and watch it end-to-end.

**Never:** guess still vs. moving shots (fast cuts mimic motion—trust `measure.json`); commit `styles/*/test/` reference frames; send reference frames to image models; copy exact lines, characters, logos, or music; set video share above the measured moving share.

---

## Track B: Deep Technique Reverse-Engineering & Proven Skill Gathering (Branch 1)

Use this 4-step loop to master one visual/motion/audio rig at a time (never a whole film in one blind pass) and export a proven spec for Branch 1:

1. **Scrape the whole video first:**
   ```cmd
   reva scrape my-study <url-or-file>
   ```
   Read `dossier.md` and `ref\contact-sheet-*.jpg` to list distinct techniques with exact time ranges.
2. **Isolate & measure one technique:**
   ```cmd
   reva add my-study line-chart --from 35 --to 59
   reva stills my-study line-chart --at 44,56
   reva colors my-study line-chart --at 44
   reva sound my-study --mode side --auto
   ```
   Inspect `theirs\_strip_35-59.jpg` and full PNG stills; log exact px dimensions, fonts, hex colors, entry order, easing, and audio jump levels in `notes.md`. (Use `sfx_lab.py audition` to ear-check candidate WAVs against voice.)
3. **Rebuild with your own content, compare, and verify:**
   - Build the technique in Branch 1 with your own topic, voice, real data, and sourced photos/assets.
   - Generate side-by-side proof and fix gaps across 2–3 iterations until the user's eye confirms a match:
   ```cmd
   reva compare my-study line-chart --mine <your.mp4> --mine-at 12,24 --ref-at 44,56
   reva verify my-study line-chart --note "Eye-checked; 12px margin fixed"
   ```
4. **Export proven skill brief for Branch 1:**
   ```cmd
   reva skill my-study
   ```
   Writes `skill-export.md` summarizing `[VERIFIED]` techniques, exact measured numbers, and any remaining gaps before writing a `## Technique: <name> (measured)` section + template into Branch 1.

---

## Tools (`scripts/`)

| Tool | Role |
|---|---|
| `_common.py` | Path/workspace/app resolution, FFmpeg/ffprobe lookup, `showinfo` cut detection, rolling VTT/SRT parser, Pillow MEDIANCUT + accent palette |
| `teardown.py` | `yt-dlp` (1080p short-side, original-lang subs) or local copy, cuts, Pillow timestamped contact sheets, `transcript.json/.txt/script.txt`, LUFS |
| `measure.py` | Scene cuts (`> 0.15`), p10/median/p90 shot lengths, thirds pace, still/subtle/moving ratio, `max_static_sec`, multi-frame palette, WPM |
| `technique.py` | Single-technique 5 fps `strip`, full-res PNG `stills`, multi-still `palette`, aspect/height-safe `compare.jpg` |
| `sfx_lab.py` | Stereo L-R `events` (with mono/dual-mono guard), cut `side` jumps, WAV `analyze`, Pillow title-card `audition` video |
| `style_kit.py` | Study `dossier.md`, auto golden `beats` + preview, `scaffold_style` (`--refresh-metrics`), placeholder guard, `export_skill` |

Requirements: Python 3, `ffmpeg`/`ffprobe` on `PATH` (or `C:\ffmpeg\bin\` or `REVA_FFMPEG`), `numpy`, `Pillow`, `yt-dlp`, and `node` (for `reva deliver`). Run `python reva.py doctor` to verify.

---

## Studies & Styles Delivered So Far

| Study | Reference | Went into | Status |
|---|---|---|---|
| `finance-doc` | TSCS-style finance documentary (1920x1080) | `tscs-finance-explainer`, `finance-charts`, `video-automation` (`sfx_kit.py`, `QUALITY.md`) | 6 techniques matched |
| `davin-kopdes` | Davin Azhar "strategi kelas dunia kopdes" Short (87.9 s) | `gem-3d-world`, style `warung`; 16 techniques | rebuilt, 35 s test film |
| `davin-lele` | Davin Azhar "bisnis ternak lele" Short (133.1 s) | `gem-3d-world`, style `kolam` | rebuilt in full (2m 16s nila film) |
| `redha-beton` | Puckerman Facts / Redha Maulana 3D civil Short (122.8 s) | `gem-3d-world`, style `konstruksi`; `lib/construct3d.js` | 8 techniques measured, 94.3 s test film |

| App Style Delivered | Reference | Result |
|---|---|---|
| `stickman-why-explainer` | Lumensia: hippos + ancient Egypt heat | 8/8 golden beats on `cinematic-story`; 43 s zebra test |
| `isometric-3d-explainer` | Puckerman Facts: concrete construction | 9:16 3D diorama style (`film` framing, 178 WPM) |
| `stickman-history-epic` | Animated History: 2000 Years of Israel | delivered pre-style-mode |

## Techniques Learned & Measured Reference Numbers

| Technique (Finance & Maps) | Where it lives now | Status |
|---|---|---|
| Data line chart with photo cards | `tscs-finance-explainer` + `templates\technique-linechart.html` | matched, eye-checked |
| Topographic paper background | `tscs.js` -> `TSCS.topo` | matched |
| Transition sound v2: soft kit (swell / pop / hit) | `video-automation\tools\sfx_kit.py`; `QUALITY.md` sec 8 | matched by numbers |
| Full-bleed b-roll (drone shot, chip, name plates) | `tscs-finance-explainer`; `footage_hunt.py` | rebuilt 4x in indo-crash v3 |
| Coastline map opener | `tscs-finance-explainer` -> real-media A | rebuilt |
| Document card + highlighter | `tscs-finance-explainer` + `templates\technique-document.html` | matched, eye-checked |
| Route story map (glowing route, lat/lon stops, bait opener) | `map-video` -> `templates\route-short`, `templates\route-long` | rebuilt (`odyssey-route`, `nutmeg-war`) |

| Technique (Davin Azhar 3D Shorts) | Where it lives now | Status |
|---|---|---|
| Single low-poly world, single camera, no cuts | `gem-3d-world` -> `W3.camPath` | rebuilt, both styles |
| Toon outline (`W3.boot({ssaa: 2})`) & soft shadows | `gem-3d-world` (`warung` / `kolam`) | matched / rebuilt |
| Header band, speech bubbles, pills, leader-line tags | `templates\warung`, `cards.js`, `W3.Tags` | matched / rebuilt |
| Glass cards, boxed-number captions, dollhouse & cutaway pond rigs | `cards.js`, `W3.Captions`, `W3.shop.setCut`, `F3.pond` | rebuilt |

**Measured benchmarks:**
- **Finance doc (1920x1080, 30 fps):** paper `#e9e8e6`, accent `#8b1a2b`, card `#c8323e`, ink `#1c1c1c`; ~155 WPM; -16 LUFS; 42.7 stereo SFX/min (pops 20 ms rise / 395 Hz / -22.4 dB vs voice; swells 160 ms rise / 332 Hz / -13.8 dB; hits 40 ms rise / 392 Hz / -18.2 dB).
- **Davin Azhar 3D Shorts (1080x1920, 30 fps, 0 cuts):** 178–186 WPM; -14.1 / -13.6 LUFS; 76–77 SFX/min (pops 278–291 Hz, 7–10 dB under voice); kopdes header `#e3ecf1` top 392 px, pill `#d98a1a`; lele sky `#a8c8af`, water `#38736b`, accent box `#fc6428`.
