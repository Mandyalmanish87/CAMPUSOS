@echo off
setlocal enabledelayedexpansion
title CampusOS — NIT Hamirpur

echo.
echo  ============================================================
echo               CampusOS v2.0  - NIT Hamirpur
echo  ============================================================
echo.
echo  Starting CampusOS Server...
echo  Press Ctrl+C to stop.
echo.

:: ---- Find Python ----
set PY=
for %%p in (
    "C:\Users\mandy\AppData\Local\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "python"
) do (
    if not defined PY (
        %%p --version >nul 2>&1 && set "PY=%%~p"
    )
)

if not defined PY (
    echo  [ERROR] Python was not found in PATH or standard directories.
    pause
    exit /b 1
)

:: Project directory
cd /d "%~dp0"

:: ---- Check Ollama (Optional for Gemma AI) ----
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:11434/ 2>nul | findstr "200" >nul
if errorlevel 1 (
    echo  [INFO] Ollama server is offline. AI features will show offline fallback.
    echo         Run 'ollama serve' in another terminal to enable Gemma AI.
) else (
    echo  [OK] Ollama is active on port 11434 - Gemma AI ready.
)

echo.
echo  CampusOS is running at: http://127.0.0.1:8000
echo.

:: Launch browser
start "" "http://127.0.0.1:8000"

:: Launch pure-Python HTTP & REST server
%PY% server.py 8000

echo.
echo  Server stopped.
pause
