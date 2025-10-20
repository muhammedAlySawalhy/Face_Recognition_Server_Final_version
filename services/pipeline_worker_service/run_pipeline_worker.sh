#!/bin/bash
# Run Processing Service (Pipeline Worker)
# This script starts a pipeline worker for processing tasks

echo "Starting Pipeline Worker Service with ID: $PIPELINE_ID"

# Set Python path to include the project root
export PYTHONPATH="$(pwd):$PYTHONPATH"

python3 pipeline_worker.py
