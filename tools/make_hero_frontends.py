"""Module-1 figure: four odometry front ends, one twist interface.

Layout (v2 -- one horizontal box per dataset)
  band A  A2D2 20180810_150607  : LiDAR scan | GNSS fixes | trajectory | twist strip
  band B  RadarScenes sequence 1: Doppler fit | CAN frames | trajectory | twist strip

Two things the reader has to get without reading a caption:
  1. which panels belong to the same drive -- hence the tinted box and the
     header bar that wrap a whole band, and the gap between bands;
  2. that every front end leaves the same kind of output -- hence the
     trajectory panel, drawn with identical styling in both bands, where the
     two front ends of that drive are integrated from their own (v, omega).

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
                 sub="two independent devices  ·  nothing shared: no field of view, no clock, no measured quantity"),
    "rs": dict(accent="#9a3412", tint="#fff9f4",
               title="RadarScenes  ·  sequence 1",
               sub="two independent devices  ·  nothing shared: no field of view, no clock, no measured quantity"),
}

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


def radar_doppler_bev(ax, az, vr, rng, n_highlight=14):
    """All detections in grey; a sparse subset carries colour and LOS Doppler arrows."""
    x, y = rng * np.cos(az), rng * np.sin(az)
    good = np.isfinite(x) & np.isfinite(y) & np.isfinite(vr)
    ax.scatter(x[good], y[good], s=5.0, color="#94a3b8", alpha=0.25,
               linewidths=0, rasterized=True, zorder=2)
    pick = select_doppler_points(az, vr, rng, n=n_highlight)
    if pick.size:
        colors = DOPPLER_CMAP(DOPPLER_NORM(vr[pick]))
        ax.scatter(x[pick], y[pick], s=24, c=colors, edgecolors="white",
                   linewidths=0.55, zorder=4)
        arrow_scale = 0.90
        ax.quiver(x[pick], y[pick], arrow_scale * vr[pick] * np.cos(az[pick]),
                  arrow_scale * vr[pick] * np.sin(az[pick]), color=colors,
                  angles="xy", scale_units="xy", scale=1.0, width=0.006,
                  headwidth=3.8, headlength=4.5, headaxislength=4.0, zorder=3)
    ax.plot([0], [0], marker="s", ms=5.0, color=C_RADAR, zorder=5)
    ax.set_xlim(-4, 82)
    ax.set_ylim(-52, 52)
    ax.set_aspect("equal")
    ax.set_xlabel("x [m]  (sensor frame)", fontsize=7.8)
    ax.set_ylabel("y [m]", fontsize=7.8)
    tidy(ax, grid=False)
    return pick


#: vertical offsets of the four header rows, in figure fraction above the axes
ROW_TITLE, ROW_DEVICE, ROW_MEASURES, ROW_SUB = 0.049, 0.033, 0.019, 0.005
#: top edge of a per-device frame, measured above the axes
HEAD_TOP = 0.067


#: header artists per axes, so sensor_box can size a frame around the text
#: rows as well as the plot (the device line is usually the widest thing here).
#: weak keys: the animation builds hundreds of figures in one process, and
#: id()-keyed entries would go stale and be silently reused.
_HEAD = weakref.WeakKeyDictionary()


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
    if device:                                   # device colour bar, band-style
        fig.add_artist(Rectangle(
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
        fig.text(bb.x1, bb.y1 + ROW_TITLE + 0.001, label,
                 ha="right", va="bottom",
                 fontsize=6.9, color="white", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.30", fc=bc, ec="none"))


def _wash(color, k=0.93):
    """color mixed k of the way to white -- a fill light enough to draw on."""
    return tuple(k + (1 - k) * c for c in to_rgb(color))


def sensor_box(fig, axes, color):
    """Independent frame around ONE physical device.

    The band box says "this is one drive".  This says "this is one box bolted
    to that car": it wraps the panel together with its four header rows, in the
    device's own colour, so the two left columns cannot be read as one stream
    plotted twice.  Pass every axes that belongs to the device (a twin y-axis
    carries its own tick labels and must be included or the frame clips them).
    """
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    bbs = [a.get_tightbbox(r).transformed(inv) for a in axes]
    bbs += [t.get_window_extent(r).transformed(inv)
            for a in axes for t in _HEAD.get(a, [])]
    x0 = min(b.x0 for b in bbs)
    x1 = max(b.x1 for b in bbs)
    y0 = min(b.y0 for b in bbs)
    y1 = max(a.get_position().y1 for a in axes) + HEAD_TOP
    px, pyb = 0.0050, 0.010
    fig.add_artist(FancyBboxPatch(
        (x0 - px, y0 - pyb), (x1 - x0) + 2 * px, (y1 - y0) + pyb,
        boxstyle="round,pad=0.003,rounding_size=0.009",
        transform=fig.transFigure, facecolor=_wash(color),
        edgecolor=color, linewidth=1.0, alpha=0.95, zorder=-4.5))
    return x0 - px, x1 + px


def merge_arrow(fig, a2, x_from, accent):
    """Arrow from the second device frame into the shared trajectory panel.

    The separation between the two raw columns is carried by the frames
    themselves, so nothing is drawn between them; this arrow is the one piece
    of grammar left -- it marks where two unrelated devices stop being
    different and become the same two numbers.
    """
    r = fig.canvas.get_renderer()
    tb = a2.get_tightbbox(r).transformed(fig.transFigure.inverted())
    yc = 0.5 * (a2.get_position().y0 + a2.get_position().y1)
    fig.add_artist(FancyArrowPatch(
        (x_from + 0.005, yc), (tb.x0 - 0.006, yc), transform=fig.transFigure,
        arrowstyle="-|>", mutation_scale=15, lw=2.1, color=accent, zorder=5))


def band_box(fig, axes, cfg):
    """tinted rounded frame + header bar around every axes of one dataset."""
    r = fig.canvas.get_renderer()
    inv = fig.transFigure.inverted()
    tbs = [a.get_tightbbox(r).transformed(inv) for a in axes]
    x0 = min(b.x0 for b in tbs)
    x1 = max(b.x1 for b in tbs)
    y0 = min(b.y0 for b in tbs)
    y1 = max(a.get_position().y1 for a in axes)
    px, pyt, pyb = 0.013, 0.112, 0.021
    box = FancyBboxPatch((x0 - px, y0 - pyb), (x1 - x0) + 2 * px, (y1 - y0) + pyt + pyb,
                         boxstyle="round,pad=0.004,rounding_size=0.012",
                         transform=fig.transFigure, facecolor=cfg["tint"],
                         edgecolor=cfg["accent"], linewidth=1.2, zorder=-5)
    fig.add_artist(box)
    yh = y1 + pyt - 0.022
    fig.add_artist(FancyBboxPatch(
        (x0 - px + 0.005, yh - 0.012), 0.0060, 0.026,
        boxstyle="square,pad=0", transform=fig.transFigure,
        facecolor=cfg["accent"], edgecolor="none", zorder=-4))
    fig.text(x0 - px + 0.018, yh, cfg["title"], ha="left", va="center",
             fontsize=12.2, fontweight="bold", color=cfg["accent"], zorder=-3)
    fig.text(x1 + px - 0.005, yh, cfg["sub"], ha="right", va="center",
             fontsize=8.2, color=MUT, zorder=-3)
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

    fig = plt.figure(figsize=(16.2, 9.9), dpi=135)
    outer = fig.add_gridspec(2, 1, hspace=0.80, left=0.052, right=0.980,
                             top=0.812, bottom=0.070)
    WR = [1.02, 1.02, 0.92, 1.36]

    def make_band(row):
        g = outer[row].subgridspec(1, 4, width_ratios=WR, wspace=0.42)
        a0 = fig.add_subplot(g[0, 0])
        a1 = fig.add_subplot(g[0, 1])
        a2 = fig.add_subplot(g[0, 2])
        sg = g[0, 3].subgridspec(2, 1, hspace=0.16)
        s0 = fig.add_subplot(sg[0, 0])
        s1 = fig.add_subplot(sg[1, 0], sharex=s0)
        return a0, a1, a2, s0, s1

    A0, A1, A2, AS0, AS1 = make_band(0)
    B0, B1, B2, BS0, BS1 = make_band(1)

    fig.text(0.052, 0.972, "One interface, four front ends",
             fontsize=17.5, fontweight="bold", ha="left", va="center", color=FG)
    fig.text(0.052, 0.938,
             "Each tinted box is one drive; the two left panels of a box are two different devices on that "
             "car.  Badge “paper” marks the front end used in the paper’s experiments, “demo” the second "
             "device shown to make the interface point.",
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
    picked = radar_doppler_bev(B0, az, vr, rng)
    B0.legend(handles=[
        Line2D([], [], marker="o", ls="none", color="#94a3b8", alpha=0.5,
               label="all detections"),
        Line2D([], [], marker="o", ls="none", color=DOPPLER_CMAP(DOPPLER_NORM(-6)),
               label="selected + Doppler vector")],
        loc="upper right", fontsize=7.0, frameon=False, handlelength=1.3,
        borderpad=0.1, labelspacing=0.22)
    B0.text(0.028, 0.045,
            "fitted ego-velocity\n"
            "$v$ = (%.2f, %.2f) m/s\n"
            "$|v|$ %.2f  ·  CAN %.2f m/s"
            % (res["rs_scan_vx"], res["rs_scan_vy"], res["rs_scan_vmag"],
               res["rs_scan_can_v"]),
            transform=B0.transAxes, ha="left", va="bottom", fontsize=7.2,
            color=FG, linespacing=1.45, zorder=6,
            bbox=dict(boxstyle="round,pad=0.38", fc="white", ec=C_RADAR,
                      lw=0.8, alpha=0.94))
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
    band_box(fig, [A0, A1, A2, AS0, AS1], BANDS["a2d2"])
    band_box(fig, [B0, B1, B2, BS0, BS1], BANDS["rs"])
    sensor_box(fig, [A0], C_LIDAR)
    sensor_box(fig, [B0], C_RADAR)
    merge_arrow(fig, A2, sensor_box(fig, [A1], C_GNSS)[1], BANDS["a2d2"]["accent"])
    merge_arrow(fig, B2, sensor_box(fig, [B1, B1b], C_CAN)[1], BANDS["rs"]["accent"])

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
