# REVA - Reverse Engineering Video Anything (Branch 2)

A Kiro Crew & Antigravity toolkit that scrapes how any reference video is built, using **one shared measurement engine** feeding **two specialized tools**:

| Tool / Skill | Purpose | Target |
|---|---|---|
| **[`reva-code`](skills/reva-code/SKILL.md)** (`reva_code.py` / `reva-code.cmd`) | **Pure coding skills** — rendering stack, `--grid` px rulers, 5 fps motion strips, hex palettes, stereo L-R SFX, side-by-side `compare.jpg`, `verify`, Branch 1 skill export | [`Exeloxylade/video-making-skills`](https://github.com/Exeloxylade/video-making-skills) (Branch 1) |
| **[`reva-style`](skills/reva-style/SKILL.md)** (`reva_style.py` / `reva-style.cmd`) | **Prompt-style cloning** — cut cadence, still-vs-moving ratio, WPM, palette, 8 golden beats, `<id>.style.json` scaffold, local dry-run `check`, and delivery | `Automated-Lunch-Free` (`styles/<id>/`) |

`reva.py` / `reva.cmd` remains available as a thin router (`reva code ...`, `reva style ...`, or direct top-level subcommands).

## The 3 Fundamental Goals of REVA

1. **Stack & Technical Research:** Identify the tools used (3D environments, WebGL, Three.js, GSAP, HyperFrames, Remotion, physics, shaders) and prove our code stack can achieve the same visual fidelity.
2. **Explanatory & Dynamic Grammar:** Deconstruct *why* the camera moves and how the 3D world is staged on purpose to make explanations dynamic, accurate, and engaging.
3. **Extract Reusable Skills (Not Blind Copies):** The 3D environment and camera must dynamically follow and prove the script. We capture the underlying explanatory capability (e.g. apparatus swapping, in-world spatial dimensions, failure simulation) so it can be rapidly used for any topic.

## Quick Commands

### Pure Coding Skills (`reva-code`)
```cmd
python reva_code.py doctor
python reva_code.py scrape my-study <url-or-file>
python reva_code.py add my-study <technique> --from 35 --to 59 --grid
python reva_code.py stills my-study <technique> --at 44,56 --grid
python reva_code.py colors my-study <technique> --at 44
python reva_code.py sound my-study --mode side --auto
python reva_code.py compare my-study <technique> --mine <your.mp4> --mine-at 12,24 --ref-at 44,56
python reva_code.py verify my-study <technique> --note "Eye-checked"
python reva_code.py skill my-study
```

### Prompt-Style Cloning (`reva-style` -> `Automated-Lunch-Free`)
```cmd
python reva_style.py doctor
python reva_style.py scrape my-study <url-or-file> --style my-style --beats 8
python reva_style.py beats my-study my-style --at 2,14,35,60,90,120,150,180
python reva_style.py check my-study
python reva_style.py deliver my-study
```

## Repository Layout

| File | Job |
|---|---|
| [`SKILL.md`](SKILL.md) | Router directing to [`skills/reva-code/SKILL.md`](skills/reva-code/SKILL.md) and [`skills/reva-style/SKILL.md`](skills/reva-style/SKILL.md) |
| [`reva_code.py`](reva_code.py) / [`reva-code.cmd`](reva-code.cmd) | Pure coding video reverse-engineering CLI (`--grid` pixel rulers, strips, SFX, `compare`, `verify`, `skill`) |
| [`reva_style.py`](reva_style.py) / [`reva-style.cmd`](reva-style.cmd) | Prompt-style cloning CLI (`scrape`, `beats`, `scaffold`, local dry-run `check`, `deliver`) |
| [`reva.py`](reva.py) / [`reva.cmd`](reva.cmd) | Unified thin router (`reva code ...` / `reva style ...` + top-level shortcuts) |
| [`scripts/_common.py`](scripts/_common.py) | FFmpeg/ffprobe lookup, path/workspace resolution, cut detection, rolling VTT/SRT parser, Pillow palette & badges |
| [`scripts/study_ops.py`](scripts/study_ops.py) | Shared study orchestration (`doctor`, `start`, `measure`, whole-video `colors`, dossier refresh) |
| [`scripts/teardown.py`](scripts/teardown.py) | Download (`yt-dlp`) or copy local video, detect cuts, render timestamped contact sheets, write transcripts, measure LUFS |
| [`scripts/measure.py`](scripts/measure.py) | Cut cadence (`median/p10/p90`), still/subtle/moving ratio, `max_static_sec`, multi-frame palette, WPM, style JSON values |
| [`scripts/technique.py`](scripts/technique.py) | 5 fps `strip`, full-res PNG `stills` + `--grid` coordinate overlay, multi-image `palette`, aspect-safe `compare.jpg` |
| [`scripts/sfx_lab.py`](scripts/sfx_lab.py) | Stereo L-R SFX `events` (with mono/dual-mono guard), cut `side` jumps, WAV `analyze`, Pillow-rendered `audition` video |
| [`scripts/style_kit.py`](scripts/style_kit.py) | Focused `dossier.md`, auto golden `beats.json` + preview, `scaffold_style`, local `check_style_local`, `export_skill` |
| [`tests/test_reva.py`](tests/test_reva.py) | Unit + FFmpeg end-to-end tests covering both `reva_code` and `reva_style` |

## Studies So Far

| Study | Went into |
|---|---|
| `finance-doc` (TSCS-style documentary) | `tscs-finance-explainer`, `finance-charts`, `video-automation` |
| `davin-kopdes` (Davin Azhar 3D Short) | `gem-3d-world`, style `warung` |
| `davin-lele` (Davin Azhar 3D Short) | `gem-3d-world`, style `kolam` (full 2m 16s film, own script) |
| `redha-beton` (3D civil engineering Short) | `gem-3d-world`, style `konstruksi`; `lib/construct3d.js` |

## Setup & Configuration

```cmd
pip install -r requirements.txt
python reva_code.py doctor
python reva_style.py doctor
```

- **Study folders:** Stored in `./studies/<study>/` (gitignored). Override with `REVA_WORKSPACE` or `--root <dir>`.
- **Target app (`reva-style`):** Auto-detects sibling `Automated-Lunch-Free` (or `Automated Lunch Free`). Override with `REVA_APP` or `--app <dir>`.
- **Binaries:** Uses `ffmpeg` / `ffprobe` on `PATH` (or `C:\ffmpeg\bin\`, or `REVA_FFMPEG` / `REVA_FFPROBE`), plus `node` for `reva-style check` / `deliver`.
