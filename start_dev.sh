#!/usr/bin/env bash
set -euo pipefail

uv run alembic upgrade head
uv run python -m fantomex.server
