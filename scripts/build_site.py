#!/usr/bin/env python3
"""Build a static HTML site from the knowledge graph.

Reads docs/**/*.md, writes site/ with one page per doc plus an index.
Requires: pip3 install pyyaml markdown
"""

import html
import re
import shutil
import subprocess
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
:root { --fg: #2a2520; --muted: #7a7068; --accent: #6b3a2a; --bg: #f5f0e8; --card: #faf8f3; --border: #d8d0c4; }
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
header { border-bottom: 2px solid #2a2520; margin-bottom: 1.5em; padding-bottom: .8em; }
header a { color: var(--fg); text-decoration: none; }
header nav { font-size: .9em; color: var(--muted); margin-top: .3em; }
header nav a { margin-right: .8em; }
h1 { margin: 0; font-size: 1.9em; letter-spacing: -.02em; }
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
    "topic": "Topics",
    "event": "Events",
}
TYPE_ORDER = ["thinker", "school", "concept", "topic", "event"]


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


def extract_teaser(body):
    """Extract first paragraph after the # heading as a teaser."""
    lines = body.strip().split("\n")
    para_lines = []
    past_heading = False
    for line in lines:
        if not past_heading:
            if line.startswith("# "):
                past_heading = True
            continue
        stripped = line.strip()
        if not stripped:
            if para_lines:
                break
            continue
        if stripped.startswith("#") or stripped.startswith("- ") or stripped.startswith("---"):
            if para_lines:
                break
            continue
        para_lines.append(stripped)
    teaser = " ".join(para_lines)
    teaser = WIKILINK.sub(lambda m: m.group(2) or m.group(1), teaser)
    if len(teaser) > 280:
        teaser = teaser[:277].rsplit(" ", 1)[0] + "…"
    return teaser


def render_index(docs):
    import json as _json

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

    all_entries = []
    for doc_id, doc in docs.items():
        meta = doc["meta"]
        all_entries.append({
            "id": doc_id,
            "name": meta.get("name", doc_id),
            "type": meta.get("type", ""),
            "meta": meta_line(meta),
            "tags": meta.get("tags") or [],
            "teaser": extract_teaser(doc["body"]),
        })
    entries_json = _json.dumps(all_entries, ensure_ascii=False)

    index_css = """
.front-page { margin-bottom: 2em; }
.front-controls { display: flex; align-items: center; gap: .8em; margin-bottom: 1.2em; }
.front-date { color: var(--muted); font-size: .85em; font-style: italic; }
.shuffle-btn { background: var(--card); border: 1px solid var(--border); padding: .3em .8em; border-radius: 4px; cursor: pointer; font-family: inherit; font-size: .85em; color: var(--muted); }
.shuffle-btn:hover { border-color: var(--accent); color: var(--accent); }
.headline-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.2em; margin-bottom: 1.2em; }
.card { background: var(--card); border: 1px solid var(--border); border-radius: 4px; padding: 1em 1.2em; }
.card a.card-title { font-size: 1.15em; font-weight: bold; color: var(--accent); text-decoration: none; }
.card a.card-title:hover { text-decoration: underline; }
.card .card-type { font-size: .72em; text-transform: uppercase; letter-spacing: .08em; margin-bottom: .3em; font-weight: bold; }
.card .card-type.type-thinker { color: #6b3a2a; }
.card .card-type.type-topic { color: #2a5a3a; }
.card .card-type.type-school { color: #3a4a6b; }
.card .card-type.type-concept { color: #5a4a2a; }
.card .card-type.type-event { color: #5a2a4a; }
.card.ctype-thinker { border-left: 3px solid #6b3a2a; }
.card.ctype-topic { border-left: 3px solid #2a5a3a; }
.card.ctype-school { border-left: 3px solid #3a4a6b; }
.card.ctype-concept { border-left: 3px solid #5a4a2a; }
.card.ctype-event { border-left: 3px solid #5a2a4a; }
.card .card-meta { font-size: .82em; color: var(--muted); font-style: italic; margin-top: .2em; }
.card .card-teaser { font-size: .88em; color: var(--fg); margin-top: .5em; line-height: 1.45; }
.card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1em; }
.card-grid .card { padding: .8em 1em; }
.card-grid .card a.card-title { font-size: 1em; }
.card-grid .card .card-teaser { display: none; }
@media (max-width: 900px) { .headline-row { grid-template-columns: 1fr; } .card-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 600px) { .card-grid { grid-template-columns: 1fr; } }
.full-index { margin-top: 2em; }
.full-index summary { cursor: pointer; font-size: 1.1em; font-weight: bold; color: var(--fg); padding: .5em 0; }
.full-index summary:hover { color: var(--accent); }
.full-index[open] #filter { margin-top: 1em; }
"""

    js = """
const ENTRIES = """ + entries_json + """;
const TYPE_LABELS = {thinker: 'Thinker', school: 'School', concept: 'Concept', topic: 'Topic', event: 'Event'};

function mulberry32(a) {
  return function() {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    var t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }
}

function dateSeed() {
  const d = new Date();
  return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
}

function shuffle(arr, rng) {
  const a = arr.slice();
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function renderCard(e, showTeaser) {
  const card = document.createElement('div');
  card.className = 'card ctype-' + e.type;
  let h = '<div class="card-type type-' + e.type + '">' + (TYPE_LABELS[e.type] || '') + '</div>';
  h += '<a class="card-title" href="' + e.id + '.html">' + escHtml(e.name) + '</a>';
  if (e.meta) h += '<div class="card-meta">' + escHtml(e.meta) + '</div>';
  if (showTeaser && e.teaser) h += '<div class="card-teaser">' + escHtml(e.teaser) + '</div>';
  card.innerHTML = h;
  return card;
}

function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function renderFrontPage(seed) {
  const rng = mulberry32(seed);
  const picked = shuffle(ENTRIES, rng);
  const headlines = picked.slice(0, 3);
  const grid = picked.slice(3, 12);

  const container = document.getElementById('front-cards');
  container.innerHTML = '';

  const headRow = document.createElement('div');
  headRow.className = 'headline-row';
  headlines.forEach(e => headRow.appendChild(renderCard(e, true)));
  container.appendChild(headRow);

  const gridDiv = document.createElement('div');
  gridDiv.className = 'card-grid';
  grid.forEach(e => gridDiv.appendChild(renderCard(e, false)));
  container.appendChild(gridDiv);
}

let currentSeed = dateSeed();
renderFrontPage(currentSeed);

document.getElementById('shuffle-btn').addEventListener('click', function() {
  currentSeed = Math.floor(Math.random() * 2147483647);
  renderFrontPage(currentSeed);
});

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
if (tag) {
  filter.value = tag; apply(tag);
  document.getElementById('full-index').open = true;
}
"""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Knowledge Graph</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}{index_css}</style>
</head><body>
<header>
<h1>Knowledge Graph</h1>
<div class="meta">Political, social, economic, and philosophical thought, with branches into the arts and non-Western traditions.</div>
<nav><a href="about/">About</a><a href="tags/">Tags</a><a href="changelog/">Change Log</a></nav>
</header>
<div class="front-page">
<div class="front-controls">
<button id="shuffle-btn" class="shuffle-btn">Shuffle</button>
<span class="front-date">{len(docs)} entries</span>
</div>
<div id="front-cards"></div>
</div>
<details class="full-index" id="full-index">
<summary>Full Index</summary>
<input id="filter" type="search" placeholder="Filter by name or tag…">
{"".join(sections)}
</details>
<footer>{len(docs)} entries</footer>
<script>{js}</script>
</body></html>"""


def render_tags(docs):
    counts = defaultdict(int)
    for doc in docs.values():
        for t in doc["meta"].get("tags") or []:
            counts[t] += 1
    items = "".join(
        f'<li><a href="../index.html?tag={html.escape(t)}">#{html.escape(t)}</a> '
        f'<span class="tag-count">({n})</span></li>'
        for t, n in sorted(counts.items())
    )
    extra_css = ".tag-list { list-style: none; padding: 0; columns: 4; column-gap: 2em; } "\
                ".tag-list li { margin: .2em 0; break-inside: avoid; } "\
                ".tag-count { color: var(--muted); font-size: .85em; } "\
                "@media (max-width: 900px) { .tag-list { columns: 3; } } "\
                "@media (max-width: 600px) { .tag-list { columns: 2; } }"
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Tags — Knowledge Graph</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}{extra_css}</style>
</head><body>
<header>
<a href="../index.html"><strong>Knowledge Graph</strong></a>
<nav><a href="../about/">About</a><a href="../tags/">Tags</a><a href="../changelog/">Change Log</a></nav>
</header>
<h1>Tags</h1>
<div class="meta">{len(counts)} tags across {len(docs)} entries. Click a tag to filter the index.</div>
<ul class="tag-list">{items}</ul>
</body></html>"""


def render_changelog(docs):
    result = subprocess.run(
        ["git", "log", "--diff-filter=A", "--name-only", "--format=%ai"],
        capture_output=True, text=True, cwd=ROOT
    )
    doc_dirs = {
        "docs/thinkers/": "Thinker",
        "docs/concepts/": "Concept",
        "docs/topics/": "Topic",
        "docs/schools/": "School",
        "docs/events/": "Event",
    }
    type_labels = {"thinker": "Thinker", "school": "School", "concept": "Concept", "topic": "Topic", "event": "Event"}
    raw_entries = []
    current_date = None
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line[0].isdigit() and len(line) > 10 and line[4] == "-":
            current_date = line
        elif line.endswith(".md"):
            for prefix in doc_dirs:
                if line.startswith(prefix):
                    doc_id = line.replace(prefix, "").replace(".md", "")
                    if doc_id in docs:
                        raw_entries.append((current_date, doc_id))
                    break
    earliest = {}
    for date, doc_id in raw_entries:
        if doc_id not in earliest or date < earliest[doc_id]:
            earliest[doc_id] = date
    entries = []
    for doc_id, date in earliest.items():
        name = docs[doc_id]["meta"].get("name", doc_id)
        doc_type = type_labels.get(docs[doc_id]["meta"].get("type", ""), "")
        entries.append((date, doc_id, name, doc_type))
    from itertools import groupby
    groups = []
    for dt, items in groupby(entries, key=lambda x: x[0]):
        items = list(items)
        groups.append((dt, items))
    groups.sort(key=lambda g: g[0], reverse=True)
    rows = []
    for dt, items in groups:
        date_str = dt.split(" ")[0] + " " + dt.split(" ")[1][:5]
        parts = []
        for _, doc_id, name, doc_type in sorted(items, key=lambda x: x[2]):
            label = f' <span style="color:var(--muted);font-size:.85em">({doc_type})</span>' if doc_type != "Thinker" else ""
            parts.append(f'<a href="../{html.escape(doc_id)}.html">{html.escape(name)}</a>{label}')
        names = ", ".join(parts)
        rows.append(f"<tr><td>{html.escape(date_str)}</td><td>{names}</td></tr>")
    extra_css = (
        ".changelog-table { width: 100%; border-collapse: collapse; } "
        ".changelog-table th, .changelog-table td { padding: .4em .8em; border-bottom: 1px solid var(--border); text-align: left; vertical-align: top; } "
        ".changelog-table th { font-weight: 600; } "
        ".changelog-table td:first-child { white-space: nowrap; width: 10em; color: var(--muted); font-size: .9em; } "
    )
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>Change Log — Knowledge Graph</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}{extra_css}</style>
</head><body>
<header>
<a href="../index.html"><strong>Knowledge Graph</strong></a>
<nav><a href="../about/">About</a><a href="../tags/">Tags</a><a href="../changelog/">Change Log</a></nav>
</header>
<h1>Change Log</h1>
<div class="meta">Entries added to the graph, most recent first. {len(entries)} additions across {len(groups)} commits.</div>
<table class="changelog-table">
<tr><th>Date / Time</th><th>Additions</th></tr>
{"".join(rows)}
</table>
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
    tags_dir = SITE / "tags"
    tags_dir.mkdir()
    (tags_dir / "index.html").write_text(render_tags(docs))
    changelog_dir = SITE / "changelog"
    changelog_dir.mkdir()
    (changelog_dir / "index.html").write_text(render_changelog(docs))

    print(f"Built {len(docs)} pages + index → {SITE}")
    print(f"Open: file://{SITE}/index.html")


if __name__ == "__main__":
    main()
