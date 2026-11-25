# Headless Blender CLI Starter Harness

1. Requires Blender installed (`blender -b -P render.py`).
2. `render.py` reads `bench.json` for resolution, fps, and duration, builds a minimal lit scene, and outputs `out.mp4`.
3. Compare side-by-side against Three.js or other candidate engines:
   `python reva_code.py compare <study> <technique> --tool blender-bpy --mine out.mp4 --mine-at ...`
