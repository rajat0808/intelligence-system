#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-.}"
export ENVIRONMENT="${ENVIRONMENT:-production}"

PORT="${PORT:-8000}"
uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
