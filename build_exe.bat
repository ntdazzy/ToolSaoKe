@echo off
setlocal
chcp 65001 > nul
set PYTHONUTF8=1

set PYTHON_EXE=C:\Program Files\PyManager\python.exe
set LOGO_IMG=logo\logo.png
set LOGO_ICO=logo\logo.ico

if not exist "%PYTHON_EXE%" (
    echo Python khong duoc tim thay tai %PYTHON_EXE%
    exit /b 1
)

if not exist "%LOGO_IMG%" (
    echo Khong tim thay file logo tai %LOGO_IMG%
    exit /b 1
)

if exist "dist\BSRv1.0.exe" del /f /q "dist\BSRv1.0.exe"
if exist "dist\BSRv1.0" rmdir /s /q "dist\BSRv1.0"
if exist "dist\ToolDoiSoatSaoKe" rmdir /s /q "dist\ToolDoiSoatSaoKe"
if exist "build\BSRv1.0" rmdir /s /q "build\BSRv1.0"
if exist "build\ToolDoiSoatSaoKe" rmdir /s /q "build\ToolDoiSoatSaoKe"

"%PYTHON_EXE%" -m pip install -r requirements.txt
echo Dang tao file icon tu %LOGO_IMG%
"%PYTHON_EXE%" -c "from pathlib import Path; from PySide6.QtGui import QImage; src = Path(r'%CD%') / r'%LOGO_IMG%'; dst = Path(r'%CD%') / r'%LOGO_ICO%'; image = QImage(str(src)); raise SystemExit(0 if (not image.isNull() and image.save(str(dst))) else 1)"
if errorlevel 1 (
    echo Khong the tao file icon %LOGO_ICO%
    exit /b 1
)

"%PYTHON_EXE%" -m PyInstaller --noconfirm --onefile --windowed --name BSRv1.0 --clean --icon "%LOGO_ICO%" --add-data "logo;logo" main.py

echo.
echo File exe nam trong thu muc dist\BSRv1.0.exe
endlocal
