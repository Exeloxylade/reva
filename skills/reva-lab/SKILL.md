---
name: reva-lab
description: "BRANCH 2C - REVA Engineering Lab (Extensible Engine Registry, Multi-Tool Test Bench & Cross-Study Reusable Pattern Library). Probe all code-callable video engines on the machine (HyperFrames, Three.js, D3, FFmpeg, Automated-Lunch-Free CLI, Blender, Manim, Remotion), dynamically register new tools, search & reuse proven patterns across videos (e.g. animated maps from Video 1 on Video 2), run multi-tool bake-offs, and promote verified breakthroughs into lab/library.json. Use for 'which tool can make this video', 'test bench bake-off', 'register new video tool', or 'reuse past video pattern'."
---

# REVA Engineering Lab

**CLI:** `python reva_lab.py ...` (or `reva-lab` / `reva lab ...`).
**Data:** [`lab/engines.json`](../../lab/engines.json) (extensible code-callable engine registry), [`lab/library.json`](../../lab/library.json) (cross-study reusable pattern library), [`lab/kit/`](../../lab/kit/) (shared reusable CAD/diagram primitives), [`lab/patterns/`](../../lab/patterns/) (verified code snapshots + AST symbol index), and [`lab/harnesses/`](../../lab/harnesses/) (starter test-bench rigs).

The Engineering Lab connects reference video measurements **and subject research** to **actual runnable tools** on your machine and compounds both visual learnings AND **actual structured code** across videos so Video 2's bench bootstraps straight from Video 1's proven modules and snapshots (`threejs_schematic.js` `RevaCAD`, `manim_schematic.py`, `lab/patterns/<id>/`) instead of blank starter cubes.

> Always run **Transcribe (`reva transcribe`) -> Internet Learning & Ingredient Sourcing (`reva research auto` / `shop` / `browse` -> `add-concept --mechanism --specs --anatomy --must-show` -> `complete`)** before `recommend` and `bench`. Use `web-browser` / [`reva-browse`](../reva-browse/SKILL.md) whenever you need JS-rendered docs, diagrams, footage, CC audio, 3D reference models, or datasets from outside. Keep bench rigs schematic/clay-first with zero texture polish waste.

---

## Core Capabilities

1. **Discover & Register Any Code-Callable Engine (`engines`, `register`)**
   - `python reva_lab.py engines` probes CLI binaries, Python modules, Branch 1 skills (`video-automation`, `gem-3d-world`, `map-video`, `finance-charts`, `tscs-finance-explainer`), and `Automated-Lunch-Free` CLI availability (`npm run make`, `npm run map`, `npm run style-test`).
   - When a new rendering tool comes out, register it once without modifying Python code:
     ```cmd
     python reva_lab.py register my-engine --name "My Engine" --kind code-3d --strengths "pbr-3d,volumetrics" --callable-via "my-engine render" --bin my-engine --install-hint "pip install my-engine"
     ```

2. **Check Past Learnings Before Building (`library`, `recommend`, `reuse`)**
   - Always search `lab/library.json` before designing a new rig (e.g. animated maps, line charts, low-poly 3D worlds):
     ```cmd
     python reva_lab.py library search "animated map"
     python reva_lab.py recommend my-study --tags "animated-map,route"
     ```
   - Link a matching baseline directly to a new study technique:
     ```cmd
     python reva_code.py reuse my-study geo-route --pattern animated-route-map
     ```
     This populates `notes.md` with the proven winning engine, rejected engines to skip, Branch 1 template path, baseline metrics, and a delta checklist.

3. **Run Multi-Tool Test-Bench Bake-Offs (`bench`, `run-bench`, `compare --tool`, `verdict`)**
   - When multiple candidate engines might match a reference technique, initialize & run isolated bench trials in 1 command (auto-renders stills + builds both full and zoomed compare sheets) without overwriting results:
     ```cmd
     python reva_code.py run-bench my-study hero-rig --tool threejs-webgl --at 0,1,2 --ref-at 12,14,16
     python reva_code.py run-bench my-study hero-rig --tool manim --at 0,1,2 --ref-at 12,14,16
     python reva_code.py verdict my-study hero-rig --winner threejs-webgl --rejected "manim:static 3D camera" --note "Matched reference cutaway"
     ```

4. **Promote Proven Patterns Back Into the Lab (`verify --promote`, `promote`, `promote-style`)**
   - Every verified technique or delivered style feeds back into `lab/library.json`:
     ```cmd
     python reva_code.py verify my-study hero-rig --tool blender-bpy --promote --id pbr-studio-rig --category 3d-explainer --tags "3d,pbr,lighting"
     python reva_lab.py promote-style my-style-study --tags "isometric,3d"
     ```

---

## Commands Reference (`reva_lab.py`)

| Command | Job |
|---|---|
| `engines [--kind ...] [--ready-only] [--json]` | Probe all registered engines, harnesses, and Branch 1 skills |
| `register <id> --strengths "..." [...]` | Register or update a new code-callable engine in `lab/engines.json` |
| `harnesses` | List starter test-bench harnesses in `lab/harnesses/` |
| `recommend <study> [--tags "..."] [--json]` | Match past reusable patterns and rank ready/upgrade engines for a study |
| `library list \| search <q> \| show <id> \| code <id>` | Browse, search, inspect JSON or saved source structure + symbols |
| `kit` | List shared modular code primitives in `lab/kit/` |
| `promote <study> <technique> [...]` | Promote a verified coding technique into `lab/library.json` |
| `promote-style <study> [...]` | Promote a completed `reva-style` style into `lab/library.json` |
| `sync-app [--app <dir>] [--json]` | Scan `Automated-Lunch-Free/styles/*` and sync all validated styles into `lab/library.json` |
