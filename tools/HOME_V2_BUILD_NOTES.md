# Home v2 build notes (PROP-455)

Spec: `project_page/REQ_home_v2.md`. This file records the decisions and the
source material the build depends on, so the page can be rebuilt without
re-deriving them.

## Decisions (user, 2026-09-21)

| id | question | decision |
|---|---|---|
| D1 | hero sensor pair | agreed: use the reference-to-target pair of the published protocol, not an arbitrary pair |
| D2 | S5 figure | table only, no figure in the Results section |
| D3 | hero plan B -> C fallback | do not auto-fall-back; stop and ask |
| D4 | language | English throughout |

## Hero source material (plan B, real data)

- twist cache: `ailab-12:/home/ailab-12/nh_calib_lidar/a2d2_kiss_calib_v040_mr5_20260831/a2d2_kiss_twist.npz`
  - per sensor: `<NAME>__t`, `__dt`, `__vx`, `__vy`, `__vz`, `__wx`, `__wy`, `__wz` (15687 frames per LiDAR)
  - chassis: `chassis__ts`, `__vx`, `__vy`, `__wz` (105153 samples)
- reference sensor (published protocol): A2D2 = `FRONT_CENTER`
  (source `results/[260917]_[Table]_[ReferenceRelative5DoF]/manifest.json`)
- hero pair: `FRONT_CENTER` (reference) -> `FRONT_LEFT` (target)
  - GT p_y: FRONT_CENTER 0.000 m, FRONT_LEFT +0.580 m -> GT relative Y = 580.0 mm
  - both sensors share p_x = 1.711 m, so the two ego-motion arcs differ almost purely
    by the lateral offset the hero is explaining
  - published reference-relative NH-Calib error for this target: Y 1.589 mm
    (source `results/[260917]_[Table]_[ReferenceRelative5DoF]/per_sensor_errors.csv`)
  - satisfies R-C2: the displayed number is the reference-relative quantity used in the paper

## S5 table source

`results/[260917]_[Table]_[ReferenceRelative5DoF]/reference_relative_5dof.md`,
NH-Calib rows only (5 rows, within the spec limit of 6). The full 15-row
comparison including baselines stays on `wiki/results.html`.

## Card SVGs — do not regenerate

`assets/cards/*.svg` are hand-maintained. `tools/make_card_figures.py` now skips
existing files unless `--force` is passed. Hashes as of 2026-09-21:

```
381548f7256893df76af6d3daaa959225bebc2412c23218b5f983b5ef3a91839  card1-no-target.svg
103aef6291c336b33fdf2ed86f8b10cdb66e9b2e7beb7bdea5379ed05d8d86d1  card2-no-shared-fov.svg
57ed157d4d29ea15c07709efe1799f8048f56b9b00207a255079f067a12cc57c  card3-alignment-scope.svg
```

## 2026-09-21 — item 4 halted at a design gate

The spec assumed plan B needs "the existing pose/twist npz only" (§2.3). A probe on
`a2d2_kiss_twist.npz` shows that assumption does not hold for the readout in R-H4:

- the naive single-segment ratio `-dI / W` over the eight strongest turns of the drive
  gives -3842.5, -1063.8, -701.3, -433.9, -107.7, -26.4, +125.8, +140.8 mm
  against a ground truth of -580.0 mm;
- the published number is not a single-segment ratio. It needs fixed-dt renormalisation,
  motion-plane levelling, inter-sensor time alignment, common-window boundary
  interpolation, and a robust regression of dI on (W, T) over many segments.
- the only per-segment artefact on disk, `results/a2d2_common_window_20260901/`, is the
  superseded stored-dt run (FC->FL estimate 0.5224 m, 57.6 mm error), not the published one.

Halted rather than falling back automatically, per decision D3.


## 2026-09-21 — S0c, the Stage-1 companion panel

User asked for the same moving treatment applied to `p_x` and the yaw offset, on the
grounds that vehicle rotation is what fixes the lateral velocity a sensor sees.

- generator `tools/make_hero_pxyaw.py`, same construction rules as `make_hero_concept.py`:
  SMIL only, no unit-bearing number in any text, pure string building, self-refusing gate.
  The gate also resolves every `href="#id"` and `url(#id)` against the ids it emitted.
- 4.5 s loop. Left panel: straight running, the sensor velocity resolved on its own
  rotated axes. Right panel: a steady left turn about a visible ICR, where the sensor
  gains `omega * p_x`. Bottom strip: lateral velocity against turn rate, one line through
  the origin.
- labels ride with the turning vehicle but stay horizontal. Each label gets its own
  `animateMotion` track, sampled as the world path of that body point. Legitimate because
  the turn is a rigid rotation about the ICR, so every body point sweeps the same angle
  and the tracks stay in step without extra timing work.
- the opposite-turn sign flip is carried by the readout strip, not by a second geometry
  panel: a mirrored panel cannot hold both the path and a visible ICR inside the frame.
- placed inside Method (after the two-stage pipeline figure) rather than at the top of the
  page, so the page opens with one claim instead of three animated figures.
- verified by headless Chrome at frozen SMIL times 0.6 s and 2.0 s plus the static
  variant; page-level asset check reports 0 broken references out of 21.

## S0e  Stage-2 real replay (2026-09-21)

`make_hero_py_real.py` renders `assets/hero/hero_py_real.{mp4,webm,png}` from two
existing dumps -- `hero_real_20260921/hero_segments.npz` (Step-4 common-window
segments of the published fixed-dt run) and the S0d chassis path.  Left panel is
the whole A2D2 drive with the gated turns lighting up as the cursor passes them;
right panel drops one point per closed segment and re-solves the weighted
two-parameter fit from the segments closed so far.

Machine check: the script's own `wfit` over all 11 segments returns
dpy = 0.581666639 m and beta = -0.002138382 m/s, asserted equal to the published
Step-4 output to 1e-9; running estimate ends at 581.6666 mm against GT 580.0 mm.
Reveal order is drive order (`argsort(seg_end)`), not magnitude order, so the
dots are synchronised with the car on the left.
