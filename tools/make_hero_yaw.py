#!/usr/bin/env python3
"""Build the Stage-1 yaw panel as a three-step story:

  1. the sensor's measured velocity = body forward speed + the turn part
     omega * p_x (sideways, along the vehicle's lateral axis),
  2. subtract omega * p_x (p_x is already known from the rate fit): only the
     body's forward velocity v is left, along the heading,
  3. read that v on the sensor's own axes, which are rotated by psi:
     v~x = v cos psi, v~y = -v sin psi, so v~y = -tan psi * v~x at any speed.

Left panel: top view of the car and the sensor.  Right panel: the sensor's own
frame, one dot per sample -- measured dots scatter with the turn, and after
step 2 every dot slides onto one line through the origin whose slope is
-tan psi.

Construction rules shared with make_hero_pxyaw.py / make_hero_rollpitch.py:
  * no JavaScript -- SMIL only
  * no number carrying a unit in any text; the panel speaks in symbols
  * pure string building, stock Python only
  * refuses to write if a text check or a dangling reference fails

Writes:
  hero_yaw.svg          16 s loop
  hero_yaw_static.svg   step-3 state, for prefers-reduced-motion
"""

from __future__ import annotations

import argparse
import hashlib
import math
import re
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "hero"

W, H = 1600, 900
INK, MUTED, RULE, SOFT, ACC, PAPER = "#191919", "#666666", "#d8d8d8", "#f5f5f3", "#a52e29", "#ffffff"
LAT = "#1d4ed8"            # the omega*p_x lever-arm part (removed in step 2)
RAW = "#9a9a9a"            # measured sensor velocity

LOOP = 16.0
PSI = 14.0                 # mounting yaw, exaggerated
SP, CP = math.sin(math.radians(PSI)), math.cos(math.radians(PSI))

# samples: body forward speed and the omega*p_x lateral part (fractions of max,
# + = left turn).  Different turns, one mount angle.
SAMPLES = [(0.50, 0.24), (0.70, -0.22), (0.90, 0.14), (0.58, -0.28),
           (0.97, -0.18), (0.40, 0.10), (0.80, 0.30)]
T1 = [0.6 + 0.62 * k for k in range(len(SAMPLES))]   # arrival time of each sample
HOLD = 0.30
SHRINK = (5.5, 6.7)        # step 2: omega*p_x shrinks to zero
SLIDE0, SLIDE_DT, SLIDE_LEN = 5.6, 0.10, 1.0          # step 2: dots slide onto the line
S3 = 9.2                   # step 3 visuals appear
WOB = (10.2, 15.0)         # step 3: speed wobbles
END, RESET = 15.4, 15.7    # transient visuals gone / state jumps back
STAGES = [(0.0, 5.0), (5.0, 9.0), (9.0, END)]
T_STATIC = 13.0

# --- geometry -----------------------------------------------------------
PANEL_Y, PANEL_W, PANEL_H = 186, 730, 574
PA_X, PB_X = 60, 810
CAR = (165.0, 520.0)       # rear-axle centre
LEVER = 190.0              # p_x in pixels
SEN = (CAR[0] + LEVER, CAR[1])
K = 300.0                  # left panel: arrow length at full speed
PO = (880.0, 420.0)        # right panel: plot origin
PL = 460.0                 # right panel: plot length at full speed
V_TRI = 0.80               # speed of the fixed slope triangle


def fmt(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def sub(s: str) -> str:
    return f'<tspan dy="7" font-size="72%">{s}</tspan><tspan dy="-7">&#8202;</tspan>'


def text(x, y, s, cls, anchor="start"):
    return f'<text x="{fmt(x)}" y="{fmt(y)}" class="{cls}" text-anchor="{anchor}">{s}</text>'


def smooth(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


# --- the motion ---------------------------------------------------------
def sample_at(t: float):
    """(v, l) of the sample sequence, before any removal."""
    if t >= RESET or t <= T1[0] + HOLD:
        return SAMPLES[0]
    for k in range(len(SAMPLES) - 1):
        a, b = T1[k] + HOLD, T1[k + 1]
        if t <= a:
            return SAMPLES[k]
        if t <= b:
            u = smooth((t - a) / (b - a))
            (v0, l0), (v1, l1) = SAMPLES[k], SAMPLES[k + 1]
            return v0 + (v1 - v0) * u, l0 + (l1 - l0) * u
    return SAMPLES[-1]


def state(t: float):
    """(v, l) shown at time t: samples, then removal, then speed wobble."""
    v, l = sample_at(t)
    if t >= RESET:
        return v, l
    if t >= SHRINK[0]:
        l *= 1 - smooth((t - SHRINK[0]) / (SHRINK[1] - SHRINK[0]))
    if WOB[0] < t < WOB[1]:
        u = (t - WOB[0]) / (WOB[1] - WOB[0])
        s = t - WOB[0]
        v += math.sin(math.pi * u) * (0.20 * math.sin(2 * math.pi * s / 2.4)
                                      + 0.05 * math.sin(2 * math.pi * s / 0.9))
    return v, l


def sensor(v, l):
    """Body (forward v, lateral l) resolved on sensor axes rotated by psi."""
    return v * CP + l * SP, -v * SP + l * CP


def right_pt(v, l):
    x, y = sensor(v, l)
    return PO[0] + PL * x, PO[1] - PL * y


def rot(a, b):
    """Local sensor frame (a along x~, b to the sensor's right) -> page."""
    return SEN[0] + a * CP + b * SP, SEN[1] - a * SP + b * CP


# --- SMIL helpers -------------------------------------------------------
KN = 0.05
KNOTS = [round(k * KN, 4) for k in range(int(round(LOOP / KN)) + 1)]


def kt(times):
    return ";".join(f"{min(max(t / LOOP, 0.0), 1.0):.4f}" for t in times)


KT_DENSE = kt(KNOTS)


def dense(attr, f):
    return (f'<animate attributeName="{attr}" dur="{LOOP}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{KT_DENSE}" values="{";".join(fmt(f(t)) for t in KNOTS)}"/>')


def keyed(attr, keys):
    return (f'<animate attributeName="{attr}" dur="{LOOP}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{kt([t for t, _ in keys])}" '
            f'values="{";".join(f"{v:g}" for _, v in keys)}"/>')


def interp(keys, t):
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            return v0 if t1 == t0 else v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return keys[-1][1]


def win(on, off, hi=1.0, lo=0.0, rise=0.2):
    """Opacity lo -> hi at `on`, back to lo at `off` (fully gone at `off`)."""
    return [(0.0, lo), (on, lo), (on + rise, hi), (off - rise, hi), (off, lo), (LOOP, lo)]


ALWAYS = [(0.0, 1.0), (15.3, 1.0), (15.5, 0.0), (15.85, 0.0), (LOOP, 1.0)]


def stage_keys(i, hi=1.0, lo=0.0):
    on, off = STAGES[i]
    if i == 0:
        return [(0.0, hi), (off - 0.15, hi), (off, lo), (15.8, lo), (LOOP, hi)]
    return win(on, off, hi, lo, rise=0.15)


def node(tag, animated, fixed="", pos=None, op=None, inner=""):
    """One element; `pos` maps attribute -> f(t), `op` is an opacity key list."""
    pos = pos or {}
    if animated:
        attrs = fixed + "".join(f' {k}="{fmt(f(0.0))}"' for k, f in pos.items())
        if op:
            attrs += f' opacity="{interp(op, 0.0):g}"'
        anims = "".join(dense(k, f) for k, f in pos.items()) + (keyed("opacity", op) if op else "")
        return f"<{tag}{attrs}>{anims}{inner}</{tag}>"
    o = interp(op, T_STATIC) if op else 1.0
    if o <= 0.01:
        return ""
    attrs = fixed + "".join(f' {k}="{fmt(f(T_STATIC))}"' for k, f in pos.items())
    if op and o < 0.99:
        attrs += f' opacity="{o:.2f}"'
    return f"<{tag}{attrs}>{inner}</{tag}>"


def frame(px, title, kicker) -> str:
    return (f'<rect x="{px}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" rx="14" class="panel"/>'
            + text(px + 32, PANEL_Y + 44, title, "h")
            + text(px + 32, PANEL_Y + 76, kicker, "lbl"))


# --- car illustration ---------------------------------------------------
def car_top() -> str:
    """Top-view car, nose to page +x."""
    x0, x1 = CAR[0] - 70, CAR[0] + LEVER + 80
    y0, y1 = CAR[1] - 62, CAR[1] + 62
    xf = CAR[0] + 225                                  # front axle
    out = ""
    for wx in (CAR[0], xf):                            # wheels, outside the body
        for wy in (y0 - 9, y1 - 9):
            out += (f'<rect x="{fmt(wx - 24)}" y="{fmt(wy)}" width="48" height="18" rx="6" '
                    f'class="tyre"/>')
    body = (f"M {fmt(x0 + 26)} {fmt(y0)} L {fmt(x1 - 64)} {fmt(y0)} "
            f"Q {fmt(x1)} {fmt(y0)} {fmt(x1)} {fmt(y0 + 42)} L {fmt(x1)} {fmt(y1 - 42)} "
            f"Q {fmt(x1)} {fmt(y1)} {fmt(x1 - 64)} {fmt(y1)} L {fmt(x0 + 26)} {fmt(y1)} "
            f"Q {fmt(x0)} {fmt(y1)} {fmt(x0)} {fmt(y1 - 26)} L {fmt(x0)} {fmt(y0 + 26)} "
            f"Q {fmt(x0)} {fmt(y0)} {fmt(x0 + 26)} {fmt(y0)} Z")
    out += f'<path d="{body}" class="body"/>'
    rw0, rw1, ws0, ws1 = x0 + 20, x0 + 46, CAR[0] + 118, CAR[0] + 152
    out += (f'<path d="M {fmt(rw1)} {fmt(y0 + 14)} L {fmt(rw0)} {fmt(y0 + 26)} L {fmt(rw0)} '
            f'{fmt(y1 - 26)} L {fmt(rw1)} {fmt(y1 - 14)} Z" class="glass"/>'
            f'<rect x="{fmt(rw1 + 4)}" y="{fmt(y0 + 12)}" width="{fmt(ws0 - rw1 - 8)}" '
            f'height="{fmt(y1 - y0 - 24)}" rx="12" class="roof"/>'
            f'<path d="M {fmt(ws0)} {fmt(y0 + 14)} L {fmt(ws1)} {fmt(y0 + 28)} L {fmt(ws1)} '
            f'{fmt(y1 - 28)} L {fmt(ws0)} {fmt(y1 - 14)} Z" class="glass"/>')
    for my, dy in ((y0, -4), (y1, 4)):                 # mirrors
        out += f'<ellipse cx="{fmt(ws0 + 4)}" cy="{fmt(my + dy)}" rx="11" ry="5" class="tyre"/>'
    for hy in (y0 + 14, y1 - 28):                      # headlights
        out += f'<rect x="{fmt(x1 - 9)}" y="{fmt(hy)}" width="7" height="14" rx="3" class="lamp"/>'
    out += (f'<line x1="{fmt(CAR[0])}" y1="{fmt(y0 - 4)}" x2="{fmt(CAR[0])}" y2="{fmt(y1 + 4)}" '
            f'class="axle"/>'
            f'<circle cx="{fmt(CAR[0])}" cy="{fmt(CAR[1])}" r="9" class="ink-fill"/>')
    return out


def omega_arc(animated: bool) -> str:
    """Turn-rate arrow around the rear axle; flips with the sign of the turn."""
    r = 44.0
    p = lambda a: (r * math.cos(math.radians(a)), -r * math.sin(math.radians(a)))
    (ax, ay), (bx, by) = p(35), p(145)
    arc = (f'<path d="M {fmt(ax)} {fmt(ay)} A {fmt(r)} {fmt(r)} 0 0 0 {fmt(bx)} {fmt(by)}" '
           f'class="omega" marker-end="url(#tip-i)"/>')
    sgn = lambda t: 1 if sample_at(t)[1] >= 0 else -1
    if animated:
        vals = ";".join(f"1 {sgn(t)}" for t in KNOTS)
        flip = (f'<animateTransform attributeName="transform" type="scale" dur="{LOOP}s" '
                f'repeatCount="indefinite" calcMode="discrete" keyTimes="{KT_DENSE}" values="{vals}"/>')
        inner = f'<g transform="scale(1 {sgn(0.0)})">{flip}{arc}</g>'
    else:
        inner = f'<g transform="scale(1 {sgn(T_STATIC)})">{arc}</g>'
    return (f'<g transform="translate({fmt(CAR[0])} {fmt(CAR[1])})">{inner}</g>'
            + text(CAR[0] - 62, CAR[1] + 10, "&#969;", "symi", "end"))


# --- panel A: top view ---------------------------------------------------
def panel_a(animated: bool) -> str:
    sx, sy = SEN
    out = frame(PA_X, "Top view",
                "sensor a lever p" + sub("x") + " ahead of the rear axle, mounted at yaw &#968;")
    out += car_top() + omega_arc(animated)
    # heading line through the sensor (the body's forward direction)
    out += (f'<line x1="{fmt(sx)}" y1="{fmt(sy)}" x2="{fmt(sx + K + 90)}" y2="{fmt(sy)}" '
            f'class="rule-dash"/>')
    out += text(sx + K + 90, sy + 34, "heading", "lbl", "end")
    # sensor box and its own axes, rotated by psi
    ex, ey = rot(390, 0)
    yx, yy = rot(0, -130)
    out += (f'<g transform="translate({fmt(sx)} {fmt(sy)}) rotate({fmt(-PSI)})">'
            f'<line x1="0" y1="0" x2="390" y2="0" class="axis-dash"/>'
            f'<line x1="0" y1="0" x2="0" y2="-130" class="axis-dash"/>'
            f'<rect x="-22" y="-16" width="44" height="32" rx="5" class="acc-fill"/></g>')
    out += text(ex + 8, ey + 8, "x&#771;", "syma") + text(yx - 8, yy - 10, "y&#771;", "syma")
    r = 150.0
    out += (f'<path d="M {fmt(sx + r)} {fmt(sy)} A {fmt(r)} {fmt(r)} 0 0 0 '
            f'{fmt(sx + r * CP)} {fmt(sy - r * SP)}" class="fg-thin"/>'
            + text(sx + r + 8, sy - 8, "&#968;", "sym"))

    tipx = lambda t: sx + K * state(t)[0]
    laty = lambda t: sy - K * state(t)[1]
    # step 2 halo on the forward arrow
    out += node("line", animated, f' y1="{fmt(sy)}" y2="{fmt(sy)}" class="halo"',
                {"x1": lambda t: sx, "x2": tipx}, win(6.7, 9.3))
    # measured sensor velocity (gray), forward part (black), turn part (blue)
    out += node("line", animated, f' x1="{fmt(sx)}" y1="{fmt(sy)}" class="raw-v" marker-end="url(#tip-r)"',
                {"x2": tipx, "y2": laty}, win(0.3, 6.9))
    out += node("line", animated, f' x1="{fmt(sx)}" y1="{fmt(sy)}" y2="{fmt(sy)}" class="v-ink" '
                f'marker-end="url(#tip-i)"', {"x2": tipx}, ALWAYS)
    out += node("line", animated, f' y1="{fmt(sy)}" class="lat" marker-end="url(#tip-b)"',
                {"x1": tipx, "x2": tipx, "y2": laty}, win(0.3, 6.4))
    lab_y = lambda t: sy - K * state(t)[1] / 2 + 9
    out += node("text", animated, ' class="symb"', {"x": lambda t: tipx(t) + 14, "y": lab_y},
                win(0.3, 5.5), "&#969;&#183;p" + sub("x"))
    out += node("text", animated, ' class="symb"', {"x": lambda t: tipx(t) + 14, "y": lab_y},
                win(5.3, 6.5), "&#8722;&#969;&#183;p" + sub("x"))
    out += node("text", animated, ' class="symi" text-anchor="middle"',
                {"x": lambda t: sx + K * state(t)[0] / 2, "y": lambda t: sy + 36}, ALWAYS, "v")
    out += node("text", animated, ' class="lbl-ink" text-anchor="middle"',
                {"x": lambda t: sx + K * state(t)[0] / 2, "y": lambda t: sy + 112},
                win(6.9, 9.2), "forward speed only")
    # step 3: the same v on the sensor axes -- right triangle x~ leg + y~ leg
    ax_ = lambda t: rot(K * state(t)[0] * CP, 0)
    out += node("line", animated, f' x1="{fmt(sx)}" y1="{fmt(sy)}" class="comp-strong" '
                f'marker-end="url(#tip-a)"', {"x2": lambda t: ax_(t)[0], "y2": lambda t: ax_(t)[1]},
                win(S3, END))
    out += node("line", animated, ' class="comp-strong" marker-end="url(#tip-a)"',
                {"x1": lambda t: ax_(t)[0], "y1": lambda t: ax_(t)[1],
                 "x2": tipx, "y2": lambda t: sy}, win(S3 + 0.3, END))
    lx = lambda t: rot(K * state(t)[0] * CP * 0.62, -22)
    ly = lambda t: rot(K * state(t)[0] * CP + 16, K * state(t)[0] * SP * 0.5)
    out += node("text", animated, ' class="syma"', {"x": lambda t: lx(t)[0] - 14, "y": lambda t: lx(t)[1]},
                win(S3, END), "&#7805;" + sub("x"))
    out += node("text", animated, ' class="syma"', {"x": lambda t: ly(t)[0], "y": lambda t: ly(t)[1] - 4},
                win(S3 + 0.3, END), "&#7805;" + sub("y"))
    # legend
    y1, y2 = PANEL_Y + PANEL_H - 58, PANEL_Y + PANEL_H - 24
    for (x, y, cls, lab) in ((92, y1, "raw-v", "measured sensor velocity"),
                             (440, y1, "lat", "turn part &#969;&#183;p" + sub("x")),
                             (92, y2, "v-ink", "body forward velocity v"),
                             (440, y2, "comp-strong", "v on the sensor axes")):
        out += (f'<line x1="{x}" y1="{y - 8}" x2="{x + 34}" y2="{y - 8}" class="{cls}"/>'
                + text(x + 46, y, lab, "lbl"))
    return out


# --- panel B: sensor frame ----------------------------------------------
def panel_b(animated: bool) -> str:
    ox, oy = PO
    out = frame(PB_X, "Sensor frame", "one dot per sample, plotted as (&#7805;" + sub("x")
                + ", &#7805;" + sub("y") + ")")
    out += (f'<line x1="{fmt(ox)}" y1="{fmt(oy)}" x2="{fmt(ox + PL + 70)}" y2="{fmt(oy)}" '
            f'class="fg-arrow" marker-end="url(#tip)"/>'
            f'<line x1="{fmt(ox)}" y1="{fmt(oy + 290)}" x2="{fmt(ox)}" y2="{fmt(oy - 140)}" '
            f'class="fg-arrow" marker-end="url(#tip)"/>')
    out += text(ox + PL + 60, oy + 40, "&#7805;" + sub("x"), "sym")
    out += text(ox + 16, oy - 118, "&#7805;" + sub("y"), "sym")

    # step 3: the line, psi wedge, slope triangle, equation
    ex, ey = ox + (PL + 60) * CP, oy + (PL + 60) * SP
    tx, ty = right_pt(V_TRI, 0.0)
    line = (f'<line x1="{fmt(ox)}" y1="{fmt(oy)}" x2="{fmt(ex)}" y2="{fmt(ey)}" class="fit-acc"/>'
            f'<path d="M {fmt(ox + 120)} {fmt(oy)} A 120 120 0 0 1 {fmt(ox + 120 * CP)} '
            f'{fmt(oy + 120 * SP)}" class="fg-thin"/>'
            + text(ox + 130, oy + 24, "&#968;", "sym"))
    out += node("g", animated, op=win(S3, END, hi=0.9), inner=line)
    tri = (f'<line x1="{fmt(ox)}" y1="{fmt(oy)}" x2="{fmt(tx)}" y2="{fmt(oy)}" class="leg"/>'
           f'<line x1="{fmt(tx)}" y1="{fmt(oy)}" x2="{fmt(tx)}" y2="{fmt(ty)}" class="leg"/>'
           + text(ox + 0.32 * (tx - ox), oy - 14, "&#7805;" + sub("x"), "syma", "middle")
           + text(tx + 14, (oy + ty) / 2 + 12, "&#7805;" + sub("y"), "syma")
           + text(ox + PL + 70, oy + 236, "&#7805;" + sub("y") + " = &#8722;tan&#8201;&#968; &#183; &#7805;"
                  + sub("x"), "slope", "end")
           + text(ox + PL + 70, oy + 268, "same line at every speed", "lbl", "end"))
    out += node("g", animated, op=win(S3 + 0.6, END), inner=tri)

    # per sample: hollow measured dot, slide onto the line, red corrected dot
    for k, (v, l) in enumerate(SAMPLES):
        rx, ry = right_pt(v, l)
        cx, cy = right_pt(v, 0.0)
        s0 = SLIDE0 + SLIDE_DT * k
        s1 = s0 + SLIDE_LEN
        out += node("circle", animated, f' cx="{fmt(rx)}" cy="{fmt(ry)}" r="9" class="ring"',
                    op=win(T1[k], END, rise=0.12))
        out += node("line", animated, f' x1="{fmt(rx)}" y1="{fmt(ry)}" x2="{fmt(cx)}" y2="{fmt(cy)}" '
                    f'class="drop"', op=win(s1 - 0.2, END, hi=0.8))
        u = lambda t, s0=s0: smooth((t - s0) / SLIDE_LEN)
        out += node("circle", animated, ' r="9" class="raw-fill"',
                    {"cx": lambda t, u=u, rx=rx, cx=cx: rx + (cx - rx) * u(t),
                     "cy": lambda t, u=u, ry=ry, cy=cy: ry + (cy - ry) * u(t)},
                    win(T1[k], s1 + 0.1, rise=0.12))
        out += node("circle", animated, f' cx="{fmt(cx)}" cy="{fmt(cy)}" r="9" class="acc-fill"',
                    op=win(s1 - 0.1, END, hi=0.55, rise=0.15))

    # live vector: measured (gray) through step 2, then the forward speed (red)
    px_ = lambda t: right_pt(*state(t))[0]
    py_ = lambda t: right_pt(*state(t))[1]
    out += node("line", animated, f' x1="{fmt(ox)}" y1="{fmt(oy)}" class="raw-v" marker-end="url(#tip-r)"',
                {"x2": px_, "y2": py_}, win(0.3, 6.9))
    out += node("line", animated, f' x1="{fmt(ox)}" y1="{fmt(oy)}" class="comp-strong" '
                f'marker-end="url(#tip-a)"', {"x2": px_, "y2": py_}, win(6.7, END))
    out += node("circle", animated, ' r="12" class="acc-fill"', {"cx": px_, "cy": py_}, win(S3, END))
    out += text(PB_X + 32, PANEL_Y + PANEL_H - 24,
                "hollow: measured &#183; red: after removing &#969;&#183;p" + sub("x"), "lbl")
    return out


# --- step bar, captions, strip -----------------------------------------
PILLS = ["Remove the turn part &#969;&#183;p" + sub("x"),
         "Only the forward speed is left",
         "Read it on the sensor axes: tan&#8201;&#968;"]
CAPTIONS = [
    "In a turn the sensor moves forward with the body and sideways by &#969;&#183;p" + sub("x")
    + " (p" + sub("x") + " is known from the rate fit).",
    "Subtract &#969;&#183;p" + sub("x") + ": the sideways part vanishes and only the body's forward "
    "velocity v is left, along the heading.",
    "The sensor axes are rotated by &#968;, so v splits into &#7805;" + sub("x") + " = v cos&#8201;&#968; and &#7805;"
    + sub("y") + " = &#8722;v sin&#8201;&#968;: their ratio is &#8722;tan&#8201;&#968; at any speed.",
]


def step_bar(animated: bool) -> str:
    out = ""
    for i, lab in enumerate(PILLS):
        x, y, w, h = 60 + 502 * i, 66, 476, 54
        base = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="27" class="pill"/>'
                f'<circle cx="{x + 28}" cy="{y + 27}" r="16" class="badge-off"/>'
                + text(x + 28, y + 35, str(i + 1), "badge-t", "middle")
                + text(x + 56, y + 35, lab, "pill-off"))
        on = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="27" class="pill-on"/>'
              f'<circle cx="{x + 28}" cy="{y + 27}" r="16" class="acc-fill"/>'
              + text(x + 28, y + 35, str(i + 1), "badge-t", "middle")
              + text(x + 56, y + 35, lab, "pill-t"))
        out += base
        if animated:
            out += node("g", True, op=stage_keys(i), inner=on)
        elif i == 2:
            out += on
    for i, cap in enumerate(CAPTIONS):
        c = text(W / 2, 162, cap, "note", "middle")
        if animated:
            out += node("g", True, op=stage_keys(i), inner=c)
        elif i == 2:
            out += c
    return out


def strip(animated: bool) -> str:
    x, y = 60, 776
    out = f'<rect x="{x}" y="{y}" width="1480" height="108" rx="14" class="strip"/>'
    segs = [(92, "&#7805; = R(&#968;)&#7488; (v, &#969;&#183;p" + sub("x") + ")"),
            (450, "&#8722;&#969;&#183;p" + sub("x") + "  &#8594;  &#7805; = v (cos&#8201;&#968;, &#8722;sin&#8201;&#968;)"),
            (960, "&#7805;" + sub("y") + " = &#8722;tan&#8201;&#968; &#183; &#7805;" + sub("x"))]
    for i, (sx, s) in enumerate(segs):
        t = text(sx, y + 52, s, "eq")
        out += node("g", animated, op=stage_keys(i, hi=1.0, lo=0.3), inner=t) if animated else t
    out += text(412, y + 52, "&#8594;", "eq-m", "middle") + text(917, y + 52, "&#8594;", "eq-m", "middle")
    out += text(x + 32, y + 90, "body frame (forward, lateral) resolved on the sensor axes", "lbl")
    out += text(x + 1448, y + 90, "schematic &#183; &#968; exaggerated", "lbl", "end")
    return out


STYLE = f"""
    .panel {{ fill: {PAPER}; stroke: {RULE}; stroke-width: 1.6; }}
    .strip {{ fill: {SOFT}; stroke: {RULE}; stroke-width: 1.6; }}
    .pill {{ fill: {SOFT}; stroke: {RULE}; stroke-width: 1.6; }}
    .pill-on {{ fill: #f7e9e8; stroke: {ACC}; stroke-width: 3; }}
    .badge-off {{ fill: #bdbdbd; }}
    .badge-t {{ font-size: 20px; font-weight: 700; fill: {PAPER}; }}
    .pill-off {{ font-size: 24px; font-weight: 700; fill: #9a9a9a; }}
    .pill-t {{ font-size: 24px; font-weight: 700; fill: {INK}; }}
    .body {{ fill: {SOFT}; stroke: {RULE}; stroke-width: 1.8; }}
    .tyre {{ fill: {INK}; }}
    .glass {{ fill: #dde3ea; stroke: {RULE}; stroke-width: 1.4; }}
    .roof {{ fill: #ececea; stroke: {RULE}; stroke-width: 1.4; }}
    .lamp {{ fill: #f2d98a; }}
    .axle {{ fill: none; stroke: {INK}; stroke-width: 6; stroke-linecap: round; }}
    .omega {{ fill: none; stroke: {INK}; stroke-width: 3; }}
    .fg-thin {{ fill: none; stroke: {MUTED}; stroke-width: 1.8; }}
    .fg-arrow {{ fill: none; stroke: {MUTED}; stroke-width: 2.4; }}
    .rule-dash {{ fill: none; stroke: #bdbdbd; stroke-width: 2; stroke-dasharray: 7 6; }}
    .axis-dash {{ fill: none; stroke: {ACC}; stroke-width: 1.8; stroke-dasharray: 8 7; opacity: .75; }}
    .halo {{ fill: none; stroke: #f2d98a; stroke-width: 22; stroke-linecap: round; }}
    .raw-v {{ fill: none; stroke: {RAW}; stroke-width: 6; }}
    .v-ink {{ fill: none; stroke: {INK}; stroke-width: 4.5; }}
    .lat {{ fill: none; stroke: {LAT}; stroke-width: 4.5; }}
    .comp-strong {{ fill: none; stroke: {ACC}; stroke-width: 4; }}
    .leg {{ fill: none; stroke: {ACC}; stroke-width: 5; stroke-linecap: round; }}
    .drop {{ fill: none; stroke: {LAT}; stroke-width: 2; stroke-dasharray: 5 5; }}
    .fit-acc {{ fill: none; stroke: {ACC}; stroke-width: 3; }}
    .ring {{ fill: {PAPER}; stroke: {RAW}; stroke-width: 2.5; }}
    .raw-fill {{ fill: {RAW}; stroke: {PAPER}; stroke-width: 2; }}
    .ink-fill {{ fill: {INK}; stroke: {PAPER}; stroke-width: 2.5; }}
    .acc-fill {{ fill: {ACC}; stroke: {PAPER}; stroke-width: 2.5; }}
    text {{ font-family: Arial, Helvetica, sans-serif; fill: {INK}; }}
    .h {{ font-size: 33px; font-weight: 700; }}
    .lbl {{ font-size: 22px; fill: {MUTED}; }}
    .lbl-ink {{ font-size: 24px; font-weight: 700; fill: {INK}; }}
    .note {{ font-size: 25px; fill: {INK}; }}
    .eq {{ font-size: 30px; font-weight: 700; fill: {INK}; }}
    .eq-m {{ font-size: 30px; font-weight: 700; fill: {MUTED}; }}
    .slope {{ font-size: 29px; font-weight: 700; fill: {ACC}; }}
    .sym {{ font-size: 30px; font-weight: 700; fill: {MUTED}; }}
    .symi {{ font-size: 30px; font-weight: 700; fill: {INK}; }}
    .syma {{ font-size: 30px; font-weight: 700; fill: {ACC}; }}
    .symb {{ font-size: 27px; font-weight: 700; fill: {LAT}; }}
"""

RIBBON = "Yaw from one sensor: remove the turn part, then read the angle of what is left"
TITLE = "Why the slope of a sensor's lateral against longitudinal speed is its mounting yaw"
DESC = (
    "Schematic in three steps. Left: a car seen from above with a sensor mounted a lever arm ahead "
    "of the rear axle and rotated by the yaw angle psi. Step 1: in a turn the sensor's measured "
    "velocity (gray) is the body's forward velocity (black) plus a sideways part equal to the turn "
    "rate times the lever arm (blue); from sample to sample the gray arrow swings. Step 2: that "
    "sideways part is known from the rate fit and is subtracted, leaving only the forward velocity "
    "along the heading. Step 3: the sensor's own axes are rotated by psi, so the forward velocity "
    "splits into a longitudinal component v cos psi and a lateral component minus v sin psi. Right: "
    "the sensor's own frame, one dot per sample. Measured dots scatter with the turn; after the "
    "subtraction every dot slides onto one line through the origin whose angle is psi, so lateral "
    "over longitudinal speed is minus tan psi at any speed. No numbers with units appear."
)


def build(animated: bool) -> str:
    defs = ['<defs>']
    for mid, col in (("tip", MUTED), ("tip-i", INK), ("tip-a", ACC), ("tip-b", LAT), ("tip-r", RAW)):
        defs.append(f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5.5" '
                    f'markerHeight="5.5" orient="auto-start-reverse">'
                    f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{col}"/></marker>')
    defs.append('</defs>')
    body = (text(W / 2, 44, RIBBON, "h", "middle") + step_bar(animated)
            + panel_a(animated) + panel_b(animated) + strip(animated))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-labelledby="pt pd"><title id="pt">{TITLE}</title><desc id="pd">{DESC}</desc>'
            f"<style>{STYLE}</style>{''.join(defs)}"
            f'<rect width="{W}" height="{H}" fill="{PAPER}"/>{body}</svg>')


UNIT_RE = re.compile(r"\d\s*(mm|cm|m|deg|rad|s|Hz|m/s)\b")
REQUIRED = ("Remove the turn part", "Only the forward speed is left", "Read it on the sensor axes",
            "Top view", "Sensor frame", "same line at every speed")


def check(svg: str, name: str) -> list[str]:
    problems = []
    texts = [re.sub(r"<[^>]+>", "", t) for t in re.findall(r"<text[^>]*>(.*?)</text>", svg, flags=re.S)]
    for t in texts:
        if UNIT_RE.search(re.sub(r"&#\d+;", " ", t)):
            problems.append(f"{name}: unit-bearing number in text: {t!r}")
    joined = " ".join(texts)
    for need in REQUIRED:
        if need not in joined:
            problems.append(f"{name}: required string missing: {need!r}")
    if "<script" in svg or "onload=" in svg:
        problems.append(f"{name}: script content present")
    ids = set(re.findall(r'id="([^"]+)"', svg))
    refs = set(re.findall(r'href="#([A-Za-z0-9_-]+)"', svg)) | set(re.findall(r'url\(#([A-Za-z0-9_-]+)\)', svg))
    for r in sorted(refs - ids):
        problems.append(f"{name}: dangling reference: #{r}")
    return problems


def self_test() -> list[str]:
    """Physics check: after removal every sample lies on slope -tan(psi)."""
    bad = []
    for v, l in SAMPLES:
        x, y = sensor(v, 0.0)
        if abs(y / x + math.tan(math.radians(PSI))) > 1e-9:
            bad.append(f"sample {(v, l)} off the line")
    for t in KNOTS:
        if S3 <= t <= END:
            v, l = state(t)
            if abs(l) > 1e-9 or v <= 0.3:
                bad.append(f"t={t}: step-3 state not pure forward or too slow: {(v, l)}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    targets = {"hero_yaw.svg": build(True), "hero_yaw_static.svg": build(False)}
    problems = self_test() + [p for n, s in targets.items() for p in check(s, n)]
    if problems:
        print("REFUSING TO WRITE -- checks failed:"); [print("  " + p) for p in problems]
        return 1
    for name, svg in targets.items():
        path = out / name
        if path.exists() and not args.force:
            print(f"skip (exists, use --force): {path}"); continue
        path.write_text(svg, encoding="utf-8")
        print(f"wrote {path}  {len(svg) / 1024:.1f} KB  sha256:{hashlib.sha256(svg.encode()).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
