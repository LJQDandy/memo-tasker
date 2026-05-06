@echo off
setlocal

cd /d "%~dp0"

set "PYTHONW_PATH=c:/Users/danli12/OneDrive - IKEA/Documents/Notebooks/workspace/mall-agent-mvp/.venv/Scripts/pythonw.exe"
set "PYTHON_PATH=c:/Users/danli12/OneDrive - IKEA/Documents/Notebooks/workspace/mall-agent-mvp/.venv/Scripts/python.exe"

if exist "%PYTHONW_PATH%" (
    start "" "%PYTHONW_PATH%" main.py
    exit /b 0
)

if exist "%PYTHON_PATH%" (
    start "" "%PYTHON_PATH%" main.py
    exit /b 0
)

echo 未找到 Python 解释器：
echo %PYTHONW_PATH%
echo %PYTHON_PATH%
pause