"""Animated version of the four-front-end figure (v3 layout).

Same two dataset columns as the still -- two device cards on top, one dashed
ODOMETRY card below, fed by an arrow from each device -- replayed over the 20 s
window: the point cloud and the radar scan advance with the drive, the CAN
strip slides, and both trajectory panels grow a trail.  The trail is the point
of the animation -- four different sensors, four different raw panels, one
identical path product.

Inputs : experiments/frontends/data/frontends_material_v2.npz
         experiments/frontends/data/frontends_sequence_v2.npz
Output : frames/*.png  (encoded to mp4/webm by the caller)

Usage  : python make_hero_frontends_anim.py <outdir> [n_workers]
"""
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import make_hero_frontends as S

ROOT = Path(__file__).resolve().parents[2]
SEQ = ROOT / "experiments" / "frontends" / "data" / "frontends_sequence_v2.npz"

# Workers read the output directory from the environment, not from a global set
# under __main__: on a spawn-start platform (Windows) the child re-imports this
# module and would otherwise raise NameError on OUTDIR.
OUTDIR = Path(os.environ.get("FR_OUTDIR", "/tmp/frontends_frames"))

# NpzFile reads lazily from one file handle; forked workers would share it and
# trip zipfile's overlapped-entry guard, so materialise both bundles up front.
Z = dict(np.load(S.SRC))
Q = dict(np.load(SEQ))
META = json.loads(str(Z["meta_json"][0]))
FT = Q["frame_t"]
WIN = float(META["window_s"])


def _prep():
    """everything that does not change frame to frame."""
    d = {}
    d["lt"] = Z["a2d2_lidar_t"]
    d["lvf"], d["lvl"], d["lwz"] = (Z["a2d2_lidar_vfwd"], Z["a2d2_lidar_vlat"],
                                    Z["a2d2_lidar_wz"])
    d["lspd"] = np.hypot(d["lvf"], d["lvl"])
    d["gt"], d["gv"], d["gwz"] = Z["a2d2_gnss_t"], Z["a2d2_gnss_v"], Z["a2d2_gnss_wz"]
    d["gfx"], d["gfy"], d["gft"] = (Z["a2d2_gnss_fix_x"], Z["a2d2_gnss_fix_y"],
                                    Z["a2d2_gnss_fix_t"])
    d["rt"], d["rvx"], d["rvy"] = Z["rs_radar_t"], Z["rs_radar_vx"], Z["rs_radar_vy"]
    d["rspd"] = np.hypot(d["rvx"], d["rvy"])
    d["ct"], d["cvx"], d["cwz"] = Z["rs_can_t"], Z["rs_can_vx"], Z["rs_can_wz"]
    rwz = np.interp(d["rt"], d["ct"], d["cwz"])

    # 2026-09-22: no display rotation, matching the still.  The still dropped
    # principal_angle() so the path is drawn in the vehicle frame at t=0, the
    # same frame as the raw-sensor panels; keeping the rotation here would have
    # left the page showing the same drive at two different orientations.
    d["axl"], d["ayl"] = S.integrate(d["lt"], d["lvf"], d["lvl"], d["lwz"])
    d["axg"], d["ayg"] = S.integrate(d["gt"], d["gv"], np.zeros_like(d["gv"]), d["gwz"])
    d["bxr"], d["byr"] = S.integrate(d["rt"], d["rvy"], d["rvx"], rwz)
    d["bxc"], d["byc"] = S.integrate(d["ct"], d["cvx"], np.zeros_like(d["cvx"]), d["cwz"])

    def lims(xs, ys, pad=0.08):
        x0, x1 = min(x.min() for x in xs), max(x.max() for x in xs)
        y0, y1 = min(y.min() for y in ys), max(y.max() for y in ys)
        mx, my = (x1 - x0) * pad + 1e-6, (y1 - y0) * pad + 1e-6
        return (x0 - mx, x1 + mx), (y0 - my, y1 + my)

    d["limA"] = lims([d["axl"], d["axg"]], [d["ayl"], d["ayg"]])
    d["limB"] = lims([d["bxr"], d["bxc"]], [d["byr"], d["byc"]])
    d["limG"] = lims([d["gfx"]], [d["gfy"]], 0.12)
    d["ylim_av"] = (min(d["lspd"].min(), d["gv"].min()) - 0.6,
                    max(d["lspd"].max(), d["gv"].max()) + 0.6)
    d["ylim_aw"] = (min(d["lwz"].min(), d["gwz"].min()) - 0.02,
                    max(d["lwz"].max(), d["gwz"].max()) + 0.02)
    d["ylim_bv"] = (min(d["rspd"].min(), d["cvx"].min()) - 0.6,
                    max(d["rspd"].max(), d["cvx"].max()) + 0.6)
    d["ylim_bw"] = (d["cwz"].min() - 0.02, d["cwz"].max() + 0.02)
    d["ylim_can_v"] = (d["cvx"].min() * 3.6 - 1.5, d["cvx"].max() * 3.6 + 1.5)
    d["ylim_can_w"] = (np.degrees(d["cwz"]).min() - 1.0,
                       np.degrees(d["cwz"]).max() + 1.0)
    return d


D = _prep()


def _trail_to(ax, x, y, tarr, T, color, lw):
    n = int(np.searchsorted(tarr, T, side="right"))
    if n < 3:
        ax.plot([x[0]], [y[0]], "o", ms=4.2, mfc="white", mec=color, mew=1.4, zorder=5)
        return
    S.trail(ax, x[:n], y[:n], color, lw=lw)


def _grown(ax, t, v, T, color, lw, ls="-", marker=None):
    ax.plot(t, v, color=color, lw=lw, ls=ls, alpha=0.16, zorder=2)
    m = t <= T
    if m.sum() >= 2:
        ax.plot(t[m], v[m], color=color, lw=lw, ls=ls, marker=marker, ms=2.6, zorder=3)
    ax.axvline(T, color="#94a3b8", lw=0.8, zorder=4)


def render(i):
    T = float(FT[i])
    fig = plt.figure(figsize=(S.FIG_W, S.FIG_H), dpi=120)
    outer = fig.add_gridspec(1, 2, wspace=0.200, left=0.050, right=0.958,
                             top=0.822, bottom=0.058)

    def band(col):
        g = outer[col].subgridspec(2, 2, hspace=0.60, wspace=0.36,
                                   height_ratios=[1.0, 0.96])
        a0 = fig.add_subplot(g[0, 0])
        a1 = fig.add_subplot(g[0, 1])
        a2 = fig.add_subplot(g[1, 0])
        sg = g[1, 1].subgridspec(2, 1, hspace=0.16)
        s0 = fig.add_subplot(sg[0, 0])
        s1 = fig.add_subplot(sg[1, 0], sharex=s0)
        return a0, a1, a2, s0, s1

    A0, A1, A2, AS0, AS1 = band(0)
    B0, B1, B2, BS0, BS1 = band(1)

    fig.text(0.050, 0.976, "One interface, four front ends",
             fontsize=17.5, fontweight="bold", ha="left", va="center", color=S.FG)
    fig.text(0.050, 0.948,
             "Each tinted column is one drive: two different physical devices on top, and the dashed "
             "ODOMETRY card below holding what both of them were reduced to.  Badge “paper” marks the "
             "front end used in the paper’s experiments.",
             fontsize=9.3, ha="left", va="center", color=S.MUT)
    fig.text(0.958, 0.976, "t = %5.2f s" % T, fontsize=12.0, ha="right", va="center",
             color=S.MUT, family="DejaVu Sans Mono")

    # ------------------------------------------------------------- band A
    pts = Q["a2d2_cloud"][i]
    S.lidar_height_scatter(A0, pts)
    for rr in (20, 40, 60):
        th = np.linspace(-np.pi / 2, np.pi / 2, 120)
        A0.plot(rr * np.cos(th), rr * np.sin(th), color="#b9c2cf", lw=0.5,
                ls=(0, (3, 3)), zorder=1)
        A0.text(rr * np.cos(np.radians(-27)), rr * np.sin(np.radians(-27)), "%d m" % rr,
                fontsize=6.2, color="#8f9aa8", ha="center", va="center", zorder=1,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.75))
    A0.plot([0], [0], marker="s", ms=5.0, color=S.C_LIDAR, zorder=5)
    A0.set_xlim(-4, 64)
    A0.set_ylim(-34, 34)
    A0.set_aspect("equal")
    A0.set_xlabel("x [m]  (sensor frame)", fontsize=7.8)
    A0.set_ylabel("y [m]", fontsize=7.8)
    S.tidy(A0, grid=False)
    S.head(A0, "SENSOR A  ·  LiDAR", "shown: live scan, FRONT_CENTER", S.C_LIDAR,
           device="Velodyne VLP-16, FRONT_CENTER view  ·  ≈ 30 Hz",
           measures="range + bearing to surfaces  →  scan matching",
           badge=("paper", S.BADGE_PAPER))

    shown = D["gft"] <= T
    A1.plot(D["gfx"], D["gfy"], "-", color=S.C_GNSS, lw=0.9, alpha=0.16, zorder=2)
    if shown.sum() >= 2:
        A1.plot(D["gfx"][shown], D["gfy"][shown], "-", color=S.C_GNSS, lw=0.9,
                alpha=0.5, zorder=3)
    if shown.sum() >= 1:
        A1.scatter(D["gfx"][shown], D["gfy"][shown], s=17, facecolor="white",
                   edgecolor=S.C_GNSS, linewidths=1.0, zorder=4)
    A1.set_xlim(*D["limG"][0])
    A1.set_ylim(*D["limG"][1])
    A1.set_aspect("equal", adjustable="datalim")
    A1.set_xlabel("east [m]  (local tangent plane)", fontsize=7.8)
    A1.set_ylabel("north [m]", fontsize=7.8)
    S.tidy(A1)
    S.head(A1, "SENSOR B  ·  GNSS", "shown: %d of %d fixes at %.1f Hz"
           % (int(shown.sum()), META["a2d2_gnss_n"], META["a2d2_gnss_rate_hz"]),
           S.C_GNSS, ("demo", S.BADGE_SAME),
           device="vehicle-bus GNSS, position only  ·  1 Hz fix",
           measures="absolute position on Earth  →  differencing fixes")

    _trail_to(A2, D["axl"], D["ayl"], D["lt"], T, S.C_LIDAR, 2.4)
    _trail_to(A2, D["axg"], D["ayg"], D["gt"], T, S.C_GNSS, 1.7)
    A2.set_xlim(*D["limA"][0])
    A2.set_ylim(*D["limA"][1])
    A2.set_aspect("equal", adjustable="datalim")
    A2.set_xlabel("x [m]  (vehicle frame at t=0)", fontsize=7.8)
    A2.set_ylabel("y [m]", fontsize=7.8)
    S.tidy(A2)
    A2.legend(handles=[Line2D([], [], color=S.C_LIDAR, lw=2.4, label="from LiDAR twist"),
                       Line2D([], [], color=S.C_GNSS, lw=1.7, label="from GNSS twist")],
              loc="lower left", fontsize=7.2, frameon=True, framealpha=0.94,
              edgecolor="none", facecolor="white", handlelength=1.5, borderpad=0.3,
              labelspacing=0.25)
    S.head(A2, "Trajectory from (v, ω)", "dead-reckoned, trail grows with the drive", S.FG)

    _grown(AS0, D["lt"], D["lspd"], T, S.C_LIDAR, 1.5)
    _grown(AS0, D["gt"], D["gv"], T, S.C_GNSS, 1.3, ls=(0, (4, 2)), marker="o")
    AS0.set_ylim(*D["ylim_av"])
    AS0.set_ylabel("|v| [m/s]", fontsize=7.8)
    AS0.tick_params(labelbottom=False)
    S.tidy(AS0)
    AS0.legend(handles=[Line2D([], [], color=S.C_LIDAR, lw=1.5, label="LiDAR"),
                        Line2D([], [], color=S.C_GNSS, lw=1.3, ls=(0, (4, 2)), label="GNSS")],
               loc="lower left", fontsize=7.2, frameon=False, ncol=2,
               handlelength=1.6, borderpad=0.1, columnspacing=1.1)
    _grown(AS1, D["lt"], D["lwz"], T, S.C_LIDAR, 1.5)
    _grown(AS1, D["gt"], D["gwz"], T, S.C_GNSS, 1.3, ls=(0, (4, 2)), marker="o")
    AS1.set_ylim(*D["ylim_aw"])
    AS1.set_xlim(0, WIN)
    AS1.set_ylabel("$\\omega_z$ [rad/s]", fontsize=7.8)
    AS1.set_xlabel("time in window [s]", fontsize=7.8)
    S.tidy(AS1)
    S.head(AS0, "The twist, as delivered", "same two numbers per frame, whatever the sensor",
           S.FG)

    # ------------------------------------------------------------- band B
    k = int(np.argmin(np.abs(Q["radar_t"] - T)))
    a, b = int(Q["radar_off"][k]), int(Q["radar_off"][k + 1])
    az = Q["radar_az"][a:b].astype(float)
    vr = Q["radar_vr"][a:b].astype(float)
    rng = Q["radar_rng"][a:b].astype(float)
    inl = Q["radar_inl"][a:b].astype(bool)
    fit = Q["radar_fit"][k]
    picked = S.radar_doppler_bev(B0, az, vr, rng)
    B0.legend(handles=[Line2D([], [], marker="o", ls="none", color="#94a3b8",
                              alpha=0.5, label="all detections"),
                       Line2D([], [], marker="o", ls="none",
                              color=S.DOPPLER_CMAP(S.DOPPLER_NORM(-6)),
                              label="selected + Doppler vector")],
              loc="upper right", fontsize=7.0, frameon=False, handlelength=1.3,
              borderpad=0.1, labelspacing=0.22)
    can_v = float(np.interp(float(Q["radar_t"][k]), D["ct"], D["cvx"]))
    B0.text(0.028, 0.045,
            "fitted ego-velocity\n"
            "$v$ = (%.2f, %.2f) m/s\n"
            "$|v|$ %.2f  ·  CAN %.2f m/s"
            % (fit[0], fit[1], float(np.hypot(fit[0], fit[1])), can_v),
            transform=B0.transAxes, ha="left", va="bottom", fontsize=7.2,
            color=S.FG, linespacing=1.45, zorder=6,
            bbox=dict(boxstyle="round,pad=0.38", fc="white", ec=S.C_RADAR,
                      lw=0.8, alpha=0.94))
    S.head(B0, "SENSOR A  ·  radar", "shown: live BEV, %d returns  ·  %d vectors"
           % (len(az), len(picked)), S.C_RADAR, ("paper", S.BADGE_PAPER),
           device="77 GHz series radar, sensor 1  ·  %.1f scans/s"
                  % (META["rs_usable_scans"] / WIN),
           measures="range, azimuth, Doppler  →  one-scan least squares")

    lo = min(max(T - 1.0, 0.0), WIN - 2.0)
    zm = (D["ct"] >= lo) & (D["ct"] <= lo + 2.0)
    B1.step(D["ct"][zm], D["cvx"][zm] * 3.6, where="post", color=S.C_CAN, lw=1.5)
    B1.plot(D["ct"][zm], D["cvx"][zm] * 3.6, "o", ms=2.4, color=S.C_CAN)
    B1.set_xlim(lo, lo + 2.0)
    B1.set_ylim(*D["ylim_can_v"])
    B1.set_ylabel("wheel speed [km/h]", fontsize=7.8, color=S.C_CAN)
    B1.tick_params(axis="y", colors=S.C_CAN)
    B1b = B1.twinx()
    B1b.step(D["ct"][zm], np.degrees(D["cwz"][zm]), where="post", color=S.C_YAW,
             lw=1.3, ls=(0, (4, 2)))
    B1b.set_ylim(*D["ylim_can_w"])
    B1b.set_ylabel("")
    B1b.text(1.0, 1.012, "yaw rate [deg/s]", transform=B1b.transAxes,
             ha="right", va="bottom", fontsize=7.4, color=S.C_YAW)
    B1b.tick_params(axis="y", colors=S.C_YAW, labelsize=7.6, length=2.6)
    B1b.spines["top"].set_visible(False)
    B1.set_xlabel("time in window [s]", fontsize=7.8)
    S.tidy(B1)
    S.head(B1, "SENSOR B  ·  CAN bus", "shown: 2 s sliding window",
           S.C_CAN, ("demo", S.BADGE_SAME),
           device="wheel encoders + yaw-rate gyro  ·  %.0f Hz" % (len(D["ct"]) / WIN),
           measures="wheel rotation + yaw rate  →  vehicle kinematics")

    _trail_to(B2, D["bxr"], D["byr"], D["rt"], T, S.C_RADAR, 2.4)
    _trail_to(B2, D["bxc"], D["byc"], D["ct"], T, S.C_CAN, 1.7)
    B2.set_xlim(*D["limB"][0])
    B2.set_ylim(*D["limB"][1])
    B2.set_aspect("equal", adjustable="datalim")
    B2.set_xlabel("x [m]  (vehicle frame at t=0)", fontsize=7.8)
    B2.set_ylabel("y [m]", fontsize=7.8)
    S.tidy(B2)
    B2.legend(handles=[Line2D([], [], color=S.C_RADAR, lw=2.4, label="from radar twist"),
                       Line2D([], [], color=S.C_CAN, lw=1.7, label="from CAN twist")],
              loc="lower right", fontsize=7.2, frameon=True, framealpha=0.94,
              edgecolor="none", facecolor="white", handlelength=1.5, borderpad=0.3,
              labelspacing=0.25)
    S.head(B2, "Trajectory from (v, ω)", "dead-reckoned, trail grows with the drive", S.FG)

    _grown(BS0, D["rt"], D["rspd"], T, S.C_RADAR, 1.5)
    _grown(BS0, D["ct"], D["cvx"], T, S.C_CAN, 1.3, ls=(0, (4, 2)))
    BS0.set_ylim(*D["ylim_bv"])
    BS0.set_ylabel("|v| [m/s]", fontsize=7.8)
    BS0.tick_params(labelbottom=False)
    S.tidy(BS0)
    BS0.legend(handles=[Line2D([], [], color=S.C_RADAR, lw=1.5, label="radar Doppler"),
                        Line2D([], [], color=S.C_CAN, lw=1.3, ls=(0, (4, 2)), label="CAN")],
               loc="lower left", fontsize=7.2, frameon=False, ncol=2,
               handlelength=1.6, borderpad=0.1, columnspacing=1.1)
    _grown(BS1, D["ct"], D["cwz"], T, S.C_CAN, 1.5)
    BS1.set_ylim(*D["ylim_bw"])
    BS1.set_xlim(0, WIN)
    BS1.set_ylabel("$\\omega_z$ [rad/s]", fontsize=7.8)
    BS1.set_xlabel("time in window [s]", fontsize=7.8)
    S.tidy(BS1)
    S.head(BS0, "The twist, as delivered", "one 2-D radar gives no ω, so ω comes from CAN",
           S.FG)

    fig.canvas.draw()
    S.band_box(fig, [A0, A1, A2, AS0, AS1], S.BANDS["a2d2"])
    S.band_box(fig, [B0, B1, B2, BS0, BS1], S.BANDS["rs"])
    S.assemble(fig, [A0], [A1], [A2, AS0, AS1], (S.C_LIDAR, S.C_GNSS),
               S.BANDS["a2d2"]["accent"],
               "both devices deliver (v, ω) on their own clock")
    S.assemble(fig, [B0], [B1, B1b], [B2, BS0, BS1], (S.C_RADAR, S.C_CAN),
               S.BANDS["rs"]["accent"],
               "both devices deliver (v, ω) on their own clock")

    out = OUTDIR / ("%05d.png" % i)
    fig.savefig(out, dpi=120, facecolor="white")
    plt.close(fig)
    return str(out)


if __name__ == "__main__":
    OUTDIR = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/frontends_frames")
    os.environ["FR_OUTDIR"] = str(OUTDIR)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    nw = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    idx = list(range(len(FT)))
    if os.environ.get("SMOKE"):
        idx = [0, 60, 120, 180, 239]
    with Pool(nw) as p:
        for j, _ in enumerate(p.imap_unordered(render, idx, chunksize=2)):
            if j % 20 == 0:
                print("frame %d/%d" % (j, len(idx)), flush=True)
    print("FRONTENDS_ANIM_DONE %d frames -> %s" % (len(idx), OUTDIR))
