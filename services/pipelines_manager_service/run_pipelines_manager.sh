#!/bin/bash
# Run Pipeline Manager Service
# This script starts the pipeline manager that coordinates all processing pipelines

echo "Starting Pipeline Manager Service..."

# Set Python path to include the project root
export PYTHONPATH="$(pwd):$PYTHONPATH"

python3 pipelines_manager.py
