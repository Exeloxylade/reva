# Manim Mathematical & Geometric Bench Harness (Schematic-First)

1. Edit `scene.py` (`BenchScene(Scene)`) using Pango `Text`, geometric diagrams, vectors, and dimension labels (`REVA_BENCH_T` selects the `--at` timestamp).
2. Run a 1-command schematic render + full & zoomed comparison:
   ```cmd
   python reva_code.py run-bench <study> <technique> --tool manim --at 0,1,2 --ref-at <t1,t2,t3>
   ```
3. Render full animated MP4 when ready: `python render_bench.py --mp4`.
