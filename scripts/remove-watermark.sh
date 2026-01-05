#!/bin/bash

# Gemini Watermark Remover - Quick Action Script
# Copy the contents of this script into Automator

LOG="/tmp/gwr-debug.log"
exec > "$LOG" 2>&1
set -x

echo "Starting at $(date)"
echo "Arguments: $@"

UV_PATH="$HOME/.local/bin/uv"
PROJECT_DIR="/Users/flrngel/project/personal/misc/gemini-watermark-remover"

for f in "$@"; do
    echo "Processing: $f"
    cd "$PROJECT_DIR"
    # -r flag for recursive directory processing
    "$UV_PATH" run gwr process "$f" -r
done

osascript -e 'display notification "Watermark removal complete" with title "GWR"'
