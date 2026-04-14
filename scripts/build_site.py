#!/usr/bin/env python3
"""Build a static HTML site from the knowledge graph.

Reads docs/**/*.md, writes site/ with one page per doc plus an index.
Requires: pip3 install pyyaml markdown
"""

import html
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

try:
    import yaml
    import markdown
except ImportError:
    sys.exit("pip3 install pyyaml markdown")

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = ROOT / "site"

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
ID_FIELDS = ("related", "influenced_by", "influenced")

CSS = """
:root { --fg: #222; --muted: #666; --accent: #8b2e2e; --bg: #fdfcf8; --card: #fff; --border: #e4e0d6; }
body.period-pre-1900 { --bg: #ffffff; --card: #fafafa; --border: #e0e0e0; }
body.period-1900-1945 { --bg: #f2f7ff; --card: #f9fbff; --border: #c8d6ec; }
body.period-1946-onward { --bg: #ffffea; --card: #fffff5; --border: #e8e0a8; }
.period-swatch { display: inline-block; width: .7em; height: .7em; border-radius: 50%; margin-right: .5em; vertical-align: middle; border: 1px solid rgba(0,0,0,.2); }
.swatch-pre-1900 { background: #ffffff; }
.swatch-1900-1945 { background: #b8cee8; }
.swatch-1946-onward { background: #ffe866; }
.index-section h3.bucket.thinker-pre-1900 { background: #ffffff; padding: .4em .6em; border-left: 3px solid #bbbbbb; }
.index-section h3.bucket.thinker-1900-1945 { background: #f2f7ff; padding: .4em .6em; border-left: 3px solid #8aa8d0; }
.index-section h3.bucket.thinker-1946-onward { background: #ffffea; padding: .4em .6em; border-left: 3px solid #d9c34a; }
* { box-sizing: border-box; }
html { font-size: 125%; }
body { font-family: Georgia, 'Iowan Old Style', serif; max-width: 1100px; margin: 2em auto; padding: 0 1.2em; color: var(--fg); background: var(--bg); line-height: 1.55; }
@media (max-width: 600px) { html { font-size: 110%; } body { margin: 1em auto; } }
header { border-bottom: 1px solid var(--border); margin-bottom: 1.5em; padding-bottom: .8em; }
header a { color: var(--fg); text-decoration: none; }
header nav { font-size: .9em; color: var(--muted); margin-top: .3em; }
header nav a { margin-right: .8em; }
h1 { margin: 0; font-size: 1.9em; }
h2 { margin-top: 1.8em; border-bottom: 1px solid var(--border); padding-bottom: .2em; font-size: 1.25em; }
h3 { font-size: 1.05em; color: var(--muted); margin-top: 1.4em; }
a { color: var(--accent); }
a:hover { text-decoration: none; }
.meta { color: var(--muted); font-size: .9em; font-style: italic; margin-bottom: 1.2em; }
.tags { margin: .5em 0 1em; }
.tag { display: inline-block; font-size: .78em; background: var(--card); border: 1px solid var(--border); padding: .1em .6em; border-radius: 10px; margin-right: .3em; color: var(--muted); text-decoration: none; }
.tag:hover { border-color: var(--accent); color: var(--accent); }
.sidebar { background: var(--card); border: 1px solid var(--border); padding: .8em 1.2em; margin: 1.5em 0; border-radius: 4px; font-size: .93em; }
.sidebar h3 { margin-top: 0; font-size: .8em; text-transform: uppercase; letter-spacing: .05em; color: var(--muted); border: none; }
.sidebar ul { margin: .3em 0; padding-left: 1.2em; }
.sidebar ul li { margin: .15em 0; }
.index-section { margin-bottom: 2em; }
.index-section h3.bucket { margin: 1.2em 0 .3em; font-size: .95em; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); }
.index-section h3.bucket .bucket-count { text-transform: none; letter-spacing: 0; font-weight: normal; }
.index-section ul { list-style: none; padding: 0; columns: 2; column-gap: 2em; }
.index-section ul li { margin: .2em 0; break-inside: avoid; }
.index-section .dates { color: var(--muted); font-size: .85em; }
#filter { width: 100%; padding: .5em .7em; border: 1px solid var(--border); border-radius: 4px; font-size: 1em; margin-bottom: 1.5em; background: var(--card); font-family: inherit; }
.broken { color: #a00; border-bottom: 1px dashed #a00; text-decoration: none; }
footer { margin-top: 3em; padding-top: 1em; border-top: 1px solid var(--border); color: var(--muted); font-size: .85em; }
"""

TYPE_LABELS = {
    "thinker": "Thinkers",
    "school": "Schools & Movements",
    "concept": "Concepts",
    "event": "Events",
}
TYPE_ORDER = ["thinker", "school", "concept", "event"]


def load_docs():
    docs = {}
    for path in DOCS.rglob("*.md"):
        if path.name.startswith("_"):
            continue
        text = path.read_text()
        m = FRONTMATTER.match(text)
        if not m:
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
        doc_id = meta.get("id") or path.stem
        docs[doc_id] = {"meta": meta, "body": body, "path": path}
    return docs


def compute_backlinks(docs):
    backlinks = defaultdict(set)
    for doc_id, doc in docs.items():
        for link in WIKILINK.findall(doc["body"]):
            backlinks[link[0]].add(doc_id)
        for field in ID_FIELDS:
            for ref in doc["meta"].get(field) or []:
                backlinks[ref].add(doc_id)
    return backlinks


def render_wikilinks(body, docs):
    def sub(m):
        target, alt = m.group(1), m.group(2)
        label = alt or (docs[target]["meta"].get("name") if target in docs else target)
        if target in docs:
            return f'<a href="{target}.html">{html.escape(label)}</a>'
        return f'<span class="broken" title="Not yet written">{html.escape(label)}</span>'
    return WIKILINK.sub(sub, body)


def meta_line(meta):
    bits = []
    if meta.get("born") or meta.get("died"):
        b, d = meta.get("born", "?"), meta.get("died", "?")
        bits.append(f"{b} – {d}")
    elif meta.get("era"):
        bits.append(str(meta["era"]))
    if meta.get("nationality"):
        bits.append(str(meta["nationality"]))
    return " · ".join(bits)


def link_list(ids, docs, label):
    valid = [i for i in ids if i in docs]
    if not valid:
        return ""
    items = "".join(
        f'<li><a href="{i}.html">{html.escape(docs[i]["meta"].get("name", i))}</a></li>'
        for i in valid
    )
    return f'<h3>{label}</h3><ul>{items}</ul>'


def period_class(meta):
    if meta.get("type") != "thinker":
        return ""
    b = meta.get("born") or 0
    if b < 1900 and b > 0:
        return "period-pre-1900"
    if 1900 <= b <= 1945:
        return "period-1900-1945"
    if b >= 1946:
        return "period-1946-onward"
    return ""


def render_doc(doc_id, doc, docs, backlinks):
    meta = doc["meta"]
    name = meta.get("name", doc_id)
    body_class = period_class(meta)
    body_html = markdown.markdown(render_wikilinks(doc["body"], docs), extensions=["extra"])
    body_html = re.sub(r"<h1[^>]*>.*?</h1>", "", body_html, count=1)

    tags_html = ""
    if meta.get("tags"):
        tags_html = '<div class="tags">' + "".join(
            f'<a class="tag" href="index.html?tag={html.escape(t)}">#{html.escape(t)}</a>'
            for t in meta["tags"]
        ) + '</div>'

    sidebar_parts = [
        link_list(meta.get("related") or [], docs, "Related"),
        link_list(meta.get("influenced_by") or [], docs, "Influenced by"),
        link_list(meta.get("influenced") or [], docs, "Influenced"),
        link_list(sorted(backlinks.get(doc_id, [])), docs, "Referenced by"),
    ]
    sidebar_html = ""
    if any(sidebar_parts):
        sidebar_html = '<aside class="sidebar">' + "".join(sidebar_parts) + '</aside>'

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>{html.escape(name)}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
</head><body class="{body_class}">
<header>
<a href="index.html"><strong>Knowledge Graph</strong></a>
<nav>{"".join(f'<a href="index.html#{t}">{TYPE_LABELS[t]}</a>' for t in TYPE_ORDER)}</nav>
</header>
<h1>{html.escape(name)}</h1>
<div class="meta">{html.escape(meta_line(meta))}</div>
{tags_html}
{body_html}
{sidebar_html}
<footer>Type: {html.escape(meta.get("type", "?"))} · id: <code>{html.escape(doc_id)}</code></footer>
</body></html>"""


def render_index(docs):
    by_type = defaultdict(list)
    for doc_id, doc in docs.items():
        by_type[doc["meta"].get("type", "other")].append((doc_id, doc))

    def render_items(entries):
        items = []
        for doc_id, doc in entries:
            meta = doc["meta"]
            name = html.escape(meta.get("name", doc_id))
            dates = html.escape(meta_line(meta))
            tagstr = html.escape(" ".join(meta.get("tags") or []))
            items.append(
                f'<li data-tags="{tagstr}" data-name="{html.escape(name.lower())}">'
                f'<a href="{doc_id}.html">{name}</a>'
                f'{f" <span class=\"dates\">({dates})</span>" if dates else ""}</li>'
            )
        return f'<ul>{"".join(items)}</ul>'

    def bucket_thinkers(entries):
        buckets = [
            ("Pre-1900", "thinker-pre-1900", lambda b: b < 1900),
            ("1900–1945", "thinker-1900-1945", lambda b: 1900 <= b <= 1945),
            ("1946 onward", "thinker-1946-onward", lambda b: b >= 1946),
        ]
        for label, bid, test in buckets:
            members = [e for e in entries if test(e[1]["meta"].get("born") or 0)]
            if members:
                yield label, bid, members

    sections = []
    for t in TYPE_ORDER:
        entries = sorted(by_type.get(t, []), key=lambda x: x[1]["meta"].get("name", x[0]))
        if not entries:
            continue
        if t == "thinker":
            body = "".join(
                f'<h3 id="{bid}" class="bucket {bid}"><span class="period-swatch swatch-{bid.replace("thinker-", "")}"></span>{label} <span class="bucket-count">({len(members)})</span></h3>'
                f'{render_items(members)}'
                for label, bid, members in bucket_thinkers(entries)
            )
        else:
            body = render_items(entries)
        sections.append(
            f'<section class="index-section" id="{t}">'
            f'<h2>{TYPE_LABELS[t]} ({len(entries)})</h2>'
            f'{body}</section>'
        )

    js = """
const filter = document.getElementById('filter');
const items = document.querySelectorAll('.index-section li');
function apply(q) {
  q = q.toLowerCase().trim();
  items.forEach(li => {
    const hay = (li.dataset.name + ' ' + li.dataset.tags);
    li.style.display = !q || hay.includes(q) ? '' : 'none';
  });
}
filter.addEventListener('input', e => apply(e.target.value));
const tag = new URLSearchParams(location.search).get('tag');
if (tag) { filter.value = tag; apply(tag); }
"""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Knowledge Graph</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style>
</head><body>
<header>
<h1>Knowledge Graph</h1>
<div class="meta">Western political, social, economic, and philosophical thought — last 200–300 years</div>
<nav><a href="values/">Values review</a><a href="books/">Reading list</a></nav>
</header>
<input id="filter" type="search" placeholder="Filter by name or tag…" autofocus>
{"".join(sections)}
<footer>{len(docs)} entries</footer>
<script>{js}</script>
</body></html>"""


def main():
    docs = load_docs()
    if not docs:
        sys.exit("No docs found.")
    backlinks = compute_backlinks(docs)

    if SITE.exists():
        shutil.rmtree(SITE)
    SITE.mkdir()

    for doc_id, doc in docs.items():
        (SITE / f"{doc_id}.html").write_text(render_doc(doc_id, doc, docs, backlinks))
    (SITE / "index.html").write_text(render_index(docs))

    print(f"Built {len(docs)} pages + index → {SITE}")
    print(f"Open: file://{SITE}/index.html")


if __name__ == "__main__":
    main()
