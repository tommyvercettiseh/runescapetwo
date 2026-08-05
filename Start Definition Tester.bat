@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Virtuele omgeving niet gevonden: .venv
    echo Start eerst de normale setup van RuneScape Two.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m tools.definition_tester.app
if errorlevel 1 pause
