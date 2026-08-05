@echo off
cd /d "%~dp0"
python -m tools.definition_editor.app
if errorlevel 1 pause
