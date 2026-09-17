"""NH-Calib algorithm wiki -- renderer.

Builds a small static wiki under project_page/wiki/ from page dictionaries.
Content lives in wiki_content_*.py; this module only turns it into HTML.
"""
from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "wiki"

NAV = [
    ("Overview", [
        ("index.html", "Algorithm index"),
        ("observability.html", "Observability decomposition"),
    ]),
    ("Stage 1 &middot; per sensor", [
        ("m1-turn-segments.html", "A1 &middot; Turn-segment extraction"),
        ("m2-roll-pitch.html", "A2 &middot; Motion-plane alignment"),
        ("gauge.html", "A3 &middot; Rotation-sign gauge"),
        ("m3-x-yaw.html", "A4 &middot; X, Yaw and slip"),
        ("relativization.html", "A5 &middot; Reference relativization"),
    ]),
    ("Stage 2 &middot; across sensors", [
        ("time-alignment.html", "B1 &middot; Time alignment &amp; windows"),
        ("sum-form.html", "B2 &middot; Sum-form relative Y"),
        ("graph.html", "B3 &middot; Graph integration"),
    ]),
    ("Evaluation", [
        ("datasets.html", "Datasets &amp; front end"),
        ("results.html", "Results &amp; metric"),
    ]),
    ("Behind the paper", [
        ("data-inventory.html", "Sensor &amp; drive inventory"),
        ("segments.html", "Turn segments in the data"),
        ("odometry.html", "Odometry front end results"),
        ("ablations.html", "Ablation catalogue"),
    ]),
    ("Reference", [
        ("notation.html", "Notation &amp; frames"),
        ("parameters.html", "Parameter reference"),
        ("failure-modes.html", "Gates &amp; failure modes"),
    ]),
]


def esc(s: str) -> str:
    return html.escape(s, quote=False)


# ---------------------------------------------------------------- blocks
def _p(b):
    cls = ' class="%s"' % b["cls"] if b.get("cls") else ""
    return "<p%s>%s</p>" % (cls, b["text"])


def _h(b):
    lvl = b.get("level", 2)
    idattr = ' id="%s"' % b["id"] if b.get("id") else ""
    num = '<span class="secno">%s</span> ' % b["no"] if b.get("no") else ""
    return "<h%d%s>%s%s</h%d>" % (lvl, idattr, num, b["text"], lvl)


def _eq(b):
    tag = '<span class="eqtag">(%s)</span>' % b["tag"] if b.get("tag") else ""
    cap = '<span class="eqcap">%s</span>' % b["cap"] if b.get("cap") else ""
    return '<div class="eq">%s<span class="eqbody">%s</span>%s</div>' % (tag, b["text"], cap)


def _ul(b):
    items = "".join("<li>%s</li>" % i for i in b["items"])
    cls = ' class="%s"' % b["cls"] if b.get("cls") else ""
    return "<ul%s>%s</ul>" % (cls, items)


def _ol(b):
    return "<ol>%s</ol>" % "".join("<li>%s</li>" % i for i in b["items"])


def _steps(b):
    out = ['<div class="steps">']
    for n, (head, body) in enumerate(b["items"], start=b.get("start", 1)):
        out.append(
            '<div class="step"><div class="stepno">%d</div>'
            '<div class="stepbody"><h4>%s</h4><p>%s</p></div></div>' % (n, head, body)
        )
    out.append("</div>")
    return "".join(out)


def _table(b):
    cap = "<figcaption>%s</figcaption>" % b["cap"] if b.get("cap") else ""
    head = "".join("<th>%s</th>" % c for c in b["head"])
    rows = "".join(
        "<tr>" + "".join("<td>%s</td>" % c for c in r) + "</tr>" for r in b["rows"]
    )
    return (
        '<figure class="tablewrap %s"><div class="tscroll"><table>'
        "<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>%s</figure>"
        % (b.get("cls", ""), head, rows, cap)
    )


def _note(b):
    kind = b.get("kind", "note")
    default = {"note": "Note", "warn": "Caution", "key": "Key point",
               "gauge": "Convention", "code": "Implementation"}
    label = b.get("label", default.get(kind, "Note"))
    return ('<div class="note %s"><span class="notelabel">%s</span><div>%s</div></div>'
            % (kind, label, b["text"]))


def _code(b):
    cap = "<figcaption>%s</figcaption>" % b["cap"] if b.get("cap") else ""
    return '<figure class="codewrap"><pre><code>%s</code></pre>%s</figure>' % (esc(b["text"]), cap)


def _fig(b):
    cap = "<figcaption>%s</figcaption>" % b["cap"] if b.get("cap") else ""
    return ('<figure class="wikifig"><img src="%s" alt="%s">%s</figure>'
            % (b["src"], esc(b.get("alt", "")), cap))


def _cards(b):
    out = ['<div class="cards">']
    for c in b["items"]:
        out.append(
            '<a class="card" href="%s"><span class="cardtag">%s</span>'
            "<h4>%s</h4><p>%s</p></a>" % (c["href"], c["tag"], c["title"], c["text"])
        )
    out.append("</div>")
    return "".join(out)


def _raw(b):
    return b["text"]


RENDER = {"p": _p, "h": _h, "eq": _eq, "ul": _ul, "ol": _ol, "steps": _steps,
          "table": _table, "note": _note, "code": _code, "fig": _fig,
          "cards": _cards, "raw": _raw}


def render_blocks(blocks):
    return "\n".join(RENDER[b["t"]](b) for b in blocks)


# ---------------------------------------------------------------- page
def nav_html(active):
    out = ['<nav class="sidenav" aria-label="Wiki navigation">']
    out.append('<a class="brand" href="../index.html">NH-Calib<span>project page</span></a>')
    out.append('<div class="navtitle">Algorithm wiki</div>')
    for group, links in NAV:
        out.append('<div class="navgroup">%s</div><ul>' % group)
        for href, label in links:
            cls = ' class="on"' if href == active else ""
            out.append('<li><a href="%s"%s>%s</a></li>' % (href, cls, label))
        out.append("</ul>")
    out.append("</nav>")
    return "".join(out)


def toc_html(blocks):
    items = [b for b in blocks if b["t"] == "h" and b.get("level", 2) == 2 and b.get("id")]
    if not items:
        return ""
    lis = "".join(
        '<li>%s<a href="#%s">%s</a></li>'
        % (('<span class="tocno">%s</span>' % b["no"]) if b.get("no") else "", b["id"], b["text"])
        for b in items
    )
    return '<div class="toc"><div class="toctitle">Contents</div><ul>%s</ul></div>' % lis


def infobox_html(page):
    ib = page.get("infobox")
    if not ib:
        return ""
    rows = "".join("<tr><th>%s</th><td>%s</td></tr>" % (k, v) for k, v in ib)
    title = page.get("infobox_title", page["title"])
    return '<aside class="infobox"><div class="ibtitle">%s</div><table>%s</table></aside>' % (title, rows)


def seealso_html(page):
    sa = page.get("seealso")
    if not sa:
        return ""
    lis = "".join('<li><a href="%s">%s</a> &mdash; %s</li>' % (h, t, d) for h, t, d in sa)
    return '<section class="seealso"><h2>See also</h2><ul>%s</ul></section>' % lis


PAGE_TPL = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow, noarchive">
<meta name="author" content="Anonymous">
<meta name="description" content="{desc}">
<title>{title} &mdash; NH-Calib algorithm wiki</title>
<link rel="stylesheet" href="wiki.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<button class="navtoggle" aria-controls="sidenav" aria-expanded="false">Contents menu</button>
<div class="shell">
<div id="sidenav">{nav}</div>
<main id="main">
<article class="page">
<div class="crumbs">{crumbs}</div>
<h1>{title}</h1>
{infobox}
<p class="tagline">{tagline}</p>
{toc}
{body}
{seealso}
<div class="pagefoot">
<span>Compiled from the project design note and the manuscript. Last updated {updated}.</span>
<span>Numeric values are reference-implementation defaults unless the page states otherwise.</span>
</div>
</article>
</main>
</div>
<script>
(function(){{
  var b=document.querySelector('.navtoggle'), s=document.getElementById('sidenav');
  if(!b||!s){{return;}}
  b.addEventListener('click',function(){{
    var open=s.classList.toggle('open');
    b.setAttribute('aria-expanded', open?'true':'false');
  }});
}})();
</script>
</body>
</html>
"""


def build(pages, updated="September 2026"):
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for p in pages:
        htmlstr = PAGE_TPL.format(
            title=p["title"],
            desc=esc(p.get("desc", p.get("tagline", ""))),
            tagline=p.get("tagline", ""),
            nav=nav_html(p["slug"]),
            crumbs=p.get("crumbs", "Algorithm wiki"),
            infobox=infobox_html(p),
            toc=toc_html(p["blocks"]) if p.get("toc", True) else "",
            body=render_blocks(p["blocks"]),
            seealso=seealso_html(p),
            updated=updated,
        )
        (OUT / p["slug"]).write_text(htmlstr, encoding="utf-8")
        written.append(p["slug"])
    return written
