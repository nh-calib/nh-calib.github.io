#!/usr/bin/env python3
"""Stage-2 (relative p_y) replay on real A2D2 data, keyed to the drive clock.

Left   full-drive CAN-integrated ego path; the cursor runs the drive and each
       gated turn segment lights up as it is traversed.
Right  one dot per *completed* turn segment at its end time, and the running
       joint fit  dI_k = dpy * W_k + beta * T_k  (weighted, w_k = |W_k|^-1.5)
       re-solved from the segments finished so far.

Everything is read from the dumps produced by make_hero_real.py (stage dump)
and dump_a2d2_stage1_fixeddt.py; no estimator is re-implemented beyond the
two-parameter weighted solve, which is asserted against the published fit.

Run on ailab-12:
    /home/ailab-12/miniforge3/envs/nhcalib/bin/python make_hero_py_real.py
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

SEG = Path("/home/ailab-12/hero_real_20260921/hero_segments.npz")
META = Path("/home/ailab-12/hero_real_20260921/hero_meta.json")
PATH = Path("/home/ailab-12/nh_calib_lidar/a2d2_s0d_dump_20260921/"
            "s0d_front_center_m3.npz")
WORK = Path("/home/ailab-12/hero_py_real_20260921")

FPS = 30
N_FRAMES = 255
N_SWEEP = 205                      # frames spent driving; the rest holds

INK, MUTED, RULE, SOFT = "#191919", "#666666", "#d8d8d8", "#f7f7f5"
C_REF, C_TGT = "#191919", "#a52e29"


def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def wfit(W, T, Z, w):
    """The Step-4 two-parameter weighted solve: Z = dpy*W + beta*T."""
    A = np.stack([W, T], 1) * np.sqrt(w)[:, None]
    sol, *_ = np.linalg.lstsq(A, Z * np.sqrt(w), rcond=None)
    return float(sol[0]), float(sol[1])


def main():
    d = np.load(SEG)
    meta = json.loads(META.read_text())
    p = np.load(PATH)

    W, T, Z, wt = d["seg_W"], d["seg_T"], d["seg_Z"], d["seg_weight"]
    s0, s1 = d["seg_start"], d["seg_end"]
    est, gt_rel = float(d["delta_py_m"]), float(d["gt_rel_m"])
    n_seg = int(d["n_segments"])
    order = np.argsort(s1)                      # reveal in drive order

    dpy_all, beta_all = wfit(W, T, Z, wt)
    assert abs(dpy_all - est) < 1e-9, (dpy_all, est)
    assert abs(beta_all - float(d["beta_mps"])) < 1e-9

    ratio_mm = 1000.0 * Z / W                   # per-turn dI / int(omega dt)
    long_seg = T > 10.0                         # multi-turn windows

    ct, cx, cy = p["ch_t"], p["ch_x"], p["ch_y"]
    t0 = float(ct[0])
    t1 = float(s1.max()) + 20.0
    keep = ct <= t1 + 1.0
    ct, cx, cy = ct[keep], cx[keep], cy[keep]
    seg_mask = np.zeros(ct.size, bool)
    for a, b in zip(s0, s1):
        seg_mask |= (ct >= a) & (ct <= b)

    span = max(cx.max() - cx.min(), cy.max() - cy.min())
    mx, my = 0.5 * (cx.min() + cx.max()), 0.5 * (cy.min() + cy.max())
    half = 0.56 * span

    tmin, tmax = 0.0, t1 - t0
    ylo = min(ratio_mm.min(), 1000.0 * gt_rel) - 14.0
    yhi = max(ratio_mm.max(), 1000.0 * gt_rel) + 22.0

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "text.color": INK,
        "axes.edgecolor": RULE, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "figure.facecolor": "white", "savefig.facecolor": "white"})

    frames = WORK / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    for old in frames.glob("f*.png"):
        old.unlink()

    running = []
    for f in range(N_FRAMES):
        u = ease(min(f, N_SWEEP - 1) / float(N_SWEEP - 1))
        tc = t0 + (t1 - t0) * u
        done = np.where(s1 <= tc)[0]
        k = done.size
        if k >= 2:
            dpy_k, beta_k = wfit(W[done], T[done], Z[done], wt[done])
        else:
            dpy_k, beta_k = float("nan"), float("nan")
        running.append(dpy_k)

        fig = plt.figure(figsize=(19.2, 10.8), dpi=100)
        fig.text(0.035, 0.957, "Stage 2 on the real drive  -  one dot per "
                 "gated turn segment", fontsize=26, fontweight="bold",
                 color=INK, va="center")
        fig.text(0.035, 0.913, "A2D2  20180810_150607   |   LiDAR ego-motion "
                 "only, no target and no shared field of view",
                 fontsize=18, color=MUTED, va="center")
        fig.text(0.975, 0.957, "reference  FRONT_CENTER", fontsize=20,
                 color=C_REF, ha="right", va="center", fontweight="bold")
        fig.text(0.975, 0.913, "target  FRONT_LEFT", fontsize=20,
                 color=C_TGT, ha="right", va="center", fontweight="bold")

        # ---------------------------------------------------------- left BEV
        ax = fig.add_axes([0.042, 0.150, 0.404, 0.672])
        ax.set_facecolor(SOFT)
        ax.set_xlim(mx - half, mx + half)
        ax.set_ylim(my - half, my + half)
        ax.set_aspect("equal")
        ax.grid(True, color=RULE, lw=0.8)
        ax.tick_params(labelsize=15)
        ax.set_xlabel("east [m]", fontsize=16)
        ax.set_ylabel("north [m]", fontsize=16)
        ax.set_title("the whole drive, gated turns in red", fontsize=19,
                     color=INK, pad=12)

        drv = ct <= tc
        ax.plot(cx, cy, color="#c6cfda", lw=1.9, zorder=1)
        ax.plot(cx[drv], cy[drv], color=MUTED, lw=1.9, zorder=2)
        sd = seg_mask & drv
        ax.plot(np.where(sd, cx, np.nan), np.where(sd, cy, np.nan),
                color=C_TGT, lw=4.2, solid_capstyle="round", zorder=3)
        if drv.any():
            ax.plot(cx[drv][-1], cy[drv][-1], "o", ms=14, mfc="white",
                    mec=INK, mew=2.6, zorder=5)
        ax.legend(handles=[
            Line2D([], [], color=MUTED, lw=2.0, label="driven so far"),
            Line2D([], [], color=C_TGT, lw=4.0, label="gated turn segment")],
            loc="upper right", fontsize=15, frameon=True, framealpha=0.94,
            edgecolor=RULE)
        ax.text(0.025, 0.030, "t = %5.1f s   |   segments closed  %2d / %d"
                % (tc - t0, k, n_seg), transform=ax.transAxes, fontsize=17,
                color=INK, va="bottom", ha="left",
                bbox=dict(facecolor="white", edgecolor=RULE, pad=5.0))

        # ------------------------------------------------------ right readout
        ax2 = fig.add_axes([0.515, 0.545, 0.455, 0.277])
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2.axis("off")
        ax2.add_patch(Rectangle((0, 0), 1, 1, transform=ax2.transAxes,
                                facecolor=SOFT, edgecolor=RULE, lw=1.2))
        final = f >= N_SWEEP
        ax2.text(0.035, 0.860, "$\\Delta p_y$   FRONT_LEFT $-$ FRONT_CENTER",
                 fontsize=21, color=INK, va="center", fontweight="bold")
        lab = "joint fit, all %d segments" % n_seg if final else \
              "joint fit so far (%d segments)" % k
        ax2.text(0.035, 0.620, lab, fontsize=19, color=MUTED, va="center")
        ax2.text(0.965, 0.620,
                 "--" if not np.isfinite(dpy_k) else "%.1f mm" % (1000 * dpy_k),
                 fontsize=34, color=C_REF, va="center", ha="right",
                 fontweight="bold")
        ax2.text(0.035, 0.390, "ground truth", fontsize=19, color=MUTED,
                 va="center")
        ax2.text(0.965, 0.390, "%.1f mm" % (1000 * gt_rel), fontsize=34,
                 color=INK, va="center", ha="right")
        ax2.text(0.035, 0.160, "error", fontsize=19, color=MUTED, va="center")
        ax2.text(0.965, 0.160,
                 "--" if not np.isfinite(dpy_k) else
                 "%+.1f mm" % (1000 * (dpy_k - gt_rel)),
                 fontsize=34, color=C_TGT, va="center", ha="right",
                 fontweight="bold")

        # --------------------------------------------------- right dot panel
        ax3 = fig.add_axes([0.515, 0.150, 0.455, 0.300])
        ax3.set_facecolor(SOFT)
        ax3.set_xlim(tmin, tmax)
        ax3.set_ylim(ylo, yhi)
        ax3.grid(True, color=RULE, lw=0.8)
        ax3.tick_params(labelsize=15)
        ax3.set_xlabel("drive time [s]", fontsize=16)
        ax3.set_ylabel("$\\Delta I\\,/\\!\\int\\!\\omega\\,dt$   [mm]",
                       fontsize=16)
        ax3.set_title("each closed turn drops one point; the fit uses them all",
                      fontsize=19, color=INK, pad=12)
        ax3.axhline(1000 * gt_rel, color=INK, lw=2.0, ls="--", zorder=2)
        if k:
            sel = [i for i in order if s1[i] <= tc]
            xs = [s1[i] - t0 for i in sel]
            ys = [ratio_mm[i] for i in sel]
            mk = [long_seg[i] for i in sel]
            ax3.plot([x for x, m in zip(xs, mk) if not m],
                     [y for y, m in zip(ys, mk) if not m], "o", ms=14,
                     color=C_TGT, mec="white", mew=1.8, zorder=5, ls="none")
            ax3.plot([x for x, m in zip(xs, mk) if m],
                     [y for y, m in zip(ys, mk) if m], "o", ms=16,
                     mfc="white", mec=C_TGT, mew=3.0, zorder=5, ls="none")
            if long_seg[sel[-1]]:
                ax3.annotate("one %.0f s window,\n%.1f rad of yaw"
                             % (T[sel[-1]], abs(W[sel[-1]])),
                             (xs[-1], ys[-1]), textcoords="offset points",
                             xytext=(-16, 16), fontsize=15, color=C_TGT,
                             ha="right", va="bottom")
        if np.isfinite(dpy_k):
            ax3.axhline(1000 * dpy_k, color=C_REF, lw=3.0, zorder=4)
        ax3.legend(handles=[
            Line2D([], [], color=C_REF, lw=3.0, label="joint fit  %s"
                   % ("--" if not np.isfinite(dpy_k)
                      else "%.1f mm" % (1000 * dpy_k))),
            Line2D([], [], color=INK, lw=2.0, ls="--",
                   label="ground truth  %.1f mm" % (1000 * gt_rel))],
            loc="upper right", fontsize=15, frameon=True, framealpha=0.94,
            edgecolor=RULE)

        fig.text(0.5, 0.072, "one point = one gated turn, its own path-length "
                 "difference divided by its own integrated yaw", fontsize=17,
                 color=MUTED, va="center", ha="center")
        fig.text(0.5, 0.030, "the joint fit solves $\\Delta I = \\Delta p_y "
                 "\\int\\!\\omega\\,dt + \\beta\\,T$ over all closed segments, "
                 "so it is not the average of the points",
                 fontsize=17, color=MUTED, va="center", ha="center")

        fig.savefig(frames / ("f%04d.png" % f))
        plt.close(fig)
        if f % 40 == 0:
            print("frame", f, flush=True)

    out = WORK / "out"
    out.mkdir(exist_ok=True)
    src = str(frames / "f%04d.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate",
                    str(FPS), "-i", src, "-vf", "scale=1280:-2", "-c:v",
                    "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
                    "-movflags", "+faststart", str(out / "hero_py_real.mp4")],
                   check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate",
                    str(FPS), "-i", src, "-vf", "scale=1280:-2", "-c:v",
                    "libvpx-vp9", "-b:v", "0", "-crf", "38", "-row-mt", "1",
                    str(out / "hero_py_real.webm")], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i",
                    str(frames / ("f%04d.png" % (N_FRAMES - 1))), "-vf",
                    "scale=1280:-2", str(out / "hero_py_real.png")],
                   check=True)

    first_ok = int(np.argmax([bool(np.isfinite(r)) for r in running]))
    (out / "hero_py_real_meta.json").write_text(json.dumps({
        "dataset": "A2D2", "drive": "20180810_150607", "dt_mode": "fixed",
        "reference": "FRONT_CENTER", "target": "FRONT_LEFT",
        "n_frames": N_FRAMES, "fps": FPS, "n_segments": n_seg,
        "delta_py_m": est, "gt_rel_m": gt_rel,
        "error_mm": 1000.0 * (est - gt_rel),
        "delta_py_se_m": float(d["delta_py_se_m"]),
        "beta_mps": beta_all, "refit_matches_published": True,
        "running_first_mm": 1000.0 * running[first_ok],
        "running_final_mm": 1000.0 * running[-1],
        "per_turn_ratio_mm": [float(v) for v in ratio_mm],
        "segment_end_s": [float(v - t0) for v in s1],
        "segment_T_s": [float(v) for v in T],
        "source_segments": str(SEG), "source_path": str(PATH),
        "published_meta": meta,
    }, indent=2), encoding="utf-8")
    print("PY_HERO_DONE", out, flush=True)


if __name__ == "__main__":
    main()
