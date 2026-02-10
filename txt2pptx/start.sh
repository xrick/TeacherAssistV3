#!/bin/bash
# TXT2PPTX - Start server
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV="$PROJECT_ROOT/pptxenv"
PID_FILE="$SCRIPT_DIR/.uvicorn.pid"
PORT="${PORT:-8000}"

# Check if already running
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "TXT2PPTX is already running (PID $(cat "$PID_FILE"))"
    echo "Use stop.sh to stop it first."
    exit 1
fi

# Activate venv
if [ -f "$VENV/bin/activate" ]; then
    source "$VENV/bin/activate"
else
    echo "Error: Virtual environment not found at $VENV"
    echo "Create it with: python -m venv $VENV && pip install fastapi uvicorn python-pptx pydantic httpx"
    exit 1
fi

# Check Ollama
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "[OK] Ollama is running"
else
    echo "[WARN] Ollama is not reachable at localhost:11434"
    echo "       The app will fall back to demo mode."
fi

echo "========================================="
echo "  TXT2PPTX - AI 簡報生成器"
echo "  http://localhost:$PORT"
echo "========================================="

cd "$SCRIPT_DIR"
python -m uvicorn backend.main:app --host 0.0.0.0 --port "$PORT" --reload &
UVICORN_PID=$!
echo "$UVICORN_PID" > "$PID_FILE"

echo "Server started (PID $UVICORN_PID)"
echo "Run 'bash stop.sh' to stop."

wait "$UVICORN_PID"
rm -f "$PID_FILE"
