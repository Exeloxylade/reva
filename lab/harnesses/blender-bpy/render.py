#!/usr/bin/env python3
"""Headless Blender schematic still / MP4 renderer (invoked via render_bench.py or `blender -b -P render.py -- ...`)."""
import argparse
import json
import math
import os
import sys

try:
    import bpy
except ImportError as exc:
    raise SystemExit("Run this script inside Blender: blender -b -P render.py") from exc


def _parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", default="0,1,2")
    ap.add_argument("--out-prefix", default="out")
    ap.add_argument("--mp4", action="store_true")
    return ap.parse_args(argv)


def _pick_engine(scene):
    avail = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    for cand in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH", "CYCLES"):
        if cand in avail:
            scene.render.engine = cand
            return cand
    return scene.render.engine


def _clay_mat(name, rgba):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.85
    return mat


def _build_schematic_scene(here, cfg):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    _pick_engine(scene)
    w = int(cfg.get("width") or 1080)
    h = int(cfg.get("height") or 1920)
    scene.render.resolution_x = w
    scene.render.resolution_y = h
    scene.render.resolution_percentage = 100

    world = bpy.data.worlds.new("REVAWorld")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.933, 0.953, 0.969, 1.0)
        bg.inputs[1].default_value = 1.0

    # Role-coded clay geometry: floor slab + core prism + hero schematic block
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.1))
    floor = bpy.context.active_object
    floor.scale = (3.4, 3.4, 0.2)
    floor.data.materials.append(_clay_mat("ClayFloor", (0.85, 0.89, 0.92, 1.0)))

    bpy.ops.mesh.primitive_cube_add(size=1.1, location=(0, 0, 0.75))
    hero = bpy.context.active_object
    hero.data.materials.append(_clay_mat("ClayHero", (0.88, 0.48, 0.08, 1.0)))

    bpy.ops.object.light_add(type="SUN", location=(5, -5, 8), rotation=(0.6, 0.2, 0.8))
    bpy.context.active_object.data.energy = 2.5

    bpy.ops.object.camera_add(location=(4.2, -4.4, 3.6))
    cam = bpy.context.active_object
    direction = (0.0 - cam.location.x, 0.0 - cam.location.y, 0.75 - cam.location.z)
    rot_z = math.atan2(direction[1], direction[0]) - math.pi / 2.0
    dist_xy = math.hypot(direction[0], direction[1])
    rot_x = math.atan2(dist_xy, -direction[2])
    cam.rotation_euler = (rot_x, 0.0, rot_z)
    scene.camera = cam
    return scene, hero


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(here, "bench.json")
    cfg = json.load(open(cfg_path, encoding="utf-8-sig")) if os.path.exists(cfg_path) else {}
    args = _parse_args()
    scene, hero = _build_schematic_scene(here, cfg)

    if args.mp4:
        fps = int(round(float(cfg.get("fps") or 30)))
        dur = float(cfg.get("duration_sec") or 3.0)
        scene.render.fps = fps
        scene.frame_start = 1
        scene.frame_end = max(2, int(round(dur * fps)))
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.filepath = os.path.join(here, "out.mp4")
        bpy.ops.render.render(animation=True)
        return

    scene.render.image_settings.file_format = "PNG"
    times = [x.strip() for x in args.at.split(",") if x.strip()]
    for idx, tok in enumerate(times):
        t_val = float(tok)
        hero.rotation_euler = (0.0, 0.0, t_val * 0.5)
        out_png = os.path.join(here, f"{args.out_prefix}_{idx}.png")
        scene.render.filepath = out_png
        bpy.ops.render.render(write_still=True)
        print(f"rendered t={tok} -> {out_png}")


if __name__ == "__main__":
    main()
