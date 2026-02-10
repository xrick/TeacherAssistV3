#!/bin/bash
# TXT2PPTX - Stop server
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/.uvicorn.pid"
PORT="${PORT:-8000}"

stopped=false

# Try PID file first
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "Stopped TXT2PPTX server (PID $PID)"
        stopped=true
    fi
    rm -f "$PID_FILE"
fi

# Fallback: find process by port
if [ "$stopped" = false ]; then
    PID=$(lsof -ti:"$PORT" 2>/dev/null)
    if [ -n "$PID" ]; then
        kill $PID
        echo "Stopped process on port $PORT (PID $PID)"
        stopped=true
    fi
fi

if [ "$stopped" = false ]; then
    echo "No TXT2PPTX server is running."
else
    echo "Done."
fi
