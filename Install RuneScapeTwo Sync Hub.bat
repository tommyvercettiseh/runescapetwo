@echo off
setlocal
set "REPO=C:\Users\Hesse\Desktop\Codex\runescapetwo"
set "TARGETDIR=C:\Users\Hesse\Desktop\Codex"
set "SOURCE=%REPO%\tools\repo_sync_launcher\RunescapeTwo Sync Hub.ps1"
set "TARGETPS=%TARGETDIR%\RunescapeTwo Sync Hub.ps1"
set "TARGETBAT=%TARGETDIR%\RunescapeTwo Sync Hub.bat"

if not exist "%SOURCE%" (
    echo Sync Hub source not found:
    echo %SOURCE%
    pause
    exit /b 1
)

copy /Y "%SOURCE%" "%TARGETPS%" >nul

> "%TARGETBAT%" echo @echo off
>> "%TARGETBAT%" echo powershell.exe -NoProfile -ExecutionPolicy Bypass -STA -WindowStyle Hidden -File "%%~dp0RunescapeTwo Sync Hub.ps1"

start "" "%TARGETBAT%"
exit /b 0
