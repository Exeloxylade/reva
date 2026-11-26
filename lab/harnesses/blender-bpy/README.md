# Headless Blender CLI Starter Harness (Schematic Clay-First)

1. Auto-detects `blender.exe` (`PATH`, `C:\Program Files\Blender Foundation\...`, or `%LOCALAPPDATA%\Programs\Blender*`) and adapts automatically to Blender 4.x/5.x `BLENDER_EEVEE`.
2. Edit `render.py` (`_build_schematic_scene`) using clay `Principled BSDF` materials and `bench.json` dimensions.
3. Run a 1-command schematic render + full & zoomed comparison:
   ```cmd
   python reva_code.py run-bench <study> <technique> --tool blender-bpy --at 0,1,2 --ref-at <t1,t2,t3>
   ```
4. Render full animated MP4 when ready: `python render_bench.py --mp4`.
