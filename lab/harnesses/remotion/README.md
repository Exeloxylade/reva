# Remotion React Bench Harness (Schematic-First)

1. Edit `BenchComp.jsx` and `index.jsx` (driven by `useCurrentFrame()` and `bench.json` props).
2. Run a 1-command schematic render + full & zoomed comparison:
   ```cmd
   python reva_code.py run-bench <study> <technique> --tool remotion --at 0,1,2 --ref-at <t1,t2,t3>
   ```
3. Render full animated MP4 when ready: `python render_bench.py --mp4`.
