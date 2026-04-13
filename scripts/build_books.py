#!/usr/bin/env python3
"""Render books.md to site/books/index.html with relative links to thinker pages."""
import re
from pathlib import Path
import markdown

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "books.md"
OUT_DIR = ROOT / "site" / "books"
OUT = OUT_DIR / "index.html"

OUT_DIR.mkdir(parents=True, exist_ok=True)

src = SRC.read_text()

def linkify_pipe(m):
    return f"[{m.group(2)}](../{m.group(1)}.html)"

def linkify_plain(m):
    return f"[{m.group(1)}](../{m.group(1)}.html)"

src = re.sub(r"\[\[([a-z0-9-]+)\|([^\]]+)\]\]", linkify_pipe, src)
src = re.sub(r"\[\[([a-z0-9-]+)\]\]", linkify_plain, src)

body = markdown.markdown(src, extensions=["extra"])

CSS = """
html { font-size: 125%; }
body { font-family: Georgia, 'Iowan Old Style', serif; max-width: 1100px; margin: 2em auto; padding: 0 1.2em; color: #222; background: #fdfcf8; line-height: 1.55; }
h1, h2, h3 { border-bottom: 1px solid #e4e0d6; padding-bottom: .2em; }
a { color: #8b2e2e; }
a:hover { text-decoration: none; }
code { background: #f4f1ea; padding: 0 .3em; border-radius: 3px; }
nav.breadcrumb { font-size: .9em; color: #666; margin-bottom: 1em; }
nav.breadcrumb a { color: #666; }
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
