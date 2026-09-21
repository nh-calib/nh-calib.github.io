"""Module-1 figure: four odometry front ends, one twist interface.

Layout (plan C):
  top    2x2 of modality-native raw representations, columns grouped by drive
             Ford Log4      : LiDAR scan pair        | GNSS/INS pose trace
             RadarScenes s1 : Doppler azimuth fit    | CAN bus messages
  bottom full-width strip, same two columns, two rows
             |v| [m/s] and omega_z [rad/s] over the same 20 s window

The claim the figure has to carry: the pipeline does not care which sensor or
which algorithm produced the motion, only that it arrives as (v, omega) per
frame.  The strip is the evidence -- two independent front ends per drive land
on the same curve.

Input : experiments/frontends/data/frontends_material.npz (built on ailab-12 by
        experiments/frontends/extract_material.py).  Nothing is re-estimated
        here; this file only draws what that bundle contains.
Output: project_page/assets/frontends_real.png (+ .pdf)
"""
import json
import math
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "experiments" / "frontends" / "data" / "frontends_material.npz"
OUTDIR = ROOT / "project_page" / "assets"

FG, MUT, GRID = "#10151d", "#475569", "#d8dee7"
C_LIDAR, C_INS, C_RADAR, C_CAN = "#2563eb", "#475569", "#dc2626", "#0f766e"
BADGE_PAPER = "#1d4ed8"
BADGE_SAME = "#0f766e"
COL_L, COL_R = 0.487, 0.963      # right edge of each grid column
COL_LX, COL_RX = 0.058, 0.545    # left edge of each grid column
COL_CL, COL_CR = 0.2725, 0.754   # centre of each grid column

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


def smooth(x, n):
    """centred moving average, edge-padded; n in samples."""
    if n <= 1:
        return np.asarray(x, float)
    k = np.ones(int(n)) / float(int(n))
    pad = int(n) // 2
    xp = np.pad(np.asarray(x, float), (pad, pad), mode="edge")
    return np.convolve(xp, k, mode="same")[pad:pad + len(x)]


def badge(ax, text, color, col_right):
    """Anchor the badge to the column's right edge in figure coordinates.

    Equal-aspect panels shrink horizontally inside their grid cell, so an
    axes-relative badge drifts inward and lands on the subtitle.
    """
    fig = ax.figure
    pos = ax.get_position()
    fig.text(col_right, pos.y1 + 0.009, text, ha="right", va="bottom",
             fontsize=7.2, color=color, fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.30", fc="white", ec=color, lw=0.8))


def panel_title(ax, text, sub, color, col_left):
    """Figure-anchored title block, so square panels keep the column margin."""
    fig = ax.figure
    pos = ax.get_position()
    fig.text(col_left, pos.y1 + 0.031, text, ha="left", va="bottom",
             fontsize=10.4, fontweight="bold", color=color)
    fig.text(col_left, pos.y1 + 0.010, sub, ha="left", va="bottom",
             fontsize=7.6, color=MUT)


def caption(ax, text, col_centre):
    """Caption pinned a fixed figure-distance below the axes, so panels of
    different aspect keep the same gap to the next row."""
    fig = ax.figure
    pos = ax.get_position()
    fig.text(col_centre, pos.y0 - 0.052, text, ha="center", va="top",
             fontsize=8.0, color=FG,
             bbox=dict(boxstyle="round,pad=0.32", fc="white", ec="#c7d0dc", lw=0.7))


def tidy(ax):
    ax.grid(True, color=GRID, lw=0.6, alpha=0.9)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)


def main():
    z = np.load(SRC)
    meta = json.loads(str(z["meta_json"][0]))

    # ---------------------------------------------------------------- derived
    ft = np.asarray(z["ford_lidar_t"], float)
    fv = np.asarray(z["ford_lidar_vfwd"], float)      # RED sensor forward is +y
    fvl = np.asarray(z["ford_lidar_vlat"], float)
    fw = np.asarray(z["ford_lidar_wz"], float)
    fdt = np.asarray(z["ford_lidar_dt"], float)
    f_speed = np.hypot(fv, fvl)

    gt = np.asarray(z["ford_gt_t"], float)
    gv = np.asarray(z["ford_gt_v"], float)
    gvl = np.asarray(z["ford_gt_vlat"], float)
    gw = np.asarray(z["ford_gt_wz"], float)
    # the INS stream is 200 Hz and differentiated; a 0.2 s centred moving
    # average removes the differentiation noise without touching the shape.
    gt_hz = 1.0 / float(np.median(np.diff(gt)))
    nsm = max(1, int(round(0.2 * gt_hz)))
    g_speed = smooth(np.hypot(gv, gvl), nsm)
    # Ford publishes its body pose in FRD (z down); the LiDAR twist lives in a
    # z-up sensor frame.  Negating yaw rate is the FRD -> FLU conversion, not a
    # fit: the two integrate to 128.67 deg and -130.77 deg over this window.
    g_wz = -smooth(gw, nsm)

    rt = np.asarray(z["rs_radar_t"], float)
    rvx = np.asarray(z["rs_radar_vx"], float)
    rvy = np.asarray(z["rs_radar_vy"], float)
    r_speed = np.hypot(rvx, rvy)
    ct = np.asarray(z["rs_can_t"], float)
    cv = np.asarray(z["rs_can_vx"], float)
    cw = np.asarray(z["rs_can_wz"], float)

    # agreement numbers quoted on the strip
    d_ford = np.median(np.abs(f_speed - np.interp(ft, gt, g_speed)))
    d_ford_w = np.median(np.abs(fw - np.interp(ft, gt, g_wz)))
    d_rs = np.median(np.abs(r_speed - np.interp(rt, ct, cv)))

    # ---------------------------------------------------------------- canvas
    fig = plt.figure(figsize=(12.8, 9.5), dpi=150)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.44, 1.0],
                          top=0.858, bottom=0.088, left=0.058, right=0.963,
                          hspace=0.30)
    top = gs[0].subgridspec(2, 2, wspace=0.23, hspace=0.95)
    bot = gs[1].subgridspec(2, 2, wspace=0.13, hspace=0.12)

    fig.text(0.058, 0.966, "Any odometry, one interface",
             fontsize=15.5, fontweight="bold", color=FG)
    fig.text(0.058, 0.940,
             "Four front ends of three different sensing principles are reduced to the same per-frame "
             "twist  (v, ω).  Everything downstream reads only that.",
             fontsize=9.3, color=MUT)

    # column headers, one per drive
    fig.text(0.058, 0.912, "Ford Multi-AV  ·  Log 4  ·  20 s window",
             fontsize=9.0, color=FG, fontweight="bold")
    fig.text(0.545, 0.912, "RadarScenes  ·  sequence 1  ·  20 s window",
             fontsize=9.0, color=FG, fontweight="bold")

    # ------------------------------------------------------------ (a) LiDAR
    ax = fig.add_subplot(top[0, 0])
    a = np.asarray(z["ford_scan_a"], float)
    b = np.asarray(z["ford_scan_b"], float)
    ax.scatter(a[:, 0], a[:, 1], s=1.1, c="#94a3b8", lw=0, alpha=0.55,
               rasterized=True, label="scan k")
    ax.scatter(b[:, 0], b[:, 1], s=1.1, c=C_LIDAR, lw=0, alpha=0.70,
               rasterized=True, label="scan k+1")
    ax.set_aspect("equal")
    ax.set_xlim(-42, 42)
    ax.set_ylim(-42, 42)
    ax.set_xlabel("sensor x [m]")
    ax.set_ylabel("sensor y [m]  (forward)")
    tidy(ax)
    scan_rel = float(np.asarray(z["ford_scan_rel_t"], float)[0])
    panel_title(ax, "LiDAR  —  scan-to-scan registration",
                "KISS-ICP on the RED HDL-32E, deskewed  ·  t = %.1f s" % scan_rel,
                C_LIDAR, COL_LX)
    badge(ax, "paper front end", BADGE_PAPER, COL_L)
    k = int(np.argmin(np.abs(ft - scan_rel)))
    caption(ax, "Δt = %.0f ms   →   |v| = %.2f m/s,   ω = %+.3f rad/s"
            % (fdt[k] * 1e3, f_speed[k], fw[k]), COL_CL)
    ax.legend(loc="upper left", fontsize=7.2, frameon=True, framealpha=0.92,
              borderpad=0.35, handletextpad=0.4, markerscale=6)

    # ------------------------------------------------------------ (b) radar
    ax = fig.add_subplot(top[0, 1])
    az = np.degrees(np.asarray(z["rs_scan_az"], float))
    vr = np.asarray(z["rs_scan_vr"], float)
    inl = np.asarray(z["rs_scan_inl"], bool)
    fit = np.asarray(z["rs_scan_fit"], float)
    ax.scatter(az[~inl], vr[~inl], s=13, facecolors="none", edgecolors="#9aa4b2",
               lw=0.7, label="rejected (moving / clutter)")
    ax.scatter(az[inl], vr[inl], s=13, c=C_RADAR, lw=0, alpha=0.80,
               label="stationary world")
    gridaz = np.linspace(az.min() - 3, az.max() + 3, 240)
    ax.plot(gridaz, -(fit[0] * np.cos(np.radians(gridaz))
                      + fit[1] * np.sin(np.radians(gridaz))),
            color=C_RADAR, lw=1.8, label="robust fit")
    ax.set_xlabel("detection azimuth [deg]")
    ax.set_ylabel("radial velocity $v_r$ [m/s]")
    tidy(ax)
    panel_title(ax, "Radar  —  Doppler ego-velocity",
                "one 2-D radar scan, sensor 1, %d detections" % az.size, C_RADAR, COL_RX)
    badge(ax, "paper front end", BADGE_PAPER, COL_R)
    caption(ax, "$v_r = -(v_x\\cos\\alpha + v_y\\sin\\alpha)$   →   |v| = %.2f m/s   "
            "(ω is not observable from one 2-D radar)" % math.hypot(fit[0], fit[1]),
            COL_CR)
    ax.legend(loc="lower left", fontsize=7.0, frameon=True, framealpha=0.92,
              borderpad=0.35, handletextpad=0.4)

    # ------------------------------------------------------------ (c) INS
    ax = fig.add_subplot(top[1, 0])
    gx = np.asarray(z["ford_gt_x"], float)
    gy = np.asarray(z["ford_gt_y"], float)
    gyaw = np.asarray(z["ford_gt_yaw"], float)
    ax.plot(gx, gy, color=C_INS, lw=1.9)
    step = max(1, len(gt) // 12)
    yaw_abs = gyaw + math.atan2(gy[1] - gy[0], gx[1] - gx[0])
    L = 0.055 * max(np.ptp(gx), np.ptp(gy))
    for i in range(0, len(gt), step):
        ax.add_patch(FancyArrowPatch(
            (gx[i], gy[i]),
            (gx[i] + L * math.cos(yaw_abs[i]), gy[i] + L * math.sin(yaw_abs[i])),
            arrowstyle="-|>", mutation_scale=7, lw=1.0, color="#94a3b8"))
    ax.plot([gx[0]], [gy[0]], "o", ms=5, color=C_INS)
    ax.set_aspect("equal")
    ax.set_xlabel("map x [m]")
    ax.set_ylabel("map y [m]")
    tidy(ax)
    panel_title(ax, "GNSS/INS  —  pose differencing",
                "6-DoF pose stream at %.0f Hz, FRD body frame" % gt_hz, C_INS, COL_LX)
    badge(ax, "same interface", BADGE_SAME, COL_L)
    caption(ax, "$(\\mathbf{p}_k, R_k) \\rightarrow (v, \\omega)$ by finite difference   ·   "
            "heading sweep %.0f° over the window"
            % abs(np.degrees(gyaw[-1] - gyaw[0])), COL_CL)

    # ------------------------------------------------------------ (d) CAN
    ax = fig.add_subplot(top[1, 1])
    exc = (ct >= 6.0) & (ct <= 9.0)
    ax.step(ct[exc], cv[exc], where="post", color=C_CAN, lw=1.6,
            label="vehicle speed")
    ax.plot(ct[exc][::6], cv[exc][::6], ".", ms=3.0, color=C_CAN)
    ax.set_xlabel("time in window [s]")
    ax.set_ylabel("vehicle speed [m/s]", color=C_CAN)
    ax.tick_params(axis="y", colors=C_CAN)
    tidy(ax)
    ax2 = ax.twinx()
    ax2.step(ct[exc], cw[exc], where="post", color="#b45309", lw=1.4,
             label="yaw rate")
    ax2.plot(ct[exc][::6], cw[exc][::6], ".", ms=3.0, color="#b45309")
    ax2.set_ylabel("yaw rate [rad/s]", color="#b45309")
    ax2.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.2f"))
    ax2.tick_params(axis="y", colors="#b45309")
    ax2.spines["top"].set_visible(False)
    can_hz = 1.0 / float(np.median(np.diff(ct)))
    panel_title(ax, "CAN  —  bus messages",
                "two scalar signals at %.0f Hz  ·  3 s excerpt" % can_hz, C_CAN, COL_RX)
    badge(ax, "same interface", BADGE_SAME, COL_R)
    caption(ax, "no point cloud, no matching — the two bus signals are already the twist",
            COL_CR)

    # ---------------------------------------------------------------- strip
    axs = fig.add_subplot(bot[0, 0])
    fig.text(0.058, axs.get_position().y1 + 0.014,
             "Common twist interface consumed by the calibration",
             fontsize=10.8, fontweight="bold", color=FG)
    axs.plot(gt, g_speed, color=C_INS, lw=1.5, ls="--", label="GNSS/INS")
    axs.plot(ft, f_speed, color=C_LIDAR, lw=1.7, label="LiDAR")
    axs.set_ylabel("$|v|$  [m/s]")
    axs.tick_params(labelbottom=False)
    tidy(axs)
    axs.legend(loc="upper right", fontsize=7.2, ncol=2, frameon=True,
               framealpha=0.92, borderpad=0.3, handletextpad=0.45,
               columnspacing=0.9)
    axs.text(0.015, 0.06, "median gap %.2f m/s" % d_ford, transform=axs.transAxes,
             fontsize=7.2, color=MUT)

    axs2 = fig.add_subplot(bot[1, 0], sharex=axs)
    axs2.plot(gt, g_wz, color=C_INS, lw=1.5, ls="--")
    axs2.plot(ft, fw, color=C_LIDAR, lw=1.7)
    axs2.set_ylabel("$\\omega_z$  [rad/s]")
    axs2.set_xlabel("time in window [s]")
    tidy(axs2)
    axs2.text(0.015, 0.08, "median gap %.3f rad/s   (INS converted FRD to FLU)" % d_ford_w,
              transform=axs2.transAxes, fontsize=7.2, color=MUT)

    axr = fig.add_subplot(bot[0, 1])
    axr.plot(ct, cv, color=C_CAN, lw=1.5, ls="--", label="CAN")
    axr.plot(rt, r_speed, color=C_RADAR, lw=1.7, label="radar Doppler")
    axr.tick_params(labelbottom=False)
    tidy(axr)
    axr.legend(loc="upper right", fontsize=7.2, ncol=2, frameon=True,
               framealpha=0.92, borderpad=0.3, handletextpad=0.45,
               columnspacing=0.9)
    axr.text(0.015, 0.06, "median gap %.2f m/s" % d_rs, transform=axr.transAxes,
             fontsize=7.2, color=MUT)

    axr2 = fig.add_subplot(bot[1, 1], sharex=axr)
    axr2.plot(ct, cw, color=C_CAN, lw=1.5, ls="--")
    axr2.set_xlabel("time in window [s]")
    tidy(axr2)
    axr2.text(0.030, 0.12,
              "radar Doppler supplies $v$ only; $\\omega$ comes from CAN",
              transform=axr2.transAxes, fontsize=7.2, color=C_RADAR)

    for a_ in (axs, axs2):
        a_.set_xlim(0, 20)
    for a_ in (axr, axr2):
        a_.set_xlim(0, 20)

    fig.text(0.058, 0.022,
             "Per-sensor components differ by mounting — that difference is exactly what the "
             "calibration estimates; the magnitudes above are frame-independent and therefore comparable.",
             fontsize=7.6, color=MUT)

    OUTDIR.mkdir(parents=True, exist_ok=True)
    png = OUTDIR / "frontends_real.png"
    fig.savefig(png, dpi=150)
    fig.savefig(OUTDIR / "frontends_real.pdf")
    plt.close(fig)

    stats = dict(
        ford_window_t0=meta["ford_t0"], rs_window_t0=meta["rs_t0"],
        ford_median_speed_gap_mps=float(d_ford),
        ford_median_wz_gap_radps=float(d_ford_w),
        rs_median_speed_gap_mps=float(d_rs),
        ford_lidar_n=int(ft.size), ford_ins_hz=float(gt_hz),
        rs_radar_n=int(rt.size), rs_can_hz=float(can_hz),
        rs_scan_detections=int(az.size),
        rs_scan_inlier_frac=float(inl.mean()),
        ins_smoothing_s=0.2,
    )
    (OUTDIR / "frontends_real_meta.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8")
    print("wrote", png)
    for k2, v2 in stats.items():
        print("  %s = %s" % (k2, v2))


if __name__ == "__main__":
    main()
