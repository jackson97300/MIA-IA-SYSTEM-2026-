@echo off
cls

echo ================================================================
echo                RESTART MIA
echo ================================================================
echo.

cd /d D:\MIA_IA_system

echo  Arret...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 3 /nobreak >nul

echo  Relancement...
call COMMANDE_MIA\START_MIA_VISIBLE.bat
