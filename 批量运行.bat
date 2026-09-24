@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist "%~dp0photos\" (
    echo ERROR: photos folder not found.
    echo Please create a folder named photos next to this file.
    echo Put your JPG, JPEG, PNG, WEBP, BMP, TIF or TIFF files there.
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0compare.py" (
    echo ERROR: compare.py not found.
    echo.
    pause
    exit /b 1
)

where py >nul 2>nul
if not errorlevel 1 goto RUN_PY_LAUNCHER

where python >nul 2>nul
if not errorlevel 1 goto RUN_PYTHON

echo ERROR: Python was not found in PATH.
echo Install Python first, then run this file again.
echo.
pause
exit /b 1

:RUN_PY_LAUNCHER
py -3 "%~dp0compare.py" "%~dp0photos"
goto END

:RUN_PYTHON
python "%~dp0compare.py" "%~dp0photos"
goto END

:END
echo.
pause
endlocal
