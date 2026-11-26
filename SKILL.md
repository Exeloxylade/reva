---
name: reva
description: "BRANCH 2 - REVA (Reverse Engineering Video Anything). Router skill directing between three dedicated pipelines: (1) reva-lab (extensible engine registry, multi-tool test bench & cross-study reusable pattern library), (2) reva-code (pure coding video skills -> HyperFrames/Three.js/GSAP/Branch 1), and (3) reva-style (prompt-style scraping & cloning -> Automated-Lunch-Free CLI). Use for any 'reverse engineer this video', 'scrape this style', 'clone this channel', 'test bench', or 'learn this animation technique' request."
---

# REVA: Engineering Lab & Reverse-Engineering Suite

REVA pairs **one shared Understanding Brain + Measurement Engine** with an **Engineering Lab** (`lab/engines.json`, `lab/library.json`, `lab/harnesses/`) across **three specialized tools and skill guides**:

## The Fundamental 3-Phase Brain (Always Run in Order)

Never jump straight to copying visuals or guessing what an animation/dish/concept is:

1. **Transcribe First (`reva transcribe <study>`):** Extract speech from subtitles, auto-STT, or direct agent listening (`ref/audio.mp3` + `--from-file`/`--from-text`, or `--silent` for pure ASMR).
2. **Learn & Research from the Internet (`reva research ...`):** Read `ref/transcript.txt` and `research/brief.md`. Run `reva research auto <study>` (1-command claims -> web search -> Wikimedia diagrams -> article fetch) or step through `claims` / `search` / `images --download` / `fetch <url>`, then lock **physical mechanism + verified specs + geometric anatomy + falsifiable `must_show` checks** (`reva research add-concept --mechanism ... --specs ... --anatomy ... --must-show ... --wrong ...`). `research complete` enforces real external URL/asset evidence.
3. **Schematic/Clay Test Bench, 1-Command Run & Hard Visual Audit (`bench` -> `run-bench` -> `audit` -> `verify`):** Never waste time polishing rebar bumps, wood grain, concrete speckles, or grass inside a test bench. Build clean matte clay/CAD schematics focusing 100% on exact geometry, proportions, and causal explanation; run `reva-code run-bench <study> <technique>` to render stills + generate **both full and `--crop` zoomed comparisons** in one command; pass every `must_show` check (`reva-code audit`); then run `verify`.

| If your goal is... | Load this Skill | Run this Tool | Output Target |
|---|---|---|---|
| **Discover/register engines, check past video patterns, or pick candidate tools** | [`skills/reva-lab/SKILL.md`](skills/reva-lab/SKILL.md) | `python reva_lab.py ...` *(or `reva-lab` / `reva lab`)* | `lab/engines.json` & `lab/library.json` |
| **Pure coding & animation skills** (`--grid` px layout, 5 fps timing, stereo SFX, multi-tool `bench` + `compare --tool` + `verdict`, `verify --promote`) | [`skills/reva-code/SKILL.md`](skills/reva-code/SKILL.md) | `python reva_code.py ...` *(or `reva-code` / `reva code`)* | `skill-export.md` → **Branch 1 (`video-making-skills`)** & `lab/library.json` |
| **Prompt-style cloning** (art style, 5–8 `picture_rules`, `framing`, `scene_cards`, cut pace, still-vs-video ratio, WPM, palette, 8 golden beats) | [`skills/reva-style/SKILL.md`](skills/reva-style/SKILL.md) | `python reva_style.py ...` *(or `reva-style` / `reva style`)* | `<id>.style.json` → **`Automated-Lunch-Free` CLI** |

All tools store study folders in `./studies/<study>/` (or `REVA_WORKSPACE` / `--root`) and check environment health with:

```cmd
python reva_lab.py engines
python reva_code.py doctor
python reva_style.py doctor
```

Read the matching `SKILL.md` (`skills/reva-lab/SKILL.md`, `skills/reva-code/SKILL.md`, or `skills/reva-style/SKILL.md`) before starting a study.
