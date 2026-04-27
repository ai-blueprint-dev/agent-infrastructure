@echo off
REM Agent Infrastructure Dashboard — local launcher (Windows).
REM
REM Binds to 127.0.0.1, which means ONLY this machine can reach the
REM dashboard. Other devices on your network cannot. To expose to your
REM LAN, change --host to 0.0.0.0 (only do this if you trust everyone
REM on your network — the dashboard reads from your ~/.claude/ folder).

cd /d %~dp0
start "" http://127.0.0.1:8501
python -m uvicorn server:app --host 127.0.0.1 --port 8501
