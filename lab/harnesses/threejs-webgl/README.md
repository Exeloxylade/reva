# Three.js / WebGL Single-Technique Bench Harness (Schematic / Clay-Mode First)

Fast isolated 3D technique testing without waiting for a full multi-minute video render:

- **Schematic / Clay-Mode First Rule:** Never waste compute or iterations authoring rebar bump textures, wood grain, concrete speckles, or decorative grass in the bench! Use crisp matte/clay role-coded colors (`MeshLambertMaterial`) so 100% of your precision goes into **exact geometric topology, engineering proportions, cross-sections, and clear cause-and-effect labels**.
- **Steps:**
  1. `bench_scene.html` reads `?t=<sec>&w=<W>&h=<H>`, loads local `three.min.js`, and draws one apparatus + real-3D-projected SVG calipers with `window.renderAt(t)`.
  2. Inspect `bench.json` for `width`, `height`, `transcript_excerpt`, `anatomy_specs` (`mechanism`, `specs`, `anatomy`, `must_show`), and `checklist_path` (`checklist.json`).
  3. Capture isolated keyframes in ~3 seconds via headless WebGL:
     ```cmd
     python render_bench.py --at 0,1,2
     ```
  4. Compare both **full-frame** and **zoomed detail** (`--crop`) directly from the rendered PNG stills:
     ```cmd
     python reva_code.py compare <study> <technique> --tool threejs-webgl --mine out_0.png,out_1.png,out_2.png --ref-at <t1,t2,t3>
     python reva_code.py compare <study> <technique> --tool threejs-webgl --mine out_0.png,out_1.png,out_2.png --ref-at <t1,t2,t3> --crop 0.12,0.20,0.76,0.56
     ```
  5. Pass every `must_show` visual audit item before calling `verify`:
     ```cmd
     python reva_code.py audit <study> <technique> --show
     python reva_code.py audit <study> <technique> --pass 1 --note "Verified zoomed compare"
     python reva_code.py verify <study> <technique> --tool threejs-webgl
     ```
