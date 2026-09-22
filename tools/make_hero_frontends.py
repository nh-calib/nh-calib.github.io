"""Module-1 figure: four odometry front ends, one twist interface.

Layout (v3 -- one vertical column per dataset, 2x2 inside)
  left column   A2D2 20180810_150607  : LiDAR scan | GNSS fixes
                                        trajectory | twist strip
  right column  RadarScenes sequence 1: Doppler BEV | CAN frames
                                        trajectory | twist strip

Three things the reader has to get without reading a caption:
  1. which panels belong to the same drive -- hence the tinted column box and
     its header bar, and the gap between the two columns;
  2. that the top row is two unrelated physical devices -- hence one framed
     card per device, in that device's own colour;
  3. that both devices end in the same product -- hence the lower two panels
     sit inside a single dashed ODOMETRY card, fed by an arrow from each of
     the two device cards above it.

Input : experiments/frontends/data/frontends_material_v2.npz
        (built on ailab-12 by extract_material_a2d2.py + extract_material_rs2.py)
Output: project_page/assets/frontends_real.png (+ .pdf, + meta json)
"""
import json
import weakref
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle
from matplotlib.colors import to_rgb

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "experiments" / "frontends" / "data" / "frontends_material_v2.npz"
OUTDIR = ROOT / "project_page" / "assets"

FG, MUT, GRID = "#10151d", "#475569", "#dde3ea"
# One colour per physical device, not per trace.  LiDAR/GNSS were both blue-cyan
# in the first cut, which read as "one stream drawn twice" instead of "two
# different boxes bolted to the same car"; blue vs magenta is separable in
# greyscale and for the common colour-vision deficiencies.
C_LIDAR, C_GNSS = "#1d4ed8", "#be185d"
C_RADAR, C_CAN = "#dc2626", "#0f766e"
C_YAW = "#7c3aed"
BADGE_PAPER, BADGE_SAME = "#1d4ed8", "#0f766e"
HEIGHT_CMAP = LinearSegmentedColormap.from_list(
    "lidar_height_gray_green_yellow", ["#9ca3af", "#22c55e", "#fde047"]
)
DOPPLER_CMAP = plt.get_cmap("coolwarm")
DOPPLER_NORM = Normalize(vmin=-8.0, vmax=8.0)

BANDS = {
    "a2d2": dict(accent="#3730a3", tint="#f4f6ff",
                 title="A2D2  ·  drive 20180810_150607",
                 sub="two devices  ·  no shared field of view, clock or quantity"),
    "rs": dict(accent="#9a3412", tint="#fff9f4",
               title="RadarScenes  ·  sequence 1",
               sub="two devices  ·  no shared field of view, clock or quantity"),
}

#: figure size.  The header row offsets below are figure fractions, so they are
#: written against this height and rescaled if it changes -- otherwise a taller
#: canvas silently inflates every header gap.
FIG_W, FIG_H = 16.4, 11.4
_HS = 9.9 / FIG_H

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.0,
    "axes.edgecolor": "#9aa4b2",
    "axes.labelcolor": FG,
    "text.color": FG,
    "xtick.color": MUT,
    "ytick.color": MUT,
    "axes.linewidth": 0.8,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})


# --------------------------------------------------------------------- helpers
def integrate(t, vfwd, vlat, wz):
    """dead-reckon a planar path from a twist stream; start at origin, heading +x."""
    x = y = th = 0.0
    X, Y = [0.0], [0.0]
    for k in range(1, len(t)):
        dt = float(t[k] - t[k - 1])
        th += float(wz[k - 1]) * dt
        x += (float(vfwd[k - 1]) * np.cos(th) - float(vlat[k - 1]) * np.sin(th)) * dt
        y += (float(vfwd[k - 1]) * np.sin(th) + float(vlat[k - 1]) * np.cos(th)) * dt
        X.append(x)
        Y.append(y)
    return np.array(X), np.array(Y)


def rot(x, y, ang):
    c, s = np.cos(ang), np.sin(ang)
    return c * x - s * y, s * x + c * y


def principal_angle(x, y):
    """angle that lays the cloud's long axis on +x, so a near-straight path
    still fills the panel instead of collapsing into a corner."""
    p = np.stack([x - x.mean(), y - y.mean()])
    _, v = np.linalg.eigh(p @ p.T)
    return -np.arctan2(v[1, -1], v[0, -1])


def trail(ax, x, y, color, lw=2.0, zorder=3):
    """path drawn as a fading trail: the head is solid, the tail washes out, so
    the eye reads a direction of travel even in a still frame."""
    pts = np.stack([x, y], axis=1).reshape(-1, 1, 2)
    seg = np.concatenate([pts[:-1], pts[1:]], axis=1)
    a = np.linspace(0.13, 1.0, len(seg)) ** 1.15
    lc = LineCollection(seg, colors=[(*matplotlib.colors.to_rgb(color), ai) for ai in a],
                        linewidths=lw, capstyle="round", zorder=zorder)
    ax.add_collection(lc)
    ax.plot([x[0]], [y[0]], "o", ms=4.2, mfc="white", mec=color, mew=1.4, zorder=zorder + 1)
    ang = np.degrees(np.arctan2(y[-1] - y[-3], x[-1] - x[-3]))
    ax.plot([x[-1]], [y[-1]], marker=(3, 0, ang - 90), ms=8.0, color=color,
            zorder=zorder + 1, linestyle="none")


def tidy(ax, grid=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    if grid:
        ax.grid(True, color=GRID, lw=0.6)
        ax.set_axisbelow(True)
    ax.tick_params(length=2.6, labelsize=7.6)


def lidar_height_scatter(ax, pts, size=1.7):
    """Low points are grey, mid-height structure green, and high returns yellow."""
    good = np.isfinite(pts).all(axis=1)
    p = pts[good]
    order = np.argsort(p[:, 2])
    return ax.scatter(p[order, 0], p[order, 1], s=size, c=p[order, 2],
                      cmap=HEIGHT_CMAP, vmin=-2.4, vmax=0.6,
                      linewidths=0, alpha=0.90, rasterized=True)


def select_doppler_points(az, vr, rng, n=14):
    """Choose a small, deterministic and angularly distributed Doppler subset."""
    valid = np.isfinite(az) & np.isfinite(vr) & np.isfinite(rng) & (rng > 2.0) & (rng < 80.0)
    ids = np.flatnonzero(valid)
    if ids.size <= n:
        return ids
    edges = np.linspace(float(az[ids].min()), float(az[ids].max()), n + 1)
    chosen = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        cand = ids[(az[ids] >= lo) & (az[ids] < hi)]
        if cand.size:
            chosen.append(int(cand[np.argmax(np.abs(vr[cand]))]))
    return np.asarray(chosen, dtype=int)


#: ego-velocity arrow is drawn at EGO_SCALE (3x the Doppler arrow scale) so a
#: ~9 m/s vector clears the cluster of returns around the sensor origin.
DOPPLER_ARROW_SCALE, EGO_SCALE, C_EGO = 0.90, 2.70, "#111827"


def ego_arrow(ax, v):
    """Estimated linear velocity of the sensor, drawn from the sensor origin.

    `v` = (vx, vy) in the plot's own sensor frame [m/s]; drawn at EGO_SCALE so a
    ~9 m/s vector reaches past the returns clustered around the sensor.
    """
    if v is None or not np.all(np.isfinite(v)):
        return
    ex, ey = EGO_SCALE * float(v[0]), EGO_SCALE * float(v[1])
    ax.annotate("", xy=(ex, ey), xytext=(0.0, 0.0),
                arrowprops=dict(arrowstyle="-|>", color=C_EGO, lw=2.4,
                                mutation_scale=13, shrinkA=0, shrinkB=0),
                zorder=7)
    ax.text(ex + 1.6, ey, r"$\hat v_{\mathrm{sensor}}$", ha="left",
            va="center", fontsize=8.6, color=C_EGO, fontweight="bold",
            zorder=7, bbox=dict(boxstyle="round,pad=0.12", fc="white",
                                ec="none", alpha=0.85))


def ego_legend_handle():
    return Line2D([], [], color=C_EGO, lw=2.2, marker=">", ms=5,
                  label="est. sensor velocity (3x scale)")


def ego_value_box(ax, v, ref_label, ref_v, edge, head_line):
    ax.text(0.028, 0.045,
            "%s\n$v$ = (%.2f, %.2f) m/s\n$|v|$ %.2f  ·  %s %.2f m/s"
            % (head_line, v[0], v[1], float(np.hypot(v[0], v[1])), ref_label, ref_v),
            transform=ax.transAxes, ha="left", va="bottom", fontsize=7.2,
            color=FG, linespacing=1.45, zorder=6,
            bbox=dict(boxstyle="round,pad=0.38", fc="white", ec=edge,
                      lw=0.8, alpha=0.94))


def radar_doppler_bev(ax, az, vr, rng, n_highlight=14, fit=None):
    """All detections in grey; a sparse subset carries colour and LOS Doppler arrows.

    `fit` = (vx, vy) of the one-scan least-squares ego-velocity, in the same
    sensor frame as the plot (vr = -(vx cos az + vy sin az)); it is drawn as
    the sensor's own linear-velocity vector from the sensor origin.
    """
    x, y = rng * np.cos(az), rng * np.sin(az)
    good = np.isfinite(x) & np.isfinite(y) & np.isfinite(vr)
    ax.scatter(x[good], y[good], s=5.0, color="#94a3b8", alpha=0.25,
               linewidths=0, rasterized=True, zorder=2)
    pick = select_doppler_points(az, vr, rng, n=n_highlight)
    if pick.size:
        colors = DOPPLER_CMAP(DOPPLER_NORM(vr[pick]))
        ax.scatter(x[pick], y[pick], s=24, c=colors, edgecolors="white",
                   linewidths=0.55, zorder=4)
        arrow_scale = DOPPLER_ARROW_SCALE
        ax.quiver(x[pick], y[pick], arrow_scale * vr[pick] * np.cos(az[pick]),
                  arrow_scale * vr[pick] * np.sin(az[pick]), color=colors,
                  angles="xy", scale_units="xy", scale=1.0, width=0.006,
                  headwidth=3.8, headlength=4.5, headaxislength=4.0, zorder=3)
    ax.plot([0], [0], marker="s", ms=5.0, color=C_RADAR, zorder=5)
    ego_arrow(ax, fit)
    ax.set_xlim(-4, 82)
    ax.set_ylim(-52, 52)
    ax.set_aspect("equal")
    ax.set_xlabel("x [m]  (sensor frame)", fontsize=7.8)
    ax.set_ylabel("y [m]", fontsize=7.8)
    tidy(ax, grid=False)
    return pick


#: vertical offsets of the four header rows, in figure fraction above the axes
ROW_TITLE, ROW_DEVICE, ROW_MEASURES, ROW_SUB = (0.049 * _HS, 0.033 * _HS,
                                                0.019 * _HS, 0.005 * _HS)
#: top edge of a per-device frame, measured above the axes
HEAD_TOP = 0.067 * _HS
#: top edge of the ODOMETRY frame -- clears the two-row panel header plus its
#: own label row, so the label never lands on "Trajectory from (v, w)".
OD_TOP = 0.067 * _HS + 0.030


#: header artists per axes, so sensor_box can size a frame around the text
#: rows as well as the plot (the device line is usually the widest thing here).
#: weak keys: the animation builds hundreds of figures in one process, and
#: id()-keyed entries would go stale and be silently reused.
_HEAD = weakref.WeakKeyDictionary()
#: device headers: (rows, colour bar, badge, axes top) -- re-pinned to the
#: card's top-left corner once `assemble` knows where the card is.
_PIN = weakref.WeakKeyDictionary()


def head(ax, text, sub, color, badge=None, device=None, measures=None):
    """Panel header.

    Raw-sensor panels pass `device` and `measures` so the reader is told which
    physical box this is and what quantity it actually senses; the shared
    trajectory / twist panels pass neither and keep the top two rows only, so
    every header in a band starts on the same baseline.
    """
    fig = ax.figure
    bb = ax.get_position()
    x = bb.x0 + (0.0115 if device else 0.0)
    bar = badge_t = None
    if device:                                   # device colour bar, band-style
        bar = fig.add_artist(Rectangle(
            (bb.x0, bb.y1 + ROW_TITLE - 0.0035), 0.0045, 0.0185,
            transform=fig.transFigure, facecolor=color, edgecolor="none",
            zorder=6))
    rows = [fig.text(x, bb.y1 + ROW_TITLE, text, ha="left", va="bottom",
                     fontsize=9.8, fontweight="bold", color=color),
            fig.text(x, bb.y1 + ROW_DEVICE, device if device else sub,
                     ha="left", va="bottom",
                     fontsize=7.3 if device else 7.5,
                     color=FG if device else MUT)]
    if measures:
        rows.append(fig.text(x, bb.y1 + ROW_MEASURES, measures, ha="left",
                             va="bottom", fontsize=6.7, color=MUT,
                             style="italic"))
    if device:
        rows.append(fig.text(x, bb.y1 + ROW_SUB, sub, ha="left", va="bottom",
                             fontsize=7.0, color=MUT))
    _HEAD[ax] = rows
    if badge:
        label, bc = badge
        badge_t = fig.text(bb.x1, bb.y1 + ROW_TITLE + 0.001, label,
                 ha="right", va="bottom",
                 fontsize=6.9, color="white", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.30", fc=bc, ec="none"))
    if device:
        _PIN[ax] = (rows, bar, badge_t, bb.y1)


def _wash(color, k=0.93):
    """color mixed k of the way to white -- a fill light enough to draw on."""
    return tuple(k + (1 - k) * c for c in to_rgb(color))


def sensor_extent(fig, axes):
    """Tight figure-fraction extent (x0, x1, y0, y1) of one device card's content."""
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    bbs = [a.get_tightbbox(r).transformed(inv) for a in axes]
    bbs += [t.get_window_extent(r).transformed(inv)
            for a in axes for t in _HEAD.get(a, [])]
    return (min(b.x0 for b in bbs), max(b.x1 for b in bbs),
            min(b.y0 for b in bbs), max(a.get_position().y1 for a in axes) + HEAD_TOP)


#: side padding of a device card and the minimum gutter between two cards
#: of one column (figure fraction; 0.014 ~ 28 px at 1968 px width)
CARD_PX, CARD_GAP = 0.0050, 0.014


def sensor_box(fig, ext, color):
    """Independent frame around ONE physical device.

    The band box says "this is one drive".  This says "this is one box bolted
    to that car": it wraps the panel together with its four header rows, in the
    device's own colour, so the two left columns cannot be read as one stream
    plotted twice.  `ext` comes from `sensor_extent`, already unified by
    `assemble` so every device card in the figure has the same size.
    """
    x0, x1, y0, y1 = ext
    px, pyb = CARD_PX, 0.009
    fig.add_artist(FancyBboxPatch(
        (x0 - px, y0 - pyb), (x1 - x0) + 2 * px, (y1 - y0) + pyb,
        boxstyle="round,pad=0.003,rounding_size=0.009",
        transform=fig.transFigure, facecolor=_wash(color),
        edgecolor=color, linewidth=1.0, alpha=0.95, zorder=-4.5))
    return x0 - px, x1 + px, y0 - pyb, y1


#: inset of a device name from its card's top-left corner (figure fraction)
PIN_DX, PIN_DY = 0.0070, 0.0085


def odometry_extent(fig, axes):
    """content extent of the ODOMETRY panels, without drawing anything."""
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    bbs = [a.get_tightbbox(r).transformed(inv) for a in axes]
    bbs += [t.get_window_extent(r).transformed(inv)
            for a in axes for t in _HEAD.get(a, [])]
    return None, None, (min(b.x0 for b in bbs), max(b.x1 for b in bbs))


def pin_header(axes, box):
    """Move a device header so the name sits at the card's top-left corner.

    Row spacing is kept; only the block is translated.  Every device card in
    the figure therefore labels itself at the same place, independent of how
    tall or narrow its plot is (the LiDAR panel is equal-aspect and shorter).
    """
    ax = next((a for a in axes if a in _PIN), None)
    if ax is None:
        return
    rows, bar, badge_t, ytop = _PIN[ax]
    bx0, bx1, _, by1 = box
    # the title row's top should land PIN_DY below the card top
    shift_y = (by1 - PIN_DY) - (ytop + ROW_TITLE + 0.0150)
    xt = bx0 + PIN_DX + 0.0115
    for t in rows:
        x, y = t.get_position()
        t.set_position((xt, y + shift_y))
    if bar is not None:
        bar.set_xy((bx0 + PIN_DX, bar.get_y() + shift_y))
    if badge_t is not None:
        x, y = badge_t.get_position()
        badge_t.set_position((bx1 - PIN_DX, y + shift_y))


def odometry_box(fig, axes, accent, note, xlim=None):
    """Dashed card around the lower two panels of a column.

    The two device cards above say "different box, different quantity".  This
    one says "and here they stop being different": the trajectory and the twist
    strip are not two more panels in the row, they are the single product that
    both devices were reduced to.  Returned is the top-centre anchor the feed
    arrows aim at.
    """
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    bbs = [a.get_tightbbox(r).transformed(inv) for a in axes]
    bbs += [t.get_window_extent(r).transformed(inv)
            for a in axes for t in _HEAD.get(a, [])]
    x0 = min(b.x0 for b in bbs)
    x1 = max(b.x1 for b in bbs)
    y0 = min(b.y0 for b in bbs)
    y1 = max(a.get_position().y1 for a in axes) + OD_TOP
    px, pyb = 0.0058, 0.011
    if xlim is not None:                  # shared column width from assemble
        x0, x1 = xlim[0] + px, xlim[1] - px
    fig.add_artist(FancyBboxPatch(
        (x0 - px, y0 - pyb), (x1 - x0) + 2 * px, (y1 - y0) + pyb,
        boxstyle="round,pad=0.003,rounding_size=0.010",
        transform=fig.transFigure, facecolor="white", alpha=0.90,
        edgecolor=accent, linewidth=1.5, linestyle=(0, (5.0, 2.4)),
        zorder=-4.2))
    ylab = y1 - 0.0175
    fig.add_artist(Rectangle(
        (x0 - px + 0.004, ylab - 0.0015), 0.0042, 0.0165,
        transform=fig.transFigure, facecolor=accent, edgecolor="none",
        zorder=-3.8))
    fig.text(x0 - px + 0.0135, ylab, "ODOMETRY", ha="left", va="bottom",
             fontsize=10.2, fontweight="bold", color=accent, zorder=-3.6)
    fig.text(x1 + px - 0.004, ylab + 0.0015, note, ha="right", va="bottom",
             fontsize=7.4, color=MUT, zorder=-3.6)
    return 0.5 * (x0 + x1), y1, (x0 - px, x1 + px, y0 - pyb, y1)


def feed_arrow(fig, src, dst, color):
    """Straight arrow from a device card down into the ODOMETRY card."""
    fig.add_artist(FancyArrowPatch(
        src, dst, transform=fig.transFigure, arrowstyle="-|>",
        mutation_scale=15, lw=2.1, color=color, alpha=0.92,
        shrinkA=0, shrinkB=0, zorder=6))


def assemble(fig, cols):
    """Draw every column's grammar: two device cards, one ODOMETRY card, two feeds.

    cols = [(devA, devB, odo, colors, accent, note), ...]; devA/devB/odo are
    lists of axes (a twin y-axis carries its own tick labels and must be
    listed, or the frame clips them).  All device cards in the figure share
    one height (common top and bottom) and one width (centred on their own
    content), so no device reads as more important than another.  Feeds drop
    straight down from each card's centre.
    """
    exts = [[sensor_extent(fig, c[0]), sensor_extent(fig, c[1])] for c in cols]
    flat = [e for pair in exts for e in pair]
    y0 = min(e[2] for e in flat)
    # + headroom: pinned headers sit at the card top, clear of the tallest plot
    # (and of the CAN panel's twin-axis label drawn above its axes)
    y1 = max(e[3] for e in flat) + 0.018
    w = max(e[1] - e[0] for e in flat)
    # a common width must not make the two cards of one column collide:
    # centre distance minus both cards' side padding minus a visible gutter
    for (a, b) in exts:
        room = (0.5 * (b[0] + b[1]) - 0.5 * (a[0] + a[1])) - 2 * CARD_PX - CARD_GAP
        w = min(w, room)
    frames = []
    for (devA, devB, odo, colors, accent, note), pair in zip(cols, exts):
        # one outer width per column, shared by the ODOMETRY card and the two
        # device cards: the wider of the odometry content and the two cards'
        # content (twin-axis tick labels can reach past the odometry panels)
        _, _, oext = odometry_extent(fig, odo)
        cx0 = min(oext[0] - 0.0058, pair[0][0] - 2 * CARD_PX)
        cx1 = max(oext[1] + 0.0058, pair[1][1] + 2 * CARD_PX)
        ox, oy, ofr = odometry_box(fig, odo, accent, note, xlim=(cx0, cx1))
        fr = [ofr]
        # the two device cards tile the ODOMETRY card's width exactly: same
        # outer left/right margin inside the dataset box, same card width,
        # CARD_GAP between them.  sensor_box adds CARD_PX on each side.
        # split point: centre of the gutter between the two cards' content
        # (the GNSS / CAN panels carry a y-label that reaches left of the
        # column centre), so both cards keep their content inside.
        xm = 0.5 * (pair[0][1] + pair[1][0])
        spans = [(ofr[0] + CARD_PX, xm - 0.5 * CARD_GAP - CARD_PX),
                 (xm + 0.5 * CARD_GAP + CARD_PX, ofr[1] - CARD_PX)]
        for (lo, hi), e, color, dev in zip(spans, pair, colors, (devA, devB)):
            if e[0] < lo - 1e-4 or e[1] > hi + 1e-4:
                raise SystemExit("card content %.4f..%.4f exceeds slot %.4f..%.4f"
                                 % (e[0], e[1], lo, hi))
            box = sensor_box(fig, (lo, hi, y0, y1), color)
            pin_header(dev, box)
            fr.append(box)
            cx = 0.5 * (box[0] + box[1])
            feed_arrow(fig, (cx, box[2] - 0.004), (cx, oy + 0.004), color)
        gap = fr[2][0] - fr[1][1]
        print("CARD_GAP %s %.4f (min %.4f)" % (note[:12], gap, CARD_GAP))
        if gap < CARD_GAP - 1e-6:
            raise SystemExit("device cards collide: gap %.4f < %.4f" % (gap, CARD_GAP))
        # outer extent (x0, x1, y0, y1) of every inner frame of this column, so
        # the dataset box can be sized around the frames instead of the axes
        frames.append((min(f[0] for f in fr), max(f[1] for f in fr),
                       min(f[2] for f in fr), max(f[3] for f in fr)))
    return frames


def band_box(fig, axes, cfg, frames):
    """tinted rounded frame + header bar around one dataset column.

    Sized from `frames` -- the outer extent of the device and ODOMETRY cards
    returned by `assemble` -- not from the axes, so no inner card can cross the
    dataset border, and the title row sits in its own strip above the cards.
    """
    x0, x1, y0, y1 = frames
    px, pyb = 0.0075, 0.0085
    pyt = 0.040                                   # title strip above the cards
    box = FancyBboxPatch((x0 - px, y0 - pyb), (x1 - x0) + 2 * px, (y1 - y0) + pyt + pyb,
                         boxstyle="round,pad=0.004,rounding_size=0.012",
                         transform=fig.transFigure, facecolor=cfg["tint"],
                         edgecolor=cfg["accent"], linewidth=1.2, zorder=-5)
    fig.add_artist(box)
    yh = y1 + 0.5 * pyt - 0.001
    fig.add_artist(FancyBboxPatch(
        (x0 - px + 0.005, yh - 0.011), 0.0060, 0.023,
        boxstyle="square,pad=0", transform=fig.transFigure,
        facecolor=cfg["accent"], edgecolor="none", zorder=-4))
    fig.text(x0 - px + 0.018, yh, cfg["title"], ha="left", va="center",
             fontsize=12.2, fontweight="bold", color=cfg["accent"], zorder=-3)
    fig.text(x1 + px - 0.005, yh, cfg["sub"], ha="right", va="center",
             fontsize=7.9, color=MUT, zorder=-3)
    for a in axes:
        a.set_facecolor("white")
        a.patch.set_alpha(1.0)


def mismatch(ta, a, tb, b):
    """median |a - b| after linear interpolation of b onto a's clock."""
    return float(np.median(np.abs(np.asarray(a) - np.interp(ta, tb, b))))


# ------------------------------------------------------------------------ main
def main():
    z = np.load(SRC)
    meta = json.loads(str(z["meta_json"][0]))

    lt = z["a2d2_lidar_t"]
    lvf, lvl, lwz = z["a2d2_lidar_vfwd"], z["a2d2_lidar_vlat"], z["a2d2_lidar_wz"]
    lspd = np.hypot(lvf, lvl)
    gt, gv, gwz = z["a2d2_gnss_t"], z["a2d2_gnss_v"], z["a2d2_gnss_wz"]
    gfx, gfy, gft = z["a2d2_gnss_fix_x"], z["a2d2_gnss_fix_y"], z["a2d2_gnss_fix_t"]

    # radar forward axis is +y in the RadarScenes sensor frame
    rt, rvx, rvy = z["rs_radar_t"], z["rs_radar_vx"], z["rs_radar_vy"]
    rspd = np.hypot(rvx, rvy)
    ct, cvx, cwz = z["rs_can_t"], z["rs_can_vx"], z["rs_can_wz"]
    rwz = np.interp(rt, ct, cwz)

    ax_l, ay_l = integrate(lt, lvf, lvl, lwz)
    ax_g, ay_g = integrate(gt, gv, np.zeros_like(gv), gwz)
    bx_r, by_r = integrate(rt, rvy, rvx, rwz)
    bx_c, by_c = integrate(ct, cvx, np.zeros_like(cvx), cwz)
    # 2026-09-22: no display rotation.  The path is drawn in the vehicle frame at
    # the first sample of the window (+x = heading at t=0, +y = left), the same
    # convention as the raw-sensor panels, so a turn seen in the point cloud and
    # the bend in this panel refer to one frame.  The earlier principal_angle()
    # rotation filled the panel better but left the two panels in unrelated
    # frames, which made the trajectory unreadable against the cloud.

    res = {
        "a2d2_v_mismatch": mismatch(gt, gv, lt, lspd),
        "a2d2_wz_mismatch": mismatch(gt, gwz, lt, lwz),
        "rs_v_mismatch": mismatch(rt, rspd, ct, cvx),
        "a2d2_path_end_gap": float(np.hypot(ax_l[-1] - ax_g[-1], ay_l[-1] - ay_g[-1])),
        "rs_path_end_gap": float(np.hypot(bx_r[-1] - bx_c[-1], by_r[-1] - by_c[-1])),
        "a2d2_v_mean_lidar": float(np.sum(np.hypot(np.diff(ax_l), np.diff(ay_l)))
                                   / (lt[-1] - lt[0])),
        "a2d2_v_mean_gnss": float(np.sum(np.hypot(np.diff(gfx), np.diff(gfy)))
                                  / (gft[-1] - gft[0])),
        "a2d2_path_len": float(np.sum(np.hypot(np.diff(ax_l), np.diff(ay_l)))),
        "rs_path_len": float(np.sum(np.hypot(np.diff(bx_r), np.diff(by_r)))),
        # fitted ego-velocity of the representative scan (sensor frame, +y forward)
        "rs_scan_vx": float(z["rs_scan_fit"][0]),
        "rs_scan_vy": float(z["rs_scan_fit"][1]),
        "rs_scan_vmag": float(np.hypot(*z["rs_scan_fit"])),
        "rs_scan_can_v": float(np.interp(float(np.atleast_1d(z["rs_scan_t"])[0]),
                                         ct, cvx)),
    }

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=135)
    # right edge stops well short of 1.0: the column frame is fitted to the
    # tight bbox, so the rightmost twin-axis tick labels push it further right
    # than the axes themselves and would otherwise be clipped.
    outer = fig.add_gridspec(1, 2, wspace=0.265, left=0.064, right=0.950,
                             top=0.804, bottom=0.068)

    def make_band(col):
        """one dataset = one 2x2 column: two devices on top, odometry below."""
        g = outer[col].subgridspec(2, 2, hspace=0.60, wspace=0.42,
                                   height_ratios=[1.0, 0.96])
        a0 = fig.add_subplot(g[0, 0])
        a1 = fig.add_subplot(g[0, 1])
        a2 = fig.add_subplot(g[1, 0])
        sg = g[1, 1].subgridspec(2, 1, hspace=0.16)
        s0 = fig.add_subplot(sg[0, 0])
        s1 = fig.add_subplot(sg[1, 0], sharex=s0)
        return a0, a1, a2, s0, s1

    A0, A1, A2, AS0, AS1 = make_band(0)
    B0, B1, B2, BS0, BS1 = make_band(1)

    fig.text(0.050, 0.976, "One interface, four front ends",
             fontsize=17.5, fontweight="bold", ha="left", va="center", color=FG)
    fig.text(0.050, 0.948,
             "Each tinted column is one drive: two different physical devices on top, and the dashed "
             "ODOMETRY card below holding what both of them were reduced to.  Badge “paper” marks the "
             "front end used in the paper’s experiments.",
             fontsize=9.3, ha="left", va="center", color=MUT)

    # ============================================================== band A: A2D2
    pts = z["a2d2_scan"]
    lidar_height_scatter(A0, pts)
    for rr in (20, 40, 60):
        th = np.linspace(-np.pi / 2, np.pi / 2, 120)
        A0.plot(rr * np.cos(th), rr * np.sin(th), color="#b9c2cf", lw=0.5,
                ls=(0, (3, 3)), zorder=1)
        A0.text(rr * np.cos(np.radians(-27)), rr * np.sin(np.radians(-27)), "%d m" % rr,
                fontsize=6.2, color="#8f9aa8", ha="center", va="center", zorder=1,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.75))
    A0.plot([0], [0], marker="s", ms=5.0, color=C_LIDAR, zorder=5)
    # sensor linear velocity at the scan instant: LiDAR twist (vx fwd, vy left),
    # the same sensor frame as the cloud, so it is drawn at the sensor origin.
    lv_scan = (float(np.interp(float(meta["a2d2_scan_rel_t"]), lt, lvf)),
               float(np.interp(float(meta["a2d2_scan_rel_t"]), lt, lvl)))
    res["a2d2_scan_vx"], res["a2d2_scan_vy"] = lv_scan
    res["a2d2_scan_gnss_v"] = float(np.interp(float(meta["a2d2_scan_rel_t"]), gt, gv))
    ego_arrow(A0, lv_scan)
    A0.legend(handles=[ego_legend_handle()], loc="upper right", fontsize=7.0,
              frameon=False, handlelength=1.3, borderpad=0.1)
    ego_value_box(A0, lv_scan, "GNSS", res["a2d2_scan_gnss_v"], C_LIDAR,
                  "scan-matched ego-velocity")
    A0.set_xlim(-4, 64)
    A0.set_ylim(-34, 34)
    A0.set_aspect("equal")
    A0.set_xlabel("x [m]  (sensor frame)", fontsize=7.8)
    A0.set_ylabel("y [m]", fontsize=7.8)
    tidy(A0, grid=False)
    head(A0, "SENSOR A  ·  LiDAR", "shown: one scan, %s points" % format(len(pts), ",d").replace(",", " "),
         C_LIDAR, ("paper", BADGE_PAPER),
         device="Velodyne VLP-16, FRONT_CENTER view  ·  ≈ 30 Hz",
         measures="range + bearing to surfaces  →  scan matching")

    A1.plot(gfx, gfy, "-", color=C_GNSS, lw=0.9, alpha=0.45, zorder=2)
    A1.scatter(gfx, gfy, s=17, facecolor="white", edgecolor=C_GNSS, linewidths=1.0, zorder=3)
    A1.set_aspect("equal", adjustable="datalim")
    A1.set_xlabel("east [m]  (local tangent plane)", fontsize=7.8)
    A1.set_ylabel("north [m]", fontsize=7.8)
    tidy(A1)
    head(A1, "SENSOR B  ·  GNSS",
         "shown: %d fixes at %.1f Hz, no attitude"
         % (meta["a2d2_gnss_n"], meta["a2d2_gnss_rate_hz"]),
         C_GNSS, ("demo", BADGE_SAME),
         device="vehicle-bus GNSS, position only  ·  1 Hz fix",
         measures="absolute position on Earth  →  differencing fixes")

    trail(A2, ax_l, ay_l, C_LIDAR, lw=2.4)
    trail(A2, ax_g, ay_g, C_GNSS, lw=1.7)
    ks = int(np.argmin(np.abs(lt - float(meta["a2d2_scan_rel_t"]))))
    A2.plot([ax_l[ks]], [ay_l[ks]], marker="*", ms=11, color="#f59e0b",
            mec="white", mew=0.8, zorder=6, linestyle="none")
    A2.annotate("scan shown here", (ax_l[ks], ay_l[ks]), textcoords="offset points",
                xytext=(6, -16), fontsize=6.8, color="#b45309")
    A2.set_aspect("equal", adjustable="datalim")
    A2.set_xlabel("x [m]  (vehicle frame at t=0)", fontsize=7.8)
    A2.set_ylabel("y [m]", fontsize=7.8)
    tidy(A2)
    A2.legend(handles=[Line2D([], [], color=C_LIDAR, lw=2.4, label="from LiDAR twist"),
                       Line2D([], [], color=C_GNSS, lw=1.7, label="from GNSS twist")],
              loc="lower left", fontsize=7.2, frameon=True, framealpha=0.94,
              edgecolor="none", facecolor="white", ncol=1,
              handlelength=1.5, borderpad=0.3, labelspacing=0.25)
    head(A2, "Trajectory from (v, ω)",
         "%.0f m driven, %.0f° of heading" % (res["a2d2_path_len"],
                                                  meta["a2d2_lidar_sweep_deg"]), FG)

    AS0.plot(lt, lspd, color=C_LIDAR, lw=1.5, label="LiDAR")
    AS0.plot(gt, gv, color=C_GNSS, lw=1.3, ls=(0, (4, 2)), marker="o", ms=2.6, label="GNSS")
    AS0.set_ylabel("|v| [m/s]", fontsize=7.8)
    AS0.tick_params(labelbottom=False)
    tidy(AS0)
    AS0.legend(loc="lower left", fontsize=7.2, frameon=False, ncol=2,
               handlelength=1.6, borderpad=0.1, columnspacing=1.1)
    AS1.plot(lt, lwz, color=C_LIDAR, lw=1.5)
    AS1.plot(gt, gwz, color=C_GNSS, lw=1.3, ls=(0, (4, 2)), marker="o", ms=2.6)
    AS1.set_ylabel("$\\omega_z$ [rad/s]", fontsize=7.8)
    AS1.set_xlabel("time in window [s]", fontsize=7.8)
    AS1.set_xlim(0, meta["window_s"])
    tidy(AS1)
    head(AS0, "The twist, as delivered",
         "path speed  %.2f vs %.2f m/s   ·   median ω gap  %.4f rad/s"
         % (res["a2d2_v_mean_lidar"], res["a2d2_v_mean_gnss"], res["a2d2_wz_mismatch"]), FG)

    # ======================================================= band B: RadarScenes
    az, vr, rng, inl = (z["rs_scan_az"], z["rs_scan_vr"], z["rs_scan_rng"],
                         z["rs_scan_inl"])
    fit = z["rs_scan_fit"]
    picked = radar_doppler_bev(B0, az, vr, rng, fit=fit)
    B0.legend(handles=[
        Line2D([], [], marker="o", ls="none", color="#94a3b8", alpha=0.5,
               label="all detections"),
        Line2D([], [], marker="o", ls="none", color=DOPPLER_CMAP(DOPPLER_NORM(-6)),
               label="selected + Doppler vector"),
        ego_legend_handle()],
        loc="upper right", fontsize=7.0, frameon=False, handlelength=1.3,
        borderpad=0.1, labelspacing=0.22)
    ego_value_box(B0, (res["rs_scan_vx"], res["rs_scan_vy"]), "CAN",
                  res["rs_scan_can_v"], C_RADAR, "fitted ego-velocity")
    head(B0, "SENSOR A  ·  radar",
         "shown: one scan, %d returns  ·  %d vectors"
         % (meta["rs_scan_n"], len(picked)),
         C_RADAR, ("paper", BADGE_PAPER),
         device="77 GHz series radar, sensor 1  ·  %.1f scans/s"
                % (meta["rs_usable_scans"] / meta["window_s"]),
         measures="range, azimuth, Doppler  →  one-scan least squares")

    zm = (ct >= 6.0) & (ct <= 8.0)
    B1.step(ct[zm], cvx[zm] * 3.6, where="post", color=C_CAN, lw=1.5)
    B1.plot(ct[zm], cvx[zm] * 3.6, "o", ms=2.6, color=C_CAN)
    B1.set_ylabel("wheel speed [km/h]", fontsize=7.8, color=C_CAN)
    B1.tick_params(axis="y", colors=C_CAN)
    B1b = B1.twinx()
    B1b.step(ct[zm], np.degrees(cwz[zm]), where="post", color=C_YAW, lw=1.3, ls=(0, (4, 2)))
    B1b.set_ylabel("")
    B1b.text(1.0, 1.012, "yaw rate [deg/s]", transform=B1b.transAxes,
             ha="right", va="bottom", fontsize=7.4, color=C_YAW)
    B1b.tick_params(axis="y", colors=C_YAW, labelsize=7.6, length=2.6)
    B1b.spines["top"].set_visible(False)
    B1.set_xlabel("time in window [s]", fontsize=7.8)
    tidy(B1)
    head(B1, "SENSOR B  ·  CAN bus",
         "shown: 2 s zoom of the window",
         C_CAN, ("demo", BADGE_SAME),
         device="wheel encoders + yaw-rate gyro  ·  %.0f Hz"
                % (len(ct) / meta["window_s"]),
         measures="wheel rotation + yaw rate  →  vehicle kinematics")

    trail(B2, bx_r, by_r, C_RADAR, lw=2.4)
    trail(B2, bx_c, by_c, C_CAN, lw=1.7)
    B2.set_aspect("equal", adjustable="datalim")
    B2.set_xlabel("x [m]  (vehicle frame at t=0)", fontsize=7.8)
    B2.set_ylabel("y [m]", fontsize=7.8)
    tidy(B2)
    B2.legend(handles=[Line2D([], [], color=C_RADAR, lw=2.4, label="from radar twist"),
                       Line2D([], [], color=C_CAN, lw=1.7, label="from CAN twist")],
              loc="lower right", fontsize=7.2, frameon=True, framealpha=0.94,
              edgecolor="none", facecolor="white", ncol=1,
              handlelength=1.5, borderpad=0.3, labelspacing=0.25)
    head(B2, "Trajectory from (v, ω)",
         "%.0f m driven, %.0f° of heading" % (res["rs_path_len"],
                                                  meta["rs_sweep_deg"]), FG)

    BS0.plot(rt, rspd, color=C_RADAR, lw=1.5, label="radar Doppler")
    BS0.plot(ct, cvx, color=C_CAN, lw=1.3, ls=(0, (4, 2)), label="CAN")
    BS0.set_ylabel("|v| [m/s]", fontsize=7.8)
    BS0.tick_params(labelbottom=False)
    tidy(BS0)
    BS0.legend(loc="lower left", fontsize=7.2, frameon=False, ncol=2,
               handlelength=1.6, borderpad=0.1, columnspacing=1.1)
    BS1.plot(ct, cwz, color=C_CAN, lw=1.5)
    BS1.set_ylabel("$\\omega_z$ [rad/s]", fontsize=7.8)
    BS1.set_xlabel("time in window [s]", fontsize=7.8)
    BS1.set_xlim(0, meta["window_s"])
    tidy(BS1)
    head(BS0, "The twist, as delivered",
         "median |v| gap   %.3f m/s    ·    one 2-D radar gives no ω"
         % res["rs_v_mismatch"], FG)

    fig.canvas.draw()
    note = "both devices deliver (v, ω) on their own clock"
    fa, fb = assemble(fig, [([A0], [A1], [A2, AS0, AS1], (C_LIDAR, C_GNSS),
                             BANDS["a2d2"]["accent"], note),
                            ([B0], [B1, B1b], [B2, BS0, BS1], (C_RADAR, C_CAN),
                             BANDS["rs"]["accent"], note)])
    band_box(fig, [A0, A1, A2, AS0, AS1], BANDS["a2d2"], fa)
    band_box(fig, [B0, B1, B2, BS0, BS1], BANDS["rs"], fb)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    png = OUTDIR / "frontends_real.png"
    fig.savefig(png, dpi=135, facecolor="white")
    fig.savefig(OUTDIR / "frontends_real.pdf", facecolor="white")
    meta_out = dict(meta)
    meta_out.update(res)
    (OUTDIR / "frontends_real_meta.json").write_text(
        json.dumps(meta_out, indent=1), encoding="utf-8")
    print("wrote", png)
    for k, v in res.items():
        print("  %-20s %.4f" % (k, v))


if __name__ == "__main__":
    main()
