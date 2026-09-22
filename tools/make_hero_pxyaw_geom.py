#!/usr/bin/env python3
"""Stage-1 X-and-yaw panel, rebuilt as the four-step geometric story.

  1. one reading  -> the mount must lie on a circle whose centre sits on the
     rear-axle line (the instantaneous centre of rotation); heading included,
     because the angle between the sensor axis and the measured velocity is
     the same at every candidate,
  2. walking along that circle trades lever arm against yaw, so in the
     (psi, p_x) plane one turn draws one line,
  3. turns of different radius and sign give lines that cross in one small
     region -- that crossing is the mount,
  4. the lines do not meet exactly, so the estimate is the point with the
     smallest weighted squared gap to all of them.

Left panel: top view of the vehicle, the rear-axle line, the circles.
Right panel: the (psi, p_x) plane with the real constraint lines of one A2D2
drive (11 gated turns, FRONT_CENTER), and the least-squares point.

Numbers in the right panel are real: they come from
  experiments/pxyaw_identifiability/pxyaw_lines.json
Left-panel angles and turn radii are compressed for legibility and are
labelled as such.

Construction rules shared with make_hero_pxyaw.py / make_hero_yaw.py:
  * no JavaScript -- SMIL only
  * pure string building, stock Python only
  * refuses to write if a self-test, a text-number check or a dangling
    reference check fails

Writes:
  hero_pxyaw_geom.svg          22 s loop
  hero_pxyaw_geom_static.svg   step-4 state, for prefers-reduced-motion
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "hero"
LINES_JSON = ROOT / "experiments" / "pxyaw_identifiability" / "pxyaw_lines.json"

# ---------------------------------------------------------------- palette
W, H = 1600, 920
INK, MUTED, RULE, SOFT, PAPER = "#191919", "#6a6a6a", "#d8d8d8", "#f5f5f3", "#ffffff"
ACC = "#a52e29"          # the answer / the true mount
LEFTT = "#1d4ed8"        # left turn  (positive slope)
RIGHTT = "#be185d"       # right turn (negative slope)
GHOST = "#b4b4b4"        # candidates that the reading cannot rule out
SUBY = 'p<tspan font-size="72%" dy="3">y</tspan><tspan dy="-3"></tspan>'
FONT = "'Inter','Helvetica Neue',Helvetica,Arial,sans-serif"

LOOP = 22.0
ACTS = [(0.4, 5.2), (5.2, 10.6), (10.6, 16.2), (16.2, 21.8)]

# ---------------------------------------------------------------- data
_d = json.loads(LINES_JSON.read_text(encoding="utf-8"))
CORE_PSI = _d["core"]["psi_deg"]
CORE_PX = _d["core"]["px_m"]
GT_PSI, GT_PX = _d["gt"]["psi_deg"], _d["gt"]["px_m"]
SEGS = _d["segments"]
CHANNEL = _d["channel"]
NSAMP = sum(s["n"] for s in SEGS)


def line_px(seg: dict, psi_deg: float) -> float:
    """p_x that this turn allows, for a trial yaw."""
    return seg["px_at_core"] + seg["slope_meas"] * math.radians(psi_deg - CORE_PSI)


def weight(seg: dict) -> float:
    """Each turn carries its sample count and its turn rate, as the solver does."""
    return seg["n"] * math.radians(seg["om_med_dps"]) ** 2


def solve_lines(segs: list[dict]) -> tuple[float, float]:
    """Weighted least squares of the gap in p_x to every line."""
    a11 = a12 = a22 = b1 = b2 = 0.0
    for s in segs:
        w, sl, a = weight(s), s["slope_meas"], s["px_at_core"]
        a11 += w * sl * sl
        a12 += -w * sl
        a22 += w
        b1 += -w * sl * a
        b2 += w * a
    det = a11 * a22 - a12 * a12
    u = (b1 * a22 - a12 * b2) / det
    px = (a11 * b2 - b1 * a12) / det
    return CORE_PSI + math.degrees(u), px


def cost(psi_deg: float, px: float) -> float:
    return sum(weight(s) * (px - line_px(s, psi_deg)) ** 2 for s in SEGS)


PSI_HAT, PX_HAT = solve_lines(SEGS)

# three turns for step 3: two right, one left, slopes far enough apart to cross
TRIO = [next(s for s in SEGS if s["seg"] == k) for k in (10, 7, 9)]
SOLO = TRIO[0]
# the left panel's true mount is where those three agree, so the sweeps close on it
PSI_REF, PX_REF = solve_lines(TRIO)

# ---------------------------------------------------------------- left panel
LP = (56, 170, 790, 880)                 # x0 y0 x1 y1
AXLE_X = 340.0                           # rear-axle line (lateral through the axle)
AXLE_Y = 660.0                           # rear-axle centre
SEN = (455.0, 640.0)                     # the true mount
PXPR = 5.0                               # px of centre offset per (m/rad) of slope


def circle_of(seg: dict) -> tuple[float, float, float]:
    """Centre on the axle line, placed so the panel ordering matches the slopes."""
    cy = SEN[1] - PXPR * seg["slope_meas"]
    r = math.hypot(SEN[0] - AXLE_X, SEN[1] - cy)
    return AXLE_X, cy, r


def spin(pt: tuple[float, float], c: tuple[float, float], deg: float) -> tuple[float, float]:
    a = math.radians(deg)
    dx, dy = pt[0] - c[0], pt[1] - c[1]
    return c[0] + dx * math.cos(a) - dy * math.sin(a), c[1] + dx * math.sin(a) + dy * math.cos(a)


def tangent(pt: tuple[float, float], c: tuple[float, float]) -> tuple[float, float]:
    """Unit velocity at pt: perpendicular to the radius, forward at the axle."""
    dx, dy = pt[0] - c[0], pt[1] - c[1]
    n = math.hypot(dx, dy)
    s = 1.0 if c[1] < pt[1] else -1.0          # centre above -> moving right
    return s * dy / n, -s * dx / n


ALPHA = 13.0                               # sensor axis vs velocity, exaggerated
SWEEP = 22.0                               # left-panel rotation at the plot edge
DPSI3 = 0.34                               # step-3 trial-yaw half range, degrees

# ---------------------------------------------------------------- right panel
RP = (810, 170, 1544, 880)
GX0, GX1, GY0, GY1 = 900.0, 1500.0, 286.0, 782.0
PSI_LO, PSI_HI = 0.72, 1.78
PX_LO, PX_HI = 1.27, 1.97
PSI_TICKS = [0.8, 1.0, 1.2, 1.4, 1.6]
PX_TICKS = [1.3, 1.5, 1.7, 1.9]


def gx(psi: float) -> float:
    return GX0 + (psi - PSI_LO) / (PSI_HI - PSI_LO) * (GX1 - GX0)


def gy(px: float) -> float:
    return GY1 - (px - PX_LO) / (PX_HI - PX_LO) * (GY1 - GY0)


# step-4 walk of the trial point
WALK = [(1.62, 1.905), (1.46, 1.822), (1.34, 1.743), (1.262, 1.698),
        (PSI_HAT, PX_HAT), (PSI_HAT, PX_HAT)]
WALK_T = [16.6, 17.5, 18.3, 19.0, 19.7, 21.8]

# ---------------------------------------------------------------- svg helpers
def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def f(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".")


def anim(attr: str, times: list[float], values: list[str]) -> str:
    kt = []
    for t in times:
        kt.append(min(1.0, max(0.0, t / LOOP)))
    for i in range(1, len(kt)):
        kt[i] = max(kt[i], kt[i - 1])
    kt[0], kt[-1] = 0.0, 1.0
    return (f'<animate attributeName="{attr}" dur="{LOOP}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{";".join(f"{k:.5f}" for k in kt)}" '
            f'values="{";".join(values)}"/>')


def fade(on: float, off: float, ft: float = 0.35) -> str:
    t = [0.0, on - ft, on, off, off + ft, LOOP]
    return anim("opacity", t, ["0", "0", "1", "1", "0", "0"])


def txt(x: float, y: float, s: str, size: float = 16, fill: str = INK,
        anchor: str = "start", weight_: str = "400", style: str = "",
        extra: str = "") -> str:
    st = f' font-style="{style}"' if style else ""
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{FONT}" font-size="{f(size)}" '
            f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight_}"{st} {extra}>{s}</text>')


def arrow(x1: float, y1: float, x2: float, y2: float, col: str, wdt: float = 2.2,
          head: float = 9.0, extra: str = "") -> str:
    ang = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - head * math.cos(ang), y2 - head * math.sin(ang)
    p1 = (bx - head * 0.45 * math.sin(ang), by + head * 0.45 * math.cos(ang))
    p2 = (bx + head * 0.45 * math.sin(ang), by - head * 0.45 * math.cos(ang))
    return (f'<g {extra}><line x1="{f(x1)}" y1="{f(y1)}" x2="{f(bx)}" y2="{f(by)}" '
            f'stroke="{col}" stroke-width="{f(wdt)}" stroke-linecap="round"/>'
            f'<polygon points="{f(x2)},{f(y2)} {f(p1[0])},{f(p1[1])} {f(p2[0])},{f(p2[1])}" '
            f'fill="{col}"/></g>')


def panel(box: tuple[float, float, float, float]) -> str:
    x0, y0, x1, y1 = box
    return (f'<rect x="{f(x0)}" y="{f(y0)}" width="{f(x1 - x0)}" height="{f(y1 - y0)}" rx="14" '
            f'fill="{PAPER}" stroke="{RULE}" stroke-width="1.2"/>')


def note_box(x: float, y: float, w: float, lines: list[str], size: float = 15.5) -> str:
    h = 14 + len(lines) * (size + 7)
    out = [f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="9" fill="{PAPER}" '
           f'fill-opacity="0.93" stroke="{RULE}" stroke-width="1"/>']
    for i, ln in enumerate(lines):
        out.append(txt(x + 13, y + 22 + i * (size + 7), ln, size, MUTED))
    return "".join(out)


# ---------------------------------------------------------------- pieces
def car() -> str:
    bx0, bx1 = 280.0, 600.0
    by0, by1 = AXLE_Y - 58, AXLE_Y + 58
    g = [f'<rect x="{f(bx0)}" y="{f(by0)}" width="{f(bx1 - bx0)}" height="{f(by1 - by0)}" rx="26" '
         f'fill="{SOFT}" stroke="{MUTED}" stroke-width="1.6"/>',
         f'<rect x="{f(bx0 + 66)}" y="{f(by0 + 17)}" width="150" height="{f(by1 - by0 - 34)}" rx="12" '
         f'fill="none" stroke="{RULE}" stroke-width="1.3"/>']
    for ax in (AXLE_X, 560.0):
        for sy in (-1, 1):
            g.append(f'<rect x="{f(ax - 15)}" y="{f(AXLE_Y + sy * 58 - 11)}" width="30" height="22" '
                     f'rx="6" fill="{MUTED}"/>')
    g.append(f'<line x1="{f(AXLE_X)}" y1="{f(AXLE_Y - 58)}" x2="{f(AXLE_X)}" y2="{f(AXLE_Y + 58)}" '
             f'stroke="{MUTED}" stroke-width="2.4"/>')
    g.append(f'<circle cx="{f(AXLE_X)}" cy="{f(AXLE_Y)}" r="5" fill="{INK}"/>')
    g.append(arrow(612, AXLE_Y, 664, AXLE_Y, MUTED, 2.0, 9))
    g.append(txt(668, AXLE_Y + 5, "forward", 14, MUTED))
    return "".join(g)


def axle_line() -> str:
    return (f'<line x1="{f(AXLE_X)}" y1="252" x2="{f(AXLE_X)}" y2="868" stroke="{MUTED}" '
            f'stroke-width="1.5" stroke-dasharray="9 7"/>'
            f'<rect x="{f(AXLE_X + 6)}" y="254" width="104" height="20" rx="4" fill="{PAPER}" '
            f'fill-opacity="0.9"/>'
            + txt(AXLE_X + 12, 268, "rear-axle line", 14, MUTED))


def glyph(pt: tuple[float, float], c: tuple[float, float], col: str, faint: bool) -> str:
    """Candidate mount: its own axis plus the velocity it would read."""
    tx, ty = tangent(pt, c)
    ha = math.atan2(ty, tx) - math.radians(ALPHA)
    hx, hy = math.cos(ha), math.sin(ha)
    op = ' opacity="0.5"' if faint else ""
    g = [f'<g{op}>']
    g.append(f'<rect x="{f(pt[0] - 6)}" y="{f(pt[1] - 6)}" width="12" height="12" rx="2.5" '
             f'transform="rotate({f(math.degrees(ha))} {f(pt[0])} {f(pt[1])})" '
             f'fill="{PAPER}" stroke="{col}" stroke-width="2"/>')
    g.append(arrow(pt[0], pt[1], pt[0] + hx * 31, pt[1] + hy * 31, col, 1.7, 6.5))
    g.append(arrow(pt[0], pt[1], pt[0] + tx * 45, pt[1] + ty * 45, ACC, 1.7, 6.5))
    g.append("</g>")
    return "".join(g)


def circle_art(seg: dict, col: str, dash: bool = False) -> str:
    cx, cy, r = circle_of(seg)
    da = ' stroke-dasharray="7 6"' if dash else ""
    return (f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="none" stroke="{col}" '
            f'stroke-width="1.8" stroke-opacity="0.75"{da}/>')


def icr_mark(seg: dict, col: str, label: str) -> str:
    cx, cy, r = circle_of(seg)
    g = [f'<circle cx="{f(cx)}" cy="{f(cy)}" r="5.5" fill="{col}"/>',
         f'<line x1="{f(cx)}" y1="{f(cy)}" x2="{f(SEN[0])}" y2="{f(SEN[1])}" stroke="{col}" '
         f'stroke-width="1.3" stroke-dasharray="5 5"/>']
    mx = cx + 0.36 * (SEN[0] - cx)
    my = cy + 0.36 * (SEN[1] - cy)
    g.append(txt(mx - 12, my + 4, label, 15, col, "end", weight_="600"))
    return "".join(g)


# ---------------------------------------------------------------- grid
def grid() -> str:
    g = [f'<rect x="{f(GX0)}" y="{f(GY0)}" width="{f(GX1 - GX0)}" height="{f(GY1 - GY0)}" '
         f'fill="{PAPER}" stroke="{RULE}" stroke-width="1.2"/>']
    for t in PSI_TICKS:
        x = gx(t)
        g.append(f'<line x1="{f(x)}" y1="{f(GY0)}" x2="{f(x)}" y2="{f(GY1)}" stroke="{RULE}" '
                 f'stroke-width="1" stroke-dasharray="3 6"/>')
        g.append(txt(x, GY1 + 24, f"{t:.1f}", 14, MUTED, "middle"))
    for t in PX_TICKS:
        y = gy(t)
        g.append(f'<line x1="{f(GX0)}" y1="{f(y)}" x2="{f(GX1)}" y2="{f(y)}" stroke="{RULE}" '
                 f'stroke-width="1" stroke-dasharray="3 6"/>')
        g.append(txt(GX0 - 12, y + 5, f"{t:.1f}", 14, MUTED, "end"))
    g.append(txt((GX0 + GX1) / 2, GY1 + 52, "mounting yaw &#968; [deg]", 16, INK, "middle"))
    g.append(f'<g transform="translate({f(GX0 - 58)} {f((GY0 + GY1) / 2)}) rotate(-90)">'
             + txt(0, 0, "lever arm p&#8339; [m]", 16, INK, "middle") + "</g>")
    return "".join(g)


def line_art(seg: dict, col: str, wdt: float, op: float, ident: str = "") -> str:
    x1, y1 = gx(PSI_LO), gy(line_px(seg, PSI_LO))
    x2, y2 = gx(PSI_HI), gy(line_px(seg, PSI_HI))
    i = f' id="{ident}"' if ident else ""
    return (f'<line{i} x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{col}" '
            f'stroke-width="{f(wdt)}" stroke-opacity="{op}" stroke-linecap="round"/>')


# ---------------------------------------------------------------- build
def build(animated: bool) -> str:
    A1, A2, A3, A4 = ACTS
    o: list[str] = []
    o.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
             f'height="{H}" role="img" aria-labelledby="ttl desc">')
    o.append('<title id="ttl">X and yaw from the turn geometry</title>')
    o.append('<desc id="desc">Four steps. One reading puts the sensor somewhere on a circle '
             'centred on the rear-axle line, heading included. Walking along that circle trades '
             'lever arm against yaw, so each turn is one line in the yaw versus lever-arm plane. '
             'Several turns give lines that cross in one small region. The estimate is the point '
             'with the smallest weighted squared gap to all eleven lines of one A2D2 drive.</desc>')
    o.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
    o.append(f'<clipPath id="clipL"><rect x="{f(LP[0])}" y="{f(LP[1])}" '
             f'width="{f(LP[2] - LP[0])}" height="{f(LP[3] - LP[1])}" rx="14"/></clipPath>')

    # header ------------------------------------------------------------
    o.append(txt(56, 48, "Where can the sensor be? The turn geometry answers it.", 27, INK,
                 weight_="600"))
    o.append(txt(56, 76, f"A2D2 {CHANNEL} &#183; {len(SEGS)} gated turns &#183; "
                 f"{NSAMP} samples &#183; one sensor at a time, no cross-sensor matching",
                 16, MUTED))

    chips = [
        ("1", "One reading", "The mount lies on a circle centred on the rear-axle",
         "line &#8212; position and heading together."),
        ("2", "Circle &#8594; line", "Walking the circle trades lever arm against yaw:",
         "one turn draws one line in the (&#968;,&#8201;p&#8339;) plane."),
        ("3", "More turns", "Turns of different radius and sign give lines",
         "that cross in one small region."),
        ("4", "Least squares", "The lines do not meet exactly; the estimate is the",
         "point of smallest weighted squared gap to all of them."),
    ]
    cw, cgap = 363.0, 12.0
    for i, (n, head, l1, l2) in enumerate(chips):
        x = 56 + i * (cw + cgap)
        on = animated
        live = f'<g>{fade(*ACTS[i])}' if on else ("<g>" if i == 3 else '<g opacity="0">')
        o.append(f'<g><rect x="{f(x)}" y="96" width="{f(cw)}" height="66" rx="10" fill="{SOFT}" '
                 f'stroke="{RULE}" stroke-width="1"/></g>')
        o.append(live)
        o.append(f'<rect x="{f(x)}" y="96" width="{f(cw)}" height="66" rx="10" fill="{PAPER}" '
                 f'stroke="{ACC}" stroke-width="1.8"/>')
        o.append("</g>")
        o.append(f'<circle cx="{f(x + 22)}" cy="118" r="11" fill="{INK}"/>')
        o.append(txt(x + 22, 123, n, 14, PAPER, "middle", "700"))
        o.append(txt(x + 41, 123, head, 15.5, INK, weight_="600"))
        o.append(txt(x + 14, 143, l1, 13.5, MUTED))
        o.append(txt(x + 14, 158, l2, 13.5, MUTED))

    # ---------------------------------------------------------------- left
    o.append(panel(LP))
    o.append('<g clip-path="url(#clipL)">')
    o.append(axle_line())
    o.append(car())

    solo_c = circle_of(SOLO)[0], circle_of(SOLO)[1]

    # act 1+2: the single circle and its candidates
    g12 = [circle_art(SOLO, LEFTT), icr_mark(SOLO, LEFTT, "R = |&#7805;| / &#969;")]
    for d in (-48.0, -24.0, 24.0, 48.0):
        g12.append(glyph(spin(SEN, solo_c, d), solo_c, GHOST, True))
    g12.append(glyph(SEN, solo_c, INK, False))
    g12.append(f'<circle cx="{f(SEN[0])}" cy="{f(SEN[1])}" r="9" fill="none" stroke="{ACC}" '
               f'stroke-width="2"/>')
    o.append('<g>' + (fade(A1[0], A2[1]) if animated else '') + "".join(g12) + "</g>")
    o.append('<g>' + (fade(A1[0], A2[1]) if animated else '')
             + txt(circle_of(SOLO)[0] + 12, circle_of(SOLO)[1] - 12, "ICR", 15, LEFTT,
                   weight_="600") + "</g>")

    # act 2: the walker
    if animated:
        ts, xs, ys = [], [], []
        knots = 19
        for i in range(knots):
            u = -1.0 + 2.0 * i / (knots - 1)
            p = spin(SEN, solo_c, -u * SWEEP)
            ts.append(5.9 + 2.5 * i / (knots - 1))
            xs.append(f(p[0]))
            ys.append(f(p[1]))
        ts = [0.0, 5.7] + ts + [9.0, LOOP]
        xs = [xs[0], xs[0]] + xs + [f(SEN[0]), f(SEN[0])]
        ys = [ys[0], ys[0]] + ys + [f(SEN[1]), f(SEN[1])]
        o.append('<g>' + fade(A2[0] + 0.3, A2[1])
                 + f'<circle r="11" fill="none" stroke="{ACC}" stroke-width="3">'
                 + anim("cx", ts, xs) + anim("cy", ts, ys) + "</circle></g>")

    # act 3: three circles, three candidates driven by one trial yaw
    g3 = [circle_art(s, c, dash=(i > 0)) for i, (s, c) in
          enumerate(zip(TRIO, (LEFTT, RIGHTT, RIGHTT)))]
    o.append('<g>' + (fade(*A3) if animated else '') + "".join(g3) + "</g>")
    if animated:
        for s, col in zip(TRIO, (LEFTT, RIGHTT, RIGHTT)):
            c = circle_of(s)[0], circle_of(s)[1]
            ts, xs, ys = [], [], []
            knots = 17
            for i in range(knots):
                u = math.sin(2 * math.pi * i / (knots - 1))
                dpsi = u * DPSI3
                p = spin(SEN, c, -dpsi / DPSI3 * SWEEP)
                ts.append(11.1 + 3.4 * i / (knots - 1))
                xs.append(f(p[0]))
                ys.append(f(p[1]))
            ts = [0.0, 10.9] + ts + [15.9, LOOP]
            xs = [xs[0], xs[0]] + xs + [f(SEN[0]), f(SEN[0])]
            ys = [ys[0], ys[0]] + ys + [f(SEN[1]), f(SEN[1])]
            o.append('<g>' + fade(A3[0] + 0.3, A3[1])
                     + f'<circle r="8" fill="{col}" fill-opacity="0.85">'
                     + anim("cx", ts, xs) + anim("cy", ts, ys) + "</circle></g>")
    # act 4 (and static): the settled mount
    o.append('<g>' + (fade(*A4) if animated else '')
             + "".join(circle_art(s, c, dash=(i > 0)) for i, (s, c) in
                       enumerate(zip(TRIO, (LEFTT, RIGHTT, RIGHTT))))
             + glyph(SEN, solo_c, INK, False)
             + f'<circle cx="{f(SEN[0])}" cy="{f(SEN[1])}" r="11" fill="none" stroke="{ACC}" '
               f'stroke-width="2.6"/>' + "</g>")
    o.append("</g>")   # clip
    o.append(f'<rect x="{f(LP[0] + 8)}" y="{f(LP[1] + 6)}" width="470" height="60" rx="8" '
             f'fill="{PAPER}" fill-opacity="0.92"/>')
    o.append(txt(LP[0] + 20, LP[1] + 32, "On the vehicle (top view)", 17, INK, weight_="600"))
    o.append(txt(LP[0] + 20, LP[1] + 54, "turn radii and angles compressed for legibility",
                 13.5, MUTED, style="italic"))

    lnotes = {
        0: ["Radius is fixed by the reading: R = |&#7805;| / &#969;; the centre is",
            "the instantaneous centre of rotation, on the rear-axle line.",
            "Every candidate reads the same velocity in its own frame,",
            "so heading turns with position &#8212; one reading pins neither."],
        1: ["Walk along the circle: the lever arm p&#8339; and the yaw &#968;",
            "move together, one against the other.",
            "That trade-off is the line drawn on the right."],
        2: ["Three turns, three circles, all through the true mount.",
            "Pick a trial yaw and each turn names its own p&#8339;;",
            "they agree at one yaw only."],
        3: ["Height along the axle line is still open: it depends on the",
            "body speed, which this stage never uses. " + SUBY + " is settled later."],
    }
    for i, lines in lnotes.items():
        g = note_box(LP[0] + 20, LP[3] - 22 - (14 + len(lines) * 22.5), 528, lines)
        if animated:
            o.append("<g>" + fade(*ACTS[i]) + g + "</g>")
        elif i == 3:
            o.append("<g>" + g + "</g>")

    # ---------------------------------------------------------------- right
    o.append(panel(RP))
    o.append(txt(RP[0] + 20, RP[1] + 32, "In the (&#968;,&#8201;p&#8339;) plane &#8212; real turns",
                 17, INK, weight_="600"))
    o.append(txt(RP[0] + 20, RP[1] + 54,
                 "each line is one gated turn of the drive; axes are real units",
                 13.5, MUTED, style="italic"))
    o.append(grid())

    # act 1: empty plane
    if animated:
        o.append('<g>' + fade(*A1)
                 + txt((GX0 + GX1) / 2, (GY0 + GY1) / 2, "waiting for the first turn",
                       17, GHOST, "middle") + "</g>")

    # act 2: the first line, revealed as the walker moves
    x1, y1 = gx(PSI_LO), gy(line_px(SOLO, PSI_LO))
    x2, y2 = gx(PSI_HI), gy(line_px(SOLO, PSI_HI))
    llen = math.hypot(x2 - x1, y2 - y1)
    if animated:
        o.append('<g>' + fade(A2[0] + 0.2, A2[1])
                 + f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{LEFTT}" '
                   f'stroke-width="3" stroke-linecap="round" stroke-dasharray="{f(llen)} {f(llen)}">'
                 + anim("stroke-dashoffset", [0.0, 5.7, 8.4, LOOP],
                        [f(llen), f(llen), "0", "0"]) + "</line></g>")
        ts, xs, ys = [], [], []
        knots = 19
        for i in range(knots):
            u = -1.0 + 2.0 * i / (knots - 1)
            psi = PSI_REF + u * (PSI_HI - PSI_LO) * 0.42
            ts.append(5.9 + 2.5 * i / (knots - 1))
            xs.append(f(gx(psi)))
            ys.append(f(gy(line_px(SOLO, psi))))
        ts = [0.0, 5.7] + ts + [9.0, LOOP]
        xs = [xs[0], xs[0]] + xs + [f(gx(PSI_REF)), f(gx(PSI_REF))]
        ys = [ys[0], ys[0]] + ys + [f(gy(line_px(SOLO, PSI_REF))), f(gy(line_px(SOLO, PSI_REF)))]
        o.append('<g>' + fade(A2[0] + 0.3, A2[1])
                 + f'<circle r="9" fill="{ACC}">' + anim("cx", ts, xs) + anim("cy", ts, ys)
                 + "</circle></g>")
        o.append('<g>' + fade(A2[0] + 0.6, A2[1])
                 + txt(GX0, GY0 - 18, "one turn = one line", 16, LEFTT, weight_="600") + "</g>")

    # act 3: three lines + trial-yaw slice
    g3l = [line_art(s, c, 3.0, 0.95) for s, c in zip(TRIO, (LEFTT, RIGHTT, RIGHTT))]
    o.append('<g>' + (fade(*A3) if animated else '') + "".join(g3l) + "</g>")
    if animated:
        ts, xv = [], []
        knots = 17
        for i in range(knots):
            u = math.sin(2 * math.pi * i / (knots - 1))
            ts.append(11.1 + 3.4 * i / (knots - 1))
            xv.append(f(gx(PSI_REF + u * DPSI3)))
        ts = [0.0, 10.9] + ts + [15.9, LOOP]
        xv = [xv[0], xv[0]] + xv + [f(gx(PSI_REF)), f(gx(PSI_REF))]
        o.append('<g>' + fade(A3[0] + 0.3, A3[1])
                 + f'<line y1="{f(GY0)}" y2="{f(GY1)}" stroke="{INK}" stroke-width="1.6" '
                   f'stroke-dasharray="6 6">' + anim("x1", ts, xv) + anim("x2", ts, xv)
                 + "</line></g>")
        for s, col in zip(TRIO, (LEFTT, RIGHTT, RIGHTT)):
            yv = []
            for i in range(knots):
                u = math.sin(2 * math.pi * i / (knots - 1))
                yv.append(f(gy(line_px(s, PSI_REF + u * DPSI3))))
            yv = [yv[0], yv[0]] + yv + [f(gy(line_px(s, PSI_REF))), f(gy(line_px(s, PSI_REF)))]
            o.append('<g>' + fade(A3[0] + 0.3, A3[1])
                     + f'<circle r="8" fill="{col}">' + anim("cx", ts, xv) + anim("cy", ts, yv)
                     + "</circle></g>")
        o.append('<g>' + fade(A3[0] + 0.6, A3[1])
                 + txt(GX0, GY0 - 18, "three turns already box it in", 16, INK,
                       weight_="600") + "</g>")
        o.append('<g>' + fade(A3[0] + 4.1, A3[1])
                 + f'<circle cx="{f(gx(PSI_REF))}" cy="{f(gy(PX_REF))}" r="20" fill="none" '
                   f'stroke="{ACC}" stroke-width="2.2"/>' + "</g>")

    # act 4: all lines, the walk, the gaps, the answer
    g4 = []
    for s in SEGS:
        col = LEFTT if s["slope_meas"] > 0 else RIGHTT
        strong = s in TRIO
        g4.append(line_art(s, col, 2.6 if strong else 1.7, 0.9 if strong else 0.45))
    o.append('<g>' + (fade(*A4) if animated else '') + "".join(g4) + "</g>")

    if animated:
        tsw = [0.0, 16.3] + WALK_T + [LOOP]
        xs = [f(gx(WALK[0][0]))] * 2 + [f(gx(p[0])) for p in WALK] + [f(gx(WALK[-1][0]))]
        ys = [f(gy(WALK[0][1]))] * 2 + [f(gy(p[1])) for p in WALK] + [f(gy(WALK[-1][1]))]
        for s in SEGS:
            col = LEFTT if s["slope_meas"] > 0 else RIGHTT
            gy2 = [f(gy(line_px(s, WALK[0][0])))] * 2 + \
                  [f(gy(line_px(s, p[0]))) for p in WALK] + [f(gy(line_px(s, WALK[-1][0])))]
            o.append('<g>' + fade(A4[0] + 0.3, A4[1])
                     + f'<line stroke="{col}" stroke-width="2.4" stroke-opacity="0.55" '
                       f'stroke-linecap="round">'
                     + anim("x1", tsw, xs) + anim("x2", tsw, xs)
                     + anim("y1", tsw, ys) + anim("y2", tsw, gy2) + "</line></g>")
        o.append('<g>' + fade(A4[0] + 0.3, A4[1])
                 + f'<circle r="10" fill="{ACC}">' + anim("cx", tsw, xs) + anim("cy", tsw, ys)
                 + "</circle></g>")
        c0 = cost(*WALK[0])
        bw = [f(210 * math.sqrt(max(cost(*p), 0.0) / c0)) for p in WALK]
        bw = [bw[0], bw[0]] + bw + [bw[-1]]
        o.append('<g>' + fade(A4[0] + 0.3, A4[1])
                 + txt(GX0, GY0 - 18, "&#931; w &#183; gap&#178;", 16, INK, weight_="600")
                 + f'<rect x="{f(GX0 + 96)}" y="{f(GY0 - 31)}" height="13" rx="6" fill="{ACC}">'
                 + anim("width", tsw, bw) + "</rect>"
                 + f'<rect x="{f(GX0 + 96)}" y="{f(GY0 - 31)}" width="210" height="13" rx="6" '
                   f'fill="none" stroke="{RULE}" stroke-width="1"/>' + "</g>")
    else:
        for s in SEGS:
            col = LEFTT if s["slope_meas"] > 0 else RIGHTT
            o.append(f'<line x1="{f(gx(PSI_HAT))}" y1="{f(gy(PX_HAT))}" x2="{f(gx(PSI_HAT))}" '
                     f'y2="{f(gy(line_px(s, PSI_HAT)))}" stroke="{col}" stroke-width="2.4" '
                     f'stroke-opacity="0.55" stroke-linecap="round"/>')
        o.append(f'<circle cx="{f(gx(PSI_HAT))}" cy="{f(gy(PX_HAT))}" r="10" fill="{ACC}"/>')

    # the answer box
    rb_x, rb_y, rb_w = GX1 - 322, GY0 + 16, 306
    ans = [f'<rect x="{f(rb_x)}" y="{f(rb_y)}" width="{f(rb_w)}" height="104" rx="10" '
           f'fill="{PAPER}" fill-opacity="0.95" stroke="{ACC}" stroke-width="1.6"/>',
           txt(rb_x + 16, rb_y + 28, "least-squares point", 14.5, MUTED),
           txt(rb_x + 16, rb_y + 57,
               f"&#968; = {PSI_HAT:.3f}&#176;", 21, INK, weight_="600"),
           txt(rb_x + 158, rb_y + 57,
               f"p&#8339; = {PX_HAT:.3f} m", 21, INK, weight_="600"),
           txt(rb_x + 16, rb_y + 84,
               f"sample-level robust solve: {CORE_PSI:.3f}&#176;, {CORE_PX:.3f} m", 13.5, MUTED)]
    o.append('<g>' + (fade(A4[0] + 1.2, A4[1]) if animated else '') + "".join(ans) + "</g>")

    # legend
    ly = GY0 - 23
    leg = [f'<line x1="{f(GX1 - 224)}" y1="{f(ly)}" x2="{f(GX1 - 192)}" y2="{f(ly)}" '
           f'stroke="{LEFTT}" stroke-width="3"/>',
           txt(GX1 - 184, ly + 5, "left turn", 14, MUTED),
           f'<line x1="{f(GX1 - 110)}" y1="{f(ly)}" x2="{f(GX1 - 78)}" y2="{f(ly)}" '
           f'stroke="{RIGHTT}" stroke-width="3"/>',
           txt(GX1 - 70, ly + 5, "right turn", 14, MUTED)]
    o.append('<g>' + (fade(A2[0], A4[1]) if animated else '') + "".join(leg) + "</g>")

    o.append(txt(RP[0] + 20, RP[3] - 16,
                 "gap read along p&#8339;, weighted by turn rate and sample count",
                 13.5, MUTED, style="italic"))
    o.append("</svg>")
    return "".join(o)


# ---------------------------------------------------------------- checks
ALLOWED_NUMBERS = set()
for _t in PSI_TICKS + PX_TICKS:
    ALLOWED_NUMBERS.add(f"{_t:.1f}")
ALLOWED_NUMBERS |= {f"{PSI_HAT:.3f}", f"{PX_HAT:.3f}", f"{CORE_PSI:.3f}", f"{CORE_PX:.3f}",
                    str(len(SEGS)), str(NSAMP), "1", "2", "3", "4"}


def check(svg: str, name: str) -> list[str]:
    bad = []
    if "<script" in svg or "javascript:" in svg:
        bad.append(f"{name}: script content present")
    ids = set(re.findall(r'id="([^"]+)"', svg))
    refs = set(re.findall(r'href="#([A-Za-z0-9_-]+)"', svg)) | \
        set(re.findall(r"url\(#([A-Za-z0-9_-]+)\)", svg))
    for r in sorted(refs - ids):
        bad.append(f"{name}: dangling reference: #{r}")
    for body in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S):
        plain = re.sub(r"<[^>]*>", " ", body)
        plain = re.sub(r"&#\d+;|&[a-z]+;", " ", plain)
        for num in re.findall(r"\d+(?:\.\d+)?", plain):
            if num not in ALLOWED_NUMBERS:
                bad.append(f"{name}: unvetted number in text: {num}")
    if svg.count("<svg") != 1 or not svg.rstrip().endswith("</svg>"):
        bad.append(f"{name}: malformed document")
    # served as <img src>, so it is parsed as XML: named entities would kill it
    for ent in sorted(set(re.findall(r"&[a-zA-Z][a-zA-Z0-9]*;", svg))):
        if ent not in ("&amp;", "&lt;", "&gt;", "&quot;", "&apos;"):
            bad.append(f"{name}: named entity {ent} is not valid XML")
    try:
        ET.fromstring(svg)
    except ET.ParseError as exc:
        bad.append(f"{name}: XML parse error: {exc}")
    return bad


def self_test() -> list[str]:
    bad = []
    # 1. the demo fit must land on the pipeline solution
    if abs(PSI_HAT - CORE_PSI) > 0.05:
        bad.append(f"line fit yaw {PSI_HAT:.4f} too far from core {CORE_PSI:.4f}")
    if abs(PX_HAT - CORE_PX) > 0.015:
        bad.append(f"line fit p_x {PX_HAT:.4f} too far from core {CORE_PX:.4f}")
    # 2. it must really be the minimum of the drawn cost
    for dpsi, dpx in ((0.02, 0), (-0.02, 0), (0, 0.01), (0, -0.01)):
        if cost(PSI_HAT + dpsi, PX_HAT + dpx) <= cost(PSI_HAT, PX_HAT):
            bad.append("least-squares point is not the minimum of the drawn cost")
    # 3. the cost must fall along the walk
    cs = [cost(*p) for p in WALK]
    if any(b > a + 1e-12 for a, b in zip(cs, cs[1:])):
        bad.append(f"walk cost not monotone: {[round(c, 5) for c in cs]}")
    # 4. every candidate on a circle reads the same velocity in its own frame
    for seg in TRIO:
        c = circle_of(seg)[0], circle_of(seg)[1]
        ref = None
        for d in (-48.0, -24.0, 0.0, 24.0, 48.0):
            p = spin(SEN, c, d)
            tx, ty = tangent(p, c)
            head = math.atan2(ty, tx) - math.radians(ALPHA)
            rel = math.degrees(math.atan2(ty, tx) - head)
            if ref is None:
                ref = rel
            elif abs(rel - ref) > 1e-9:
                bad.append("heading-to-velocity angle not invariant along the circle")
    # 5. the three step-3 turns must actually agree where the sweeps close
    spread = max(line_px(t, PSI_REF) for t in TRIO) - min(line_px(t, PSI_REF) for t in TRIO)
    if spread > 0.02:
        bad.append(f"step-3 turns disagree by {spread * 1000:.1f} mm at the closing yaw")
    # 6. the panel ordering must follow the real slopes
    for seg in TRIO:
        above = circle_of(seg)[1] < SEN[1]
        if above != (seg["slope_meas"] > 0):
            bad.append(f"seg {seg['seg']}: circle side disagrees with its slope sign")
    # 7. all drawn lines stay inside the plotted window
    for s in SEGS:
        for psi in (PSI_LO, PSI_HI):
            if not (PX_LO <= line_px(s, psi) <= PX_HI):
                bad.append(f"seg {s['seg']}: line leaves the p_x window at psi={psi}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    targets = {"hero_pxyaw_geom.svg": build(True), "hero_pxyaw_geom_static.svg": build(False)}
    problems = self_test() + [p for n, s in targets.items() for p in check(s, n)]
    if problems:
        print("REFUSING TO WRITE -- checks failed:")
        for p in dict.fromkeys(problems):
            print("  " + p)
        return 1
    for name, svg in targets.items():
        path = out / name
        if path.exists() and not args.force:
            print(f"skip (exists, use --force): {path}")
            continue
        path.write_text(svg, encoding="utf-8")
        print(f"wrote {path}  {len(svg) / 1024:.1f} KB  "
              f"sha256:{hashlib.sha256(svg.encode()).hexdigest()[:16]}")
    print(f"fit: psi={PSI_HAT:.4f} deg  px={PX_HAT:.4f} m   "
          f"core: {CORE_PSI:.4f} deg {CORE_PX:.4f} m   gt: {GT_PSI:.4f} deg {GT_PX:.4f} m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
