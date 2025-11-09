@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo Starting DeepFunGen...
echo.

set "UV_CMD=uv"
where %UV_CMD% >nul 2>nul
if %errorlevel% neq 0 (
  set "UV_CMD=%~dp0bin\uv.exe"
)

if not exist "%UV_CMD%" (
  echo Error: uv not found at %UV_CMD%
  echo Current directory: %CD%
  echo Script directory: %SCRIPT_DIR%
  echo Checking bin\uv.exe...
  if exist "%~dp0bin\uv.exe" (
    echo Found: %~dp0bin\uv.exe
    set "UV_CMD=%~dp0bin\uv.exe"
  ) else (
    echo Error: bin\uv.exe does not exist
    echo Please ensure bin\uv.exe exists or install uv globally.
    pause
    exit /b 1
  )
)

echo Syncing dependencies...
"%UV_CMD%" sync
if %errorlevel% neq 0 (
  echo.
  echo Error: Failed to sync dependencies
  pause
  exit /b %errorlevel%
)

echo.
echo Running DeepFunGen...
echo.
"%UV_CMD%" run main.py %*
set "EXIT_CODE=%errorlevel%"

if %EXIT_CODE% neq 0 (
  echo.
  echo Application exited with error code %EXIT_CODE%
  pause
)

exit /b %EXIT_CODE%

