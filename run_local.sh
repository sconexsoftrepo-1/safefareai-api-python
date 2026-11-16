#!/usr/bin/env bash
# Local run on http://127.0.0.1:8000  (Swagger: http://127.0.0.1:8000/docs)
set -e
[ -d venv ] && source venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
