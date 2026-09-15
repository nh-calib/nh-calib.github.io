# NH-Calib project page

Static, dependency-free project page for the anonymous NH-Calib ICRA 2027 submission.

## Anonymous publication target

- Candidate account: `nh-calib-project` (available when checked on 15 September 2026).
- Candidate URL: `https://nh-calib-project.github.io/`.
- Create the GitHub account with a new neutral email address that is not associated with any author, lab, institution, ORCID, or existing GitHub account.
- Do not fork from, transfer from, star with, or add as a collaborator any identity-bearing account during review.
- Use only neutral commit metadata such as `Anonymous Researcher <anonymous@users.noreply.github.com>`.
- Keep analytics, external fonts, author links, lab logos, and identity-bearing media metadata out of the review deployment.

## Local preview

From this directory, run a local HTTP server:

```powershell
& 'C:\Program Files\Python312\python.exe' -m http.server 8080
```

Then open `http://localhost:8080/` on win_lab.

## Review-period publication checklist

- Keep `Anonymous`, `Under review`, and the frozen English paper title unchanged during review.
- Keep paper, code, data, and video identity-bearing URLs disabled until the anonymity period ends.
- Confirm every metric against the camera-ready manuscript.
- Replace draft raster figures if final vector exports become available.
- Add an Open Graph preview image only after verifying that its metadata is anonymous.
- Test keyboard navigation, mobile layout, and external links.

## GitHub Pages deployment

Publish this folder as the root of the dedicated `nh-calib-project.github.io` repository owned by the anonymous `nh-calib-project` account. No build step is required.

The review deployment is intentionally non-indexed and contains no analytics. Replace anonymous metadata and activate archival links only after acceptance.
