@echo off
echo ========================================
echo    Cloudflare Tunnel - MIA Dashboard
echo    Exposition publique du dashboard
echo ========================================
echo.
echo Dashboard local: http://localhost:8503
echo Dashboard public: https://mia-ia-system.com
echo.
echo Le tunnel va rester actif jusqu'a fermeture...
echo.

REM Rafraichir le PATH
set "PATH=%PATH%;%LOCALAPPDATA%\cloudflared"

REM Lancer le tunnel
cloudflared tunnel run mia-dashboard

pause
