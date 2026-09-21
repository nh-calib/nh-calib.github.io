"""PROP-458 item2/3: render the A2D2 p_x / psi hero (fixed-dt condition).

Left  : CAN-integrated ego path, turn segments highlighted, cursor.
Right : omega vs slip-corrected lateral rate.  The M3 residual
            r = sin(psi)vx + cos(psi)vy - omega*px + vc*tan(c*vc*omega)
        rearranges to   y := lateral + vc*tan(c*vc*omega) = px * omega + r,
        so the through-origin slope of the accumulating cloud IS p_x.
Readout: running p_x, final psi, both against the A2D2 GT extrinsics.
"""
import json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

SRC = Path("/home/ailab-12/nh_calib_lidar/a2d2_s0d_dump_20260921")
OUT = Path("/home/ailab-12/nh_calib_lidar/a2d2_s0d_frames_20260921")
GTP = "/home/ailab-12/nh_calib_lidar/a2d2_gt.json"
CH = "FRONT_CENTER"
NFRAMES, FPS = 240, 30
FG, MUT, ACC, TURN = "#10151d", "#475569", "#2563eb", "#dc2626"

d = np.load(SRC / f"s0d_{CH.lower()}_m3.npz")
meta = json.loads((SRC / f"s0d_{CH.lower()}_meta.json").read_text())
gt = json.load(open(GTP))[CH]
assert meta["dt_mode"] == "fixed", meta["dt_mode"]

t, om, vc = d["t"], d["om"], d["vc"]
c, px_f, psi_f = float(meta["c"]), float(meta["px_m"]), float(meta["psi_deg"])
y = d["lateral"] + vc * np.tan(np.clip(c * vc * om, -1.4, 1.4))     # = px*omega + r
ct, cx, cy = d["ch_t"], d["ch_x"], d["ch_y"]
_w = (ct >= float(d["t"][0])) & (ct <= float(d["t"][-1]))
ct, cx, cy = ct[_w], cx[_w], cy[_w]
segs = meta["turn_segments"]
t0, t1 = float(t[0]), float(t[-1])


def slope(om_s, y_s):
    """Through-origin Huber IRLS slope -- same loss family as the core M3."""
    if len(om_s) < 12 or np.ptp(om_s) < 1e-3:
        return float("nan")
    b = float(om_s @ y_s / (om_s @ om_s))
    for _ in range(8):
        r = y_s - b * om_s
        sc = 1.4826 * np.median(np.abs(r)) + 1e-12
        w = np.minimum(1.0, 1.345 * sc / np.maximum(np.abs(r), 1e-12))
        b = float((w * om_s) @ y_s / ((w * om_s) @ om_s))
    return b


seg_mask = np.zeros(len(ct), bool)
for s in segs:
    seg_mask |= (ct >= s["start_s"]) & (ct <= s["end_s"])
OUT.mkdir(parents=True, exist_ok=True)
xlim = (-max(abs(np.degrees(om).min()), abs(np.degrees(om).max())) * 1.12,) * 1
W = max(abs(np.degrees(om)).max(), 1.0) * 1.12
H = max(abs(y).max(), 0.1) * 1.15

for k in range(NFRAMES):
    tc = t0 + (t1 - t0) * (k + 1) / NFRAMES
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(13.33, 6.0), dpi=120,
                                   gridspec_kw={"width_ratios": [1.0, 1.12]})
    fig.patch.set_facecolor("white")

    # ---- left: ego path -------------------------------------------------
    mp = ct <= tc
    axL.plot(cx, cy, color="#e8edf3", lw=1.4, zorder=1)
    axL.plot(cx[mp], cy[mp], color=MUT, lw=1.6, zorder=2)
    seg_done = seg_mask & mp
    xs = np.where(seg_done, cx, np.nan)
    axL.plot(xs, np.where(seg_done, cy, np.nan), color=TURN, lw=3.0, zorder=3,
             solid_capstyle="round")
    if mp.any():
        axL.plot(cx[mp][-1], cy[mp][-1], "o", ms=9, mfc=ACC, mec="white", mew=1.8, zorder=4)
    axL.set_aspect("equal")
    axL.set_title("CAN-integrated ego path   ·   turn segments in red",
                  fontsize=13, color=FG, pad=10)
    axL.set_xlabel("east [m]", fontsize=11); axL.set_ylabel("north [m]", fontsize=11)
    axL.grid(alpha=0.25, lw=0.6)
    n_done = sum(1 for s in segs if s["end_s"] <= tc + 1e-6)
    axL.text(0.98, 0.98, f"t = {tc - t0:6.1f} s\nturns completed: {n_done} / {len(segs)}",
             transform=axL.transAxes, va="top", ha="right", fontsize=11.5, color=FG, zorder=6,
             family="DejaVu Sans Mono",
             bbox=dict(fc="white", ec="#cbd5e1", boxstyle="round,pad=0.45"))

    # ---- right: omega vs slip-corrected lateral rate --------------------
    m = t <= tc
    axR.axhline(0, color="#cbd5e1", lw=0.9); axR.axvline(0, color="#cbd5e1", lw=0.9)
    axR.scatter(np.degrees(om[m]), y[m], s=15, c=ACC, alpha=0.40, lw=0, zorder=2)
    b = slope(om[m], y[m])
    gx = np.array([-W, W])
    if np.isfinite(b):
        axR.plot(gx, b * np.radians(gx), color=TURN, lw=2.6, zorder=3)
    axR.plot(gx, px_f * np.radians(gx), color="#0f766e", lw=1.6, ls=(0, (6, 4)), zorder=4)
    axR.axvspan(-5.0, 5.0, color="#f1f5f9", zorder=0)
    axR.text(0.42, 0.045, r"turn gate: $|\omega|\geq 5$ deg/s excluded", transform=axR.transAxes, ha="center", va="bottom", fontsize=9.5, color="#64748b", zorder=1)
    axR.set_xlim(-W, W); axR.set_ylim(-H, H)
    axR.set_xlabel(r"sensor yaw rate  $\omega$  [deg/s]", fontsize=11)
    axR.set_ylabel(r"slip-corrected lateral rate  [m/s]", fontsize=11)
    axR.set_title(r"slope of this cloud $=\ p_x$   (single sensor, no association)",
                  fontsize=13, color=FG, pad=10)
    axR.grid(alpha=0.25, lw=0.6)
    axR.legend(handles=[Line2D([], [], color=TURN, lw=2.6, label="running robust fit"),
                        Line2D([], [], color="#0f766e", lw=1.6, ls=(0, (6, 4)), label="converged fit")],
               loc="lower right", fontsize=10, framealpha=0.95)
    bs = f"{b:6.3f}" if np.isfinite(b) else "  --  "
    axR.text(0.02, 0.98,
             f"px  {bs} m   GT {gt['px']:.3f}\n"
             f"psi {psi_f:6.3f} deg  GT {gt['psi_deg']:.3f}\n"
             f"samples {int(m.sum()):4d} / {len(t)}",
             transform=axR.transAxes, va="top", ha="left", fontsize=11.5, color=FG,
             family="DejaVu Sans Mono",
             bbox=dict(fc="white", ec="#cbd5e1", boxstyle="round,pad=0.45"))

    fig.suptitle("A2D2 FRONT_CENTER  ·  Stage 1 (px, psi) from one sensor's own twist",
                 fontsize=14.5, color=FG, y=0.975)
    fig.text(0.5, 0.012, "absolute px carries the slip-coefficient bias; the reported metric is reference-relative "
         "(4 targets, fixed-dt: X 8.8 mm, Y 3.2 mm, yaw 0.03 deg)", ha="center", fontsize=10, color="#64748b")
    fig.tight_layout(rect=(0, 0.035, 1, 0.945))
    fig.savefig(OUT / f"{k:04d}.png", facecolor="white")
    plt.close(fig)

final = slope(om, y)
summary = {"dt_mode": "fixed", "channel": CH, "n_frames": NFRAMES, "fps": FPS,
           "px_running_final_m": final, "px_core_m": px_f, "px_gt_m": gt["px"],
           "px_err_mm": (px_f - gt["px"]) * 1e3,
           "psi_core_deg": psi_f, "psi_gt_deg": gt["psi_deg"],
           "psi_err_deg": psi_f - gt["psi_deg"],
           "n_samples": int(len(t)), "n_turn_segments": len(segs)}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
