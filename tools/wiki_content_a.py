# -*- coding: utf-8 -*-
"""Stage 1 algorithm pages (A1-A5)."""

# ------------------------------------------------------------------ A1
M1 = {
    "slug": "m1-turn-segments",
    "title": "A1 &middot; Turn-segment extraction",
    "crumbs": "Algorithm wiki &rsaquo; Stage 1 &rsaquo; A1",
    "tagline": "Every later estimator consumes the same list of turning segments. "
               "A1 smooths each sensor twist, then cuts it into direction-consistent turns "
               "that carry enough rotational information to be worth estimating from.",
    "desc": "How NH-Calib detects turning segments from per-sensor angular rate.",
    "infobox": [
        ("Stage", "1 &mdash; per sensor, no association"),
        ("Input", "Raw twist <span class='sym'>&xi;</span><sub>j</sub>(t) = [v<sup>&#8868;</sup>, &omega;<sup>&#8868;</sup>]<sup>&#8868;</sup>; optional platform speed v<sub>c</sub>"),
        ("Output", "Ordered segment list with start/end time, net heading W<sub>k</sub>, duration T<sub>k</sub>, sign, peak rate"),
        ("Consumed by", "A2, A4, B1, B2"),
        ("Runs before", "Roll/pitch levelling &mdash; detection is yaw-centric and pre-level"),
        ("Failure", "Zero accepted segments &rarr; channel dropped at stage <code>turn</code>"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "why", "no": 1, "text": "Why segments at all"},
        {"t": "p", "text": "NH-Calib never uses the whole drive. Straight driving carries almost no "
                           "information about mounting angles or lever arms: the rotation axis is undefined when "
                           "<span class='sym'>&omega;</span> &asymp; 0, and the lateral lever-arm term "
                           "<span class='sym'>&omega;p<sub>x</sub></span> vanishes with it. Every NH-Calib observation "
                           "equation is proportional to rotation, so the estimator is restricted to intervals that "
                           "actually rotate."},
        {"t": "p", "text": "Using a <em>shared</em> segment list also keeps the modules comparable. A2 fits a rotation "
                           "axis, A4 fits a lateral residual and B2 integrates forward displacement &mdash; if each "
                           "re-detected its own intervals, a disagreement between modules could not be traced to a "
                           "single cause. Segments are detected once, in A1, and injected downstream."},
        {"t": "note", "kind": "key",
         "text": "Segments are detected <strong>before</strong> roll/pitch levelling. Detection therefore cannot "
                 "depend on the attitude estimate that A2 has not produced yet. This is safe under the planar "
                 "assumption: a significant rotation episode on a road vehicle is a yaw turn, so a yaw-centric "
                 "scalar is a sufficient detector even in an unlevelled sensor frame."},

        {"t": "h", "level": 2, "id": "smooth", "no": 2, "text": "Step 1 &mdash; centred twist smoothing"},
        {"t": "p", "text": "Scan-matching odometry produces trajectories that look clean at the second scale but "
                           "whose frame-to-frame twist oscillates with period two. A4 and B2 read the twist directly, "
                           "so that oscillation would be absorbed into the lever arms. A1 therefore smooths the twist "
                           "before anything else touches it."},
        {"t": "eq", "text": "N<sub>w</sub> = odd_round( <span class='sym'>&tau;</span><sub>smooth</sub> / median(&Delta;t) ),"
                            "&nbsp;&nbsp; N<sub>w</sub> &ge; 1,&nbsp;&nbsp; half = (N<sub>w</sub> &minus; 1) / 2",
         "cap": "The smoothing window is specified as a time constant and converted to an odd sample count per "
                "dataset. At 30&nbsp;Hz a 1.0&nbsp;s constant gives 31 samples; at 10&nbsp;Hz it gives 11. "
                "N<sub>w</sub> = 1 is the identity."},
        {"t": "note", "kind": "warn", "label": "Causal filters are prohibited",
         "text": "A trailing (causal) average delays yaw rate relative to lateral velocity. The relative-Y regression "
                 "then reads that phase lag as a lever arm of the wrong sign. Only centred windows are allowed: the "
                 "window <code>[i&minus;h, i+h]</code> is symmetric, and shrinks symmetrically at the sequence ends."},
        {"t": "table", "cls": "num",
         "head": ["Mode", "What it does", "Role"],
         "rows": [
             ["<code>pose-sg</code>",
              "Integrate twist to poses; fit a polynomial to world-frame position and a tangent-space polynomial to "
              "rotation inside the window; re-differentiate.",
              "Default for LiDAR"],
             ["<code>pose-ma</code>", "Same pose-domain construction with a plain mean (polynomial order 0).", "Variant"],
             ["<code>twist-ma</code>", "Window-average the six twist components directly.", "Control"],
             ["<code>central</code>", "No averaging; central difference between the poses at the window ends.", "Frozen experiment setting"],
             ["<code>none</code>", "Identity, bit-for-bit.", "Radar / CAN-rate channels"],
         ],
         "cap": "All modes are centred. Constant and linear ramps pass through with zero phase shift, which is the "
                "property the lever-arm estimators depend on."},
        {"t": "ul", "items": [
            "Smoothing is applied to <code>vx, vy, vz, wx, wy, wz</code> only. Timestamps, <code>dt</code> and "
            "front-end quality fields are passed through unchanged.",
            "Dropped-scan gaps split the stream into contiguous blocks; integration and smoothing never cross a gap.",
            "Platform speed from chassis/CAN is not smoothed here &mdash; it is already a filtered vehicle signal.",
            "No additional low-pass filtering is permitted elsewhere in the pipeline. Smoothing exists once, in A1.",
        ]},

        {"t": "h", "level": 2, "id": "detect", "no": 3, "text": "Step 2 &mdash; turn detection"},
        {"t": "fig", "src": "figs/turn-anatomy.png",
         "alt": "Yaw rate and integrated heading for one accepted turn in two datasets",
         "cap": "One accepted segment per dataset, with the three conditions drawn onto the signal. A segment opens only if the peak clears the 15&nbsp;deg/s trigger, stays open while the rate holds above the 5&nbsp;deg/s edge, and is accepted only if the integrated heading reaches 30&nbsp;deg. Left: a truck recording, peak 19.4&nbsp;deg/s, 188&nbsp;deg net over 12.8&nbsp;s. Right: A2D2, peak 20.1&nbsp;deg/s, 949&nbsp;deg net over 55.8&nbsp;s &mdash; a long roundabout that the hold level keeps as one segment instead of shattering into several."},
        {"t": "p", "text": "Detection runs on a single signed scalar per channel, the yaw-centric turn rate."},
        {"t": "eq", "text": "&omega;<sub>turn</sub>(t) = &#8214;<span class='sym'>&omega;</span>(t)&#8214; &middot; sign( &omega;<sub>z</sub>(t) )",
         "cap": "Default <code>norm</code> mode: magnitude from the full three-dimensional angular velocity, sign from "
                "its vertical component. A <code>wz</code> mode using the signed vertical component alone is available, "
                "and is used automatically for planar streams that carry no wx/wy."},
        {"t": "steps", "items": [
            ["Two-level hysteresis",
             "A candidate opens when |&omega;<sub>turn</sub>| crosses the <em>peak</em> threshold and stays open while "
             "it remains above the lower <em>hold</em> threshold. One threshold alone either fragments a single turn "
             "into pieces or admits noise crossings."],
            ["Split on discontinuity",
             "A candidate is cut where sample indices are non-contiguous, where sign(&omega;) changes, or where the "
             "sample spacing exceeds the maximum gap. The gap rule is mandatory: without it a whole drive can fuse "
             "into one mega-segment whose integral is meaningless."],
            ["Accept on accumulated rotation",
             "A surviving candidate is kept only if its net heading change |W<sub>k</sub>| reaches the minimum and "
             "the mean platform speed is above the speed floor. Low-speed manoeuvres give poor lever-arm leverage."],
            ["Inspect and exclude",
             "Accepted segments get stable indices so that a human or an automatic quality rule can remove specific "
             "turns without changing the detector. Exclusion is a mask, not a re-detection."],
        ]},
        {"t": "table", "cls": "num",
         "head": ["Gate", "Default", "Purpose"],
         "rows": [
             ["Hold rate", "5&nbsp;deg/s", "Segment entry and exit boundary"],
             ["Peak rate", "15&nbsp;deg/s", "Rejects weak threshold crossings caused by noise"],
             ["Net heading |W<sub>k</sub>|", "30&nbsp;deg", "Guarantees usable regression leverage"],
             ["Mean platform speed", "1.0&nbsp;m/s", "Excludes near-stationary rotation"],
             ["Maximum internal gap", "0.3&nbsp;s", "Mandatory split; prevents mega-segments"],
             ["Minimum duration", "0.8&nbsp;s (design default)",
              "Present in the settings object; the reported configuration does not enforce it as a separate gate, "
              "because the heading and peak gates already remove short crossings."],
         ],
         "cap": "Gate values are per-channel and identical for every sensor in a run."},

        {"t": "fig", "src": "figs/turn-threshold-sweep.png",
         "alt": "Share of driving time retained as turn segments against the peak trigger level",
         "cap": "How much of a drive the definition keeps as the trigger is swept, for three net-rotation requirements. A2D2 holds at 22&ndash;23&nbsp;% and is almost insensitive to the trigger; the truck recording falls from 1.9&nbsp;% to 0.4&nbsp;%. The dashed line marks the 15&nbsp;deg/s default used throughout this wiki."},
        {"t": "h", "level": 2, "id": "out", "no": 4, "text": "Outputs"},
        {"t": "table",
         "head": ["Field", "Meaning"],
         "rows": [
             ["<code>start_s</code>, <code>end_s</code>, <code>T_s</code>", "Segment boundaries and duration"],
             ["<code>W_rad</code>", "Net heading change &int;&omega;&nbsp;dt over the segment"],
             ["<code>I_m</code>", "Forward displacement integrated over the segment"],
             ["<code>peak_rate_rps</code>, <code>sign</code>", "Maximum absolute rate and turn direction"],
             ["<code>n_samples</code>, <code>max_gap_s</code>", "Sample support and worst internal gap"],
             ["<code>smooth_meta</code>", "Mode, window length, polynomial order, per-channel RMS change from smoothing"],
         ]},
        {"t": "note", "kind": "code",
         "text": "Changing any A1 setting &mdash; including the smoothing window alone &mdash; invalidates everything "
                 "downstream, because the detection signal itself changed. The pipeline recomputes from A1 rather than "
                 "patching later modules. Odometry is <em>not</em> regenerated."},
    ],
    "seealso": [
        ("m2-roll-pitch.html", "A2 &middot; Motion-plane alignment", "first consumer of the segment list"),
        ("time-alignment.html", "B1 &middot; Time alignment", "how segments of two sensors are paired"),
        ("parameters.html", "Parameter reference", "all A1 thresholds in one table"),
        ("failure-modes.html", "Gates &amp; failure modes", "what a <code>turn</code> drop means"),
    ],
}

# ------------------------------------------------------------------ A2
M2 = {
    "slug": "m2-roll-pitch",
    "title": "A2 &middot; Motion-plane alignment",
    "crumbs": "Algorithm wiki &rsaquo; Stage 1 &rsaquo; A2",
    "tagline": "A wheeled platform on a locally planar road rotates about one axis: the plane normal. "
               "Whatever direction that axis has in a sensor frame is the sensor's mounting tilt. "
               "A2 recovers it from the sensor's own angular velocity, with no second sensor involved.",
    "desc": "Roll and pitch from the dominant angular-velocity axis under locally planar motion.",
    "infobox": [
        ("Stage", "1 &mdash; per sensor, no association"),
        ("Input", "Angular velocity <span class='sym'>&omega;</span><sup>S</sup><sub>j</sub>(t) inside accepted turns"),
        ("Output", "Axis <strong>a</strong><sub>j</sub>, levelling rotation, roll <span class='sym'>&phi;</span><sub>j</sub>, pitch <span class='sym'>&theta;</span><sub>j</sub>"),
        ("Sample gate", "15&nbsp;deg/s &le; &#8214;&omega;&#8214; &le; 60&nbsp;deg/s, at least 20 samples"),
        ("Ambiguity", "180&deg; branch of the axis &mdash; resolved by <a href='gauge.html'>A3</a>"),
        ("Not observable", "Rotation about the axis itself (that is yaw &rarr; <a href='m3-x-yaw.html'>A4</a>)"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "idea", "no": 1, "text": "The geometric statement"},
        {"t": "p", "text": "Within one calibration segment the platform follows a single local motion plane. Its "
                           "angular velocity is then parallel to that plane's normal at all times; only the magnitude "
                           "changes. Expressed in the frame of a rigidly mounted sensor, this becomes a collinearity "
                           "statement whose direction is fixed by the mounting rotation."},
        {"t": "eq", "tag": "A2.1",
         "text": "<span class='sym'>&omega;</span><sup>S</sup><sub>j</sub>(t) &nbsp;&#8771;&nbsp; "
                 "&omega;(t) &middot; <strong>a</strong><sub>j</sub>, &nbsp;&nbsp;&nbsp; "
                 "<strong>a</strong><sub>j</sub> = R<sub>j</sub><sup>&#8868;</sup> <strong>e</strong><sub>z</sub>",
         "cap": "&omega;(t) is the shared scalar turn rate of the platform; <strong>a</strong><sub>j</sub> is the "
                "motion-plane normal written in sensor j's frame. Estimating a direction, not a rate, is what makes "
                "this step insensitive to inter-sensor timing."},
        {"t": "note", "kind": "key",
         "text": "Because (A2.1) involves only sensor j's own angular velocity, roll and pitch need no field-of-view "
                 "overlap, no common modality and no clock alignment with any other sensor. This is the first of the "
                 "four degrees of freedom that NH-Calib estimates without association."},

        {"t": "h", "level": 2, "id": "proc", "no": 2, "text": "Procedure"},
        {"t": "fig", "src": "figs/rollpitch-axis-align.png",
         "alt": "Three-panel schematic of sign alignment, weighted axis summation and Rodrigues levelling",
         "cap": "The three steps in one picture: (a) only samples inside accepted turns, with a rate between 15 and 60&nbsp;deg/s, are kept; (b) each sample is sign-aligned against the strongest sample and combined into a single axis by a norm-weighted sum; (c) a Rodrigues rotation about r = a &times; e<sub>z</sub> brings that axis onto +z, and the ZYX Euler read-out of that rotation is the reported Roll and Pitch. Drawn with illustrative values &mdash; it is a schematic of the procedure, not a measurement."},
        {"t": "steps", "items": [
            ["Select informative samples",
             "Keep samples inside accepted turns whose angular-rate magnitude lies between the lower information "
             "bound and the upper sanity bound. Below the lower bound the direction is noise; above the upper bound "
             "the sample is more likely an odometry failure than a real manoeuvre."],
            ["Align sample signs",
             "The measured vectors point along &plusmn;<strong>a</strong><sub>j</sub> depending on turn direction. "
             "They are sign-aligned against the strongest sample so that left and right turns reinforce rather than "
             "cancel each other."],
            ["Form the representative axis",
             "Sum the aligned unit directions weighted by their magnitudes and normalize. Fast rotation carries more "
             "directional information than slow rotation, so magnitude weighting is the natural estimator here. "
             "Trimming is disabled by default; the sample gate already removes the dangerous tails."],
            ["Fix the branch",
             "The magnitude-weighted axis is defined only up to a 180&deg; flip. The branch consistent with a coarse "
             "initial mounting orientation is selected; the systematic treatment is in A3."],
            ["Level",
             "Build the minimum Rodrigues rotation taking <strong>a</strong><sub>j</sub> to the vertical axis "
             "<strong>e</strong><sub>z</sub>. Its first two ZYX Euler angles are the reported roll and pitch."],
        ]},
        {"t": "eq", "tag": "A2.2",
         "text": "<strong>a</strong><sub>j</sub> = normalize( &sum;<sub>k</sub> &#8214;<span class='sym'>&omega;</span><sub>k</sub>&#8214; &middot; s<sub>k</sub> <span class='sym'>&omega;&#770;</span><sub>k</sub> ), "
                 "&nbsp;&nbsp; s<sub>k</sub> = sign( <span class='sym'>&omega;&#770;</span><sub>k</sub> &middot; <span class='sym'>&omega;&#770;</span><sub>max</sub> )",
         "cap": "Sign-aligned, magnitude-weighted direction average. This is the degenerate single-vector case of the "
                "classical attitude-from-vector-observations problem; it is used here as one component of the "
                "degree-of-freedom decomposition, not as a new axis-alignment algorithm."},
        {"t": "eq", "tag": "A2.3",
         "text": "L<sub>j</sub> = Rodrigues( <strong>a</strong><sub>j</sub> &rarr; <strong>e</strong><sub>z</sub> ), "
                 "&nbsp;&nbsp; (<span class='sym'>&phi;</span><sub>j</sub>, <span class='sym'>&theta;</span><sub>j</sub>) = ZYX<sub>1,2</sub>( L<sub>j</sub> )",
         "cap": "The levelled twist <span class='sym'>&#7797;</span> = L<sub>j</sub><span class='sym'>&xi;</span><sub>j</sub> "
                "is the common two-dimensional input consumed by A4 and B2."},

        {"t": "h", "level": 2, "id": "why-relative", "no": 3, "text": "Why the reported roll and pitch are relative"},
        {"t": "p", "text": "The recovered axis is the normal of whatever plane the platform actually travelled on, "
                           "not of an ideal horizontal plane. Road cross-slope, grade and static suspension attitude all "
                           "enter every sensor's estimate identically, because all sensors ride the same body."},
        {"t": "p", "text": "That shared component is exactly what reference-relative composition removes. Comparing "
                           "sensor j against reference r through rotation-matrix composition cancels the common plane "
                           "term to first order and leaves the genuine difference in mounting tilt, which is the "
                           "quantity a calibration ground truth can be compared against."},
        {"t": "note", "kind": "warn",
         "text": "Persistent non-planarity &mdash; sustained banking, heave or strong suspension motion &mdash; breaks "
                 "the single-plane premise inside a segment rather than adding a constant offset. It is a model "
                 "boundary, not a noise term, and it biases the estimate."},

        {"t": "h", "level": 2, "id": "out", "no": 4, "text": "Outputs and diagnostics"},
        {"t": "table",
         "head": ["Field", "Meaning"],
         "rows": [
             ["<code>roll_deg</code>, <code>pitch_deg</code>", "Estimated mounting tilt of this sensor"],
             ["<code>axis_vector</code>", "Unit axis <strong>a</strong><sub>j</sub> in the raw sensor frame"],
             ["<code>level_matrix</code>", "Rotation taking <strong>a</strong><sub>j</sub> to +z"],
             ["viz arrays", "Per-segment rotation vectors and the fitted representative axis, for overlay plots"],
         ]},
        {"t": "ul", "items": [
            "Fewer than 20 gated samples &rarr; the channel is dropped at stage <code>axis</code>; nothing downstream "
            "runs for it.",
            "Planar streams that carry no wx/wy at all bypass this module entirely with roll = pitch = 0 and an "
            "identity levelling matrix &mdash; see the caveat in <a href='gauge.html'>A3</a>.",
            "Diagnostic plots: angular-velocity samples on the unit sphere with the fitted axis; before/after sign "
            "alignment; levelled versus raw angular-velocity trajectories.",
        ]},
    ],
    "seealso": [
        ("gauge.html", "A3 &middot; Rotation-sign gauge", "resolving the 180&deg; branch"),
        ("m3-x-yaw.html", "A4 &middot; X, Yaw and slip", "consumes the levelled twist"),
        ("observability.html", "Observability decomposition", "where roll and pitch sit among the six degrees of freedom"),
    ],
}

# ------------------------------------------------------------------ A3
GAUGE = {
    "slug": "gauge",
    "title": "A3 &middot; Rotation-sign gauge",
    "crumbs": "Algorithm wiki &rsaquo; Stage 1 &rsaquo; A3",
    "tagline": "A rotation axis has no intrinsic direction. Every sensor therefore carries one sign bit that the "
               "motion constraint alone cannot fix. A3 separates the bits that data <em>can</em> decide from the one "
               "bit that must be declared.",
    "desc": "Sign ambiguity of the estimated rotation axis, and how NH-Calib resolves it.",
    "infobox": [
        ("Stage", "1 &mdash; between A2 and A4"),
        ("Problem", "180&deg; flip of <strong>a</strong><sub>j</sub>, i.e. a <span class='sym'>Rot<sub>x</sub></span>(&pi;) gauge"),
        ("Total freedom", "2<sup>N</sup> for N sensors"),
        ("Observable", "N &minus; 1 relative bits"),
        ("Not observable", "1 global bit &mdash; fixed by convention"),
        ("Effect on results", "Relative extrinsics are invariant to the global bit"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "problem", "no": 1, "text": "Where the ambiguity comes from"},
        {"t": "p", "text": "A2 estimates the direction along which all angular-velocity samples lie. Both "
                           "<strong>a</strong> and &minus;<strong>a</strong> describe the same line, and under planar "
                           "motion both are consistent with every observation: flipping the axis flips the sign of the "
                           "scalar rate, and the product is unchanged. Formally, post-multiplying a sensor rotation by "
                           "<span class='sym'>Rot<sub>x</sub></span>(&pi;) = diag(1, &minus;1, &minus;1) leaves the "
                           "planar residuals untouched."},
        {"t": "p", "text": "A sensor that is physically mounted upside down and a sensor that is upright therefore look "
                           "identical to the plane-fitting step unless something external tells them apart. With N "
                           "sensors the ambiguity has 2<sup>N</sup> branches, one independent bit per sensor."},
        {"t": "eq", "tag": "A3.1",
         "text": "2<sup>N</sup> &nbsp;=&nbsp; (N &minus; 1) relative bits &nbsp;&times;&nbsp; 1 global bit",
         "cap": "The decomposition that makes the problem tractable: relative bits are decidable from data; the global "
                "bit is not."},

        {"t": "h", "level": 2, "id": "g1", "no": 2, "text": "Convention G1 &mdash; the global bit is declared"},
        {"t": "note", "kind": "gauge", "label": "Convention, not an estimate",
         "text": "One reference channel is designated as the gauge anchor and <strong>declared</strong> to be mounted "
                 "upright, i.e. |roll<sub>ref</sub>| &lt; 90&deg;. No other sensor is allowed to decide its sign "
                 "independently. This statement cannot be verified or falsified from the motion data; it names the "
                 "output frame rather than measuring it."},
        {"t": "ul", "items": [
            "The correct name for the output frame is &ldquo;the body frame defined by assuming the reference sensor "
            "is upright&rdquo;. It is not claimed to be the physical z-up body frame.",
            "If the reference sensor is in fact mounted rolled by 180&deg;, then p<sub>y</sub>, p<sub>z</sub>, "
            "<span class='sym'>&psi;</span> and &omega;<sub>z</sub> of <em>all</em> sensors flip together. One bit per "
            "dataset, recoverable afterwards.",
            "A single external cue settles it if absolute values must be reported: chassis yaw-rate sign, IMU gravity "
            "direction, ground-plane normal, or a deployed transform tree.",
            "Relative extrinsics &mdash; the quantities NH-Calib reports &mdash; are invariant to this bit, so the "
            "main results are unaffected.",
        ]},

        {"t": "h", "level": 2, "id": "g2", "no": 3, "text": "Convention G2 &mdash; relative bits are measured"},
        {"t": "p", "text": "The remaining N &minus; 1 bits are decidable, because the sensors are rigidly attached to "
                           "one body: after rotating each sensor's angular velocity into the body frame, all "
                           "reconstructions must agree. A flipped sensor reconstructs a waveform of opposite sign, "
                           "which no rotation can hide."},
        {"t": "eq", "tag": "A3.2",
         "text": "min<sub>{R<sub>s</sub>}, {<span class='sym'>&omega;</span><sub>b</sub>(t)}</sub> &nbsp; "
                 "&sum;<sub>s</sub> &sum;<sub>t</sub> w<sub>s</sub>(t) &#8214; R<sub>s</sub><span class='sym'>&omega;</span><sup>s</sup>(t) "
                 "&minus; <span class='sym'>&omega;</span><sub>b</sub>(t) &#8214;<sup>2</sup>",
         "cap": "Joint rotation averaging with a shared body angular velocity as an unknown, anchored at "
                "R<sub>ref</sub> = I. This is the rotational half of a hand&ndash;eye problem, solved by block "
                "coordinate descent: a weighted Procrustes update per sensor, then a weighted mean for the shared "
                "waveform."},
        {"t": "ul", "items": [
            "The residual itself is invariant to the flip, but the <em>reconstructed vector</em> is not &mdash; that is "
            "precisely what the shared unknown exposes.",
            "It works under purely planar motion as well, thanks to the shared scalar waveform. Extracting a principal "
            "axis per sensor in isolation would leave the ambiguity intact, so joint estimation is required.",
            "The decision statistic is an <strong>uncentred</strong> cosine similarity. Drives dominated by one turn "
            "direction have a non-zero mean yaw rate, and mean removal would delete the very sign information being "
            "tested.",
            "Below a minimum absolute correlation (default 0.2) the decision is withheld: the relative bit is reported "
            "as assumed rather than measured. Sensors are never flipped silently.",
            "A sensor whose angular rate exceeds the sanity bound on more than half its samples is excluded from the "
            "shared average but still receives its own verdict, so a diverged channel cannot corrupt the reference.",
            "G2 decides roll, pitch and the sign only. Rotation about the axis itself &mdash; yaw &mdash; remains "
            "undetermined at this point and is A4's job.",
        ]},

        {"t": "h", "level": 2, "id": "signature", "no": 4, "text": "Asynchronous signature check"},
        {"t": "p", "text": "A lightweight variant is available when even coarse time alignment between two sensors is "
                           "unavailable. Each sensor writes one ordered signature vector over the drive: +1 for a turn "
                           "about its local positive z-axis, &minus;1 for the opposite direction, 0 where no turn was "
                           "detected."},
        {"t": "eq", "tag": "A3.3",
         "text": "<strong>s</strong><sub>i</sub> &middot; <strong>s</strong><sub>j</sub> &gt; 0 &nbsp;&rArr;&nbsp; same branch"
                 "&nbsp;&nbsp;&nbsp;&nbsp; <strong>s</strong><sub>i</sub> &middot; <strong>s</strong><sub>j</sub> &lt; 0 &nbsp;&rArr;&nbsp; opposite branches",
         "cap": "Only the order of turns has to be matched, not their sample times. The check is therefore "
                "synchronization-free and leaves one global sign as the sole convention."},

        {"t": "h", "level": 2, "id": "planar", "no": 5, "text": "The planar-stream trap"},
        {"t": "note", "kind": "warn",
         "text": "Channels whose wx and wy are exactly zero &mdash; typical of two-dimensional radar odometry &mdash; "
                 "are routed through a planar branch that forces an identity levelling matrix. In that branch the "
                 "sign-decision step is never reached, so an upside-down channel keeps its wrong sign silently. The "
                 "joint formulation of section 3 covers these channels because it does not distinguish sensor type; "
                 "the per-sensor scalar rule does not."},
        {"t": "p", "text": "A related sharp edge: planarity is detected by an exact numerical closeness test, so a "
                           "channel with angular noise at the 10<sup>&minus;4</sup>&nbsp;rad/s level can take a "
                           "different code path from an otherwise identical channel. A physically meaningful threshold "
                           "is the appropriate fix and is tracked separately."},

        {"t": "h", "level": 2, "id": "report", "no": 6, "text": "What is reported"},
        {"t": "table",
         "head": ["Field", "Meaning"],
         "rows": [
             ["<code>gauge.anchor_channel</code>", "Which channel was declared upright"],
             ["<code>gauge.rule</code>", "Always <code>ref_upright</code> for G1"],
             ["<code>gauge.global_bit_observable</code>", "Constant <code>false</code> &mdash; states plainly that this is a convention"],
             ["<code>rel_flip</code> (per sensor)", "+1 or &minus;1 relative to the anchor"],
             ["<code>rel_flip_source</code>", "<code>omega_align</code>, <code>orient_can</code> or <code>assumed</code>"],
             ["<code>omega_corr</code>", "The correlation value the decision was based on"],
         ],
         "cap": "Any table of absolute extrinsics must carry the gauge caption naming the anchor and the rule."},
    ],
    "seealso": [
        ("m2-roll-pitch.html", "A2 &middot; Motion-plane alignment", "produces the axis whose sign is at stake"),
        ("observability.html", "Observability decomposition", "the full list of what is and is not observable"),
        ("failure-modes.html", "Gates &amp; failure modes", "withheld decisions and excluded channels"),
    ],
}

# ------------------------------------------------------------------ A4
M3 = {
    "slug": "m3-x-yaw",
    "title": "A4 &middot; X, Yaw and slip",
    "crumbs": "Algorithm wiki &rsaquo; Stage 1 &rsaquo; A4",
    "tagline": "The non-holonomic constraint says the rear-axle centre has no lateral velocity. Any lateral velocity "
               "a sensor measures during a turn is therefore its own longitudinal lever arm &mdash; which makes X and "
               "Yaw solvable from that sensor alone.",
    "desc": "Per-sensor yaw and longitudinal lever arm from the lateral non-holonomic residual.",
    "infobox": [
        ("Stage", "1 &mdash; per sensor, no association"),
        ("Input", "Levelled two-dimensional twist; platform forward speed v<sub>c</sub>; yaw rate"),
        ("Estimates", "<span class='sym'>&psi;</span><sub>j</sub>, p<sub>x,j</sub> per sensor; one shared c"),
        ("Solver", "Huber-weighted IRLS Gauss&ndash;Newton"),
        ("Sample gate", "At least 50 samples per channel after the planar gate"),
        ("Caveat", "c is a nuisance parameter, not a vehicle property"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "idea", "no": 1, "text": "The constraint that does the work"},
        {"t": "p", "text": "A wheeled platform cannot slide sideways at the rear-axle centre. Under the nominal "
                           "non-holonomic constraint v<sub>c,y</sub> = 0, and the lateral velocity seen at a sensor "
                           "origin during a turn is produced entirely by the sensor's longitudinal offset."},
        {"t": "eq", "tag": "A4.1",
         "text": "v<sub>j,y</sub> = v<sub>c,y</sub> + &omega; p<sub>x,j</sub> &nbsp;&nbsp;&xrarr;&nbsp;&nbsp; "
                 "v<sub>j,y</sub> = &omega; p<sub>x,j</sub>&nbsp;&nbsp;(nominal NHC)",
         "cap": "No reference to any other sensor appears. This is why X and yaw belong to the association-free group."},
        {"t": "p", "text": "The sensor's own measurement is expressed in its own frame, so the unknown mounting yaw "
                           "<span class='sym'>&psi;</span><sub>j</sub> appears as the rotation that brings that "
                           "measurement onto the platform's lateral axis. Yaw and X are therefore estimated jointly "
                           "from the same residual."},

        {"t": "h", "level": 2, "id": "slip", "no": 2, "text": "Relaxing the constraint for tire sideslip"},
        {"t": "p", "text": "Perfect no-slip does not hold in real driving. Lateral tire slip grows with lateral "
                           "acceleration, so the rear-axle lateral velocity is approximated by a speed-and-rate "
                           "dependent term with a single shared coefficient."},
        {"t": "eq", "tag": "A4.2",
         "text": "v<sub>c,y</sub> &asymp; &minus; c v<sub>c</sub><sup>2</sup> &omega;",
         "cap": "One coefficient c is shared by all sensors, because it describes the platform rather than any "
                "individual mounting. Setting c = 0 recovers the classical non-holonomic constraint exactly."},
        {"t": "note", "kind": "warn", "label": "c absorbs odometry bias",
         "text": "Empirically the fitted c changes sign with the odometry front end and with the voxel size used by "
                 "it. It is therefore treated as a nuisance parameter that absorbs a common odometry bias, not as a "
                 "physical vehicle characteristic. Its main victim is <em>absolute</em> X; relative X is protected "
                 "because the bias is common-mode. Physical interpretation of c is not claimed."},

        {"t": "h", "level": 2, "id": "residual", "no": 3, "text": "Residual and unknowns"},
        {"t": "eq", "tag": "A4.3",
         "text": "r<sub>j,k</sub> = sin<span class='sym'>&psi;</span><sub>j</sub> &#7797;<sub>x,j,k</sub> "
                 "+ cos<span class='sym'>&psi;</span><sub>j</sub> &#7797;<sub>y,j,k</sub> "
                 "&minus; &omega;<sub>j,k</sub> p<sub>x,j</sub> "
                 "+ v<sub>c,j,k</sub> tan( c v<sub>c,j,k</sub> &omega;<sub>j,k</sub> )",
         "cap": "Per-sample lateral residual for sensor j. The first two terms rotate the levelled sensor velocity "
                "into platform axes, the third is the lever-arm term, the fourth is the slip correction."},
        {"t": "eq", "tag": "A4.4",
         "text": "<span class='sym'>&theta;</span> = [ <span class='sym'>&psi;</span><sub>1</sub>, p<sub>x,1</sub>, &hellip;, "
                 "<span class='sym'>&psi;</span><sub>J</sub>, p<sub>x,J</sub>, c ]<sup>&#8868;</sup>",
         "cap": "Arrow-shaped parameter vector: two parameters per sensor plus one coupling scalar. The normal "
                "equations are block-sparse and the shared coefficient can be eliminated by Schur complement."},
        {"t": "note", "kind": "key",
         "text": "The only cross-sensor coupling in Stage 1 is the shared c through the platform speed channel. "
                 "With c fixed at zero the sensors decouple completely."},

        {"t": "fig", "src": "figs/a2d2-yaw-px-measurements.png",
         "alt": "Scatter plots of the two regressions behind mounting yaw and longitudinal offset on five A2D2 LiDARs",
         "cap": "The samples that actually enter the A4 fit, one column per A2D2 LiDAR. Top: levelled lateral against longitudinal velocity in straight motion, whose direction gives mounting yaw &mdash; from +1.24&deg; on the front-centre unit to &minus;93.00&deg; on the side-right unit. Bottom: yaw-aligned lateral speed against yaw rate inside turns, whose slope is p<sub>x</sub> &mdash; 1.64&ndash;1.65&nbsp;m for the three front units and 0.60&nbsp;m for the two side units. Neither panel involves a second sensor."},
        {"t": "h", "level": 2, "id": "solver", "no": 4, "text": "Robust solver"},
        {"t": "table", "cls": "num",
         "head": ["Setting", "Value", "Role"],
         "rows": [
             ["Initial <span class='sym'>&psi;</span>, p<sub>x</sub>, c", "0, 0&nbsp;m, 0",
              "Reported configuration. A design variant initialises <span class='sym'>&psi;</span> from the median "
              "heading agreement with the platform and p<sub>x</sub> at 1&nbsp;m."],
             ["Robust loss", "Huber, constant 1.345", "Standard 95% efficiency choice for Gaussian cores"],
             ["Residual scale", "max(1.4826 &middot; MAD, 10<sup>&minus;3</sup>&nbsp;m/s)",
              "Data-driven scale with a floor, so a near-perfect fit cannot collapse the weights"],
             ["Weight", "Huber(r / scale) / scale<sup>2</sup>", "IRLS reweighting applied each iteration"],
             ["Step caps", "0.3&nbsp;rad, 1&nbsp;m, 0.004&nbsp;s&sup2;/m", "Prevents divergence from a bad first linearization"],
             ["Iterations", "at most 60", "Convergence when the largest step falls below 10<sup>&minus;11</sup>"],
         ]},
        {"t": "p", "text": "Slip significance is reported as the chi-square improvement of the fitted coefficient over "
                           "the c = 0 model. The core computes the statistic and reports it; it does not apply a pass "
                           "or fail threshold."},

        {"t": "h", "level": 2, "id": "gate", "no": 5, "text": "Sample gate"},
        {"t": "p", "text": "Before fitting, samples pass a planar-excitation gate. Its purpose is to keep only samples "
                           "where the lever-arm term is actually excited and the inputs are mutually valid."},
        {"t": "ul", "items": [
            "Sensor timestamp lies inside the platform-speed time range.",
            "Selected yaw rate magnitude is at least the excitation floor (default 15&nbsp;deg/s).",
            "Platform forward speed magnitude is at least 1.0&nbsp;m/s.",
            "Levelled sensor yaw rate stays below the sanity bound (default 60&nbsp;deg/s).",
            "The sample lies inside an accepted turn segment from A1.",
        ]},
        {"t": "note", "kind": "warn",
         "text": "Fewer than 50 surviving samples drops the channel at stage <code>planar</code>. This is the most "
                 "common drop in practice for sequences with little turning."},

        {"t": "h", "level": 2, "id": "sync", "no": 6, "text": "Timing behaviour"},
        {"t": "p", "text": "When the yaw rate in (A4.3) is the sensor's own, a clock shift applied to any other sensor "
                           "does not change a single input of this estimator. Roll, pitch, yaw and X are then exactly "
                           "invariant to inter-sensor time offsets &mdash; a measured, not merely argued, property."},
        {"t": "note", "kind": "warn", "label": "The substitution that costs this property",
         "text": "If a sensor cannot estimate its own angular rate and a platform yaw-rate signal is substituted, the "
                 "estimator becomes sensitive to the offset between that sensor and the platform clock, and X loses "
                 "its synchronization-free status. The substitution remains useful for sensors that cannot produce "
                 "geometric odometry at all, but it is a documented limitation rather than part of the main claim."},
    ],
    "seealso": [
        ("relativization.html", "A5 &middot; Reference relativization", "what happens to these estimates next"),
        ("sum-form.html", "B2 &middot; Sum-form relative Y", "the same lever arm applied to forward velocity"),
        ("parameters.html", "Parameter reference", "solver constants in one table"),
    ],
}

# ------------------------------------------------------------------ A5
RELATIVIZE = {
    "slug": "relativization",
    "title": "A5 &middot; Reference relativization",
    "crumbs": "Algorithm wiki &rsaquo; Stage 1 &rsaquo; A5",
    "tagline": "All sensors ride the same body over the same segments, so they share the same model error. "
               "Composing every estimate against one reference sensor cancels that shared error to first order &mdash; "
               "and defines the quantity that ground truth can actually score.",
    "desc": "Converting per-sensor absolute estimates into reference-relative extrinsics.",
    "infobox": [
        ("Stage", "1 &mdash; final step"),
        ("Input", "Per-sensor <span class='sym'>&phi;</span>, <span class='sym'>&theta;</span>, <span class='sym'>&psi;</span>, p<sub>x</sub>"),
        ("Output", "Reference-relative X, Yaw, Roll, Pitch"),
        ("Operation", "Transform composition, not Euler-angle subtraction"),
        ("Cancels", "Platform-common bias b<sub>common</sub> to first order"),
        ("Gauge", "Reference sensor is the frame origin; y<sub>r</sub> = 0 in Stage 2"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "why", "no": 1, "text": "Why relativize"},
        {"t": "p", "text": "Each Stage 1 estimate is stated with respect to a platform frame that the data defines "
                           "only implicitly: the motion plane the vehicle happened to travel on, the speed signal the "
                           "dataset happened to publish, the slip coefficient that absorbed whatever bias the odometry "
                           "front end carried. Those are shared inputs, and their errors land on every sensor the same "
                           "way."},
        {"t": "eq", "tag": "A5.1",
         "text": "q&#770;<sub>j</sub> = q<sub>j</sub> + b<sub>common</sub> + <span class='sym'>&epsilon;</span><sub>j</sub> "
                 "&nbsp;&nbsp;&rArr;&nbsp;&nbsp; q&#770;<sub>j</sub> &minus; q&#770;<sub>r</sub> = "
                 "(q<sub>j</sub> &minus; q<sub>r</sub>) + (<span class='sym'>&epsilon;</span><sub>j</sub> &minus; <span class='sym'>&epsilon;</span><sub>r</sub>)",
         "cap": "The shared term disappears; only the genuinely per-sensor part survives. This is the formal reason "
                "relative accuracy is consistently better than absolute accuracy in the reported results."},
        {"t": "note", "kind": "key",
         "text": "This applies to <em>all</em> estimated components, not only lateral offset. Motions that violate the "
                 "platform model &mdash; a road with cross-slope, a speed signal referenced to the wrong point, "
                 "suspension attitude &mdash; act on every sensor at once and are therefore removed by the same "
                 "mechanism. Absolute values can be slightly off while relative values stay accurate."},

        {"t": "h", "level": 2, "id": "how", "no": 2, "text": "How it is computed"},
        {"t": "eq", "tag": "A5.2",
         "text": "T&#770;<sub>rj</sub> = ( T&#770;<sub>Vr</sub> )<sup>&minus;1</sup> T&#770;<sub>Vj</sub>, "
                 "&nbsp;&nbsp;&nbsp; R&#770;<sub>rj</sub> = R&#770;<sub>Vr</sub><sup>&#8868;</sup> R&#770;<sub>Vj</sub>",
         "cap": "Rotations are composed as matrices. Subtracting Euler angles is not equivalent and introduces "
                "order-dependent error once two angles are non-small."},
        {"t": "steps", "items": [
            ["Choose the reference",
             "One channel is designated the reference. It is also the gauge anchor used by A3 and the fixed node of "
             "the Stage 2 graph, so that all three gauge choices coincide."],
            ["Assemble per-sensor poses",
             "Roll and pitch from A2, yaw and longitudinal offset from A4 form each sensor's estimated pose in the "
             "implicit platform frame. Lateral offset is still unknown at this point &mdash; it is Stage 2's output."],
            ["Compose",
             "Apply (A5.2) to every sensor. Rotational parts are extracted from the composed rotation matrix; the "
             "longitudinal component is differenced in the reference frame."],
            ["Report",
             "The output of Stage 1 is reference-relative X, Yaw, Roll and Pitch. Lateral offset joins later to "
             "complete the five-degree-of-freedom result."],
        ]},

        {"t": "h", "level": 2, "id": "limits", "no": 3, "text": "What relativization does not fix"},
        {"t": "ul", "items": [
            "Errors that differ between sensors &mdash; a channel whose odometry tracking degraded, or one with a much "
            "weaker turn sample &mdash; survive by construction. They are the residual "
            "<span class='sym'>&epsilon;</span><sub>j</sub> &minus; <span class='sym'>&epsilon;</span><sub>r</sub>.",
            "A poor reference channel contaminates every pair, since its own error enters all of them with the same "
            "sign. Reference selection is a real design decision, not a labelling convention.",
            "The cancellation is first order. A bias large enough for second-order terms to matter is not removed "
            "cleanly.",
            "Vertical offset is not recovered by relativization. It is unobservable under planar motion for structural "
            "reasons, discussed in the <a href='observability.html'>observability</a> page.",
        ]},
    ],
    "seealso": [
        ("m3-x-yaw.html", "A4 &middot; X, Yaw and slip", "produces the components being composed"),
        ("graph.html", "B3 &middot; Graph integration", "applies the same reference as the fixed node"),
        ("observability.html", "Observability decomposition", "why five degrees of freedom and not six"),
    ],
}

PAGES = [M1, M2, GAUGE, M3, RELATIVIZE]
