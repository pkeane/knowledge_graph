#!/usr/bin/env bash
# Rebuild the static site and publish it to the gh-pages branch.
# Run from the repo root: ./scripts/publish.sh
set -euo pipefail

cd "$(dirname "$0")/.."

./venv/bin/python scripts/build_site.py

if ! git diff --quiet -- site || ! git diff --cached --quiet -- site; then
  git add site
  git commit -m "Rebuild site"
fi

git branch -D gh-pages-tmp 2>/dev/null || true
git subtree split --prefix site -b gh-pages-tmp
git push -f origin gh-pages-tmp:gh-pages
git branch -D gh-pages-tmp

git push origin main

echo
echo "Published → https://pkeane.github.io/knowledge_graph/"
