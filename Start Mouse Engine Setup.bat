@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_LAUNCHER="
where py >nul 2>&1 && set "PYTHON_LAUNCHER=py"
if not defined PYTHON_LAUNCHER where python >nul 2>&1 && set "PYTHON_LAUNCHER=python"
if not defined PYTHON_LAUNCHER goto :no_python

set "NEED_INSTALL="
if not exist ".venv\Scripts\python.exe" (
  echo [RuneScape Two] Virtuele omgeving wordt aangemaakt...
  %PYTHON_LAUNCHER% -m venv .venv || goto :error
  set "NEED_INSTALL=1"
)

call ".venv\Scripts\activate.bat" || goto :error
python -c "import pynput" >nul 2>&1
if errorlevel 1 set "NEED_INSTALL=1"

if defined NEED_INSTALL (
  echo [RuneScape Two] Benodigdheden installeren...
  python -m pip install --disable-pip-version-check -r requirements.txt || goto :error
)

python -m tools.mouse_engine_setup.app
exit /b 0

:no_python
echo Python is niet gevonden. Installeer Python en voeg het toe aan PATH.
pause
exit /b 1

:error
echo.
echo Mouse Engine Setup kon niet worden gestart.
pause
exit /b 1
