@echo off

REM Get current directory
set BASE_DIR=%~dp0

start "Backend" cmd /k "uvicorn app.main:app --reload --port 8000"
start "Frontend" cmd /k "cd /d %BASE_DIR%test-frontend && python -m http.server 8080"

echo.
echo Backend  running on http://localhost:8000
echo Frontend running on http://localhost:8080