# Three.js / WebGL Continuous 3D Starter Harness

1. Inspect `bench.json` for target resolution (`1080x1920` for Shorts or `1920x1080` for wide), fps, and measured hex palette.
2. Implement the apparatus / continuous camera rig in `scene.html` (or using `gem-3d-world` `W3.camPath` / `W3.boot({ssaa:2})`).
3. Render `out.mp4` and compare side-by-side:
   `python reva_code.py compare <study> <technique> --tool threejs-webgl --mine <out.mp4> --mine-at ...`
