"""Animated version of the four-front-end figure (module 1).

Same layout as make_hero_frontends.py, but a cursor walks the 20 s window:
  (a) the Ford RED LiDAR scan of the current frame, previous scan behind it
  (b) the RadarScenes sensor-1 scan of the current time with its robust fit
  (c) the INS path filling in, with the current pose marked
  (d) a 3 s sliding view of the CAN bus signals ending at the cursor
  strip  the two twist rows revealed up to the cursor

Inputs (same bundles as the still):
  frontends_material.npz   window, twists, INS path, CAN signals
  frontends_sequence.npz   per-frame LiDAR clouds, per-scan radar detections

Run with --frames-only to stop before encoding (no ffmpeg on Windows).
"""
import argparse
import json
import math
import os
import subprocess
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.ticker
import matplotlib.pyplot as plt

FG, MUT, GRID = "#10151d", "#475569", "#d8dee7"
C_LIDAR, C_INS, C_RADAR, C_CAN = "#2563eb", "#475569", "#dc2626", "#0f766e"
BADGE_PAPER, BADGE_SAME = "#1d4ed8", "#0f766e"
COL_L, COL_R = 0.487, 0.935
COL_LX, COL_RX = 0.058, 0.545
COL_CL, COL_CR = 0.2725, 0.740
FADE = "#cbd5e1"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.0,
    "axes.edgecolor": "#9aa4b2", "axes.labelcolor": FG, "text.color": FG,
    "xtick.color": MUT, "ytick.color": MUT, "axes.linewidth": 0.8,
    "figure.facecolor": "white", "axes.facecolor": "white",
})


def smooth(x, n):
    if n <= 1:
        return np.asarray(x, float)
    k = np.ones(n) / n
    pad = n // 2
    xp = np.pad(np.asarray(x, float), (pad, pad), mode="edge")
    return np.convolve(xp, k, mode="same")[pad:pad + len(x)]


def badge(ax, text, color, col_right):
    pos = ax.get_position()
    ax.figure.text(col_right, pos.y1 + 0.009, text, ha="right", va="bottom",
                   fontsize=7.2, color=color, fontweight="bold",
                   bbox=dict(boxstyle="round,pad=0.30", fc="white", ec=color, lw=0.8))


def panel_title(ax, text, sub, color, col_left):
    pos = ax.get_position()
    ax.figure.text(col_left, pos.y1 + 0.031, text, ha="left", va="bottom",
                   fontsize=10.4, fontweight="bold", color=color)
    return ax.figure.text(col_left, pos.y1 + 0.010, sub, ha="left", va="bottom",
                          fontsize=7.6, color=MUT)


def caption(ax, text, col_centre):
    pos = ax.get_position()
    return ax.figure.text(col_centre, pos.y0 - 0.052, text, ha="center", va="top",
                          fontsize=8.0, color=FG,
                          bbox=dict(boxstyle="round,pad=0.32", fc="white",
                                    ec="#c7d0dc", lw=0.7))


def tidy(ax):
    ax.grid(True, color=GRID, lw=0.6, alpha=0.9)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=None, help="directory holding the two npz bundles")
    ap.add_argument("--out", default=None, help="output directory")
    ap.add_argument("--frames", type=int, default=240)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--smoke", type=int, default=0, help="render only N frames")
    ap.add_argument("--frames-only", action="store_true")
    args = ap.parse_args()

    here = Path(__file__).resolve()
    try:                      # the script is also copied to /tmp on the render host
        repo_src = here.parents[2] / "experiments" / "frontends" / "data"
        repo_out = here.parents[1] / "assets" / "hero"
    except IndexError:
        repo_src = repo_out = Path("/tmp")
    src = Path(args.src) if args.src else (repo_src if repo_src.exists() else Path("/tmp"))
    out = Path(args.out) if args.out else repo_out
    frames_dir = out / "_frames_frontends"
    frames_dir.mkdir(parents=True, exist_ok=True)

    z = np.load(src / "frontends_material.npz")
    q = np.load(src / "frontends_sequence.npz")

    ft = np.asarray(z["ford_lidar_t"], float)
    f_speed = np.hypot(z["ford_lidar_vfwd"], z["ford_lidar_vlat"])
    fw = np.asarray(z["ford_lidar_wz"], float)
    fdt = np.asarray(z["ford_lidar_dt"], float)

    gt = np.asarray(z["ford_gt_t"], float)
    gt_hz = 1.0 / float(np.median(np.diff(gt)))
    nsm = max(1, int(round(0.2 * gt_hz)))
    g_speed = smooth(np.hypot(z["ford_gt_v"], z["ford_gt_vlat"]), nsm)
    g_wz = -smooth(np.asarray(z["ford_gt_wz"], float), nsm)   # FRD -> FLU
    gx = np.asarray(z["ford_gt_x"], float)
    gy = np.asarray(z["ford_gt_y"], float)

    ct = np.asarray(z["rs_can_t"], float)
    cv = np.asarray(z["rs_can_vx"], float)
    cw = np.asarray(z["rs_can_wz"], float)
    can_hz = 1.0 / float(np.median(np.diff(ct)))

    rt = np.asarray(q["radar_t"], float)
    roff = np.asarray(q["radar_off"], int)
    raz = np.asarray(q["radar_az"], float)
    rvr = np.asarray(q["radar_vr"], float)
    rinl = np.asarray(q["radar_inl"], bool)
    rfit = np.asarray(q["radar_fit"], float)
    r_speed = np.hypot(z["rs_radar_vx"], z["rs_radar_vy"])
    rts = np.asarray(z["rs_radar_t"], float)

    cloud = np.asarray(q["lidar_xy"], float)

    nfr = args.smoke if args.smoke else args.frames
    times = np.linspace(0.0, 20.0, args.frames)

    # a handful of clutter returns reach tens of m/s; clamping the axis to the
    # robust spread keeps the Doppler cosine readable in every frame
    lo_r, hi_r = np.percentile(rvr, [0.5, 99.5])
    pad_r = 0.15 * max(hi_r - lo_r, 4.0)
    vr_lim = (float(lo_r) - pad_r, float(hi_r) + pad_r)
    az_lim = (math.degrees(float(np.nanmin(raz))) - 4.0,
              math.degrees(float(np.nanmax(raz))) + 4.0)

    for fi in range(nfr):
        tc = float(times[fi])
        il = int(np.argmin(np.abs(ft - tc)))
        ir = int(np.argmin(np.abs(rt - tc)))

        fig = plt.figure(figsize=(12.8, 9.5), dpi=150)
        gs = fig.add_gridspec(2, 1, height_ratios=[1.44, 1.0],
                              top=0.858, bottom=0.088, left=0.058, right=0.935,
                              hspace=0.30)
        top = gs[0].subgridspec(2, 2, wspace=0.23, hspace=0.95)
        bot = gs[1].subgridspec(2, 2, wspace=0.13, hspace=0.12)

        fig.text(0.058, 0.966, "Any odometry, one interface",
                 fontsize=15.5, fontweight="bold", color=FG)
        fig.text(0.058, 0.940,
                 "Four front ends of three different sensing principles are reduced to the same per-frame "
                 "twist  (v, ω).  Everything downstream reads only that.",
                 fontsize=9.3, color=MUT)
        fig.text(0.058, 0.912, "Ford Multi-AV  ·  Log 4  ·  20 s window",
                 fontsize=9.0, color=FG, fontweight="bold")
        fig.text(0.545, 0.912, "RadarScenes  ·  sequence 1  ·  20 s window",
                 fontsize=9.0, color=FG, fontweight="bold")

        # ---------------------------------------------------------- (a) LiDAR
        ax = fig.add_subplot(top[0, 0])
        if il > 0:
            prev = cloud[il - 1]
            ax.scatter(prev[:, 0], prev[:, 1], s=1.2, c="#c3ccd8", lw=0,
                       alpha=0.55, rasterized=True, label="previous scan")
        cur = cloud[il]
        ax.scatter(cur[:, 0], cur[:, 1], s=1.2, c=C_LIDAR, lw=0, alpha=0.80,
                   rasterized=True, label="current scan")
        ax.set_aspect("equal")
        ax.set_xlim(-42, 42)
        ax.set_ylim(-42, 42)
        ax.set_xlabel("sensor x [m]")
        ax.set_ylabel("sensor y [m]  (forward)")
        tidy(ax)
        panel_title(ax, "LiDAR  —  scan-to-scan registration",
                    "KISS-ICP on the RED HDL-32E, deskewed  ·  frame %d / %d"
                    % (il + 1, ft.size), C_LIDAR, COL_LX)
        badge(ax, "paper front end", BADGE_PAPER, COL_L)
        caption(ax, "Δt = %.0f ms   →   |v| = %.2f m/s,   ω = %+.3f rad/s"
                % (fdt[il] * 1e3, f_speed[il], fw[il]), COL_CL)
        ax.legend(loc="upper left", fontsize=7.2, frameon=True, framealpha=0.92,
                  borderpad=0.35, handletextpad=0.4, markerscale=6)

        # ---------------------------------------------------------- (b) radar
        ax = fig.add_subplot(top[0, 1])
        s0, s1 = roff[ir], roff[ir + 1]
        az = np.degrees(raz[s0:s1])
        vr = rvr[s0:s1]
        inl = rinl[s0:s1]
        fit = rfit[ir]
        ax.scatter(az[~inl], vr[~inl], s=13, facecolors="none",
                   edgecolors="#9aa4b2", lw=0.7, label="rejected (moving / clutter)")
        ax.scatter(az[inl], vr[inl], s=13, c=C_RADAR, lw=0, alpha=0.80,
                   label="stationary world")
        g = np.linspace(az_lim[0], az_lim[1], 240)
        ax.plot(g, -(fit[0] * np.cos(np.radians(g)) + fit[1] * np.sin(np.radians(g))),
                color=C_RADAR, lw=1.8, label="robust fit")
        ax.set_xlim(*az_lim)
        ax.set_ylim(*vr_lim)
        ax.set_xlabel("detection azimuth [deg]")
        ax.set_ylabel("radial velocity $v_r$ [m/s]")
        tidy(ax)
        panel_title(ax, "Radar  —  Doppler ego-velocity",
                    "one 2-D radar scan, sensor 1, %d detections" % az.size,
                    C_RADAR, COL_RX)
        badge(ax, "paper front end", BADGE_PAPER, COL_R)
        caption(ax, "$v_r = -(v_x\\cos\\alpha + v_y\\sin\\alpha)$   →   |v| = %.2f m/s   "
                "(ω is not observable from one 2-D radar)"
                % math.hypot(fit[0], fit[1]), COL_CR)
        ax.legend(loc="lower left", fontsize=7.0, frameon=True, framealpha=0.92,
                  borderpad=0.35, handletextpad=0.4)

        # ---------------------------------------------------------- (c) INS
        ax = fig.add_subplot(top[1, 0])
        ax.plot(gx, gy, color=FADE, lw=1.6)
        mg = gt <= tc
        if mg.sum() > 1:
            ax.plot(gx[mg], gy[mg], color=C_INS, lw=2.0)
            ax.plot([gx[mg][-1]], [gy[mg][-1]], "o", ms=5.5, color=C_INS)
        ax.set_aspect("equal")
        ax.set_xlabel("map x [m]")
        ax.set_ylabel("map y [m]")
        tidy(ax)
        panel_title(ax, "GNSS/INS  —  pose differencing",
                    "6-DoF pose stream at %.0f Hz, FRD body frame" % gt_hz,
                    C_INS, COL_LX)
        badge(ax, "same interface", BADGE_SAME, COL_L)
        sweep = abs(np.degrees(np.asarray(z["ford_gt_yaw"], float)[mg][-1])) if mg.sum() else 0.0
        caption(ax, "$(\\mathbf{p}_k, R_k) \\rightarrow (v, \\omega)$ by finite difference   ·   "
                "heading turned %.0f° so far" % sweep, COL_CL)

        # ---------------------------------------------------------- (d) CAN
        ax = fig.add_subplot(top[1, 1])
        lo = max(0.0, tc - 3.0)
        exc = (ct >= lo) & (ct <= max(tc, lo + 0.2))
        ax.step(ct[exc], cv[exc], where="post", color=C_CAN, lw=1.6)
        ax.set_xlim(lo, lo + 3.0)
        ax.set_ylim(float(cv.min()) - 0.4, float(cv.max()) + 0.4)
        ax.set_xlabel("time in window [s]")
        ax.set_ylabel("vehicle speed [m/s]", color=C_CAN)
        ax.tick_params(axis="y", colors=C_CAN)
        tidy(ax)
        ax2 = ax.twinx()
        ax2.step(ct[exc], cw[exc], where="post", color="#b45309", lw=1.4)
        ax2.set_xlim(lo, lo + 3.0)
        ax2.set_ylim(float(cw.min()) - 0.03, float(cw.max()) + 0.03)
        ax2.set_ylabel("yaw rate [rad/s]", color="#b45309")
        ax2.tick_params(axis="y", colors="#b45309")
        ax2.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.2f"))
        ax2.spines["top"].set_visible(False)
        panel_title(ax, "CAN  —  bus messages",
                    "two scalar signals at %.0f Hz  ·  3 s sliding view" % can_hz,
                    C_CAN, COL_RX)
        badge(ax, "same interface", BADGE_SAME, COL_R)
        caption(ax, "no point cloud, no matching — the two bus signals are already the twist",
                COL_CR)

        # ---------------------------------------------------------- strip
        def strip(axx, t_a, y_a, c_a, t_b, y_b, c_b, ylab, show_x):
            axx.plot(t_b, y_b, color=FADE, lw=1.3)
            axx.plot(t_a, y_a, color=FADE, lw=1.3)
            mb = t_b <= tc
            ma = t_a <= tc
            if mb.sum() > 1:
                axx.plot(t_b[mb], y_b[mb], color=c_b, lw=1.5, ls="--")
            if ma.sum() > 1:
                axx.plot(t_a[ma], y_a[ma], color=c_a, lw=1.7)
            axx.axvline(tc, color="#94a3b8", lw=0.9, alpha=0.8)
            axx.set_xlim(0, 20)
            if ylab:
                axx.set_ylabel(ylab)
            if show_x:
                axx.set_xlabel("time in window [s]")
            else:
                axx.tick_params(labelbottom=False)
            tidy(axx)

        axs = fig.add_subplot(bot[0, 0])
        fig.text(0.058, axs.get_position().y1 + 0.014,
                 "Common twist interface consumed by the calibration",
                 fontsize=10.8, fontweight="bold", color=FG)
        strip(axs, ft, f_speed, C_LIDAR, gt, g_speed, C_INS, "$|v|$  [m/s]", False)
        axs.legend(handles=[plt.Line2D([], [], color=C_INS, ls="--", lw=1.5, label="GNSS/INS"),
                            plt.Line2D([], [], color=C_LIDAR, lw=1.7, label="LiDAR")],
                   loc="upper right", fontsize=7.2, ncol=2, frameon=True,
                   framealpha=0.92, borderpad=0.3, handletextpad=0.45,
                   columnspacing=0.9)

        axs2 = fig.add_subplot(bot[1, 0])
        strip(axs2, ft, fw, C_LIDAR, gt, g_wz, C_INS, "$\\omega_z$  [rad/s]", True)

        axr = fig.add_subplot(bot[0, 1])
        strip(axr, rts, r_speed, C_RADAR, ct, cv, C_CAN, None, False)
        axr.legend(handles=[plt.Line2D([], [], color=C_CAN, ls="--", lw=1.5, label="CAN"),
                            plt.Line2D([], [], color=C_RADAR, lw=1.7, label="radar Doppler")],
                   loc="upper right", fontsize=7.2, ncol=2, frameon=True,
                   framealpha=0.92, borderpad=0.3, handletextpad=0.45,
                   columnspacing=0.9)

        axr2 = fig.add_subplot(bot[1, 1])
        axr2.plot(ct, cw, color=FADE, lw=1.3)
        mb = ct <= tc
        if mb.sum() > 1:
            axr2.plot(ct[mb], cw[mb], color=C_CAN, lw=1.5, ls="--")
        axr2.axvline(tc, color="#94a3b8", lw=0.9, alpha=0.8)
        axr2.set_xlim(0, 20)
        axr2.set_xlabel("time in window [s]")
        tidy(axr2)
        axr2.text(0.030, 0.12,
                  "radar Doppler supplies $v$ only; $\\omega$ comes from CAN",
                  transform=axr2.transAxes, fontsize=7.2, color=C_RADAR)

        fig.text(0.058, 0.022,
                 "Per-sensor components differ by mounting — that difference is exactly what the "
                 "calibration estimates; the magnitudes above are frame-independent and therefore comparable.",
                 fontsize=7.6, color=MUT)

        fig.savefig(frames_dir / ("%04d.png" % fi), dpi=150)
        plt.close(fig)
        if fi % 20 == 0:
            print("frame %d/%d  t=%.2f s" % (fi, nfr, tc), flush=True)

    print("frames done:", nfr)
    if args.frames_only or args.smoke:
        return

    stem = out / "hero_frontends_real"
    common = ["-y", "-framerate", str(args.fps), "-i", str(frames_dir / "%04d.png")]
    subprocess.run(["ffmpeg"] + common + [
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
        "-vf", "scale=1920:-2", "-movflags", "+faststart", str(stem) + ".mp4"], check=True)
    subprocess.run(["ffmpeg"] + common + [
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p", "-crf", "36", "-b:v", "0",
        "-vf", "scale=1920:-2", str(stem) + ".webm"], check=True)
    subprocess.run(["cp", str(frames_dir / ("%04d.png" % (args.frames - 1))),
                    str(stem) + ".png"], check=True)
    meta = dict(frames=args.frames, fps=args.fps, window_s=20.0,
                ford_lidar_frames=int(ft.size), rs_radar_scans=int(rt.size))
    (out / "hero_frontends_real_meta.json").write_text(json.dumps(meta, indent=2))
    print("encoded", stem)


if __name__ == "__main__":
    main()
