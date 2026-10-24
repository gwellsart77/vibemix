@echo off
cd /d "%~dp0"
set PY=
py -3 -c "import sys" >nul 2>&1 && set PY=py -3
if "%PY%"=="" ( python -c "import sys" >nul 2>&1 && set PY=python )
if "%PY%"=="" (
  echo Python 3 isn't installed yet. Get it from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" in the installer, then run this again.
  pause
  exit /b 1
)
if not exist .venv-win\Scripts\python.exe (
  echo First run: setting things up ^(about a minute^)...
  if exist .venv-win rmdir /s /q .venv-win
  %PY% -m venv .venv-win && .venv-win\Scripts\python -m pip install -q --upgrade pip && .venv-win\Scripts\python -m pip install -q -r requirements.txt
  if errorlevel 1 (
    echo Setup failed. Check your internet connection and run this again.
    pause
    exit /b 1
  )
)
.venv-win\Scripts\python app.py
pause
