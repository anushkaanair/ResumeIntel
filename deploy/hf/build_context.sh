#!/bin/sh
# Assemble the Space repo contents in $1 (default ./.hf-space). Does not touch the main repo.
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-$ROOT/.hf-space}"
rm -rf "$OUT" && mkdir -p "$OUT"
cp "$ROOT/pyproject.toml" "$OUT/"
cp -R "$ROOT/src" "$OUT/src"
find "$OUT/src" -name __pycache__ -type d -prune -exec rm -rf {} +
cp "$ROOT/deploy/hf/Dockerfile" "$ROOT/deploy/hf/start.sh" "$OUT/"
cp "$ROOT/deploy/hf/SPACE_README.md" "$OUT/README.md"
echo "$OUT"
