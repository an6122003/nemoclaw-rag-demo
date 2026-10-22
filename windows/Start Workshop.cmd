@echo off
rem Double-click to start the workshop (the desktop shortcut does the same).
rem Closing the window that opens stops the workshop app.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
