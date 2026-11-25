---
name: reva
description: "BRANCH 2 - REVA (Reverse Engineering Video Anything). Router skill directing between three dedicated pipelines: (1) reva-lab (extensible engine registry, multi-tool test bench & cross-study reusable pattern library), (2) reva-code (pure coding video skills -> HyperFrames/Three.js/GSAP/Branch 1), and (3) reva-style (prompt-style scraping & cloning -> Automated-Lunch-Free CLI). Use for any 'reverse engineer this video', 'scrape this style', 'clone this channel', 'test bench', or 'learn this animation technique' request."
---

# REVA: Engineering Lab & Reverse-Engineering Suite

REVA pairs **one shared measurement engine** with an **Engineering Lab** (`lab/engines.json`, `lab/library.json`, `lab/harnesses/`) across **three specialized tools and skill guides**:

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
