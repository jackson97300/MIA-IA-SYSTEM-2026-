@echo off
chcp 65001 > nul
cls

echo ================================================================
echo                LANCEMENT MIA - MODE VISIBLE
echo ================================================================
echo.
echo  Le bot va s'ouvrir dans une nouvelle fenetre (logs visibles)
echo  Le watchdog surveille en arriere-plan
echo.
echo ================================================================

cd /d D:\MIA_IA_system

REM Arreter les anciens processus Python
echo.
echo  Arret des anciens processus...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM Lancer le bot en visible dans une nouvelle fenetre PowerShell
echo  Lancement du bot (fenetre visible)...
start "MIA BOT" powershell -NoExit -Command "cd D:\MIA_IA_system; Write-Host 'MIA BOT - Logs en direct' -ForegroundColor Cyan; Write-Host ('=' * 60); python LAUNCH/launch_production_CLEAN_v2.py"

REM Attendre que le bot demarre
timeout /t 5 /nobreak >nul

REM Lancer le watchdog en arriere-plan (fenetre minimisee)
echo  Lancement du watchdog (arriere-plan)...
start /min "MIA WATCHDOG" powershell -Command "cd D:\MIA_IA_system; python LAUNCH/mia_watchdog.py"

echo.
echo ================================================================
echo  MIA lance!
echo.
echo  Fenetre "MIA BOT" = Logs en direct
echo  Fenetre "MIA WATCHDOG" = Surveillance (minimisee)
echo.
echo  Pour arreter: STOP_MIA.bat ou fermer les fenetres
echo ================================================================
echo.
pause
