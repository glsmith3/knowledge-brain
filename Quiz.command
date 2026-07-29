#!/bin/zsh
# Double-clickable launcher for a Knowledge Brain review session (macOS).
# Drag this file to the right side of your Dock for one-click sessions.
cd "$(dirname "$0")"
python3 quiz.py
echo ""
echo "Session over — you can close this window."
