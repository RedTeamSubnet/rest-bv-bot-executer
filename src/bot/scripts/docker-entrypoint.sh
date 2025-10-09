#!/bin/bash
set -euo pipefail

echo "INFO: Running bot docker-entrypoint.sh..."

# Activate virtual environment and run the bot script
cd /app
source venv/bin/activate
exec python -u main.py
