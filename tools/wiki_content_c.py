# -*- coding: utf-8 -*-
"""Overview and reference pages."""

# ------------------------------------------------------------------ index
INDEX = {
    "slug": "index.html",
    "title": "NH-Calib algorithm wiki",
    "crumbs": "NH-Calib &rsaquo; Algorithm wiki",
    "tagline": "A page-per-algorithm reference for the NH-Calib extrinsic calibration pipeline. Each page states what "
               "one module assumes, what it consumes, the equation it solves, how it is solved, what can make it fail, "
               "and what it hands to the next module.",
    "desc": "Index of the NH-Calib algorithm wiki: per-sensor Stage 1 modules and cross-sensor Stage 2 modules.",
    "infobox": [
        ("Problem", "Extrinsic calibration of vehicle-mounted sensors without targets or shared field of view"),
        ("Inputs", "Per-sensor metric twist; optional platform forward speed"),
        ("Outputs", "Reference-relative Roll, Pitch, Yaw, X, Y"),
        ("Not estimated", "Vertical offset p<sub>z</sub> &mdash; unobservable under planar motion"),
        ("Association", "Required for one component only"),
        ("Modules", "Five in Stage 1, three in Stage 2"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "start", "text": "Where to start"},
        {"t": "p", "text": "If you want the single idea behind the method, read "
                           "<a href='observability.html'>Observability decomposition</a> first: it explains why the "
                           "six-degree-of-freedom problem splits into four components each sensor can solve alone, one "
                           "component that needs two sensors, and one that cannot be solved at all from planar motion. "
                           "Every other page is a detailed account of one box in that split."},
        {"t": "cards", "items": [
            {"href": "observability.html", "tag": "Start here", "title": "Observability decomposition",
             "text": "Which degrees of freedom are observable, from what, and at what cost."},
            {"href": "m1-turn-segments.html", "tag": "Entry point", "title": "A1 &middot; Turn-segment extraction",
             "text": "The shared segment list every other module consumes."},
            {"href": "sum-form.html", "tag": "Core mechanism", "title": "B2 &middot; Sum-form relative Y",
             "text": "Why integrating over a turn removes the unknown vehicle speed."},
            {"href": "notation.html", "tag": "Reference", "title": "Notation &amp; frames",
             "text": "Symbols, frames, Euler order and sign conventions used across the wiki."},
            {"href": "results.html", "tag": "Evidence", "title": "Results &amp; metric",
             "text": "What the method scored on three public datasets, and what each number does not claim."},
            {"href": "datasets.html", "tag": "Evidence", "title": "Datasets &amp; front end",
             "text": "Sensor layouts, odometry settings, time handling and excluded drives."},
            {"href": "ablations.html", "tag": "Behind the paper", "title": "Ablation catalogue",
             "text": "Every controlled experiment, including the ones that changed nothing."},
            {"href": "odometry.html", "tag": "Behind the paper", "title": "Odometry front end results",
             "text": "Per-channel tracking quality, deskew, voxel collapse and timestamp defects."},
            {"href": "segments.html", "tag": "Behind the paper", "title": "Turn segments in the data",
             "text": "What the detector found in each drive and how many windows survived."},
            {"href": "data-inventory.html", "tag": "Behind the paper", "title": "Sensor &amp; drive inventory",
             "text": "Layouts, extrinsics, drive profiles and measured co-visibility per pair."},
        ]},

        {"t": "h", "level": 2, "id": "pipeline", "text": "Pipeline at a glance"},
        {"t": "fig", "src": "../assets/fig02_two_stage_pipeline_module_data_v6.png",
         "alt": "Two-stage NH-Calib pipeline with modules and data nodes",
         "cap": "Stage 1 runs independently per sensor and needs no inter-sensor synchronization. Stage 2 is the only "
                "part that pairs sensors, and it produces exactly one component of the result."},
        {"t": "code", "cap": "Data flow in text form. Arrows carry data, not control.",
         "text": """per-sensor twist  (v, omega, timestamps)
        |
  [A1]  smoothing  ->  shared turn segments -------------------------.
        |                                                            |
  [A2]  representative rotation axis  ->  roll, pitch                |
        |                                                            |
  [A3]  sign gauge:  relative bits measured, global bit declared     |
        |                                                            |
        +--> levelled 2-D twist ------------------.                  |
        |                                         |                  |
  [A4]  lateral NHC residual  ->  yaw, X, shared c |                 |
        |                                         |                  |
  [A5]  compose against reference  ->  relative roll, pitch, yaw, X  |
                                                  |                  |
                                                  v                  v
                                        [B1] clock offset, association, common windows
                                                  |
                                        [B2] integrate over window  ->  pairwise dY
                                                  |
                                        [B3] robust weighted graph  ->  relative Y
                                                  |
                                   reference-relative 5-DoF calibration"""},

        {"t": "h", "level": 2, "id": "modules", "text": "Module index"},
        {"t": "table",
         "head": ["ID", "Module", "Consumes", "Produces", "Needs a second sensor?"],
         "rows": [
             ["<a href='m1-turn-segments.html'>A1</a>", "Turn-segment extraction",
              "Raw twist", "Smoothed twist, shared segments", "No"],
             ["<a href='m2-roll-pitch.html'>A2</a>", "Motion-plane alignment",
              "Angular velocity in turns", "Roll, pitch, levelling rotation", "No"],
             ["<a href='gauge.html'>A3</a>", "Rotation-sign gauge",
              "Per-sensor axes", "Sign bits, gauge declaration", "Only for the relative bits"],
             ["<a href='m3-x-yaw.html'>A4</a>", "X, Yaw and slip",
              "Levelled twist, platform speed", "Yaw, longitudinal offset, shared c", "No"],
             ["<a href='relativization.html'>A5</a>", "Reference relativization",
              "Per-sensor poses", "Relative roll, pitch, yaw, X", "Reference channel only"],
             ["<a href='time-alignment.html'>B1</a>", "Alignment and windows",
              "Segments, yaw-rate signals", "Associated pairs, common windows", "Yes"],
             ["<a href='sum-form.html'>B2</a>", "Sum-form relative Y",
              "Common windows", "Pairwise lateral difference", "Yes"],
             ["<a href='graph.html'>B3</a>", "Graph integration",
              "Pairwise measurements", "Consistent relative Y", "Yes"],
         ],
         "cap": "Five of the eight modules never look at a second sensor. That asymmetry is the method's central "
                "design property."},

        {"t": "h", "level": 2, "id": "props", "text": "Properties worth knowing before reading further"},
        {"t": "ul", "items": [
            "<strong>No overlapping field of view is required.</strong> Sensors are never registered against each "
            "other; only their motion is compared.",
            "<strong>No targets, no infrastructure.</strong> The vehicle's own turning motion is the calibration "
            "signal.",
            "<strong>Modality-independent.</strong> Any front end that produces metric linear and angular velocity "
            "qualifies &mdash; LiDAR odometry, radar odometry, GNSS/INS, or wheel speed with an angular-rate source.",
            "<strong>One-way pipeline.</strong> A1 &rarr; A5 &rarr; B3 with no feedback loop; changing an early "
            "setting invalidates everything after it.",
            "<strong>Relative by construction.</strong> Results are stated against a reference sensor, which is also "
            "the gauge anchor and the fixed graph node.",
            "<strong>Scale is assumed known.</strong> Sensors without metric translation, such as a monocular camera, "
            "are outside the scope of the method as described here.",
        ]},

        {"t": "h", "level": 2, "id": "caveats", "text": "Reading caveats"},
        {"t": "note", "kind": "warn",
         "text": "Numeric values on these pages are reference-implementation defaults for the reported configuration. "
                 "Where the design note and the manuscript differ &mdash; for instance in solver initialisation "
                 "&mdash; the page says so explicitly rather than silently picking one. Accuracy figures are stated "
                 "with their sample basis; single-log numbers are not representative on their own."},
    ],
    "seealso": [
        ("../index.html", "Project page", "abstract, figures and quantitative results"),
        ("../algorithm.html", "Visual walkthrough", "the same pipeline as a single scrollable illustration"),
    ],
}

# ------------------------------------------------------------------ observability
OBS = {
    "slug": "observability.html",
    "title": "Observability decomposition",
    "crumbs": "Algorithm wiki &rsaquo; Overview",
    "tagline": "Six degrees of freedom, three fates. Four are recoverable by each sensor on its own, one needs two "
               "sensors to observe the same turn, and one is not observable from planar motion at all. Every design "
               "choice in NH-Calib follows from this table.",
    "desc": "Which extrinsic degrees of freedom are observable under wheeled-vehicle planar motion, and from what.",
    "infobox": [
        ("Total", "6 extrinsic degrees of freedom"),
        ("Sensor-alone", "Roll, Pitch, Yaw, X"),
        ("Needs association", "Y (lateral offset)"),
        ("Unobservable", "Z (vertical offset)"),
        ("Gauge freedom", "One global rotation sign bit"),
        ("Consequence", "Only one component depends on inter-sensor timing"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "table", "no": 1, "text": "The decomposition"},
        {"t": "table",
         "head": ["Component", "Observed from", "Second sensor?", "Timing dependence", "Module"],
         "rows": [
             ["Roll <span class='sym'>&phi;</span>", "Direction of the sensor's own angular-velocity axis",
              "No", "None", "<a href='m2-roll-pitch.html'>A2</a>"],
             ["Pitch <span class='sym'>&theta;</span>", "Same axis, second Euler component",
              "No", "None", "<a href='m2-roll-pitch.html'>A2</a>"],
             ["Yaw <span class='sym'>&psi;</span>", "Rotation bringing the sensor's lateral velocity onto the platform axis",
              "No", "None", "<a href='m3-x-yaw.html'>A4</a>"],
             ["X (p<sub>x</sub>)", "Lateral velocity induced by yaw rotation, v<sub>y</sub> = &omega;p<sub>x</sub>",
              "No", "None, when the sensor's own angular rate is used",
              "<a href='m3-x-yaw.html'>A4</a>"],
             ["Y (p<sub>y</sub>)", "Arc-length difference of two sensors over one turn",
              "<strong>Yes</strong>", "<strong>Confined to two window boundaries</strong>",
              "<a href='sum-form.html'>B2</a>, <a href='graph.html'>B3</a>"],
             ["Z (p<sub>z</sub>)", "Nothing &mdash; planar motion provides no vertical excitation",
              "&mdash;", "&mdash;", "not estimated"],
         ],
         "cap": "The column that matters is the third one. Four components never require another sensor to exist, let "
                "alone to be synchronized with."},

        {"t": "h", "level": 2, "id": "four", "no": 2, "text": "Why four components come free"},
        {"t": "p", "text": "Wheeled-vehicle motion supplies two constraints that a single sensor can exploit without "
                           "any external reference."},
        {"t": "ol", "items": [
            "<strong>Planar motion.</strong> Within a segment the platform rotates about one axis. A sensor measuring "
            "its own angular velocity therefore measures the plane normal in its own frame, which fixes two rotational "
            "degrees of freedom &mdash; roll and pitch &mdash; up to a sign.",
            "<strong>The non-holonomic constraint.</strong> The rear-axle centre has no lateral velocity, so any "
            "lateral velocity a sensor measures during a turn is its own longitudinal lever arm. This fixes yaw and "
            "the longitudinal offset from the same residual.",
        ]},
        {"t": "note", "kind": "key",
         "text": "These are two independent assumptions, not one. Planar motion is a statement about the road and the "
                 "body; the non-holonomic constraint is a statement about the wheels. Conflating them would make the "
                 "argument circular, because interval-based alternatives are affected by planar motion too."},

        {"t": "fig", "src": "figs/core-idea.png",
         "alt": "Two-panel derivation of the longitudinal offset from the lever arm and of the lateral offset from arc length",
         "cap": "The two mechanisms side by side. (a) With no lateral velocity at the rear-axle point, a sensor's own lateral speed in a turn is &omega;&middot;p<sub>x</sub>, so its longitudinal offset follows from its own twist alone. (b) Two sensors on one rigid body share the same instantaneous centre and the same heading change, so their path-length difference over a turn is &minus;&Delta;p<sub>y</sub>&middot;&Delta;&theta;: the vehicle speed cancels, but two sensors are required &mdash; which is why this one component stays coupled."},
        {"t": "h", "level": 2, "id": "one", "no": 3, "text": "Why Y is different"},
        {"t": "p", "text": "The lateral offset appears in the longitudinal velocity relation "
                           "v<sub>j,x</sub> = v<sub>c,x</sub> &minus; &omega;p<sub>y,j</sub>. Unlike the lateral "
                           "equation, this one contains the platform's forward speed, and that speed is unknown and "
                           "time-varying. A sensor cannot separate its own lateral offset from a speed it cannot "
                           "measure independently."},
        {"t": "p", "text": "Two sensors can, because the unknown speed is common to both and cancels in the "
                           "difference. That is the entire reason Stage 2 exists, and the reason it is restricted to "
                           "one component."},
        {"t": "note", "kind": "note", "label": "A special case, deliberately not proposed",
         "text": "If the platform held a constant forward speed while driving a variety of curvatures, the speed term "
                 "would become a constant and a single sensor could identify its own lateral offset from the variation "
                 "of the yaw rate alone. That requires a dedicated manoeuvre and does not hold in ordinary driving, so "
                 "it is noted only as an observation and is not part of the proposed method, its claims, or its "
                 "experiments."},

        {"t": "h", "level": 2, "id": "z", "no": 4, "text": "Why Z is absent"},
        {"t": "p", "text": "Vertical offset would need the platform to rotate about a horizontal axis, or to translate "
                           "vertically in a way the sensors can observe. Locally planar driving supplies neither in "
                           "sufficient magnitude, so no amount of data collection makes it observable."},
        {"t": "note", "kind": "warn",
         "text": "This is a property of the <em>motion</em>, not a weakness of NH-Calib relative to other motion-based "
                 "methods. Interval-based hand&ndash;eye formulations lose the same component under the same motion. "
                 "It is stated here so that a five-component output is not mistaken for an incomplete implementation."},

        {"t": "p", "text": "That statement has been measured rather than only argued. Road-induced pitch transients "
                           "&mdash; speed bumps, dips, expansion joints &mdash; are the natural candidate for vertical "
                           "excitation, because p<sub>z</sub> enters the rigid-body relation only through the pitch "
                           "channel, v<sub>j,x</sub> = v<sub>c,x</sub> + &omega;<sub>y</sub>p<sub>z,j</sub> "
                           "&minus; &omega;<sub>z</sub>p<sub>y,j</sub>. Integrated over a window this gives "
                           "I<sub>x</sub> = &Theta;<sub>y</sub>&middot;&Delta;p<sub>z</sub> &minus; "
                           "&Theta;<sub>z</sub>&middot;&Delta;p<sub>y</sub>, so the entire lever for the vertical "
                           "offset is the integrated pitch angle &Theta;<sub>y</sub> = &int;&omega;<sub>y</sub>dt."},
        {"t": "p", "text": "Counting those transients in the Ford INS attitude at 200&nbsp;Hz &mdash; peak rate at "
                           "least 2&deg;/s, duration between 0.2 and 0.6&nbsp;s &mdash; finds plenty of them. The "
                           "lever they carry is the problem, not their number."},
        {"t": "table",
         "head": ["Drive", "Pitch transients", "&Theta;<sub>y</sub> median [rad]", "Aggregate lever vs five turns",
                  "&Delta;p<sub>z</sub> MAE, oracle lever [mm]", "&Delta;p<sub>z</sub> MAE, sensor lever [mm]",
                  "Trivial &Delta;p<sub>z</sub>=0 [mm]"],
         "rows": [
             ["Log&nbsp;4", "278", "0.0092", "0.193", "330.0", "605.0", "90.0"],
             ["Log&nbsp;5", "374", "0.0096", "0.224", "680.8", "562.2", "90.0"],
             ["Log&nbsp;6", "245", "0.0096", "0.182", "273.4", "447.3", "90.0"],
         ],
         "cap": "One transient carries about 1.8&percnt; of the lever of a single 30&deg; turn. Pooling every "
                "transient in all three drives still reaches only 35&percnt; of the lever that five turns already "
                "provide for the lateral offset. Fitting &Delta;p<sub>z</sub> on those windows &mdash; even when the "
                "lever is computed from the 200&nbsp;Hz ground-truth attitude rather than from the sensor &mdash; is "
                "three to seven times worse than simply declaring the two sensors to be at the same height."},
        {"t": "note", "kind": "warn", "label": "Two mechanisms remove the lever",
         "text": "A bump that is driven over completely returns the body to its original attitude, so "
                 "&int;&omega;<sub>y</sub>dt over the full event is approximately zero and the integral form cancels "
                 "its own lever. Using only the rising or falling half keeps a lever but exposes differential scale "
                 "error. Separately, a 0.28&nbsp;s transient spans roughly three frames of a 10&nbsp;Hz lidar: the "
                 "pitch lever actually visible in the sensor stream is only 30&ndash;44&percnt; of the lever present "
                 "in the 200&nbsp;Hz reference."},
        {"t": "note", "kind": "note", "label": "The omitted roll term",
         "text": "The lateral residual in <a href='m3-x-yaw.html'>A4</a> drops a &minus;&omega;<sub>x</sub>p<sub>z</sub> "
                 "term for the same reason. Measured on the samples the pipeline actually consumes, that term is "
                 "3&ndash;16&percnt; the size of the &omega;<sub>z</sub>p<sub>x</sub> term it sits beside, and holding "
                 "p<sub>z</sub> at its true value shifts the absolute longitudinal offset by up to about 40&nbsp;mm "
                 "with the same sign across forward channels &mdash; largely common mode, so relative estimates absorb "
                 "most of it. Letting p<sub>z</sub> float instead is actively harmful: the design condition number "
                 "rises by 4&ndash;16&times; and some channels jump to the opposite yaw branch."},

        {"t": "h", "level": 2, "id": "gauge", "no": 5, "text": "Gauge freedoms"},
        {"t": "table",
         "head": ["Freedom", "Status", "How it is handled"],
         "rows": [
             ["Global rotation sign (one bit for the whole platform)", "Not observable from planar motion",
              "Declared: the reference sensor is defined to be upright &mdash; see <a href='gauge.html'>A3</a>"],
             ["Per-sensor relative sign bits (N &minus; 1)", "Observable",
              "Measured by joint rotation averaging against a shared body angular velocity"],
             ["Additive constant on all lateral offsets", "Not observable from differences alone",
              "Removed by fixing the reference node at y<sub>r</sub> = 0 in <a href='graph.html'>B3</a>"],
             ["Vehicle-frame lateral origin", "Observable only with an extra channel",
              "Optional wheel-odometry virtual node at the rear-axle centre"],
         ]},

        {"t": "h", "level": 2, "id": "consequence", "no": 6, "text": "What the decomposition buys"},
        {"t": "ul", "items": [
            "Sensors that share no field of view can still be calibrated against each other, because nothing is "
            "registered between them.",
            "Adding a sensor adds one node and its edges; the existing per-sensor estimates do not have to be redone.",
            "A channel whose odometry degrades affects its own estimates and its own edges; it does not corrupt the "
            "others through a shared trajectory constraint.",
            "Only one of the five reported components is exposed to inter-sensor clock error, and that exposure is "
            "further confined to two integration boundaries.",
        ]},
        {"t": "note", "kind": "warn", "label": "What this does not claim",
         "text": "Reducing the number of alignment-dependent components is not the same as being robust to "
                 "misalignment. When a clock offset is injected deliberately, the lateral component degrades; the "
                 "measured advantage is that the other four components do not move at all, and that integrating over "
                 "a window degrades more slowly than differencing sample by sample. Time alignment itself is ordinary "
                 "preprocessing available to any method."},
    ],
    "seealso": [
        ("m2-roll-pitch.html", "A2 &middot; Motion-plane alignment", "the planar-motion half of the argument"),
        ("m3-x-yaw.html", "A4 &middot; X, Yaw and slip", "the non-holonomic half"),
        ("sum-form.html", "B2 &middot; Sum-form relative Y", "the one component that needs association"),
    ],
}

# ------------------------------------------------------------------ notation
NOTATION = {
    "slug": "notation.html",
    "title": "Notation and frames",
    "crumbs": "Algorithm wiki &rsaquo; Reference",
    "tagline": "Symbols, coordinate frames and sign conventions used throughout the wiki. Where a sign could be read "
               "two ways, the convention is stated explicitly rather than implied.",
    "desc": "Reference table of symbols, frames and conventions in NH-Calib.",
    "infobox": [
        ("Vehicle frame", "Origin at rear-axle centre; X forward, Y left, Z up"),
        ("Euler order", "R = R<sub>z</sub>(yaw) R<sub>y</sub>(pitch) R<sub>x</sub>(roll)"),
        ("Angles", "radians internally, degrees in reported output"),
        ("Rotation composition", "matrix product, never Euler subtraction"),
        ("Reference sensor", "same channel for gauge anchor, relativization and graph node"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "frames", "no": 1, "text": "Frames"},
        {"t": "table",
         "head": ["Frame", "Definition"],
         "rows": [
             ["Vehicle <span class='sym'>V</span>",
              "Right-handed; origin at the rear-axle centre; X forward, Y left, Z up. The non-holonomic constraint is "
              "stated at this origin."],
             ["Sensor <span class='sym'>S</span><sub>j</sub>",
              "The frame in which sensor j's odometry reports its twist. Its pose in the vehicle frame is the "
              "calibration target."],
             ["Levelled frame",
              "Sensor frame after A2's levelling rotation. Its z-axis coincides with the motion-plane normal; its "
              "remaining freedom about that axis is the mounting yaw."],
             ["Reference-relative frame",
              "The frame of the designated reference sensor. All reported results live here."],
         ]},
        {"t": "note", "kind": "gauge",
         "text": "The vehicle frame recovered by NH-Calib is defined by the motion plane the platform actually "
                 "travelled on and by the convention that the reference sensor is upright. It is not asserted to "
                 "coincide with a surveyed physical body frame."},

        {"t": "h", "level": 2, "id": "symbols", "no": 2, "text": "Symbols"},
        {"t": "table",
         "head": ["Symbol", "Meaning", "Unit / frame"],
         "rows": [
             ["<span class='sym'>&xi;</span><sub>j</sub>(t)", "Sensor twist, linear and angular velocity stacked", "m/s, rad/s; sensor frame"],
             ["v<sub>j,x</sub>, v<sub>j,y</sub>", "Sensor-origin linear velocity components", "m/s"],
             ["<span class='sym'>&omega;</span><sub>j</sub>", "Sensor angular velocity vector", "rad/s; sensor frame"],
             ["&omega;(t)", "Scalar platform turn rate", "rad/s"],
             ["&omega;<sub>turn</sub>", "Yaw-centric detection scalar, &#8214;&omega;&#8214;&middot;sign(&omega;<sub>z</sub>)", "rad/s"],
             ["v<sub>c</sub>", "Platform forward speed from chassis, INS or CAN", "m/s; vehicle frame"],
             ["<strong>a</strong><sub>j</sub>", "Estimated rotation axis of sensor j", "unit vector; sensor frame"],
             ["<span class='sym'>&phi;</span><sub>j</sub>, <span class='sym'>&theta;</span><sub>j</sub>, <span class='sym'>&psi;</span><sub>j</sub>",
              "Mounting roll, pitch, yaw", "rad internally, deg reported"],
             ["p<sub>x,j</sub>, p<sub>y,j</sub>, p<sub>z,j</sub>", "Sensor lever arm in the vehicle frame", "m"],
             ["c", "Shared slip coefficient (nuisance parameter)", "s&sup2;/m"],
             ["W<sub>k</sub>", "Net heading change of segment k", "rad"],
             ["T<sub>k</sub>", "Duration of segment k", "s"],
             ["I<sub>j,k</sub>", "Forward displacement of sensor j over the common window of segment k", "m"],
             ["<span class='sym'>&Delta;</span>I<sub>k</sub>", "Arc-length difference of the sensor pair", "m"],
             ["Z<sub>k</sub>", "Regression observation formed from the segment difference", "m"],
             ["w<sub>k</sub>, w<sub>ij</sub>", "Segment weight and pairwise edge confidence", "&mdash;"],
             ["d<sub>ij</sub>", "Pairwise relative lateral measurement", "m"],
             ["<span class='sym'>&tau;</span><sub>ij</sub>", "Estimated clock offset of a sensor pair", "s"],
             ["N<sub>w</sub>", "Odd smoothing window length in samples", "count"],
         ]},

        {"t": "h", "level": 2, "id": "signs", "no": 3, "text": "Sign conventions"},
        {"t": "table",
         "head": ["Quantity", "Convention", "Where it matters"],
         "rows": [
             ["Yaw rate", "Positive for a left turn, consistent with a Z-up vehicle frame",
              "Turn detection, gauge decision"],
             ["Lateral offset", "Positive to the left of the rear-axle centre", "All lateral results"],
             ["<span class='sym'>&Delta;</span>I and <span class='sym'>&Delta;</span>p<sub>y</sub>",
              "<span class='sym'>&Delta;</span>I = I<sub>i</sub> &minus; I<sub>j</sub> is paired with "
              "<span class='sym'>&Delta;</span>p<sub>y,ij</sub> = p<sub>y,i</sub> &minus; p<sub>y,j</sub>, giving "
              "<span class='sym'>&Delta;</span>I = &minus;<span class='sym'>&Delta;</span>p<sub>y</sub>W",
              "<a href='sum-form.html'>B2</a> regression &mdash; the minus sign is not optional"],
             ["Slip term", "v<sub>c,y</sub> &asymp; &minus;c v<sub>c</sub><sup>2</sup>&omega;, so c = 0 recovers the "
                           "classical constraint", "<a href='m3-x-yaw.html'>A4</a> residual"],
             ["Rotation axis", "Defined up to a 180&deg; flip; the global branch is a declared convention",
              "<a href='gauge.html'>A3</a>"],
         ]},
        {"t": "note", "kind": "warn",
         "text": "Relative rotations are always taken as matrix products "
                 "R&#770;<sub>rj</sub> = R&#770;<sub>Vr</sub><sup>&#8868;</sup>R&#770;<sub>Vj</sub>. Subtracting Euler "
                 "angles gives a different answer as soon as two of the angles are not small, and the difference is "
                 "large enough to matter at the accuracy level being reported."},

        {"t": "h", "level": 2, "id": "axes", "no": 4, "text": "Axis naming in results"},
        {"t": "p", "text": "Tables and plots use X, Y, Yaw, Roll and Pitch as column labels. Equations keep the "
                           "symbolic forms p<sub>x</sub>, p<sub>y</sub> and <span class='sym'>&psi;</span>. The two "
                           "refer to the same quantities; the split exists so that result tables stay readable "
                           "without subscripts."},
    ],
    "seealso": [
        ("parameters.html", "Parameter reference", "numeric defaults for every symbol that has one"),
        ("observability.html", "Observability decomposition", "which of these symbols are actually solvable"),
    ],
}

# ------------------------------------------------------------------ parameters
PARAMS = {
    "slug": "parameters.html",
    "title": "Parameter reference",
    "crumbs": "Algorithm wiki &rsaquo; Reference",
    "tagline": "Every threshold, constant and solver setting in one place, grouped by the module that reads it. "
               "Values are the reference-implementation defaults; deviations used in a specific experiment are stated "
               "on the module page.",
    "desc": "Complete list of NH-Calib parameters with defaults and purpose.",
    "infobox": [
        ("Scope", "Core pipeline only; odometry front-end settings are external"),
        ("Granularity", "Run-level &mdash; identical for every channel in a run"),
        ("Refit rule", "Changing any A1 value invalidates all later modules"),
        ("Tuning sensitivity", "Most gates are inert on the reported datasets"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "a1", "no": 1, "text": "A1 &mdash; smoothing and turn detection"},
        {"t": "table", "cls": "num",
         "head": ["Parameter", "Default", "Meaning"],
         "rows": [
             ["smoothing window", "1.0&nbsp;s", "Time constant; converted to an odd sample count per dataset"],
             ["smoothing mode", "<code>pose-sg</code>", "Pose-domain polynomial smoothing; alternatives listed on the A1 page"],
             ["polynomial order", "2", "Order used by the pose-domain fit"],
             ["turn hold rate", "5&nbsp;deg/s", "Lower hysteresis threshold, segment boundaries"],
             ["turn peak rate", "15&nbsp;deg/s", "Upper hysteresis threshold, candidate acceptance"],
             ["turn heading minimum", "30&nbsp;deg", "Minimum |W<sub>k</sub>| for an accepted segment"],
             ["speed minimum", "1.0&nbsp;m/s", "Minimum mean platform speed inside a segment"],
             ["maximum internal gap", "0.3&nbsp;s", "Mandatory split; prevents mega-segments"],
             ["turn rate mode", "<code>norm</code>", "&#8214;&omega;&#8214;&middot;sign(&omega;<sub>z</sub>); <code>wz</code> mode for planar streams"],
             ["duration minimum", "0.8&nbsp;s", "Present in settings; not enforced as a separate gate in the reported configuration"],
             ["excluded segment ids", "empty", "Manual or automatic exclusion mask applied after detection"],
         ]},

        {"t": "h", "level": 2, "id": "a2", "no": 2, "text": "A2 / A3 &mdash; axis and gauge"},
        {"t": "table", "cls": "num",
         "head": ["Parameter", "Default", "Meaning"],
         "rows": [
             ["axis information minimum", "15&nbsp;deg/s", "Lower bound on &#8214;&omega;&#8214; for a sample to inform the axis"],
             ["rate sanity maximum", "60&nbsp;deg/s", "Upper bound; above this a sample is treated as an odometry artefact"],
             ["minimum axis samples", "20", "Below this the channel drops at stage <code>axis</code>"],
             ["axis trimming", "disabled", "Robust trimming is off by default; the sample gate already removes tails"],
             ["gauge mode", "joint &omega; alignment", "Alternative: per-sensor scalar rule, kept only as a control"],
             ["minimum absolute correlation", "0.2", "Below this the sign verdict is withheld and reported as assumed"],
             ["bootstrap draws", "0", "Axis bootstrap disabled in the core; enables standard errors when positive"],
         ]},

        {"t": "h", "level": 2, "id": "a4", "no": 3, "text": "A4 &mdash; X, yaw and slip"},
        {"t": "table", "cls": "num",
         "head": ["Parameter", "Default", "Meaning"],
         "rows": [
             ["excitation minimum", "15&nbsp;deg/s", "Minimum yaw rate for a sample to enter the fit"],
             ["minimum planar samples", "50", "Below this the channel drops at stage <code>planar</code>"],
             ["yaw-rate source", "platform channel", "Sensor-own rate is the option that keeps X synchronization-free"],
             ["slip coefficient initial", "0 (manuscript) / 0.008 (design note)", "Initialisation only; the fitted value is reported"],
             ["fit slip", "enabled", "Disabling it forces the classical non-holonomic constraint"],
             ["Huber constant", "1.345", "Robust loss parameter"],
             ["residual scale floor", "10<sup>&minus;3</sup>&nbsp;m/s", "Prevents weight collapse on near-perfect fits"],
             ["step caps", "0.3&nbsp;rad, 1&nbsp;m, 0.004&nbsp;s&sup2;/m", "Per-iteration update limits"],
             ["maximum iterations", "60", "Convergence threshold 10<sup>&minus;11</sup> on the largest step"],
         ]},

        {"t": "h", "level": 2, "id": "b", "no": 4, "text": "B1&ndash;B3 &mdash; association, regression and fusion"},
        {"t": "table", "cls": "num",
         "head": ["Parameter", "Default", "Meaning"],
         "rows": [
             ["association rule", "same sign, positive overlap", "Candidate filter before greedy matching"],
             ["matching order", "overlap descending", "Greedy one-to-one assignment"],
             ["boundary handling", "linear interpolation", "Applied at both common-window ends"],
             ["quality statistics", "uncentred cosine, NRMSE", "Joint verdict against the median waveform"],
             ["alternation rounds", "3", "Clock offset and calibration refined alternately"],
             ["segment weight exponent", "0.5", "Weight is |W<sub>k</sub>|<sup>&nbsp;p&minus;2</sup>, i.e. |W<sub>k</sub>|<sup>&minus;1.5</sup>"],
             ["minimum segments per pair", "2", "Design rank must also be at least two"],
             ["graph loss", "robust kernel", "Suppresses unstable edges and cycle inconsistency"],
             ["graph gauge", "y<sub>r</sub> = 0", "Reference node fixed; optional wheel-odometry node at p<sub>y</sub> = 0"],
         ]},

        {"t": "h", "level": 2, "id": "sens", "no": 5, "text": "Which parameters actually matter"},
        {"t": "ul", "items": [
            "<strong>Time handling dominates.</strong> Treating a variable frame interval as a fixed nominal rate "
            "introduces a systematic error far larger than any threshold choice on the affected dataset.",
            "<strong>Quality gates are near-inert.</strong> Over a wide range the accepted segment set does not change "
            "at all; tightening them enough to reject segments makes results worse, because information is lost.",
            "<strong>Voxel and front-end settings live outside this table</strong> but change the fitted slip "
            "coefficient, including its sign &mdash; another reason c is not interpreted physically.",
            "<strong>Number of valid turns is the real lever.</strong> Pooling additional logs of the same platform "
            "reduced the reported lateral error more than any parameter change tested.",
        ]},
    ],
    "seealso": [
        ("failure-modes.html", "Gates &amp; failure modes", "what happens when a gate is not met"),
        ("m1-turn-segments.html", "A1 &middot; Turn-segment extraction", "where most of these thresholds are applied"),
    ],
}

# ------------------------------------------------------------------ failure modes
FAIL = {
    "slug": "failure-modes.html",
    "title": "Gates and failure modes",
    "crumbs": "Algorithm wiki &rsaquo; Reference",
    "tagline": "NH-Calib prefers dropping a channel to reporting a confident wrong number. This page lists every "
               "point where that decision is made, what it means, and what usually causes it.",
    "desc": "Drop stages, gate conditions and diagnostic guidance for NH-Calib.",
    "infobox": [
        ("Principle", "Fail loudly and early; never silently substitute"),
        ("Granularity", "Per channel, and per sensor pair in Stage 2"),
        ("Propagation", "Drops flow forward only; later modules never retry"),
        ("Total failure", "All channels dropped &rarr; the run raises an error"),
    ],
    "blocks": [
        {"t": "h", "level": 2, "id": "drops", "no": 1, "text": "Drop stages"},
        {"t": "table",
         "head": ["Stage label", "Condition", "Module", "Typical cause"],
         "rows": [
             ["<code>turn</code>", "No accepted segments after exclusion", "A1",
              "Straight-only sequence, or a drive whose turns never reach the peak or heading thresholds"],
             ["<code>axis</code>", "Fewer than 20 gated samples", "A2",
              "Very little turning, or angular rates that exceed the sanity bound and are rejected as artefacts"],
             ["<code>planar</code>", "Fewer than 50 samples after the excitation gate", "A2 &rarr; A4",
              "Weak yaw excitation, low speed, or a mismatch between sensor and platform-speed time ranges"],
             ["<code>step4</code>", "Regression cannot be formed", "B2",
              "Fewer than two associated segments, or a rank-deficient design"],
         ],
         "cap": "A dropped channel produces no downstream estimate. Surviving channels are still reported."},
        {"t": "note", "kind": "key",
         "text": "Drops are not errors in the software sense &mdash; they are the correct response to a sequence that "
                 "does not contain the motion the method needs. The distinction to keep in mind: a drop means "
                 "<em>this drive cannot answer</em>, not <em>this sensor is miscalibrated</em>."},

        {"t": "h", "level": 2, "id": "pairs", "no": 2, "text": "Pair-level rejections"},
        {"t": "table",
         "head": ["Rejection", "Where", "Meaning"],
         "rows": [
             ["No associated segment", "B1", "The two sensors never observed a compatible turn together"],
             ["Empty common window", "B1", "Associated segments overlap in index but not in time after offset correction"],
             ["Quality verdict failed", "B1", "One sensor's waveform disagrees with the median in shape or magnitude"],
             ["Withheld sign verdict", "A3", "Correlation too weak to decide the relative sign; reported as assumed, not applied"],
             ["Excluded from shared body rate", "A3", "The channel exceeds the rate sanity bound on more than half its samples"],
             ["Edge downweighted", "B3", "The robust loss suppresses a pairwise measurement inconsistent with the rest of the graph"],
         ]},

        {"t": "h", "level": 2, "id": "silent", "no": 3, "text": "Failure modes that do not raise anything"},
        {"t": "note", "kind": "warn", "label": "Planar-stream sign bypass",
         "text": "A channel whose angular velocity is exactly two-dimensional takes a shortcut that forces an identity "
                 "levelling matrix and never reaches the sign-decision step. A physically inverted channel of this "
                 "kind keeps its wrong sign without any warning. The joint gauge formulation covers these channels; "
                 "the per-sensor scalar rule does not. See <a href='gauge.html'>A3</a>."},
        {"t": "note", "kind": "warn", "label": "Fixed nominal frame interval",
         "text": "Substituting a nominal sensor rate for the actual per-frame interval leaves every gate satisfied "
                 "while biasing the integrals. This is a data-handling mistake rather than an algorithmic one, and it "
                 "is invisible to the pipeline's own checks."},
        {"t": "note", "kind": "warn", "label": "Slip coefficient sign flip",
         "text": "The fitted coefficient absorbs whatever common bias the odometry front end carries, so it can change "
                 "sign when the front end or its voxel size changes. Relative results are protected because the bias "
                 "is common-mode; absolute longitudinal offset is not. Never report c as a vehicle property."},
        {"t": "note", "kind": "warn", "label": "Degraded reference channel",
         "text": "Because everything is stated relative to one reference sensor, that channel's own error enters every "
                 "pair with the same sign. A weak reference degrades all results uniformly, which can look like a "
                 "systematic offset rather than a single bad channel."},

        {"t": "h", "level": 2, "id": "diag", "no": 4, "text": "Diagnostics to look at first"},
        {"t": "table",
         "head": ["Symptom", "Check", "Page"],
         "rows": [
             ["Channel dropped at <code>turn</code>", "Turn-rate trace against the two thresholds; segment count per channel",
              "<a href='m1-turn-segments.html'>A1</a>"],
             ["Roll or pitch off by roughly 180&deg;", "Relative sign verdict and its correlation value",
              "<a href='gauge.html'>A3</a>"],
             ["Longitudinal offset drifts between runs", "Fitted slip coefficient and the front-end configuration",
              "<a href='m3-x-yaw.html'>A4</a>"],
             ["Lateral result scatters across segments", "Per-window heading change and the regression residuals",
              "<a href='sum-form.html'>B2</a>"],
             ["Pairwise values disagree around a cycle", "Edge weights and residuals after robust fusion",
              "<a href='graph.html'>B3</a>"],
             ["One sensor is consistently offset", "Whether it is the reference channel itself",
              "<a href='relativization.html'>A5</a>"],
         ]},
        {"t": "p", "cls": "small",
         "text": "The single most informative test when results look wrong: replace the odometry with a ground-truth "
                 "trajectory and rerun the same estimator. If the error collapses, the pipeline is sound and the front "
                 "end is the cause; if it does not, the problem is in association, timing or convention."},
    ],
    "seealso": [
        ("parameters.html", "Parameter reference", "the thresholds these gates apply"),
        ("observability.html", "Observability decomposition", "failures that are properties of the motion, not bugs"),
    ],
}

PAGES = [INDEX, OBS, NOTATION, PARAMS, FAIL]
