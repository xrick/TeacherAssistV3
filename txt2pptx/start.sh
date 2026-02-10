#!/bin/bash
# TXT2PPTX - Start server
cd "$(dirname "$0")"
echo "========================================="
echo "  TXT2PPTX - AI 簡報生成器"
echo "  http://localhost:8000"
echo "========================================="
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
