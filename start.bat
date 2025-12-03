@echo off
setlocal EnableDelayedExpansion

echo ========================================
echo   zImage - Text to Image MVP
echo ========================================
echo.

:: Default config
if "%APP_PORT%"=="" set APP_PORT=8000
if "%AUTH_TOKEN%"=="" set AUTH_TOKEN=change
if "%COMFY_BASE%"=="" set COMFY_BASE=http://127.0.0.1:8188

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
    pause
    exit /b 1
)

:: Check dependencies
echo [Check] Python dependencies...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [Setup] Installing Python dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [Error] Failed to install dependencies.
        pause
        exit /b 1
    )
)

:: Check cloudflared
echo [Check] Cloudflared...
set CLOUDFLARED=
if exist "cloudflared-windows-amd64.exe" (
    set CLOUDFLARED=cloudflared-windows-amd64.exe
) else if exist "cloudflared.exe" (
    set CLOUDFLARED=cloudflared.exe
)

if not defined CLOUDFLARED (
    echo [Warning] Cloudflared not found. Starting local server only.
)

echo.
echo ========================================
echo   Starting Services
echo ========================================
echo.

:: Start cloudflared if exists
if defined CLOUDFLARED (
    echo [Start] Cloudflared tunnel...
    echo [Info] Check the new window for public URL
    start "Cloudflared Tunnel" cmd /k "%CLOUDFLARED% tunnel --url http://localhost:%APP_PORT%"
    timeout /t 3 /nobreak >nul
)

echo.
echo [Start] FastAPI server...
echo [Info] Local URL: http://localhost:%APP_PORT%
echo [Info] Press Ctrl+C to stop
echo.

:: Start FastAPI server
python -m uvicorn server:app --host 0.0.0.0 --port %APP_PORT%

endlocal
pause
