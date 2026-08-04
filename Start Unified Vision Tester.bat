@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_LAUNCHER="
where py >nul 2>&1 && set "PYTHON_LAUNCHER=py"
if not defined PYTHON_LAUNCHER (
  where python >nul 2>&1 && set "PYTHON_LAUNCHER=python"
)
if not defined PYTHON_LAUNCHER goto :no_python

if not exist ".venv\Scripts\python.exe" (
  echo [RuneScape Two] Virtuele omgeving wordt aangemaakt...
  %PYTHON_LAUNCHER% -m venv .venv || goto :error
)

call ".venv\Scripts\activate.bat" || goto :error
python -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto :error
python -m tools.vision_tester.app
exit /b 0

:no_python
echo Python is niet gevonden. Installeer Python en voeg het toe aan PATH.
pause
exit /b 1

:error
echo.
echo Unified Vision Tester kon niet worden gestart.
echo Controleer of Python is geinstalleerd en bekijk de melding hierboven.
pause
exit /b 1
