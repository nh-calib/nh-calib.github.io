# NH-Calib project page

Static, dependency-free project page for the anonymous NH-Calib manuscript:

> **NH-Calib: Vehicle-Motion-Constrained Self-Calibration of Onboard Sensor Extrinsics**

Published at <https://nh-calib.github.io/>.

## Current content

- Latest anonymous title, abstract, and vehicle-motion-constrained framing.
- Two-stage method overview with the current user-authored Figs. 1--3.
- Graph-integrated relative calibration results for A2D2, RadarScenes, and Ford Multi-AV Logs 4--6.
- Anonymous resource placeholders for the paper, code, processed data, and documentation.
- `algorithm.html` &mdash; a single scrollable visual walkthrough of the pipeline.
- `wiki/` &mdash; a generated, page-per-algorithm reference (19 pages, 38 figures).

## Algorithm wiki

`wiki/` is generated, not hand-edited. Content lives in Python dictionaries and is rendered to static HTML:

| File | Role |
| --- | --- |
| `tools/build_wiki.py` | Entry point; builds every page and verifies that all internal links and images resolve |
| `tools/wiki_render.py` | HTML renderer, sidebar navigation, page template, block types |
| `tools/wiki_content_a.py` | Stage 1 pages (A1 turn segments, A2 motion-plane alignment, A3 sign gauge, A4 X/yaw/slip, A5 relativization) |
| `tools/wiki_content_b.py` | Stage 2 pages (B1 alignment and windows, B2 sum-form relative Y, B3 graph integration) |
| `tools/wiki_content_c.py` | Index, observability decomposition, notation, parameters, failure modes |
| `tools/wiki_content_d.py` | Evaluation pages (datasets and front end, results and metric) |
| `tools/wiki_content_e.py` | Behind-the-paper pages (sensor and drive inventory, turn segments, odometry front end, ablation catalogue) |
| `wiki/wiki.css` | Wiki stylesheet (hand-edited) |
| `wiki/figs/` | Experiment figures referenced by the pages (web copies, max width 1500 px) |

Rebuild after any content change:

```powershell
& 'C:\Program Files\Python312\python.exe' tools/build_wiki.py
```

The build prints the size of every page and fails loudly if a cross-reference or image path is broken.

### Figures

`wiki/figs/` holds web copies of figures produced by the experiment runs; the originals, with their index
notes and source data, stay in `figures/` in the research tree. Copies are downscaled to 1500 px and the
point-cloud panels are stored as JPEG. Each figure caption states what the panel shows, which run produced
it, and, where a figure is a schematic rather than a measurement, says so explicitly. Figures carrying
numbers from a superseded protocol are captioned with that protocol named.

Source of record for the wiki text: the project design note (`docs/design/NH-Calib_Core_Code_Mapping.md`) and the
canonical manuscript. Numeric defaults are transcribed from those documents; where the two disagree, the page states
both rather than silently choosing one.

## Local preview

From this directory, run:

```powershell
& 'C:\Program Files\Python312\python.exe' -m http.server 8080
```

Then open <http://localhost:8080/> on `win_lab`.

## Publication policy

- Keep author names, affiliations, lab logos, and identity-bearing metadata out while anonymous review is required.
- Release code and processed assets through this project site upon publication.
- Confirm every reported metric against the canonical manuscript before deployment.
- Keep the site dependency-free and free of analytics during anonymous review.

## Deployment

The repository remote is `https://github.com/nh-calib/nh-calib.github.io.git`. GitHub Pages serves the `main` branch from the repository root; no build step is required.
