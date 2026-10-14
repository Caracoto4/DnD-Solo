@echo off
REM Запуск backend DnD Solo (Windows)
REM Требует: Python 3.12+ (пакеты установлены через pip --user)
chcp 65001 >nul
cd /d "%~dp0"
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
