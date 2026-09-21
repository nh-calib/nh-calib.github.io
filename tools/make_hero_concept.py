#!/usr/bin/env python3
"""Build the S0a hero panel: an animated, purely schematic SVG of the NH-Calib idea.

Spec: REQ_home_v2.md sections 2.2, 2.4 (R-H1, R-H2, R-H3, R-H5, R-H6, R-H7, R-H8)
and 2.5 (R-TA1 .. R-TA6).

Hard constraints this script enforces by construction:
  * no JavaScript -- animation is SMIL only
  * no number carrying a unit anywhere in the text (R-C1 / spec section 7 item 5);
    the panel speaks in symbols: dI, dp_y, omega, ICR
  * badge strings are the S2 card headings, character for character (spec section 7 item 6)

Two files are written side by side:
  hero_concept.svg          8 s loop, left turn -> switch -> right turn
  hero_concept_static.svg   the end state of that loop, for prefers-reduced-motion

Pure string construction, no third-party imports -- same approach as
make_card_figures.py, so it runs anywhere with a stock Python.
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

# The three badges must equal the S2 card headings in index.html exactly.
BADGES = (
    "No target, no calibration site",
    "No shared field of view",
    "Timing touches one parameter",
)

# --- turn geometry ------------------------------------------------------
# Both panels read left to right so the eye tracks one direction of travel.
# The instantaneous centre of rotation sits above the path on a left turn and
# below it on a right turn -- that flip is the whole point of the figure.
SWEEP = 55.0          # degrees either side of the apex
R_REF = 300.0         # reference-sensor turn radius
D_LAT = 70.0          # exaggerated lateral offset between the two sensors

LEFT_ICR = (425.0, 215.0)
RIGHT_ICR = (1175.0, 545.0)

# --- loop timing (R-TA5): 3.5 s left, 1 s switch, 3.5 s right ------------
LOOP = 8.0
T_LEFT_END = 3.5 / LOOP       # 0.4375
T_RIGHT_START = 4.5 / LOOP    # 0.5625
PATH_LEN = 1000               # nominal pathLength, so dash maths stays integral


def fmt(v: float) -> str:
    """Trim float noise out of the path data."""
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def arc_points(icr, radius, above, n=97):
    """Sample a circular arc travelling left to right.

    above=True puts the centre above the path (left turn), False below it
    (right turn).  Returns screen-space points, y growing downward.
    """
    cx, cy = icr
    pts = []
    for i in range(n):
        phi = math.radians(-SWEEP + (2 * SWEEP) * i / (n - 1))
        x = cx + radius * math.sin(phi)
        y = cy + radius * math.cos(phi) if above else cy - radius * math.cos(phi)
        pts.append((x, y))
    return pts


def path_d(pts) -> str:
    head = f"M {fmt(pts[0][0])} {fmt(pts[0][1])}"
    return head + "".join(f" L {fmt(x)} {fmt(y)}" for x, y in pts[1:])


def arc_endpoint(icr, radius, above, phi_deg):
    cx, cy = icr
    phi = math.radians(phi_deg)
    x = cx + radius * math.sin(phi)
    y = cy + radius * math.cos(phi) if above else cy - radius * math.cos(phi)
    # heading is the tangent; on a left turn the heading rotates counter-clockwise
    heading = -phi_deg if above else phi_deg
    return x, y, heading


# --- small drawing helpers ---------------------------------------------
def text(x, y, s, cls, anchor="start"):
    return f'<text x="{fmt(x)}" y="{fmt(y)}" class="{cls}" text-anchor="{anchor}">{s}</text>'


def vehicle_marker(tag):
    """Two sensors on a common axle plus a heading arrow.

    Deliberately not a car outline: at this lateral exaggeration a to-scale body
    would swamp the panel, and the claim is about two points on one chassis.
    """
    return (
        f'<g id="{tag}">'
        f'<line x1="0" y1="0" x2="0" y2="{fmt(-D_LAT)}" class="axle"/>'
        f'<line x1="16" y1="{fmt(-D_LAT / 2)}" x2="52" y2="{fmt(-D_LAT / 2)}" class="fg-arrow" marker-end="url(#tip)"/>'
        f'<circle cx="0" cy="0" r="11" class="ink-fill"/>'
        f'<circle cx="0" cy="{fmt(-D_LAT)}" r="11" class="acc-fill"/>'
        f"</g>"
    )


def icr_marker(icr, label_dx, label_dy):
    cx, cy = icr
    return (
        f'<g class="icr">'
        f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="9" class="icr-dot"/>'
        f'<line x1="{fmt(cx - 22)}" y1="{fmt(cy)}" x2="{fmt(cx + 22)}" y2="{fmt(cy)}" class="fg-thin"/>'
        f'<line x1="{fmt(cx)}" y1="{fmt(cy - 22)}" x2="{fmt(cx)}" y2="{fmt(cy + 22)}" class="fg-thin"/>'
        f"{text(cx + label_dx, cy + label_dy, 'ICR', 'sym', 'middle')}"
        f"</g>"
    )


def omega_arc(icr, clockwise):
    """A short curved arrow around the ICR, labelled with the yaw-rate symbol."""
    cx, cy = icr
    r = 54.0
    # SVG y grows downward, so increasing polar angle sweeps clockwise on screen
    a0, a1 = (205.0, 335.0) if clockwise else (335.0, 205.0)
    p0 = (cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0)))
    p1 = (cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1)))
    sweep = 1 if clockwise else 0
    d = f"M {fmt(p0[0])} {fmt(p0[1])} A {fmt(r)} {fmt(r)} 0 0 {sweep} {fmt(p1[0])} {fmt(p1[1])}"
    return (
        f'<path d="{d}" class="fg-arrow" marker-end="url(#tip)"/>'
        + text(cx, cy - r - 18, "&#969;", "sym", "middle")
    )


def lateral_bracket(icr, above):
    """Draw the radius line and mark the radius difference as dp_y (R-H7)."""
    cx, cy = icr
    r_far = R_REF
    r_near = R_REF - D_LAT if above else R_REF
    r_other = R_REF - D_LAT if above else R_REF + D_LAT
    sign = 1 if above else -1
    y_ref = cy + sign * r_far
    y_tgt = cy + sign * r_other
    y_lo, y_hi = sorted((y_ref, y_tgt))
    radius_end = cy + sign * max(r_far, r_other)
    parts = [
        f'<line x1="{fmt(cx)}" y1="{fmt(cy)}" x2="{fmt(cx)}" y2="{fmt(radius_end)}" class="rule-dash"/>',
        f'<line x1="{fmt(cx)}" y1="{fmt(y_lo)}" x2="{fmt(cx)}" y2="{fmt(y_hi)}" '
        f'class="bracket" marker-start="url(#tip-s)" marker-end="url(#tip)"/>',
        text(cx + 18, (y_lo + y_hi) / 2 + 9, "&#916;p", "sym", "start"),
        f'<text x="{fmt(cx + 18 + 38)}" y="{fmt((y_lo + y_hi) / 2 + 17)}" class="sym-sub">y</text>',
    ]
    _ = r_near
    return "".join(parts)


# --- panels -------------------------------------------------------------
def panel(idx, animated):
    """Build one turn panel.  idx 0 = left turn, idx 1 = right turn."""
    left = idx == 0
    icr = LEFT_ICR if left else RIGHT_ICR
    above = left                      # centre above the path on a left turn
    r_tgt = R_REF - D_LAT if left else R_REF + D_LAT

    px = 60 if left else 810
    frame = (
        f'<rect x="{px}" y="100" width="730" height="530" rx="14" class="panel"/>'
        + text(px + 32, 152, "Left turn" if left else "Right turn", "h")
    )

    if left:
        # the legend sits in the left panel only; repeating it would just add ink
        ly = 596
        frame += (
            f'<line x1="{px + 32}" y1="{ly}" x2="{px + 74}" y2="{ly}" class="trace-ref"/>'
            + text(px + 86, ly + 8, "reference sensor", "lbl")
            + f'<line x1="{px + 300}" y1="{ly}" x2="{px + 342}" y2="{ly}" class="trace-tgt"/>'
            + text(px + 354, ly + 8, "target sensor", "lbl")
        )

    ref_pts = arc_points(icr, R_REF, above)
    tgt_pts = arc_points(icr, r_tgt, above)
    ref_id = f"p{idx}ref"
    tgt_id = f"p{idx}tgt"

    traces = (
        f'<path id="{ref_id}" d="{path_d(ref_pts)}" class="trace-ref" pathLength="{PATH_LEN}"/>'
        f'<path id="{tgt_id}" d="{path_d(tgt_pts)}" class="trace-tgt" pathLength="{PATH_LEN}"/>'
    )

    if animated:
        # dash the traces on: the left panel draws first, the right one after the switch
        if left:
            vals, keys = f"{PATH_LEN};0;0", f"0;{T_LEFT_END};1"
        else:
            vals, keys = f"{PATH_LEN};{PATH_LEN};0", f"0;{T_RIGHT_START};1"
        anim = (
            f'<animate attributeName="stroke-dashoffset" values="{vals}" keyTimes="{keys}" '
            f'dur="{LOOP}s" calcMode="linear" repeatCount="indefinite"/>'
        )
        traces = (
            f'<path id="{ref_id}" d="{path_d(ref_pts)}" class="trace-ref" pathLength="{PATH_LEN}" '
            f'stroke-dasharray="{PATH_LEN}" stroke-dashoffset="{PATH_LEN}">{anim}</path>'
            f'<path id="{tgt_id}" d="{path_d(tgt_pts)}" class="trace-tgt" pathLength="{PATH_LEN}" '
            f'stroke-dasharray="{PATH_LEN}" stroke-dashoffset="{PATH_LEN}">{anim}</path>'
        )

    decor = (
        icr_marker(icr, 0, 46)
        + omega_arc(icr, clockwise=not left)
        + lateral_bracket(icr, above)
    )
    if animated and not left:
        # the right scene has not happened yet during the first half of the loop
        decor = (
            f'<g opacity="0">'
            f'<animate attributeName="opacity" values="0;0;1;1" '
            f'keyTimes="0;{T_RIGHT_START - 0.06};{T_RIGHT_START};1" '
            f'dur="{LOOP}s" calcMode="linear" repeatCount="indefinite"/>'
            f"{decor}</g>"
        )

    # the vehicle rides the reference path, so its two sensor dots trace the two arcs
    if animated:
        if left:
            kp, kt = "0;1;1", f"0;{T_LEFT_END};1"
            fade = ""
        else:
            kp, kt = "0;0;1", f"0;{T_RIGHT_START};1"
            fade = (
                f'<animate attributeName="opacity" values="0;0;1;1" '
                f'keyTimes="0;{T_RIGHT_START - 0.004};{T_RIGHT_START};1" '
                f'dur="{LOOP}s" calcMode="discrete" repeatCount="indefinite"/>'
            )
        veh = (
            f'<g class="veh">{fade}'
            f'<use href="#veh{idx}"/>'
            f'<animateMotion dur="{LOOP}s" repeatCount="indefinite" rotate="auto" '
            f'calcMode="linear" keyPoints="{kp}" keyTimes="{kt}">'
            f'<mpath href="#{ref_id}"/></animateMotion>'
            f"</g>"
        )
    else:
        x, y, ang = arc_endpoint(icr, R_REF, above, SWEEP)
        veh = f'<g transform="translate({fmt(x)},{fmt(y)}) rotate({fmt(ang)})"><use href="#veh{idx}"/></g>'

    return frame + decor + traces + veh


# --- the delta-I readout strip -----------------------------------------
def gauge(animated):
    cx, cy = 800.0, 768.0
    half, bh = 230.0, 44.0
    strip = (
        f'<rect x="60" y="656" width="1480" height="216" rx="14" class="panel"/>'
        + text(110, 722, "&#916;I", "big")
        + text(110, 768, "accumulated path-length difference", "lbl")
        + text(110, 802, "between the two sensor paths", "lbl")
        + f'<line x1="{fmt(cx)}" y1="{fmt(cy - bh - 18)}" x2="{fmt(cx)}" y2="{fmt(cy + bh + 18)}" class="fg-thin"/>'
        + text(cx, cy - bh - 28, "0", "lbl", "middle")
        + f'<line x1="{fmt(cx - half)}" y1="{fmt(cy)}" x2="{fmt(cx + half)}" y2="{fmt(cy)}" class="rule-line"/>'
    )

    if animated:
        neg = (
            f'<rect y="{fmt(cy - bh)}" height="{fmt(bh)}" class="bar-neg" x="{fmt(cx)}" width="0">'
            f'<animate attributeName="x" values="{fmt(cx)};{fmt(cx - half)};{fmt(cx - half)}" '
            f'keyTimes="0;{T_LEFT_END};1" dur="{LOOP}s" calcMode="linear" repeatCount="indefinite"/>'
            f'<animate attributeName="width" values="0;{fmt(half)};{fmt(half)}" '
            f'keyTimes="0;{T_LEFT_END};1" dur="{LOOP}s" calcMode="linear" repeatCount="indefinite"/>'
            f"</rect>"
        )
        pos = (
            f'<rect y="{fmt(cy)}" height="{fmt(bh)}" class="bar-pos" x="{fmt(cx)}" width="0">'
            f'<animate attributeName="width" values="0;0;{fmt(half)}" '
            f'keyTimes="0;{T_RIGHT_START};1" dur="{LOOP}s" calcMode="linear" repeatCount="indefinite"/>'
            f"</rect>"
        )
    else:
        neg = f'<rect x="{fmt(cx - half)}" y="{fmt(cy - bh)}" width="{fmt(half)}" height="{fmt(bh)}" class="bar-neg"/>'
        pos = f'<rect x="{fmt(cx)}" y="{fmt(cy)}" width="{fmt(half)}" height="{fmt(bh)}" class="bar-pos"/>'

    labels = (
        text(cx - half, cy - bh - 28, "&#8722;&#8195;left turn", "lbl", "start")
        + text(cx + half, cy + bh + 34, "right turn&#8195;+", "lbl", "end")
    )

    note = (
        text(1500, 742, "&#916;I grows with the turn,", "note", "end")
        + text(1500, 782, "and its sign follows the", "note", "end")
        + text(1500, 822, "turn direction.", "note", "end")
    )
    return strip + neg + pos + labels + note


# --- badges -------------------------------------------------------------
def badges():
    # advance widths are approximated from Arial bold metrics; the pills are
    # centred on their own text so a small estimate error stays invisible
    def width_of(s):
        wide = sum(1 for ch in s if ch in "mMwW")
        narrow = sum(1 for ch in s if ch in "iljItf,.' ")
        return 15.2 * len(s) + 5.0 * wide - 6.4 * narrow

    pads, gap = 30.0, 26.0
    widths = [width_of(b) + 2 * pads for b in BADGES]
    total = sum(widths) + gap * (len(widths) - 1)
    x = (W - total) / 2
    out = []
    for b, bw in zip(BADGES, widths):
        out.append(
            f'<rect x="{fmt(x)}" y="24" width="{fmt(bw)}" height="52" rx="26" class="badge"/>'
            + text(x + bw / 2, 59, b, "badge-t", "middle")
        )
        x += bw + gap
    return "".join(out)


# --- assembly -----------------------------------------------------------
STYLE = f"""
    .panel {{ fill: {PAPER}; stroke: {RULE}; stroke-width: 1.6; }}
    .fg-thin {{ fill: none; stroke: {MUTED}; stroke-width: 1.8; }}
    .fg-arrow {{ fill: none; stroke: {MUTED}; stroke-width: 2.4; }}
    .rule-line {{ fill: none; stroke: {RULE}; stroke-width: 2; }}
    .rule-dash {{ fill: none; stroke: {RULE}; stroke-width: 2; stroke-dasharray: 7 6; }}
    .bracket {{ fill: none; stroke: {INK}; stroke-width: 2.4; }}
    .axle {{ fill: none; stroke: {INK}; stroke-width: 6; stroke-linecap: round; }}
    .trace-ref {{ fill: none; stroke: {INK}; stroke-width: 5; stroke-linecap: round; }}
    .trace-tgt {{ fill: none; stroke: {ACC}; stroke-width: 5; stroke-linecap: round; }}
    .ink-fill {{ fill: {INK}; stroke: {PAPER}; stroke-width: 2.5; }}
    .acc-fill {{ fill: {ACC}; stroke: {PAPER}; stroke-width: 2.5; }}
    .icr-dot {{ fill: {PAPER}; stroke: {MUTED}; stroke-width: 3; }}
    .badge {{ fill: {SOFT}; stroke: {RULE}; stroke-width: 1.4; }}
    .bar-neg {{ fill: {INK}; }}
    .bar-pos {{ fill: {ACC}; }}
    text {{ font-family: Arial, Helvetica, sans-serif; fill: {INK}; }}
    .badge-t {{ font-size: 27px; font-weight: 700; letter-spacing: .01em; }}
    .h {{ font-size: 33px; font-weight: 700; }}
    .lbl {{ font-size: 24px; fill: {MUTED}; }}
    .note {{ font-size: 26px; fill: {MUTED}; }}
    .sym {{ font-size: 30px; font-weight: 700; fill: {MUTED}; }}
    .sym-sub {{ font-size: 21px; font-weight: 700; fill: {MUTED};
                font-family: Arial, Helvetica, sans-serif; }}
    .big {{ font-size: 54px; font-weight: 700; }}
    .sym-sub-big {{ font-size: 26px; fill: {MUTED};
                    font-family: Arial, Helvetica, sans-serif; }}
"""

TITLE = "How NH-Calib reads a mounting offset out of a turn"
DESC = (
    "Schematic. Two panels show the same vehicle driving a left turn and a right turn. "
    "In each panel the reference sensor and the target sensor trace arcs of different radius "
    "about a shared instantaneous centre of rotation, and the difference of those radii is the "
    "lateral mounting offset. A bar below shows the accumulated path-length difference growing "
    "and reversing sign between the two turns. No numbers with units appear: the figure is a "
    "mechanism sketch, not a measurement."
)


def build(animated: bool) -> str:
    defs = (
        "<defs>"
        f'<marker id="tip" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
        f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{MUTED}"/></marker>'
        f'<marker id="tip-s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
        f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{INK}"/></marker>'
        + vehicle_marker("veh0")
        + vehicle_marker("veh1")
        + "</defs>"
    )
    body = badges() + panel(0, animated) + panel(1, animated) + gauge(animated)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {W} {H}" role="img" aria-labelledby="ht hd">'
        f'<title id="ht">{TITLE}</title><desc id="hd">{DESC}</desc>'
        f"<style>{STYLE}</style>{defs}"
        f'<rect width="{W}" height="{H}" fill="{PAPER}"/>'
        f"{body}</svg>"
    )


UNIT_RE = re.compile(r"\d\s*(mm|cm|m|deg|rad|s|Hz|m/s)\b")


def check(svg: str, name: str) -> list[str]:
    """Guard the two properties the spec checks mechanically."""
    problems = []
    texts = re.findall(r"<text[^>]*>(.*?)</text>", svg, flags=re.S)
    for t in texts:
        if UNIT_RE.search(t):
            problems.append(f"{name}: unit-bearing number in text: {t!r}")
    joined = " ".join(texts)
    for b in BADGES:
        if b not in joined:
            problems.append(f"{name}: badge string missing: {b!r}")
    if "<script" in svg or "onload=" in svg:
        problems.append(f"{name}: script content present")
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
        "hero_concept.svg": build(animated=True),
        "hero_concept_static.svg": build(animated=False),
    }

    problems = []
    for name, svg in targets.items():
        problems += check(svg, name)
    if problems:
        print("REFUSING TO WRITE -- spec checks failed:")
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
