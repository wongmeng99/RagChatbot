#!/usr/bin/env bash
# Run all code quality checks. Exit non-zero if any check fails.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Formatting check (black)"
uv run black --check backend/ main.py

echo ""
echo "All checks passed."
