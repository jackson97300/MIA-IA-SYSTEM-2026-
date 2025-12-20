@echo off
cls

echo ================================================================
echo                ARRET MIA (Bot + Watchdog)
echo ================================================================
echo.

cd /d D:\MIA_IA_system

echo  Arret de tous les processus Python...
taskkill /F /IM python.exe >nul 2>&1

if %errorlevel% == 0 (
    echo  Processus arretes avec succes
) else (
    echo  Aucun processus Python en cours
)

echo.
echo ================================================================
echo  MIA arrete!
echo ================================================================
echo.
pause
