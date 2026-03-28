@echo off
setlocal
chcp 65001 > nul
set PYTHONUTF8=1

set PYTHON_EXE=C:\Program Files\PyManager\python.exe
set LOGO_JPG=logo\logo.jpg
set LOGO_ICO=logo\logo.ico

if not exist "%PYTHON_EXE%" (
    echo Python khong duoc tim thay tai %PYTHON_EXE%
    exit /b 1
)

if not exist "%LOGO_JPG%" (
    echo Khong tim thay file logo tai %LOGO_JPG%
    exit /b 1
)

"%PYTHON_EXE%" -m pip install -r requirements.txt
echo Dang tao file icon tu %LOGO_JPG%
"%PYTHON_EXE%" -c "from pathlib import Path; from PySide6.QtGui import QImage; src = Path(r'%CD%') / r'%LOGO_JPG%'; dst = Path(r'%CD%') / r'%LOGO_ICO%'; image = QImage(str(src)); raise SystemExit(0 if (not image.isNull() and image.save(str(dst))) else 1)"
if errorlevel 1 (
    echo Khong the tao file icon %LOGO_ICO%
    exit /b 1
)

"%PYTHON_EXE%" -m PyInstaller --noconfirm --windowed --name BSRv1.0 --clean --icon "%LOGO_ICO%" --add-data "logo;logo" main.py

echo.
echo File exe nam trong thu muc dist\BSRv1.0
endlocal
