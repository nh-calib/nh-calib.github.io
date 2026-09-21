#!/usr/bin/env python3
"""Turn-segment extraction on the real A2D2 drive.

Left   the whole drive's yaw rate with the accepted turn segments shaded, so
       the reader sees how little of a drive the estimator actually consumes.
Right  one segment in close-up: the rate trace against the two gate levels and
       the heading it accumulates, against the net-rotation acceptance level.

Data comes from the Stage-1 dump (chassis clock) and the Stage-2 segment dump;
nothing is re-estimated here.

Run on ailab-12:
    /home/ailab-12/miniforge3/envs/nhcalib/bin/python make_turn_gate_real.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DUMP = Path("/home/ailab-12/nh_calib_lidar/a2d2_s0d_dump_20260921/s0d_front_center_m3.npz")
SEG = Path("/home/ailab-12/hero_real_20260921/hero_segments.npz")
OUT = Path("/home/ailab-12/turn_gate_20260921/turn_gate_real.png")
META = OUT.with_suffix(".json")

TRIGGER_DPS = 15.0     # peak level that opens a segment
EDGE_DPS = 5.0         # hold level that closes it
NET_DEG = 30.0         # net rotation required to accept

INK, MUTED, RULE = "#191919", "#666666", "#d8d8d8"
ACCENT = "#a52e29"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9.5,
    "axes.edgecolor": RULE, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": "white",
})


def main():
    d = np.load(DUMP)
    s = np.load(SEG)
    t = d["ch_t"] - d["ch_t"][0]
    wz = np.degrees(d["ch_wz"])
    head = np.degrees(np.unwrap(d["ch_head"]))
    t0 = d["ch_t"][0]
    starts = s["seg_start"] - t0
    ends = s["seg_end"] - t0
    dur = ends - starts

    # close-up: the longest segment that is not the 56 s mega-window
    order = np.argsort(dur)
    pick = int(order[len(order) // 2])

    fig, (axA, axB) = plt.subplots(
        1, 2, figsize=(11.0, 3.4), gridspec_kw={"width_ratios": [1.55, 1.0], "wspace": 0.28})

    # ---- (a) whole drive ------------------------------------------------
    for a, b in zip(starts, ends):
        axA.axvspan(a, b, color=ACCENT, alpha=0.16, lw=0, zorder=1)
    axA.plot(t, wz, color=INK, lw=0.6, zorder=3)
    for lv in (TRIGGER_DPS, -TRIGGER_DPS):
        axA.axhline(lv, color=ACCENT, lw=0.9, ls="--", zorder=2)
    for lv in (EDGE_DPS, -EDGE_DPS):
        axA.axhline(lv, color=MUTED, lw=0.7, ls=":", zorder=2)
    axA.set_xlim(t[0], t[-1])
    axA.set_ylim(-32, 32)
    axA.set_xlabel("time into the drive  [s]")
    axA.set_ylabel("yaw rate  [deg/s]")
    axA.set_title(f"{len(starts)} accepted turn segments in a {t[-1]/60:.0f}-minute drive",
                  fontsize=10, loc="left", pad=20)
    axA.text(0.0, 1.03, "shaded = consumed by the estimator; everything else is discarded",
             transform=axA.transAxes, fontsize=8.5, color=MUTED, va="bottom")
    axA.annotate("trigger  15 deg/s", (t[-1] * 0.76, TRIGGER_DPS + 1.5), ha="left",
                 va="bottom", fontsize=8, color=ACCENT)
    axA.annotate("edge  5 deg/s", (t[-1] * 0.76, EDGE_DPS + 1.0), ha="left",
                 va="bottom", fontsize=8, color=MUTED)
    for side in ("top", "right"):
        axA.spines[side].set_visible(False)

    # ---- (b) one segment, close up --------------------------------------
    a, b = starts[pick], ends[pick]
    pad = 0.45 * (b - a)
    m = (t > a - pad) & (t < b + pad)
    tt = t[m] - a
    axB.axvspan(0.0, b - a, color=ACCENT, alpha=0.16, lw=0, zorder=1)
    axB.plot(tt, wz[m], color=INK, lw=1.0, zorder=3, label="yaw rate")
    axB.axhline(TRIGGER_DPS, color=ACCENT, lw=0.9, ls="--", zorder=2)
    axB.axhline(EDGE_DPS, color=MUTED, lw=0.7, ls=":", zorder=2)
    axB.axhline(-TRIGGER_DPS, color=ACCENT, lw=0.9, ls="--", zorder=2)
    axB.axhline(-EDGE_DPS, color=MUTED, lw=0.7, ls=":", zorder=2)
    axB.set_xlim(tt[0], tt[-1])
    axB.set_ylim(-32, 32)
    axB.set_xlabel("time from segment start  [s]")
    axB.set_ylabel("yaw rate  [deg/s]")

    hh = head[m] - np.interp(a, t, head)
    net = float(np.interp(b, t, head) - np.interp(a, t, head))
    ax2 = axB.twinx()
    ax2.plot(tt, hh, color=ACCENT, lw=1.2, zorder=3)
    ax2.axhline(np.sign(net) * NET_DEG, color=ACCENT, lw=0.7, ls=":", zorder=2)
    lim = max(60.0, abs(hh).max() * 1.25)
    ax2.set_ylim(-lim, lim)
    ax2.set_ylabel("heading  [deg]", color=ACCENT)
    ax2.tick_params(axis="y", colors=ACCENT)
    ax2.spines["top"].set_visible(False)
    for side in ("top",):
        axB.spines[side].set_visible(False)
    axB.set_title(f"one segment: {b-a:.1f} s, {abs(net):.0f} deg net rotation",
                  fontsize=10, loc="left", pad=20)
    axB.text(0.0, 1.03,
             f"opens on a peak past 15 deg/s, closes at 5 deg/s, kept if it turns past {NET_DEG:.0f} deg",
             transform=axB.transAxes, fontsize=8.5, color=MUTED, va="bottom")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white")

    meta = {
        "drive": "A2D2 20180810_150607",
        "signal": "chassis (CAN) yaw rate on the chassis clock",
        "drive_length_s": round(float(t[-1]), 1),
        "n_segments": int(len(starts)),
        "segment_durations_s": [round(float(v), 2) for v in dur],
        "closeup_index": pick,
        "closeup_duration_s": round(float(b - a), 2),
        "closeup_net_deg": round(net, 1),
        "gate_levels_dps": {"trigger": TRIGGER_DPS, "edge": EDGE_DPS, "net_deg": NET_DEG},
        "sources": [str(DUMP), str(SEG)],
    }
    META.write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
