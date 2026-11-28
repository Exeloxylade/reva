# Three.js / WebGL Single-Technique Bench Harness

Fast isolated 3D technique testing without waiting for a full multi-minute video render. Two kit modes are auto-staged into every `threejs-webgl` bench:

1. **Clay/CAD Topology Check (`RevaCAD` in `threejs_schematic.js`)** — Fast role-coded `MeshLambertMaterial` geometry & caliper verification (`bench_scene.html`).
2. **Cozy Blender-Style Final Polish (`RevaCanvas` in `threejs_canvas.js` + `RevaPBR` in `threejs_pbr_materials.js`)** — Self-contained 2x SSAA post-process (8-tap Depth Contact AO + silhouette-only warm charcoal ink + ACES filmic sRGB) paired with calibrated rebar, pewter stirrup, Voronoi concrete, speckled concrete, terracotta brick, honey-pine formwork, frosted cover glass, and spring-meadow grass diorama.

## Steps
1. Inspect `bench.json` for `width`, `height`, `transcript_excerpt`, `anatomy_specs` (`mechanism`, `specs`, `anatomy`, `must_show`), and `checklist_path` (`checklist.json`).
2. Load `./three.min.js` plus `./threejs_schematic.js` (and optionally `./threejs_pbr_materials.js` + `./threejs_canvas.js`) in `bench_scene.html`, exposing `window.renderAt(t)` for `?t=<sec>&w=<W>&h=<H>`.
3. Capture isolated keyframes in ~3 seconds via headless WebGL:
   ```cmd
   python render_bench.py --at 0,1,2
   ```
4. Compare both **full-frame** and **zoomed detail** (`--crop`) directly against the reference PNG stills:
   ```cmd
   python reva_code.py compare <study> <technique> --tool threejs-webgl --mine out_0.png,out_1.png,out_2.png --ref-at <t1,t2,t3>
   python reva_code.py compare <study> <technique> --tool threejs-webgl --mine out_0.png,out_1.png,out_2.png --ref-at <t1,t2,t3> --crop 0.10,0.18,0.80,0.64
   ```
5. Pass every `must_show` visual audit item before calling `verify`:
   ```cmd
   python reva_code.py audit <study> <technique> --show
   python reva_code.py audit <study> <technique> --pass 1 --note "Verified zoomed compare"
   python reva_code.py verify <study> <technique> --tool threejs-webgl
   ```
