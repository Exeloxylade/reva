---
name: cozy-3d-explainer
description: "Topic-agnostic general 3D explainer style guide ('Cozy Blender-Matte Diorama + Silhouette Ink + Technical Clarity') built on REVA's Three.js WebGL kit (threejs_canvas.js RevaCanvas + threejs_pbr_materials.js RevaPBR). Use whenever building ANY 3D educational or engineering explainer video (engines, plumbing, electronics, solar, physics, biology, architecture, machines, or construction) that needs bright daylight softness, 16-tap Depth GTAO, silhouette-only ink outlines, Fresnel X-ray cutaways, continuous camera grammar, and minimal 3D-tracked HUD callouts."
---

# Cozy 3D Explainer — General Style Instruction (`threejs-webgl`)

This skill defines the **complete, topic-agnostic visual, camera, material, HUD, and audio style** for procedural Three.js (`three.min.js`) explainer videos. Use it on **any domain** — construction is only one example.

**Core runtime stack (auto-staged into every `threejs-webgl` bench):**
- [`lab/kit/threejs_canvas.js`](../../lab/kit/threejs_canvas.js) (`RevaCanvas`) — self-contained studio renderer, lighting, 2x SSAA 16-tap Depth GTAO + silhouette ink post-pass, ACES color pipeline, grass/soil diorama, and floating HUD.
- [`lab/kit/threejs_pbr_materials.js`](../../lab/kit/threejs_pbr_materials.js) (`RevaPBR`) — universal procedural materials, beveled boxes, fractured shards, Fresnel translucent X-ray shells, and minimalist scale worker.
- [`lab/kit/threejs_schematic.js`](../../lab/kit/threejs_schematic.js) (`RevaCAD`) — fast flat/clay topology pass helper + structural geometry primitives.

---

## 1. Visual Aesthetic Philosophy ("Cozy Matte Diorama + Technical Clarity")

- **Bright Soft-Daylight World:** Always frame the hero assembly against a smooth sky-to-horizon gradient (`#b8cad8` zenith → `#dae4ec` mid → `#eef2f5` horizon), never a harsh pitch-black studio or clipped pure white (`#ffffff`).
- **Grounded Diorama Island:** Ground the hero inside a miniature cutaway base (`buildCozyGrassDiorama()` spring-meadow lawn `#9fcc70` over ochre-pebble soil cross-section, OR a clean matte tabletop/plinth scaled to your topic) so the camera always feels like it is orbiting a physical model.
- **Warm Desaturated Base + Crisp Semantic Accents:** Keep real-world surfaces (concrete, stone, wood, painted metal, soil) matte and warm-neutral (`roughness: 0.70–0.92`) so bright saturated UI tags and calipers read effortlessly without visual noise.
- **Fresnel X-Ray Cutaways Over Hard Hide:** When explaining hidden internal mechanisms (pistons, wiring, valves, pipes, rebar inside casings), wrap the outer casing in a Fresnel frosted translucent shell (`createConcreteCoverGlassMaterial({ color })`) so interior motion stays readable in full context.

---

## 2. Lighting, Shadows, Depth GTAO & Silhouette Ink Rules

Call `RevaCanvas.boot({ W: 1080, H: 1920 })` and preserve its calibrated 3-point + post-processing balance:

| Parameter / Layer | Calibrated Default | Visual Job |
|---|---|---|
| Key Sun (`sunDir`, `sunK`) | `[28, 34, 22]`, `1.12` | ~42° warm daylight casting clear diagonal directional shadows |
| Hemisphere + Cool Bounce | `hemi: 0.36`, `fillK: 0.14` | Soft cozy skylight fill without washing out shadows |
| Tight Shadow Frustum | `shadowExtent: 5.8`, `radius: 5.0`, `normalBias: 0.008` | Keeps thin rods/pipes firmly attached to their cast shadows |
| 2-Ring 16-Tap Depth GTAO | `aoStrength: 0.56`, `aoRadius: 14.0` | Tight contact darkening at seams + wide corner occlusion |
| Silhouette-Only Ink | `inkColor: #2e2925`, `inkK: 0.54`, `depthK: 0.010`, `normK: 0.54` | Thin warm-charcoal outlines separating major volumes cleanly |
| Color Output | ACES Filmic (`exposure: 0.92`) + sRGB gamma | Film-like highlight roll-off, rich midtones, zero neon blowouts |

> **Golden Ink Rule:** Mark high-frequency micro-detail meshes (threaded bolts, heat-sink fins, corrugated ribs, gears with fine teeth, foliage blades) with `RevaCanvas.markNoInk(mesh, true)`. Their outer depth silhouette remains ink-crisp while interior surface ridges never smudge!

---

## 3. Continuous-Camera & Narrative Grammar (`0` Hard Cuts / `100%` Moving)

Never string static slides together while narration speaks. Structure a full explainer around this 6-act continuous-camera arc:

1. **Cold-Open Hook (`0–12s`):** Zoom directly onto the hero failure/myth in tight close-up (dramatic fracture/overheat/collapse or counter-intuitive size-vs-geometry reveal) to establish *why the mechanism matters*.
2. **Isometric Assembly Overview (`12–18s`):** Orbit smoothly out to a whole-assembly shot with a minimalist scale reference (`RevaPBR.buildWorkerFigure()` or familiar prop) and drop numbered pins `(1)…(N)` showing where each rule lives in 3D space.
3. **Numbered Rule Chapters (`N` cycles, `12–22s` each):**
   - **A. Mechanism Close-Up:** Glide smoothly into the active part as it assembles, bends, rotates, flows, or compresses in real time.
   - **B. 3D-Tracked Spec Caliper:** Anchor `hud.caliper()` + `hud.tag()` directly onto exact 3D points so labels move organically with the geometry.
   - **C. Cause-and-Effect Contrast:** Animate the wrong vs. right failure mode (`defect -> stress -> failure`) or clear X-ray comparison.
4. **Cutaway / Fresnel X-Ray Reveal:** Fade/slice an outer wall into translucent Fresnel glass to tie surface rules back to hidden internal loads/flows.
5. **Full Payoff Zoom-Out (`5–8s`):** Pull back to the complete finished diorama in action (e.g., finished machine, house, or working circuit) reinforcing the core thesis.
6. **Dark Summary Checklist Card (`3–4s`):** Dim background slightly (`rgba(20, 24, 30, 0.92)`) and reveal concise green checkmarks summarizing every numbered rule.

---

## 4. Universal Material & Geometry Rules (Any Topic)

When writing custom materials or props for any new domain inside `threejs-webgl`, follow these exact rules:

1. **Fix sRGB Linearization:** Pass `useSRGB = true` on every `CanvasTexture` albedo map, and call `.convertSRGBToLinear()` (or `THREE.Color(hex).convertSRGBToLinear()`) on **all** untextured solid colors (`color: ...`) before feeding them into `RevaCanvas`'s ACES+gamma pass.
2. **Never Leave Flat Plastic Surfaces:** Generate procedural `512x512`–`1024x1024` textures combining multi-scale `fbm` mottling + fine surface pores/speckles/grain + `heightToNormalTex(...)` bump relief + rough/matte `roughnessMap`.
3. **Bevel Box Edges (`buildBeveledBox`):** Avoid razor-sharp `BoxGeometry` edges on prominent props (clamps, casings, bricks, tiles, spacers); bevels catch soft key-light highlights like real Blender bevel modifiers.
4. **Always Cap Open Tubes:** Cap ends of `TubeGeometry` / open `CylinderGeometry` pipes, shafts, wires, and rods with textured matte discs oriented to the endpoint tangent (`buildStirrup135`, `buildSculptedRebarCylinder`).
5. **Cross-Domain Starter Kit Mapping:**

| Universal Part Needed | Reuse from `RevaPBR` / `RevaCanvas` | Adapt for Any Domain Via... |
|---|---|---|
| Translucent X-Ray Casing / Tank | `createConcreteCoverGlassMaterial({ color, rimColor, centerAlpha, edgeAlpha })` | Water pipes, battery cells, cylinders, lungs, roof cutaways |
| Machined Metal Rods / Pipes / Shafts | `createStirrupSteelMaterial({ rgb, roughness })` | Pistons, copper/steel piping, rails, axles, heat pipes |
| Wooden Frames / Enclosures / Crates | `createTimberFormworkMaterial({ tone, rgb })` | Cabinetry, furniture, acoustic boxes, bridges, trays |
| Beveled Blocks / Tiles / Housings | `buildBeveledBox(w, h, d, bevel, mat)` | Enclosures, ceramic tiles, solar frames, battery packs |
| Angular Broken Shards / Rocks / Debris | `buildFracturedChunk(radius, mat, seed)` | Rock strata, spall debris, crystals, soil clods |
| Earth / Terrain Cutaway Base | `buildCozyGrassDiorama(...)` + `createSoilCutawayMaterial()` | Yard, geological layers, agriculture, foundations |
| Human Scale Reference | `buildWorkerFigure({ scale })` | Architecture, ergonomics, vehicles, safety explainers |

---

## 5. Typography, Safe Zones & Minimalist HUD Rules (`1080x1920` Vertical 9:16)

Keep 80%+ of the vertical canvas unobstructed by UI:
- **Top Floating Chapter Pill:** `#rc-header` (`top: 124px`), pure white pill with soft drop shadow, blue numbered circle (`#1e88e5`), bold dark charcoal title (`setHeader(1, "Rule Title")`).
- **Bottom Subtitle Pill:** `#rc-caption` (`bottom: 190px`), `rgba(24, 28, 34, 0.92)` dark pill, bold white sans text, short 3–6 word speech phrase synced to voiceover (`setCaption(...)`).
- **1–3 Short Labels Max per Beat:** Project tags and calipers straight from 3D world coordinates (`hud.tag`, `hud.caliper`, `hud.numBadge`) inside safe margins (`x ∈ [32, 1048]`, `y ∈ [220, 1650]`).
- **Semantic Color Codes:**
  - `green` (`#12985d`): passing specification, safe zone, exact dimension caliper
  - `blue` (`#248bf0`): active component callout, rule highlight, chapter index
  - `red` (`#e13b33`): failing spec, defect, overload, "wrong way" warning
  - `gray` (`#96989c`): geometric variable (`d`, `r`, `L`, angle)

---

## 6. Audio, Pacing & Two-Stage Bench Workflow

- **Audio & SFX Balance:** Mix narration around **`-14 LUFS`** (`peak < -0.6 dBTP`) accented with clean, subtle procedural SFX: soft *pop* on HUD badges, warm *swell* on camera zooms, crisp *click/crack* on mechanical snap or failure beats.
- **Stage 1 (Clay/Topology First):** Prototype mechanism & proportions using `RevaCAD` clay materials (`threejs_schematic.js`), run `reva_code.py run-bench`, and pass every anatomical `must_show` checkpoint via `reva_code.py audit`.
- **Stage 2 (Cozy PBR + Canvas Polish):** Switch scene boot to `RevaCanvas.boot()`, apply `RevaPBR` materials + `markNoInk()` on fine ridges, render keyframes, and verify full + zoomed parity (`reva_code.py compare --crop ...`).

---

## 7. Minimal Topic-Agnostic Starter Boilerplate

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <script src="./three.min.js"></script>
  <script src="./threejs_schematic.js"></script>
  <script src="./threejs_pbr_materials.js"></script>
  <script src="./threejs_canvas.js"></script>
</head>
<body>
  <script>
    const ctx = RevaCanvas.boot({ W: 1080, H: 1920 });
    const { scene, camera, hud, buildCozyGrassDiorama, markNoInk } = ctx;

    // 1. Diorama ground (or replace with topic workbench plinth)
    scene.add(buildCozyGrassDiorama(1.2, [], { size: 16, tuftCount: 180 }));

    // 2. Hero subject (machined shaft + Fresnel translucent housing)
    const pipeMat = RevaPBR.createStirrupSteelMaterial({ rgb: [132, 146, 158] });
    const pipe = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.22, 3.2, 32), pipeMat);
    pipe.position.y = 1.6;
    pipe.castShadow = true;
    scene.add(pipe);

    const shellMat = RevaPBR.createConcreteCoverGlassMaterial({ color: 0x6fb4e2 });
    const shell = new THREE.Mesh(new THREE.BoxGeometry(1.4, 3.0, 1.4), shellMat);
    shell.position.y = 1.5;
    shell.renderOrder = 4;
    markNoInk(shell, true);
    scene.add(shell);

    // 3. Per-timestamp animation & 3D-tracked HUD
    window.renderAt = function (t) {
      hud.clear();
      ctx.setHeader(1, "How Pressure Valves Seal");
      ctx.setCaption("Spring force holds the piston shut.");
      camera.position.set(3.2 * Math.cos(t * 0.2), 3.6, 4.4);
      camera.lookAt(0, 1.5, 0);
      camera.updateMatrixWorld();

      hud.tag(RevaCAD.V(0.22, 2.1, 0.0), "intake shaft", "blue", 130, -60, true);
      hud.caliper(RevaCAD.V(-0.7, 0.2, 0.7), RevaCAD.V(0.7, 0.2, 0.7), "clear W", "green", "#12985d", 0, 20, 0, 26);
      ctx.render();
    };
    window.renderAt(ctx.tInit);
    document.body.dataset.ready = "1";
  </script>
</body>
</html>
```
