@echo off
echo ========================================
echo   zImage - Named Tunnel (your-domain.example.com)
echo ========================================
echo.

set CF=cloudflared-windows-amd64.exe

echo [Info] Starting tunnel to your-domain.example.com
echo [Info] Make sure the server is running on port 8000
echo [Info] Press Ctrl+C to stop
echo.

%CF% tunnel --config cloudflared-config.yml run zimage

pause
