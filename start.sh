#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PIPE_DIR="$ROOT_DIR/pipelines/src"
if [[ ! -f "$PIPE_DIR/agent_wrapper.py" ]]; then
  echo "Missing $PIPE_DIR/agent_wrapper.py" >&2
  exit 1
fi

docker compose up -d

echo "OpenWebUI is running at http://localhost:3000"
