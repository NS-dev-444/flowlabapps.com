#!/bin/bash
# Installs the repo's git hooks. Hooks live in .git/, which is not tracked,
# so this has to be run once per clone.
cd "$(git rev-parse --show-toplevel)" || exit 1
cp _build/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "installed .git/hooks/pre-commit"
