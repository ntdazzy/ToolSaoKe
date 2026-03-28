@echo off
setlocal
chcp 65001 > nul
set PYTHONUTF8=1

set PYTHON_EXE=C:\Program Files\PyManager\python.exe

if not exist "%PYTHON_EXE%" (
    echo Python khong duoc tim thay tai %PYTHON_EXE%
    exit /b 1
)

"%PYTHON_EXE%" -m pip install -r requirements.txt
"%PYTHON_EXE%" -m PyInstaller --noconfirm --windowed --name ToolDoiSoatSaoKe --clean main.py

echo.
echo File exe nam trong thu muc dist\ToolDoiSoatSaoKe
endlocal
