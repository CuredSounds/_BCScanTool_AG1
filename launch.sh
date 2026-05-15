#!/bin/bash
# BC Scan Tool Launch Script

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "===================================================="
echo "  BC Scan Tool - Launcher"
echo "===================================================="

# Check for virtual environment
if [ -d ".venv" ]; then
    echo "Using virtual environment (.venv)"
    source .venv/bin/activate
fi

# Run environment check
python3 scripts/setup_env.py

# Prompt to launch
echo -n "Do you want to launch the GUI? (y/n): "
read -r answer
if [[ "$answer" =~ ^[Yy]$ ]]; then
    python3 scripts/launch.py
fi
