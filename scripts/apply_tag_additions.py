#!/usr/bin/env python3
"""Apply tag-additions.txt: add tags to existing entries."""
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = ROOT / "tag-additions.txt"
DOCS = ROOT / "docs"
FM = re.compile(r"^(---\n)(.*?)(\n---\n)(.*)$", re.DOTALL)


def load_additions():
    adds = defaultdict(list)
    for line in MAP_FILE.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        doc_id, tags = line.split(":", 1)
        for t in tags.split(","):
            t = t.strip()
            if t:
                adds[doc_id.strip()].append(t)
    return adds


def main():
    adds = load_additions()
    # Build id -> path
    paths = {}
    for p in DOCS.rglob("*.md"):
        text = p.read_text()
        m = FM.match(text)
        if not m:
            continue
        fm_body = m.group(2)
        id_match = re.search(r"^id:\s*(\S+)", fm_body, re.MULTILINE)
        if id_match:
            paths[id_match.group(1)] = p
        else:
            paths[p.stem] = p

    changed = 0
    missing = []
    for doc_id, new_tags in adds.items():
        if doc_id not in paths:
            missing.append(doc_id)
            continue
        p = paths[doc_id]
        text = p.read_text()
        m = FM.match(text)
        if not m:
            continue
        fm_body = m.group(2)
        tags_match = re.search(r"^tags:\s*\[([^\]]*)\]", fm_body, re.MULTILINE)
        if tags_match:
            current = [t.strip() for t in tags_match.group(1).split(",") if t.strip()]
            merged = list(current)
            for t in new_tags:
                if t not in merged:
                    merged.append(t)
            if merged == current:
                continue
            new_line = "tags: [" + ", ".join(merged) + "]"
            new_fm = fm_body[:tags_match.start()] + new_line + fm_body[tags_match.end():]
        else:
            new_line = "tags: [" + ", ".join(new_tags) + "]"
            new_fm = fm_body + "\n" + new_line
        p.write_text(m.group(1) + new_fm + m.group(3) + m.group(4))
        changed += 1
    print(f"Updated {changed} files")
    if missing:
        print(f"Missing ids: {missing}")


if __name__ == "__main__":
    main()
