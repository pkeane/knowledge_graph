#!/usr/bin/env python3
"""List docs that nothing links to (no [[wikilink]] and no frontmatter reference)."""

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


def main():
    all_ids = set()
    referenced = set()

    for path in DOCS.rglob("*.md"):
        if path.name.startswith("_"):
            continue
        m = FRONTMATTER.match(path.read_text())
        if not m:
            continue
        meta = yaml.safe_load(m.group(1)) or {}
        body = m.group(2)
        if meta.get("id"):
            all_ids.add(meta["id"])
        for field in ID_FIELDS:
            for ref in meta.get(field) or []:
                referenced.add(ref)
        for link in WIKILINK.findall(body):
            referenced.add(link)

    orphans = sorted(all_ids - referenced)
    if orphans:
        print("Orphans (no incoming links):")
        for o in orphans:
            print(f"  {o}")
    else:
        print("No orphans.")


if __name__ == "__main__":
    main()
