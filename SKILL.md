---
name: reva
description: "BRANCH 2 - REVA (Reverse Engineering Video Anything). Learn how any reference video is made and turn it into skills or app styles: tear it apart (cuts, frames, script, sound), measure it (cuts, picture length, still vs moving, words per minute, layout px, fonts, colours, easing, sound levels), rebuild each technique with your own content and compare side by side, then write the measurements into a Video Making skill OR deliver a style file into the Automated Lunch Free app (reva measure / reva deliver, style-check, the 8-picture style test). Use for 'reverse engineer this video', 'how is this made', 'match this style', 'add this reference', 'learn this channel's look'. For making videos, use BRANCH 1: video-automation."
---

# REVA: Reverse Engineering Video Anything

Two branches:
- **Branch 1, Video Making** (`video-automation` is its head, repo `Exeloxylade/video-making-skills`): makes videos.
  GEM (`gem-3d-world`) lives there too: the 3D world Shorts rebuilt from the Davin Azhar studies below.
- **Branch 2, REVA** (this skill, repo `Exeloxylade/reva`): studies a reference and upgrades branch 1.

Rule: REVA learns **techniques** (how a chart draws, how a card enters, how loud a swish is) and
rebuilds them with **your own script, voice and data**. It does not rebuild a whole reference film
scene by scene over its own narration. The output of REVA is a better skill, not a copy.

REVA delivers to two places:
| Target | What REVA writes | Used by |
|---|---|---|
| A code video skill (Branch 1) | a `## Technique: <name> (measured)` section + a template file | `video-automation` and its format skills (HyperFrames films) |
| **The app** (Automated Lunch Free) | a style folder `styles\<id>\` (`<id>.style.json` + `<id>.md`) | the app's style mode: the style wins over the preset (see "Deliver a style to the app" below) |

## Quick start: one command, one folder per study

```
set REVA=%USERPROFILE%\.kiro\crew\skills\reva\reva.cmd
%REVA% start finance-doc <url-or-file>                     tear down -> workspace\reva\finance-doc\ref\
%REVA% add finance-doc document-card --from 87 --to 93     strip at 5 fps + 3 stills + notes.md
%REVA% stills finance-doc document-card --at 89.5          more stills to measure
%REVA% colors finance-doc document-card                    paper / ink / accent hex
%REVA% sound finance-doc                                   transition sound numbers
%REVA% compare finance-doc document-card --mine <your.mp4> --mine-at 12,20
%REVA% status                                              every study and technique
%REVA% measure finance-doc                                 style-file numbers: cuts, picture length, still vs moving, wpm
%REVA% deliver finance-doc                                 copy <study>\style\<id>\ into the app's styles\ + style-check
```
Study folder: `study.json` (source + technique list + status), `ref\` (teardown),
`<technique>\theirs\` (strip, stills), `<technique>\notes.md` (measured numbers, gaps),
`<technique>\compare.jpg` (reference left, yours right).
Build the rebuild in Branch 1 (`vm new lab-<technique> --from indo-crash`, or `gem new lab-x --style kolam` for 3D Shorts), then compare here.

## Studies so far

| Study | Reference | Went into | Status |
|---|---|---|---|
| `finance-doc` | TSCS-style finance documentary (1920x1080) | `tscs-finance-explainer`, `finance-charts`, `video-automation` (`sfx_kit.py`, `QUALITY.md`) | 6 techniques matched |
| `davin-kopdes` | Davin Azhar "strategi kelas dunia kopdes" Short, youtube.com/shorts/hKWH77Um7BU (87.9 s) | `gem-3d-world`, style `warung`; `recipe.md` lists 16 techniques | rebuilt, 35 s test film |
| `davin-lele` | Davin Azhar "bisnis ternak lele" Short, youtube.com/shorts/pYYtBLGfkIw (133.1 s) | `gem-3d-world`, style `kolam` | rebuilt in full, 2m 16s film with its own script (nila) |

Study folders live in `workspace\reva\<study>\` (not in this repo): reference downloads are not ours to publish.

## Tools (`scripts/`)

| Tool | Job |
|---|---|
| `teardown.py` | Download (yt-dlp) or take a file; find cuts, grab frames into contact sheets, pull subtitles (script + wpm), measure loudness. Writes `teardown.json`. Vertical Shorts come as 1080x1920 (`-S res:1080` = short side); original-language subtitles first, and an HTTP 429 on one subtitle track no longer stops the video download. |
| `technique.py strip` | One time range at 5 fps in one sheet: see how things enter and move. |
| `technique.py stills` | Full-size frames at chosen seconds: measure positions and sizes in px. |
| `technique.py palette` | Main colours and accent colours of a still, as hex. |
| `technique.py compare` | Reference stills (left) next to your render (right) at matching moments. |
| `sfx_probe.py` | Transition sound: jump in level overall / 4-8 kHz / 40-200 Hz, and how long the bright part lasts. |
| `measure.py` | The numbers a style file needs: cuts (median/p10/p90, per minute, per third), still / subtle / moving shots, words per minute from deduped auto-captions; prints them as style-file values. Run by `reva measure`. |
| `sfx_lab.py events` | EVERY sound effect in a mix with the voice removed (L-R side): count per minute, kind (swell / pop / hit / hiss), rise and tail in ms, brightness Hz, level vs the voice. Use this first for sound. `--json` saves the list. |
| `sfx_lab.py analyze / side / audition` | Numbers for single WAVs; side signal at chosen cuts; an audition video (each sound alone, then under the voice at film level, `--gains`) for the ear check. |
| `compare.py` | Whole-video score (colour, brightness, layout) - rough only; the user's eye is the real test. |

Needs ffmpeg (`C:\ffmpeg\bin`), `python -m yt_dlp`, Pillow.

## The method (worked on the line-chart technique and the transition sound)

1. **Tear down.** `python scripts\teardown.py <url-or-file> --out <work>\_ref --name ref --sps 1`.
   Read every contact sheet. Write a **technique list**: each distinct scene type, with time ranges
   (e.g. "data line chart with photo cards 35-59 s", "document card + highlighter 87-93 s").
2. **Pick one technique.** One at a time. Never the whole film at once.
3. **Measure it.**
   - `technique.py strip --from a --to b --fps 5` -> count frames for entry times, holds, order.
   - `technique.py stills --at ...` -> read px: title size and position, plot box, line widths,
     card size, border, tilt, label sizes, gaps.
   - `technique.py palette` on a still -> paper, ink, accent hex.
   - Fonts: match the letter shapes (the line-chart study found Poppins); get it free (Google Fonts, OFL)
     and load with `@font-face` - system fonts never match.
   - Sound: `sfx_lab.py events ref.mp4 --dur 180` (all effects, voice removed), then the same on your render.
     Match kind, rise, brightness and level vs voice; then make the user listen to `sfx_lab.py audition`.
   - Footage: strip + `stills`, then mean luma of a still (how dark full-bleed footage is), shot length, what sits on top.
   Write the numbers down as a list before building.
4. **Rebuild with your own content.** Your words, your voice, real data you pulled
   (`finance-charts`), real photos you found (`image_hunt.py`). Same measured layout, timing, motion.
5. **Side by side.** `technique.py compare --ref <stills> --mine <render> --mine-at <times>`.
   Look at it yourself, list every difference, fix, repeat 2-3 times.
6. **User's eye check.** Show the compare sheet and the clip. The user's eye beats any score.
   Fix what they name. Repeat until they say it matches.
7. **Write it into Branch 1.** Add a `## Technique: <name> (measured)` section to the right making
   skill with every number, and save the working piece as a template. Push the skill.
8. Next technique.

## Deliver a style to the app (Automated Lunch Free)

The app reads `styles\<id>\<id>.style.json`. When a video uses it, **the style wins over the preset**
wherever it has data (story order, hook, wpm, narration rules, picture length, shot types = scene cards,
picture rules, framing, drawn words, host, still camera, hard cuts, video-clip cap). Field list, checks
and examples: `<app>\docs\reference-styles.md`. Template: `<app>\docs\reference-style.template.json`.
Worked example: `<app>\styles\stickman-why-explainer\`.

One path, in order:
1. `reva start <study> <url>` and read every contact sheet. List each kind of picture (= scene cards).
2. `reva measure <study>`: cuts, picture length, still vs moving, wpm, as style-file values.
3. Write `<study>\style\<id>\<id>.style.json` from the template, and its `<id>.md` twin.
   - `look.picture_rules`: 5-8 rules a stranger could draw from (ideas per picture, character size,
     camera height, background, symbols, where words sit, layouts). Without them the app falls back to
     film-crew frames.
   - `look.framing`: `flat` (comic panels) or `film` (a real camera: realistic styles).
   - `look.text_in_image`: allowed only if the reference draws words in its pictures (never for photo-real).
   - `look.can_do.camera_moves: false` when the reference holds still pictures; video share from `measure`.
4. Golden beats: 8 reference frames, one per scene card that matters, with the line spoken over each:
   `<study>\style\<id>\test\beats.json` + `test\ref\*.jpg` (`[{"id":"b1","scene":"sc01","ref":"ref/b1.jpg","narration":"..."}]`).
5. `reva deliver <study>`: copies the folder into `<app>\styles\<id>\` and runs `npm run style-check`.
   Fix every ERROR, read every WARNING, deliver again.
6. In the app folder: `npm.cmd run style-test -- --style <id> --preset cinematic-story`. Open
   `projects\_style-tests\<id>-<time>\compare.jpg`. **Pass = 6 of 8 beats** show the same idea, layout,
   symbols and drawn words as the reference. Fail: fix the style (rules, cards), never the beats.
7. Make a 45 s video with it (`npm run make -- --topic "..." --style <id> --no-export`), watch all of it,
   then show the user the compare sheet and the video. The user's eye decides.

Never: judge a style by its look text alone; guess still vs moving (measure it: fast cuts look like
motion); put reference frames in the app's git (`styles/*/test/` is ignored) or send them to the image
model; copy the reference's lines, characters, logos or music; set a video share above the measured one.

| Style delivered | Reference | Result |
|---|---|---|
| `stickman-why-explainer` | Lumensia: "Kenapa Kita Tidak Makan Kudanil?" + "Bagaimana Orang Mesir Kuno Mengatasi Panas 50°C" | 8 of 8 golden beats on the worst preset; 43 s zebra test video; Funny drawing low/medium/high tested |
| `stickman-history-epic` | Animated History, "2000 Years of Israel History" | delivered before style mode; style-check warns: no picture rules yet, uses real photos the app cannot fetch |

## Techniques learned so far (finance documentary reference)

| Technique | Where it lives now | Status |
|---|---|---|
| Data line chart with photo cards | `tscs-finance-explainer` -> "Technique: data line chart" + `templates\technique-linechart.html` | matched, eye-checked |
| Topographic paper background | `tscs.js` -> `TSCS.topo` | matched |
| Transition sound v2: soft kit (swell / pop / hit) | `tscs-finance-explainer` -> "Technique: transition sound"; kit `video-automation\tools\sfx_kit.py`; QUALITY.md section 8 | matched by numbers, waiting for the user's ear |
| Full-bleed b-roll (drone shot, location chip, name plates) | `tscs-finance-explainer` -> "Technique: full-bleed b-roll"; `footage_hunt.py`; QUALITY.md section 7 | rebuilt 4x in indo-crash v3 |
| Coastline map opener | `tscs-finance-explainer` -> real-media A | rebuilt |
| Document card + highlighter | `tscs-finance-explainer` -> "Technique: document card + highlighter" + `templates\technique-document.html` | matched, eye-checked |
| Route story map (ship on a dashed glowing route, stop labels with lat/lon, picture cards, full-route "bait" opener) | `map-video` -> "Route story films" + `templates\route-short`, `templates\route-long` | rebuilt from studies `short-nELG`, `short-eXpS`; tested `odyssey-route`, `nutmeg-war` |
| Dark skyline title scenes | - | to do |
| Menu board with flags | - | to do |

## Techniques learned so far (Davin Azhar 3D business Shorts)

| Technique | Where it lives now | Status |
|---|---|---|
| One low-poly world, one camera, no cuts | `gem-3d-world` -> `W3.camPath` (timed + `pass` keys, `aim` hook) | rebuilt, both styles |
| Toon look with an even outline (Kopdes) | `W3.boot({ssaa: 2})` + ink pass from depth and normals | matched; fixed the pixelated v1 |
| Soft light + shadows, no outline (lele) | `W3.boot({outline: false, shadows: true})` + `shadowAt` | rebuilt |
| Header band + numbered titles (Kopdes) | `templates\warung\film.html` | matched, hard cut like the reference |
| Title speech bubble + pill (lele) | `cards.js` -> `bubble`, `pill` (no presenter face, on purpose) | rebuilt |
| Tags on leader lines | `W3.Tags` (fade when the point leaves the frame) | rebuilt |
| Glass cards growing row by row (lele) | `cards.js` -> rows, totals, checklists, bars, donut, line chart, dots, price chain | rebuilt |
| Ground marks (ring, route) | `templates\warung`, `templates\kolam` | rebuilt |
| Captions with boxed numbers and key words | `W3.Captions({boxNumbers, keys, karaoke})` | rebuilt |
| Dollhouse dive (roof off) | `W3.shop.setCut`, `F3.restaurant().roof` | rebuilt |
| Cutaway pond (water face, mud, fish) | `F3.pond({cut: true}).setCut` | rebuilt |
| Map pull-out, night light, grey "on paper" twist | `templates\warung`, `templates\kolam` | rebuilt |
| Sound: ~76 low sounds a minute | `templates\*\build_film.py` (pops 220/250 Hz, low swells, hits) | close by numbers |
| Presenter cut-out, real-footage insert | - | left out (no face wanted; footage needs rights) |

## Measured reference numbers (keep for comparison)

- Picture: 1920x1080, 30 fps. Paper `#e9e8e6`, accent `#8b1a2b`, card frame `#c8323e`, ink `#1c1c1c`.
- Voice: ~155 wpm. Mix: about -16 LUFS.
- Transitions (sfx_probe, old method): bright part ~0.20 s, +19.4 dB in 4-8 kHz, +4.9 dB low body (median of 13 cuts).
- Sound events (sfx_lab events, first 180 s, voice removed): 42.7 per minute. Pops 70 (20 ms rise, 395 Hz, -22.4 dB
  vs voice), swells 22 (160 ms rise, 240 ms tail, 332 Hz, -13.8 dB), hits 18 (40 ms rise, 760 ms tail, 392 Hz, -18.2 dB).
- B-roll 170.4-175.0 s: one continuous drone shot, mean luma ~51 (p95 ~103), chip "SCBD, JAKARTA" top-left,
  name plate at x 170 y 520 (dark name box + red role bar), portrait card right, stamp "QUIT, 30 JAN".
- Something new appears every 1-2 s; cards enter in ~0.4 s steps.

Davin Azhar 3D Shorts (Kopdes / lele):
- Picture: 1080x1920, 30 fps, 0 hard cuts. Voice 178-186 wpm. Mix -14.1 / -13.6 LUFS.
- Camera moving in 100% / 98% of seconds; change per 0.1 s (median) 8.9 / 2.1, so the lele camera is much calmer.
- Sound events: 77 / 76 a minute; pops 278-291 Hz with a 20-40 ms rise, 7-10 dB under the voice.
- Kopdes: header band `#e3ecf1` over the top 392 px, title x 50 ~58 px, pill `#d98a1a`, captions y ~1188, 64 px.
- Lele: sky `#a8c8af`, dirt `#c7b287`, grass `#94bb6c`, tarp `#215d98`, water `#38736b` (cut `#30708e`), rail `#ea8638`;
  title bubble x 60 y 252-360, card x 70-640 with a 64 px header, captions y ~1232, 66 px, numbers in an orange `#fc6428` box.
