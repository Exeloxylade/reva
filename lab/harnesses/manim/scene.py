"""REVA Manim Schematic Starter Scene importing shared lab/kit/manim_schematic.py."""
import json
import os
from manim import Scene, BLUE_D, Arrow, UP, VGroup

from manim_schematic import CLAY_PALETTE, make_cutaway_zone, make_header


class BenchScene(Scene):
    """Minimal clay/CAD schematic diagram starter without LaTeX dependencies."""

    def construct(self):
        here = os.path.dirname(os.path.abspath(__file__))
        cfg_path = os.path.join(here, "bench.json")
        cfg = json.load(open(cfg_path, encoding="utf-8-sig")) if os.path.exists(cfg_path) else {}
        title_txt = cfg.get("technique") or "manim-schematic"

        self.camera.background_color = CLAY_PALETTE["bg"]
        header = make_header(title_txt)
        zone = make_cutaway_zone(outer_lbl="Unconfined Cover", inner_lbl="Confined Core")
        arr = Arrow(start=zone.get_top() + UP * 0.45, end=zone[2].get_top(), color=BLUE_D, stroke_width=6)

        diagram = VGroup(zone, arr)
        t_eval = float(os.environ.get("REVA_BENCH_T", "0") or 0)
        diagram.rotate(t_eval * 0.12)

        self.add(header, diagram)
        self.wait(0.2)
