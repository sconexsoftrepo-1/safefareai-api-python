@echo off
REM Local run on http://127.0.0.1:8000  (Swagger: http://127.0.0.1:8000/docs)
REM Needs the venv:  python -m venv venv  &&  venv\Scripts\activate  &&  pip install -r requirements.txt
call venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
