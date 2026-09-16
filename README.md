# NH-Calib project page

Static, dependency-free project page for the anonymous NH-Calib manuscript:

> **NH-Calib: Vehicle-Motion-Constrained Self-Calibration of Onboard Sensor Extrinsics**

Published at <https://nh-calib.github.io/>.

## Current content

- Latest anonymous title, abstract, and vehicle-motion-constrained framing.
- Two-stage method overview with the current user-authored Figs. 1--3.
- Graph-integrated relative calibration results for A2D2, RadarScenes, and Ford Multi-AV Logs 4--6.
- Anonymous resource placeholders for the paper, code, processed data, and documentation.

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
