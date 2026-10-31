# REVA - Reverse Engineering Video Anything (Branch 2)

A Kiro Crew skill that learns how a reference video is made and turns what it learns into making skills.
It tears the video apart (cuts, frames, script, sound), lists its techniques, measures each one
(layout px, fonts, colours, timing, easing, sound levels), rebuilds it with **your own content**,
and compares the two side by side until they match. The result is a better skill, never a copy of the film.

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

## Install

Copy this folder to `%USERPROFILE%\.kiro\crew\skills\reva`. Needs ffmpeg (`C:\ffmpeg\bin` or on PATH),
Python 3 with numpy and Pillow, and `pip install yt-dlp`. Study folders (reference downloads, frames) stay in
`workspace\reva\` and are never published.
