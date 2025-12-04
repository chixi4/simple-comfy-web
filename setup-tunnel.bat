@echo off
echo ========================================
echo   zImage - Setup Cloudflare Tunnel
echo ========================================
echo.

set CF=cloudflared-windows-amd64.exe

echo [Step 1] Login to Cloudflare...
echo This will open a browser for authorization.
%CF% login
if errorlevel 1 (
    echo [Error] Login failed.
    pause
    exit /b 1
)

echo.
echo [Step 2] Create tunnel named "zimage"...
%CF% tunnel create zimage
if errorlevel 1 (
    echo [Warning] Tunnel may already exist, continuing...
)

echo.
echo [Step 3] Route DNS your-domain.example.com to tunnel...
%CF% tunnel route dns zimage your-domain.example.com
if errorlevel 1 (
    echo [Warning] DNS route may already exist, continuing...
)

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Now you need to:
echo 1. Find your tunnel ID: %CF% tunnel list
echo 2. Edit cloudflared-config.yml and replace ^<TUNNEL_ID^> with your actual tunnel ID
echo 3. Run start-tunnel-named.bat to start the tunnel
echo.
pause
