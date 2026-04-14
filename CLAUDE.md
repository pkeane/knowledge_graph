# knowledge_graph

Personal markdown knowledge graph of ~200–300 years of Western political, social, economic, philosophical, and theological thought. Modeled loosely on the territory of Alan Ryan's *On Politics*, extended into psychology, theology, American literature, civil rights, and contemporary critics. Curated around Peter's `~/VALUES.md`: regulated capitalism, strong public sector, Sermon-on-the-Mount Christianity, affinity with Black American Christianity, anti-racism/sexism, attention to the voiceless, moral complexity ("good and evil intertwined").

## Layout

- `docs/thinkers/` `docs/schools/` `docs/concepts/` `docs/events/` — entries, ~50–300 words, plain markdown with YAML frontmatter
- `docs/_template.md` — frontmatter template
- `scripts/build_site.py` — static site generator (markdown + pyyaml). Renders to `site/`. Wikilinks pointing at non-existent ids render as dashed red — they're intentional TODOs, not bugs.
- `scripts/validate_links.py`, `scripts/list_orphans.py` — link checkers
- `scripts/publish.sh` — rebuild + force-push `site/` subtree to `gh-pages` and push `main`
- `values-review.md` / `values-review.html` — analysis of who maps to Peter's values + suggested additions
- `venv/` — python3 venv (PEP 668 requires it on this Mac)

## Frontmatter

```yaml
---
id: kebab-case-matches-filename
type: thinker | school | concept | event
name: Display Name
born: 1900            # or omit
died: 1980            # omit if living
era: 20th century
nationality: ...
tags: [tag1, tag2]
related: [other-id, ...]
influenced_by: [...]
influenced: [...]
---
```

## Conventions

- Entry length: typically 200–400 words for thinkers, less for concepts/events. Two or three substantive paragraphs, then `## Key themes` (or `## Key ideas`) and `## Key works` lists.
- Link generously via `[[id]]` to related docs. When adding a new entry that connects to existing ones, also update *their* `related` / `influenced_by` / `influenced` arrays.
- Forward references are fine — broken `[[links]]` are visible TODOs.
- ids are kebab-case `lastname-firstname` for thinkers (e.g. `du-bois-web`, `forman-james-jr`).
- No emojis. Serious-prose register; the site uses Georgia serif on a cream background.

## Workflow

```bash
# add/edit entries under docs/
./venv/bin/python scripts/build_site.py     # rebuild site/
./scripts/publish.sh                         # commit, push main, deploy gh-pages
```

## Hosting

- Repo: https://github.com/pkeane/kg (public; renamed from `knowledge_graph` in April 2026, GitHub redirects the old URL)
- Pages: https://pkeane.github.io/kg/ (served from `gh-pages` branch root, populated by `git subtree split` of `site/`)
- Default branch: `main`. `site/` is committed (not gitignored) so the subtree split has something to publish.

## Style of summaries

Look at `docs/thinkers/du-bois-web.md`, `thurman-howard.md`, `berry-wendell.md`, `morrison-toni.md` for the established voice — confident, biographical, locates the figure in their tradition, names the central books and the central ideas, willing to make an evaluative claim. Avoid hagiography; avoid dismissiveness; assume an intelligent general reader.
