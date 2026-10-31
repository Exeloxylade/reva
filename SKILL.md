---
name: reva
description: "BRANCH 2 - REVA (Reverse Engineering Video Anything). Learn how any reference video is made and turn it into skills: tear it apart (cuts, frames, script, sound), list its techniques, measure each one (layout px, fonts, colours, timing, easing, sound levels), rebuild that technique with your own content, put it side by side for the user's eye check, repeat until it matches, then write the measurements into a Video Making skill. Use for 'reverse engineer this video', 'how is this made', 'match this style', 'learn this channel's look'. For making videos, use BRANCH 1: video-automation."
---

# REVA: Reverse Engineering Video Anything

Two branches:
- **Branch 1, Video Making** (`video-automation` is its head): makes videos.
- **Branch 2, REVA** (this skill): studies a reference and upgrades branch 1.

Rule: REVA learns **techniques** (how a chart draws, how a card enters, how loud a swish is) and
rebuilds them with **your own script, voice and data**. It does not rebuild a whole reference film
scene by scene over its own narration. The output of REVA is a better skill, not a copy.

## Quick start: one command, one folder per study

```
set REVA=C:\Users\Ahmad\.kiro\crew\skills\reva\reva.cmd
%REVA% start finance-doc <url-or-file>                     tear down -> workspace\reva\finance-doc\ref\
%REVA% add finance-doc document-card --from 87 --to 93     strip at 5 fps + 3 stills + notes.md
%REVA% stills finance-doc document-card --at 89.5          more stills to measure
%REVA% colors finance-doc document-card                    paper / ink / accent hex
%REVA% sound finance-doc                                   transition sound numbers
%REVA% compare finance-doc document-card --mine <your.mp4> --mine-at 12,20
%REVA% status                                              every study and technique
```
Study folder: `study.json` (source + technique list + status), `ref\` (teardown),
`<technique>\theirs\` (strip, stills), `<technique>\notes.md` (measured numbers, gaps),
`<technique>\compare.jpg` (reference left, yours right). The existing study is `finance-doc`.
Build the rebuild in Branch 1 (`vm new lab-<technique> --from indo-crash`), then compare here.

## Tools (`scripts/`)

| Tool | Job |
|---|---|
| `teardown.py` | Download (yt-dlp) or take a file; find cuts, grab frames into contact sheets, pull subtitles (script + wpm), measure loudness. Writes `teardown.json`. |
| `technique.py strip` | One time range at 5 fps in one sheet: see how things enter and move. |
| `technique.py stills` | Full-size frames at chosen seconds: measure positions and sizes in px. |
| `technique.py palette` | Main colours and accent colours of a still, as hex. |
| `technique.py compare` | Reference stills (left) next to your render (right) at matching moments. |
| `sfx_probe.py` | Transition sound: jump in level overall / 4-8 kHz / 40-200 Hz, and how long the bright part lasts. |
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

## Techniques learned so far (finance documentary reference)

| Technique | Where it lives now | Status |
|---|---|---|
| Data line chart with photo cards | `tscs-finance-explainer` -> "Technique: data line chart" + `templates\technique-linechart.html` | matched, eye-checked |
| Topographic paper background | `tscs.js` -> `TSCS.topo` | matched |
| Transition sound v2: soft kit (swell / pop / hit) | `tscs-finance-explainer` -> "Technique: transition sound"; kit `video-automation\tools\sfx_kit.py`; QUALITY.md section 8 | matched by numbers, waiting for the user's ear |
| Full-bleed b-roll (drone shot, location chip, name plates) | `tscs-finance-explainer` -> "Technique: full-bleed b-roll"; `footage_hunt.py`; QUALITY.md section 7 | rebuilt 4x in indo-crash v3 |
| Coastline map opener | `tscs-finance-explainer` -> real-media A | rebuilt |
| Document card + highlighter | `tscs-finance-explainer` -> "Technique: document card + highlighter" + `templates\technique-document.html` | matched, eye-checked |
| Dark skyline title scenes | - | to do |
| Menu board with flags | - | to do |

## Measured reference numbers (keep for comparison)

- Picture: 1920x1080, 30 fps. Paper `#e9e8e6`, accent `#8b1a2b`, card frame `#c8323e`, ink `#1c1c1c`.
- Voice: ~155 wpm. Mix: about -16 LUFS.
- Transitions (sfx_probe, old method): bright part ~0.20 s, +19.4 dB in 4-8 kHz, +4.9 dB low body (median of 13 cuts).
- Sound events (sfx_lab events, first 180 s, voice removed): 42.7 per minute. Pops 70 (20 ms rise, 395 Hz, -22.4 dB
  vs voice), swells 22 (160 ms rise, 240 ms tail, 332 Hz, -13.8 dB), hits 18 (40 ms rise, 760 ms tail, 392 Hz, -18.2 dB).
- B-roll 170.4-175.0 s: one continuous drone shot, mean luma ~51 (p95 ~103), chip "SCBD, JAKARTA" top-left,
  name plate at x 170 y 520 (dark name box + red role bar), portrait card right, stamp "QUIT, 30 JAN".
- Something new appears every 1-2 s; cards enter in ~0.4 s steps.
