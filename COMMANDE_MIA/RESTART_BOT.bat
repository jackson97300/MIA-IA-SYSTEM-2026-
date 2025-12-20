@echo off
:: MIA BOT - RESTART

title MIA - RESTART

echo.
echo ================================================================
echo            RESTART DU BOT MIA
echo ================================================================
echo.

cd /d D:\MIA_IA_system

:: ETAPE 1: Arreter
echo [1/3] Arret du bot...
taskkill /F /IM python.exe >nul 2>&1
if exist "logs\bot.pid" del "logs\bot.pid"
if exist "logs\heartbeat.json" del "logs\heartbeat.json"
echo       OK
timeout /t 3 /nobreak >nul

:: ETAPE 2: Verification
echo [2/3] Verification arret complet...
for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set COUNT=%%a

if not "%COUNT%"=="0" (
    echo       [!] %COUNT% processus encore en cours, nouvelle tentative...
    taskkill /F /IM python.exe >nul 2>&1
    timeout /t 2 /nobreak >nul
)
echo       OK

:: ETAPE 3: Redemarrer
echo [3/3] Demarrage du bot...
if not exist "logs" mkdir logs
start "MIA Trading Bot" python LAUNCH\launch_production_CLEAN_v2.py
echo       OK

timeout /t 5 /nobreak >nul

:: Verification finale
for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set RUNNING=%%a

echo.
echo ================================================================
if not "%RUNNING%"=="0" (
    echo   [OK] RESTART REUSSI !
    echo ----------------------------------------------------------------
    echo   Processus en cours: %RUNNING%
) else (
    echo   [X] ERREUR: Le bot n'a pas redemarre
)
echo ================================================================
echo.

pause
