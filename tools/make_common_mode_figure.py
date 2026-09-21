#!/usr/bin/env python3
"""Common-mode elimination, on the published NH-Calib numbers.

Left   per-sensor ABSOLUTE longitudinal-offset error on A2D2: five sensors,
       five errors, all sitting in a narrow band far from zero.  That band is
       the common component -- shared slip bias, shared vehicle-frame gauge --
       and it is what referencing removes.
Right  absolute vs reference-relative X MAE on the three page datasets, so the
       case where referencing does NOT help (Ford) is visible too.

Inputs are the published result tables; nothing is recomputed here.
Run on win_lab:  "C:/Program Files/Python312/python.exe" make_common_mode_figure.py
"""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]          # .../ICRA_NH_Calib
PER_SENSOR = ROOT / "results" / "[260904]_[Table]_[BEV_5DoF_MethodComparison]" / "nh_absolute_axis.csv"
ABSREL = ROOT / "results" / "[260909]_[Table]_[NHCalib_AbsRel_5DoF]"
OUT = Path(__file__).resolve().parent.parent / "assets" / "common_mode_real.png"

INK, MUTED, RULE, SOFT = "#191919", "#666666", "#d8d8d8", "#f7f7f5"
ACCENT = "#a52e29"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9.5,
    "axes.edgecolor": RULE,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "figure.facecolor": "white",
})


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    rows = read_rows(PER_SENSOR)
    a2d2 = [r for r in rows if r["dataset"] == "A2D2"]
    names = [r["sensor"].replace("_", " ") for r in a2d2]
    px = [float(r["px_err_mm"]) for r in a2d2]
    mean_px = sum(px) / len(px)

    absrel_path = next(ABSREL.glob("*.csv"))
    ar = read_rows(absrel_path)
    x_rows = {r["dataset"]: r for r in ar if r["dof"] == "X_mm"}
    sets = ["A2D2", "RadarScenes", "Ford"]
    labels = ["A2D2\n5 LiDAR", "RadarScenes\n4 radar", "Ford Log4\n4 LiDAR"]
    abs_mae = [float(x_rows[s]["abs_mae"]) for s in sets]
    rel_mae = [float(x_rows[s]["rel_mae"]) for s in sets]

    fig, (axL, axR) = plt.subplots(
        1, 2, figsize=(10.4, 3.5), gridspec_kw={"width_ratios": [1.25, 1.0], "wspace": 0.36}
    )

    # ---- left: per-sensor absolute error, A2D2 -------------------------
    y = list(range(len(px)))[::-1]
    axL.axvspan(min(px), max(px), color=ACCENT, alpha=0.08, zorder=0)
    axL.axvline(mean_px, color=ACCENT, lw=1.2, ls="--", zorder=2)
    axL.axvline(0.0, color=INK, lw=1.0, zorder=2)
    axL.scatter(px, y, s=46, color=INK, zorder=3)
    for xi, yi in zip(px, y):
        axL.annotate(f"{xi:+.0f}", (xi, yi), textcoords="offset points",
                     xytext=(10, -3.5), ha="left", fontsize=8.5, color=MUTED)
    axL.set_yticks(y)
    axL.set_yticklabels(names, fontsize=9)
    axL.set_xlim(-98, 16)
    axL.set_ylim(-0.9, len(px) - 0.25)
    axL.set_xlabel("absolute error in $p_x$  [mm]   (estimate $-$ ground truth)")
    axL.set_title("Every A2D2 sensor misses $p_x$ the same way",
                  fontsize=10, loc="left", pad=22)
    axL.annotate(f"shared component  {mean_px:.1f} mm", (mean_px - 2.5, -0.72), ha="right",
                 va="center", fontsize=8.5, color=ACCENT)
    axL.annotate("truth", (0.0, -0.72), ha="center", va="center",
                 fontsize=8.5, color=MUTED)
    axL.text(0.0, 1.035,
             "spread about that band is only $\\pm$9 mm \u2014 referencing cancels the rest",
             transform=axL.transAxes, fontsize=8.5, color=MUTED, va="bottom")
    for side in ("top", "right"):
        axL.spines[side].set_visible(False)

    # ---- right: absolute vs relative MAE, three datasets ---------------
    xs = list(range(len(sets)))
    w = 0.34
    b1 = axR.bar([x - w / 2 for x in xs], abs_mae, w, color=RULE,
                 edgecolor=MUTED, linewidth=0.7, label="absolute (vehicle frame)")
    b2 = axR.bar([x + w / 2 for x in xs], rel_mae, w, color=ACCENT,
                 label="reference-relative")
    for bars in (b1, b2):
        for b in bars:
            axR.annotate(f"{b.get_height():.1f}", (b.get_x() + b.get_width() / 2, b.get_height()),
                         textcoords="offset points", xytext=(0, 3), ha="center",
                         fontsize=8.5, color=INK)
    axR.set_xticks(xs)
    axR.set_xticklabels(labels, fontsize=9)
    axR.set_ylim(0, 260)
    axR.set_ylabel("$p_x$ MAE  [mm]")
    axR.set_title("What referencing buys, per dataset", fontsize=10, loc="left", pad=22)
    axR.legend(frameon=False, fontsize=8.5, loc="upper right", bbox_to_anchor=(1.0, 0.80))
    axR.text(0.0, 1.035,
             "Ford is the honest exception: its absolute error is not common-mode",
             transform=axR.transAxes, fontsize=8.5, color=MUTED, va="bottom")
    for side in ("top", "right"):
        axR.spines[side].set_visible(False)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=170, bbox_inches="tight", facecolor="white")
    print("wrote", OUT)
    print("A2D2 per-sensor px err:", [round(v, 1) for v in px], "mean", round(mean_px, 1))
    print("abs/rel X MAE:", list(zip(sets, [round(v, 1) for v in abs_mae],
                                     [round(v, 1) for v in rel_mae])))


if __name__ == "__main__":
    main()
