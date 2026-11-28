# REVA - Reverse Engineering Video Anything (Branch 2)

An **Engineering Lab** and video reverse-engineering toolkit for Kiro Crew, Codex, and Antigravity. **One shared measurement engine** + **extensible Engine Registry & Reusable Pattern Library (`lab/`)** feed **three specialized tools**:

| Tool / Skill | Purpose | Target |
|---|---|---|
| **[`reva-lab`](skills/reva-lab/SKILL.md)** (`reva_lab.py` / `reva-lab.cmd`) | **Engineering Lab** — probe available engines (`11`), inspect shared `lab/kit/`, search & reuse structured-code patterns (`lab/patterns/`) | `lab/engines.json`, `lab/kit/` & `lab/library.json` |
| **[`cozy-3d-explainer`](skills/cozy-3d-explainer/SKILL.md)** | **General 3D Explainer Style** — topic-agnostic Cozy Blender-Matte + 16-tap GTAO + silhouette ink + Fresnel cutaways + HUD guide | Any `threejs-webgl` scene (`RevaCanvas` + `RevaPBR`) |
| **[`reva-browse`](skills/reva-browse/SKILL.md)** (`reva.py research browse\|shop`) | **Web Browse & Ingredient Sourcer** — headless Edge/Chrome JS DOM + screenshot capture and 6-aisle external asset shop (`docs`, `images`, `footage`, `audio`, `models3d`, `data`) | `research/assets/` & `research/brief.{json,md}` |
| **[`reva-code`](skills/reva-code/SKILL.md)** (`reva_code.py` / `reva-code.cmd`) | **Pure coding skills** — `--grid` px rulers, 5 fps motion strips, hex palettes, stereo L-R SFX, test-bench bake-offs (`bench`, `compare --tool`, `verdict`), `verify --promote`, Branch 1 export | [`Exeloxylade/video-making-skills`](https://github.com/Exeloxylade/video-making-skills) (Branch 1) |
| **[`reva-style`](skills/reva-style/SKILL.md)** (`reva_style.py` / `reva-style.cmd`) | **Prompt-style cloning** — cut cadence, still-vs-moving ratio, WPM, palette, 8 golden beats, `<id>.style.json` scaffold, local dry-run `check`, CLI delivery & promotion | `Automated-Lunch-Free` CLI (`styles/<id>/`) |

`reva.py` / `reva.cmd` remains available as a thin unified router (`reva lab ...`, `reva code ...`, `reva style ...`, or direct top-level subcommands).

## The Fundamental 3-Phase Brain + Lab Goals

1. **Transcribe First (`reva transcribe`):** Every spoken video gets a real timestamped transcript (`ref/transcript.{json,txt}`) via embedded captions, optional local/cloud STT, or compact `ref/audio.mp3` listening + import (unless explicitly marked `--silent`).
2. **Learn & Research from the Internet (`reva research`):** Extract transcript claims (`reva research claims`), search external articles/specs & Wikimedia diagrams (`search_web`, `reva research search`, `reva research images --download`), fetch real reference pages into `research/assets/` (`reva research fetch <url>`), and record **physical mechanism + verified specs + geometric anatomy + falsifiable `must_show` checks** (`--mechanism`, `--specs`, `--anatomy`, `--must-show`, `--wrong`). `research complete` blocks without verified URL/asset evidence.
3. **Schematic/Clay-First Test Bench, Zoomed Compare & Hard Audit Gate:** Build clean clay/CAD schematics with zero texture waste, compare full + `--crop` zoomed views, and pass every `checklist.json` visual item (`reva-code audit`) before `verify` or full-film assembly.

## Quick Commands

### Step 1 & 2: Fundamental Brain (`transcribe` & `research`)
```cmd
python reva.py transcribe my-study [--from-file subs.srt | --silent]
python reva.py research init my-study
python reva.py research auto my-study
python reva.py research shop my-study "concrete stirrup" --aisle all --download 1
python reva.py research browse my-study "https://..." --query "seismic hook 135" --discover-links
python reva.py research claims my-study
python reva.py research search my-study "query terms"
python reva.py research images my-study "stirrup rebar concrete" --download 1
python reva.py research fetch my-study "https://..." --query "seismic hook 135 confinement"
python reva.py research add-concept my-study --term "..." --meaning "..." --mechanism "..." --specs "..." --anatomy "..." --must-show "..." --wrong "..." --at 16.5
python reva.py research add-source my-study --title "..." --kind standard --url "https://..." --takeaway "..."
python reva.py research complete my-study --what "..." --domain "..." --implication "..."
python reva.py audit my-study <technique> --show
```

### Engineering Lab (`reva-lab`)
```cmd
python reva_lab.py engines
python reva_lab.py kit
python reva_lab.py library search "stirrup"
python reva_lab.py library code sni-stirrup-135-cutaway
python reva_lab.py recommend my-study --tags "animated-map,route"
python reva_lab.py register my-engine --name "My Engine" --kind code-3d --strengths "pbr-3d,physics" --bin my-engine
```

### Pure Coding & Test-Bench Bake-Off (`reva-code`)
```cmd
python reva_code.py doctor
python reva_code.py scrape my-study <url-or-file>
python reva_code.py add my-study route-map --from 35 --to 59 --grid
python reva_code.py reuse my-study route-map --pattern animated-route-map
python reva_code.py bench my-study route-map --tool threejs-webgl
python reva_code.py run-bench my-study route-map --tool threejs-webgl --at 0,1,2 --ref-at 44,56,60
python reva_code.py verdict my-study route-map --winner hyperframes-2d --rejected "ffmpeg-compositor:static labels"
python reva_code.py verify my-study route-map --tool hyperframes-2d --promote --category animated-map
python reva_code.py skill my-study
```

### Prompt-Style Cloning (`reva-style` -> `Automated-Lunch-Free`)
```cmd
python reva_style.py doctor
python reva_style.py scrape my-study <url-or-file> --style my-style --beats 8
python reva_style.py beats my-study my-style --at 2,14,35,60,90,120,150,180
python reva_style.py check my-study
python reva_style.py deliver my-study --promote
```

## Repository Layout

| File | Job |
|---|---|
| [`SKILL.md`](SKILL.md) | Router directing to [`skills/reva-lab/SKILL.md`](skills/reva-lab/SKILL.md), [`skills/cozy-3d-explainer/SKILL.md`](skills/cozy-3d-explainer/SKILL.md), [`skills/reva-code/SKILL.md`](skills/reva-code/SKILL.md), and [`skills/reva-style/SKILL.md`](skills/reva-style/SKILL.md) |
| [`reva_lab.py`](reva_lab.py) / [`reva-lab.cmd`](reva-lab.cmd) | Engineering Lab CLI (`engines`, `register`, `harnesses`, `recommend`, `library`, `promote`, `promote-style`, `sync-app`) |
| [`reva_code.py`](reva_code.py) / [`reva-code.cmd`](reva-code.cmd) | Pure coding & test-bench CLI (`add`, `bench`, `reuse`, `stills --grid`, `colors`, `sound`, `compare --tool`, `verdict`, `verify --promote`, `skill`) |
| [`reva_style.py`](reva_style.py) / [`reva-style.cmd`](reva-style.cmd) | Prompt-style cloning CLI (`scrape`, `beats`, `scaffold`, local dry-run `check`, `deliver`) |
| [`reva.py`](reva.py) / [`reva.cmd`](reva.cmd) | Unified thin router (`reva lab ...` / `reva code ...` / `reva style ...` + top-level shortcuts) |
| [`lab/engines.json`](lab/engines.json) | Extensible declarative registry of code-callable render/AI engines |
| [`lab/library.json`](lab/library.json) | Cross-study Reusable Pattern Library seeded with proven patterns |
| [`lab/harnesses/`](lab/harnesses) | Minimal starter test-bench harnesses (`ffmpeg-probe`, `hyperframes-2d`, `threejs-webgl`, `blender-bpy`, `automated-lunch-free`) |
| [`scripts/_common.py`](scripts/_common.py) | FFmpeg/ffprobe lookup, workspace/lab/Branch-1 discovery, cut detection, rolling VTT/SRT parser, Pillow palette & badges |
| [`scripts/transcribe.py`](scripts/transcribe.py) | Step 1 Brain: `ref/audio.mp3` extraction, `.srt`/`.vtt`/`.json`/`.txt` import, optional STT backends (`faster-whisper`, `whisper`, `gemini`, `groq`, `openai`) |
| [`scripts/research.py`](scripts/research.py) | Step 2 Brain: transcript claim extraction, multi-provider web search (`Wikipedia`/`OpenAlex`/`DDG`), Wikimedia image lookup, `fetch` page cache, `mechanism`/`specs`/visual-anatomy logging & evidence gate (`research/brief.{json,md}`) |
| [`scripts/lab_engine.py`](scripts/lab_engine.py) | Engine probing, custom engine registration, test-bench setup, and capability recommendations |
| [`scripts/lab_library.py`](scripts/lab_library.py) | Pattern search, cross-video reuse linking, and technique/style promotion |
| [`scripts/study_ops.py`](scripts/study_ops.py) | Shared study orchestration (`doctor`, `start`, `measure`, whole-video `colors`, dossier refresh) |
| [`scripts/teardown.py`](scripts/teardown.py) | Download (`yt-dlp`) or copy local video, detect cuts, render timestamped contact sheets, write transcripts, measure LUFS |
| [`scripts/measure.py`](scripts/measure.py) | Cut cadence (`median/p10/p90`), still/subtle/moving ratio, `max_static_sec`, multi-frame palette, WPM, style JSON values |
| [`scripts/technique.py`](scripts/technique.py) | 5 fps `strip`, full-res PNG `stills` + `--grid` coordinate overlay, multi-image `palette`, labeled `compare[_<tool>].jpg` |
| [`scripts/sfx_lab.py`](scripts/sfx_lab.py) | Stereo L-R SFX `events` (with mono/dual-mono guard), cut `side` jumps, WAV `analyze`, Pillow-rendered `audition` video |
| [`scripts/style_kit.py`](scripts/style_kit.py) | Focused `dossier.md` with lab recommendations, golden `beats.json` + preview, `scaffold_style`, `check_style_local`, `export_skill` |
| [`tests/test_reva.py`](tests/test_reva.py) | Unit + FFmpeg end-to-end tests covering `reva_lab`, `reva_code`, `reva_style`, and unified `reva` |

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
python reva_lab.py engines
python reva_code.py doctor
python reva_style.py doctor
```

- **Study folders:** Stored in `./studies/<study>/` (gitignored). Override with `REVA_WORKSPACE` or `--root <dir>`.
- **Engineering Lab:** Stored in `./lab/`. Override with `REVA_LAB_DIR` or `--lab-dir <dir>`.
- **Branch 1 skills:** Auto-detects `REVA_BRANCH1`, sibling `video-making-skills`, `~/.kiro/crew/skills`, `~/.codex/skills`, and `~/.gemini/config/plugins`.
- **Target app (`reva-style`):** Auto-detects sibling `Automated-Lunch-Free` (or `Automated Lunch Free`). Override with `REVA_APP` or `--app <dir>`.
- **Binaries:** Uses `ffmpeg` / `ffprobe` on `PATH` (or `C:\ffmpeg\bin\`, or `REVA_FFMPEG` / `REVA_FFPROBE`), plus `node` for `reva-style check` / `deliver`.
