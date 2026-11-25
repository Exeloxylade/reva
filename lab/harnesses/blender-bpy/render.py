#!/usr/bin/env python3
"""Headless Blender test-bench starter (run with: blender -b -P render.py)."""
import json
import os

try:
    import bpy
except ImportError as exc:
    raise SystemExit("Run this script inside Blender: blender -b -P render.py") from exc


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(here, "bench.json")
    cfg = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, encoding="utf-8") as fp:
            cfg = json.load(fp)

    w = int(cfg.get("width") or 1080)
    h = int(cfg.get("height") or 1920)
    fps = int(round(float(cfg.get("fps") or 30)))
    dur = float(cfg.get("duration_sec") or 3.0)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.fps = fps
    scene.frame_start = 1
    scene.frame_end = max(2, int(round(dur * fps)))
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.filepath = os.path.join(here, "out.mp4")

    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
    bpy.ops.object.light_add(type="AREA", location=(4, -4, 6))
    bpy.ops.object.camera_add(location=(5, -5, 3.5), rotation=(1.1, 0, 0.785))
    scene.camera = bpy.context.active_object
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
