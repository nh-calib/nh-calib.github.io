# -*- coding: utf-8 -*-
"""Evaluation pages: datasets / front end, and the reported results.

Every number on these pages is transcribed from the manuscript's experiment
section. Where the manuscript states a condition under which a number is or is
not meaningful, that condition is carried over with it.
"""

# ------------------------------------------------------------- datasets
DATASETS = {
    "slug": "datasets.html",
    "title": "Datasets and front end",
    "crumbs": "NH-Calib &rsaquo; Algorithm wiki &rsaquo; Evaluation",
    "tagline": "What was run on what. Sensor layout, ego-motion front end, time handling, reference channel and "
               "exclusions for each of the three public datasets used in the reported evaluation.",
    "desc": "Dataset layouts, odometry front ends and time handling behind the reported NH-Calib results.",
    "infobox_title": "Evaluation inputs",
    "infobox": [
        ("Datasets", "A2D2, RadarScenes, Ford Multi-AV"),
        ("Vehicle experiments", "None in-house &mdash; public recordings only"),
        ("LiDAR front end", "KISS-ICP pose differentiation"),
        ("Radar front end", "Doppler ego-velocity + CAN yaw rate"),
        ("Ground truth", "Official extrinsics, scoring only"),
        ("Excluded drives", "Ford Log2, Log3"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "why", "no": "1", "text": "Why these three"},
        {"t": "p", "text": "The three datasets were not chosen to be easy. They were chosen because they place the "
                           "method in three different observational regimes, and the method behaves differently in "
                           "each &mdash; which is the part of the evaluation that carries information."},
        {"t": "table",
         "head": ["Dataset", "Layout and motion input", "What it tests"],
         "rows": [
             ["A2D2", "Five LiDARs; lateral channels share almost no structure with the front one. "
                      "LiDAR odometry twist.",
              "The no-overlap regime &mdash; the side sensors cannot be registered against the reference at all."],
             ["RadarScenes", "Four radars; geometric radar odometry unusable. Doppler ego-velocity with CAN yaw "
                             "rate.",
              "The alternative-input regime &mdash; the motion signal is constructed, not sensor-only odometry."],
             ["Ford Multi-AV", "Four 360&deg; LiDARs with broad common structure. LiDAR odometry twist.",
              "The favourable case for registration &mdash; included as the honest comparison point."],
         ],
         "cap": "The Ford layout is the one where a classical overlapping-view method should win. It is included for "
                "that reason."},
        {"t": "note", "kind": "note",
         "text": "A2D2 is real sensor data, not simulation. No in-house vehicle experiment is part of the reported "
                 "results."},

        {"t": "h", "level": 2, "id": "motion", "no": "2", "text": "Ego-motion input per dataset"},
        {"t": "p", "text": "NH-Calib consumes a metric twist, not points. What produces that twist differs by "
                           "dataset, and the difference matters when reading the results table."},
        {"t": "steps", "items": [
            ("A2D2 and Ford &mdash; LiDAR odometry only",
             "Continuous poses are estimated with KISS-ICP and differentiated to give linear and angular velocity. "
             "No external signal enters the estimate."),
            ("RadarScenes &mdash; Doppler plus CAN",
             "Geometric radar odometry was not reliable enough in the tested configuration, so Doppler ego-velocity "
             "is combined with a temporally aligned CAN yaw rate. This is an alternative input path, and the "
             "manuscript reports it as such rather than as a sensor-only five-degree-of-freedom result."),
            ("Sign gauge is never taken from CAN",
             "In every dataset the rotation-axis sign is a gauge convention anchored to the chosen reference sensor. "
             "See <a href='gauge.html'>A3 &middot; Rotation-sign gauge</a>."),
        ]},
        {"t": "note", "kind": "warn",
         "text": "Because the RadarScenes twist depends on an external CAN signal, alignment error against that "
                 "signal propagates into X. The usability and the independence limits of that path are reported "
                 "together; it is not interchangeable with the LiDAR-only results."},

        {"t": "fig", "src": "figs/rs-doppler-frontend.jpg",
         "alt": "Doppler ego-velocity against vehicle speed, agreement scatter, sensor-frame lateral velocity and yaw-rate input",
         "cap": "The radar motion front end. (a) Doppler ego-velocity magnitude tracks the vehicle speed across a sequence. (b) Against the speed predicted at each mount point, the RMSE is 0.14&ndash;1.19&nbsp;m/s. (c) The sensor-frame lateral component is large for the side-looking units by construction &mdash; that component is the signal A4 uses. (d) Rotation is not observable from one 120&deg; sector, so the yaw rate comes from the vehicle bus; the shaded band is what the turn gate rejects."},
        {"t": "h", "level": 2, "id": "frontend", "no": "3", "text": "Front-end settings"},
        {"t": "table",
         "head": ["Setting", "A2D2", "Ford Multi-AV", "RadarScenes"],
         "rows": [
             ["Odometry", "KISS-ICP", "KISS-ICP 1.2.3", "&mdash; (Doppler + CAN)"],
             ["Registration voxel", "0.20 m", "0.30 m", "&mdash;"],
             ["Range window", "5&ndash;80 m", "2&ndash;80 m", "&mdash;"],
             ["Ego-body filter", "off", "off", "&mdash;"],
             ["Deskew", "none", "explicit point-time deskew; KISS internal deskew disabled", "&mdash;"],
             ["Frame interval", "fixed 30 Hz", "actual scan time differences per Log", "sample timestamps"],
             ["Reference sensor", "FRONT_CENTER", "RED", "RADAR_1"],
             ["Scored targets", "4", "3 per Log", "3"],
         ],
         "cap": "Front-end configuration for the reported runs. The two LiDAR datasets differ in voxel size, range "
                "and deskew handling; neither was tuned per sensor channel."},
        {"t": "note", "kind": "key",
         "text": "The A2D2 fixed 30 Hz interval is not a convenience approximation. The stored intervals contain an "
                 "alternating error, so both the time axis and the velocity reconstructed from pose increments are "
                 "corrected consistently. Using the stored intervals directly corrupts every downstream velocity."},

        {"t": "fig", "src": "figs/a2d2-kiss-paths.png",
         "alt": "Five A2D2 LiDAR odometry paths, one panel per sensor, each in its own sensor frame",
         "cap": "What the LiDAR front end produces on A2D2: one path per sensor, each drawn in its own sensor frame, which is why the same drive appears rotated from panel to panel. The calibrator never consumes these poses directly &mdash; it consumes the per-frame twist derived from them. Settings shown in the figure title belong to the voxel-sweep run, not to the reported configuration in the table above."},
        {"t": "h", "level": 2, "id": "radar-loop", "no": "4", "text": "RadarScenes: alternating offset and calibration"},
        {"t": "p", "text": "For RadarScenes the time offset and the calibration are updated alternately for three "
                           "iterations before the final two-dimensional evaluation. Roll and Pitch are not estimation "
                           "targets for this dataset, because the Doppler-plus-CAN input is two-dimensional by "
                           "construction. The final run estimated a slip coefficient of <i>c</i> = 0.0049."},

        {"t": "fig", "src": "figs/rs-sync-convergence.png",
         "alt": "Time offset, mounting yaw, longitudinal and lateral offset errors against iteration index",
         "cap": "The alternation converges in one update. (a) All four offsets move from zero to about &minus;115&nbsp;ms on the first pass and stay there. (b)&ndash;(d) Mounting yaw, longitudinal and lateral offset errors settle at the same point. The residual longitudinal offset of about &minus;0.21&nbsp;m in panel (c) is this particular run's missing slip term, not a synchronisation residual; the slip ablation on the results page shows it closing to 12&nbsp;mm once the term is restored."},
        {"t": "fig", "src": "figs/rs-relative-py-synced.png",
         "alt": "Pairwise forward-velocity difference against yaw rate for all six radar pairs after synchronisation",
         "cap": "The cross-sensor relation on the synchronised radar streams: for each pair, the difference of forward velocities against the yaw rate, whose slope is the relative lateral offset. Per-pair errors run from 5.2 to 31.6&nbsp;mm. No vehicle speed datum enters the slope, which is the same cancellation the LiDAR datasets get from the integrated form."},
        {"t": "fig", "src": "figs/rs-py-accuracy.png",
         "alt": "Absolute and relative lateral offsets against published values, with an error summary",
         "cap": "Accuracy of the radar variant <em>before</em> the alternating offset estimation was introduced: 31&nbsp;mm mean absolute error on the four absolute offsets and 43&nbsp;mm on the six pairs. The synchronised run in the results table reaches 16.5&nbsp;mm relative. Both are scored against the published extrinsics, which the estimator never reads."},
        {"t": "h", "level": 2, "id": "exclusions", "no": "5", "text": "What was excluded, and why it is reported"},
        {"t": "ul", "items": [
            "<strong>Ford Log2 and Log3</strong> did not contain enough valid turn segments and were excluded from "
            "calibration. They are reported as applicability failures rather than silently dropped &mdash; a drive "
            "with too little turning is outside the method's operating regime, and hiding that would misstate the "
            "regime.",
            "<strong>Ford segment acceptance</strong> requires the input angular-rate cosine gate and the normalised "
            "error gate to pass; a drive is rejected when too few valid associated turns survive. See "
            "<a href='failure-modes.html'>Gates and failure modes</a>.",
            "<strong>Ford Log4, Log5 and Log6</strong> use identical timestamp handling and KISS-ICP settings but are "
            "scored as three independent evaluation sets. Neither the minimum across Logs nor a pooled value is "
            "presented as representing Ford as a whole.",
        ]},
        {"t": "note", "kind": "warn",
         "text": "Ford INS and official ground-truth poses may share a positioning source. They are therefore not "
                 "interpreted as an independent motion reference."},

        {"t": "fig", "src": "figs/rs-rejected-motion-source.jpg",
         "alt": "Yaw-rate distribution, mounting errors and conditioning for the rejected radar scan-matching front end",
         "cap": "Why radar scan matching was rejected as the motion source, even though it ran on all 158 sequences. (a) Its turn-gated yaw rate reaches 2458&ndash;2557&nbsp;deg/s where the vehicle bus never exceeds 47&nbsp;deg/s. (b)&ndash;(c) Mounting yaw error up to several degrees and longitudinal error up to 3.7&nbsp;m. (d) The joint fit is conditioned at 1.3&times;10<sup>15</sup> against 7.1 for the adopted Doppler front end. This is a front-end verdict, not a statement about radar in general."},
        {"t": "h", "level": 2, "id": "gt", "no": "6", "text": "Where ground truth is and is not used"},
        {"t": "p", "text": "All main-result cells are ground-truth-free during estimation. Official extrinsics enter "
                           "only at scoring time, through the reference-sensor anchor described on the "
                           "<a href='results.html#metric'>results page</a>. Segment acceptance and graph weights are "
                           "determined without ground truth. The one experiment that does inject ground truth into "
                           "the pipeline &mdash; the attitude oracle &mdash; is labelled separately and is a "
                           "diagnostic, not a result."},
    ],
    "seealso": [
        ("results.html", "Results and metric", "the numbers these settings produced"),
        ("failure-modes.html", "Gates and failure modes", "what rejects a segment, a pair or a whole drive"),
        ("parameters.html", "Parameter reference", "every knob and the ones that actually move the result"),
    ],
}


# -------------------------------------------------------------- results
RESULTS = {
    "slug": "results.html",
    "title": "Results and evaluation metric",
    "crumbs": "NH-Calib &rsaquo; Algorithm wiki &rsaquo; Evaluation",
    "tagline": "The reported reference-relative five-degree-of-freedom errors, the metric that produced them, and the "
               "conditions under which each row is and is not comparable.",
    "desc": "Reference-relative 5-DoF MAE for NH-Calib and baselines on A2D2, RadarScenes and Ford Multi-AV, with the "
            "metric definition and the conditions attached to each row.",
    "infobox_title": "Reported metric",
    "infobox": [
        ("Metric", "Mean absolute error over target sensors"),
        ("Referenced to", "One fixed reference sensor per dataset"),
        ("Units", "Translation mm, rotation deg"),
        ("Direction", "Lower is better"),
        ("Samples per cell", "4 targets (A2D2), 3 (RadarScenes, Ford)"),
        ("Repeated runs", "None &mdash; comparisons are descriptive"),
    ],
    "blocks": [
        {"t": "note", "kind": "warn", "label": "Read this first",
         "text": "Every comparison on this page is descriptive. There are no independent repeated runs, so a smaller "
                 "number is a smaller number on one configuration &mdash; not a claim of statistical superiority. "
                 "Both baselines are our own reproductions, because no compatible official implementation was "
                 "available for every dataset and input format."},

        {"t": "h", "level": 2, "id": "metric", "no": "1", "text": "How the numbers are computed"},
        {"t": "p", "text": "The estimator produces one final calibration per target sensor against one reference "
                           "sensor, so the score is taken on those final sensor states. Averaging all directed pair "
                           "permutations would count the same estimate several times and is not used."},
        {"t": "steps", "items": [
            ("Anchor Stage 1 to the reference pose",
             "The estimated reference-to-target transform is composed with the <em>ground-truth</em> pose of the "
             "reference sensor. This is the only place ground truth enters, and it fixes the common frame so that a "
             "relative estimate can be compared against an absolute table."),
            ("Take X and rotation errors in that frame",
             "The X error is the difference of the longitudinal component. The rotation error is the residual "
             "rotation between estimate and ground truth, read out as ZYX Euler Roll, Pitch and Yaw."),
            ("Take Y from the graph node, not from an edge",
             "Relative Y is scored from the final graph node against the ground-truth lateral difference of the "
             "target and the reference. A single pairwise edge is not scored, because a single edge is not what the "
             "method outputs."),
            ("Average absolute errors over targets",
             "The mean absolute error runs over all sensors except the reference. The reference contributes a "
             "structural zero and is excluded, leaving four targets for A2D2 and three for RadarScenes and Ford."),
        ]},
        {"t": "eq", "tag": "M1",
         "text": "MAE<sub>d</sub> = (1 / (|S| &minus; 1)) &middot; &Sigma;<sub>j &ne; r</sub> |e<sub>d,j</sub>|",
         "cap": "for each degree of freedom d, over target sensors j, with reference r excluded"},
        {"t": "note", "kind": "note",
         "text": "Baselines are scored from their own reference-to-target outputs with the same anchor and the same "
                 "protocol. The NH-Calib graph post-processing is <em>not</em> applied to them &mdash; that would "
                 "hand our smoothing to a competitor's raw output and make the row uninterpretable."},

        {"t": "h", "level": 2, "id": "main", "no": "2", "text": "Reference-relative five-DoF error"},
        {"t": "table", "cls": "num",
         "head": ["Dataset &middot; method", "Targets", "X [mm]", "Y [mm]", "Yaw [&deg;]", "Roll [&deg;]",
                  "Pitch [&deg;]"],
         "rows": [
             ["<strong>A2D2 &middot; NH-Calib</strong>", "4", "<b>8.45</b>", "<b>3.21</b>", "0.072", "0.262", "0.239"],
             ["A2D2 &middot; Hand-eye SE(3)", "4", "41.16", "35.92", "<b>0.070</b>", "0.095", "4.267"],
             ["A2D2 &middot; Registration (ICP)", "3", "1275.12", "622.90", "17.540", "<b>0.085</b>", "<b>0.111</b>"],
             ["<strong>RadarScenes &middot; NH-Calib</strong>", "3", "8.28", "<b>16.48</b>", "<b>0.090</b>",
              "&mdash;", "&mdash;"],
             ["RadarScenes &middot; Hand-eye SE(2)", "3", "<b>7.14</b>", "28.28", "0.093", "&mdash;", "&mdash;"],
             ["RadarScenes &middot; Registration (ICP)", "3", "843.06", "1825.29", "112.229", "&mdash;", "&mdash;"],
             ["<strong>Ford Log4 &middot; NH-Calib</strong>", "3", "42.99", "35.65", "0.195", "0.341", "1.675"],
             ["Ford Log4 &middot; Hand-eye SE(3)", "3", "29.71", "27.62", "<b>0.120</b>", "0.192", "0.426"],
             ["Ford Log4 &middot; Registration (ICP)", "3", "<b>13.60</b>", "<b>9.53</b>", "0.157", "<b>0.089</b>",
              "<b>0.179</b>"],
             ["<strong>Ford Log5 &middot; NH-Calib</strong>", "3", "<b>6.87</b>", "18.07", "<b>0.106</b>", "0.196",
              "0.483"],
             ["Ford Log5 &middot; Hand-eye SE(3)", "3", "20.84", "<b>6.54</b>", "0.109", "<b>0.189</b>",
              "<b>0.162</b>"],
             ["Ford Log5 &middot; Registration (ICP)", "3", "50.62", "40.53", "0.327", "0.193", "0.203"],
             ["<strong>Ford Log6 &middot; NH-Calib</strong>", "3", "35.60", "<b>7.41</b>", "0.144", "0.226", "0.868"],
             ["Ford Log6 &middot; Hand-eye SE(3)", "3", "<b>11.16</b>", "60.28", "<b>0.109</b>", "0.201", "1.035"],
             ["Ford Log6 &middot; Registration (ICP)", "3", "43.66", "15.25", "0.627", "<b>0.148</b>", "<b>0.200</b>"],
         ],
         "cap": "Targets excludes the fixed reference; each target contributes one final calibration. Bold marks the "
                "smallest value within a dataset and degree of freedom. Lower is better."},

        {"t": "h", "level": 3, "text": "Reading the table"},
        {"t": "ul", "items": [
            "<strong>A2D2</strong> &mdash; NH-Calib is smallest in X and Y. The registration row is not comparable: "
            "it covers only three accepted targets instead of four, and its X and Y errors are above one metre.",
            "<strong>RadarScenes</strong> &mdash; NH-Calib is smallest in Y and Yaw; hand-eye SE(2) is smaller in X. "
            "Registration produces 843 mm in X, 1825 mm in Y and 112&deg; in Yaw, which is a complete failure under "
            "the tested condition, not a usable calibration.",
            "<strong>Ford Log4</strong> &mdash; registration is smallest in X, Y, Roll and Pitch; hand-eye gives the "
            "smallest Yaw. This is the expected outcome on four overlapping 360&deg; LiDARs and is reported as such.",
            "<strong>Ford Log5</strong> &mdash; NH-Calib is smallest in X and Yaw; hand-eye in Y, Roll and Pitch.",
            "<strong>Ford Log6</strong> &mdash; NH-Calib is smallest in Y; hand-eye in X and Yaw; registration in "
            "Roll and Pitch.",
        ]},
        {"t": "note", "kind": "key",
         "text": "The pattern, not the minima, is the result: NH-Calib stays within the same order of magnitude as "
                 "overlap-based registration where overlap exists, and remains usable where registration collapses. "
                 "On Ford &mdash; the layout that favours registration &mdash; it does not win, and the manuscript "
                 "says so."},

        {"t": "fig", "src": "figs/ford-sensor-positions.png",
         "alt": "Top view of published and estimated sensor positions on Ford, with residual vectors",
         "cap": "The Ford Log4 result drawn in the vehicle frame: circles are published positions, crosses are the GT-free estimates, and the right panel shows the residual vectors, 2.4&ndash;12.0&nbsp;cm. The common lateral translation is not observable from pairwise relative calibration and is aligned to the published centroid for the picture only; the relative lateral errors are unchanged by that alignment."},
        {"t": "fig", "src": "figs/baseline-pairwise-comparison.png",
         "alt": "Per-pair relative lateral error for the three methods on A2D2, RadarScenes and Ford",
         "cap": "The same three methods resolved per sensor pair. The pattern that the table summarises is visible directly: registration is competitive only where the two sensors truly co-observe, and degrades by two to three orders of magnitude on the A2D2 side pairs and on the opposed radar pairs. Note the protocol difference &mdash; this figure averages over sensor <em>pairs</em>, while the table above scores the final per-sensor states against one reference, so the summary numbers printed here are not the table's numbers."},
        {"t": "h", "level": 2, "id": "overlap", "no": "3", "text": "Why registration wins on Ford and fails elsewhere"},
        {"t": "fig", "src": "figs/localmap-covisibility.jpg",
         "alt": "Bird's-eye local-map pairs coloured by which sensor observed each point",
         "cap": "Two local maps per panel, placed in a common frame with the published extrinsics and coloured by "
                "origin: blue and orange are seen by one sensor only, purple by both. Ford's 360&deg; LiDARs keep "
                "broad common structure, the two A2D2 side units keep almost none, and the opposed radar pair keeps "
                "none at all. The fractions printed inside the panels are the measured co-visibility tabulated on "
                "the <a href=\"data-inventory.html#overlap\">inventory page</a>; the manuscript uses only the "
                "picture."},
        {"t": "p", "text": "This is a qualitative explanation of an input condition, not a numerical overlap metric. "
                           "No overlap number is introduced, because introducing one and then optimising against it "
                           "would make the comparison circular."},

        {"t": "h", "level": 2, "id": "windows", "no": "4", "text": "Sample basis for the Ford relative-Y rows"},
        {"t": "p", "text": "Relative Y is regressed over common turning windows, so the number of accepted windows is "
                           "the effective sample size behind each Y cell."},
        {"t": "table",
         "head": ["Drive", "Common windows used for relative Y", "Status"],
         "rows": [
             ["Ford Log4", "5", "scored"],
             ["Ford Log5", "14", "scored"],
             ["Ford Log6", "8", "scored"],
             ["Ford Log2", "&mdash;", "rejected &mdash; too few valid turn segments"],
             ["Ford Log3", "&mdash;", "rejected &mdash; too few valid turn segments"],
         ],
         "cap": "Five accepted windows on Log4 is a small basis. It is stated rather than pooled away."},

        {"t": "fig", "src": "figs/ford-pair-estimate-vs-gt.png",
         "alt": "Estimated against published relative lateral offset for twelve directed Ford pairs under two front ends",
         "cap": "Every directed Ford Log4 pair against the published value, for the two odometry front ends. The spread around the identity line, not the correlation, is the result: the pairs span &plusmn;1&nbsp;m of true offset, so a high correlation here is trivial and only the residual is informative."},
        {"t": "h", "level": 2, "id": "sync", "no": "5", "text": "Ablation: clock offset"},
        {"t": "p", "text": "A constant offset was injected into the timestamps of one A2D2 channel and the whole "
                           "estimation pipeline was rerun. The experiment separates a change in inter-sensor relative "
                           "time from a change in relative time against the external CAN signal."},
        {"t": "fig", "src": "../assets/fig06_sync_dependency_v1.png",
         "alt": "Relative-Y error against injected clock offset",
         "cap": "Relative-Y sensitivity to an injected clock offset. Rejected common windows are not counted as "
                "low-error successes."},
        {"t": "ul", "items": [
            "Under an inter-sensor-only offset, Roll, Pitch, Yaw and X are numerically unchanged, because their "
            "sample sets are unchanged. This is an implementation sanity check of the structural decomposition "
            "&mdash; not independent empirical evidence for it, and it does not extend to arbitrary jitter.",
            "Against a frame-wise regression serving the same purpose, the common-window sum form gives "
            "<strong>2.9&ndash;5.5&times;</strong> lower relative-Y error at the tested nonzero offsets.",
            "In a separate per-degree-of-freedom hand-eye experiment, Roll, Pitch, Yaw, X and Y all responded to the "
            "offset &mdash; evidence that interval-level correspondence does not by itself decouple the estimated "
            "quantities.",
            "No result showed the sample-wise control to be uniformly more sensitive than hand-eye, so timing "
            "sensitivity is not ranked by correspondence granularity alone.",
        ]},
        {"t": "note", "kind": "note",
         "text": "The sample-wise relative-Y control is the frame-wise counterpart of the sum-form estimator, not a "
                 "separate calibration method, and is therefore not a row in the main table. On A2D2 its all-pair "
                 "relative-Y error is 1785.10 mm, dominated by SIDE_LEFT; that failure is attributed to instantaneous "
                 "odometry inconsistency rather than timing granularity alone. See "
                 "<a href='sum-form.html'>B2 &middot; Sum-form relative Y</a>."},

        {"t": "fig", "src": "figs/sync-granularity.png",
         "alt": "Alignment error against injected clock offset for five estimators, and per-degree-of-freedom response",
         "cap": "(a) Injected clock offset against relative-lateral error for five estimators on A2D2. The sample-wise and interval-wise baselines degrade monotonically; the segment form is lowest until it refuses the pair outright at 763&nbsp;ms, when no common window survives. (b) Peak-to-peak movement of each output over the same offset grid: for hand-eye every one of the six components moves, while four of ours are numerically unmoved."},
        {"t": "h", "level": 2, "id": "oracle", "no": "6", "text": "Ablation: ground-truth attitude injection"},
        {"t": "p", "text": "A small attitude error perturbs a projected velocity through a first-order cross-axis "
                           "term, while the cosine scaling of the intended component is only second order. If Stage-1 "
                           "attitude error were the dominant source of Stage-2 Y error, replacing attitude with "
                           "ground truth should visibly improve Y. Stage 1 was rerun with ground-truth Roll and "
                           "Pitch, and Stage 2 additionally with ground-truth Yaw. All variants reuse the common "
                           "windows detected by the ground-truth-free baseline, so segment reselection cannot explain "
                           "the comparison."},
        {"t": "table", "cls": "num",
         "head": ["Metric", "A2D2", "Ford Log4"],
         "rows": [
             ["Stage-1 X [mm]", "11.138 &rarr; 11.042", "40.984 &rarr; 41.733"],
             ["Stage-1 Yaw [&deg;]", "0.0230 &rarr; 0.0383", "0.3543 &rarr; 0.2798"],
             ["Stage-2 relative Y [mm]", "3.280 &rarr; 3.553", "35.172 &rarr; 36.346"],
         ],
         "cap": "Each entry is baseline &rarr; ground-truth oracle, on fixed windows. RadarScenes is excluded because "
                "its two-dimensional Doppler-plus-CAN input does not define the same experiment."},
        {"t": "note", "kind": "key",
         "text": "There is no consistent improvement &mdash; four of six entries get slightly worse. That rejects "
                 "Stage-1 attitude error as the dominant Stage-2 Y source, which is a negative result and is reported "
                 "as one."},

        {"t": "h", "level": 2, "id": "slip", "no": "7", "text": "Ablation: slip coefficient"},
        {"t": "table", "cls": "num",
         "head": ["Dataset", "Free c &mdash; X [mm]", "Zero c &mdash; X [mm]", "Prior c &mdash; X [mm]",
                  "Relative-Y range [mm]"],
         "rows": [
             ["A2D2", "58.3", "43.2", "230.3", "2.86&ndash;4.81"],
             ["Ford Log4", "57.7", "106.1", "197.8", "32.93&ndash;34.36"],
             ["RadarScenes", "64.8", "219.9", "12.0", "16.39&ndash;16.69"],
         ],
         "cap": "X is absolute mean absolute error; relative Y reports the range across free, zero and prior c. "
                "Lower is better."},
        {"t": "ul", "items": [
            "X moves by a factor of several across the three treatments, and no treatment wins on all datasets "
            "&mdash; zero <i>c</i> is best on A2D2, free <i>c</i> on Ford Log4, prior <i>c</i> on RadarScenes.",
            "Relative Y barely moves in comparison, staying inside the ranges above.",
            "The sweep exposes X&ndash;<i>c</i> confounding directly: the <i>c</i>&ndash;X correlation is "
            "0.40&ndash;0.70 and the normal-matrix condition number is 5.0&times;10<sup>3</sup>&ndash;"
            "2.2&times;10<sup>4</sup>.",
        ]},
        {"t": "note", "kind": "warn",
         "text": "Because of that confounding, <i>c</i> is retained only as a nuisance correction. No claim is made "
                 "that physical slip and the longitudinal offset are separated. Alternative representative-value "
                 "estimators were tried and did not remove the residual, so M-estimation is retained. See "
                 "<a href='m3-x-yaw.html'>A4 &middot; X, Yaw and slip</a>."},

        {"t": "h", "level": 2, "id": "limits", "no": "8", "text": "What these numbers do not establish"},
        {"t": "ul", "items": [
            "<strong>Z is not estimated.</strong> The vertical offset is unobservable under planar motion and does "
            "not appear in any table. A numerical variation of Z in a baseline is not treated as an error of an "
            "observable quantity.",
            "<strong>No statistical claim.</strong> Single configuration, no independent repeated runs, no "
            "confidence intervals. Bold marks a minimum, nothing more.",
            "<strong>Baselines are reproductions.</strong> They diagnose applicability per input condition; they do "
            "not establish a universal ranking of published methods.",
            "<strong>Single-log numbers are single-log numbers.</strong> Ford Log4, Log5 and Log6 disagree with each "
            "other on which method wins which axis. Neither their minimum nor their pooled value represents Ford.",
            "<strong>RadarScenes is an alternative-input result.</strong> Doppler plus CAN is not a sensor-only "
            "five-degree-of-freedom demonstration.",
            "<strong>Open limits</strong> &mdash; planar and lateral-motion violations, <i>c</i>&ndash;X confounding, "
            "front-end bias, and external-input reference and timing error.",
        ]},
    ],
    "seealso": [
        ("datasets.html", "Datasets and front end", "the configuration that produced these numbers"),
        ("observability.html", "Observability decomposition", "why Y is separate and Z is absent"),
        ("failure-modes.html", "Gates and failure modes", "what a rejected drive looks like before it is a number"),
        ("../index.html", "Project page", "abstract and paper figures"),
    ],
}

PAGES = [DATASETS, RESULTS]
