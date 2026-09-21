#!/usr/bin/env python3
"""Build the S0b "real data" hero clip for the NH-Calib project page.

Run on ailab-12 (the A2D2 twist archive and ffmpeg live there):

    /home/ailab-12/miniforge3/envs/nhcalib/bin/python make_hero_real.py \
        --work /home/ailab-12/hero_real_20260921

Stages
    dump    reproduce the published A2D2 calibration and dump the Step-4
            common-window segments plus per-segment ego trajectories
    render  matplotlib frames
    encode  ffmpeg -> hero_real.mp4 / hero_real.webm / hero_real_poster.png

The published condition reproduced here is ``cpp_free`` of
``results/[260902]_[Table]_[SlipCoefficientAblation]/raw/nh_c_ablation_lidar2.py``:
fixed dt = 1/30 s renormalisation, M1 smoothing, M2 motion-plane levelling,
M3 yaw / p_x / slip, M4 common-window relative p_y with FRONT_CENTER as the
reference.  It returns delta_py(FRONT_CENTER -> FRONT_LEFT) = 0.581666639 m
against GT 0.580000044 m, i.e. +1.667 mm, over 11 gated turn segments.

No core algorithm file is modified; this script only reads nh_calib_core.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np

CORE_ROOT = "/home/ailab-12/git/nh_calib"
ASSET = "/home/ailab-12/nh_calib_lidar"
TWIST = ASSET + "/a2d2_final_calibration_20260811/a2d2_lidar5_final_twist.npz"
GT_JSON = ASSET + "/a2d2_gt.json"
SENSORS = ["FRONT_CENTER", "FRONT_LEFT", "FRONT_RIGHT", "SIDE_LEFT", "SIDE_RIGHT"]
REF, TGT = "FRONT_CENTER", "FRONT_LEFT"
FIELDS = ("t", "dt", "vx", "vy", "vz", "wx", "wy", "wz", "fitness", "rmse")
MOTION = ("vx", "vy", "vz", "wx", "wy", "wz")
FIXED_DT = 1.0 / 30.0

FPS = 30
N_FRAMES = 240                      # 8.0 s loop
P1, P2, P3 = 120, 150, 200          # phase boundaries in frames

INK = "#191919"
MUTED = "#666666"
RULE = "#d8d8d8"
SOFT = "#f7f7f5"
C_REF = "#191919"   # reference sensor; matches S0a (reference = ink, target = accent)
C_TGT = "#a52e29"


# --------------------------------------------------------------------- dump
def stage_dump(work):
    sys.path.insert(0, CORE_ROOT)
    from nh_calib_core.axis import levelling_matrix
    from nh_calib_core.pipeline import Settings, calibrate
    from nh_calib_core.planar import (_forward_velocity, level_twist,
                                      step4_relative_py_multisensor)

    ar = np.load(TWIST, allow_pickle=True)
    streams = {}
    for s in SENSORS:
        d = {f: np.asarray(ar[s + "__" + f], float).copy() for f in FIELDS}
        scale = d["dt"] / FIXED_DT          # fixed-dt velocity renormalisation
        for m in MOTION:
            d[m] *= scale
        d["dt"][:] = FIXED_DT
        streams[s] = d
    chassis = {"t": np.asarray(ar["chassis__ts"], float),
               "vx": np.asarray(ar["chassis__vx"], float),
               "vy": np.asarray(ar["chassis__vy"], float),
               "wz": np.asarray(ar["chassis__wz"], float)}
    gt = json.loads(Path(GT_JSON).read_text())

    cal = calibrate(streams, chassis, Settings())
    levelled, psi = {}, {}
    for s in SENSORS:
        e = cal["sensors"][s]
        levelled[s] = level_twist(
            streams[s], levelling_matrix(np.asarray(e["step2"]["axis"], float)))
        psi[s] = math.radians(float(e["psi_deg"]))

    res = step4_relative_py_multisensor(
        levelled, psi, REF,
        min_common_duration_s=0.5, min_omega_cosine=0.0, require_all=True)
    fit = res["target_results"][TGT]
    est = float(fit["delta_py_m"])
    gt_rel = float(gt[TGT]["py"] - gt[REF]["py"])
    print("FC->FL estimate_m=%.9f gt_m=%.9f error_mm=%+.4f n_seg=%d"
          % (est, gt_rel, (est - gt_rel) * 1000.0, fit["n_segments"]), flush=True)

    segs = fit["segments"]
    fwd = {s: _forward_velocity(levelled[s], psi[s]) for s in (REF, TGT)}
    px = {s: float(cal["sensors"][s]["px_m"]) for s in (REF, TGT)}

    traj = {}
    for k, m in enumerate(segs):
        t0, t1 = m["start_s"], m["end_s"]
        n = max(int(round((t1 - t0) / FIXED_DT)) + 1, 8)
        grid = np.linspace(t0, t1, n)
        entry = {}
        for role, name in (("ref", REF), ("tgt", TGT)):
            t = np.asarray(levelled[name]["t"], float)
            # same sample set as nh_calib_core.planar._window_integrals:
            # native samples strictly inside plus linearly interpolated ends
            inside = (t > t0) & (t < t1)

            def clip(a):
                a = np.asarray(a, float)
                return np.concatenate(([float(np.interp(t0, t, a))], a[inside],
                                       [float(np.interp(t1, t, a))]))

            st = np.concatenate(([t0], t[inside], [t1]))
            dst = np.diff(st)

            def cumtrap(a):
                return np.concatenate(
                    ([0.0], np.cumsum(0.5 * (a[1:] + a[:-1]) * dst)))

            vx, vy = clip(levelled[name]["vx"]), clip(levelled[name]["vy"])
            wz, fw = clip(levelled[name]["wz"]), clip(fwd[name])
            th, cum_i = cumtrap(wz), cumtrap(fw)
            c, sn = math.cos(psi[name]), math.sin(psi[name])
            vex, vey = c * vx - sn * vy, sn * vx + c * vy
            x = px[name] + cumtrap(np.cos(th) * vex - np.sin(th) * vey)
            y = (0.0 if role == "ref" else est) + cumtrap(
                np.sin(th) * vex + np.cos(th) * vey)
            entry[role] = dict(
                t=grid, x=np.interp(grid, st, x), y=np.interp(grid, st, y),
                th=np.interp(grid, st, th), wz=np.interp(grid, st, wz),
                fwd=np.interp(grid, st, fw), i_m=np.interp(grid, st, cum_i))
        traj[k] = entry

    work.mkdir(parents=True, exist_ok=True)
    extra = {}
    for k in traj:
        for r in ("ref", "tgt"):
            for f in ("t", "x", "y", "th", "wz", "fwd", "i_m"):
                extra["traj%d_%s_%s" % (k, r, f)] = traj[k][r][f]
    np.savez_compressed(
        work / "hero_segments.npz",
        seg_start=np.array([m["start_s"] for m in segs]),
        seg_end=np.array([m["end_s"] for m in segs]),
        seg_W=np.array([m["W_k_rad"] for m in segs]),
        seg_T=np.array([m["T_k_s"] for m in segs]),
        seg_Z=np.array([m["Z_k_m"] for m in segs]),
        seg_Iref=np.array([m["I_reference_m"] for m in segs]),
        seg_Itgt=np.array([m["I_target_m"] for m in segs]),
        seg_weight=np.array([m["weight"] for m in segs]),
        delta_py_m=est, delta_py_se_m=fit["delta_py_se_m"],
        beta_mps=fit["beta_mps"], gt_rel_m=gt_rel, rmse_m=fit["rmse_m"],
        n_segments=fit["n_segments"], **extra)
    (work / "hero_meta.json").write_text(json.dumps(dict(
        dataset="A2D2", drive="20180810_150607", reference=REF, target=TGT,
        twist=TWIST, fixed_dt_s=FIXED_DT, delta_py_m=est, gt_rel_m=gt_rel,
        error_mm=(est - gt_rel) * 1000.0, n_segments=int(fit["n_segments"]),
        delta_py_se_m=fit["delta_py_se_m"], beta_mps=fit["beta_mps"],
        rmse_m=fit["rmse_m"],
        psi_deg={s: float(cal["sensors"][s]["psi_deg"]) for s in SENSORS},
        px_m={s: float(cal["sensors"][s]["px_m"]) for s in SENSORS},
        slip_c=float(cal["slip"].get("c", float("nan"))),
    ), indent=2))
    print("DUMP_DONE", work, flush=True)


# ------------------------------------------------------------------- render
def ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3.0 - 2.0 * u)


def stage_render(work):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "text.color": INK,
        "axes.edgecolor": RULE, "axes.labelcolor": MUTED,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "figure.facecolor": "white", "savefig.facecolor": "white",
    })

    d = np.load(work / "hero_segments.npz")
    seg_w = d["seg_W"]
    seg_z = d["seg_Z"]
    seg_t = d["seg_T"]
    est = float(d["delta_py_m"])
    gt_rel = float(d["gt_rel_m"])
    n_seg = int(d["n_segments"])
    per_turn_mm = 1000.0 * seg_z / seg_w

    # Deterministic hero segment: the largest |integral omega dt| among the
    # single-manoeuvre segments (T < 10 s).  No hand-picked exception window.
    single = np.where(seg_t < 10.0)[0]
    hero = int(single[np.argmax(np.abs(seg_w[single]))])
    reveal = [hero] + [int(i) for i in np.argsort(np.abs(seg_w))[::-1]
                       if int(i) != hero]

    tr = {r: {f: d["traj%d_%s_%s" % (hero, r, f)] for f in
              ("t", "x", "y", "th", "wz", "fwd", "i_m")} for r in ("ref", "tgt")}
    n_pts = len(tr["ref"]["t"])
    t_rel = tr["ref"]["t"] - tr["ref"]["t"][0]
    d_i = tr["ref"]["i_m"] - tr["tgt"]["i_m"]
    w_t = tr["ref"]["th"]
    seg_dur = float(t_rel[-1])
    d_i_max = float(np.max(np.abs(d_i)))

    xs = np.concatenate([tr["ref"]["x"], tr["tgt"]["x"]])
    ys = np.concatenate([tr["ref"]["y"], tr["tgt"]["y"]])
    cx, cy = 0.5 * (xs.min() + xs.max()), 0.5 * (ys.min() + ys.max())
    half = 0.58 * max(xs.max() - xs.min(), ys.max() - ys.min())

    frames = work / "frames"
    frames.mkdir(exist_ok=True)
    for old in frames.glob("f*.png"):
        old.unlink()

    for f in range(N_FRAMES):
        fig = plt.figure(figsize=(19.2, 10.8), dpi=100)

        fig.text(0.035, 0.957,
                 "NH-Calib on real drive data  -  A2D2  20180810_150607",
                 fontsize=26, fontweight="bold", color=INK, va="center")
        fig.text(0.035, 0.913,
                 "LiDAR ego-motion only.  No calibration target, no shared "
                 "field of view.",
                 fontsize=18, color=MUTED, va="center")
        fig.text(0.975, 0.957, "reference  FRONT_CENTER", fontsize=20,
                 color=C_REF, ha="right", va="center", fontweight="bold")
        fig.text(0.975, 0.913, "target  FRONT_LEFT", fontsize=20,
                 color=C_TGT, ha="right", va="center", fontweight="bold")

        # ---- BEV panel (square: 0.377 * 1920 == 0.67 * 1080)
        ax = fig.add_axes([0.050, 0.160, 0.377, 0.670])
        ax.set_facecolor(SOFT)
        ax.set_xlim(cx - half, cx + half)
        ax.set_ylim(cy - half, cy + half)
        ax.set_aspect("equal")
        ax.grid(True, color=RULE, lw=0.8)
        ax.set_xlabel("x [m]", fontsize=17)
        ax.set_ylabel("y [m]", fontsize=17)
        ax.tick_params(labelsize=16)
        ax.set_title("Ego-motion of the two LiDARs through one gated turn",
                     fontsize=19, color=INK, pad=14)

        if f < P1:
            i = int(round(ease(f / float(P1 - 1)) * (n_pts - 1)))
        else:
            i = n_pts - 1
        i = max(i, 1)
        ax.plot(tr["ref"]["x"][:i + 1], tr["ref"]["y"][:i + 1],
                color=C_REF, lw=3.4, solid_capstyle="round", zorder=3)
        ax.plot(tr["tgt"]["x"][:i + 1], tr["tgt"]["y"][:i + 1],
                color=C_TGT, lw=3.4, solid_capstyle="round", zorder=3)
        ax.plot([tr["ref"]["x"][i]], [tr["ref"]["y"][i]], "o", ms=13,
                color=C_REF, mec="white", mew=2.0, zorder=5)
        ax.plot([tr["tgt"]["x"][i]], [tr["tgt"]["y"][i]], "o", ms=13,
                color=C_TGT, mec="white", mew=2.0, zorder=5)
        ax.legend(handles=[Line2D([], [], color=C_REF, lw=3.4,
                                  label="FRONT_CENTER"),
                           Line2D([], [], color=C_TGT, lw=3.4,
                                  label="FRONT_LEFT")],
                  loc="upper right", fontsize=16, frameon=True,
                  framealpha=0.92, edgecolor=RULE)

        # ---- live readout panel
        ax2 = fig.add_axes([0.500, 0.545, 0.475, 0.285])
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2.axis("off")
        ax2.add_patch(Rectangle((0, 0), 1, 1, transform=ax2.transAxes,
                                facecolor=SOFT, edgecolor=RULE, lw=1.2,
                                zorder=0))
        tt = float(t_rel[i])
        ax2.text(0.035, 0.895, "What the two ego-motions disagree about",
                 fontsize=19, fontweight="bold", color=INK, va="center")
        ax2.text(0.035, 0.745,
                 "turn segment %d of %d        t = %4.2f / %4.2f s"
                 % (hero + 1, n_seg, tt, seg_dur),
                 fontsize=18, color=MUTED, va="center")
        ax2.text(0.035, 0.600,
                 "integrated yaw   $\\int\\omega\\,dt$ = %+7.1f deg"
                 % math.degrees(w_t[i]),
                 fontsize=21, color=INK, va="center")
        ax2.text(0.035, 0.465,
                 "path length      %6.2f m    |    %6.2f m"
                 % (tr["ref"]["i_m"][i], tr["tgt"]["i_m"][i]),
                 fontsize=21, color=INK, va="center")
        ax2.text(0.035, 0.330,
                 "difference       $\\Delta I$ = %+6.3f m" % d_i[i],
                 fontsize=22, color=INK, va="center", fontweight="bold")
        frac = abs(d_i[i]) / max(d_i_max, 1e-9)
        ax2.add_patch(Rectangle((0.035, 0.185), 0.93, 0.065,
                                facecolor="white", edgecolor=RULE, lw=1.0))
        ax2.add_patch(Rectangle((0.035, 0.185), 0.93 * frac, 0.065,
                                facecolor=C_TGT, edgecolor="none"))
        if abs(w_t[i]) > 0.25:
            ax2.text(0.035, 0.080,
                     "$\\Delta I\\,/\\!\\int\\!\\omega\\,dt$ = %.0f mm   "
                     "(this turn alone)" % (1000.0 * d_i[i] / w_t[i]),
                     fontsize=20, color=C_TGT, va="center", ha="left")

        # ---- per-segment panel
        ax3 = fig.add_axes([0.500, 0.160, 0.475, 0.290])
        ax3.set_facecolor(SOFT)
        ax3.set_xlim(0.3, n_seg + 0.7)
        ax3.set_ylim(548, 622)
        ax3.grid(True, color=RULE, lw=0.8)
        ax3.tick_params(labelsize=16)
        ax3.set_xticks(range(1, n_seg + 1))
        ax3.set_xlabel("gated turn segment", fontsize=17)
        ax3.set_ylabel("$\\Delta I\\,/\\!\\int\\!\\omega\\,dt$  [mm]", fontsize=17)
        ax3.set_title("Every gated turn of the drive, then one joint fit",
                      fontsize=19, color=INK, pad=12)

        if f < P1:
            ax3.text(0.5 * (n_seg + 1), 585.0,
                     "one point per completed turn segment",
                     fontsize=18, color=MUTED, ha="center", va="center")
        else:
            if f < P2:
                n_show = 1
            elif f < P3:
                n_show = 1 + int(round(
                    ease((f - P2) / float(P3 - P2 - 1)) * (n_seg - 1)))
            else:
                n_show = n_seg
            shown = reveal[:n_show]
            ax3.plot([s + 1 for s in shown], [per_turn_mm[s] for s in shown],
                     "o", ms=13, color=C_TGT, mec="white", mew=1.8, zorder=4)
            ax3.text(0.55, 619.5, "one gated turn alone", fontsize=17,
                     color=C_TGT, va="top", ha="left",
                     bbox=dict(facecolor="white", edgecolor="none", pad=1.5))
        if f >= P3:
            a = ease((f - P3) / float(N_FRAMES - P3 - 1))
            ax3.axhline(1000.0 * gt_rel, color=INK, lw=2.0, ls="--", zorder=3)
            ax3.axhline(1000.0 * est, color=C_REF, lw=3.0, zorder=3,
                        alpha=0.35 + 0.65 * a)
            ax3.text(n_seg + 0.55, 1000.0 * gt_rel - 3.0,
                     "ground truth  %.1f mm" % (1000.0 * gt_rel),
                     fontsize=17, color=INK, ha="right", va="top")
            ax3.text(n_seg + 0.55, 1000.0 * est + 3.0,
                     "NH-Calib joint fit  %.1f mm" % (1000.0 * est),
                     fontsize=17, color=C_REF, ha="right", va="bottom",
                     fontweight="bold")

        # ---- final readout replaces the live panel
        if f >= P3:
            a = ease((f - P3) / float(N_FRAMES - P3 - 1))
            ax2.add_patch(Rectangle((0, 0), 1, 1, transform=ax2.transAxes,
                                    facecolor="white", edgecolor=RULE,
                                    lw=1.2, zorder=6, alpha=a))
            if a > 0.05:
                ax2.text(0.035, 0.855,
                         "$\\Delta p_y$   FRONT_LEFT $-$ FRONT_CENTER",
                         fontsize=21, color=INK, va="center", zorder=7,
                         alpha=a, fontweight="bold")
                ax2.text(0.035, 0.625, "estimated", fontsize=20, color=MUTED,
                         va="center", zorder=7, alpha=a)
                ax2.text(0.965, 0.625, "%.1f mm" % (1000.0 * est), fontsize=34,
                         color=C_REF, va="center", ha="right", zorder=7,
                         alpha=a, fontweight="bold")
                ax2.text(0.035, 0.395, "ground truth", fontsize=20,
                         color=MUTED, va="center", zorder=7, alpha=a)
                ax2.text(0.965, 0.395, "%.1f mm" % (1000.0 * gt_rel),
                         fontsize=34, color=INK, va="center", ha="right",
                         zorder=7, alpha=a)
                ax2.text(0.035, 0.175, "error", fontsize=20, color=MUTED,
                         va="center", zorder=7, alpha=a)
                ax2.text(0.965, 0.175, "%+.1f mm" % (1000.0 * (est - gt_rel)),
                         fontsize=34, color=C_TGT, va="center", ha="right",
                         zorder=7, alpha=a, fontweight="bold")

        fig.text(0.5, 0.068,
                 "A2D2 drive 20180810_150607   |   reference FRONT_CENTER "
                 "$\\rightarrow$ target FRONT_LEFT   |   %d gated turn segments"
                 % n_seg,
                 fontsize=17, color=MUTED, va="center", ha="center")
        fig.text(0.5, 0.026,
                 "$\\Delta I = I_{ref} - I_{tgt}$ is the path-length "
                 "difference.   Reference-relative $\\Delta p_y$ comes from the "
                 "joint fit $\\Delta I = \\Delta p_y \\int\\omega\\,dt + "
                 "\\beta\\,T$.",
                 fontsize=17, color=MUTED, va="center", ha="center")

        fig.savefig(frames / ("f%04d.png" % f))
        plt.close(fig)
        if f % 40 == 0:
            print("frame", f, flush=True)
    print("RENDER_DONE", frames, flush=True)


# ------------------------------------------------------------------- encode
def stage_encode(work):
    frames = work / "frames"
    out = work / "out"
    out.mkdir(exist_ok=True)
    mp4 = out / "hero_real.mp4"
    webm = out / "hero_real.webm"
    poster = out / "hero_real_poster.png"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
        "-i", str(frames / "f%04d.png"), "-an",
        "-c:v", "libx264", "-preset", "slow", "-crf", "24",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-vf", "scale=1920:1080", str(mp4)], check=True)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
        "-i", str(frames / "f%04d.png"), "-an",
        "-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "36", "-row-mt", "1",
        "-pix_fmt", "yuv420p", str(webm)], check=True)

    from PIL import Image
    last = sorted(frames.glob("f*.png"))[-1]
    img = Image.open(last).convert("RGB")
    for colors in (192, 128, 96, 64, 48):
        img.quantize(colors=colors, method=Image.MEDIANCUT,
                     dither=Image.NONE).save(poster, optimize=True)
        if poster.stat().st_size <= 300 * 1024:
            break
    for p in (mp4, webm, poster):
        print("SIZE %-24s %8.1f KB" % (p.name, p.stat().st_size / 1024.0),
              flush=True)
    print("ENCODE_DONE", out, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="/home/ailab-12/hero_real_20260921")
    ap.add_argument("--stages", default="dump,render,encode")
    a = ap.parse_args()
    work = Path(a.work)
    stages = [s.strip() for s in a.stages.split(",") if s.strip()]
    if "dump" in stages:
        stage_dump(work)
    if "render" in stages:
        stage_render(work)
    if "encode" in stages:
        stage_encode(work)
    print("HERO_REAL_DONE", flush=True)


if __name__ == "__main__":
    main()
