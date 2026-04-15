#!/usr/bin/env python3
"""Apply tag-merges.txt to all docs/**/*.md frontmatter."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = ROOT / "tag-merges.txt"
DOCS = ROOT / "docs"
FM = re.compile(r"^(---\n)(.*?)(\n---\n)(.*)$", re.DOTALL)


def load_map():
    mapping = {}
    for line in MAP_FILE.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or "->" not in line:
            continue
        old, new = [s.strip() for s in line.split("->", 1)]
        if new.upper().startswith("DROP-KEEP"):
            continue
        if new.upper() == "DROP":
            mapping[old] = []
        else:
            mapping[old] = [t.strip() for t in new.split(",") if t.strip()]
    return mapping


def apply_to_tags(tags, mapping):
    out = []
    seen = set()
    for t in tags:
        replacements = mapping[t] if t in mapping else [t]
        for r in replacements:
            if r not in seen:
                seen.add(r)
                out.append(r)
    return out


def main():
    mapping = load_map()
    print(f"Loaded {len(mapping)} merge rules")
    changed = 0
    for path in DOCS.rglob("*.md"):
        text = path.read_text()
        m = FM.match(text)
        if not m:
            continue
        meta = yaml.safe_load(m.group(2)) or {}
        tags = meta.get("tags") or []
        if not tags:
            continue
        new_tags = apply_to_tags(tags, mapping)
        if new_tags == tags:
            continue
        meta["tags"] = new_tags
        # Re-serialize frontmatter preserving key order as much as possible.
        # Simple approach: edit the tags line directly.
        fm_text = m.group(2)
        tags_line_re = re.compile(r"^tags:.*?(?=\n[a-zA-Z_]+:|\Z)", re.DOTALL | re.MULTILINE)
        new_tags_str = "tags: [" + ", ".join(new_tags) + "]"
        if tags_line_re.search(fm_text):
            new_fm = tags_line_re.sub(new_tags_str, fm_text, count=1)
        else:
            new_fm = fm_text + "\n" + new_tags_str
        path.write_text(m.group(1) + new_fm + m.group(3) + m.group(4))
        changed += 1
    print(f"Updated {changed} files")


if __name__ == "__main__":
    main()
