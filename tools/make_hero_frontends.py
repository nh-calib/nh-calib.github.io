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
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "experiments" / "frontends" / "data" / "frontends_material_v2.npz"
OUTDIR = ROOT / "project_page" / "assets"

FG, MUT, GRID = "#10151d", "#475569", "#dde3ea"
C_LIDAR, C_GNSS = "#2563eb", "#0891b2"
C_RADAR, C_CAN = "#dc2626", "#0f766e"
C_YAW = "#7c3aed"
BADGE_PAPER, BADGE_SAME = "#1d4ed8", "#0f766e"

BANDS = {
    "a2d2": dict(accent="#3730a3", tint="#f4f6ff",
                 title="A2D2  ·  drive 20180810_150607",
                 sub="front ends:  LiDAR (KISS-ICP, FRONT_CENTER)   +   GNSS fixes (vehicle bus)"),
    "rs": dict(accent="#9a3412", tint="#fff9f4",
               title="RadarScenes  ·  sequence 1",
               sub="front ends:  2-D radar Doppler (sensor 1)   +   CAN odometry (vehicle bus)"),
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


def head(ax, text, sub, color, badge=None):
    fig = ax.figure
    bb = ax.get_position()
    fig.text(bb.x0, bb.y1 + 0.021, text, ha="left", va="bottom",
             fontsize=9.8, fontweight="bold", color=color)
    fig.text(bb.x0, bb.y1 + 0.006, sub, ha="left", va="bottom",
             fontsize=7.5, color=MUT)
    if badge:
        label, bc = badge
        fig.text(bb.x1, bb.y1 + 0.023, label, ha="right", va="bottom", fontsize=6.9,
                 color="white", fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.30", fc=bc, ec="none"))


def band_box(fig, axes, cfg):
    """tinted rounded frame + header bar around every axes of one dataset."""
    x0 = min(a.get_position().x0 for a in axes)
    x1 = max(a.get_position().x1 for a in axes)
    y0 = min(a.get_position().y0 for a in axes)
    y1 = max(a.get_position().y1 for a in axes)
    px, pyt, pyb = 0.017, 0.088, 0.058
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
    rotA = principal_angle(np.r_[ax_l, ax_g], np.r_[ay_l, ay_g])
    rotB = principal_angle(np.r_[bx_r, bx_c], np.r_[by_r, by_c])
    ax_l, ay_l = rot(ax_l, ay_l, rotA)
    ax_g, ay_g = rot(ax_g, ay_g, rotA)
    bx_r, by_r = rot(bx_r, by_r, rotB)
    bx_c, by_c = rot(bx_c, by_c, rotB)

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
    }

    fig = plt.figure(figsize=(16.2, 9.3), dpi=135)
    outer = fig.add_gridspec(2, 1, hspace=0.70, left=0.052, right=0.980,
                             top=0.800, bottom=0.078)
    WR = [1.02, 1.02, 0.92, 1.36]

    def make_band(row):
        g = outer[row].subgridspec(1, 4, width_ratios=WR, wspace=0.33)
        a0 = fig.add_subplot(g[0, 0])
        a1 = fig.add_subplot(g[0, 1])
        a2 = fig.add_subplot(g[0, 2])
        sg = g[0, 3].subgridspec(2, 1, hspace=0.16)
        s0 = fig.add_subplot(sg[0, 0])
        s1 = fig.add_subplot(sg[1, 0], sharex=s0)
        return a0, a1, a2, s0, s1

    A0, A1, A2, AS0, AS1 = make_band(0)
    B0, B1, B2, BS0, BS1 = make_band(1)

    fig.text(0.052, 0.968, "One interface, four front ends",
             fontsize=17.5, fontweight="bold", ha="left", va="center", color=FG)
    fig.text(0.052, 0.930,
             "Each tinted box is one drive.  Inside a box: what the sensor natively measures (left two), "
             "the trajectory that follows from its twist (third), and the twist itself (right) — the only "
             "thing the calibrator reads.",
             fontsize=9.3, ha="left", va="center", color=MUT)

    # ============================================================== band A: A2D2
    pts = z["a2d2_scan"]
    order = np.argsort(pts[:, 2])
    A0.scatter(pts[order, 0], pts[order, 1], s=1.7, c=pts[order, 2], cmap="viridis",
               vmin=-2.4, vmax=0.6, linewidths=0, alpha=0.9, rasterized=True)
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
    head(A0, "LiDAR point cloud", "one scan, %d points, forward wedge" % len(pts),
         C_LIDAR, ("paper front end", BADGE_PAPER))

    A1.plot(gfx, gfy, "-", color=C_GNSS, lw=0.9, alpha=0.45, zorder=2)
    A1.scatter(gfx, gfy, s=17, facecolor="white", edgecolor=C_GNSS, linewidths=1.0, zorder=3)
    A1.set_aspect("equal", adjustable="datalim")
    A1.set_xlabel("east [m]  (local tangent plane)", fontsize=7.8)
    A1.set_ylabel("north [m]", fontsize=7.8)
    tidy(A1)
    head(A1, "GNSS fixes",
         "%d distinct fixes at %.1f Hz, no attitude"
         % (meta["a2d2_gnss_n"], meta["a2d2_gnss_rate_hz"]),
         C_GNSS, ("same interface", BADGE_SAME))

    trail(A2, ax_l, ay_l, C_LIDAR, lw=2.4)
    trail(A2, ax_g, ay_g, C_GNSS, lw=1.7)
    A2.set_aspect("equal", adjustable="datalim")
    A2.set_xlabel("x [m]", fontsize=7.8)
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
    az, vr, inl = z["rs_scan_az"], z["rs_scan_vr"], z["rs_scan_inl"]
    fit = z["rs_scan_fit"]
    B0.scatter(np.degrees(az[~inl]), vr[~inl], s=13, facecolor="none",
               edgecolor="#bda5a5", linewidths=0.8, zorder=2, label="moving, rejected")
    B0.scatter(np.degrees(az[inl]), vr[inl], s=13, color=C_RADAR, alpha=0.72,
               linewidths=0, zorder=3, label="static, used")
    aa = np.linspace(az.min(), az.max(), 200)
    B0.plot(np.degrees(aa), -(fit[0] * np.cos(aa) + fit[1] * np.sin(aa)),
            color="#7f1d1d", lw=1.8, zorder=4, label="ego-velocity fit")
    B0.set_xlabel("azimuth [deg]  (sensor frame)", fontsize=7.8)
    B0.set_ylabel("radial speed $v_r$ [m/s]", fontsize=7.8)
    tidy(B0)
    B0.legend(loc="upper right", fontsize=7.0, frameon=False, handlelength=1.3,
              borderpad=0.1, labelspacing=0.22)
    head(B0, "Radar detections",
         "one scan, %d returns, %.0f%% inliers, residual %.3f m/s"
         % (meta["rs_scan_n"], 100 * meta["rs_scan_inlier"], meta["rs_scan_res_rms"]),
         C_RADAR, ("paper front end", BADGE_PAPER))

    zm = (ct >= 6.0) & (ct <= 8.0)
    B1.step(ct[zm], cvx[zm] * 3.6, where="post", color=C_CAN, lw=1.5)
    B1.plot(ct[zm], cvx[zm] * 3.6, "o", ms=2.6, color=C_CAN)
    B1.set_ylabel("wheel speed [km/h]", fontsize=7.8, color=C_CAN)
    B1.tick_params(axis="y", colors=C_CAN)
    B1b = B1.twinx()
    B1b.step(ct[zm], np.degrees(cwz[zm]), where="post", color=C_YAW, lw=1.3, ls=(0, (4, 2)))
    B1b.set_ylabel("yaw rate [deg/s]", fontsize=7.8, color=C_YAW)
    B1b.tick_params(axis="y", colors=C_YAW, labelsize=7.6, length=2.6)
    B1b.spines["top"].set_visible(False)
    B1.set_xlabel("time in window [s]", fontsize=7.8)
    tidy(B1)
    head(B1, "CAN bus frames", "2 s zoom of the %d messages in the window" % len(ct),
         C_CAN, ("same interface", BADGE_SAME))

    trail(B2, bx_r, by_r, C_RADAR, lw=2.4)
    trail(B2, bx_c, by_c, C_CAN, lw=1.7)
    B2.set_aspect("equal", adjustable="datalim")
    B2.set_xlabel("x [m]", fontsize=7.8)
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
