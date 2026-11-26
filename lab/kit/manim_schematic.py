"""manim_schematic.py - Shared REVA Clay/CAD schematic helpers for Manim benches."""
from manim import (
    BLUE_D, GREEN_D, ORANGE, Arrow, Line, Rectangle, RoundedRectangle, Text,
    VGroup, DOWN, LEFT, RIGHT, UP,
)

CLAY_PALETTE = {
    "bg": "#eef3f7",
    "ink": "#0f172a",
    "muted": "#334155",
    "cover_stroke": "#475569",
    "cover_fill": "#cbd5e1",
    "core_stroke": GREEN_D,
    "core_fill": "#6ee7b7",
    "hoop_ok": ORANGE,
    "accent_blue": BLUE_D,
}


def make_header(title_text):
    """Build crisp top schematic header badge."""
    return Text(str(title_text), font_size=38, color=CLAY_PALETTE["ink"], weight="BOLD").to_edge(UP, buff=0.65)


def make_cutaway_zone(outer_w=5.4, outer_h=4.4, inner_w=3.8, inner_h=2.9, outer_lbl="Unconfined Zone", inner_lbl="Confined Core"):
    """Build nested Clay/CAD zone diagram separating outer layer vs confined core."""
    outer = RoundedRectangle(
        width=outer_w, height=outer_h, corner_radius=0.18,
        color=CLAY_PALETTE["cover_stroke"], fill_color=CLAY_PALETTE["cover_fill"], fill_opacity=0.45, stroke_width=5,
    )
    inner = Rectangle(
        width=inner_w, height=inner_h,
        color=CLAY_PALETTE["core_stroke"], fill_color=CLAY_PALETTE["core_fill"], fill_opacity=0.55, stroke_width=5,
    )
    hoop = RoundedRectangle(
        width=inner_w + 0.22, height=inner_h + 0.22, corner_radius=0.2,
        color=CLAY_PALETTE["hoop_ok"], stroke_width=10,
    )
    lbl_in = Text(str(inner_lbl), font_size=26, color="#0f766e", weight="BOLD").move_to(inner.get_center())
    lbl_out = Text(str(outer_lbl), font_size=24, color=CLAY_PALETTE["muted"]).next_to(outer, DOWN, buff=0.35)
    return VGroup(outer, inner, hoop, lbl_in, lbl_out)


def make_caliper(p1, p2, label, color=BLUE_D):
    """Build clean CAD dimension line with end ticks and label badge."""
    bar = Line(p1, p2, color=color, stroke_width=5)
    txt = Text(str(label), font_size=24, color=color, weight="BOLD").next_to(bar, RIGHT, buff=0.2)
    return VGroup(bar, txt)
