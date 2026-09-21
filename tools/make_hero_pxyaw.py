#!/usr/bin/env python3
"""Build the S0c hero panel: an animated schematic SVG of the Stage-1 idea.

Companion to make_hero_concept.py.  That panel explains the pairwise lateral
offset dp_y; this one explains the two parameters a *single* sensor can answer
on its own -- the longitudinal lever arm p_x and the yaw offset psi.

The mechanism the figure has to carry:
  * the vehicle body point (axle centre) has no lateral velocity -- that is the
    non-holonomic constraint,
  * therefore a sensor mounted a lever arm p_x ahead of it sees a lateral
    velocity equal to omega * p_x, and nothing else,
  * forward motion makes yaw observable, while turn rate couples yaw and p_x,
  * each accepted curvature contributes a different constraint in (psi, p_x),
    and their intersection identifies both parameters.

Same construction rules as make_hero_concept.py:
  * no JavaScript -- SMIL only
  * no number carrying a unit anywhere in the text; the panel speaks in symbols
  * pure string building, stock Python only

Two files are written side by side:
  hero_pxyaw.svg          4.5 s loop
  hero_pxyaw_static.svg   the end state of that loop, for prefers-reduced-motion
"""

from __future__ import annotations

import argparse
import hashlib
import math
import re
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "hero"

# --- canvas -------------------------------------------------------------
W, H = 1600, 900

INK = "#191919"
MUTED = "#666666"
RULE = "#d8d8d8"
SOFT = "#f5f5f3"
ACC = "#a52e29"
PAPER = "#ffffff"

LOOP = 4.5            # s
T_TRAVEL = 0.44       # fraction of the loop the vehicle is moving

# --- the rigid sensor/chassis assembly, in vehicle-frame pixels ---------
# local +x is the heading, local +y is the vehicle's right-hand side.
LEVER = 150.0         # p_x, axle centre -> sensor, exaggerated
V_AXLE = 86.0         # length of the axle-point velocity arrow
V_SENS = 110.0        # length of the sensor longitudinal component
PSI_DEG = 30.0        # yaw offset drawn in the forward-motion panel, exaggerated
BRACKET_Y = 56.0      # p_x bracket sits below the body in both panels

# --- panel A: forward motion during a gentle turn ----------------------
PA_X, PB_X = 60, 810
PANEL_Y, PANEL_W, PANEL_H = 104, 730, 530
PA_ROAD_Y = 400.0
PA_START, PA_END = 150.0, 430.0
PA_R = 950.0
PA_SWEEP = 10.0
PA_ICR = (340.0, PA_ROAD_Y - PA_R)

# --- panel B: steady left turn -----------------------------------------
PB_R = 300.0          # turn radius of the axle point
PB_SWEEP = 40.0       # degrees of arc travelled
PB_ICR = (1175.0, 170.0)
PB_APEX_Y = PB_ICR[1] + PB_R          # where the vehicle ends up
LAT_LEN = V_SENS * LEVER / PB_R       # omega*p_x drawn to scale against V_SENS

# --- readout strip ------------------------------------------------------
ST_X, ST_Y, ST_W, ST_H = 60, 660, 1480, 216
PLOT_O = (790.0, 768.0)
PLOT_HALF = 230.0
PLOT_RISE = 62.0


def fmt(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def rot(lx: float, ly: float, deg: float):
    t = math.radians(deg)
    c, s = math.cos(t), math.sin(t)
    return lx * c - ly * s, lx * s + ly * c


def arc_O(icr, radius, above, phi_deg):
    """Axle-point position and heading at arc parameter phi (degrees)."""
    cx, cy = icr
    phi = math.radians(phi_deg)
    x = cx + radius * math.sin(phi)
    y = cy + radius * math.cos(phi) if above else cy - radius * math.cos(phi)
    heading = -phi_deg if above else phi_deg
    return x, y, heading


def arc_path(icr, radius, above, phi0, phi1, n=49) -> str:
    pts = []
    for i in range(n):
        phi = phi0 + (phi1 - phi0) * i / (n - 1)
        x, y, _ = arc_O(icr, radius, above, phi)
        pts.append((x, y))
    head = f"M {fmt(pts[0][0])} {fmt(pts[0][1])}"
    return head + "".join(f" L {fmt(x)} {fmt(y)}" for x, y in pts[1:])


def local_track(icr, radius, above, phi0, phi1, local, n=25) -> str:
    """World path traced by one point of the rigid assembly.

    The vehicle turns as a rigid body about the ICR, so every body point rides a
    circle about the same centre and sweeps the same angle -- which is why these
    label tracks stay in step with the geometry without any extra timing work.
    """
    lx, ly = local
    pts = []
    for i in range(n):
        phi = phi0 + (phi1 - phi0) * i / (n - 1)
        ox, oy, hd = arc_O(icr, radius, above, phi)
        dx, dy = rot(lx, ly, hd)
        pts.append((ox + dx, oy + dy))
    head = f"M {fmt(pts[0][0])} {fmt(pts[0][1])}"
    return head + "".join(f" L {fmt(x)} {fmt(y)}" for x, y in pts[1:])


# --- text helpers -------------------------------------------------------
def text(x, y, s, cls, anchor="start"):
    return f'<text x="{fmt(x)}" y="{fmt(y)}" class="{cls}" text-anchor="{anchor}">{s}</text>'


def sym(x, y, main, sub="", cls="sym", sub_dx=0.0):
    """A symbol with an optional subscript, laid out left to right from x."""
    out = text(x, y, main, cls)
    if sub:
        out += text(x + sub_dx, y + 9, sub, cls + "-s")
    return out


# --- the shared assembly ------------------------------------------------
def body_and_bracket() -> str:
    """Chassis body, axle, the two marked points, and the p_x bracket."""
    x0, x1 = -40.0, LEVER + 46.0
    return (
        f'<rect x="{fmt(x0)}" y="-30" width="{fmt(x1 - x0)}" height="60" rx="16" class="body"/>'
        f'<line x1="0" y1="-30" x2="0" y2="30" class="axle"/>'
        f'<line x1="0" y1="{fmt(BRACKET_Y - 22)}" x2="0" y2="{fmt(BRACKET_Y)}" class="fg-thin"/>'
        f'<line x1="{fmt(LEVER)}" y1="{fmt(BRACKET_Y - 22)}" x2="{fmt(LEVER)}" y2="{fmt(BRACKET_Y)}" class="fg-thin"/>'
        f'<line x1="0" y1="{fmt(BRACKET_Y)}" x2="{fmt(LEVER)}" y2="{fmt(BRACKET_Y)}" class="bracket" '
        f'marker-start="url(#tip-i)" marker-end="url(#tip-i)"/>'
        f'<circle cx="0" cy="0" r="10" class="ink-fill"/>'
        f'<circle cx="{fmt(LEVER)}" cy="0" r="11" class="acc-fill"/>'
    )


def assembly_forward() -> str:
    """Forward motion: the sensor reading splits along its misaligned axes."""
    psi = math.radians(PSI_DEG)
    sx, sy = math.cos(psi), -math.sin(psi)            # sensor x axis, screen
    bx = LEVER + V_SENS * math.cos(psi) * sx
    by = V_SENS * math.cos(psi) * sy
    return (
        body_and_bracket()
        # the vehicle's own velocity: forward only, at both marked points
        + f'<line x1="0" y1="0" x2="{fmt(V_AXLE)}" y2="0" class="v-ink" marker-end="url(#tip-i)"/>'
        + f'<line x1="{fmt(LEVER)}" y1="0" x2="{fmt(LEVER + V_SENS)}" y2="0" class="v-ink" marker-end="url(#tip-i)"/>'
        # the sensor's own axes, rotated by psi
        + f'<line x1="{fmt(LEVER)}" y1="0" x2="{fmt(LEVER + 168 * sx)}" y2="{fmt(168 * sy)}" class="axis-dash"/>'
        # the same velocity resolved on those axes
        + f'<line x1="{fmt(LEVER)}" y1="0" x2="{fmt(bx)}" y2="{fmt(by)}" class="comp" marker-end="url(#tip-a)"/>'
        + f'<line x1="{fmt(bx)}" y1="{fmt(by)}" x2="{fmt(LEVER + V_SENS)}" y2="0" class="comp-strong" marker-end="url(#tip-a)"/>'
        # the psi wedge at the sensor
        + f'<path d="M {fmt(LEVER + 42)} 0 A 42 42 0 0 0 {fmt(LEVER + 42 * sx)} {fmt(42 * sy)}" class="fg-thin"/>'
    )


def assembly_turn() -> str:
    """Steady turn: the axle point stays lateral-free, the sensor does not."""
    return (
        body_and_bracket()
        + f'<line x1="0" y1="0" x2="{fmt(V_AXLE)}" y2="0" class="v-ink" marker-end="url(#tip-i)"/>'
        + f'<line x1="{fmt(LEVER)}" y1="0" x2="{fmt(LEVER + V_SENS)}" y2="0" class="ink-dash"/>'
        + f'<line x1="{fmt(LEVER)}" y1="0" x2="{fmt(LEVER + V_SENS)}" y2="{fmt(-LAT_LEN)}" '
        f'class="v-thin" marker-end="url(#tip-i)"/>'
        + f'<line x1="{fmt(LEVER + V_SENS)}" y1="0" x2="{fmt(LEVER + V_SENS)}" y2="{fmt(-LAT_LEN)}" '
        f'class="comp-strong" marker-end="url(#tip-a)"/>'
    )


# --- panel frames -------------------------------------------------------
def frame(px, title, kicker, notes) -> str:
    out = (
        f'<rect x="{px}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" rx="14" class="panel"/>'
        + text(px + 32, PANEL_Y + 46, title, "h")
        + text(px + PANEL_W - 30, PANEL_Y + 90, kicker, "big-m", "end")
    )
    for i, line in enumerate(notes):
        out += text(px + 32, PANEL_Y + 486 + 30 * i, line, "note")
    return out


# --- panel A ------------------------------------------------------------
PA_LABELS = (
    # (local x, local y, main, sub, class, subscript offset)
    (LEVER / 2 - 12, BRACKET_Y + 30, "p", "x", "symi", 17.0),
    (LEVER + 26, -52, "&#7805;", "x", "syma", 16.0),
    (LEVER + V_SENS + 6, -30, "&#7805;", "y", "syma", 16.0),
    (LEVER + 52, -12, "&#968;", "", "sym", 0.0),
)


def panel_a(animated: bool) -> str:
    out = frame(
        PA_X,
        "Forward motion in a turn",
        "v&#8339; &#8800; 0",
        (
            "Forward speed makes the yaw offset observable.",
            "Each accepted curvature couples &#968; and X differently.",
        ),
    )
    road = arc_path(PA_ICR, PA_R, True, -PA_SWEEP, PA_SWEEP)
    trail = arc_path(PA_ICR, PA_R, True, -PA_SWEEP, PA_SWEEP)
    out += f'<path d="{road}" class="road"/>'
    inner = assembly_forward() + "".join(
        sym(lx, ly, main, sub, cls, dx) for lx, ly, main, sub, cls, dx in PA_LABELS
    )
    if animated:
        out += (
            f'<path d="{trail}" class="trace" pathLength="1000" stroke-dasharray="1000" '
            f'stroke-dashoffset="1000"><animate attributeName="stroke-dashoffset" values="1000;0;0" '
            f'keyTimes="0;{T_TRAVEL};1" dur="{LOOP}s" calcMode="linear" repeatCount="indefinite"/></path>'
            f'<g opacity="0"><animateMotion dur="{LOOP}s" repeatCount="indefinite" rotate="auto" '
            f'calcMode="linear" keyPoints="0;1;1" keyTimes="0;{T_TRAVEL};1">'
            f'<mpath href="#paTrail" xlink:href="#paTrail"/></animateMotion>'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.08;0.88;1" '
            f'dur="{LOOP}s" calcMode="linear" repeatCount="indefinite"/>'
            f"{inner}</g>"
        )
    else:
        out += f'<path d="{trail}" class="trace"/>'
        ox, oy, hd = arc_O(PA_ICR, PA_R, True, PA_SWEEP)
        out += f'<g transform="translate({fmt(ox)},{fmt(oy)}) rotate({fmt(hd)})">{inner}</g>'
    return out


# --- panel B ------------------------------------------------------------
PB_LABELS = (
    (LEVER / 2 - 12, BRACKET_Y + 30, "p", "x", "symi", 17.0),
    (LEVER + V_SENS + 16, -LAT_LEN + 4, "&#969; p", "x", "syma", 47.0),
)


def icr_and_omega() -> str:
    cx, cy = PB_ICR
    r = 54.0
    a0, a1 = 335.0, 205.0          # left turn: counter-clockwise on screen
    p0 = (cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0)))
    p1 = (cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1)))
    d = f"M {fmt(p0[0])} {fmt(p0[1])} A {fmt(r)} {fmt(r)} 0 0 0 {fmt(p1[0])} {fmt(p1[1])}"
    return (
        f'<line x1="{fmt(cx)}" y1="{fmt(cy)}" x2="{fmt(cx)}" y2="{fmt(PB_APEX_Y)}" class="rule-dash"/>'
        f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="9" class="icr-dot"/>'
        f'<line x1="{fmt(cx - 22)}" y1="{fmt(cy)}" x2="{fmt(cx + 22)}" y2="{fmt(cy)}" class="fg-thin"/>'
        f'<line x1="{fmt(cx)}" y1="{fmt(cy - 22)}" x2="{fmt(cx)}" y2="{fmt(cy + 22)}" class="fg-thin"/>'
        + text(cx - 26, cy + 42, "ICR", "sym", "end")
        + f'<path d="{d}" class="fg-arrow" marker-end="url(#tip)"/>'
        + text(cx + r + 18, cy + 10, "&#969;", "sym")
    )


def panel_b(animated: bool) -> str:
    out = frame(
        PB_X,
        "Steady turn",
        "&#969; &#8800; 0",
        (
            "The axle point has no lateral velocity at all.",
            "What the sensor sees is the lever arm times &#969;.",
        ),
    )
    out += icr_and_omega()
    road = arc_path(PB_ICR, PB_R, True, -PB_SWEEP, PB_SWEEP)
    trail = arc_path(PB_ICR, PB_R, True, -PB_SWEEP, 0.0)
    out += f'<path d="{road}" class="road"/>'

    if animated:
        out += (
            f'<path d="{trail}" class="trace" pathLength="1000" stroke-dasharray="1000" '
            f'stroke-dashoffset="1000">'
            f'<animate attributeName="stroke-dashoffset" values="1000;0;0" keyTimes="0;{T_TRAVEL};1" '
            f'dur="{LOOP}s" calcMode="linear" repeatCount="indefinite"/></path>'
            f'<g><animateMotion dur="{LOOP}s" repeatCount="indefinite" rotate="auto" calcMode="linear" '
            f'keyPoints="0;1;1" keyTimes="0;{T_TRAVEL};1">'
            f'<mpath href="#pbTrail" xlink:href="#pbTrail"/></animateMotion>'
            f'<use href="#asmTurn" xlink:href="#asmTurn"/></g>'
        )
        for i, (lx, ly, main, sub, cls, dx) in enumerate(PB_LABELS):
            out += (
                f'<g><animateMotion dur="{LOOP}s" repeatCount="indefinite" calcMode="linear" '
                f'keyPoints="0;1;1" keyTimes="0;{T_TRAVEL};1">'
                f'<mpath href="#pbL{i}" xlink:href="#pbL{i}"/></animateMotion>'
                f"{sym(0, 0, main, sub, cls, dx)}</g>"
            )
    else:
        out += f'<path d="{trail}" class="trace"/>'
        ox, oy, hd = arc_O(PB_ICR, PB_R, True, 0.0)
        out += (
            f'<g transform="translate({fmt(ox)},{fmt(oy)}) rotate({fmt(hd)})">'
            f'<use href="#asmTurn" xlink:href="#asmTurn"/></g>'
        )
        for lx, ly, main, sub, cls, dx in PB_LABELS:
            wx, wy = rot(lx, ly, hd)
            out += sym(ox + wx, oy + wy, main, sub, cls, dx)
    return out


# --- readout strip ------------------------------------------------------
def strip(animated: bool) -> str:
    ox, oy = PLOT_O
    x0, x1 = ox - PLOT_HALF, ox + PLOT_HALF
    line_d = f"M {fmt(x0)} {fmt(oy + PLOT_RISE)} L {fmt(x1)} {fmt(oy - PLOT_RISE)}"
    out = (
        f'<rect x="{ST_X}" y="{ST_Y}" width="{ST_W}" height="{ST_H}" rx="14" class="panel"/>'
        + text(110, 716, "One line, two unknowns", "h")
        + sym(110, 758, "slope &#8594; p", "x", "symi", 140.0)
        + sym(110, 798, "origin &#8594; &#968;", "", "symi", 0.0)
        # axes
        + f'<line x1="{fmt(x0 - 16)}" y1="{fmt(oy)}" x2="{fmt(x1 + 16)}" y2="{fmt(oy)}" class="rule-line"/>'
        + f'<line x1="{fmt(ox)}" y1="{fmt(oy - 78)}" x2="{fmt(ox)}" y2="{fmt(oy + 78)}" class="rule-line"/>'
        + text(x1 + 28, oy + 10, "&#969;", "sym")
        + text(ox - 18, ST_Y + 30, "lateral velocity in vehicle axes", "lbl", "end")
        # the fit line and the three landmarks
        + f'<path d="{line_d}" class="fit" id="fitLine"/>'
        + f'<circle cx="{fmt(x0 + 10)}" cy="{fmt(oy + PLOT_RISE - 2.7)}" r="9" class="acc-open"/>'
        + text(x0 + 22, oy + PLOT_RISE + 34, "opposite turn", "lbl")
        + f'<rect x="{fmt(ox - 28)}" y="{fmt(oy - 78)}" width="56" height="156" class="gate-band"/>'
        + text(ox + 16, oy + 34, "gated band", "lbl")
        + text(x1 - 6, ST_Y + 30, "turning frames", "lbl", "end")
    )
    dot = '<circle cx="0" cy="0" r="10" class="acc-fill"/>'
    if animated:
        out += (
            f'<g><animateMotion dur="{LOOP}s" repeatCount="indefinite" calcMode="linear" '
            f'keyPoints="0.5;0.978;0.978" keyTimes="0;{T_TRAVEL};1">'
            f'<mpath href="#fitLine" xlink:href="#fitLine"/></animateMotion>{dot}</g>'
        )
    else:
        out += f'<g transform="translate({fmt(x1 - 10)},{fmt(oy - PLOT_RISE + 2.7)})">{dot}</g>'
    for i, line in enumerate(
        (
            "The slope of that line is the lever arm.",
            "Forward speed supplies the yaw lever; different",
            "curvatures intersect in the (&#968;, X) space.",
        )
    ):
        out += text(1500, 730 + 38 * i, line, "note", "end")
    return out


# --- assembly -----------------------------------------------------------
STYLE = f"""
    .panel {{ fill: {PAPER}; stroke: {RULE}; stroke-width: 1.6; }}
    .body {{ fill: {SOFT}; stroke: {RULE}; stroke-width: 1.8; }}
    .road {{ fill: none; stroke: {RULE}; stroke-width: 6; stroke-linecap: round; }}
    .trace {{ fill: none; stroke: {INK}; stroke-width: 5; stroke-linecap: round; opacity: .55; }}
    .fg-thin {{ fill: none; stroke: {MUTED}; stroke-width: 1.8; }}
    .fg-arrow {{ fill: none; stroke: {MUTED}; stroke-width: 2.4; }}
    .rule-line {{ fill: none; stroke: {RULE}; stroke-width: 2; }}
    .rule-dash {{ fill: none; stroke: {RULE}; stroke-width: 2; stroke-dasharray: 7 6; }}
    .ink-dash {{ fill: none; stroke: {MUTED}; stroke-width: 1.8; stroke-dasharray: 8 7; }}
    .axis-dash {{ fill: none; stroke: {ACC}; stroke-width: 1.8; stroke-dasharray: 8 7; opacity: .75; }}
    .fit {{ fill: none; stroke: {MUTED}; stroke-width: 2.6; }}
    .gate-band {{ fill: {RULE}; opacity: .45; }}
    .bracket {{ fill: none; stroke: {INK}; stroke-width: 2.2; }}
    .axle {{ fill: none; stroke: {INK}; stroke-width: 6; stroke-linecap: round; }}
    .v-ink {{ fill: none; stroke: {INK}; stroke-width: 4; }}
    .v-thin {{ fill: none; stroke: {INK}; stroke-width: 2.2; }}
    .comp {{ fill: none; stroke: {ACC}; stroke-width: 3; opacity: .8; }}
    .comp-strong {{ fill: none; stroke: {ACC}; stroke-width: 5; }}
    .ink-fill {{ fill: {INK}; stroke: {PAPER}; stroke-width: 2.5; }}
    .acc-fill {{ fill: {ACC}; stroke: {PAPER}; stroke-width: 2.5; }}
    .acc-open {{ fill: {PAPER}; stroke: {ACC}; stroke-width: 3.4; }}
    .icr-dot {{ fill: {PAPER}; stroke: {MUTED}; stroke-width: 3; }}
    text {{ font-family: Arial, Helvetica, sans-serif; fill: {INK}; }}
    .h {{ font-size: 33px; font-weight: 700; }}
    .lbl {{ font-size: 23px; fill: {MUTED}; }}
    .note {{ font-size: 25px; fill: {MUTED}; }}
    .big-m {{ font-size: 44px; font-weight: 700; fill: {MUTED}; }}
    .sym {{ font-size: 30px; font-weight: 700; fill: {MUTED}; }}
    .sym-s {{ font-size: 21px; font-weight: 700; fill: {MUTED}; }}
    .symi {{ font-size: 30px; font-weight: 700; fill: {INK}; }}
    .symi-s {{ font-size: 21px; font-weight: 700; fill: {INK}; }}
    .syma {{ font-size: 30px; font-weight: 700; fill: {ACC}; }}
    .syma-s {{ font-size: 21px; font-weight: 700; fill: {ACC}; }}
"""

RIBBON_1 = ("Lateral velocity is not free: the turn rate and the "
            "longitudinal lever arm fix it.")
RIBBON_2 = ("One sensor, one scalar per frame &#8212; no target, no shared field of view, "
            "no point correspondence.")

TITLE = "How one sensor reads its own lever arm and yaw offset out of vehicle motion"
DESC = (
    "Schematic. Left panel: a vehicle moving forward through a gentle turn. Forward speed "
    "makes yaw observable, while each accepted curvature couples yaw and longitudinal lever "
    "arm differently. Right panel: the same vehicle in a steady turn about an instantaneous centre of "
    "rotation. The axle point is still lateral-free, while the sensor, mounted a lever arm "
    "ahead of it, gains a lateral velocity equal to the turn rate times that lever arm. A "
    "readout below plots lateral velocity against turn rate: the near-zero turn-rate band is "
    "gated out and accepted turns constrain yaw and lever arm jointly. No numbers with units "
    "appear; the figure is a mechanism sketch, not a measurement."
)


def build(animated: bool) -> str:
    defs = [
        '<defs>',
        f'<marker id="tip" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
        f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{MUTED}"/></marker>',
        f'<marker id="tip-i" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
        f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{INK}"/></marker>',
        f'<marker id="tip-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
        f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{ACC}"/></marker>',
        f'<g id="asmTurn">{assembly_turn()}</g>',
    ]
    if animated:
        defs.append(
            f'<path id="paTrail" d="{arc_path(PA_ICR, PA_R, True, -PA_SWEEP, PA_SWEEP)}" class="mp"/>'
        )
        defs.append(
            f'<path id="pbTrail" d="{arc_path(PB_ICR, PB_R, True, -PB_SWEEP, 0.0)}" class="mp"/>'
        )
        for i, (lx, ly, _m, _s, _c, _d) in enumerate(PB_LABELS):
            track = local_track(PB_ICR, PB_R, True, -PB_SWEEP, 0.0, (lx, ly))
            defs.append(f'<path id="pbL{i}" d="{track}" class="mp"/>')
    defs.append("</defs>")

    body = (
        text(W / 2, 48, RIBBON_1, "h", "middle")
        + text(W / 2, 84, RIBBON_2, "lbl", "middle")
        + panel_a(animated)
        + panel_b(animated)
        + strip(animated)
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="pt pd">'
        f'<title id="pt">{TITLE}</title><desc id="pd">{DESC}</desc>'
        f"<style>{STYLE}</style>{''.join(defs)}"
        f'<rect width="{W}" height="{H}" fill="{PAPER}"/>'
        f"{body}</svg>"
    )


UNIT_RE = re.compile(r"\d\s*(mm|cm|m|deg|rad|s|Hz|m/s)\b")
REQUIRED = (
    "Forward motion in a turn",
    "Steady turn",
    "ICR",
    "One line, two unknowns",
    "gated band",
    "opposite turn",
)


def check(svg: str, name: str) -> list[str]:
    problems = []
    texts = re.findall(r"<text[^>]*>(.*?)</text>", svg, flags=re.S)
    for t in texts:
        if UNIT_RE.search(t):
            problems.append(f"{name}: unit-bearing number in text: {t!r}")
    joined = " ".join(texts)
    for need in REQUIRED:
        if need not in joined:
            problems.append(f"{name}: required string missing: {need!r}")
    if "<script" in svg or "onload=" in svg:
        problems.append(f"{name}: script content present")
    ids = set(re.findall(r'id="([^"]+)"', svg))
    refs = set(re.findall(r'href="#([A-Za-z0-9_-]+)"', svg))
    refs |= set(re.findall(r'url\(#([A-Za-z0-9_-]+)\)', svg))
    for r in sorted(refs - ids):
        problems.append(f"{name}: dangling reference: #{r}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing files (they may carry hand edits)")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    targets = {
        "hero_pxyaw.svg": build(animated=True),
        "hero_pxyaw_static.svg": build(animated=False),
    }

    problems = []
    for name, svg in targets.items():
        problems += check(svg, name)
    if problems:
        print("REFUSING TO WRITE -- checks failed:")
        for p in problems:
            print("  " + p)
        return 1

    for name, svg in targets.items():
        path = out / name
        if path.exists() and not args.force:
            print(f"skip (exists, use --force): {path}")
            continue
        path.write_text(svg, encoding="utf-8")
        digest = hashlib.sha256(svg.encode("utf-8")).hexdigest()[:16]
        print(f"wrote {path}  {len(svg) / 1024:.1f} KB  sha256:{digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
