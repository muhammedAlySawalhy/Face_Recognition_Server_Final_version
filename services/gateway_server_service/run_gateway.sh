#!/bin/bash
# Run Gateway Service (Server)
# This script starts the websocket server that handles client connections

echo "Starting Gateway Service..."

# Wait for RabbitMQ to become reachable before starting the service.
python3 - <<'PY'
import os
import socket
import time
from urllib.parse import urlparse

rmq_url = os.environ.get("RMQ_URL", "rmq_Server:5672")
if "://" not in rmq_url:
    rmq_url = f"amqp://{rmq_url}"
parsed = urlparse(rmq_url)
host = parsed.hostname or "rmq_Server"
port = parsed.port or 5672
timeout = int(os.environ.get("RMQ_WAIT_TIMEOUT", "120"))
interval = int(os.environ.get("RMQ_WAIT_INTERVAL", "5"))
deadline = time.time() + timeout

while True:
    try:
        with socket.create_connection((host, port), timeout=5):
            break
    except OSError:
        if time.time() >= deadline:
            raise SystemExit(
                f"RabbitMQ at {host}:{port} did not become reachable within {timeout} seconds"
            )
        print(f"Waiting for RabbitMQ at {host}:{port}...", flush=True)
        time.sleep(interval)
PY

# Set Python path to include the project root
export PYTHONPATH="$(pwd):$PYTHONPATH"

python3 gateway_server.py
