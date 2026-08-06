@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found: .venv
    echo Run the normal RuneScape Two setup first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m tools.unified_tester.inventory_app
if errorlevel 1 pause
