"""A2D2 Stage-1 hero: turning the p_x and psi knobs of the M3 residual.

Physics shown (A2D2 FRONT_CENTER, fixed-dt condition, real M3 samples):

  The sensor measures its own velocity (vx~, vy~) in its own frame.  A mount
  yaw psi rotates that reading into the vehicle-aligned frame:

      v_lat(psi) = sin(psi) * vx~ + cos(psi) * vy~ .

  Under the (slip-relaxed) NHC the rear axle has no lateral speed, so a sensor
  mounted p_x ahead of it moves sideways only through the lever arm:

      v_lat(psi) + slip  =  p_x * omega .                 (M3 residual = 0)

  Left   : one real sample.  Sensor axes (red) and the candidate vehicle axes
           (black, rotated by psi_hat); the reading is split along the vehicle
           axes and its lateral part is compared with omega * p_x_hat.
           The mount angle is drawn exaggerated so it can be seen.
  Middle : every M3 sample, omega vs v_lat(psi_hat) + slip, coloured by the
           sensor forward speed.  The line is y = p_x_hat * omega.
             * turning p_x only pivots the line  (the cloud does not move);
             * turning psi only moves the cloud  (each point by ~ d_psi * vx~,
               so the fast samples leave the line first);
           only the right pair puts every sample on the line.
  Right  : the Huber cost of the residual over (psi_hat, p_x_hat).  The knob
           path is traced on it; the minimum is the core M3 solution.

Numbers are computed from the dump, never typed.  A self-check asserts that the
landscape minimum and the Gauss-Newton path end at the core solution.
"""
import json, math, os, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch

SRC = Path(os.environ.get("M3K_SRC", "/home/ailab-12/nh_calib_lidar/a2d2_s0d_dump_20260921"))
OUT = Path(os.environ.get("M3K_OUT", "/tmp/m3k_frames"))
GTP = os.environ.get("M3K_GT", "")
CH = "FRONT_CENTER"
FPS = 30
FG, MUT, ACC, RED = "#10151d", "#475569", "#2563eb", "#dc2626"
EXAG = 8.0                       # drawing exaggeration of the mount angle (left panel only)

d = np.load(SRC / f"s0d_{CH.lower()}_m3.npz")
meta = json.loads((SRC / f"s0d_{CH.lower()}_meta.json").read_text())
assert meta["dt_mode"] == "fixed", meta["dt_mode"]
vx, vy, om, vc = d["vx"], d["vy"], d["om"], d["vc"]
c = float(meta["c"])
PSI0, PX0 = math.radians(float(meta["psi_deg"])), float(meta["px_m"])
slip = vc * np.tan(np.clip(c * vc * om, -1.4, 1.4))
gt = json.load(open(GTP))[CH] if GTP and Path(GTP).exists() else None


def resid(p, q):
    return np.sin(p) * vx + np.cos(p) * vy - om * q + slip


r0 = resid(PSI0, PX0)
SIG = 1.4826 * np.median(np.abs(r0))
DEL = 1.345 * SIG


def huber_cost(p, q):
    r = np.abs(resid(p, q))
    return float(np.mean(np.where(r <= DEL, 0.5 * r * r, DEL * (r - 0.5 * DEL))))


def gn_path(p, q, n=12):
    """Huber IRLS Gauss-Newton on (psi, px), c held -- same residual/loss family
    as nh_planar_core.fit_m3.  Returns every iterate."""
    path = [(p, q)]
    for _ in range(n):
        r = resid(p, q)
        w = np.minimum(1.0, DEL / np.maximum(np.abs(r), 1e-12))
        J = np.stack([np.cos(p) * vx - np.sin(p) * vy, -om], 1)
        A = J.T @ (w[:, None] * J)
        g = J.T @ (w * r)
        dp, dq = np.linalg.solve(A, -g)
        p, q = p + dp, q + dq
        path.append((p, q))
    return path


# ---------------------------------------------------------------- landscape
PSI_G = np.radians(np.linspace(-4.0, 6.0, 161))
PX_G = np.linspace(0.3, 3.0, 136)
Jg = np.array([[huber_cost(p, q) for p in PSI_G] for q in PX_G])
iq, ip = np.unravel_index(np.argmin(Jg), Jg.shape)
assert abs(math.degrees(PSI_G[ip] - PSI0)) < 0.1 and abs(PX_G[iq] - PX0) < 0.03, \
    (math.degrees(PSI_G[ip]), PX_G[iq])

START = (math.radians(-3.0), 0.70)
GN = gn_path(*START)
assert abs(math.degrees(GN[-1][0] - PSI0)) < 0.02 and abs(GN[-1][1] - PX0) < 0.005, GN[-1]

# ---------------------------------------------------------------- timeline
def ease(u):
    u = min(max(u, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * u)


PX_LO, PX_HI = 0.6, 2.8
PS_LO, PS_HI = math.radians(-3.5), math.radians(5.5)
PHASES = [  # (name, seconds)
    ("pxknob", 4.5), ("hold1", 0.6), ("psiknob", 4.5), ("hold2", 0.6), ("both", 4.0), ("hold3", 1.4)]
T_END = sum(s for _, s in PHASES)
NFRAMES = int(round(T_END * FPS))


def knob(t):
    """(psi_hat, px_hat, phase, trail_key) at time t [s]."""
    t0 = 0.0
    for name, dur in PHASES:
        if t < t0 + dur or name == PHASES[-1][0]:
            u = (t - t0) / dur
            break
        t0 += dur
    if name == "pxknob":           # psi at optimum, px: optimum -> low -> high -> optimum
        if u < 0.25:
            q = PX0 + (PX_LO - PX0) * ease(u / 0.25)
        elif u < 0.75:
            q = PX_LO + (PX_HI - PX_LO) * ease((u - 0.25) / 0.5)
        else:
            q = PX_HI + (PX0 - PX_HI) * ease((u - 0.75) / 0.25)
        return PSI0, q, name, u
    if name == "hold1":
        return PSI0, PX0, name, u
    if name == "psiknob":
        if u < 0.25:
            p = PSI0 + (PS_LO - PSI0) * ease(u / 0.25)
        elif u < 0.75:
            p = PS_LO + (PS_HI - PS_LO) * ease((u - 0.25) / 0.5)
        else:
            p = PS_HI + (PSI0 - PS_HI) * ease((u - 0.75) / 0.25)
        return p, PX0, name, u
    if name == "hold2":
        return START[0] + (0) * u, START[1], name, u   # jump to the both-wrong start
    if name == "both":
        k = u * (len(GN) - 1) * 0.999
        # spend real time on the first iterates (they carry the motion)
        k = (len(GN) - 1) * (1 - (1 - u) ** 3)
        i = min(int(k), len(GN) - 2)
        f = ease(k - i)
        p = GN[i][0] + (GN[i + 1][0] - GN[i][0]) * f
        q = GN[i][1] + (GN[i + 1][1] - GN[i][1]) * f
        return p, q, name, u
    return GN[-1][0], GN[-1][1], name, u


TITLES = {
    "pxknob": ("1  Turn the  $p_x$  knob only", "the line pivots; the cloud does not move"),
    "hold1": ("1  Turn the  $p_x$  knob only", "the line pivots; the cloud does not move"),
    "psiknob": ("2  Turn the  $\\psi$  knob only", "the cloud moves, fast samples first; the line does not"),
    "hold2": ("3  Start with both wrong", "one minimum of the residual fixes both"),
    "both": ("3  Start with both wrong", "one minimum of the residual fixes both"),
    "hold3": ("3  Both at the minimum", "every turn sample lies on  $v_{lat} = p_x\\,\\omega$"),
}

# representative sample for the left panel: fast and turning hard
score = vx * np.abs(om)
KS = int(np.argmax(score))
OMR = np.degrees(om)
VMIN, VMAX = float(vx.min()), float(vx.max())
YL = 1.05 * max(np.abs(resid(PS_LO, 0) + om * 0).max(), np.abs(resid(PS_HI, 0)).max(),
                PX_HI * np.abs(om).max())


def draw(fi):
    t = fi / FPS
    p, q, ph, u = knob(t)
    fig = plt.figure(figsize=(19.2, 7.6), dpi=100)
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(1, 3, width_ratios=[0.86, 1.18, 1.0], left=0.055, right=0.975,
                          top=0.80, bottom=0.135, wspace=0.26)
    a0, a1, a2 = (fig.add_subplot(gs[0, i]) for i in range(3))
    h1, h2 = TITLES[ph]
    fig.text(0.035, 0.935, h1, fontsize=22, fontweight="bold", color=FG, ha="left", va="center")
    fig.text(0.035, 0.885, h2, fontsize=16, color=MUT, ha="left", va="center")
    rr = resid(p, q)
    rms = float(np.sqrt(np.mean(rr ** 2)))
    fig.text(0.975, 0.935, f"$\\hat\\psi$ = {math.degrees(p):+.2f}°     $\\hat p_x$ = {q:.3f} m",
             fontsize=18, color=FG, ha="right", va="center")
    fig.text(0.975, 0.885, f"residual RMS {rms:.3f} m/s   (at the minimum {np.sqrt(np.mean(r0**2)):.3f})",
             fontsize=14, color=MUT, ha="right", va="center")

    # ------------------------------------------------ left: one reading, as bars
    ax = a0
    sx, sy, so, ss = float(vx[KS]), float(vy[KS]), float(om[KS]), float(slip[KS])
    A = math.cos(p) * sy                       # rotated lateral reading
    B = math.sin(p) * sx                       # forward reading leaking in: psi knob
    lhs = A + B + ss
    rhs = q * so                               # lever arm: p_x knob
    act_psi = ph in ("psiknob", "both")
    act_px = ph in ("pxknob", "both")

    def seg(x, y0, h, col, alpha=1.0, hatch=None):
        ax.bar(x, h, bottom=y0, width=0.52, color=col, alpha=alpha, edgecolor="white", lw=1.2, hatch=hatch)

    y0 = 0.0
    seg(0, y0, A, "#94a3b8"); y0 += A
    seg(0, y0, B, ACC, 1.0 if act_psi else 0.55); y0 += B
    seg(0, y0, ss, "#cbd5e1"); y0 += ss
    seg(1, 0.0, rhs, "#16a34a", 1.0 if act_px else 0.55)
    ax.plot([-0.33, 0.33], [lhs, lhs], color=FG, lw=2.0)
    ax.plot([0.67, 1.33], [rhs, rhs], color=FG, lw=2.0)
    GX = 1.58
    ax.annotate("", xy=(GX, rhs), xytext=(GX, lhs),
                arrowprops=dict(arrowstyle="<->", color=RED, lw=2.0, shrinkA=0, shrinkB=0))
    ax.plot([0.33, GX], [lhs, lhs], color=FG, lw=0.7, ls=":")
    ax.plot([1.33, GX], [rhs, rhs], color=FG, lw=0.7, ls=":")
    ax.text(GX + 0.05, 0.5 * (lhs + rhs), "gap\n%+.3f" % (lhs - rhs), color=RED, fontsize=13,
            ha="left", va="center", fontweight="bold")
    ax.axhline(0, color=FG, lw=0.8)
    ax.set_xlim(-0.45, 2.05); ax.set_ylim(-0.45, 1.95)
    ax.set_yticks(np.arange(-0.4, 1.25, 0.2))
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["sensor reading\nin vehicle axes", "lever arm\n" + r"$\hat p_x\,\omega$"], fontsize=13)
    ax.set_ylabel("lateral speed  [m/s]", fontsize=13)
    ax.yaxis.set_label_coords(-0.09, 0.35)
    ax.tick_params(axis="y", labelsize=12)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_title(r"One reading: both sides of  $v_{lat} = p_x\,\omega$", fontsize=14, color=FG, loc="left")
    rows = [(r"$\cos\hat\psi\,\tilde v_y$  = %+.3f" % A, "#64748b", False),
            (r"$\sin\hat\psi\,\tilde v_x$  = %+.3f" % B + (r"     $\leftarrow$ $\psi$ knob" if act_psi else ""), ACC, act_psi),
            (r"slip term  = %+.3f" % ss, "#94a3b8", False),
            (r"$\hat p_x\,\omega$  = %+.3f" % rhs + (r"     $\leftarrow$ $p_x$ knob" if act_px else ""), "#16a34a", act_px)]
    for k, (tx, col, bold) in enumerate(rows):
        ax.text(-0.40, 1.86 - 0.115 * k, tx, color=col, fontsize=13, ha="left", va="top",
                fontweight="bold" if bold else "normal")
    ax.text(-0.40, 1.34, r"reading: $\tilde v_x$ %.2f m/s, $\tilde v_y$ %+.2f m/s, $\omega$ %+.1f deg/s"
            % (sx, sy, math.degrees(so)), fontsize=11, color=MUT, va="top")

    # ------------------------------------------------ middle: omega vs vehicle lateral speed
    ax = a1
    y = np.sin(p) * vx + np.cos(p) * vy + slip
    sc = ax.scatter(OMR, y, c=vx, cmap="viridis", vmin=VMIN, vmax=VMAX, s=14, lw=0, alpha=0.85, zorder=3)
    xx = np.array([-17, 17])
    ax.plot(xx, q * np.radians(xx), color=RED, lw=2.4, zorder=4, label=r"$p_x\,\hat{}\,\omega$")
    ax.plot(xx, PX0 * np.radians(xx), color=MUT, lw=1.0, ls=(0, (4, 3)), zorder=2)
    ax.axhline(0, color="#cbd5e1", lw=0.8, zorder=1); ax.axvline(0, color="#cbd5e1", lw=0.8, zorder=1)
    ax.set_xlim(-17, 17); ax.set_ylim(-YL, YL)
    ax.set_xlabel(r"yaw rate $\omega$  [deg/s]", fontsize=14)
    ax.set_ylabel(r"vehicle-frame lateral speed  $v_{lat}(\hat\psi)$ + slip  [m/s]", fontsize=13)
    ax.set_title(r"All turn samples:  lateral speed must equal  $p_x\,\omega$", fontsize=14,
                 color=FG, loc="left")
    ax.plot(OMR[KS], y[KS], "o", ms=13, mfc="none", mec=FG, mew=2, zorder=5)
    ax.legend(handles=[Line2D([], [], color=RED, lw=2.4, label=r"line  $\hat p_x\,\omega$"),
                       Line2D([], [], color=MUT, lw=1.0, ls=(0, (4, 3)), label="line at the minimum"),
                       Line2D([], [], marker="o", ls="", mfc="none", mec=FG, mew=2, ms=10,
                              label="the reading on the left")],
              loc="upper left", fontsize=12, frameon=False)
    cb = fig.colorbar(sc, ax=ax, fraction=0.04, pad=0.015)
    cb.set_label(r"sensor forward speed $\tilde v_x$  [m/s]", fontsize=12)
    ax.tick_params(labelsize=12)

    # ------------------------------------------------ right: cost landscape
    ax = a2
    ax.contourf(np.degrees(PSI_G), PX_G, np.log10(Jg), levels=22, cmap="Greys_r", alpha=0.55)
    ax.contour(np.degrees(PSI_G), PX_G, np.log10(Jg), levels=14, colors="#64748b", linewidths=0.6)
    ax.plot(math.degrees(PSI0), PX0, marker="*", ms=20, color="#f59e0b", mec=FG, mew=1.0, zorder=6)
    if gt is not None:
        ax.plot(float(gt["yaw_deg"]) if "yaw_deg" in gt else np.nan, float(gt.get("px", np.nan)),
                "+", ms=14, mew=2.2, color=ACC, zorder=6)
    # trail of the knob path so far
    ts = np.arange(0, fi + 1) / FPS
    tr = np.array([knob(s)[:2] for s in ts])
    ax.plot(np.degrees(tr[:, 0]), tr[:, 1], color=RED, lw=1.6, alpha=0.6, zorder=5)
    ax.plot(math.degrees(p), q, "o", ms=13, color=RED, mec="white", mew=1.6, zorder=7)
    ax.set_xlabel(r"mount yaw  $\hat\psi$  [deg]", fontsize=14)
    ax.set_ylabel(r"lever arm  $\hat p_x$  [m]", fontsize=14)
    ax.set_title("Huber cost of the residual over both knobs", fontsize=14, color=FG, loc="left")
    ax.tick_params(labelsize=12)
    hl = [Line2D([], [], marker="*", ls="", ms=16, color="#f59e0b", mec=FG, label="minimum = M3 solution"),
          Line2D([], [], marker="o", ls="", ms=11, color=RED, mec="white", label="current knobs")]
    ax.legend(handles=hl, loc="upper right", fontsize=12, framealpha=0.9)
    fig.text(0.5, 0.025, r"A2D2 FRONT_CENTER · real M3 turn samples (n = %d, fixed-dt) · "
             r"residual  $r = \sin\hat\psi\,\tilde v_x + \cos\hat\psi\,\tilde v_y - \hat p_x\,\omega$ + slip"
             % len(vx), fontsize=13, color=MUT, ha="center")
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{fi:04d}.png", dpi=100, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    only = [int(k) for k in sys.argv[1:]]
    frames = only or list(range(NFRAMES))
    if len(frames) > 8:
        from multiprocessing import Pool
        with Pool(int(os.environ.get("M3K_PROC", "8"))) as pl:
            pl.map(draw, frames)
    else:
        for f in frames:
            draw(f)
    json.dump({"channel": CH, "dt_mode": "fixed", "n_samples": int(len(vx)), "fps": FPS,
               "n_frames": NFRAMES, "psi_core_deg": math.degrees(PSI0), "px_core_m": PX0,
               "landscape_min_psi_deg": math.degrees(PSI_G[ip]), "landscape_min_px_m": float(PX_G[iq]),
               "gn_start": [math.degrees(START[0]), START[1]],
               "gn_end": [math.degrees(GN[-1][0]), GN[-1][1]], "gn_iters": len(GN) - 1,
               "residual_rms_at_min_mps": float(np.sqrt(np.mean(r0 ** 2))),
               "rep_sample_index": KS, "rep_vx_mps": float(vx[KS]), "rep_om_degps": float(OMR[KS]),
               "px_knob_range_m": [PX_LO, PX_HI],
               "psi_knob_range_deg": [math.degrees(PS_LO), math.degrees(PS_HI)]},
              open(OUT / "meta.json", "w"), indent=1)
    print("M3K_DONE", len(frames))
