@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m tools.inventory_checker.app
) else (
    python -m tools.inventory_checker.app
)

pause
