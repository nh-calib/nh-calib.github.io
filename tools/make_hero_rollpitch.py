#!/usr/bin/env python3
"""Build the S0e hero panel: an animated schematic SVG of motion-plane alignment.

Third companion to make_hero_concept.py (pairwise dp_y) and make_hero_pxyaw.py
(lever arm p_x and yaw offset psi).  This one carries the step that runs before
both of them -- the roll and pitch a single sensor recovers from its own
angular-rate stream.

The mechanism the figure has to carry:
  * a turn on a locally planar surface has exactly one rotation axis, the plane
    normal, and every sensor bolted to the chassis measures that same vector,
  * a sensor mounted with a tilt does not see that vector along its own vertical
    axis -- it sees it spread over all three of its components,
  * pooling the gated turn samples gives one representative axis direction,
  * the rotation that brings that direction back onto the sensor's vertical is
    the mounting roll and pitch; the leftover turn about the axis itself is yaw,
    which this step cannot and does not fix.

Same construction rules as the two earlier panels:
  * no JavaScript -- SMIL only
  * no number carrying a unit anywhere in the text; the panel speaks in symbols
  * pure string building, stock Python only

Two files are written side by side:
  hero_rollpitch.svg          6.0 s loop
  hero_rollpitch_static.svg   the end state of that loop, for prefers-reduced-motion
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

LOOP = 6.0

# --- timeline (fractions of the loop) -----------------------------------
T_SAMPLE_0 = 0.06     # first angular-rate sample lands
T_SAMPLE_D = 0.035    # spacing between samples
T_MEAN = 0.46         # representative axis appears
T_ROT_0 = 0.58        # levelling rotation starts
T_ROT_1 = 0.86        # ... and ends

# --- panel geometry -----------------------------------------------------
MARGIN, GAP = 40, 40
PANEL_W = (W - 2 * MARGIN - 2 * GAP) // 3           # 480
PANEL_Y, PANEL_H = 104, 520
PX = [MARGIN + i * (PANEL_W + GAP) for i in range(3)]

# --- panel A: the physical turn ----------------------------------------
PA_C = (PX[0] + PANEL_W / 2, 418.0)                  # centre of the ground ellipse
PA_RX, PA_RY = 152.0, 54.0
PA_NORMAL = 168.0                                    # length of the plane-normal arrow

# --- panels B and C: the sensor triad ----------------------------------
AX_LEN = 148.0
TILT = 27.0                                          # drawn mounting tilt, exaggerated
SAMPLE_R = 158.0
GHOST_R = SAMPLE_R                                   # the pre-levelling arrow, same length
N_SAMPLES = 11
JITTER = (  # (angle off the mean direction, radius offset) per pooled sample
    (-9.5, 12.0), (6.5, -9.0), (-4.0, -16.0), (8.5, 7.0), (-6.5, -4.0), (1.5, 15.0),
    (4.5, -14.0), (-1.5, 4.0), (7.5, 17.0), (-7.5, -8.0), (2.5, -3.0),
)

PB_O = (PX[1] + PANEL_W / 2 - 18, 432.0)
PC_O = (PX[2] + PANEL_W / 2 - 18, 432.0)

# --- readout strip ------------------------------------------------------
ST_X, ST_Y, ST_W, ST_H = MARGIN, 654, W - 2 * MARGIN, 206


def fmt(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def polar(origin, deg_from_up: float, length: float):
    """Point at `length` from origin, `deg_from_up` degrees off screen-vertical.

    Positive angles lean to the right, matching the drawn mounting tilt.
    """
    a = math.radians(deg_from_up)
    return origin[0] + length * math.sin(a), origin[1] - length * math.cos(a)


def text(x, y, s, cls, anchor="start"):
    return f'<text x="{fmt(x)}" y="{fmt(y)}" class="{cls}" text-anchor="{anchor}">{s}</text>'


def sym(x, y, main, sub="", cls="sym", sub_dx=0.0):
    out = text(x, y, main, cls)
    if sub:
        out += text(x + sub_dx, y + 9, sub, cls + "-s")
    return out


def ellipse_path(c, rx, ry, n=73) -> str:
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / (n - 1)
        pts.append((c[0] + rx * math.cos(t), c[1] + ry * math.sin(t)))
    head = f"M {fmt(pts[0][0])} {fmt(pts[0][1])}"
    return head + "".join(f" L {fmt(x)} {fmt(y)}" for x, y in pts[1:])


def arc_between(origin, a0, a1, radius) -> str:
    """Screen arc from angle a0 to a1 (both measured off vertical, degrees)."""
    p0 = polar(origin, a0, radius)
    p1 = polar(origin, a1, radius)
    sweep = 1 if a1 > a0 else 0
    return (f"M {fmt(p0[0])} {fmt(p0[1])} A {fmt(radius)} {fmt(radius)} 0 0 {sweep} "
            f"{fmt(p1[0])} {fmt(p1[1])}")


def frame(px, title, kicker, lead, notes) -> str:
    """Panel chrome: title, a right-aligned kicker on its own line, and notes."""
    out = (
        f'<rect x="{px}" y="{PANEL_Y}" width="{PANEL_W}" height="{PANEL_H}" rx="14" class="panel"/>'
        + text(px + 28, PANEL_Y + 44, title, "h")
        + text(px + 28, PANEL_Y + 88, lead, "lbl")
        + text(px + PANEL_W - 26, PANEL_Y + 88, kicker, "kick", "end")
    )
    for i, line in enumerate(notes):
        out += text(px + 28, PANEL_Y + 446 + 28 * i, line, "note")
    return out


# --- panel A ------------------------------------------------------------
def panel_a(animated: bool) -> str:
    cx, cy = PA_C
    out = frame(
        PX[0],
        "Planar turn",
        "one axis",
        "vehicle on the plane",
        (
            "On a locally planar surface a turn has",
            "a single rotation axis: the plane normal.",
            "Every sensor on the chassis shares it.",
        ),
    )
    # the ground patch, drawn in perspective
    quad = (f"M {fmt(cx - PA_RX - 44)} {fmt(cy + PA_RY + 40)} "
            f"L {fmt(cx - PA_RX + 22)} {fmt(cy - PA_RY - 34)} "
            f"L {fmt(cx + PA_RX - 22)} {fmt(cy - PA_RY - 34)} "
            f"L {fmt(cx + PA_RX + 44)} {fmt(cy + PA_RY + 40)} Z")
    out += f'<path d="{quad}" class="ground"/>'
    out += f'<path d="{ellipse_path(PA_C, PA_RX, PA_RY)}" class="road" id="paOrbit"/>'

    # the plane normal, and the turn sense wrapped around it
    tipx, tipy = cx, cy - PA_NORMAL
    out += (
        f'<line x1="{fmt(cx)}" y1="{fmt(cy)}" x2="{fmt(tipx)}" y2="{fmt(tipy)}" '
        f'class="omega" marker-end="url(#tip-a)"/>'
        + f'<ellipse cx="{fmt(cx)}" cy="{fmt(cy)}" rx="16" ry="6" class="foot"/>'
        + f'<path d="M {fmt(cx - 46)} {fmt(tipy + 34)} A 46 17 0 0 0 {fmt(cx + 46)} {fmt(tipy + 34)}" '
        f'class="spin" marker-end="url(#tip)"/>'
        + sym(tipx + 18, tipy + 16, "&#969;", "", "syma")
        + text(cx + PA_RX + 34, cy + PA_RY + 34, "ground plane", "lbl", "end")
    )

    car = ('<g><rect x="-17" y="-9" width="34" height="18" rx="6" class="car"/>'
           '<circle cx="12" cy="0" r="4" class="acc-fill"/></g>')
    if animated:
        out += (f'<g><animateMotion dur="{LOOP}s" repeatCount="indefinite" rotate="auto" '
                f'calcMode="linear"><mpath href="#paOrbit" xlink:href="#paOrbit"/>'
                f'</animateMotion>{car}</g>')
    else:
        out += f'<g transform="translate({fmt(cx + PA_RX)},{fmt(cy)}) rotate(90)">{car}</g>'
    return out


# --- panels B and C: shared triad --------------------------------------
def triad() -> str:
    """Sensor axes, drawn upright: the sensor's own coordinate frame."""
    zx, zy = 0.0, -AX_LEN
    xx, xy = AX_LEN * 0.87, AX_LEN * 0.5
    yx, yy = -AX_LEN * 0.87, AX_LEN * 0.5
    return (
        f'<line x1="0" y1="0" x2="{fmt(zx)}" y2="{fmt(zy)}" class="axis" marker-end="url(#tip)"/>'
        f'<line x1="0" y1="0" x2="{fmt(xx)}" y2="{fmt(xy)}" class="axis" marker-end="url(#tip)"/>'
        f'<line x1="0" y1="0" x2="{fmt(yx)}" y2="{fmt(yy)}" class="axis" marker-end="url(#tip)"/>'
        + text(zx - 22, zy + 6, "z", "sym", "end")
        + text(xx + 16, xy + 8, "x", "sym")
        + text(yx - 16, yy + 8, "y", "sym", "end")
        + '<circle cx="0" cy="0" r="8" class="ink-fill"/>'
    )


def samples(origin, animated: bool) -> str:
    out = ""
    for i, (d_ang, d_rad) in enumerate(JITTER[:N_SAMPLES]):
        px, py = polar(origin, TILT + d_ang, SAMPLE_R + d_rad)
        t0 = T_SAMPLE_0 + i * T_SAMPLE_D
        dot = f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="7" class="samp"'
        if animated:
            out += (dot + f' opacity="0"><animate attributeName="opacity" '
                    f'values="0;0;1;1" keyTimes="0;{t0:.3f};{t0 + 0.02:.3f};1" '
                    f'dur="{LOOP}s" calcMode="linear" repeatCount="indefinite"/></circle>')
        else:
            out += dot + "/>"
    return out


def panel_b(animated: bool) -> str:
    ox, oy = PB_O
    out = frame(
        PX[1],
        "Sensor axes",
        "three components",
        "pooled turn samples",
        (
            "A tilted sensor does not see that axis",
            "along its own vertical. The same vector",
            "now has a part on every component.",
        ),
    )
    out += f'<g transform="translate({fmt(ox)},{fmt(oy)})">{triad()}</g>'
    out += samples(PB_O, animated)

    tipx, tipy = polar(PB_O, TILT, SAMPLE_R)
    mean = (
        f'<line x1="{fmt(ox)}" y1="{fmt(oy)}" x2="{fmt(tipx)}" y2="{fmt(tipy)}" '
        f'class="omega" marker-end="url(#tip-a)"/>'
        # the component split: down to the vertical axis, then along it
        + f'<line x1="{fmt(tipx)}" y1="{fmt(tipy)}" x2="{fmt(ox)}" y2="{fmt(tipy)}" class="comp-dash"/>'
        + f'<line x1="{fmt(ox)}" y1="{fmt(oy)}" x2="{fmt(ox)}" y2="{fmt(tipy)}" class="comp-dash"/>'
        + f'<path d="{arc_between(PB_O, 0.0, TILT, 78.0)}" class="fg-thin"/>'
        # the tilt sits outside the wedge, clear of the axis and of the arrow
        + text(polar(PB_O, TILT + 10.0, 94.0)[0], polar(PB_O, TILT + 10.0, 94.0)[1], "tilt", "sym")
        + sym(ox + 12, tipy + 26, "&#969;", "xy", "syma", 19.0)
        + sym(ox - 30, (oy + tipy) / 2 + 8, "&#969;", "z", "syma", 19.0)
    )
    if animated:
        out += (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1" '
                f'keyTimes="0;{T_MEAN:.3f};{T_MEAN + 0.05:.3f};1" dur="{LOOP}s" '
                f'calcMode="linear" repeatCount="indefinite"/>{mean}</g>')
    else:
        out += mean
    return out


def panel_c(animated: bool) -> str:
    ox, oy = PC_O
    out = frame(
        PX[2],
        "Level the stream",
        "two angles",
        "the mounting rotation",
        (
            "One rotation puts that axis back on the",
            "vertical. Its roll and pitch are the mount.",
            "Turning about the axis changes nothing.",
        ),
    )
    out += f'<g transform="translate({fmt(ox)},{fmt(oy)})">{triad()}</g>'

    gx, gy = polar(PC_O, TILT, GHOST_R)
    out += (
        f'<line x1="{fmt(ox)}" y1="{fmt(oy)}" x2="{fmt(gx)}" y2="{fmt(gy)}" class="omega-ghost"/>'
        + text(polar(PC_O, TILT + 15.0, 118.0)[0] + 6, polar(PC_O, TILT + 15.0, 118.0)[1], "before", "lbl-ghost")
    )

    arrow = (f'<line x1="0" y1="0" x2="0" y2="{fmt(-SAMPLE_R)}" class="omega" '
             f'marker-end="url(#tip-a)"/>')
    if animated:
        out += (
            f'<g transform="translate({fmt(ox)},{fmt(oy)})">'
            f'<g><animateTransform attributeName="transform" type="rotate" '
            f'values="{fmt(TILT)};{fmt(TILT)};0;0" '
            f'keyTimes="0;{T_ROT_0:.3f};{T_ROT_1:.3f};1" dur="{LOOP}s" '
            f'calcMode="spline" keySplines="0 0 1 1;.4 0 .2 1;0 0 1 1" '
            f'repeatCount="indefinite"/>{arrow}</g></g>'
        )
    else:
        out += f'<g transform="translate({fmt(ox)},{fmt(oy)})">{arrow}</g>'

    rot_arc = (f'<path d="{arc_between(PC_O, TILT, 2.0, 96.0)}" class="fg-arrow" '
               f'marker-end="url(#tip)"/>')
    caption = sym(ox + 56, oy - 152, "roll, pitch", "", "symi")
    if animated:
        out += (f'<g opacity="0"><animate attributeName="opacity" values="0;0;1;1" '
                f'keyTimes="0;{T_ROT_0:.3f};{T_ROT_0 + 0.06:.3f};1" dur="{LOOP}s" '
                f'calcMode="linear" repeatCount="indefinite"/>{rot_arc}{caption}</g>')
    else:
        out += rot_arc + caption
    return out


# --- readout strip ------------------------------------------------------
CHIPS = (
    ("Roll", "fixed here", True),
    ("Pitch", "fixed here", True),
    ("Yaw", "left open", False),
)


def strip() -> str:
    out = (f'<rect x="{ST_X}" y="{ST_Y}" width="{ST_W}" height="{ST_H}" rx="14" class="panel"/>'
           + text(ST_X + 44, ST_Y + 56, "What one sensor settles by itself", "h"))
    x = ST_X + 44
    for name, state, done in CHIPS:
        cls = "chip-on" if done else "chip-off"
        out += (f'<rect x="{fmt(x)}" y="{fmt(ST_Y + 88)}" width="196" height="76" rx="12" class="{cls}"/>'
                + text(x + 22, ST_Y + 126, name, "chip-h" if done else "chip-h-off")
                + text(x + 22, ST_Y + 152, state, "chip-s"))
        x += 216
    notes = (
        "Aligning one axis can only settle two angles: the turn about the axis",
        "itself leaves it where it was, so yaw waits for the lever-arm step.",
        "No target, no shared field of view, and no clock shared with another",
        "sensor &#8212; only an agreed sign convention for the axis direction.",
    )
    for i, line in enumerate(notes):
        out += text(W - MARGIN - 44, ST_Y + 56 + 34 * i, line, "note", "end")
    return out


# --- assembly -----------------------------------------------------------
STYLE = f"""
    .panel {{ fill: {PAPER}; stroke: {RULE}; stroke-width: 1.6; }}
    .ground {{ fill: {SOFT}; stroke: {RULE}; stroke-width: 1.8; }}
    .road {{ fill: none; stroke: {RULE}; stroke-width: 5; stroke-linecap: round; }}
    .car {{ fill: {PAPER}; stroke: {INK}; stroke-width: 2.4; }}
    .axis {{ fill: none; stroke: {MUTED}; stroke-width: 2.6; }}
    .omega {{ fill: none; stroke: {ACC}; stroke-width: 5; stroke-linecap: round; }}
    .omega-ghost {{ fill: none; stroke: {ACC}; stroke-width: 2.6; stroke-dasharray: 9 8; opacity: .42; }}
    .comp-dash {{ fill: none; stroke: {ACC}; stroke-width: 2; stroke-dasharray: 7 6; opacity: .7; }}
    .fg-thin {{ fill: none; stroke: {MUTED}; stroke-width: 1.8; }}
    .fg-arrow {{ fill: none; stroke: {INK}; stroke-width: 2.6; }}
    .spin {{ fill: none; stroke: {MUTED}; stroke-width: 2.2; }}
    .foot {{ fill: none; stroke: {MUTED}; stroke-width: 2; }}
    .samp {{ fill: {ACC}; stroke: {PAPER}; stroke-width: 2; opacity: .42; }}
    .ink-fill {{ fill: {INK}; stroke: {PAPER}; stroke-width: 2.5; }}
    .acc-fill {{ fill: {ACC}; stroke: none; }}
    .chip-on {{ fill: {SOFT}; stroke: {INK}; stroke-width: 2.2; }}
    .chip-off {{ fill: {PAPER}; stroke: {RULE}; stroke-width: 2.2; stroke-dasharray: 8 7; }}
    text {{ font-family: Arial, Helvetica, sans-serif; fill: {INK}; }}
    .h {{ font-size: 32px; font-weight: 700; }}
    .kick {{ font-size: 24px; font-weight: 700; fill: {MUTED}; }}
    .lbl {{ font-size: 21px; fill: {MUTED}; }}
    .lbl-ghost {{ font-size: 21px; fill: #a9a9a9; }}
    .note {{ font-size: 22px; fill: {MUTED}; }}
    .chip-h {{ font-size: 27px; font-weight: 700; fill: {INK}; }}
    .chip-h-off {{ font-size: 27px; font-weight: 700; fill: {MUTED}; }}
    .chip-s {{ font-size: 20px; fill: {MUTED}; }}
    .sym {{ font-size: 28px; font-weight: 700; fill: {MUTED}; }}
    .sym-s {{ font-size: 20px; font-weight: 700; fill: {MUTED}; }}
    .symi {{ font-size: 28px; font-weight: 700; fill: {INK}; }}
    .symi-s {{ font-size: 20px; font-weight: 700; fill: {INK}; }}
    .syma {{ font-size: 28px; font-weight: 700; fill: {ACC}; }}
    .syma-s {{ font-size: 20px; font-weight: 700; fill: {ACC}; }}
"""

RIBBON_1 = "A turn carries one axis; a tilted sensor spreads it over three components."
RIBBON_2 = ("Rotating that axis back onto the sensor's own vertical is what roll and pitch are "
            "&#8212; one sensor at a time.")

TITLE = "How a single sensor recovers its mounting roll and pitch from turn rate alone"
DESC = (
    "Schematic in three panels. Left: a vehicle driving a circle on a locally planar patch of "
    "ground, with the rotation axis drawn as an arrow along the plane normal and a curved arrow "
    "showing the turn sense. Middle: the same vector seen in the coordinate frame of a sensor "
    "that is mounted with a tilt, so that pooled angular-rate samples from the gated turns "
    "cluster around a direction off the sensor's vertical axis and split into an in-plane part "
    "and a vertical part. Right: the rotation that swings that representative direction back "
    "onto the sensor's vertical axis; its roll and pitch are the mounting angles, while a "
    "rotation about the axis itself leaves the axis unchanged and so yaw is not determined "
    "here. A strip below marks roll and pitch as settled and yaw as left open, and notes that "
    "the step needs no target, no shared field of view and no clock shared with another sensor, "
    "only an agreed sign convention for the axis direction. No numbers with units appear; the "
    "figure is a mechanism sketch, not a measurement."
)


def build(animated: bool) -> str:
    defs = [
        '<defs>',
        f'<marker id="tip" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
        f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{MUTED}"/></marker>',
        f'<marker id="tip-a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
        f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{ACC}"/></marker>',
        '</defs>',
    ]
    body = (
        text(W / 2, 48, RIBBON_1, "h", "middle")
        + text(W / 2, 84, RIBBON_2, "lbl", "middle")
        + panel_a(animated)
        + panel_b(animated)
        + panel_c(animated)
        + strip()
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="rt rd">'
        f'<title id="rt">{TITLE}</title><desc id="rd">{DESC}</desc>'
        f"<style>{STYLE}</style>{''.join(defs)}"
        f'<rect width="{W}" height="{H}" fill="{PAPER}"/>'
        f"{body}</svg>"
    )


UNIT_RE = re.compile(r"\d\s*(mm|cm|m|deg|rad|s|Hz|m/s)\b")
REQUIRED = (
    "Planar turn",
    "Sensor axes",
    "Level the stream",
    "Roll",
    "Pitch",
    "Yaw",
    "ground plane",
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
        "hero_rollpitch.svg": build(animated=True),
        "hero_rollpitch_static.svg": build(animated=False),
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
