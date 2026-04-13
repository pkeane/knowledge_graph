# Knowledge Graph: Political / Social / Economic / Philosophical Thought

A personal learning resource covering roughly the last 200–300 years of Western thought — the sort of territory covered by Alan Ryan's *On Politics*.

## Structure

```
docs/
  thinkers/    People (philosophers, economists, political theorists)
  schools/     Movements and traditions (utilitarianism, marxism, etc.)
  concepts/    Ideas (social contract, negative liberty, etc.)
  events/      Historical moments (French Revolution, 1848, etc.)
scripts/       Tools for validating and exploring the graph
```

Each document is a Markdown file with YAML frontmatter plus a 50–300 word summary. Documents link to each other using `[[wiki-style links]]` matching the `id` field of the target doc.

## Frontmatter schema

```yaml
---
id: mill-js                      # unique, kebab-case, matches filename
type: thinker                    # thinker | school | concept | event
name: John Stuart Mill           # display name
born: 1806
died: 1873
era: 19th century                # or decade/century for non-people
nationality: British
tags: [liberalism, utilitarianism, ethics]
related: [bentham-jeremy, harriet-taylor-mill]
influenced_by: [bentham-jeremy, tocqueville-alexis]
influenced: [rawls-john, berlin-isaiah]
---
```

Not all fields apply to every type — use what fits. For `school`/`concept`/`event`, replace `born/died` with `era` or date ranges.

## Linking

Inside the prose, reference other docs by id: `[[bentham-jeremy]]` or with alt text `[[bentham-jeremy|Bentham]]`.

## Viewing the graph

Open this folder in [Obsidian](https://obsidian.md) for a visual graph view out of the box. Plain text means it also works fine in any editor.

## Scripts

All scripts use the project venv. First time:

```
python3 -m venv venv
./venv/bin/pip install pyyaml markdown
```

Then:

- `./venv/bin/python scripts/build_site.py` — generate `site/` (one HTML page per doc, plus a filterable index)
- `./venv/bin/python scripts/validate_links.py` — flags broken `[[links]]` and missing `related` targets
- `./venv/bin/python scripts/list_orphans.py` — finds docs no one links to

Open `site/index.html` in a browser. The index has a live filter-by-name-or-tag box. Every doc page shows incoming backlinks, related ids, and influence chains as clickable sidebars. Broken `[[links]]` (to not-yet-written docs) render in dashed red so you can see what's missing.
