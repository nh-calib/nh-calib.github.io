#!/usr/bin/env python3
"""Build the Stage-1 yaw panel: why the slope of lateral against longitudinal
sensor speed IS the mounting yaw.

Mechanism the figure has to carry:
  * the chassis moves along its own heading (non-holonomic constraint); in a
    turn the sensor additionally moves sideways by omega * p_x,
  * omega * p_x is known from the rate plot of the same sensor, so it can be
    taken out of the lateral reading,
  * what is left is the forward motion of the body seen through a mount rotated
    by psi:  (v_x, v_y)_sensor = v * (cos psi, -sin psi),
  * so every speed and every turn lands on ONE line through the origin whose
    slope is -tan psi.  Speed only stretches the arrow; the angle is the mount.
    Zero forward speed carries no yaw information -- the yaw lever is forward
    speed, not straight driving.

Construction rules shared with make_hero_pxyaw.py / make_hero_rollpitch.py:
  * no JavaScript -- SMIL only
  * no number carrying a unit in any text; the panel speaks in symbols
  * pure string building, stock Python only
  * refuses to write if a text check or a dangling reference fails

Writes:
  hero_yaw.svg          9 s loop
  hero_yaw_static.svg   end state, for prefers-reduced-motion
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
LAT = "#1d4ed8"            # the omega*p_x lever-arm part (removed)

LOOP = 9.0
PSI = 14.0                 # mounting yaw, exaggerated
SP, CP = math.sin(math.radians(PSI)), math.cos(math.radians(PSI))

# four samples: forward speed (fraction of max) and the omega*p_x lateral part
# (fraction of max, + = left turn).  Different turns, one mount angle.
STEPS = [(0.40, 0.20), (0.62, -0.16), (0.80, 0.11), (1.00, -0.19)]
T0, DT = 0.4, 1.75         # first step start, step length

# --- panel geometry -----------------------------------------------------
PANEL_Y, PANEL_W, PANEL_H = 104, 730, 530
PA_X, PB_X = 60, 810
# panel A: top view of the car, heading = page +x
CAR = (175.0, 420.0)       # axle centre
LEVER = 190.0              # p_x in pixels
SEN = (CAR[0] + LEVER, CAR[1])
VL = 260.0                 # velocity arrow length at full speed
LL = 300.0                 # lateral arrow length at |fraction| = 1
# panel B: the sensor's own frame, x~ horizontal
PO = (890.0, 345.0)        # plot origin
PL = 520.0                 # plot length at full speed
LATP = 0.7                 # plot scale of the removed turn part (schematic)


def fmt(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def text(x, y, s, cls, anchor="start"):
    return f'<text x="{fmt(x)}" y="{fmt(y)}" class="{cls}" text-anchor="{anchor}">{s}</text>'


def sym(x, y, main, sub, cls, sub_dx):
    return text(x, y, main, cls) + (text(x + sub_dx, y + 9, sub, cls + "-s") if sub else "")


def kt(times):
    return ";".join(f"{min(max(t / LOOP, 0.0), 1.0):.4f}" for t in times)


def speed_profile():
    """(time, speed) knots of the piecewise-linear speed ramp, looping to zero."""
    pts = [(0.0, 0.0)]
    prev = 0.0
    for k, (v, _) in enumerate(STEPS):
        t = T0 + k * DT
        pts += [(t, prev), (t + 0.5, v)]
        prev = v
    pts += [(LOOP - 0.5, prev), (LOOP, 0.0)]
    return pts


def anim_attr(attr, fn, pts):
    times = [t for t, _ in pts]
    vals = ";".join(fmt(fn(s)) for _, s in pts)
    return (f'<animate attributeName="{attr}" dur="{LOOP}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{kt(times)}" values="{vals}"/>')


def fade(on, off, peak=1.0, rise=0.18):
    """Opacity 0 -> peak at `on`, back to 0 at `off` (both in seconds)."""
    times = [0.0, on, on + rise, off - rise, off, LOOP]
    vals = [0, 0, peak, peak, 0, 0]
    if off >= LOOP:
        times, vals = [0.0, on, on + rise, LOOP - 0.25, LOOP], [0, 0, peak, peak, 0]
    return (f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" '
            f'calcMode="linear" keyTimes="{kt(times)}" values="{";".join(str(v) for v in vals)}"/>')


def frame(px, title, kicker, notes) -> str:
    out = (f'<rect x="{px}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" rx="14" class="panel"/>'
           + text(px + 32, PANEL_Y + 46, title, "h")
           + text(px + 32, PANEL_Y + 80, kicker, "lbl"))
    for i, line in enumerate(notes):
        out += text(px + 32, PANEL_Y + 470 + 29 * i, line, "note")
    return out


# --- panel A ------------------------------------------------------------
def panel_a(animated: bool) -> str:
    sx, sy = SEN
    out = frame(PA_X, "Sensor mounted at yaw &#968;",
                "the body moves along its heading; the sensor sees it rotated",
                ["blue: the turn part &#969;&#8201;p&#8202;x, read off the rate plot",
                 "of this same sensor and removed first"])
    # chassis
    out += (f'<rect x="{fmt(CAR[0] - 70)}" y="{fmt(CAR[1] - 62)}" width="{fmt(LEVER + 150)}" '
            f'height="124" rx="22" class="body"/>'
            f'<line x1="{fmt(CAR[0])}" y1="{fmt(CAR[1] - 62)}" x2="{fmt(CAR[0])}" '
            f'y2="{fmt(CAR[1] + 62)}" class="axle"/>'
            f'<circle cx="{fmt(CAR[0])}" cy="{fmt(CAR[1])}" r="9" class="ink-fill"/>')
    # heading reference line through the sensor
    out += (f'<line x1="{fmt(sx)}" y1="{fmt(sy)}" x2="{fmt(sx + VL + 60)}" y2="{fmt(sy)}" '
            f'class="rule-dash"/>')
    # the sensor and its own axes, rotated by psi (visually counter-clockwise)
    out += (f'<g transform="translate({fmt(sx)} {fmt(sy)}) rotate({fmt(-PSI)})">'
            f'<line x1="0" y1="0" x2="{fmt(VL + 70)}" y2="0" class="axis-dash"/>'
            f'<line x1="0" y1="0" x2="0" y2="-120" class="axis-dash"/>'
            f'<rect x="-22" y="-16" width="44" height="32" rx="5" class="acc-fill"/>'
            + text(VL + 78, 8, "x&#771;", "syma")
            + text(-10, -130, "y&#771;", "syma")
            + '</g>')
    # psi wedge between heading and sensor x~
    r = 92.0
    out += (f'<path d="M {fmt(sx + r)} {fmt(sy)} A {fmt(r)} {fmt(r)} 0 0 0 '
            f'{fmt(sx + r * CP)} {fmt(sy - r * SP)}" class="fg-thin"/>'
            + text(sx + r + 10, sy - 10, "&#968;", "sym"))

    pts = speed_profile()
    last_v = STEPS[-1][0]
    # vehicle velocity along the heading (length = speed)
    if animated:
        out += (f'<line x1="{fmt(sx)}" y1="{fmt(sy)}" x2="{fmt(sx)}" y2="{fmt(sy)}" '
                f'class="v-ink" marker-end="url(#tip-i)">'
                + anim_attr("x2", lambda s: sx + VL * s, pts) + '</line>')
    else:
        out += (f'<line x1="{fmt(sx)}" y1="{fmt(sy)}" x2="{fmt(sx + VL * last_v)}" y2="{fmt(sy)}" '
                f'class="v-ink" marker-end="url(#tip-i)"/>')
    out += text(sx + VL * 0.72, sy + 40, "v", "symi")
    # the same velocity resolved on the sensor axes (local frame, y down)
    g = f'<g transform="translate({fmt(sx)} {fmt(sy)}) rotate({fmt(-PSI)})">'
    if animated:
        g += (f'<line x1="0" y1="0" x2="0" y2="0" class="comp-strong" marker-end="url(#tip-a)">'
              + anim_attr("x2", lambda s: VL * s * CP, pts) + '</line>')
        g += (f'<line x1="0" y1="0" x2="0" y2="0" class="comp-strong" marker-end="url(#tip-a)">'
              + anim_attr("y2", lambda s: VL * s * SP, pts) + '</line>')
        g += ('<line x1="0" y1="0" x2="0" y2="0" class="ink-dash">'
              + anim_attr("x1", lambda s: VL * s * CP, pts) + anim_attr("x2", lambda s: VL * s * CP, pts)
              + anim_attr("y2", lambda s: VL * s * SP, pts) + '</line>')
        g += ('<line x1="0" y1="0" x2="0" y2="0" class="ink-dash">'
              + anim_attr("y1", lambda s: VL * s * SP, pts) + anim_attr("x2", lambda s: VL * s * CP, pts)
              + anim_attr("y2", lambda s: VL * s * SP, pts) + '</line>')
    else:
        a, b = VL * last_v * CP, VL * last_v * SP
        g += (f'<line x1="0" y1="0" x2="{fmt(a)}" y2="0" class="comp-strong" marker-end="url(#tip-a)"/>'
              f'<line x1="0" y1="0" x2="0" y2="{fmt(b)}" class="comp-strong" marker-end="url(#tip-a)"/>'
              f'<line x1="{fmt(a)}" y1="0" x2="{fmt(a)}" y2="{fmt(b)}" class="ink-dash"/>'
              f'<line x1="0" y1="{fmt(b)}" x2="{fmt(a)}" y2="{fmt(b)}" class="ink-dash"/>')
    g += '</g>'
    out += g
    # component labels (fixed at the full-speed geometry)
    fx, fy = sx + VL * CP * CP + 6, sy - VL * CP * SP - 18
    out += sym(fx - 40, fy - 6, "&#7805;", "x", "syma", 16.0)
    out += sym(sx + 14, sy + VL * SP * CP + 40, "&#7805;", "y", "syma", 16.0)

    # the turn part omega*p_x (vehicle-lateral = page up for a left turn), per step
    for k, (_v, lat) in enumerate(STEPS):
        t = T0 + k * DT
        y2 = sy - LL * lat
        arrow = (f'<line x1="{fmt(sx)}" y1="{fmt(sy)}" x2="{fmt(sx)}" y2="{fmt(y2)}" '
                 f'class="lat" marker-end="url(#tip-b)"/>')
        ly = (sy + y2) / 2 + 8
        lab = (text(sx - 44, ly, "&#969;&#8201;p", "symb", "end")
               + text(sx - 42, ly + 9, "x", "symb-s"))
        if animated:
            out += f'<g opacity="0">{fade(t + 0.15, t + 1.25)}{arrow}{lab}</g>'
        elif k == len(STEPS) - 1:
            out += f'<g opacity="0.35">{arrow}{lab}</g>'
    return out


# --- panel B ------------------------------------------------------------
def panel_b(animated: bool) -> str:
    ox, oy = PO
    out = frame(PB_X, "The sensor's own frame",
                "each dot: one sample, turn part removed",
                ["hollow: raw reading, scattered by the turn part",
                 "filled: turn part removed &#8212; one line through the origin"])
    # axes
    out += (f'<line x1="{fmt(ox)}" y1="{fmt(oy)}" x2="{fmt(ox + PL + 50)}" y2="{fmt(oy)}" '
            f'class="fg-arrow" marker-end="url(#tip)"/>'
            f'<line x1="{fmt(ox)}" y1="{fmt(oy + 200)}" x2="{fmt(ox)}" y2="{fmt(oy - 130)}" '
            f'class="fg-arrow" marker-end="url(#tip)"/>')
    out += sym(ox + PL + 30, oy + 40, "&#7805;", "x", "sym", 16.0)
    out += text(ox + 16, oy - 112, "lateral &#8722; turn part", "lbl")
    # the fitted line and the psi wedge
    ex, ey = ox + (PL + 20) * CP, oy + (PL + 20) * SP
    line = (f'<line x1="{fmt(ox)}" y1="{fmt(oy)}" x2="{fmt(ex)}" y2="{fmt(ey)}" class="fit-acc"/>'
            f'<path d="M {fmt(ox + 150)} {fmt(oy)} A 150 150 0 0 1 {fmt(ox + 150 * CP)} '
            f'{fmt(oy + 150 * SP)}" class="fg-thin"/>'
            + text(ox + 162, oy + 30, "&#968;", "sym")
            + text(ox + PL + 40, oy - 50, "slope = &#8722;tan&#8201;&#968;", "slope", "end"))
    t_line = T0 + len(STEPS) * DT - 0.2
    out += (f'<g opacity="0">{fade(t_line, LOOP)}{line}</g>' if animated else line)

    for k, (v, lat) in enumerate(STEPS):
        t = T0 + k * DT
        fx, fy = ox + PL * v * CP, oy + PL * v * SP               # removed
        rx, ry = fx - PL * LATP * lat * SP, fy - PL * LATP * lat * CP            # raw = + lat*(sin, cos) in y~-up
        drop = (f'<line x1="{fmt(rx)}" y1="{fmt(ry)}" x2="{fmt(fx)}" y2="{fmt(fy)}" '
                f'class="drop" marker-end="url(#tip-b)"/>')
        raw = f'<circle cx="{fmt(rx)}" cy="{fmt(ry)}" r="10" class="raw"/>'
        dot = f'<circle cx="{fmt(fx)}" cy="{fmt(fy)}" r="11" class="acc-fill"/>'
        if animated:
            out += f'<g opacity="0">{fade(t + 0.55, LOOP, peak=0.9)}{raw}</g>'
            out += f'<g opacity="0">{fade(t + 0.95, t + 1.6)}{drop}</g>'
            out += f'<g opacity="0">{fade(t + 1.2, LOOP)}{dot}</g>'
        else:
            out += f'<g opacity="0.9">{raw}</g>{dot}'
    return out


# --- strip --------------------------------------------------------------
def strip() -> str:
    x, y = 60, 660
    out = f'<rect x="{x}" y="{y}" width="1480" height="216" rx="14" class="strip"/>'
    out += text(x + 32, y + 50, "Forward speed is the yaw lever", "h")
    out += text(x + 32, y + 100,
                "&#7805;&#8202;y &#8722; (&#969;&#8201;p&#8202;x &#8722; slip) / cos&#8201;&#968;"
                "  =  &#8722;tan&#8201;&#968; &#183; &#7805;&#8202;x", "eq")
    out += text(x + 32, y + 146,
                "one mount angle, every speed, every turn: one line through the origin", "note")
    out += text(x + 32, y + 180,
                "speed only stretches the arrow &#8212; at zero forward speed the dot sits on the "
                "origin and says nothing about &#968;", "note")
    out += text(x + 1448, y + 50, "no second sensor, no shared clock", "lbl", "end")
    out += text(x + 1448, y + 190, "schematic &#183; &#968; exaggerated", "lbl", "end")
    return out


STYLE = f"""
    .panel {{ fill: {PAPER}; stroke: {RULE}; stroke-width: 1.6; }}
    .strip {{ fill: {SOFT}; stroke: {RULE}; stroke-width: 1.6; }}
    .body {{ fill: {SOFT}; stroke: {RULE}; stroke-width: 1.8; }}
    .axle {{ fill: none; stroke: {INK}; stroke-width: 6; stroke-linecap: round; }}
    .fg-thin {{ fill: none; stroke: {MUTED}; stroke-width: 1.8; }}
    .fg-arrow {{ fill: none; stroke: {MUTED}; stroke-width: 2.4; }}
    .rule-dash {{ fill: none; stroke: {RULE}; stroke-width: 2; stroke-dasharray: 7 6; }}
    .ink-dash {{ fill: none; stroke: {MUTED}; stroke-width: 1.6; stroke-dasharray: 6 6; }}
    .axis-dash {{ fill: none; stroke: {ACC}; stroke-width: 1.8; stroke-dasharray: 8 7; opacity: .75; }}
    .v-ink {{ fill: none; stroke: {INK}; stroke-width: 4.5; }}
    .comp-strong {{ fill: none; stroke: {ACC}; stroke-width: 4; }}
    .lat {{ fill: none; stroke: {LAT}; stroke-width: 4.5; }}
    .drop {{ fill: none; stroke: {LAT}; stroke-width: 2.2; stroke-dasharray: 5 5; }}
    .fit-acc {{ fill: none; stroke: {ACC}; stroke-width: 3; }}
    .raw {{ fill: {PAPER}; stroke: {LAT}; stroke-width: 3; }}
    .ink-fill {{ fill: {INK}; stroke: {PAPER}; stroke-width: 2.5; }}
    .acc-fill {{ fill: {ACC}; stroke: {PAPER}; stroke-width: 2.5; }}
    text {{ font-family: Arial, Helvetica, sans-serif; fill: {INK}; }}
    .h {{ font-size: 33px; font-weight: 700; }}
    .lbl {{ font-size: 22px; fill: {MUTED}; }}
    .note {{ font-size: 24px; fill: {MUTED}; }}
    .eq {{ font-size: 31px; font-weight: 700; fill: {INK}; }}
    .slope {{ font-size: 27px; font-weight: 700; fill: {ACC}; }}
    .sym {{ font-size: 30px; font-weight: 700; fill: {MUTED}; }}
    .sym-s {{ font-size: 21px; font-weight: 700; fill: {MUTED}; }}
    .symi {{ font-size: 30px; font-weight: 700; fill: {INK}; }}
    .syma {{ font-size: 30px; font-weight: 700; fill: {ACC}; }}
    .syma-s {{ font-size: 21px; font-weight: 700; fill: {ACC}; }}
    .symb-s {{ font-size: 19px; font-weight: 700; fill: {LAT}; }}
    .symb {{ font-size: 27px; font-weight: 700; fill: {LAT}; }}
"""

RIBBON_1 = "Take the turn part out, and lateral over longitudinal speed is the mount angle."
RIBBON_2 = "One sensor, its own twist &#8212; the slope of that line is &#8722;tan&#8201;&#968;."
TITLE = "Why the slope of a sensor's lateral against longitudinal speed is its mounting yaw"
DESC = (
    "Schematic. Left: a vehicle seen from above, with a sensor mounted rotated by the yaw angle "
    "psi. The body moves along its own heading; in a turn the sensor also moves sideways by the "
    "turn rate times its longitudinal lever arm, and that part is read off the rate plot of the "
    "same sensor and removed. What remains is the body's forward velocity, which the sensor "
    "resolves on its own rotated axes into a longitudinal and a lateral component. As the speed "
    "changes the arrow stretches but its direction does not. Right: the sensor's own frame. "
    "Each sample drops a dot; raw readings scatter with the turn, and once the turn part is "
    "removed every dot falls on one line through the origin whose angle to the longitudinal axis "
    "is psi, so the slope is minus tan psi. Zero forward speed puts the dot on the origin and "
    "carries no yaw information. No numbers with units appear."
)


def build(animated: bool) -> str:
    defs = ['<defs>']
    for mid, col in (("tip", MUTED), ("tip-i", INK), ("tip-a", ACC), ("tip-b", LAT)):
        defs.append(f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5.5" '
                    f'markerHeight="5.5" orient="auto-start-reverse">'
                    f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{col}"/></marker>')
    defs.append('</defs>')
    body = (text(W / 2, 48, RIBBON_1, "h", "middle") + text(W / 2, 84, RIBBON_2, "lbl", "middle")
            + panel_a(animated) + panel_b(animated) + strip())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
            f'aria-labelledby="pt pd"><title id="pt">{TITLE}</title><desc id="pd">{DESC}</desc>'
            f"<style>{STYLE}</style>{''.join(defs)}"
            f'<rect width="{W}" height="{H}" fill="{PAPER}"/>{body}</svg>')


UNIT_RE = re.compile(r"\d\s*(mm|cm|m|deg|rad|s|Hz|m/s)\b")
REQUIRED = ("Sensor mounted at yaw", "The sensor's own frame", "Forward speed is the yaw lever",
            "one line through the origin", "slope = ")


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
    refs = set(re.findall(r'href="#([A-Za-z0-9_-]+)"', svg)) | set(re.findall(r'url\(#([A-Za-z0-9_-]+)\)', svg))
    for r in sorted(refs - ids):
        problems.append(f"{name}: dangling reference: #{r}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="overwrite existing files")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    targets = {"hero_yaw.svg": build(True), "hero_yaw_static.svg": build(False)}
    problems = [p for n, s in targets.items() for p in check(s, n)]
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
