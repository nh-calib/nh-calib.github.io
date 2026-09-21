"""A2D2 p_x / psi hero, fixed-dt condition.  Three panels.

Left   : CAN-integrated ego path, turn segments highlighted, cursor.
Middle : omega vs slip-corrected lateral rate.  The M3 residual
             r = sin(psi)vx + cos(psi)vy - omega*px + vc*tan(c*vc*omega)
         rearranges to  y := lateral + slip = px*omega + r, so the
         through-origin slope of the accumulating cloud IS p_x.
Right  : the (psi, p_x) constraint space.  Perturbing the truth by
         (dpsi, dpx) expands the residual to
             r  ~=  omega*dpx  +  dpsi*v_jx ,   v_jx = v_cx - omega*p_y
         so ONE curvature projects to ONE straight line of slope
         dpx/dpsi = <omega*v_jx>/<omega^2> = 1/kappa.  The yaw lever is the
         sensor's own longitudinal speed v_jx, not straight driving; turns of
         different curvature -- especially of opposite sign -- make the lines
         cross, and the crossing is what fixes (psi, px).
Readout: running (psi, px) solved on the samples seen so far, vs A2D2 GT.
"""
import json, itertools, math
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

for k in range(NFRAMES):
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

    # ---- right: the (psi, px) constraint space --------------------------
    shown = [i for i, lm in enumerate(lmeta) if lm is not None and lm["end"] <= tc + 1e-6]
    newest = shown[-1] if shown else None
    for i in shown:
        col = CCW if lmeta[i]["sign"] > 0 else CW
        fresh = (i == newest) and (tc - lmeta[i]["end"] < 6.0)
        axR.plot(grid_deg, lines[i], color=col, lw=2.6 if fresh else 1.5,
                 alpha=0.95 if fresh else 0.55, zorder=4 if fresh else 3)
    axR.plot([gt["psi_deg"]], [gt["px"]], marker="+", ms=17, mew=2.2,
             color="#0f766e", zorder=6)
    p_run, q_run = solve2(m)
    if np.isfinite(p_run):
        axR.plot([math.degrees(p_run)], [q_run], "o", ms=11, mfc="none",
                 mec=FG, mew=2.2, zorder=7)
    axR.set_xlim(psi_f - PS_HALF, psi_f + PS_HALF)
    axR.set_ylim(px_f - PX_HALF, px_f + PX_HALF)
    axR.set_xlabel("sensor yaw  $\\psi$  [deg]", fontsize=10.5)
    axR.set_ylabel("longitudinal offset  $p_x$  [m]", fontsize=10.5)
    axR.tick_params(labelsize=9.5)
    axR.set_title("one curvature = one line, not a point\n"
                  "slope $=\\ v_{jx}/\\omega$ ;  curvatures must differ",
                  fontsize=12.5, color=FG, pad=8)
    axR.grid(alpha=0.25, lw=0.6)
    if newest is not None and (tc - lmeta[newest]["end"] < 6.0):
        lm = lmeta[newest]
        axR.text(0.5, 0.955,
                 "turn %d:  $|\\omega|$ %.1f deg/s,  $v_{jx}$ %.1f m/s,  slope %+.0f m/rad"
                 % (shown.index(newest) + 1, lm["om"], lm["vjx"], lm["slope"]),
                 transform=axR.transAxes, ha="center", va="top", fontsize=9.5,
                 color=CCW if lm["sign"] > 0 else CW, zorder=8,
                 bbox=dict(fc="white", ec="none", alpha=0.88, boxstyle="round,pad=0.25"))
    axR.legend(handles=[Line2D([], [], color=CCW, lw=2.0, label="left turn  ($\\omega>0$)"),
                        Line2D([], [], color=CW, lw=2.0, label="right turn  ($\\omega<0$)"),
                        Line2D([], [], color=FG, marker="o", mfc="none", mew=2.0, ls="none",
                               label="running solve"),
                        Line2D([], [], color="#0f766e", marker="+", mew=2.0, ls="none",
                               label="A2D2 GT")],
               loc="lower right", fontsize=9, framealpha=0.95)

    # ---- readout --------------------------------------------------------
    bs = f"{b_run:6.3f}" if np.isfinite(b_run) else "  --  "
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
