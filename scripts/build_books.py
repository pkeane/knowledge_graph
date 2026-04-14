#!/usr/bin/env python3
"""Render books.md to site/books/index.html with relative links to thinker pages.

Also auto-appends a bibliography of every *Key works* entry across all graph
thinkers, plus a curated list of related works whose authors are not yet in
the graph.
"""
import html as htmlmod
import re
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "books.md"
THINKERS = ROOT / "docs" / "thinkers"
OUT_DIR = ROOT / "site" / "books"
OUT = OUT_DIR / "index.html"

OUT_DIR.mkdir(parents=True, exist_ok=True)

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
KEY_WORKS = re.compile(r"##\s+Key works[^\n]*\n(.*?)(?=\n##\s+|\Z)", re.DOTALL)
WORK_LINE = re.compile(r"-\s+(.+?)\s+\((\d{4})[^)]*\)\s*$")


def extract_works(body):
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


def sort_key(name, doc_id):
    # doc_id is typically surname-first kebab-case; fall back to name's last token.
    return (doc_id.lower(), name.lower())


def build_bibliography():
    entries = []
    for path in THINKERS.glob("*.md"):
        text = path.read_text()
        m = FRONTMATTER.match(text)
        if not m:
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
        name = meta.get("name") or path.stem
        doc_id = meta.get("id") or path.stem
        works = extract_works(body)
        if not works:
            continue
        entries.append((sort_key(name, doc_id), name, doc_id, works))
    entries.sort()

    groups = []
    for _, name, doc_id, works in entries:
        works_html = "".join(
            f'<li><em>{htmlmod.escape(title)}</em> ({year})</li>'
            for title, year in works
        )
        groups.append(
            f'<div class="bib-author">'
            f'<a href="../{doc_id}.html">{htmlmod.escape(name)}</a>'
            f'<ul>{works_html}</ul>'
            f'</div>'
        )

    # Curated related works whose authors are not (yet) in the graph.
    related = [
        ("Michelle Alexander", "The New Jim Crow", "2010"),
        ("Ta-Nehisi Coates", "Between the World and Me", "2015"),
        ("James H. Cone", "The Cross and the Lynching Tree", "2011"),
        ("Matthew Desmond", "Evicted", "2016"),
        ("Matthew Desmond", "Poverty, by America", "2023"),
        ("Frederick Douglass", "Narrative of the Life of Frederick Douglass", "1845"),
        ("Gustavo Gutiérrez", "A Theology of Liberation", "1971"),
        ("Pope Francis", "Laudato Si'", "2015"),
        ("Heather McGhee", "The Sum of Us", "2021"),
        ("Walter Rauschenbusch", "Christianity and the Social Crisis", "1907"),
        ("Marilynne Robinson", "Gilead", "2004"),
        ("Marilynne Robinson", "Home", "2008"),
        ("Marilynne Robinson", "Lila", "2014"),
        ("Marilynne Robinson", "The Death of Adam", "1998"),
        ("Walter Rodney", "How Europe Underdeveloped Africa", "1972"),
        ("Audrey Tang", "Plurality", "2024"),
        ("Adam Tooze", "Crashed", "2018"),
        ("Cornel West", "Race Matters", "1993"),
        ("Eric Williams", "Capitalism and Slavery", "1944"),
        ("Howard Zinn", "A People's History of the United States", "1980"),
        ("Ethan Zuckerman", "Mistrust", "2020"),
    ]
    related.sort(key=lambda r: (r[0].split()[-1].lower(), r[2]))

    # Group curated related works by author.
    from itertools import groupby
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
        f'<div class="bib">{"".join(groups)}</div>'
        f'<h3>Related works (authors not in the graph)</h3>'
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
