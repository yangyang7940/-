@echo off
setlocal EnableExtensions
title Resume Matching System
cd /d "%~dp0"

echo.
echo ========================================================
echo   Intelligent Resume Matching System - Launcher
echo ========================================================
echo   Detecting Python. Please wait...
echo.

set "APP_PYTHON="

rem Check common per-user Python installation paths first.
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "APP_PYTHON=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined APP_PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "APP_PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined APP_PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "APP_PYTHON=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined APP_PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "APP_PYTHON=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
if not defined APP_PYTHON if exist "%LOCALAPPDATA%\Programs\Python\Python39\python.exe" set "APP_PYTHON=%LOCALAPPDATA%\Programs\Python\Python39\python.exe"

rem Codex local runtime fallback for this computer.
if not defined APP_PYTHON if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" set "APP_PYTHON=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if defined APP_PYTHON goto python_found

rem Try the Windows Python Launcher without relying on PATH aliases.
for /f "delims=" %%P in ('py -3 -c "import sys; print^(sys.executable^)" 2^>nul') do set "APP_PYTHON=%%P"
if defined APP_PYTHON goto python_found

rem Last fallback: accept a python command only when it really starts.
for /f "delims=" %%P in ('python -c "import sys; print^(sys.executable^)" 2^>nul') do set "APP_PYTHON=%%P"
if defined APP_PYTHON goto python_found
goto no_python

:python_found
if not exist "%APP_PYTHON%" goto no_python
echo   Python executable: %APP_PYTHON%
"%APP_PYTHON%" -c "import sys; print('  Python version: ' + sys.version.split()[0])"
if errorlevel 1 goto no_python
echo.
echo   The browser will open automatically after startup.
echo   Keep this window open. Press Ctrl+C here to stop the app.
echo.

"%APP_PYTHON%" app.py %*
set "APP_EXIT_CODE=%ERRORLEVEL%"

echo.
if "%APP_EXIT_CODE%"=="0" goto stopped_ok
echo   Startup failed. Error code: %APP_EXIT_CODE%
echo   Keep this window open and take a screenshot of the error above.
goto wait_before_close

:stopped_ok
echo   The app has stopped.

:wait_before_close
echo.
echo   Press any key to close this window...
pause >nul
exit /b %APP_EXIT_CODE%

:no_python
echo.
echo   Startup failed: no working Python installation was found.
echo   Install Python 3.9 or later and enable "Add Python to PATH".
echo   Download: https://www.python.org/downloads/
echo.
echo   Press any key to close this window...
pause >nul
exit /b 1
