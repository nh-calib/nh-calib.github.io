"""PROP-458 item1: dump A2D2 Step-3 (M3) intermediates for one channel.

Runs the real nh_calib_core pipeline and captures, by monkeypatching the two
entry points the pipeline itself calls, exactly the arrays M3/M4 consumed.
No re-implementation of the estimator here.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/home/ailab-12/git/nh_calib")
from nh_calib_core import pipeline, planar  # noqa: E402

NPZ = "/home/ailab-12/nh_calib_lidar/a2d2_final_calibration_20260811/a2d2_lidar5_final_twist.npz"
OUT = Path("/home/ailab-12/nh_calib_lidar/a2d2_s0d_dump_20260921")
TARGET = "FRONT_CENTER"

OUT.mkdir(parents=True, exist_ok=True)

captured = {"samples": {}, "levelled": {}, "segments": {}, "chassis_segments": None}

_orig_samples = planar.planar_samples
_orig_step4 = planar.step4_py


def _spy_samples(levelled, chassis, *a, **kw):
    out = _orig_samples(levelled, chassis, *a, **kw)
    # identify channel by sample count at call time; pipeline calls in dict order
    captured["samples"][len(captured["samples"])] = (levelled, out)
    return out


def _spy_step4(levelled, chassis, psi, *a, **kw):
    out = _orig_step4(levelled, chassis, psi, *a, **kw)
    captured["segments"][len(captured["segments"])] = (
        kw.get("target_segments"), kw.get("reference_segments"), out)
    return out


planar.planar_samples = _spy_samples
planar.step4_py = _spy_step4

streams, chassis, planar_only = pipeline.load_twist_cache(NPZ)

# A2D2 fixed-dt condition: the recorded per-frame stamps are pathological
# (dataset defect, not a method defect).  Rewrite every sensor stream onto a
# uniform 30 Hz grid and rescale velocities by dt*30, because the cached
# velocities were formed as delta/dt with those stamps.
FS = 30.0
for _n, _d in list(streams.items()):
    _d = dict(_d)
    _k = np.asarray(_d["dt"], float) * FS
    for _f in ("vx", "vy", "vz", "wx", "wy", "wz"):
        if _f in _d:
            _d[_f] = np.asarray(_d[_f], float) * _k
    _n0 = len(np.asarray(_d["t"], float))
    _d["t"] = float(np.asarray(_d["t"], float)[0]) + np.arange(_n0) / FS
    _d["dt"] = np.full(_n0, 1.0 / FS)
    streams[_n] = _d
DT_MODE = "fixed"
names = sorted(streams)
print("channels:", names, flush=True)

result = pipeline.calibrate(streams, chassis, planar_only=planar_only)

planar.planar_samples = _orig_samples
planar.step4_py = _orig_step4

order = [n for n in names if n in result["sensors"]]
idx = order.index(TARGET)
levelled, sample = captured["samples"][idx]
tgt_segs, ref_segs, step4 = captured["segments"][idx]

row = result["sensors"][TARGET]
psi = np.radians(row["psi_deg"])
px = float(row["px_m"])
c = float(result["slip"]["c"])

t = np.asarray(sample["t"], float)
vx = np.asarray(sample["vx"], float)
vy = np.asarray(sample["vy"], float)
om = np.asarray(sample["om"], float)
vc = np.asarray(sample["vc"], float)
lateral = np.sin(psi) * vx + np.cos(psi) * vy
resid = lateral - om * px + vc * np.tan(np.clip(c * vc * om, -1.4, 1.4))

# ego BEV path from CAN only (no GT): integrate vx, wz on the chassis clock
ct = np.asarray(chassis["t"], float)
cvx = np.asarray(chassis["vx"], float)
cwz = np.asarray(chassis["wz"], float)
dt = np.diff(ct, prepend=ct[0])
head = np.cumsum(cwz * dt)
ex = np.cumsum(cvx * np.cos(head) * dt)
ey = np.cumsum(cvx * np.sin(head) * dt)

segs = [{k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
         for k, v in s.items() if k not in ("i0", "i1")} for s in (tgt_segs or [])]

np.savez_compressed(
    OUT / f"s0d_{TARGET.lower()}_m3.npz",
    t=t, vx=vx, vy=vy, om=om, vc=vc, lateral=lateral, resid=resid,
    lv_t=np.asarray(levelled["t"], float),
    lv_wz=np.asarray(levelled["wz"], float),
    ch_t=ct, ch_vx=cvx, ch_wz=cwz, ch_head=head, ch_x=ex, ch_y=ey,
)

meta = {
    "source_npz": NPZ,
    "dt_mode": "fixed",
    "channel": TARGET,
    "psi_deg": row["psi_deg"],
    "px_m": row["px_m"],
    "py_m": row.get("py_m"),
    "c": c,
    "n_samples": int(t.size),
    "sample_counts": {k: int(v) for k, v in sample["counts"].items()},
    "n_turn_segments_channel": len(segs),
    "residual_rms_mps": float(np.sqrt(np.mean(resid ** 2))),
    "t_span_s": [float(t[0]), float(t[-1])],
    "om_span_degps": [float(np.degrees(om.min())), float(np.degrees(om.max()))],
    "vc_span_mps": [float(vc.min()), float(vc.max())],
    "turn_segments": segs,
    "all_sensors": {n: {k: result["sensors"][n][k] for k in ("psi_deg", "px_m", "py_m")
                        if k in result["sensors"][n]} for n in order},
}
(OUT / f"s0d_{TARGET.lower()}_meta.json").write_text(
    json.dumps(meta, indent=2), encoding="utf-8")

print(json.dumps({k: v for k, v in meta.items() if k != "turn_segments"}, indent=2))
print("WROTE", OUT)
