# REVA - Reverse Engineering Video Anything (Branch 2)

A Kiro Crew & Antigravity skill that scrapes how any reference video is made, measures every visual/pacing/audio signal, verifies rebuilds side-by-side, and turns proven patterns into reusable **Branch 1 video-making skills** or **Automated Lunch Free** style clones.

## The 3 Fundamental Goals of REVA

1. **Stack & Technical Research:** Identify the tools used (3D environments, WebGL, Three.js, GSAP, HyperFrames, Remotion, physics, shaders) and prove our code stack can achieve the same visual fidelity.
2. **Explanatory & Dynamic Grammar:** Deconstruct *why* the camera moves and how the 3D world is staged on purpose to make explanations dynamic, accurate, and engaging.
3. **Extract Reusable Skills (Not Blind Copies):** The 3D environment and camera must dynamically follow and prove the script. We capture the underlying explanatory capability (e.g., apparatus swapping, in-world spatial dimensions, failure simulation) so it can be rapidly used for any topic.

## The Branches

| Branch | Repo | Job |
|---|---|---|
| 1. Video Making (+ GEM 3D Shorts) | [Exeloxylade/video-making-skills](https://github.com/Exeloxylade/video-making-skills) | Makes videos |
| 2. REVA | This repo | Scrapes references, measures techniques, clones styles, exports proven skills |

## Quick Commands

```cmd
python reva.py doctor                                                    check tools, workspace, and app path
python reva.py scrape my-study <url-or-file> --style my-style --beats 8  1-command teardown + measure + sound + dossier + style + beats
python reva.py deliver my-study                                          validate placeholders, copy to Automated-Lunch-Free, run style-check

python reva.py add my-study <technique> --from 87 --to 93                isolate 1 technique (5 fps strip + 3 stills + notes.md)
python reva.py stills / colors / sound                                   measure px, hex palette, stereo L-R SFX events
python reva.py compare my-study <technique> --mine <mp4> --mine-at ...   side-by-side compare.jpg (ref left, yours right)
python reva.py verify my-study <technique> --note "matched"              record verification proof
python reva.py skill my-study                                            export proven Branch 1 skill spec (skill-export.md)
python reva.py status                                                    list studies, techniques, and deliveries
```

## Repository Files

| File | Job |
|---|---|
| [`SKILL.md`](SKILL.md) | Two streamlined workflows (Style Cloning & Branch 1 Skill Gathering), completed studies, measured benchmarks |
| [`reva.py`](reva.py) / [`reva.cmd`](reva.cmd) | Unified CLI orchestrator (`doctor`, `scrape`, `start`, `measure`, `add`, `stills`, `colors`, `sound`, `compare`, `verify`, `beats`, `scaffold`, `deliver`, `skill`, `status`) |
| [`scripts/_common.py`](scripts/_common.py) | Shared FFmpeg/ffprobe lookup, path/workspace resolution, cut detection, VTT/SRT rolling-caption parser, Pillow palette & badges |
| [`scripts/teardown.py`](scripts/teardown.py) | Download (`yt-dlp`) or copy local video, detect cuts, render timestamped contact sheets, write `transcript.json/.txt/script.txt`, measure LUFS |
| [`scripts/measure.py`](scripts/measure.py) | Cut cadence (`median/p10/p90`, per min, thirds), still/subtle/moving ratio, `max_static_sec`, multi-frame palette, WPM, style JSON metrics |
| [`scripts/technique.py`](scripts/technique.py) | Single-technique inspection: timestamped 5 fps `strip`, full-res PNG `stills`, multi-image `palette`, aspect-safe `compare.jpg` |
| [`scripts/sfx_lab.py`](scripts/sfx_lab.py) | Stereo L-R SFX `events` (with mono/dual-mono guard), cut `side` jumps, WAV `analyze`, Pillow-rendered `audition` video |
| [`scripts/style_kit.py`](scripts/style_kit.py) | Study `dossier.md`, auto golden `beats.json` + preview, `scaffold` style JSON + `.md` twin, placeholder check, `export_skill` |
| [`tests/test_reva.py`](tests/test_reva.py) | Automated unit + synthetic FFmpeg end-to-end tests |

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
python reva.py doctor
```

- **Study folders:** Stored in `./studies/<study>/` (gitignored). Override with `REVA_WORKSPACE` or `--root <dir>`.
- **Target app:** Auto-detects sibling `Automated-Lunch-Free` (or `Automated Lunch Free`). Override with `REVA_APP` or `--app <dir>`.
- **Binaries:** Uses `ffmpeg` / `ffprobe` on `PATH` (or `C:\ffmpeg\bin\`, or `REVA_FFMPEG` / `REVA_FFPROBE`), plus `node` for `reva deliver`.
