@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m tools.action_studio.app
) else (
  python -m tools.action_studio.app
)
pause
