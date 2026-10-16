@echo off
title CRM API Explorer
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" goto no_venv

cls
echo ======================================================
echo               CRM API Explorer Launcher
echo ======================================================
echo.
echo   [1] Web Dashboard (Default - opens in browser)
echo   [2] Terminal Explorer
echo   [0] Exit
echo.
set "choice=1"
set /p "choice=Select an option [Default: 1]: "

:: Strip any spaces
set "choice=%choice: =%"

if "%choice%"=="1" goto dashboard
if "%choice%"=="2" goto terminal
if "%choice%"=="0" goto end

echo Invalid choice: %choice%
pause
goto end

:dashboard
echo.
echo Starting Web Dashboard at http://localhost:8501 ...
".venv\Scripts\streamlit.exe" run app.py
goto end

:terminal
echo.
".venv\Scripts\python.exe" main.py
goto end

:no_venv
echo [ERROR] Virtual environment (.venv) not found!
echo Please make sure .venv is installed in this folder.
pause
exit /b 1

:end
