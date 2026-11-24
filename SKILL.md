---
name: reva
description: "BRANCH 2 - REVA (Reverse Engineering Video Anything). Router skill directing between two dedicated pipelines: (1) reva-code (pure coding video skills -> HyperFrames/Three.js/GSAP/Branch 1) and (2) reva-style (prompt-style scraping & cloning -> Automated-Lunch-Free). Use for any 'reverse engineer this video', 'scrape this style', 'clone this channel', or 'learn this animation technique' request."
---

# REVA: Pick the Right Tool & Skill

REVA shares one core measurement engine across **two separate tools and skill guides** so pure coding workflows and prompt-style workflows stay clean and distraction-free:

| If your goal is... | Load this Skill | Run this Tool | Output Target |
|---|---|---|---|
| **Pure coding & animation skills** (HyperFrames, Three.js, GSAP, charts, maps, `--grid` px layout, 5 fps timing, stereo SFX, `compare` + `verify`) | [`skills/reva-code/SKILL.md`](skills/reva-code/SKILL.md) | `python reva_code.py ...` *(or `reva-code` / `reva code`)* | `skill-export.md` → **Branch 1 (`video-making-skills`)** |
| **Prompt-style cloning** (art style, 5–8 `picture_rules`, `framing`, `scene_cards`, cut pace, still-vs-video ratio, WPM, palette, 8 golden beats) | [`skills/reva-style/SKILL.md`](skills/reva-style/SKILL.md) | `python reva_style.py ...` *(or `reva-style` / `reva style`)* | `<id>.style.json` → **`Automated-Lunch-Free`** |

Both tools store study folders in `./studies/<study>/` (or `REVA_WORKSPACE` / `--root`) and check your environment with `doctor`:

```cmd
python reva_code.py doctor
python reva_style.py doctor
```

Read the matching `SKILL.md` (`skills/reva-code/SKILL.md` or `skills/reva-style/SKILL.md`) before starting a study.
