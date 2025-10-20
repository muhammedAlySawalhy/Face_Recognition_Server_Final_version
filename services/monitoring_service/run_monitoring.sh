#!/bin/bash

set -euo pipefail

echo "Starting Monitoring Service..."

export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

uvicorn monitoring_service.app:app --host 0.0.0.0 --port "${MONITORING_PORT:-8080}"
