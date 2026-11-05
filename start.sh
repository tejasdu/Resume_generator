#!/bin/bash
# Resume Tailor — start script
# Usage: ./start.sh  (or double-click it)

set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

source venv/bin/activate
python app.py
