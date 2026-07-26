@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -m venv .venv || goto :error
call ".venv\Scripts\activate.bat" || goto :error
python -m pip install --quiet --disable-pip-version-check -r requirements.txt || goto :error
python -m tools.colour_tester.app
exit /b 0
:error
echo Colour Tester kon niet worden gestart.
pause
exit /b 1
