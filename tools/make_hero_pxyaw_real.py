"""A2D2 p_x / psi hero, fixed-dt condition.  Three panels.

Left   : CAN-integrated ego path, turn segments highlighted, cursor.
Middle : omega vs slip-corrected lateral rate.  The M3 residual
             r = sin(psi)vx + cos(psi)vy - omega*px + vc*tan(c*vc*omega)
         rearranges to  y := lateral + slip = px*omega + r, so the
         through-origin slope of the accumulating cloud IS p_x.
Right  : sensor longitudinal speed vs lever-removed lateral speed.  The
         same residual, solved for the sensor-frame lateral reading, is
             vy - (omega*px - slip)/cos(psi)  =  -tan(psi) * vx ,
         so once the omega*p_x lever-arm part is taken out, every sample of
         every turn -- left or right -- falls on one through-origin line
         whose slope is -tan(psi): the forward motion of the body, seen
         through a mount rotated by psi.  The yaw lever is the longitudinal
         speed v_x, not straight driving.  Raw lateral readings are drawn
         faintly to show how much of them is the lever arm.
Readout: running (psi, px) solved on the samples seen so far, vs A2D2 GT.
"""
import json, itertools, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

import os
SRC = Path(os.environ.get("S0D_SRC", "/home/ailab-12/nh_calib_lidar/a2d2_s0d_dump_20260921"))
OUT = Path(os.environ.get("S0D_OUT", "/home/ailab-12/nh_calib_lidar/a2d2_s0d_frames_20260921"))
GTP = os.environ.get("S0D_GT", "/home/ailab-12/nh_calib_lidar/a2d2_gt.json")
ONLY = [int(k) for k in os.environ.get("S0D_ONLY", "").split(",") if k]
CH = "FRONT_CENTER"
NFRAMES, FPS = 240, 30
FG, MUT, ACC, TURN = "#10151d", "#475569", "#2563eb", "#dc2626"
CCW, CW = "#1d4ed8", "#b91c1c"          # left-turn / right-turn constraint lines

d = np.load(SRC / f"s0d_{CH.lower()}_m3.npz")
meta = json.loads((SRC / f"s0d_{CH.lower()}_meta.json").read_text())
gt = json.load(open(GTP))[CH]
assert meta["dt_mode"] == "fixed", meta["dt_mode"]

t, om, vc = d["t"], d["om"], d["vc"]
vx, vy = d["vx"], d["vy"]
c, px_f, psi_f = float(meta["c"]), float(meta["px_m"]), float(meta["psi_deg"])
psi_r = math.radians(psi_f)
slip = vc * np.tan(np.clip(c * vc * om, -1.4, 1.4))
y = d["lateral"] + slip                                   # = px*omega + r
ct, cx, cy = d["ch_t"], d["ch_x"], d["ch_y"]
_w = (ct >= float(t[0])) & (ct <= float(t[-1]))
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


def solve2(m, psi0=0.0, px0=1.0):
    """Huber IRLS Gauss-Newton for (psi, px) on the M3 residual, c held at the
    core value.  Same residual and loss family as nh_planar_core.fit_m3."""
    if int(m.sum()) < 12:
        return float("nan"), float("nan")
    a, b, o, s = vx[m], vy[m], om[m], slip[m]
    p, q = psi0, px0
    for _ in range(40):
        r = math.sin(p) * a + math.cos(p) * b - o * q + s
        sc = 1.4826 * np.median(np.abs(r)) + 1e-12
        w = np.minimum(1.0, 1.345 * sc / np.maximum(np.abs(r), 1e-12))
        j0 = math.cos(p) * a - math.sin(p) * b          # dr/dpsi  (= v_jx)
        j1 = -o                                          # dr/dpx
        h00 = float(w @ (j0 * j0)); h01 = float(w @ (j0 * j1)); h11 = float(w @ (j1 * j1))
        g0 = float(w @ (j0 * r));   g1 = float(w @ (j1 * r))
        det = h00 * h11 - h01 * h01
        if abs(det) < 1e-14:
            break
        dp = -(h11 * g0 - h01 * g1) / det
        dq = -(h00 * g1 - h01 * g0) / det
        p += dp; q += dq
        if abs(dp) < 1e-12 and abs(dq) < 1e-12:
            break
    return p, q


# --- self-check: the full-sample solve must reproduce the core solution -----
_p, _q = solve2(np.ones(len(t), bool))
assert abs(math.degrees(_p) - psi_f) < 0.02, (math.degrees(_p), psi_f)
assert abs(_q - px_f) < 0.02, (_q, px_f)
print(f"self-check  psi {math.degrees(_p):.4f} vs core {psi_f:.4f} deg   "
      f"px {_q:.4f} vs core {px_f:.4f} m")

# --- lever-removed lateral: vy - (omega*px - slip)/cos(psi) = -tan(psi)*vx --
z = vy - (om * px_f - slip) / math.cos(psi_r)
_bz = slope(vx, z)
assert abs(-math.degrees(math.atan(_bz)) - psi_f) < 0.01, (_bz, psi_f)
print(f"self-check  yaw slope {_bz:.5f}  ->  psi {-math.degrees(math.atan(_bz)):.4f} deg")

# --- per-segment constraint lines in (psi, px) ------------------------------
PS_HALF, PX_HALF = 1.25, 0.72                             # deg / m half-windows
grid = np.radians(np.linspace(psi_f - PS_HALF, psi_f + PS_HALF, 41))
grid_deg = np.degrees(grid)
lines, lmeta = [], []
for i, s in enumerate(segs):
    m = (t >= s["start_s"]) & (t <= s["end_s"])
    if int(m.sum()) < 12:
        lines.append(None); lmeta.append(None); continue
    o, a, b, sl = om[m], vx[m], vy[m], slip[m]
    cur = np.array([slope(o, np.sin(p) * a + np.cos(p) * b + sl) for p in grid])
    vjx_s = math.cos(psi_r) * a - math.sin(psi_r) * b
    lines.append(cur)
    # drop the line when the segment's LAST SAMPLE is reached: a segment can
    # end after the last M3 sample, which would hide it for the whole clip.
    lmeta.append(dict(sign=int(np.sign(np.median(o))),
                      end=float(t[m][-1]),
                      slope=float((o * vjx_s).sum() / (o * o).sum()),
                      om=float(np.degrees(np.median(np.abs(o)))),
                      vjx=float(np.median(vjx_s))))

seg_mask = np.zeros(len(ct), bool)
for s in segs:
    seg_mask |= (ct >= s["start_s"]) & (ct <= s["end_s"])
OUT.mkdir(parents=True, exist_ok=True)
W = max(abs(np.degrees(om)).max(), 1.0) * 1.12
H = max(abs(y).max(), 0.1) * 1.15

VXM = float(vx.max()) * 1.08
ZLO = float(min(np.percentile(vy, 0.5), z.min())) - 0.05
ZHI = float(max(np.percentile(vy, 99.5), z.max())) + 0.05
frames = ONLY if ONLY else range(NFRAMES)
for k in frames:
    tc = t0 + (t1 - t0) * (k + 1) / NFRAMES
    fig, (axL, axM, axR) = plt.subplots(
        1, 3, figsize=(16.0, 7.2), dpi=120,
        gridspec_kw={"width_ratios": [0.80, 1.0, 1.06]})
    fig.patch.set_facecolor("white")

    # ---- left: ego path -------------------------------------------------
    mp = ct <= tc
    axL.plot(cx, cy, color="#e8edf3", lw=1.4, zorder=1)
    axL.plot(cx[mp], cy[mp], color=MUT, lw=1.6, zorder=2)
    seg_done = seg_mask & mp
    axL.plot(np.where(seg_done, cx, np.nan), np.where(seg_done, cy, np.nan),
             color=TURN, lw=3.0, zorder=3, solid_capstyle="round")
    if mp.any():
        axL.plot(cx[mp][-1], cy[mp][-1], "o", ms=9, mfc=ACC, mec="white", mew=1.8, zorder=4)
    axL.set_aspect("equal")
    axL.set_anchor("N")          # equal-aspect shrinks the box; keep titles aligned
    axL.set_title("CAN-integrated ego path\nturn segments in red",
                  fontsize=12.5, color=FG, pad=8)
    axL.set_xlabel("east [m]", fontsize=10.5); axL.set_ylabel("north [m]", fontsize=10.5)
    axL.tick_params(labelsize=9.5)
    axL.grid(alpha=0.25, lw=0.6)
    # count with the same rule the right panel drops lines by (last sample)
    n_done = sum(1 for lm in lmeta if lm is not None and lm["end"] <= tc + 1e-6)
    axL.text(0.97, 0.98, f"t = {tc - t0:5.1f} s\nturns: {n_done} / {len(segs)}",
             transform=axL.transAxes, va="top", ha="right", fontsize=10.5, color=FG, zorder=6,
             family="DejaVu Sans Mono",
             bbox=dict(fc="white", ec="#cbd5e1", boxstyle="round,pad=0.4"))

    # ---- middle: omega vs slip-corrected lateral rate -------------------
    m = t <= tc
    axM.axhline(0, color="#cbd5e1", lw=0.9); axM.axvline(0, color="#cbd5e1", lw=0.9)
    axM.scatter(np.degrees(om[m]), y[m], s=13, c=ACC, alpha=0.38, lw=0, zorder=2)
    b_run = slope(om[m], y[m])
    gx = np.array([-W, W])
    if np.isfinite(b_run):
        axM.plot(gx, b_run * np.radians(gx), color=TURN, lw=2.5, zorder=3)
    axM.plot(gx, px_f * np.radians(gx), color="#0f766e", lw=1.5, ls=(0, (6, 4)), zorder=4)
    axM.axvspan(-5.0, 5.0, color="#f1f5f9", zorder=0)
    axM.text(0.03, 0.965, r"turn gate: $|\omega| < 5$ deg/s excluded",
             transform=axM.transAxes, ha="left", va="top",
             fontsize=9, color="#64748b", zorder=1)
    axM.set_xlim(-W, W); axM.set_ylim(-H, H)
    axM.set_xlabel(r"sensor yaw rate  $\omega$  [deg/s]", fontsize=10.5)
    axM.set_ylabel(r"slip-corrected lateral rate  [m/s]", fontsize=10.5)
    axM.tick_params(labelsize=9.5)
    axM.set_title("at the solved $\\psi$:  slope $=\\ p_x$\nsingle sensor, no association",
                  fontsize=12.5, color=FG, pad=8)
    axM.grid(alpha=0.25, lw=0.6)
    axM.legend(handles=[Line2D([], [], color=TURN, lw=2.5, label="running robust fit"),
                        Line2D([], [], color="#0f766e", lw=1.5, ls=(0, (6, 4)),
                               label="converged fit")],
               loc="lower right", fontsize=9.5, framealpha=0.95)

    # ---- right: longitudinal speed vs lever-removed lateral speed -------
    axR.axhline(0, color="#cbd5e1", lw=0.9)
    axR.scatter(vx[m], vy[m], s=9, c="#94a3b8", alpha=0.18, lw=0, zorder=1)
    col = np.where(om[m] > 0, CCW, CW)
    axR.scatter(vx[m], z[m], s=13, c=col, alpha=0.45, lw=0, zorder=2)
    bz_run = slope(vx[m], z[m])
    gv = np.array([0.0, VXM])
    if np.isfinite(bz_run):
        axR.plot(gv, bz_run * gv, color=TURN, lw=2.5, zorder=3)
    axR.plot(gv, -math.tan(psi_r) * gv, color="#0f766e", lw=1.5, ls=(0, (6, 4)), zorder=4)
    axR.plot(gv, -math.tan(math.radians(gt["psi_deg"])) * gv, color=FG, lw=0.9,
             ls=(0, (1.5, 2.5)), zorder=4)
    axR.set_xlim(0, VXM); axR.set_ylim(ZLO, ZHI)
    axR.set_xlabel(r"sensor longitudinal speed  $\tilde v_x$  [m/s]", fontsize=10.5)
    axR.set_ylabel(r"lever-removed lateral speed  [m/s]", fontsize=10.5)
    axR.tick_params(labelsize=9.5)
    axR.set_title(r"at the solved $p_x$:  slope $= -\tan\psi$" "\n"
                  r"remove $\omega p_x$: every turn falls on one line",
                  fontsize=12.5, color=FG, pad=8)
    axR.grid(alpha=0.25, lw=0.6)
    if np.isfinite(bz_run):
        axR.text(0.03, 0.965,
                 "slope %+.4f  ->  psi = %.3f deg" % (bz_run, -math.degrees(math.atan(bz_run))),
                 transform=axR.transAxes, ha="left", va="top", fontsize=9.5, color=TURN,
                 family="DejaVu Sans Mono", zorder=8,
                 bbox=dict(fc="white", ec="none", alpha=0.88, boxstyle="round,pad=0.25"))
    axR.legend(handles=[Line2D([], [], color="#94a3b8", marker="o", ls="none", ms=5, alpha=0.6,
                               label=r"raw lateral  $\tilde v_y$"),
                        Line2D([], [], color=CCW, marker="o", ls="none", ms=5,
                               label="lever removed, left turn"),
                        Line2D([], [], color=CW, marker="o", ls="none", ms=5,
                               label="lever removed, right turn"),
                        Line2D([], [], color=TURN, lw=2.5, label="running robust fit"),
                        Line2D([], [], color=FG, lw=0.9, ls=(0, (1.5, 2.5)),
                               label="A2D2 GT yaw")],
               loc="lower left", fontsize=8.8, framealpha=0.95)

    # ---- readout --------------------------------------------------------
    p_run, q_run = solve2(m)                     # joint (psi, px) on samples so far
    bs = f"{q_run:6.3f}" if np.isfinite(q_run) else "  --  "
    ps = f"{math.degrees(p_run):6.3f}" if np.isfinite(p_run) else "  --  "
    fig.text(0.335, 0.912,
             f"running solve   psi {ps} deg  (GT {gt['psi_deg']:.3f})\n"
             f"                px  {bs} m    (GT {gt['px']:.3f})\n"
             f"                samples {int(m.sum()):4d} / {len(t)}",
             va="top", ha="left", fontsize=10.5, color=FG, family="DejaVu Sans Mono",
             bbox=dict(fc="white", ec="#cbd5e1", boxstyle="round,pad=0.4"), zorder=9)
    fig.suptitle("A2D2 FRONT_CENTER  .  Stage 1 (px, psi) from one sensor's own twist",
                 fontsize=14.5, color=FG, y=0.985)
    fig.text(0.5, 0.012,
             "the yaw lever is the sensor's own longitudinal speed v_jx, not straight driving;  "
             "absolute px carries the slip-coefficient bias, the reported metric is "
             "reference-relative (4 targets, fixed-dt: X 8.8 mm, Y 3.2 mm, yaw 0.03 deg)",
             ha="center", fontsize=9.5, color="#64748b")
    fig.tight_layout(rect=(0, 0.032, 1, 0.892))
    fig.savefig(OUT / f"{k:04d}.png", facecolor="white")
    plt.close(fig)

final_px = slope(om, y)
pF, qF = solve2(np.ones(len(t), bool))
ints = []
for i, j in itertools.combinations([i for i, l in enumerate(lines) if l is not None], 2):
    diff = lines[i] - lines[j]
    idx = np.where(np.diff(np.sign(diff)) != 0)[0]
    if len(idx):
        q = idx[0]; f = diff[q] / (diff[q] - diff[q + 1])
        ints.append((grid_deg[q] + f * (grid_deg[q + 1] - grid_deg[q]),
                     lines[i][q] + f * (lines[i][q + 1] - lines[i][q])))
A = np.array(ints) if ints else np.zeros((0, 2))
summary = {
    "dt_mode": "fixed", "channel": CH, "n_frames": NFRAMES, "fps": FPS,
    "px_running_final_m": final_px, "px_core_m": px_f, "px_gt_m": gt["px"],
    "px_err_mm": (px_f - gt["px"]) * 1e3,
    "psi_core_deg": psi_f, "psi_gt_deg": gt["psi_deg"],
    "psi_err_deg": psi_f - gt["psi_deg"],
    "selfcheck_solve2_psi_deg": math.degrees(pF), "selfcheck_solve2_px_m": qF,
    "n_samples": int(len(t)), "n_turn_segments": len(segs),
    "n_constraint_lines": int(sum(l is not None for l in lines)),
    "n_line_intersections": int(len(A)),
    "intersection_median_psi_deg": float(np.median(A[:, 0])) if len(A) else None,
    "intersection_median_px_m": float(np.median(A[:, 1])) if len(A) else None,
    "line_slopes_m_per_rad": [round(lm["slope"], 2) for lm in lmeta if lm],
    "n_left_turns": int(sum(1 for lm in lmeta if lm and lm["sign"] > 0)),
    "n_right_turns": int(sum(1 for lm in lmeta if lm and lm["sign"] < 0)),
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
