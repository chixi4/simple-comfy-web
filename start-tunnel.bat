@echo off
setlocal

echo ========================================
echo   zImage - Cloudflared Tunnel Only
echo ========================================
echo.

:: Set port
if "%APP_PORT%"=="" set APP_PORT=8000

:: Check cloudflared
set CLOUDFLARED=
if exist "cloudflared-windows-amd64.exe" (
    set CLOUDFLARED=cloudflared-windows-amd64.exe
) else if exist "cloudflared.exe" (
    set CLOUDFLARED=cloudflared.exe
)

if not defined CLOUDFLARED (
    echo [Error] Cloudflared executable not found.
    echo Please put cloudflared-windows-amd64.exe in this directory.
    pause
    exit /b 1
)

echo [Info] Starting tunnel to port %APP_PORT%
echo [Info] Public URL will be shown below (*.trycloudflare.com)
echo [Info] Share this URL with users who need access
echo [Info] Press Ctrl+C to stop
echo.
echo ========================================
echo.

%CLOUDFLARED% tunnel --url http://localhost:%APP_PORT%

endlocal
pause
