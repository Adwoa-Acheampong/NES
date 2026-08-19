@echo off
setlocal
cd /d "%~dp0\..\.."
python pipeline\supaagent\control.py
if errorlevel 1 (
  echo.
  echo SupaAgent control panel could not start.
  echo Make sure Python is installed and available as "python".
  echo.
  pause
)
