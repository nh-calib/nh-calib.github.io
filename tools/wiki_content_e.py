# -*- coding: utf-8 -*-
"""Material that did not fit in the paper.

Four pages: the raw sensor/drive inventory, what the turn-segment detector
actually found in each drive, how the odometry front ends behaved, and the
full ablation catalogue.

Every number here is transcribed from a result artefact in results/ or
experiments/. Where a number comes from a superseded configuration or from an
oracle, the page says so on the same line. Numbers marked "diagnostic" must not
be quoted as headline accuracy.
"""

# =====================================================================
#  E1 -- sensor and drive inventory
# =====================================================================
INVENTORY = {
    "slug": "data-inventory.html",
    "title": "Sensor and drive inventory",
    "crumbs": "NH-Calib &rsaquo; Algorithm wiki &rsaquo; Behind the paper",
    "tagline": "What is physically in each recording: sensor layout, published extrinsics, drive statistics for "
               "every candidate log, sample counts that reach the estimator, and the measured co-visibility "
               "between sensor pairs. Most of this did not fit in the paper.",
    "desc": "Sensor layouts, published extrinsics, per-drive statistics and measured pairwise co-visibility for "
            "the three NH-Calib evaluation datasets.",
    "infobox_title": "Inventory at a glance",
    "infobox": [
        ("Sensors scored", "5 LiDAR + 4 radar + 4 LiDAR"),
        ("Ford logs profiled", "6 (3 usable)"),
        ("Stage-1 samples", "0.7k&ndash;19k per sensor"),
        ("Co-visibility range", "0.000 &ndash; 0.884"),
        ("Extrinsic frame", "vehicle FLU, rear-axle centre"),
        ("Source", "results/ artefacts, not the paper"),
    ],
    "blocks": [
        {"t": "note", "kind": "note",
         "text": "This page is reference material. The paper reports a subset; the tables below are the full "
                 "inventory the experiments were drawn from, including the drives that were rejected."},

        {"t": "h", "level": 2, "id": "layouts", "no": "1", "text": "Sensor layouts and published extrinsics"},
        {"t": "p", "text": "All three layouts are given in the vehicle frame used for scoring: x forward, y left, "
                           "z up, origin at the rear-axle centre. These are the published values, used only to "
                           "score &mdash; never inside the estimator."},

        {"t": "h", "level": 3, "text": "A2D2 &mdash; five LiDARs"},
        {"t": "table",
         "head": ["Sensor", "p<sub>x</sub> [m]", "p<sub>y</sub> [m]", "Mounting yaw [deg]", "Role"],
         "rows": [
             ["FRONT_CENTER", "1.711", "0.000", "+1.225", "reference"],
             ["FRONT_LEFT", "1.711", "+0.580", "+4.646", "target"],
             ["FRONT_RIGHT", "1.711", "&minus;0.580", "&minus;0.380", "target"],
             ["SIDE_LEFT", "0.651", "+0.580", "+91.088", "target"],
             ["SIDE_RIGHT", "0.651", "&minus;0.580", "&minus;93.067", "target"],
         ],
         "cap": "Published A2D2 extrinsics as consumed by the scoring code. The two side units are yawed roughly "
                "&plusmn;90&deg;, which is why they share almost no structure with the front units."},

        {"t": "h", "level": 3, "text": "RadarScenes &mdash; four radars"},
        {"t": "table",
         "head": ["Sensor", "p<sub>x</sub> [m]", "p<sub>y</sub> [m]", "Mounting yaw [deg]", "Role"],
         "rows": [
             ["RADAR_1", "3.663", "&minus;0.873", "&minus;85.038", "reference"],
             ["RADAR_2", "3.860", "&minus;0.700", "&minus;24.992", "target"],
             ["RADAR_3", "3.860", "+0.700", "+24.981", "target"],
             ["RADAR_4", "3.663", "+0.873", "+85.027", "target"],
         ],
         "cap": "All four radars sit on the front bumper within 0.2 m in x; the layout is a yaw fan, not a ring. "
                "The outer pair looks almost sideways."},
        {"t": "note", "kind": "warn",
         "text": "An earlier internal note described RADAR_3 and RADAR_4 as rear units. That was a naming error; "
                 "the published x coordinates place all four on the front bumper."},

        {"t": "h", "level": 3, "text": "Ford Multi-AV &mdash; four HDL-32E"},
        {"t": "table",
         "head": ["Sensor", "p<sub>x</sub> [m]", "p<sub>y</sub> [m]", "p<sub>z</sub> [m]", "Mounting yaw [deg]",
                  "Role"],
         "rows": [
             ["RED", "1.132", "+0.378", "1.406", "&minus;90.396", "reference"],
             ["YELLOW", "1.126", "+0.501", "1.272", "&minus;90.649", "target"],
             ["BLUE", "1.112", "&minus;0.369", "1.415", "&minus;90.300", "target"],
             ["GREEN", "1.122", "&minus;0.521", "1.292", "&minus;90.028", "target"],
         ],
         "cap": "Converted from the published Ford FRD body frame into the FLU vehicle frame. The four roof units "
                "are within 1.02 m of each other laterally and all spin 360&deg;, so their fields of view overlap "
                "heavily &mdash; the opposite of the A2D2 case."},
        {"t": "note", "kind": "key",
         "text": "YELLOW and GREEN carry a real mounting pitch near &plusmn;25&deg;. That is a genuine installation "
                 "value, not an estimation error, and it is why a planar two-dimensional hand-eye variant cannot "
                 "represent this layout."},

        {"t": "h", "level": 2, "id": "ford-logs", "no": "2", "text": "Ford: all six logs profiled, three used"},
        {"t": "p", "text": "Six Ford V2 logs were downloaded and profiled before any calibration was run. The "
                           "profile is computed from the released pose stream alone and decides whether a drive "
                           "carries enough rotation to be usable at all."},
        {"t": "table",
         "head": ["Log", "Poses", "Duration [s]", "Distance [m]", "v median / p95 [m/s]",
                  "|&omega;| p95 / max [deg/s]", "Turns (L/R)", "Total turn yaw [deg]", "Gate"],
         "rows": [
             ["Log1", "146,136", "826.3", "17,035", "24.7 / 28.5", "3.79 / 21.4", "2 (1/1)", "118", "FAIL"],
             ["Log2", "198,162", "1089.1", "23,268", "24.3 / 29.9", "4.15 / 24.5", "1 (1/0)", "78", "FAIL"],
             ["Log3", "169,125", "931.3", "9,239", "11.4 / 17.9", "2.29 / 18.3", "1 (1/0)", "48", "FAIL"],
             ["Log4", "131,694", "722.7", "4,474", "6.2 / 13.5", "8.30 / 28.3", "6 (4/2)", "364", "PASS"],
             ["Log5", "162,356", "888.1", "7,462", "7.9 / 16.8", "13.06 / 26.8", "11 (7/4)", "765", "PASS"],
             ["Log6", "114,600", "630.0", "5,256", "7.3 / 16.8", "13.82 / 29.0", "9 (5/4)", "650", "PASS"],
         ],
         "cap": "Pose stream is released at about 200 Hz in every log. The gate requires at least three detected "
                "turns; Log1&ndash;Log3 are highway or arterial drives and fail it."},
        {"t": "note", "kind": "key",
         "text": "The three rejected logs are not bad recordings. They are fast, straight drives &mdash; exactly "
                 "the regime in which this method has nothing to work with. A drive with 78&deg; of total turning "
                 "over 23 km cannot identify a lever arm, and the gate says so before any odometry is run."},
        {"t": "note", "kind": "warn",
         "text": "Log1 was nevertheless run end-to-end early in the project, before the gate existed. Two of its "
                 "four channels lost tracking in the 26&ndash;29 m/s section and the four-channel common segment "
                 "count fell to zero. That outcome is consistent with the gate, and the Log1 numbers were dropped."},

        {"t": "h", "level": 2, "id": "samples", "no": "3", "text": "What actually reaches the estimator"},
        {"t": "table",
         "head": ["Dataset", "Unit", "Per-sensor count", "Note"],
         "rows": [
             ["A2D2", "accepted turn samples entering the X / Yaw fit", "699",
              "one drive, 5 sensors"],
             ["RadarScenes", "accepted turn samples entering the X / Yaw fit", "19,114 &ndash; 19,300",
              "pooled over 158 sequences; 91.5k additional straight-driving samples feed the offset alignment"],
             ["Ford Log4", "odometry frames per channel", "6,608 &ndash; 6,620", "about 9.15 Hz"],
             ["Ford Log5", "odometry frames per channel", "8,125 &ndash; 8,133", ""],
             ["Ford Log6", "odometry frames per channel", "5,733 &ndash; 5,749", ""],
         ],
         "cap": "Sample counts differ by three orders of magnitude between A2D2 and RadarScenes. The A2D2 result "
                "rests on far fewer samples than its error suggests, which is why its standard error matters."},

        {"t": "h", "level": 2, "id": "overlap", "no": "4",
         "text": "Measured co-visibility between sensor pairs"},
        {"t": "p", "text": "The paper argues qualitatively that A2D2 side units share no view with the front ones "
                           "and that the Ford roof units share a great deal. That claim was measured. Two local "
                           "maps are placed in the same frame using the published extrinsics &mdash; so the measure "
                           "does not depend on what any registration converged to &mdash; and overlap is the "
                           "smaller of the two directional fractions of points with a partner within 0.5 m (LiDAR) "
                           "or 1.0 m (radar)."},
        {"t": "table",
         "head": ["Dataset", "Pair", "Overlap, single scan", "Overlap, accumulated window",
                  "Registration &Delta;p<sub>y</sub> error [mm]"],
         "rows": [
             ["A2D2", "FL&ndash;FR", "0.884", "0.970", "1.30"],
             ["A2D2", "FC&ndash;FR", "0.639", "0.771", "12.22"],
             ["A2D2", "FC&ndash;FL", "0.655", "0.771", "14.97"],
             ["A2D2", "FR&ndash;SR", "0.047", "0.457", "28.23"],
             ["A2D2", "FL&ndash;SR", "0.000", "0.412", "no consensus"],
             ["A2D2", "FC&ndash;SR", "0.000", "0.368", "no consensus"],
             ["A2D2", "FL&ndash;SL", "0.081", "0.284", "no consensus"],
             ["A2D2", "FR&ndash;SL", "0.024", "0.251", "no consensus"],
             ["A2D2", "FC&ndash;SL", "0.000", "0.151", "1328.08"],
             ["A2D2", "SL&ndash;SR", "0.000", "0.003", "1179.74"],
             ["RadarScenes", "R1&ndash;R2", "0.215", "0.321", "111.88"],
             ["RadarScenes", "R2&ndash;R3", "0.194", "0.315", "1201.17"],
             ["RadarScenes", "R3&ndash;R4", "0.237", "0.299", "622.54"],
             ["RadarScenes", "R1&ndash;R3", "0.007", "0.022", "2364.53"],
             ["RadarScenes", "R2&ndash;R4", "0.002", "0.006", "1953.75"],
             ["RadarScenes", "R1&ndash;R4", "0.000", "0.000", "1879.88"],
             ["Ford Log4", "BLUE&ndash;RED", "0.522", "0.829", "2.46"],
             ["Ford Log4", "BLUE&ndash;YELLOW", "0.387", "0.650", "15.56"],
             ["Ford Log4", "RED&ndash;YELLOW", "0.419", "0.633", "1.53"],
             ["Ford Log4", "BLUE&ndash;GREEN", "0.386", "0.611", "33.65"],
             ["Ford Log4", "GREEN&ndash;RED", "0.351", "0.604", "25.06"],
             ["Ford Log4", "GREEN&ndash;YELLOW", "0.333", "0.465", "9.87"],
         ],
         "cap": "Window lengths: 5 s for the two LiDAR datasets, 4 s for RadarScenes. A2D2 pairs are ordered by "
                "accumulated overlap; three of the four non-converged pairs sit below 0.42."},
        {"t": "ul", "items": [
            "Accumulating a window helps but does not rescue a non-overlapping pair: A2D2 SL&ndash;SR goes from "
            "0.000 to 0.003 over five seconds of driving.",
            "Across the 18 pairs where registration converged, the rank correlation between overlap and "
            "registration error is <strong>&rho; = &minus;0.897</strong> (p = 4.7&times;10<sup>&minus;7</sup>).",
            "The four A2D2 pairs where registration found no consensus all sit at overlap &le; 0.41, so including "
            "them could only strengthen the trend.",
        ]},
        {"t": "note", "kind": "note",
         "text": "The paper presents this relationship as a picture of two real local maps rather than as a "
                 "correlation coefficient, on the grounds that a reader who has not seen the overlap definition "
                 "cannot interpret the number. The measurement is kept here."},

        {"t": "h", "level": 2, "id": "other", "no": "5", "text": "Datasets examined and not used"},
        {"t": "table",
         "head": ["Dataset", "Why it was examined", "Why it is not a result"],
         "rows": [
             ["TruckDrive", "Multi-LiDAR and multi-radar truck recordings with per-trip extrinsics.",
              "The available chassis yaw rate is derived from one of the LiDAR odometries, so a yaw-rate metric "
              "computed against it is circular. Published extrinsics also change between trips, which breaks "
              "per-scene pooling. Retained only as a limitation."],
             ["MTS", "Six LiDAR channels with turn segments already indexed.",
              "Per-frame rotation noise is large enough that every method tested, including the trivial "
              "zero-offset estimator, lands in the same error band. Rankings from it are not quotable."],
             ["Waymo", "Considered as an additional multi-LiDAR source.",
              "Short-range side units; kept as an auxiliary robustness case only."],
         ],
         "cap": "Datasets that were processed but produce no reportable calibration number, with the specific "
                "reason in each case."},
    ],
    "seealso": [
        ("datasets.html", "Datasets &amp; front end", "the configuration summary the paper reports"),
        ("segments.html", "Turn segments in the data", "what the detector found in each of these drives"),
        ("odometry.html", "Odometry front end results", "how well the twist behind these numbers tracked"),
    ],
}


# =====================================================================
#  E2 -- turn segments in the data
# =====================================================================
SEGMENTS = {
    "slug": "segments.html",
    "title": "Turn segments in the data",
    "crumbs": "NH-Calib &rsaquo; Algorithm wiki &rsaquo; Behind the paper",
    "tagline": "The detector output for every drive: how many turns were found, how long they were, what fraction "
               "passed the quality test, how many survived intersection into common windows, and how that count "
               "tracks the final error.",
    "desc": "Turn-segment counts, durations, quality-gate statistics and common-window survival for each NH-Calib "
            "evaluation drive.",
    "infobox_title": "Segment statistics",
    "infobox": [
        ("Peak threshold", "15 deg/s"),
        ("Hold threshold", "5 deg/s"),
        ("Minimum turn yaw", "30 deg"),
        ("Ford segments scored", "108 sensor-segments"),
        ("Quality pass ratio", "0.90 &ndash; 1.00"),
        ("Common windows kept", "5 / 14 / 8 (Ford), 11 (A2D2)"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "rule", "no": "1", "text": "What counts as a turn"},
        {"t": "p", "text": "A candidate turn opens when the magnitude of the yaw rate crosses the hold level and is "
                           "kept only if it later peaks above the peak level and accumulates enough total heading "
                           "change. Short gaps below the hold level are bridged rather than splitting the segment "
                           "in two."},
        {"t": "table",
         "head": ["Parameter", "Value", "Effect if raised", "Effect if lowered"],
         "rows": [
             ["Hold level", "5 deg/s", "segments shorten and lose their entry and exit ramps",
              "straight driving leaks in and dilutes the regression"],
             ["Peak level", "15 deg/s", "gentle sweeping turns are discarded",
              "weak-excitation segments enter and inflate the spread"],
             ["Minimum accumulated yaw", "30 deg", "fewer, stronger segments",
              "many short segments with poor conditioning"],
             ["Maximum internal gap", "0.3 s", "one physical turn splits into several segments",
              "two separate turns merge into one"],
         ],
         "cap": "Detection parameters as used for drive profiling. The calibration pipeline's segment builder "
                "applies the same rate logic; it does not enforce a separate hard minimum duration, so segment "
                "length is a consequence of the rate and yaw conditions rather than a parameter."},
        {"t": "note", "kind": "note",
         "text": "The detector runs independently on each sensor's own twist. Two sensors on the same vehicle "
                 "therefore produce two segment lists that are close but not identical &mdash; reconciling them is "
                 "Stage 2's job, not the detector's."},

        {"t": "h", "level": 2, "id": "perdrive", "no": "2", "text": "What was found in each drive"},
        {"t": "table",
         "head": ["Drive", "Turns detected", "Turn time fraction", "Total turn yaw [deg]",
                  "Windows kept after intersection"],
         "rows": [
             ["Ford Log4", "6 (4 left / 2 right)", "0.092", "364", "5"],
             ["Ford Log5", "11 (7 left / 4 right)", "0.115", "765", "14"],
             ["Ford Log6", "9 (5 left / 4 right)", "0.147", "650", "8"],
             ["Ford Log1", "2", "&mdash;", "118", "0 across four channels"],
             ["Ford Log2", "1", "&mdash;", "78", "not run"],
             ["Ford Log3", "1", "&mdash;", "48", "not run"],
             ["A2D2", "about 12 per sensor", "&mdash;", "&mdash;", "11"],
         ],
         "cap": "Turn time fraction is the share of the drive spent inside a detected turn. Ford Log5 keeps more "
                "windows than it has detected turns because long turns split into several usable common windows."},
        {"t": "note", "kind": "key",
         "text": "The three usable Ford logs spend between 9 % and 15 % of their time turning. The rejected ones "
                 "spend almost none. Everything this method estimates about the lateral offset comes out of that "
                 "small fraction of the recording."},

        {"t": "h", "level": 2, "id": "quality", "no": "3", "text": "Per-segment quality statistics"},
        {"t": "p", "text": "Every sensor-segment is scored against the consensus of the other channels before it is "
                           "allowed into the estimate. Detection on each sensor's own twist yields 5, 12 and 10 turn segments in "
                           "Log4, Log5 and Log6, which over four channels gives 108 scored sensor-segments. "
                           "That count differs from the pose-profile turn count in the table above because the "
                           "two detectors run on different signals."},
        {"t": "table",
         "head": ["Log", "Sensor-segments scored", "Pass ratio", "Angular cosine, median",
                  "Angular NRMSE, median", "Forward-speed ratio, median"],
         "rows": [
             ["Log4", "20", "0.95", "0.9958", "0.095", "1.003"],
             ["Log5", "48", "1.00", "0.9961", "0.089", "1.012"],
             ["Log6", "40", "0.90", "0.9961", "0.090", "0.987"],
         ],
         "cap": "Medians across all sensor-segments of each log. The cosine gate sits at 0.95 and the NRMSE gate at "
                "0.25, so the median segment clears both with a wide margin."},
        {"t": "note", "kind": "warn",
         "text": "That margin is the point of a separate ablation: because almost nothing is near the threshold, "
                 "sweeping the gate over a wide range changes the result by nothing at all. See the "
                 "<a href='ablations.html#gates'>ablation catalogue</a>."},
        {"t": "table",
         "head": ["Log4 sensor", "Segment", "Duration [s]", "Angular cosine", "Angular NRMSE",
                  "Forward-speed ratio"],
         "rows": [
             ["RED", "0", "3.27", "0.9980", "0.067", "0.975"],
             ["RED", "3", "7.39", "0.9967", "0.082", "1.035"],
             ["YELLOW", "0", "3.27", "0.9960", "0.094", "0.973"],
             ["YELLOW", "3", "7.39", "0.9941", "0.111", "1.024"],
             ["BLUE", "0", "3.27", "0.9970", "0.080", "1.012"],
             ["BLUE", "3", "7.39", "0.9964", "0.086", "0.982"],
             ["GREEN", "0", "3.27", "0.9947", "0.109", "1.033"],
             ["GREEN", "3", "7.39", "0.9914", "0.132", "0.984"],
         ],
         "cap": "A slice of the raw per-segment table for Ford Log4. Segment durations run from about 3.3 s to "
                "7.4 s; GREEN is consistently the weakest channel and RED the strongest, in that order, on every "
                "segment."},

        {"t": "h", "level": 2, "id": "common", "no": "4", "text": "From per-sensor segments to common windows"},
        {"t": "p", "text": "Two sensors contribute one measurement only over the interval where both of their "
                           "segments are active. The A2D2 run recorded that intersection in detail."},
        {"t": "ul", "items": [
            "<strong>221</strong> associated sensor-pair segments were logged across the directed pairs.",
            "<strong>11</strong> common windows survived intersection across all five sensors, averaging about "
            "9.3 s each.",
            "<strong>100 %</strong> of window boundaries required interpolation &mdash; no boundary landed exactly "
            "on a sample of both channels.",
            "Mean angular-rate cosine between the paired channels over the common windows: <strong>0.9847</strong>.",
            "Mean absolute difference in accumulated heading between reference and target over a window: "
            "<strong>0.048 rad</strong> (about 2.7&deg;).",
        ]},
        {"t": "note", "kind": "key",
         "text": "Boundary interpolation is not an optional refinement. If every boundary needs it, then skipping "
                 "it means every window is truncated at a sample edge, and the truncation error enters the "
                 "integrated arc difference directly."},

        {"t": "h", "level": 2, "id": "count", "no": "5", "text": "Window count versus final error"},
        {"t": "table",
         "head": ["Pool", "Common windows", "Relative Y MAE [mm]", "RMSE [mm]", "max [mm]",
                  "Median pairwise standard error [mm]"],
         "rows": [
             ["Ford Log4", "5", "32.91", "36.53", "63.52", "19.9"],
             ["Ford Log5", "14", "24.72", "27.59", "47.96", "22.7"],
             ["Ford Log6", "8", "8.01", "9.10", "12.77", "34.6"],
             ["Ford Log4 + Log5", "19", "16.72", "21.31", "32.91", "18.1"],
             ["Ford Log4 + Log5 + Log6", "27", "10.60", "12.72", "23.82", "16.5"],
         ],
         "cap": "Pooling windows across logs, which is possible because the Ford extrinsics are constant across "
                "the recording campaign. The pooled row is a diagnostic; the paper scores each log separately."},
        {"t": "ul", "items": [
            "More windows reduce the error, but not as fast as independent averaging would predict &mdash; the "
            "standard error falls only from 19.9 mm to 16.5 mm while the count rises five-fold, so the "
            "per-window errors are not independent.",
            "Log6 has fewer windows than Log5 yet a much lower error, so window count alone does not determine "
            "accuracy; per-window spread does.",
            "The per-window spread of the lateral estimate is about 50 mm standard deviation over 60 windows. That "
            "spread, not the estimator, is what sets the Ford error floor.",
        ]},
        {"t": "note", "kind": "warn",
         "text": "Do not quote the pooled 10.60 mm as a Ford result. It mixes three drives into one number, and "
                 "the paper deliberately reports Log4, Log5 and Log6 as three independent evaluation sets."},
    ],
    "seealso": [
        ("m1-turn-segments.html", "A1 &middot; Turn-segment extraction", "the detector itself"),
        ("time-alignment.html", "B1 &middot; Time alignment &amp; windows", "how the intersection and interpolation work"),
        ("ablations.html", "Ablation catalogue", "what changing the segment gates does, and does not, do"),
    ],
}


# =====================================================================
#  E3 -- odometry front end results
# =====================================================================
ODOMETRY = {
    "slug": "odometry.html",
    "title": "Odometry front end results",
    "crumbs": "NH-Calib &rsaquo; Algorithm wiki &rsaquo; Behind the paper",
    "tagline": "How well the motion input actually tracked, per channel and per drive: path-length agreement "
               "against the released pose stream, the deskew and voxel settings that decide whether tracking "
               "survives, the A2D2 timestamp defect, and the two datasets where the front end was the limit.",
    "desc": "Per-channel odometry quality, deskew and voxel sensitivity, timestamp pathologies and front-end "
            "failure cases behind the NH-Calib results.",
    "infobox_title": "Front-end summary",
    "infobox": [
        ("LiDAR backend", "KISS-ICP, voxel 0.20&ndash;0.30 m"),
        ("Ford path agreement", "0.978 &ndash; 1.001 of GT"),
        ("Deskew off penalty", "10.5&times; &ndash; 44&times;"),
        ("Voxel 0.10 m", "tracking collapse"),
        ("A2D2 stored dt", "alternating, unusable"),
        ("Radar geometric odometry", "not usable"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "role", "no": "1", "text": "What the calibrator sees"},
        {"t": "p", "text": "NH-Calib never touches points. It consumes a per-sensor twist &mdash; linear and "
                           "angular velocity with timestamps &mdash; so every front-end defect arrives at the "
                           "estimator already converted into a velocity error. A ground-truth-trajectory control "
                           "run makes the split explicit: feeding the estimator the released pose stream instead "
                           "of odometry brings the Ford lateral error down to <strong>0.82 mm</strong> on the same "
                           "windows, against about 12 mm for odometry input. The estimator is not the bottleneck; "
                           "the twist is."},
        {"t": "note", "kind": "warn",
         "text": "The 0.82 mm figure is an oracle diagnostic. It uses a ground-truth trajectory as input and can "
                 "never be reported as an achieved calibration accuracy."},

        {"t": "h", "level": 2, "id": "ford-channels", "no": "2", "text": "Ford: per-channel tracking quality"},
        {"t": "p", "text": "Each of the four Ford channels is tracked independently over the whole drive. Path "
                           "length against the released pose stream is the cheapest honest check: it is sensitive "
                           "to scale error and to lost tracking, and it needs no alignment."},
        {"t": "table",
         "head": ["Log", "Channel", "Frames", "Path length [m]", "Reference distance [m]", "Ratio",
                  "Yaw-rate p95 [deg/s]"],
         "rows": [
             ["Log4", "RED", "6,615", "4,478.2", "4,473.9", "1.0010", "8.39"],
             ["Log4", "YELLOW", "6,620", "4,474.1", "4,473.9", "1.0000", "7.50"],
             ["Log4", "BLUE", "6,609", "4,476.0", "4,473.9", "1.0005", "8.42"],
             ["Log4", "GREEN", "6,614", "4,376.2", "4,473.9", "0.9782", "6.31"],
             ["Log5", "RED", "8,125", "7,464.5", "7,461.8", "1.0004", "12.91"],
             ["Log5", "YELLOW", "8,133", "7,310.5", "7,461.8", "0.9797", "11.55"],
             ["Log5", "BLUE", "8,130", "7,460.9", "7,461.8", "0.9999", "13.04"],
             ["Log5", "GREEN", "8,127", "7,441.7", "7,461.8", "0.9973", "11.55"],
             ["Log6", "RED", "5,739", "5,261.0", "5,255.9", "1.0010", "13.41"],
             ["Log6", "YELLOW", "5,733", "5,237.7", "5,255.9", "0.9965", "10.74"],
             ["Log6", "BLUE", "5,749", "5,262.2", "5,255.9", "1.0012", "13.87"],
             ["Log6", "GREEN", "5,746", "5,257.3", "5,255.9", "1.0003", "11.75"],
         ],
         "cap": "All twelve channel runs registered every frame (valid rate 1.000) and completed. Ratios are "
                "path length divided by the distance travelled according to the released poses."},
        {"t": "ul", "items": [
            "Ten of the twelve channels land within 0.3 % of the reference distance.",
            "The two outliers &mdash; Log4 GREEN at 0.978 and Log5 YELLOW at 0.980 &mdash; are the same channels "
            "that carry the largest mounting pitch, and they are the channels with the weakest per-segment quality "
            "scores.",
            "A 2 % path deficit is not visible in a trajectory plot but is exactly the kind of differential scale "
            "error that integrates into the lateral estimate.",
        ]},
        {"t": "note", "kind": "note",
         "text": "This is also the check that caught the earlier Ford Log1 failures: two channels there produced "
                 "path ratios of 0.34 and 0.51, which is tracking loss rather than drift."},

        {"t": "h", "level": 2, "id": "deskew", "no": "3", "text": "Deskew is not optional on Ford"},
        {"t": "p", "text": "An HDL-32E completes one revolution in roughly 0.1 s. At 6 m/s the sensor moves about "
                           "0.6 m during a single sweep, which is twice the registration voxel. Three deskew "
                           "conditions were run end to end."},
        {"t": "table",
         "head": ["Condition", "Log4 [mm]", "Log5 [mm]", "Log6 [mm]", "Mean [mm]", "Common windows kept"],
         "rows": [
             ["External point-time deskew", "32.91", "24.72", "8.01", "21.88", "5 / 14 / 8"],
             ["KISS internal deskew", "32.91", "24.72", "8.01", "21.88", "5 / 14 / 8"],
             ["No deskew", "345.48", "370.79", "353.95", "356.74", "4 / 8 / 3"],
         ],
         "cap": "Relative Y MAE over twelve directed pairs. The two deskew paths agree to within 1e-9 m on all "
                "three logs; the difference between them is only which initial motion estimate is used to correct."},
        {"t": "ul", "items": [
            "Turning off deskew costs a factor of 10.5 to 44 depending on the log.",
            "It also costs segments: the number of accepted common windows drops in every log, so the damage is "
            "visible in the quality gates before it is visible in the error.",
            "External and internal deskew are numerically tied. Neither can be described as better.",
        ]},
        {"t": "note", "kind": "warn",
         "text": "These conditions re-detect segments independently, so the comparison is end-to-end. It is not a "
                 "measurement of deskew alone on a fixed window set."},

        {"t": "h", "level": 2, "id": "voxel", "no": "4", "text": "Voxel size: the failure is abrupt"},
        {"t": "p", "text": "A planned sweep over registration voxel sizes stopped at its first cell. At 0.10 m the "
                           "front end collapsed rather than degrading: the GREEN channel's median speed statistic "
                           "fell to 0.49 m/s against 5.93 m/s at 0.30 m, and YELLOW to 3.13 m/s against 6.06. RED "
                           "and BLUE were unaffected. With two channels lost, only one turn could be associated "
                           "and the lateral stage raised an error instead of producing a number."},
        {"t": "ul", "items": [
            "A finer voxel is not a conservative choice here. It removes the structure the scan matcher needs in "
            "a sparse 32-beam cloud.",
            "The same pattern was seen independently on another dataset, where a 0.10 m voxel dropped the segment "
            "pass rate from 78 % to 53 % against 0.30 m.",
            "The remaining sweep points (0.20, 0.40, 0.60 m) were never run, because the runner aborted the whole "
            "experiment on the first cell's exception instead of isolating it. No voxel-sweep numbers exist.",
        ]},
        {"t": "note", "kind": "note",
         "text": "Reported so that the absence is explicit: there is no voxel sensitivity curve for this method. "
                 "The 0.30 m point is the one that was validated."},

        {"t": "h", "level": 2, "id": "a2d2-dt", "no": "5", "text": "A2D2: the stored frame interval is defective"},
        {"t": "p", "text": "A2D2 stores a per-frame time interval alongside the scans. Those stored intervals "
                           "alternate: successive values swing high and low around the true rate, giving a lag-one "
                           "autocorrelation near &minus;0.5. Reconstructing velocity from pose increments divided "
                           "by such an interval injects an alternating velocity error into every channel."},
        {"t": "table",
         "head": ["Channel", "Interval CV", "Frames disagreeing with the timestamp difference by &gt;2 %",
                  "Lag-1 autocorrelation", "Turn yaw-rate RMSE, stored &rarr; fixed [deg/s]"],
         "rows": [
             ["FRONT_CENTER", "0.286", "90.1 %", "&minus;0.458", "3.32 &rarr; 0.88"],
             ["FRONT_LEFT", "0.139", "71.8 %", "&minus;0.496", "1.92 &rarr; 0.32"],
             ["FRONT_RIGHT", "0.171", "75.4 %", "&minus;0.498", "2.64 &rarr; 0.34"],
             ["SIDE_LEFT", "0.169", "74.9 %", "&minus;0.489", "2.62 &rarr; 0.38"],
             ["SIDE_RIGHT", "0.119", "53.6 %", "&minus;0.478", "2.03 &rarr; 0.65"],
         ],
         "cap": "Computed without ground truth. The last column is the angular-rate disagreement against the "
                "consensus of the other channels, before and after replacing the stored interval with the nominal "
                "30 Hz spacing."},
        {"t": "note", "kind": "key",
         "text": "This is why the A2D2 runs use a fixed nominal interval. It is a data defect correction, not a "
                 "convenience. Its effect on the final result is the single largest factor in the whole ablation "
                 "catalogue &mdash; see <a href='ablations.html#dt'>dt and window</a>."},
        {"t": "p", "text": "The same statistics were computed on the other candidate datasets to check whether the "
                           "defect is general. It is not: the other multi-LiDAR sources show interval variation of "
                           "0.2&ndash;2 %, disagreement rates below 0.3 %, positive lag-one autocorrelation, and "
                           "turn yaw-rate RMSE that is unchanged to four digits when the interval definition is "
                           "swapped. A2D2 is the only affected dataset."},

        {"t": "h", "level": 2, "id": "radar", "no": "6", "text": "RadarScenes: why the input is constructed"},
        {"t": "p", "text": "Geometric radar odometry was not usable on this data. The detections are too sparse and "
                           "too weakly structured to register scan to scan; the co-visibility measurements on the "
                           "<a href='data-inventory.html#overlap'>inventory page</a> show cross-pairs at 0.000 to "
                           "0.022. The motion input is therefore Doppler ego-velocity combined with a CAN yaw rate, "
                           "aligned iteratively."},
        {"t": "table",
         "head": ["Sensor", "Estimated clock offset [ms]", "Yaw-rate RMSE before &rarr; after [deg/s]",
                  "Forward-velocity residual RMS [m/s]", "Samples"],
         "rows": [
             ["RADAR_1", "&minus;116.75", "2.23 &rarr; 1.94", "0.116", "19,114"],
             ["RADAR_2", "&minus;112.50", "5.25 &rarr; 4.48", "0.286", "19,300"],
             ["RADAR_3", "&minus;115.50", "4.09 &rarr; 4.04", "0.257", "19,254"],
             ["RADAR_4", "&minus;115.25", "2.01 &rarr; 1.76", "0.105", "19,176"],
         ],
         "cap": "Three alternating passes of offset estimation and calibration. All four offsets converge into a "
                "4 ms band around &minus;115 ms, which is consistent with a single fixed bus-to-sensor latency "
                "rather than four independent errors."},
        {"t": "note", "kind": "warn",
         "text": "Because this path takes its angular rate from the vehicle bus, the per-sensor longitudinal offset "
                 "is no longer invariant to a sensor-to-bus timing error. That is a stated limitation of the "
                 "alternative-input path, not a property of the method."},

        {"t": "h", "level": 2, "id": "backend", "no": "7", "text": "Backend choice and the datasets it could not save"},
        {"t": "table",
         "head": ["Case", "Observation", "Consequence"],
         "rows": [
             ["Ford Log4, GICP instead of KISS-ICP", "67.56 mm versus 32.93 mm lateral error on the same windows",
              "the point-to-plane variant was not adopted; the difference is front-end quality, not estimator "
              "behaviour"],
             ["A truck dataset with side LiDARs",
              "turn yaw-rate disagreement of 26&ndash;28 deg/s on the side channels, while the frame-interval "
              "statistics are clean",
              "the limit is odometry quality, not timing; excluded from results"],
             ["A six-LiDAR dataset",
              "per-channel rotation disagreement of 4&ndash;9 deg/s; every method tested lands in the same error "
              "band as a trivial zero estimator",
              "no ranking can be drawn from it; reported as a limitation"],
         ],
         "cap": "Two datasets were processed to completion and still produce no usable calibration, for reasons "
                "located entirely in the motion input."},
        {"t": "note", "kind": "key",
         "text": "The pattern across all of these is the same: this method's accuracy ceiling is the differential "
                 "quality of the per-channel twist inside turns. Nothing in Stage 1 or Stage 2 can recover what "
                 "the front end did not measure."},
    ],
    "seealso": [
        ("datasets.html", "Datasets &amp; front end", "the configuration table for the reported runs"),
        ("ablations.html", "Ablation catalogue", "the controlled experiments these observations motivated"),
        ("failure-modes.html", "Gates &amp; failure modes", "how a bad twist is detected at run time"),
    ],
}


# =====================================================================
#  E4 -- ablation catalogue
# =====================================================================
ABLATIONS = {
    "slug": "ablations.html",
    "title": "Ablation catalogue",
    "crumbs": "NH-Calib &rsaquo; Algorithm wiki &rsaquo; Behind the paper",
    "tagline": "Every controlled experiment run on the pipeline, including the ones the paper has no room for and "
               "the ones that changed nothing. Each entry states what was varied, what was held fixed, the "
               "numbers, and what may not be concluded from them.",
    "desc": "Full catalogue of NH-Calib ablations: time interval, common window, clock offset, slip coefficient, "
            "representative estimator, attitude oracle, deskew, pooling and graph integration.",
    "infobox_title": "Catalogue",
    "infobox": [
        ("Entries", "9 experiments"),
        ("Largest single effect", "frame interval, &minus;83 %"),
        ("Smallest", "quality gate, exactly zero"),
        ("Oracle entries", "2, marked as diagnostics"),
        ("Withdrawn conclusions", "1 (attenuation claim)"),
    ],
    "blocks": [
        {"t": "note", "kind": "note",
         "text": "House rule for this page: one factor changes per row, the input stream and the estimator stay "
                 "fixed, and ground truth is used only to score. Rows that break the rule are labelled."},

        {"t": "h", "level": 2, "id": "dt", "no": "1", "text": "Frame interval and common window"},
        {"t": "p", "text": "Two factors crossed on A2D2 over 20 directed pairs: whether the defective stored frame "
                           "interval or a fixed nominal interval is used, and whether each sensor integrates over "
                           "its own turn windows or over the intersected common window."},
        {"t": "table",
         "head": ["Frame interval", "Window handling", "MAE [mm]", "RMSE [mm]", "max [mm]", "Mean windows"],
         "rows": [
             ["stored", "per-sensor windows", "125.18", "139.32", "223.39", "12.2"],
             ["stored", "common window, quality gate off", "145.76", "168.00", "287.36", "11.0"],
             ["stored", "common window, quality gate on", "103.69", "122.67", "249.16", "10.3"],
             ["fixed 30 Hz", "per-sensor windows", "21.08", "24.70", "45.35", "12.2"],
             ["fixed 30 Hz", "common window, quality gate off", "2.8615", "3.3186", "5.570", "11.0"],
             ["fixed 30 Hz", "common window, quality gate on", "2.8615", "3.3186", "5.570", "11.0"],
         ],
         "cap": "Relative Y MAE on A2D2. The two fixed-interval common-window rows agree to sixteen digits."},
        {"t": "ul", "items": [
            "Fixing the frame interval alone accounts for <strong>&minus;83 %</strong> of the error. It is the "
            "dominant factor in the entire catalogue.",
            "On top of a correct time base, the common window is worth a further factor of about seven.",
            "On a corrupted time base the common window is <em>worse</em> than per-sensor windows by 16 % unless "
            "the quality gate is on &mdash; so the apparent benefit of the common window under the stored interval "
            "was entirely the gate rejecting corrupted observations.",
            "Once the time base is correct, the gate rejects nothing at all, which is why the last two rows are "
            "identical.",
        ]},

        {"t": "h", "level": 2, "id": "tau", "no": "2", "text": "Injected clock offset"},
        {"t": "p", "text": "A synthetic offset is added to one channel's timestamps and the whole estimator is "
                           "re-run, over a grid up to &plusmn;763 ms &mdash; the native acquisition offset between "
                           "the A2D2 front and side units. Two questions are asked at once: which degrees of "
                           "freedom move, and whether integrating over a segment attenuates the offset relative to "
                           "fitting the same model per sample."},
        {"t": "table",
         "head": ["|&tau;| [ms]", "Sum-form, common window", "Sum-form, per-sensor windows",
                  "Same model, per sample", "Ratio", "Hand-eye SE(3)", "Hand-eye SE(2)"],
         "rows": [
             ["0", "2.47", "26.36", "3.08", "1.2", "40.53", "24.02"],
             ["33", "2.56", "26.36", "7.41", "2.9", "55.04", "28.77"],
             ["67", "3.77", "26.36", "19.00", "5.0", "70.71", "37.38"],
             ["100", "5.68", "26.36", "31.25", "5.5", "84.33", "46.12"],
             ["200", "16.41", "26.36", "70.70", "4.3", "128.66", "64.14"],
             ["400", "50.42", "26.36", "150.72", "3.0", "150.14", "107.50"],
             ["763", "pair rejected", "26.36", "280.51", "&mdash;", "292.60", "204.01"],
         ],
         "cap": "Relative Y MAE [mm] over the pairs containing the shifted channel. Hand-eye columns use the same "
                "fair input and the same quantity."},
        {"t": "ul", "items": [
            "Roll, pitch, mounting yaw and the longitudinal offset have a peak-to-peak variation of "
            "<strong>exactly zero</strong> across the entire grid. Not approximately flat &mdash; bit-identical, "
            "because the per-sensor stage never reads another sensor's clock.",
            "Integrating over a segment attenuates the offset by <strong>3&ndash;5&times;</strong> relative to the "
            "identical model fitted per sample.",
            "Beyond the segment overlap the common-window estimator returns no estimate rather than a biased one. "
            "The pair is rejected. That is a safety property.",
            "The per-sensor-window variant is completely offset-blind at 26.36 mm everywhere &mdash; and ten times "
            "worse at zero offset. Accuracy is bought with offset sensitivity, and the pipeline buys it and then "
            "adds explicit alignment.",
        ]},
        {"t": "note", "kind": "warn",
         "text": "An earlier internal conclusion rejecting the attenuation claim was withdrawn after this run: the "
                 "original comparison had no per-sample control in it. Equally, none of this supports saying the "
                 "method is more robust to synchronisation than hand-eye. Alignment is method-neutral "
                 "pre-processing and was applied to hand-eye too. The defensible statement is the reduced number "
                 "of degrees of freedom that depend on alignment."},
        {"t": "table",
         "head": ["Angular-rate source", "Longitudinal offset error at &plusmn;763 ms sensor-to-bus offset [mm]"],
         "rows": [
             ["vehicle bus (default)", "&minus;284 &hellip; &minus;717"],
             ["the sensor's own angular rate", "&minus;1.9 &hellip; &minus;38.9"],
         ],
         "cap": "The longitudinal offset is invariant to sensor-to-sensor offsets but not to a sensor-to-bus "
                "offset when the angular rate is taken from the bus. Mounting yaw stays below 0.13&deg; in every "
                "condition."},

        {"t": "h", "level": 2, "id": "slip", "no": "3", "text": "Slip coefficient"},
        {"t": "p", "text": "The lateral-velocity relaxation term carries one shared coefficient. Three conditions: "
                           "free fitting, forcing it to zero, and forcing a physically motivated positive prior."},
        {"t": "table",
         "head": ["Dataset", "Front end", "Condition", "c [s&sup2;/m]", "Yaw MAE [deg]",
                  "Absolute X MAE [mm]", "Relative Y MAE [mm]"],
         "rows": [
             ["A2D2", "KISS-ICP", "free", "&minus;0.00359", "0.034", "58.26", "2.86"],
             ["A2D2", "KISS-ICP", "c = 0", "0", "0.052", "43.23", "3.56"],
             ["A2D2", "KISS-ICP", "c = +0.0066", "+0.00660", "0.194", "230.27", "4.81"],
             ["Ford Log4", "KISS-ICP", "free", "&minus;0.00356", "0.430", "57.65", "32.93"],
             ["Ford Log4", "KISS-ICP", "c = 0", "0", "0.448", "106.09", "33.29"],
             ["Ford Log4", "KISS-ICP", "c = +0.0066", "+0.00660", "0.475", "197.80", "34.36"],
             ["Ford Log4", "GICP", "free", "+0.00276", "0.482", "79.22", "67.56"],
             ["RadarScenes", "Doppler + CAN", "free", "+0.00490", "0.070", "64.81", "16.69"],
             ["RadarScenes", "Doppler + CAN", "c = 0", "0", "0.079", "219.92", "16.57"],
             ["RadarScenes", "Doppler + CAN", "c = +0.0066", "+0.00660", "0.070", "11.97", "16.39"],
         ],
         "cap": "One estimator, one input stream per dataset; only the coefficient handling changes."},
        {"t": "ul", "items": [
            "The relative lateral result moves by at most 2 mm across all three conditions. The coefficient enters "
            "every sensor identically, so the relative estimate largely cancels it.",
            "The absolute longitudinal offset is what pays, and it pays the predicted amount: 13&ndash;32 mm per "
            "0.001 s&sup2;/m, matching the angular-rate-weighted mean square speed lever to within 10 %.",
            "The fitted sign is <em>not</em> stable across front ends &mdash; the same drive gives "
            "&minus;0.00356 with one backend and +0.00276 with another. It is therefore treated as a nuisance "
            "parameter that absorbs a common odometry bias, not as a vehicle property.",
            "Correlation between the coefficient and the longitudinal offset runs +0.40 to +0.70, with normal-matrix "
            "condition numbers of 5.0e3 to 2.2e4. The two are not cleanly separable at constant speed.",
        ]},

        {"t": "h", "level": 2, "id": "estimator", "no": "4", "text": "Representative estimator"},
        {"t": "p", "text": "Which robust statistic condenses the per-sample fits. All four use the same accepted "
                           "samples and the same coefficient."},
        {"t": "table",
         "head": ["Dataset", "Least squares", "M-estimator", "Median", "RANSAC"],
         "rows": [
             ["A2D2 &mdash; Yaw MAE [deg]", "0.026", "0.034", "0.027", "0.030"],
             ["A2D2 &mdash; X MAE [mm]", "55.83", "58.26", "55.80", "55.92"],
             ["Ford Log4 &mdash; Yaw MAE [deg]", "0.462", "0.430", "0.499", "0.451"],
             ["Ford Log4 &mdash; X MAE [mm]", "86.00", "57.65", "94.32", "54.72"],
             ["RadarScenes &mdash; Yaw MAE [deg]", "0.058", "0.070", "0.081", "0.069"],
             ["RadarScenes &mdash; X MAE [mm]", "68.46", "64.81", "69.27", "65.23"],
         ],
         "cap": "The choice of representative estimator is worth a few percent on clean data and about 35 % on "
                "the longitudinal offset in the noisiest dataset."},
        {"t": "note", "kind": "key",
         "text": "The representative estimator is not the source of the residual error. On A2D2 all four agree to "
                 "within 3 mm; the shipped M-estimator is kept because it is the most stable on the noisy dataset, "
                 "not because it wins everywhere."},

        {"t": "h", "level": 2, "id": "oracle", "no": "5", "text": "Attitude oracle injection"},
        {"t": "p", "text": "A reviewer question: if the levelling attitude or the mounting yaw were perfect, how "
                           "much of the remaining error would disappear? Ground truth is injected into the pipeline "
                           "and the rest is re-estimated on fixed windows."},
        {"t": "table",
         "head": ["Dataset", "Condition", "Relative X MAE [mm]", "Relative Yaw MAE [deg]",
                  "Relative Y MAE [mm]"],
         "rows": [
             ["A2D2", "estimated roll/pitch, estimated yaw", "11.14", "0.023", "3.28"],
             ["A2D2", "ground-truth roll/pitch, yaw re-estimated", "11.04", "0.038", "3.31"],
             ["A2D2", "estimated roll/pitch, ground-truth yaw", "&mdash;", "&mdash;", "3.01"],
             ["A2D2", "ground-truth roll/pitch and yaw", "&mdash;", "&mdash;", "3.55"],
             ["Ford Log4", "estimated roll/pitch, estimated yaw", "40.98", "0.354", "35.17"],
             ["Ford Log4", "ground-truth roll/pitch, yaw re-estimated", "41.73", "0.280", "35.40"],
             ["Ford Log4", "estimated roll/pitch, ground-truth yaw", "&mdash;", "&mdash;", "35.52"],
             ["Ford Log4", "ground-truth roll/pitch and yaw", "&mdash;", "&mdash;", "36.35"],
         ],
         "cap": "Oracle diagnostic. Every cell uses ground truth inside the pipeline and none of them is an "
                "achievable accuracy."},
        {"t": "ul", "items": [
            "Replacing the estimated attitude with ground truth changes the lateral result by less than 1 mm, and "
            "in two of the four conditions makes it slightly worse.",
            "So Stage-1 attitude error is not the cause of the residual lateral error. The residual lives in the "
            "per-window integration of differential odometry error.",
            "That does not make levelling optional. Removing it entirely degrades the A2D2 lateral result from "
            "about 33 mm to 50 mm on the Ford case &mdash; levelling is a necessary pre-condition whose remaining "
            "error no longer matters.",
        ]},

        {"t": "h", "level": 2, "id": "deskew-abl", "no": "6", "text": "Deskew"},
        {"t": "table",
         "head": ["Condition", "Log4", "Log5", "Log6", "Windows kept"],
         "rows": [
             ["deskew on (either path)", "32.91", "24.72", "8.01", "5 / 14 / 8"],
             ["deskew off", "345.48", "370.79", "353.95", "4 / 8 / 3"],
         ],
         "cap": "Relative Y MAE [mm]. Detailed in the <a href='odometry.html#deskew'>odometry page</a>."},

        {"t": "h", "level": 2, "id": "pooling", "no": "7", "text": "Pooling windows across drives"},
        {"t": "table",
         "head": ["Pool", "Windows", "MAE [mm]", "max [mm]", "Median standard error [mm]"],
         "rows": [
             ["Log4", "5", "32.91", "63.52", "19.9"],
             ["Log5", "14", "24.72", "47.96", "22.7"],
             ["Log6", "8", "8.01", "12.77", "34.6"],
             ["Log4 + Log5", "19", "16.72", "32.91", "18.1"],
             ["Log4 + Log5 + Log6", "27", "10.60", "23.82", "16.5"],
         ],
         "cap": "Diagnostic only. The paper scores each log separately; this row set exists to show how much of "
                "the single-log error is sample noise."},

        {"t": "h", "level": 2, "id": "graph", "no": "8", "text": "Graph integration versus direct pairs"},
        {"t": "table",
         "head": ["Dataset", "Directed edges", "Direct pairwise MAE [mm]", "Graph MAE [mm]",
                  "Direct max cycle error [mm]", "Graph max cycle error [mm]"],
         "rows": [
             ["A2D2", "20", "2.862", "2.848", "0.980", "2.2e&minus;16"],
             ["RadarScenes", "12", "16.572", "16.586", "1.515", "3.6e&minus;15"],
             ["Ford Log4", "12", "32.912", "31.293", "12.811", "0.000"],
             ["Ford Log5", "12", "24.724", "24.750", "1.824", "3.6e&minus;15"],
             ["Ford Log6", "12", "8.006", "7.280", "16.893", "1.8e&minus;15"],
         ],
         "cap": "The final Stage-2 output is the graph column. Antisymmetry and cycle closure become exact by "
                "construction."},
        {"t": "ul", "items": [
            "Consistency is enforced, not encouraged: cycle error drops from up to 16.9 mm to numerical zero.",
            "Accuracy moves both ways &mdash; better on Ford Log4 and Log6, marginally worse on RadarScenes and "
            "Log5 &mdash; because the consistency projection is not supervised by ground truth.",
            "Direct pairwise MAE is therefore kept as an edge-quality diagnostic, and the graph value is the "
            "reported score.",
        ]},

        {"t": "h", "level": 2, "id": "gates", "no": "9", "text": "Things that changed nothing"},
        {"t": "p", "text": "Negative results, kept because each one closes off an obvious suggestion."},
        {"t": "table",
         "head": ["What was tried", "Result", "Why it does not help"],
         "rows": [
             ["Sweeping the segment quality gate over seven levels and four turn thresholds",
              "identical MAE across six of the seven levels; only the tightest setting changed anything, and it "
              "made the result worse",
              "the accepted segments clear the threshold by a wide margin, so the gate is inert on clean input"],
             ["Re-weighting windows by duration instead of the shipped weight",
              "29.31 mm against 32.91 mm, but the fit standard error rose from 18.3 to 20&ndash;22 mm",
              "the improvement is inside its own uncertainty, and it is a post-hoc weight choice"],
             ["Estimating differential scale from straight sections",
              "channel-to-channel differences of 0.01&ndash;0.04 %, |z| &le; 0.56; ground truth confirms the true "
              "differential scale in straight driving is 1.0000 &plusmn; 0.00005",
              "the differential scale error that matters appears only inside turns (2.7&ndash;2.9 % against "
              "0.9 % straight), so it cannot be measured where it is absent"],
             ["Estimating and removing per-channel clock offsets against the chassis",
              "offsets of 9.7&ndash;51.3 ms found and corrected; result 33.62 mm against 32.91 mm",
              "segment integration and boundary interpolation already absorb offsets of this size, consistent with "
              "the injected-offset sweep showing +0.1 mm at 33 ms"],
             ["Adding more turn segments by relaxing the turn threshold",
              "5 to 10 segments moved A2D2-style pooling within its standard error; on one backend it got worse",
              "weak segments add samples and noise in the same proportion"],
         ],
         "cap": "Five attempts to reduce the residual lateral error that did not survive their own uncertainty."},
        {"t": "note", "kind": "key",
         "text": "Taken together with the ground-truth-trajectory control, these say the same thing from five "
                 "directions: the residual is differential odometry error integrated inside the turn windows. It "
                 "is reduced by better motion input or more windows, and by nothing inside the estimator."},
    ],
    "seealso": [
        ("results.html", "Results &amp; metric", "the headline numbers these ablations perturb"),
        ("odometry.html", "Odometry front end results", "where the residual error comes from"),
        ("parameters.html", "Parameter reference", "which parameters these experiments varied"),
    ],
}


PAGES = [INVENTORY, SEGMENTS, ODOMETRY, ABLATIONS]
