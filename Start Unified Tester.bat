@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found: .venv
    echo Run the normal RuneScape Two setup first.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m tools.unified_tester.scenario_editor_app
if errorlevel 1 pause
