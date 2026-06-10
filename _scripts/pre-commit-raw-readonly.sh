#!/usr/bin/env bash
# Fail if any staged file modifies or renames an existing file in
# datasets/*/raw/ except allowed patterns. New files (additions) are
# permitted — ADR-004 says don't edit existing raw files, not don't
# add new ones.
# Allowed modifications: SOURCE.md, .gitignore, .gitkeep, .dvc pointers
set -eo pipefail

changed=$(git diff --cached --name-only --diff-filter=MR 2>/dev/null || true)
violations=$(echo "$changed" | grep -P '^datasets/[^/]+/raw/(?!SOURCE\.md|\.gitignore|\.gitkeep|.*\.dvc$)' || true)

if [ -n "$violations" ]; then
    echo "ERROR: raw/ files are immutable (ADR-004)." >&2
    echo "Only SOURCE.md, .gitignore, .gitkeep, and .dvc pointers may be modified in raw/." >&2
    echo "" >&2
    echo "Violating files:" >&2
    echo "$violations" >&2
    exit 1
fi