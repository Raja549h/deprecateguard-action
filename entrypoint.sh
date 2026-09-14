#!/bin/bash
set -e
export PYTHONPATH="/app"
echo "Running DeprecateGuard Scanner..."
python /app/src/cli/action_entrypoint.py
