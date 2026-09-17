# -*- coding: utf-8 -*-
"""Stage 2 algorithm pages (B1-B3)."""

# ------------------------------------------------------------------ B1
TIME = {
    "slug": "time-alignment",
    "title": "B1 &middot; Time alignment and windows",
    "crumbs": "Algorithm wiki &rsaquo; Stage 2 &rsaquo; B1",
    "tagline": "Lateral offset is the one component that two sensors must observe together. B1 builds that shared "
               "observation: it estimates the clock shift between the sensors, pairs their turns, and cuts an exact "
               "common window so that only two boundaries remain exposed to timing error.",
    "desc": "Clock-offset estimation, turn association and common-window construction in NH-Calib.",
    "infobox": [
        ("Stage", "2 &mdash; first cross-sensor step"),
        ("Input", "Per-sensor turn segments from A1; levelled yaw-rate signals"),
        ("Output", "Associated segment pairs with exact common windows and quality verdicts"),
        ("Alignment", "Yaw-rate cross-correlation, refined by alternation"),
        ("Boundary handling", "Linear interpolation at both window ends"),
        ("Quality gate", "Uncentred cosine similarity and NRMSE against the median waveform"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "why", "no": 1, "text": "Why this stage exists"},
        {"t": "p", "text": "Stage 1 needed no other sensor. Lateral offset does: a single sensor cannot separate its "
                           "own lateral offset from the platform's forward speed, because both appear in the same "
                           "scalar. Two sensors observing the same turn can, by differencing. That requires them to "
                           "agree on which turn, and on when it started and ended."},
        {"t": "p", "text": "Every remaining timing dependence in NH-Calib is concentrated here. If B1 does its job, "
                           "timing error touches the estimate only through two window boundaries rather than through "
                           "every sample."},

        {"t": "h", "level": 2, "id": "offset", "no": 2, "text": "Clock-offset estimation"},
        {"t": "p", "text": "Sensor clocks in a recorded platform are rarely aligned to better than tens of "
                           "milliseconds. The yaw-rate waveform, however, is the same physical signal seen by every "
                           "sensor, which makes it the natural alignment reference: it is modality-independent and "
                           "does not require any overlapping field of view."},
        {"t": "eq", "tag": "B1.1",
         "text": "<span class='sym'>&tau;</span><sub>ij</sub> = arg max<sub><span class='sym'>&tau;</span></sub> &nbsp; "
                 "corr( &omega;<sub>i</sub>(t), &omega;<sub>j</sub>(t + <span class='sym'>&tau;</span>) )",
         "cap": "The shift maximising the correlation of the two yaw-rate signals is taken as the clock offset of the "
                "pair."},
        {"t": "note", "kind": "key", "label": "Alternating refinement",
         "text": "Offset estimation and calibration are coupled: a better offset gives a better lateral estimate, "
                 "which in turn sharpens the signals being correlated. The two are therefore alternated for a small "
                 "number of rounds. On the radar dataset the procedure converges within three rounds, recovering "
                 "per-channel offsets in the range &minus;116.75&nbsp;ms to &minus;112.50&nbsp;ms."},
        {"t": "note", "kind": "warn",
         "text": "Time alignment is a method-neutral preprocessing step, not an advantage of NH-Calib. Any "
                 "motion-based calibration method can apply the same correction, and in the reported comparisons the "
                 "baselines are given the same aligned inputs. The claim NH-Calib makes is about <em>how many</em> "
                 "degrees of freedom depend on alignment at all, not about being robust to misalignment."},

        {"t": "h", "level": 2, "id": "assoc", "no": 3, "text": "Segment association"},
        {"t": "p", "text": "Association answers a simple question: which turn in sensor i is the same physical turn as "
                           "which turn in sensor j? It is deliberately conservative &mdash; a wrong pairing is far "
                           "more damaging than a missing one."},
        {"t": "steps", "items": [
            ["Candidate filter",
             "Two segments may be paired only if they have the same turn direction and their time intervals actually "
             "overlap after offset correction. Opposite-sign candidates are never paired."],
            ["Greedy one-to-one matching",
             "Candidates are sorted by overlap duration, longest first, and matched greedily. Each segment is used at "
             "most once, so a long turn in one sensor cannot absorb several turns in the other."],
            ["Reject the unmatched",
             "Segments with no partner are dropped for this pair. They may still be used by another sensor pair, and "
             "they remain valid inputs to Stage 1, which is per-sensor."],
        ]},
        {"t": "note", "kind": "code",
         "text": "Association is performed on the shared segment list produced by A1. No sensor re-detects turns at "
                 "this point; re-detection would let two sensors disagree about segment boundaries for reasons "
                 "unrelated to their mounting."},

        {"t": "h", "level": 2, "id": "window", "no": 4, "text": "Common windows and boundary interpolation"},
        {"t": "p", "text": "Two associated segments rarely start and end at the same instant. Integrating over "
                           "different intervals would compare different motions, so the integration window is defined "
                           "as their intersection."},
        {"t": "eq", "tag": "B1.2",
         "text": "t<sub>0,k</sub> = max<sub>j</sub> t<sub>0,j,k</sub>, &nbsp;&nbsp;&nbsp;&nbsp; "
                 "t<sub>1,k</sub> = min<sub>j</sub> t<sub>1,j,k</sub>",
         "cap": "Latest start, earliest end. If the intersection is empty the pair is rejected rather than stretched."},
        {"t": "p", "text": "These boundaries generally fall between samples. Each sensor's motion is therefore linearly "
                           "interpolated at both ends, so that both integrals genuinely begin and end at the same "
                           "instants rather than at the nearest available samples."},
        {"t": "note", "kind": "key",
         "text": "This is what confines timing sensitivity to two points. Whatever residual clock error remains after "
                 "B1.1 affects only the two interpolated boundary strips, whereas a sample-wise formulation would "
                 "expose every sample in the turn."},

        {"t": "h", "level": 2, "id": "qc", "no": 5, "text": "Segment quality verdict"},
        {"t": "p", "text": "Association guarantees that two segments overlap in time, not that they describe the same "
                           "motion well. Inside the common window each sensor's yaw-rate waveform is compared against "
                           "the median waveform of the participating sensors."},
        {"t": "table",
         "head": ["Statistic", "What it catches", "Why this form"],
         "rows": [
             ["Uncentred cosine similarity",
              "A sensor whose waveform has the wrong shape or the wrong sign",
              "Mean removal would delete the sign information itself on drives dominated by one turn direction, so "
              "the similarity is deliberately uncentred."],
             ["Normalized RMSE",
              "A sensor whose waveform has the right shape but the wrong magnitude",
              "Cosine similarity is scale-invariant; NRMSE supplies the missing scale check."],
         ],
         "cap": "Both statistics are computed jointly; a sensor&ndash;segment combination that fails either one is "
                "excluded from subsequent processing for that pair."},
        {"t": "note", "kind": "warn", "label": "This gate is usually inert",
         "text": "On the reported datasets the accepted segments sit far inside the thresholds, so tightening or "
                 "loosening the gate over a wide range changes the result by nothing at all. The gate is a guard "
                 "against pathological segments, not a tuning knob that improves accuracy. Tightening it far enough "
                 "to start rejecting segments makes the result worse, because it removes information."},
        {"t": "note", "kind": "code",
         "text": "The reference waveform is a median across sensors, not the reference sensor's own waveform. Using "
                 "one designated channel as the yardstick would make the verdict circular whenever that channel is "
                 "the degraded one."},
    ],
    "seealso": [
        ("m1-turn-segments.html", "A1 &middot; Turn-segment extraction", "produces the segments being associated"),
        ("sum-form.html", "B2 &middot; Sum-form relative Y", "consumes the common windows"),
        ("observability.html", "Observability decomposition", "why exactly one component depends on this stage"),
    ],
}

# ------------------------------------------------------------------ B2
SUMFORM = {
    "slug": "sum-form",
    "title": "B2 &middot; Sum-form relative Y",
    "crumbs": "Algorithm wiki &rsaquo; Stage 2 &rsaquo; B2",
    "tagline": "Two sensors on the same turning platform travel concentric arcs. Over one complete turn their "
               "path-length difference is proportional to the heading change and to their lateral separation &mdash; "
               "and the unknown vehicle speed cancels out entirely.",
    "desc": "Pairwise relative lateral offset from integrated arc-length differences over common turning windows.",
    "infobox": [
        ("Stage", "2 &mdash; per sensor pair"),
        ("Input", "Common windows from B1; levelled forward velocity and yaw rate"),
        ("Output", "Pairwise <span class='sym'>&Delta;</span>p<sub>y</sub>, its standard error, segment count"),
        ("Core relation", "<span class='sym'>&Delta;</span>I<sub>k</sub> = &minus;<span class='sym'>&Delta;</span>p<sub>y</sub> W<sub>k</sub>"),
        ("Estimator", "Weighted robust linear regression over segments"),
        ("Minimum data", "Two associated segments; design rank at least two"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "lever", "no": 1, "text": "The same lever arm, now longitudinal"},
        {"t": "p", "text": "A4 used the lateral component of the rigid-body velocity relation. B2 uses the "
                           "longitudinal one: a sensor mounted to the left or right of the rotation centre travels "
                           "faster or slower along the vehicle's forward direction during a turn."},
        {"t": "eq", "tag": "B2.1",
         "text": "v<sub>j,x</sub> = v<sub>c,x</sub> &minus; &omega; p<sub>y,j</sub>",
         "cap": "The platform speed v<sub>c,x</sub> is common to every sensor and unknown, which is exactly why a "
                "single sensor cannot solve for its own lateral offset."},
        {"t": "p", "text": "Differencing two sensors at the same instant removes the common speed and leaves the "
                           "lateral separation. That instantaneous form, however, requires the two sensors to be "
                           "compared sample by sample &mdash; every sample then carries the full weight of any clock "
                           "error."},
        {"t": "eq", "tag": "B2.2",
         "text": "<span class='sym'>&Delta;</span>v<sub>x</sub> = v<sub>i,x</sub> &minus; v<sub>j,x</sub> "
                 "= &minus;&omega; ( p<sub>y,i</sub> &minus; p<sub>y,j</sub> ) = &minus;&omega; <span class='sym'>&Delta;</span>p<sub>y</sub>",
         "cap": "Correct, but sample-wise: this is the formulation NH-Calib deliberately does <em>not</em> use."},

        {"t": "h", "level": 2, "id": "sum", "no": 2, "text": "Integrating instead of differencing"},
        {"t": "p", "text": "Integrating both sides over the common window turns a per-sample constraint into one "
                           "measurement per segment. Timing error then acts only at the two boundaries, which B1 has "
                           "already interpolated."},
        {"t": "eq", "tag": "B2.3",
         "text": "I<sub>i,k</sub> = &int;<sub>t<sub>0,k</sub></sub><sup>t<sub>1,k</sub></sup> v<sub>i,x</sub>(t) dt, "
                 "&nbsp;&nbsp; I<sub>j,k</sub> = &int;<sub>t<sub>0,k</sub></sub><sup>t<sub>1,k</sub></sup> v<sub>j,x</sub>(t) dt, "
                 "&nbsp;&nbsp; W<sub>k</sub> = &int;<sub>t<sub>0,k</sub></sub><sup>t<sub>1,k</sub></sup> &omega;(t) dt = <span class='sym'>&Delta;&theta;</span><sub>k</sub>",
         "cap": "Forward distance travelled by each sensor over the identical window, and the platform's accumulated "
                "rotation in radians."},
        {"t": "eq", "tag": "B2.4",
         "text": "<span class='sym'>&Delta;</span>I<sub>k</sub> = I<sub>i,k</sub> &minus; I<sub>j,k</sub> "
                 "= &minus; <span class='sym'>&Delta;</span>p<sub>y,ij</sub> W<sub>k</sub>",
         "cap": "The arc-length difference of two concentric arcs is the radius difference times the swept angle. "
                "Sign convention: <span class='sym'>&Delta;</span>I = I<sub>i</sub> &minus; I<sub>j</sub> paired with "
                "<span class='sym'>&Delta;</span>p<sub>y,ij</sub> = p<sub>y,i</sub> &minus; p<sub>y,j</sub>."},
        {"t": "note", "kind": "key", "label": "Why this is the central trick",
         "text": "The vehicle's forward speed profile &mdash; unknown, time-varying, and shared &mdash; disappears "
                 "completely from (B2.4). What remains is a straight line through the origin whose slope is the "
                 "quantity being calibrated. No speed sensor, no map, and no overlapping field of view is involved."},

        {"t": "h", "level": 2, "id": "regress", "no": 3, "text": "Regression over segments"},
        {"t": "p", "text": "Each associated segment contributes one point (W<sub>k</sub>, "
                           "<span class='sym'>&Delta;</span>I<sub>k</sub>). Collecting them across the drive turns "
                           "calibration into a one-dimensional slope-fitting problem."},
        {"t": "eq", "tag": "B2.5",
         "text": "Z<sub>k</sub> = p<sub>y</sub> W<sub>k</sub> + <span class='sym'>&beta;</span> T<sub>k</sub> + <span class='sym'>&epsilon;</span><sub>k</sub>, "
                 "&nbsp;&nbsp;&nbsp; w<sub>k</sub> = |W<sub>k</sub>|<sup>&nbsp;p&minus;2</sup>",
         "cap": "A two-parameter weighted fit. The second term, proportional to segment duration T<sub>k</sub>, "
                "absorbs a slowly varying scale discrepancy between the two channels so that it is not mistaken for "
                "lateral offset. With the default weight exponent p = 0.5 the weight is |W<sub>k</sub>|<sup>&minus;1.5</sup>."},
        {"t": "ul", "items": [
            "At least two associated segments are required and the design matrix must have rank two; otherwise the "
            "pair is rejected rather than reported with a fabricated confidence.",
            "Large |W<sub>k</sub>| segments carry more slope information, which is why weighting is expressed in terms "
            "of accumulated heading rather than duration or sample count.",
            "Both turn directions should be represented. A drive that only ever turns one way still identifies the "
            "slope, but a drift between channels aliases into it far more easily.",
            "Because each segment gives one independent measurement, the standard error scales with the number of "
            "valid turns &mdash; which is why a drive with more turning windows reports a tighter result.",
        ]},
        {"t": "note", "kind": "code", "label": "Representative value",
         "text": "A sensor pair produces one measurement per segment, and those measurements scatter. The pair's "
                 "reported value is the robust aggregate, obtained with an M-estimator. Alternatives &mdash; plain "
                 "least squares, RANSAC, median &mdash; were compared and the choice of aggregator was not the "
                 "dominant error source."},

        {"t": "h", "level": 2, "id": "limit", "no": 4, "text": "What limits the accuracy"},
        {"t": "p", "text": "The estimator consumes odometry, so its accuracy is bounded by how differently the two "
                           "channels' odometry drifts inside a window. Feeding ground-truth trajectories into the same "
                           "estimator produces sub-millimetre agreement, which localises the residual error in the "
                           "front end rather than in the formulation."},
        {"t": "ul", "items": [
            "Per-window scatter is the dominant term, and it does not shrink by reweighting or by re-detecting "
            "windows &mdash; both were tested and neither helps.",
            "It does shrink with more independent turns. Pooling several logs of the same platform reduced the "
            "reported lateral error substantially on the Ford configuration.",
            "Common-window construction removes boundary mismatch but not differential drift <em>inside</em> the "
            "window; that part is a genuine lower bound set by the odometry.",
            "The same lower bound applies to interval-based hand&ndash;eye methods, which consume the same integrated "
            "motion. Only methods that register raw point clouds against each other avoid it &mdash; at the cost of "
            "requiring overlapping fields of view.",
        ]},
    ],
    "seealso": [
        ("time-alignment.html", "B1 &middot; Time alignment", "how the common window is built"),
        ("graph.html", "B3 &middot; Graph integration", "combining many pairwise measurements"),
        ("m3-x-yaw.html", "A4 &middot; X, Yaw and slip", "the lateral counterpart of the same lever arm"),
    ],
}

# ------------------------------------------------------------------ B3
GRAPH = {
    "slug": "graph",
    "title": "B3 &middot; Graph integration",
    "crumbs": "Algorithm wiki &rsaquo; Stage 2 &rsaquo; B3",
    "tagline": "Pairwise answers disagree around a cycle. Treating sensors as nodes and pairwise lateral offsets as "
               "weighted edges turns many inconsistent differences into one consistent layout with a single fixed "
               "reference.",
    "desc": "Robust weighted least-squares fusion of pairwise relative-Y measurements.",
    "infobox": [
        ("Stage", "2 &mdash; final fusion"),
        ("Input", "Pairwise d<sub>ij</sub> and confidence w<sub>ij</sub> from B2"),
        ("Output", "One lateral offset per sensor, relative to the reference"),
        ("Structure", "Nodes = sensors, edges = pairwise measurements"),
        ("Gauge", "y<sub>r</sub> = 0 at the reference sensor"),
        ("Scope", "Lateral offset only &mdash; the other four components are single-valued"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "why", "no": 1, "text": "Why only this component needs fusion"},
        {"t": "p", "text": "Roll, pitch, yaw and longitudinal offset each come out of Stage 1 as one number per "
                           "sensor. There is nothing to reconcile: no second estimate of the same quantity exists, so "
                           "no optimization is needed for them."},
        {"t": "p", "text": "Lateral offset is different. B2 produces one measurement per <em>pair</em>, and with N "
                           "sensors there are up to N(N&minus;1)/2 of them for only N&minus;1 free values. The system "
                           "is overdetermined, and the redundancy shows up as cycle inconsistency: going i &rarr; j "
                           "&rarr; k &rarr; i does not return exactly zero."},
        {"t": "note", "kind": "key",
         "text": "The graph is therefore not a heavyweight back end. It is the minimal machinery needed to turn "
                 "redundant scalar differences into one consistent set of values &mdash; a robust weighted "
                 "least-squares problem in N&minus;1 unknowns."},

        {"t": "h", "level": 2, "id": "form", "no": 2, "text": "Formulation"},
        {"t": "eq", "tag": "B3.1",
         "text": "<strong>y</strong>* = arg min<sub>{y<sub>j</sub>}, y<sub>r</sub>=0</sub> &nbsp; "
                 "&sum;<sub>(i,j) &isin; E</sub> <span class='sym'>&rho;</span>( w<sub>ij</sub> [ (y<sub>i</sub> &minus; y<sub>j</sub>) &minus; d<sub>ij</sub> ] )",
         "cap": "<span class='sym'>&rho;</span> is a robust loss; w<sub>ij</sub> is the confidence of the pairwise "
                "regression that produced d<sub>ij</sub>; fixing the reference node removes the remaining gauge "
                "freedom."},
        {"t": "table",
         "head": ["Element", "Meaning", "Source"],
         "rows": [
             ["Node y<sub>j</sub>", "Lateral offset of sensor j relative to the reference", "Unknown being solved"],
             ["Edge d<sub>ij</sub>", "Measured lateral difference of the pair", "B2 regression slope"],
             ["Weight w<sub>ij</sub>", "Confidence of that pair", "Regression standard error and segment count"],
             ["Loss <span class='sym'>&rho;</span>", "Robust kernel suppressing outlier edges",
              "Pairs with few or poorly conditioned segments"],
             ["Constraint y<sub>r</sub> = 0", "Gauge fixing", "Same reference sensor as A5 and A3"],
         ]},
        {"t": "note", "kind": "gauge",
         "text": "Without the constraint the cost is invariant to adding a constant to every node: the problem "
                 "determines differences, not absolute positions. Fixing the reference is the cleanest way to remove "
                 "that freedom, and it keeps the output consistent with the reference-relative convention used "
                 "everywhere else."},

        {"t": "h", "level": 2, "id": "absolute", "no": 3, "text": "Optional metric anchor"},
        {"t": "p", "text": "The graph can be closed against the vehicle frame instead of against a sensor. Wheel "
                           "odometry from the vehicle bus is introduced as a virtual node whose lateral offset is "
                           "known to be zero, because it refers to the rear-axle centre by construction."},
        {"t": "eq", "tag": "B3.2",
         "text": "y<sub>CAN</sub> &equiv; 0 &nbsp;&rArr;&nbsp; y<sub>j</sub> becomes absolute p<sub>y,j</sub> in the vehicle frame",
         "cap": "One extra node converts every relative value into a vehicle-frame absolute value, with no change to "
                "the estimator itself."},
        {"t": "note", "kind": "warn",
         "text": "This is a channel-configuration property, not a property unique to NH-Calib: any method able to "
                 "consume a wheel-odometry channel can close the gauge the same way. It is described here because it "
                 "is the only route from relative to absolute lateral offset within the method."},

        {"t": "h", "level": 2, "id": "out", "no": 4, "text": "Final output"},
        {"t": "p", "text": "The Stage 2 lateral offsets are combined with the Stage 1 reference-relative roll, pitch, "
                           "yaw and longitudinal offset to form the complete result: a five-degree-of-freedom "
                           "reference-relative extrinsic calibration for every sensor."},
        {"t": "eq", "tag": "B3.3",
         "text": "T&#770;<sub>rj</sub> = ( <span class='sym'>&phi;</span><sub>rj</sub>, <span class='sym'>&theta;</span><sub>rj</sub>, "
                 "<span class='sym'>&psi;</span><sub>rj</sub>, p<sub>x,rj</sub>, p<sub>y,rj</sub> ), "
                 "&nbsp;&nbsp; p<sub>z</sub> not estimated",
         "cap": "Vertical offset is excluded because planar motion provides no observation of it &mdash; a property of "
                "the motion, shared by every motion-based method."},
    ],
    "seealso": [
        ("sum-form.html", "B2 &middot; Sum-form relative Y", "produces the edges"),
        ("relativization.html", "A5 &middot; Reference relativization", "supplies the other four components"),
        ("observability.html", "Observability decomposition", "why p<sub>z</sub> is absent"),
    ],
}

PAGES = [TIME, SUMFORM, GRAPH]
