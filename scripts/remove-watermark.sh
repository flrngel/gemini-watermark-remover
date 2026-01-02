#!/bin/bash

# Gemini Watermark Remover - Quick Action Script
# Copy the contents of this script into Automator

UV_PATH="$HOME/.local/bin/uv"
PROJECT_DIR="/Users/flrngel/project/personal/misc/gemini-watermark-remover"

for f in "$@"; do
    cd "$PROJECT_DIR"
    "$UV_PATH" run gwr process "$f"
done

osascript -e 'display notification "Watermark removal complete" with title "GWR"'
