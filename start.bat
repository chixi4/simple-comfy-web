@echo off
cd /d "%~dp0"
setlocal

echo ========================================
echo   zImage - Text to Image MVP
echo ========================================
echo.

:: Default config
if not defined APP_PORT set "APP_PORT=8000"
if not defined AUTH_TOKEN set "AUTH_TOKEN=changeme"
if not defined COMFY_BASE set "COMFY_BASE=http://127.0.0.1:8188"
if not defined WORKFLOW_PATH set "WORKFLOW_PATH=workflow.json"

:: Show config
echo [Config]
echo   Port: %APP_PORT%
echo   Token: %AUTH_TOKEN%
echo   ComfyUI: %COMFY_BASE%
echo.

:: Create directories
if not exist "generated" (
    echo [Setup] Creating generated directory...
    mkdir generated
)

:: Check Python
echo [Check] Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [Error] Python not found. Please install Python and add to PATH.
    goto :fail
)

:: Check dependencies
echo [Check] Python dependencies...
python -m pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [Setup] Installing Python dependencies...
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo [Error] Failed to install dependencies.
        goto :fail
    )
)

:: Check cloudflared
echo [Check] Cloudflared...
set "CLOUDFLARED="
if exist "cloudflared-windows-amd64.exe" (
    set "CLOUDFLARED=cloudflared-windows-amd64.exe"
) else (
    if exist "cloudflared.exe" set "CLOUDFLARED=cloudflared.exe"
)

echo.
echo ========================================
echo   Starting Services
echo ========================================
echo.

:: Start named tunnel if config exists
if defined CLOUDFLARED (
    if exist "cloudflared-config.yml" (
        echo [Start] Named tunnel your-domain.example.com ...
        start "Cloudflared Tunnel" cmd /k ""%CLOUDFLARED%" tunnel --config cloudflared-config.yml run zimage"
        timeout /t 3 /nobreak >nul
    ) else (
        echo [Info] No cloudflared-config.yml found, skipping tunnel.
    )
) else (
    echo [Info] Cloudflared not found, skipping tunnel.
)

echo.
echo [Start] FastAPI server...
echo [Info] Local URL: http://localhost:%APP_PORT%
echo [Info] Public URL: https://your-domain.example.com
echo [Info] Press Ctrl+C to stop
echo.

:: Start FastAPI server
python -m uvicorn server:app --host 0.0.0.0 --port %APP_PORT%
if errorlevel 1 goto :fail

goto :eof

:fail
echo.
echo [Error] Something went wrong.
pause
exit /b 1
