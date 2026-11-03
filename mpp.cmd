@echo off
setlocal
set "HERE=%~dp0"

if not "%MPP_PYTHON%"=="" (
  "%MPP_PYTHON%" "%HERE%mpp.py" %*
  exit /b %errorlevel%
)

py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 (
  py -3 "%HERE%mpp.py" %*
  exit /b %errorlevel%
)

python -c "import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)" >nul 2>nul
if not errorlevel 1 (
  python "%HERE%mpp.py" %*
  exit /b %errorlevel%
)

echo [mpp] Python 3 not found. Install Python 3.9+ or set MPP_PYTHON.
exit /b 1
