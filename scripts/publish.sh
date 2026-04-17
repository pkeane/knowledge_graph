#!/usr/bin/env bash
# Rebuild the static site and publish it to the gh-pages branch.
# Run from the repo root: ./scripts/publish.sh
set -euo pipefail

cd "$(dirname "$0")/.."

./venv/bin/python scripts/build_site.py
./venv/bin/python scripts/build_about.py

git add -A docs scripts site about.md CLAUDE.md README.md .gitignore
if ! git diff --cached --quiet; then
  git commit -m "Update knowledge graph"
fi

git branch -D gh-pages-tmp 2>/dev/null || true
git subtree split --prefix site -b gh-pages-tmp
git push -f origin gh-pages-tmp:gh-pages
git branch -D gh-pages-tmp

git push origin main

echo
echo "Published → https://pkeane.github.io/kg/"
