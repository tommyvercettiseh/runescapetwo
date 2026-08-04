@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [RuneScape Two] Virtuele omgeving wordt aangemaakt...
  py -m venv .venv || goto :error
)

call ".venv\Scripts\activate.bat" || goto :error
python -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto :error
python -m tools.vision_tester.app
exit /b 0

:error
echo.
echo Unified Vision Tester kon niet worden gestart.
echo Controleer of Python is geinstalleerd en bekijk de melding hierboven.
pause
exit /b 1
