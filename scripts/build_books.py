#!/usr/bin/env python3
"""Render books.md to site/books/index.html with relative links to thinker pages.

Also auto-appends a bibliography of every *Key works* entry across all graph
thinkers, merged with every *Secondary sources* entry across all graph pages
(thinkers, schools, concepts, events), plus a curated list of related works
whose authors are not yet in the graph.
"""
import html as htmlmod
import re
from collections import defaultdict
from itertools import groupby
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "books.md"
DOCS = ROOT / "docs"
OUT_DIR = ROOT / "site" / "books"
OUT = OUT_DIR / "index.html"

OUT_DIR.mkdir(parents=True, exist_ok=True)

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
KEY_WORKS = re.compile(r"##\s+Key works[^\n]*\n(.*?)(?=\n##\s+|\Z)", re.DOTALL)
SEC_SOURCES = re.compile(r"##\s+Secondary sources[^\n]*\n(.*?)(?=\n##\s+|\Z)", re.DOTALL)
WORK_LINE = re.compile(r"-\s+(.+?)\s+\((\d{4})[^)]*\)\s*$")
SEC_LINE_LINKED = re.compile(
    r"-\s+\[\[([a-z0-9-]+)\|([^\]]+)\]\],\s+\*([^*]+?)\*\s+\((\d{4})[^)]*\)"
)
SEC_LINE_PLAIN = re.compile(
    r"-\s+([^,\[*][^,]*?),\s+\*([^*]+?)\*\s+\((\d{4})[^)]*\)"
)


def extract_key_works(body):
    m = KEY_WORKS.search(body)
    if not m:
        return []
    out = []
    seen = set()
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        mm = WORK_LINE.match(line)
        if not mm:
            continue
        title = re.sub(r"\*+", "", mm.group(1)).strip()
        year = mm.group(2)
        key = (title.lower(), year)
        if key in seen:
            continue
        seen.add(key)
        out.append((title, year))
    out.sort(key=lambda w: w[1])
    return out


def extract_secondary(body):
    m = SEC_SOURCES.search(body)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        ml = SEC_LINE_LINKED.match(line)
        if ml:
            out.append({
                "author_id": ml.group(1),
                "author_name": ml.group(2).strip(),
                "title": ml.group(3).strip(),
                "year": ml.group(4),
            })
            continue
        mp = SEC_LINE_PLAIN.match(line)
        if mp:
            out.append({
                "author_id": None,
                "author_name": mp.group(1).strip(),
                "title": mp.group(2).strip(),
                "year": mp.group(3),
            })
    return out


def author_sort_key(author_id, display_name):
    if author_id:
        return (0, author_id.lower())
    surname = display_name.split()[-1].lower() if display_name else ""
    return (0, f"{surname}-{display_name.lower()}")


def build_bibliography():
    TYPE_ORDER_BIB = ["thinker", "school", "concept", "event"]
    TYPE_LABELS_BIB = {
        "thinker": "Thinkers",
        "school": "Schools & Movements",
        "concept": "Concepts",
        "event": "Events",
    }

    # subject_id -> {display, type, primary: [...], secondary: [...]}
    # primary item: {title, year}
    # secondary item: {author_id, author_name, title, year}
    subjects = {}

    for path in sorted(DOCS.rglob("*.md")):
        text = path.read_text()
        m = FRONTMATTER.match(text)
        if not m:
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
        doc_id = meta.get("id") or path.stem
        subject_name = meta.get("name") or path.stem
        doc_type = meta.get("type") or "thinker"

        primary = []
        if doc_type == "thinker":
            for title, year in extract_key_works(body):
                primary.append({"title": title, "year": year})

        secondary = extract_secondary(body)

        if primary or secondary:
            subjects[doc_id] = {
                "display": subject_name,
                "type": doc_type,
                "primary": primary,
                "secondary": secondary,
            }

    def subject_sort_key(doc_id, entry):
        # Thinkers by id (usually surname-first); others by display.
        if entry["type"] == "thinker":
            return (0, doc_id.lower())
        return (0, entry["display"].lower())

    groups_by_type = defaultdict(list)

    for doc_id, entry in subjects.items():
        lines = []

        if entry["primary"]:
            primary_sorted = sorted(entry["primary"], key=lambda w: (w["year"], w["title"].lower()))
            for w in primary_sorted:
                lines.append(
                    f'<li><em>{htmlmod.escape(w["title"])}</em> ({w["year"]})</li>'
                )

        if entry["secondary"]:
            # Dedup secondary by (title lower, year).
            seen = set()
            sec_unique = []
            for s in entry["secondary"]:
                k = (s["title"].lower(), s["year"])
                if k in seen:
                    continue
                seen.add(k)
                sec_unique.append(s)
            sec_sorted = sorted(sec_unique, key=lambda s: (s["year"], s["title"].lower()))
            if entry["primary"]:
                lines.append('<li class="bib-subhead">Secondary</li>')
            for s in sec_sorted:
                if s["author_id"]:
                    author_html = (
                        f'<a href="../{s["author_id"]}.html">{htmlmod.escape(s["author_name"])}</a>'
                    )
                else:
                    author_html = htmlmod.escape(s["author_name"])
                lines.append(
                    f'<li>{author_html}, <em>{htmlmod.escape(s["title"])}</em> ({s["year"]})</li>'
                )

        head = (
            f'<a href="../{doc_id}.html">{htmlmod.escape(entry["display"])}</a>'
        )
        groups_by_type[entry["type"]].append(
            (subject_sort_key(doc_id, entry),
             f'<div class="bib-author">{head}<ul>{"".join(lines)}</ul></div>')
        )

    groups_html_parts = []
    for t in TYPE_ORDER_BIB:
        items = groups_by_type.get(t, [])
        if not items:
            continue
        items.sort(key=lambda x: x[0])
        groups_html_parts.append(
            f'<h3 class="bib-type">{TYPE_LABELS_BIB[t]}</h3>'
            f'<div class="bib">{"".join(g[1] for g in items)}</div>'
        )
    groups_html = "".join(groups_html_parts)

    # Curated related works whose authors are not (yet) in the graph.
    related = [
        ("Matthew Desmond", "Evicted", "2016"),
        ("Matthew Desmond", "Poverty, by America", "2023"),
        ("Pope Francis", "Laudato Si'", "2015"),
        ("Heather McGhee", "The Sum of Us", "2021"),
        ("Walter Rodney", "How Europe Underdeveloped Africa", "1972"),
        ("Audrey Tang", "Plurality", "2024"),
        ("Eric Williams", "Capitalism and Slavery", "1944"),
        ("Howard Zinn", "A People's History of the United States", "1980"),
        ("Ethan Zuckerman", "Mistrust", "2020"),
    ]
    related.sort(key=lambda r: (r[0].split()[-1].lower(), r[2]))

    related_groups = []
    for author, author_works in groupby(related, key=lambda r: r[0]):
        works_html = "".join(
            f'<li><em>{htmlmod.escape(title)}</em> ({year})</li>'
            for _, title, year in author_works
        )
        related_groups.append(
            f'<div class="bib-author">'
            f'<span class="bib-name">{htmlmod.escape(author)}</span>'
            f'<ul>{works_html}</ul>'
            f'</div>'
        )

    return (
        f'{groups_html}'
        f'<h3 class="bib-type">Related works (authors not in the graph)</h3>'
        f'<div class="bib">{"".join(related_groups)}</div>'
    )


src = SRC.read_text()


def linkify_pipe(m):
    return f"[{m.group(2)}](../{m.group(1)}.html)"


def linkify_plain(m):
    return f"[{m.group(1)}](../{m.group(1)}.html)"


src = re.sub(r"\[\[([a-z0-9-]+)\|([^\]]+)\]\]", linkify_pipe, src)
src = re.sub(r"\[\[([a-z0-9-]+)\]\]", linkify_plain, src)

body = markdown.markdown(src, extensions=["extra"])
body += build_bibliography()

CSS = """
html { font-size: 125%; }
body { font-family: Georgia, 'Iowan Old Style', serif; max-width: 1100px; margin: 2em auto; padding: 0 1.2em; color: #222; background: #fdfcf8; line-height: 1.55; }
h1, h2, h3 { border-bottom: 1px solid #e4e0d6; padding-bottom: .2em; }
h3 { margin-top: 1.8em; }
a { color: #8b2e2e; }
a:hover { text-decoration: none; }
code { background: #f4f1ea; padding: 0 .3em; border-radius: 3px; }
nav.breadcrumb { font-size: .9em; color: #666; margin-bottom: 1em; }
nav.breadcrumb a { color: #666; }
.bib { margin-top: 1em; }
.bib-author { margin: .9em 0; padding-bottom: .4em; border-bottom: 1px dotted #e4e0d6; }
.bib-author > a, .bib-author > .bib-name { font-weight: bold; }
.bib-author > .bib-name { color: #222; }
.bib-author ul { list-style: none; padding-left: 1.2em; margin: .2em 0 0; }
.bib-author ul li { padding: .08em 0; color: #444; }
.bib-on { color: #666; font-size: .9em; }
.bib-subhead { list-style: none; margin-left: -1em; font-variant: small-caps; color: #888; font-size: .85em; letter-spacing: .05em; margin-top: .3em; }
h3.bib-type { margin-top: 2em; font-size: 1.05em; color: #555; }
@media (max-width: 600px) { html { font-size: 110%; } body { margin: 1em auto; } }
"""

html = (
    '<!doctype html><html lang="en"><head>'
    '<meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    '<title>Reading List — Knowledge Graph</title>'
    f'<style>{CSS}</style>'
    '</head><body>'
    '<nav class="breadcrumb"><a href="../index.html">← Knowledge Graph</a></nav>'
    f'{body}'
    '</body></html>'
)

OUT.write_text(html)
print(f"Wrote {OUT.relative_to(ROOT)}")
