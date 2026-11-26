---
name: reva-style
description: "BRANCH 2B - REVA Style (Prompt-Style Scraping & Cloning for Automated-Lunch-Free). Measure a reference channel's pacing, still-vs-video ratio, WPM, and color palette, extract 8 narration-aligned golden beats, author promptable picture rules and scene cards into <id>.style.json, validate locally (check), deliver to Automated-Lunch-Free, and prove visually with the 8-beat style-test gate. Use for 'clone this style for Automated Lunch Free', 'make a style file from this video', 'scrape this channel style'."
---

# REVA Style: Prompt-Style Cloning (`Automated-Lunch-Free`)

**Target:** `Automated-Lunch-Free\styles\<id>\` (`<id>.style.json`, `<id>.md`, and gitignored `test\beats.json` + `test\ref\*.jpg`).
**CLI:** `python reva_style.py ...` (or `reva-style` / `reva style ...`).

Prompt-style cloning captures **art direction, story order, pacing, framing, and picture rules** so `Automated-Lunch-Free` (a code-callable Electron/Node CLI engine) reproduces a channel's look and rhythm — **no manual pixel coordinates or easing curves required**.

---

## 4-Step Style Cloning Loop

1. **Scrape, measure, scaffold & extract 8 golden beats in one command:**
   ```cmd
   python reva_style.py scrape my-study <url-or-file> --style my-style --beats 8
   ```
   Generates:
   - `studies\my-study\dossier.md` + timestamped `ref\contact-sheet-*.jpg` + `ref\transcript.txt`
   - `ref\measure.json`: exact `avg_shot_sec`, `shot_length_sec`, `cuts_per_min`, **still vs. moving ratio**, `max_static_sec`, WPM, `default_aspect`, and color palette
   - `style\my-style\my-style.style.json` + `.md` pre-filled with every measured number
   - `style\my-style\test\beats.json` + `ref\b1..b8.jpg` + `beats-preview.jpg` (8 beats across the timeline with aligned spoken narration)

2. **Inspect contact sheets & author the promptable style rules:**
   Read `dossier.md`, `ref\contact-sheet-*.jpg`, and `style\my-style\test\beats-preview.jpg`. Replace every `<TODO:...>` in `my-style.style.json`:
   - `look.art_style`, `character`, `background`, `lighting`: clear painting/model directions any prompt can follow (zero reference-specific character names or copyrighted titles).
   - `look.picture_rules`: **5–8 rules a stranger could draw from** (ideas per frame, subject scale, camera height, background simplicity, recurring symbols, text placement, panel/split/grid layouts).
   - `look.framing`: `"flat"` (comic panels / 2D diagrams, front view), `"film"` (real camera shots: wide, close, macro), or `"fixed-tabletop"` (locked macro overhead/slate perspective for ASMR process styles).
   - For silent ASMR / Foley channels (0 spoken words), scaffold with `--silent-asmr --framing fixed-tabletop [--domain culinary|automotive-restoration]` to configure `direction.voice = "off"`, `graphics = false`, `prompt_profile = "silent-process-asmr"`, and `-18 LUFS` / `LRA 15` sound targets.
   - `look.text_in_image.allowed`: `true` only if the reference draws words/numbers inside panels (`false` for photo-real styles so text renders as clean overlays).
   - `direction.story.order` + `direction.scene_cards` + `direction.hook_0_5s` + `direction.narration.rules` / `line_templates`.
   - Optionally re-pick specific signature frames for golden beats:
     `python reva_style.py beats my-study my-style --at 2,14,35,60,...`

3. **Dry-run check & deliver to `Automated-Lunch-Free`:**
   ```cmd
   python reva_style.py check my-study
   python reva_style.py deliver my-study --promote --tags "explainer,2d"
   ```
   - `check` verifies no UTF-8 BOM, zero leftover `<...>` placeholders, and runs `Automated-Lunch-Free\scripts\style-check.js` locally without copying anything yet.
   - `deliver` copies `style\<id>\` into `<app>\styles\<id>\` and runs `style-check.js <id>`. Passing `--promote` (or running `reva-lab promote-style my-study`) indexes the style into `lab/library.json` for reuse on future channel studies. Fix every `ERROR` and review `WARNING`s.

4. **Prove visually (`style-test` + 45s test render):**
   ```cmd
   cd "<Automated-Lunch-Free>"
   npm.cmd run style-test -- --style my-style --preset cinematic-story
   ```
   Open `projects\_style-tests\my-style-*\compare.jpg`.
   - **Pass gate = at least 6 of 8 beats** match the reference's idea, layout, symbols, and drawn words.
   - If it fails: fix `<id>.style.json` (`picture_rules`, `scene_cards`, `framing`, `text_in_image`) — **never weaken the beats** — and re-run `deliver` + `style-test`.
   - Finish with a 45 s video render (`npm run make -- --topic "..." --length 45 --style my-style --no-export`) and watch it end-to-end.
   - `Automated-Lunch-Free` CLI supports full GUI parity: `--topic-override`, `--humor`, `--stop-after plan|frames`, `--approve <id>`, `--ref <img.png>`, `--list-styles`, `npm run map`, and `npm run gfx`.

---

## Guardrails ("Never Do This")

- **Never judge a style by its look text alone** — prove it with `style-test` (6/8 beats).
- **Never guess still vs. moving shots** — fast cuts mimic video motion (one study assumed 100% clips when 89% were still images). Always trust `measure.json`.
- **Never set video share higher than measured moving share.**
- **Never send reference frames to the image model** (`style-test` tests prompts only, never image-to-image copying).
- **Never commit `styles/*/test/` reference frames** (`Automated-Lunch-Free/.gitignore` ignores them).
- **Never copy exact reference lines, host characters, logos, or music.**
- **Never enable `text_in_image` on photo-real styles.**

---

## Commands Reference (`reva_style.py`)

| Command | Job |
|---|---|
| `doctor` | Check Python, FFmpeg/ffprobe, `yt-dlp`, NumPy, Pillow, Node, and `Automated-Lunch-Free` |
| `scrape <study> <source> [--style <id>] [--beats 8] [--framing ...] [--silent-asmr]` | Full style scrape: teardown + measure + dossier + scaffold + auto golden beats |
| `measure <study>` / `colors <study>` | Re-measure pacing/still%/WPM or whole-video hex palette |
| `beats <study> [<id>] (--at ... \| --auto)` | Extract golden beat JPEGs + aligned narration + `beats-preview.jpg` |
| `scaffold <study> [<id>] [--framing ...] [--silent-asmr] [--refresh-metrics]` | Create `<id>.style.json` + `<id>.md` (or refresh only measured metrics) |
| `check <study> [--style <id>]` | Dry-run placeholder check + local `style-check.js` without copying |
| `deliver <study> [--style <id>] [--promote]` | Validate, copy into `<app>\styles\<id>\`, run `style-check.js`, and optionally promote to `lab/library.json` |
| `status [<study>]` | Show style studies, remaining placeholders (`ready` vs count), and delivery status |

---

## App Styles Delivered So Far

| Style ID | Reference | Result |
|---|---|---|
| `stickman-why-explainer` | Lumensia: hippos + ancient Egypt heat | 8/8 golden beats on `cinematic-story`; 43 s zebra test |
| `isometric-3d-explainer` | Puckerman Facts: concrete construction | 9:16 3D diorama style (`film` framing, 178 WPM) |
| `stickman-history-epic` | Animated History: 2000 Years of Israel | delivered pre-style-mode |
