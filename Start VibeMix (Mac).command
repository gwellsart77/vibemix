#!/bin/bash
cd "$(dirname "$0")"
PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "Python 3 isn't installed yet. Get it from https://www.python.org/downloads/ then run this again."
  read -p "Press Enter to close."; exit 1
fi
if [ ! -d .venv-mac ] || [ ! -x .venv-mac/bin/python ]; then
  echo "First run: setting things up (about a minute)..."
  rm -rf .venv-mac
  "$PY" -m venv .venv-mac && .venv-mac/bin/python -m pip install -q --upgrade pip && .venv-mac/bin/python -m pip install -q -r requirements.txt || {
    echo "Setup failed. Check your internet connection and run this again."; read -p "Press Enter to close."; exit 1; }
fi
.venv-mac/bin/python app.py
