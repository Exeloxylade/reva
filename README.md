# REVA - Reverse Engineering Video Anything (Branch 2)

A Kiro Crew & Antigravity skill that learns how any reference video is made and turns what it learns into high-quality video-making skills.

## The 3 Fundamental Goals of REVA

1. **Stack & Technical Research:** Identify the tools used (3D environments, WebGL, Three.js, GSAP, HyperFrames, Remotion, physics, shaders) and prove our code stack can achieve the same visual fidelity.
2. **Explanatory & Dynamic Grammar:** Deconstruct *why* the camera moves and how the 3D world is staged on purpose to make explanations dynamic, accurate, and engaging.
3. **Extract Reusable Skills (Not Blind Copies):** The 3D environment and camera must dynamically follow and prove the script. We copy the underlying explanatory capability (e.g. apparatus swapping, in-world spatial dimensions, failure simulation) so it can be rapidly used for ANY topic.

## The branches

| Branch | Repo | Job |
|---|---|---|
| 1. Video Making (+ GEM 3D Shorts) | [Exeloxylade/video-making-skills](https://github.com/Exeloxylade/video-making-skills) | makes videos |
| 2. REVA | this repo | studies references, measures techniques, writes them into Branch 1 |

## Commands

```
set REVA=%USERPROFILE%\.kiro\crew\skills\reva\reva.cmd
%REVA% start <study> <url-or-file>                    tear down -> workspace\reva\<study>\ref\
%REVA% add <study> <technique> --from 87 --to 93       strip at 5 fps + 3 stills + notes.md
%REVA% stills / colors / sound / compare / status       measure, then compare with your rebuild
```

| File | Job |
|---|---|
| [`SKILL.md`](SKILL.md) | the method, every tool, the studies, techniques learned and measured numbers |
| `reva.py` / `reva.cmd` | the `reva` command (study folders) |
| `scripts/teardown.py` | download or take a file; cuts, contact sheets, subtitles + wpm, loudness |
| `scripts/technique.py` | strip, stills, palette, compare |
| `scripts/sfx_lab.py` | every sound effect with the voice removed: count, kind, rise, tail, brightness, level |
| `scripts/sfx_probe.py`, `scripts/compare.py` | transition sound numbers; rough whole-video score |

## Studies so far

| Study | Went into |
|---|---|
| `finance-doc` (TSCS-style documentary) | `tscs-finance-explainer`, `finance-charts`, `video-automation` |
| `davin-kopdes` (Davin Azhar 3D Short) | `gem-3d-world`, style `warung` |
| `davin-lele` (Davin Azhar 3D Short) | `gem-3d-world`, style `kolam` (full 2m 16s film, own script) |
| `redha-beton` (3D civil engineering Short) | `gem-3d-world`, style `konstruksi`; `lib/construct3d.js` |

## Install

Copy this folder to `%USERPROFILE%\.kiro\crew\skills\reva`. Needs ffmpeg (`C:\ffmpeg\bin` or on PATH),
Python 3 with numpy and Pillow, and `pip install yt-dlp`. Study folders (reference downloads, frames) stay in
`workspace\reva\` and are never published.
