# HyperFrames 2D Starter Harness

1. Inspect `bench.json` for measured resolution, fps, palette, and reference time range.
2. Edit `index.html` using exact pixel coordinates from `../../theirs/grid_*.png`, measured hex palette, and Google Fonts via `@font-face`.
3. Render with HyperFrames (`npx hyperframes render index.html --out out.mp4`) or your Branch 1 `vm` pipeline.
4. Compare side-by-side:
   `python reva_code.py compare <study> <technique> --tool hyperframes-2d --mine <out.mp4> --mine-at ...`
