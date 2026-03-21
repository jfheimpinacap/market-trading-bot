#!/usr/bin/env bash
set -euo pipefail

docker compose up -d postgres redis

echo "Infrastructure started: postgres + redis"
echo "Next steps:"
echo "  1) cd apps/backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt"
echo "  2) cd apps/frontend && npm install"
