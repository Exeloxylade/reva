# HyperFrames 2D Starter Harness (Schematic-First)

1. Inspect `bench.json` for `width`, `height`, `fps`, `transcript_excerpt`, and `anatomy_specs`.
2. Edit `index.html` using `window.__setTime(t)` for deterministic frame rendering (focus on layout, causal callouts, and measured proportions).
3. Fast 1-command compare + zoom:
   ```cmd
   python reva_code.py run-bench <study> <technique> --tool hyperframes-2d --at 0,1,2 --ref-at <t1,t2,t3>
   ```
   Or manually render stills (`python render_bench.py --at 0,1,2`) or full MP4 (`python render_bench.py --mp4`).
