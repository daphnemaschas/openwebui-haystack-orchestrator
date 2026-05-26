#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PIPE_DIR="$ROOT_DIR/pipelines/src"
BUILD_SCRIPT="$PIPE_DIR/build_agent.py"
if [[ ! -f "$BUILD_SCRIPT" ]]; then
  echo "Missing $BUILD_SCRIPT" >&2
  exit 1
fi

uv run python "$BUILD_SCRIPT"
docker compose up -d

echo "Hayhooks is running at http://localhost:1416"
echo "Chainlit is running at http://localhost:8000"
