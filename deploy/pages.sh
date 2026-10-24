#!/usr/bin/env bash
# Publish the static demo (recorded run, no backend) to GitHub Pages from a gh-pages branch.
# Needs the repo to be public (or a paid plan). Only the built bundle is pushed — never your main branch.
#   ./deploy/pages.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
REPO_URL="$(git remote get-url origin)"
(cd frontend && npm install --silent && VITE_DEMO=1 VITE_API_URL=/api/v1 npx vite build --base ./ --outDir dist-demo)
TMP="$(mktemp -d)"; cp -R frontend/dist-demo/. "$TMP/"; touch "$TMP/.nojekyll"
cd "$TMP"; git init -q -b gh-pages; git add -A
git -c user.name="$(git -C "$ROOT" config user.name)" -c user.email="$(git -C "$ROOT" config user.email)" commit -q -m "Publish static demo"
git push -f "$REPO_URL" gh-pages
echo "Now enable Pages: repo Settings → Pages → Branch: gh-pages / (root). Site: https://$(echo "$REPO_URL" | sed -E 's#.*github.com[:/]([^/]+)/([^/.]+).*#\1.github.io/\2#')/"
