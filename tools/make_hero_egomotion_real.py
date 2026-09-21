#!/usr/bin/env python3
"""Module 1 hero: raw LiDAR stream -> metric ego-motion, on real A2D2 data.

Left   one cached FRONT_CENTER scan per video frame, bird's-eye, in the SENSOR
       frame, coloured by height.  Nothing is transformed: this is exactly what
       the odometry front end is handed.
Right  the path that the same sensor's twist integrates to, drawn in the
       sensor's own start frame, growing one twist sample per video frame.
Column the forward speed and yaw rate of that twist -- the two numbers every
       later NH-Calib stage consumes -- with a cursor on the window profile.

Sources (nothing synthetic, nothing re-estimated here):
  scans  /media/ailab-12/3580-E7B41/nh_cache/a2d2_20180810_150607/cam_front_center
  twist  /home/ailab-12/nh_calib_lidar/a2d2_final_calibration_20260811/
         a2d2_lidar5_final_twist.npz   (keys FRONT_CENTER__{t,dt,vx,vy,wz})

The A2D2 fixed-dt condition is applied to the twist exactly as in
tools/dump_a2d2_stage1_fixeddt.py (the recorded per-frame stamps are a dataset
defect): v,w are rescaled by dt*FS and the stream is placed on a uniform FS Hz
grid.  Raw scan stamps are still used to look the cache frames up.

Run on ailab-12:
    /home/ailab-12/miniforge3/envs/nhcalib/bin/python make_hero_egomotion_real.py
    SMOKE=1 ... same ...            # 60-frame layout check
"""
from __future__ import annotations

import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.lines import Line2D

CACHE = Path("/media/ailab-12/3580-E7B41/nh_cache/a2d2_20180810_150607/"
             "cam_front_center")
TWIST = Path("/home/ailab-12/nh_calib_lidar/a2d2_final_calibration_20260811/"
             "a2d2_lidar5_final_twist.npz")
WORK = Path("/home/ailab-12/hero_egomotion_20260921")
INDEX = WORK / "fc_cache_index.npz"

DRIVE = "20180810_150607"
CH = "FRONT_CENTER"
FS = 30.0                     # A2D2 fixed-dt grid
FPS = 30
I0, NFRAMES = 1580, 300       # twist index of the window start, 10.0 s
MAX_PTS = 14000               # per-frame draw budget (uniform random, seeded)

FIGW, FIGH, DPI = 13.33, 6.0, 120
RECT_L = [0.040, 0.185, 0.300, 0.650]     # left  BEV axes, figure fraction
RECT_R = [0.400, 0.185, 0.300, 0.650]     # right BEV axes, same size
BOXA = (RECT_L[2] * FIGW) / (RECT_L[3] * FIGH)   # panel width / height

# BEV box in the sensor frame [m]; y span is set so the metres-square data
# box exactly fills the panel (no letterboxing under aspect="equal")
X_LO, X_HI = -4.0, 50.0       # +x forward
Y_HI = 0.5 * (X_HI - X_LO) * BOXA
Y_LO = -Y_HI                  # +y left
Z_LO, Z_HI = -2.5, 6.0        # height colour limits

FG, MUT, RULE, SOFT = "#10151d", "#475569", "#cbd5e1", "#f8fafc"
ACC, RED = "#2563eb", "#dc2626"
CMAP = LinearSegmentedColormap.from_list(
    "nh_height", ["#a8b6c6", "#64748b", "#334155", "#8f2320", RED])


# --------------------------------------------------------------------- data
def cache_index() -> tuple[np.ndarray, np.ndarray]:
    """Per-scan median point stamp [s] and file path, in time order."""
    if INDEX.exists():
        d = np.load(INDEX, allow_pickle=True)
        return d["tmid"], d["files"]
    files = sorted(glob.glob(str(CACHE / "*" / "*.npy")))
    tmid = np.empty(len(files))
    t0 = time.time()
    for i, f in enumerate(files):
        tmid[i] = float(np.median(np.asarray(
            np.load(f, mmap_mode="r")["timestamp"]))) / 1e6
    assert np.all(np.diff(tmid) > 0), "scan stamps are not monotone"
    WORK.mkdir(parents=True, exist_ok=True)
    np.savez(INDEX, tmid=tmid, files=np.array(files))
    print("cache index built in %.1f s, %d scans" % (time.time() - t0,
                                                     len(files)), flush=True)
    return tmid, np.array(files)


def fixed_dt_twist() -> dict:
    d = np.load(TWIST)
    t = d[f"{CH}__t"].astype(float)
    dt = d[f"{CH}__dt"].astype(float)
    k = dt * FS                                  # cached v was formed as d/dt
    n = t.size
    return dict(t_raw=t,
                t=t[0] + np.arange(n) / FS,
                dt=np.full(n, 1.0 / FS),
                vx=d[f"{CH}__vx"].astype(float) * k,
                vy=d[f"{CH}__vy"].astype(float) * k,
                wz=d[f"{CH}__wz"].astype(float) * k)


def integrate(vx, vy, wz, dt):
    """Sensor-frame twist -> 2D pose track in the sensor's own start frame."""
    yaw = np.cumsum(wz * dt) - wz[0] * dt[0]
    x = np.cumsum((vx * np.cos(yaw) - vy * np.sin(yaw)) * dt)
    y = np.cumsum((vx * np.sin(yaw) + vy * np.cos(yaw)) * dt)
    return x - x[0], y - y[0], yaw


# -------------------------------------------------------------------- frame
def draw(fig, st, k):
    fig.clf()
    fig.patch.set_facecolor("white")
    tr = st["t_rel"][k]

    fig.text(0.040, 0.955, "Module 1  ·  sensor ego-motion", fontsize=16,
             fontweight="bold", color=FG, va="center")
    fig.text(0.040, 0.905,
             "A2D2 %s  ·  LiDAR %s  ·  one cached scan per video "
             "frame, no transform applied" % (DRIVE, CH),
             fontsize=11, color=MUT, va="center")
    fig.text(0.985, 0.955, "raw stream  →  metric twist", fontsize=13,
             color=RED, ha="right", va="center", fontweight="bold")

    # ------------------------------------------------------------- left BEV
    axL = fig.add_axes(RECT_L)
    axL.set_facecolor(SOFT)
    P = st["cloud"]
    axL.scatter(P[:, 1], P[:, 0], s=2.0, c=P[:, 2], cmap=CMAP,
                norm=Normalize(Z_LO, Z_HI), lw=0, alpha=0.70, zorder=3,
                rasterized=True)
    axL.plot([0], [0], marker="P", ms=9, color=RED, mec="white", mew=1.0,
             zorder=6, ls="none")
    axL.annotate("sensor origin", (0, 0), textcoords="offset points",
                 xytext=(9, 4), fontsize=9.5, color=RED, zorder=6)
    axL.set_xlim(Y_HI, Y_LO)                     # +y left -> left of screen
    axL.set_ylim(X_LO, X_HI)
    axL.set_aspect("equal")
    axL.grid(alpha=0.25, lw=0.6, color=RULE)
    axL.tick_params(labelsize=9.5, colors=MUT)
    axL.set_xlabel("lateral  y [m]   (+left)", fontsize=10.5, color=MUT)
    axL.set_ylabel("forward  x [m]", fontsize=10.5, color=MUT)
    axL.set_title("raw point cloud, sensor frame", fontsize=12.5, color=FG,
                  pad=8)
    axL.text(0.025, 0.975, "scan %d of %d\n%s points" % (
        k + 1, st["n_frames"], format(st["npts"], ",d")),
        transform=axL.transAxes, va="top", ha="left", fontsize=10,
        family="DejaVu Sans Mono", color=FG, zorder=8,
        bbox=dict(fc="white", ec=RULE, boxstyle="round,pad=0.36"))

    cax = fig.add_axes([0.083, 0.072, 0.214, 0.014])
    cb = fig.colorbar(plt.cm.ScalarMappable(Normalize(Z_LO, Z_HI), CMAP),
                      cax=cax, orientation="horizontal", extend="both")
    cb.set_label("height  z [m]  (sensor frame)", fontsize=9, color=MUT,
                 labelpad=2)
    cb.ax.tick_params(labelsize=8, colors=MUT, length=2.5, pad=1)
    cb.outline.set_edgecolor(RULE)

    # ------------------------------------------------------------ right BEV
    axR = fig.add_axes(RECT_R)
    axR.set_facecolor(SOFT)
    px, py = st["px"], st["py"]
    axR.plot(py, px, color="#e6ebf2", lw=1.4, zorder=1)
    axR.plot(py[:k + 1], px[:k + 1], color=MUT, lw=2.0, zorder=3,
             solid_capstyle="round")
    h = 3.2
    ca, sa = np.cos(st["yaw"][k]), np.sin(st["yaw"][k])
    axR.annotate("", xy=(py[k] + h * sa, px[k] + h * ca), xytext=(py[k], px[k]),
                 arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.8,
                                 shrinkA=0, shrinkB=0), zorder=4)
    axR.plot(py[k], px[k], "o", ms=8, mfc="white", mec=RED, mew=2.0, zorder=5)
    axR.plot([0], [0], marker="P", ms=8, color=FG, mec="white", mew=1.0,
             zorder=5, ls="none")
    axR.set_xlim(st["plim"][1], st["plim"][0])
    axR.set_ylim(st["plim"][2], st["plim"][3])
    axR.set_aspect("equal")
    axR.grid(alpha=0.25, lw=0.6, color=RULE)
    axR.tick_params(labelsize=9.5, colors=MUT)
    axR.set_xlabel("lateral  y [m]   (+left)", fontsize=10.5, color=MUT)
    axR.set_ylabel("forward  x [m]", fontsize=10.5, color=MUT)
    axR.set_title("ego path from that stream, start frame", fontsize=12.5,
                  color=FG, pad=8)
    axR.text(0.025, 0.975, "travelled %5.1f m\nheading  %+6.1f°" % (
        st["arc"][k], np.degrees(st["yaw"][k])),
        transform=axR.transAxes, va="top", ha="left", fontsize=10,
        family="DejaVu Sans Mono", color=FG, zorder=8,
        bbox=dict(fc="white", ec=RULE, boxstyle="round,pad=0.36"))
    axR.legend(handles=[
        Line2D([], [], color="#e6ebf2", lw=1.8, label="window"),
        Line2D([], [], color=MUT, lw=2.0, label="integrated so far")],
        loc="lower right", fontsize=9, frameon=True, framealpha=0.95,
        edgecolor=RULE, handlelength=1.6, borderpad=0.4)

    # --------------------------------------------------------- readout col
    x0 = 0.752
    fig.text(x0, 0.828, "t = %5.2f s  /  %5.2f s" % (tr, st["t_rel"][-1]),
             fontsize=11, color=MUT, family="DejaVu Sans Mono", va="center")

    fig.text(x0, 0.768, "forward speed  v", fontsize=11, color=MUT,
             va="center")
    fig.text(x0, 0.697, "%.2f" % st["v"][k], fontsize=26, color=FG,
             fontweight="bold", va="center", family="DejaVu Sans Mono")
    fig.text(x0 + 0.090, 0.691, "m/s", fontsize=13, color=MUT, va="center")

    axv = fig.add_axes([x0 + 0.010, 0.540, 0.215, 0.110])
    axv.plot(st["t_rel"], st["v"], color=RULE, lw=1.4)
    axv.plot(st["t_rel"][:k + 1], st["v"][:k + 1], color=ACC, lw=1.8)
    axv.plot(tr, st["v"][k], "o", ms=4.5, color=ACC)
    _spark(axv, st["t_rel"], st["vlim"])

    fig.text(x0, 0.458, "yaw rate  ω", fontsize=11, color=MUT, va="center")
    fig.text(x0, 0.387, "%+.1f" % st["w"][k], fontsize=26, color=FG,
             fontweight="bold", va="center", family="DejaVu Sans Mono")
    fig.text(x0 + 0.090, 0.381, "°/s", fontsize=13, color=MUT, va="center")

    axw = fig.add_axes([x0 + 0.010, 0.230, 0.215, 0.110])
    axw.axhline(0.0, color=RULE, lw=0.8)
    axw.plot(st["t_rel"], st["w"], color=RULE, lw=1.4)
    axw.plot(st["t_rel"][:k + 1], st["w"][:k + 1], color=RED, lw=1.8)
    axw.plot(tr, st["w"][k], "o", ms=4.5, color=RED)
    _spark(axw, st["t_rel"], st["wlim"])

    fig.text(x0, 0.163, "the two numbers every later NH-Calib", fontsize=9.5,
             color=MUT, va="center")
    fig.text(x0, 0.132, "stage consumes", fontsize=9.5, color=MUT,
             va="center")

    fig.text(0.400, 0.048, "twist: FRONT_CENTER__{vx,vy,wz} from "
             "a2d2_lidar5_final_twist.npz, fixed-dt condition", fontsize=9,
             color=MUT, ha="left", va="center")
    fig.text(0.400, 0.019, "path: that same twist integrated on its own "
             "clock — no ground truth, no second sensor", fontsize=9,
             color=MUT, ha="left", va="center")


def _spark(ax, t, lim):
    ax.set_xlim(t[0], t[-1])
    ax.set_ylim(*lim)
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(RULE)
    ax.tick_params(labelsize=8, colors=MUT, length=2.5, pad=1)
    ax.set_xticks([t[0], t[-1]])
    ax.set_xticklabels(["0 s", "%.0f s" % round(t[-1])])
    ax.grid(alpha=0.2, lw=0.5, color=RULE)


# --------------------------------------------------------------------- main
def main():
    smoke = os.environ.get("SMOKE") == "1"
    tmid, files = cache_index()
    tw = fixed_dt_twist()

    sl = slice(I0, I0 + NFRAMES)
    vx, vy, wz = tw["vx"][sl], tw["vy"][sl], tw["wz"][sl]
    dt = tw["dt"][sl]
    t_raw = tw["t_raw"][sl]
    px, py, yaw = integrate(vx, vy, wz, dt)
    arc = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(px),
                                                    np.diff(py)))])

    # limits fixed from frame 0 to the whole window path, padded, then grown
    # to the panel aspect so metres stay square and the panel is filled
    cx, cy = 0.5 * (px.min() + px.max()), 0.5 * (py.min() + py.max())
    hx = 0.5 * np.ptp(px) + 4.0
    hy = 0.5 * np.ptp(py) + 4.0
    if hy / hx < BOXA:
        hy = hx * BOXA
    else:
        hx = hy / BOXA
    plim = (cy - hy, cy + hy, cx - hx, cx + hx)           # ylo yhi xlo xhi

    v = np.hypot(vx, vy)
    w = np.degrees(wz)
    vpad, wpad = 0.10 * max(np.ptp(v), 1.0), 0.12 * max(np.ptp(w), 1.0)

    # scan lookup on the raw scan clock
    j = np.clip(np.searchsorted(tmid, t_raw), 1, tmid.size - 1)
    pick = np.where(np.abs(tmid[j] - t_raw) < np.abs(tmid[j - 1] - t_raw),
                    j, j - 1)
    lag = np.abs(tmid[pick] - t_raw)

    st = dict(t_rel=tw["t"][sl] - tw["t"][I0], v=v, w=w, px=px, py=py,
              yaw=yaw, arc=arc, plim=plim, n_frames=NFRAMES,
              vlim=(v.min() - vpad, v.max() + vpad),
              wlim=(w.min() - wpad, w.max() + wpad))

    frames = WORK / ("frames_smoke" if smoke else "frames")
    frames.mkdir(parents=True, exist_ok=True)
    for old in frames.glob("f*.png"):
        old.unlink()

    order = (list(range(0, NFRAMES, NFRAMES // 59))[:59] + [NFRAMES - 1]
             if smoke else list(range(NFRAMES)))
    npts_used, npts_raw = [], []
    fig = plt.figure(figsize=(FIGW, FIGH), dpi=DPI)
    plt.rcParams.update({"font.family": "DejaVu Sans"})
    for n, k in enumerate(order):
        a = np.load(files[pick[k]], allow_pickle=True)
        P = np.stack([a["x"], a["y"], a["z"]], 1)
        npts_raw.append(int(P.shape[0]))
        m = ((P[:, 0] > X_LO) & (P[:, 0] < X_HI) &
             (P[:, 1] > Y_LO) & (P[:, 1] < Y_HI))
        P = P[m]
        if P.shape[0] > MAX_PTS:
            P = P[np.random.default_rng(7000 + k).choice(P.shape[0], MAX_PTS,
                                                         replace=False)]
        st["cloud"] = P
        st["npts"] = int(m.sum())
        npts_used.append(int(m.sum()))
        draw(fig, st, k)
        fig.savefig(frames / ("f%04d.png" % n), facecolor="white")
        if n % 50 == 0:
            print("frame", n, "/", len(order), flush=True)
    plt.close(fig)

    out = WORK / ("out_smoke" if smoke else "out")
    out.mkdir(exist_ok=True)
    src = str(frames / "f%04d.png")
    tag = "hero_egomotion_real"
    cmd_mp4 = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
               "-i", src, "-vf", "scale=1280:-2", "-c:v", "libx264",
               "-pix_fmt", "yuv420p", "-crf", "30", "-preset", "slow",
               "-movflags", "+faststart", str(out / (tag + ".mp4"))]
    cmd_webm = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                "-i", src, "-vf", "scale=1280:-2", "-c:v", "libvpx-vp9",
                "-b:v", "0", "-crf", "40", "-row-mt", "1",
                str(out / (tag + ".webm"))]
    cmd_png = ["ffmpeg", "-y", "-loglevel", "error", "-i",
               str(frames / ("f%04d.png" % (len(order) - 1))), "-vf",
               "scale=1280:-2", str(out / (tag + ".png"))]
    for c in (cmd_mp4, cmd_webm, cmd_png):
        subprocess.run(c, check=True)

    meta = {
        "dataset": "A2D2", "drive": DRIVE, "channel": CH,
        "role": "module 0 - sensor ego-motion (raw stream -> metric twist)",
        "dt_mode": "fixed", "fps": FPS, "n_frames": len(order),
        "duration_s": round(len(order) / FPS, 3),
        "twist_index_window": [I0, I0 + NFRAMES],
        "window_t_rel_drive_s": [float(tw["t"][I0] - tw["t"][0]),
                                 float(tw["t"][I0 + NFRAMES - 1] - tw["t"][0])],
        "window_t_unix_s": [float(t_raw[0]), float(t_raw[-1])],
        "window_duration_s": float(st["t_rel"][-1]),
        "scan_index_window": [int(pick[0]), int(pick[-1])],
        "scan_lookup_lag_s": {"median": float(np.median(lag)),
                              "max": float(lag.max())},
        "points_per_frame_raw": {"min": int(np.min(npts_raw)),
                                 "median": int(np.median(npts_raw)),
                                 "max": int(np.max(npts_raw))},
        "points_per_frame_in_box": {"min": int(np.min(npts_used)),
                                    "median": int(np.median(npts_used)),
                                    "max": int(np.max(npts_used))},
        "max_points_drawn": MAX_PTS,
        "bev_box_m": {"x": [X_LO, X_HI], "y": [Y_LO, Y_HI]},
        "height_colour_limits_m": [Z_LO, Z_HI],
        "speed_mps": {"min": float(v.min()), "max": float(v.max()),
                      "mean": float(v.mean())},
        "yaw_rate_degps": {"min": float(w.min()), "max": float(w.max())},
        "net_heading_change_deg": float(np.degrees(yaw[-1] - yaw[0])),
        "path_length_m": float(arc[-1]),
        "path_extent_m": {"x": [float(px.min()), float(px.max())],
                          "y": [float(py.min()), float(py.max())]},
        "sources": {
            "scan_cache": str(CACHE),
            "twist_npz": str(TWIST),
            "twist_keys": [f"{CH}__{s}" for s in
                           ("t", "dt", "vx", "vy", "wz")],
        },
        "commands": {
            "render": "SMOKE=%s /home/ailab-12/miniforge3/envs/nhcalib/bin/"
                      "python make_hero_egomotion_real.py"
                      % ("1" if smoke else "0"),
            "mp4": " ".join(cmd_mp4),
            "webm": " ".join(cmd_webm),
            "poster": " ".join(cmd_png),
        },
    }
    (out / (tag + "_meta.json")).write_text(json.dumps(meta, indent=2),
                                            encoding="utf-8")
    print("EGOMOTION_HERO_DONE", out, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
