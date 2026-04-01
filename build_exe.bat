@echo off
setlocal
chcp 65001 > nul
set PYTHONUTF8=1

set "PYTHON_EXE="
set LOGO_IMG=logo\logo.png
set LOGO_ICO=logo\logo.ico

for /f "delims=" %%I in ('py -3.13 -c "import sys; print(sys.executable)" 2^>nul') do (
    if not defined PYTHON_EXE set "PYTHON_EXE=%%I"
)
if not defined PYTHON_EXE (
    for /f "delims=" %%I in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do (
        if not defined PYTHON_EXE set "PYTHON_EXE=%%I"
    )
)
if not defined PYTHON_EXE (
    for /f "delims=" %%I in ('where python 2^>nul') do (
        if /I not "%%~fI"=="%LocalAppData%\Microsoft\WindowsApps\python.exe" if not defined PYTHON_EXE set "PYTHON_EXE=%%~fI"
    )
)

if not defined PYTHON_EXE (
    echo Khong tim thay Python thuc thi. Vui long cai Python va dam bao lenh ^`py^` hoac ^`python^` hoat dong.
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo Python khong duoc tim thay tai %PYTHON_EXE%
    exit /b 1
)

echo Su dung Python: %PYTHON_EXE%

if not exist "%LOGO_IMG%" (
    echo Khong tim thay file logo tai %LOGO_IMG%
    exit /b 1
)

if exist "dist\BSRv1.0.exe" del /f /q "dist\BSRv1.0.exe"
if exist "dist\BSRv1.0" rmdir /s /q "dist\BSRv1.0"
if exist "build\BSRv1.0" rmdir /s /q "build\BSRv1.0"
if exist "build\ToolDoiSoatSaoKe" rmdir /s /q "build\ToolDoiSoatSaoKe"

"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Cai dat requirements that bai.
    exit /b 1
)
echo Dang tao file icon tu %LOGO_IMG%
"%PYTHON_EXE%" -c "from pathlib import Path; from PySide6.QtGui import QImage; src = Path(r'%CD%') / r'%LOGO_IMG%'; dst = Path(r'%CD%') / r'%LOGO_ICO%'; image = QImage(str(src)); raise SystemExit(0 if (not image.isNull() and image.save(str(dst))) else 1)"
if errorlevel 1 (
    echo Khong the tao file icon %LOGO_ICO%
    exit /b 1
)

"%PYTHON_EXE%" -m PyInstaller --noconfirm --onefile --windowed --name BSRv1.0 --clean --icon "%LOGO_ICO%" --add-data "logo;logo" main.py
if errorlevel 1 (
    echo Build exe that bai.
    exit /b 1
)

echo.
echo File exe nam trong thu muc dist\BSRv1.0.exe
endlocal
