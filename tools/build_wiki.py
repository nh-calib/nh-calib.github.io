# -*- coding: utf-8 -*-
"""Build the NH-Calib algorithm wiki into project_page/wiki/.

Usage:  python tools/build_wiki.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import wiki_render as R          # noqa: E402
import wiki_content_a as A       # noqa: E402
import wiki_content_b as B       # noqa: E402
import wiki_content_c as C       # noqa: E402
import wiki_content_d as D       # noqa: E402

ORDER = ([C.INDEX, C.OBS] + A.PAGES + B.PAGES + D.PAGES
         + [C.NOTATION, C.PARAMS, C.FAIL])


def normalize(pages):
    for p in pages:
        if not p["slug"].endswith(".html"):
            p["slug"] = p["slug"] + ".html"
    return pages


def check_links(pages):
    """Every internal href must resolve to a generated page or an existing asset."""
    slugs = {p["slug"] for p in pages}
    root = R.OUT
    problems = []
    for p in pages:
        html = (root / p["slug"]).read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"#]+)(?:#[^"]*)?"', html):
            if href.startswith(("http", "mailto:")):
                continue
            if href.endswith(".css"):
                continue
            if href.startswith("../"):
                if not (root.parent / href[3:]).exists():
                    problems.append((p["slug"], href, "missing parent-dir target"))
                continue
            if href not in slugs:
                problems.append((p["slug"], href, "unknown wiki page"))
        for src in re.findall(r'<img src="([^"]+)"', html):
            target = (root / src).resolve()
            if not target.exists():
                problems.append((p["slug"], src, "missing image"))
    return problems


def main():
    pages = normalize(ORDER)
    written = R.build(pages)
    print("built %d pages in %s" % (len(written), R.OUT))
    for s in written:
        size = (R.OUT / s).stat().st_size
        print("  %-26s %7d B" % (s, size))

    nav_targets = {h for _, links in R.NAV for h, _ in links}
    missing_nav = nav_targets - set(written)
    if missing_nav:
        print("NAV points at pages that were not built: %s" % sorted(missing_nav))

    problems = check_links(pages)
    if problems:
        print("\nLINK PROBLEMS (%d):" % len(problems))
        for a, b, c in problems:
            print("  %-26s -> %-42s %s" % (a, b, c))
    else:
        print("\nlink check: OK (all internal hrefs and images resolve)")
    return 1 if problems or missing_nav else 0


if __name__ == "__main__":
    raise SystemExit(main())
