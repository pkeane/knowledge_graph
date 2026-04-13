#!/usr/bin/env python3
"""Validate [[wiki-links]] and frontmatter id references across the knowledge graph.

Reports:
  - docs whose filename doesn't match their `id`
  - [[links]] pointing to ids that don't exist
  - `related`/`influenced_by`/`influenced` ids that don't exist
"""

import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pip3 install pyyaml")

DOCS = Path(__file__).resolve().parent.parent / "docs"
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
ID_FIELDS = ("related", "influenced_by", "influenced")


def load_docs():
    docs = {}
    for path in DOCS.rglob("*.md"):
        if path.name.startswith("_"):
            continue
        text = path.read_text()
        m = FRONTMATTER.match(text)
        if not m:
            print(f"WARN: no frontmatter in {path}")
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
        docs[path] = (meta, body)
    return docs


def main():
    docs = load_docs()
    ids = {meta.get("id") for meta, _ in docs.values() if meta.get("id")}
    errors = 0

    for path, (meta, body) in docs.items():
        doc_id = meta.get("id")
        if not doc_id:
            print(f"ERR  {path}: missing id")
            errors += 1
            continue
        if path.stem != doc_id:
            print(f"ERR  {path}: filename doesn't match id '{doc_id}'")
            errors += 1

        for field in ID_FIELDS:
            for ref in meta.get(field) or []:
                if ref not in ids:
                    print(f"ERR  {doc_id}.{field}: unknown id '{ref}'")
                    errors += 1

        for link in WIKILINK.findall(body):
            if link not in ids:
                print(f"ERR  {doc_id}: broken [[{link}]]")
                errors += 1

    print(f"\n{len(docs)} docs checked, {errors} error(s)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
