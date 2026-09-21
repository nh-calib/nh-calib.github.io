#!/usr/bin/env python3
"""Generate the three schematic card figures for the landing-page section
"Where existing calibration stops".

Deterministic hand-authored SVG (no raster, no external assets) so the figures
stay crisp at any width and can be regenerated after a palette change.

    python tools/make_card_figures.py

Writes assets/cards/card1-no-target.svg, card2-no-shared-fov.svg,
card3-alignment-scope.svg.
"""
import argparse
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "cards"

INK = "#191919"
MUTED = "#666666"
RULE = "#d8d8d8"
SOFT = "#f5f5f3"
ACCENT = "#a52e29"

W, H = 640, 360

STYLE = f"""
  <style>
    .fg {{ fill: none; stroke: {INK}; stroke-width: 1.6; }}
    .fg-thin {{ fill: none; stroke: {MUTED}; stroke-width: 1.2; }}
    .rule {{ fill: none; stroke: {RULE}; stroke-width: 1.2; }}
    .acc {{ fill: none; stroke: {ACCENT}; stroke-width: 1.8; }}
    .dash {{ stroke-dasharray: 5 4; }}
    .dot {{ stroke-dasharray: 2 3; }}
    .soft {{ fill: {SOFT}; stroke: none; }}
    .body {{ fill: #ffffff; stroke: {INK}; stroke-width: 1.6; }}
    .ink-fill {{ fill: {INK}; stroke: none; }}
    .acc-fill {{ fill: {ACCENT}; stroke: none; }}
    text {{ font-family: Arial, Helvetica, sans-serif; fill: {INK}; }}
    .h {{ font-size: 15px; font-weight: 700; }}
    .h-acc {{ font-size: 15px; font-weight: 700; fill: {ACCENT}; }}
    .lbl {{ font-size: 12.5px; fill: {MUTED}; }}
    .lbl-ink {{ font-size: 12.5px; fill: {INK}; }}
    .tag {{ font-size: 11.5px; font-weight: 700; letter-spacing: .06em; fill: {MUTED}; }}
    .mono {{ font-size: 13px; font-weight: 700; }}
  </style>
"""


def svg(title: str, desc: str, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'role="img" aria-labelledby="t d">\n'
        f'  <title id="t">{title}</title>\n'
        f'  <desc id="d">{desc}</desc>\n'
        f"{STYLE}"
        f"{body}\n"
        f"</svg>\n"
    )


def divider() -> str:
    return f'  <line class="rule" x1="320" y1="18" x2="320" y2="342" />\n'


def cross(cx: float, cy: float, r: float = 9) -> str:
    d = r * 0.5
    return (
        f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{ACCENT}" stroke-width="1.6" />\n'
        f'  <path class="acc" d="M {cx-d} {cy-d} L {cx+d} {cy+d} M {cx+d} {cy-d} L {cx-d} {cy+d}" />\n'
    )


def check(cx: float, cy: float, r: float = 9) -> str:
    return (
        f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{INK}" stroke-width="1.6" />\n'
        f'  <path class="fg" d="M {cx-4.5} {cy+0.3} L {cx-1.2} {cy+3.6} L {cx+4.8} {cy-3.8}" />\n'
    )


def car_top(cx: float, cy: float, rot: float = 0, scale: float = 1.0) -> str:
    """Top-view car glyph, nose pointing -y before rotation."""
    g = (
        f'  <g transform="translate({cx} {cy}) rotate({rot}) scale({scale})">\n'
        f'    <rect class="body" x="-17" y="-29" width="34" height="58" rx="8" />\n'
        f'    <path class="fg-thin" d="M -12 -14 L 12 -14 M -12 8 L 12 8" />\n'
        f'    <rect class="ink-fill" x="-21" y="-22" width="5" height="11" rx="2" />\n'
        f'    <rect class="ink-fill" x="16" y="-22" width="5" height="11" rx="2" />\n'
        f'    <rect class="ink-fill" x="-21" y="12" width="5" height="11" rx="2" />\n'
        f'    <rect class="ink-fill" x="16" y="12" width="5" height="11" rx="2" />\n'
        f"  </g>\n"
    )
    return g


# ---------------------------------------------------------------- card 1
def card1() -> str:
    b = []
    b.append('  <text class="tag" x="20" y="26">CONVENTIONAL</text>')
    b.append('  <text class="h" x="20" y="48">A prepared target scene</text>')

    # --- checkerboard on a tripod
    bx, by, bw, bh = 186, 96, 96, 72
    b.append(f'  <rect class="fg" x="{bx}" y="{by}" width="{bw}" height="{bh}" />')
    cw, ch = bw / 4, bh / 3
    for r in range(3):
        for c in range(4):
            if (r + c) % 2 == 0:
                b.append(
                    f'  <rect class="ink-fill" x="{bx + c*cw}" y="{by + r*ch}" '
                    f'width="{cw}" height="{ch}" />'
                )
    b.append(f'  <path class="fg" d="M 234 168 L 234 214" />')
    b.append(f'  <path class="fg" d="M 234 214 L 210 286 M 234 214 L 258 286 M 234 214 L 240 284" />')

    # --- sensor with dashed rays onto the board
    b.append('  <rect class="body" x="52" y="176" width="40" height="27" rx="4" />')
    b.append('  <circle class="ink-fill" cx="72" cy="189" r="5" />')
    b.append('  <text class="lbl" x="72" y="222" text-anchor="middle">sensor</text>')
    b.append('  <path class="fg-thin dash" d="M 92 182 L 186 100 M 92 190 L 186 168 M 92 198 L 186 136" />')

    # --- manual measurement callout
    b.append('  <path class="fg-thin" d="M 60 254 L 226 254" />')
    b.append('  <path class="fg-thin" d="M 60 248 L 60 260 M 226 248 L 226 260" />')
    b.append('  <text class="lbl" x="143" y="245" text-anchor="middle">measured placement</text>')
    b.append(f'  <line class="rule" x1="20" y1="300" x2="300" y2="300" />')
    b.append('  <text class="lbl" x="20" y="322">Calibration room, operator, re-run after</text>')
    b.append('  <text class="lbl" x="20" y="338">every mount change.</text>')
    b.append(cross(288, 313))

    b.append(divider())

    # --- right: ours
    b.append('  <text class="tag" x="350" y="26" fill="' + ACCENT + '">NH-CALIB</text>')
    b.append('  <text class="h" x="350" y="48">Any drive that turns</text>')

    road = "M 436 278 C 436 224 458 182 508 162 C 552 144 592 144 620 136"
    b.append(f'  <path d="{road}" fill="none" stroke="{SOFT}" stroke-width="26" stroke-linecap="round" />')
    b.append(f'  <path d="{road}" fill="none" stroke="{MUTED}" stroke-width="1.2" stroke-dasharray="6 5" />')
    b.append(car_top(436, 266, 2, 0.60))
    b.append(car_top(474, 190, 33, 0.60))
    b.append(car_top(552, 150, 76, 0.60))
    b.append('  <text class="lbl" x="350" y="194">no target</text>')
    b.append('  <text class="lbl" x="350" y="214">no operator</text>')
    b.append('  <text class="lbl" x="350" y="234">no site setup</text>')
    b.append(f'  <line class="rule" x1="350" y1="300" x2="620" y2="300" />')
    b.append('  <text class="lbl" x="350" y="322">Ordinary driving logs already contain the</text>')
    b.append('  <text class="lbl" x="350" y="338">turning motion the estimator needs.</text>')
    b.append(check(608, 313))

    defs = (
        '  <defs><marker id="ar" viewBox="0 0 8 8" refX="4" refY="4" markerWidth="5" '
        f'markerHeight="5" orient="auto"><path d="M 0 1 L 6 4 L 0 7 z" fill="{MUTED}" />'
        "</marker></defs>\n"
    )
    return svg(
        "Target-based calibration versus NH-Calib",
        "Left: a sensor observing a checkerboard target on a tripod inside a calibration room, "
        "marked as a limitation. Right: a vehicle driving a turning trajectory on an ordinary road, "
        "marked as the NH-Calib input.",
        defs + "\n".join(b),
    )


# ---------------------------------------------------------------- card 2
def card2() -> str:
    b = []
    b.append('  <text class="tag" x="20" y="26">CONVENTIONAL</text>')
    b.append('  <text class="h" x="20" y="48">Needs co-visible structure</text>')

    # vehicle with two opposite-facing sensors
    b.append(car_top(168, 196, 0, 1.15))
    # front sensor wedge (up)
    b.append(f'  <path class="soft" d="M 168 160 L 92 74 L 244 74 z" />')
    b.append(f'  <path class="fg-thin dot" d="M 168 160 L 92 74 M 168 160 L 244 74" />')
    b.append('  <circle class="acc-fill" cx="168" cy="160" r="4.5" />')
    b.append('  <text class="lbl-ink" x="168" y="66" text-anchor="middle">sensor A field of view</text>')
    # rear sensor wedge (down)
    b.append(f'  <path class="soft" d="M 168 232 L 100 282 L 236 282 z" />')
    b.append(f'  <path class="fg-thin dot" d="M 168 232 L 100 282 M 168 232 L 236 282" />')
    b.append('  <circle class="acc-fill" cx="168" cy="232" r="4.5" />')
    b.append('  <text class="lbl-ink" x="168" y="296" text-anchor="middle">sensor B field of view</text>')
    # empty intersection callout
    b.append(f'  <circle class="acc dash" cx="168" cy="196" r="27" />')
    b.append(cross(168, 196, 8))
    b.append(f'  <path class="fg-thin" d="M 196 196 L 268 196" />')
    b.append('  <text class="lbl" x="272" y="192">no shared</text>')
    b.append('  <text class="lbl" x="272" y="208">points</text>')
    b.append(f'  <line class="rule" x1="20" y1="308" x2="300" y2="308" />')
    b.append('  <text class="lbl" x="20" y="330">Registration and overlap-based methods</text>')
    b.append('  <text class="lbl" x="20" y="346">need a scene both sensors can see.</text>')
    b.append(cross(288, 322))

    b.append(divider())

    # ours
    b.append('  <text class="tag" x="350" y="26" fill="' + ACCENT + '">NH-CALIB</text>')
    b.append('  <text class="h" x="350" y="48">Compare motions, not views</text>')

    pa = "M 390 238 C 390 196 416 168 466 150 C 512 134 562 134 600 130"
    pb = "M 390 277 C 392 232 424 196 474 178 C 520 162 570 160 614 154"
    b.append(f'  <path d="{pa}" fill="none" stroke="{INK}" stroke-width="1.6" stroke-dasharray="6 5" />')
    b.append(f'  <path d="{pb}" fill="none" stroke="{ACCENT}" stroke-width="1.6" stroke-dasharray="6 5" />')
    b.append(car_top(390, 258, 2, 0.66))
    b.append('  <circle class="ink-fill" cx="390" cy="239" r="4.5" />')
    b.append('  <circle class="acc-fill" cx="390" cy="277" r="4.5" />')
    b.append('  <text class="lbl-ink" x="366" y="236" text-anchor="end">A</text>')
    b.append(f'  <text class="lbl" x="366" y="282" text-anchor="end" fill="{ACCENT}">B</text>')
    b.append('  <circle class="ink-fill" cx="600" cy="130" r="4.5" />')
    b.append('  <circle class="acc-fill" cx="614" cy="154" r="4.5" />')
    b.append('  <text class="lbl-ink" x="556" y="118">motion of A</text>')
    b.append(f'  <text class="lbl" x="558" y="174" fill="{ACCENT}">motion of B</text>')

    # the offset between the two motions is the quantity being solved
    b.append(f'  <path class="acc" d="M 468 148 L 478 177" />')
    b.append(f'  <path class="acc" d="M 463 145 L 473 141 M 473 180 L 483 176" />')
    b.append('  <text class="lbl-ink" x="450" y="210">mounting offset</text>')

    b.append(f'  <line class="rule" x1="350" y1="308" x2="620" y2="308" />')
    b.append('  <text class="lbl" x="350" y="330">Two ego-motions of one rigid body differ</text>')
    b.append('  <text class="lbl" x="350" y="346">only by the extrinsic, not by a shared view.</text>')
    b.append(check(608, 322))

    defs = (
        '  <defs><marker id="ar2" viewBox="0 0 8 8" refX="5" refY="4" markerWidth="5.5" '
        f'markerHeight="5.5" orient="auto"><path d="M 0 1 L 6 4 L 0 7 z" fill="{ACCENT}" />'
        "</marker></defs>\n"
    )
    return svg(
        "Non-overlapping fields of view",
        "Left: two sensors on one vehicle pointing in opposite directions, their fields of view do not "
        "intersect, so no common points exist. Right: the same two sensors, each measuring its own "
        "ego-motion, linked by the single rigid chassis motion.",
        defs + "\n".join(b),
    )


# ---------------------------------------------------------------- card 3
def card3() -> str:
    b = []
    b.append('  <text class="tag" x="20" y="26">DEGREES OF FREEDOM</text>')
    b.append('  <text class="h" x="20" y="48">Where inter-sensor timing enters</text>')

    chips = [
        ("X", "longitudinal", "local"),
        ("Roll", "motion plane", "local"),
        ("Pitch", "motion plane", "local"),
        ("Yaw", "heading", "local"),
        ("Y", "lateral", "aligned"),
        ("Z", "height", "none"),
    ]
    x0, y0, cw, ch, gx, gy = 20, 74, 190, 64, 15, 14
    for i, (name, sub, kind) in enumerate(chips):
        col, row = i % 3, i // 3
        x = x0 + col * (cw + gx)
        y = y0 + row * (ch + gy)
        if kind == "local":
            b.append(f'  <rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="7" fill="{SOFT}" stroke="{RULE}" stroke-width="1.2" />')
            b.append(f'  <text class="mono" x="{x+14}" y="{y+27}">{name}</text>')
            b.append(f'  <text class="lbl" x="{x+14}" y="{y+46}">{sub} &#183; sensor-local</text>')
            b.append(check(x + cw - 20, y + 20, 8))
        elif kind == "aligned":
            b.append(f'  <rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="7" fill="#fff" stroke="{ACCENT}" stroke-width="2" />')
            b.append(f'  <text class="mono" x="{x+14}" y="{y+27}" fill="{ACCENT}">{name}</text>')
            b.append(f'  <text class="lbl" x="{x+14}" y="{y+46}">{sub} &#183; needs alignment</text>')
            # clock glyph
            ccx, ccy = x + cw - 20, y + 20
            b.append(f'  <circle cx="{ccx}" cy="{ccy}" r="9" fill="none" stroke="{ACCENT}" stroke-width="1.6" />')
            b.append(f'  <path class="acc" d="M {ccx} {ccy-5} L {ccx} {ccy} L {ccx+4} {ccy+3}" />')
        else:
            b.append(f'  <rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="7" fill="none" stroke="{RULE}" stroke-width="1.2" stroke-dasharray="5 4" />')
            b.append(f'  <text class="mono" x="{x+14}" y="{y+27}" fill="{MUTED}">{name}</text>')
            b.append(f'  <text class="lbl" x="{x+14}" y="{y+46}">{sub} &#183; not observable</text>')

    # summary strip
    sy = 240
    b.append(f'  <line class="rule" x1="20" y1="{sy}" x2="620" y2="{sy}" />')
    b.append(f'  <text class="lbl-ink" x="20" y="{sy+26}">Of the five degrees of freedom this motion makes observable,</text>')
    b.append(f'  <text class="h-acc" x="20" y="{sy+48}">exactly one &#8212; relative Y &#8212; is coupled to inter-sensor time alignment.</text>')
    b.append(f'  <text class="lbl" x="20" y="{sy+72}">Z stays unobservable because planar driving never excites it &#8212; a property of the motion,</text>')
    b.append(f'  <text class="lbl" x="20" y="{sy+90}">not an advantage of the method.</text>')

    return svg(
        "Which calibration parameters depend on inter-sensor time alignment",
        "Six chips for the six rigid-body degrees of freedom. X, roll, pitch and yaw are marked "
        "sensor-local and alignment-free; Y is marked as requiring inter-sensor time alignment; "
        "Z is marked unobservable under planar motion.",
        "\n".join(b),
    )


def main() -> None:
    # The three card SVGs are hand-maintained by the author after this generator
    # produced the first draft (2026-09-21).  Re-running the generator would silently
    # discard that work, so an existing file is never overwritten without --force.
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="overwrite existing card SVGs (destroys hand edits)")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "card1-no-target.svg": card1(),
        "card2-no-shared-fov.svg": card2(),
        "card3-alignment-scope.svg": card3(),
    }
    for name, text in files.items():
        target = OUT / name
        if target.exists() and not args.force:
            print(f"skip   {target}  (already exists; pass --force to overwrite)")
            continue
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target}  ({len(text)} bytes)")


if __name__ == "__main__":
    main()
