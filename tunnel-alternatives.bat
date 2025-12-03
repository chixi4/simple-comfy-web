@echo off
echo ========================================
echo   zImage - Alternative Tunnel Options
echo ========================================
echo.
echo Cloudflare tunnel failed? Try these alternatives:
echo.
echo [Option 1] Retry Cloudflare with proxy
echo   set HTTPS_PROXY=http://127.0.0.1:YOUR_PROXY_PORT
echo   cloudflared-windows-amd64.exe tunnel --url http://localhost:8000
echo.
echo [Option 2] Use ngrok (https://ngrok.com)
echo   1. Download ngrok from https://ngrok.com/download
echo   2. Sign up and get auth token
echo   3. Run: ngrok http 8000
echo.
echo [Option 3] Use cpolar (Chinese friendly, https://www.cpolar.com)
echo   1. Download from https://www.cpolar.com
echo   2. Sign up and login: cpolar authtoken YOUR_TOKEN
echo   3. Run: cpolar http 8000
echo.
echo [Option 4] Use localtunnel (no signup needed)
echo   1. Install Node.js
echo   2. Run: npx localtunnel --port 8000
echo.
echo ========================================
pause
