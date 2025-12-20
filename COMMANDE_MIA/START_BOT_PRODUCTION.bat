@echo off
:: MIA BOT - DEMARRAGE EN MODE PRODUCTION
:: Active test_mode=False pour respecter les restrictions horaires

title MIA - START BOT (MODE PRODUCTION)
chcp 65001 >nul

echo.
echo ================================================================
echo       DEMARRAGE DU BOT MIA - MODE PRODUCTION
echo ================================================================
echo.
echo   Ce mode respecte les RESTRICTIONS HORAIRES:
echo   - London:        08:00 - 11:00
echo   - US Morning:    15:50 - 17:00
echo   - LUNCH:         17:00 - 19:30 (BLOQUE)
echo   - US Power Hour: 20:00 - 21:30
echo   - Hard Stop:     21:30+
echo.

cd /d D:\MIA_IA_system

:: ETAPE 1: Arret de tous les processus Python existants
echo [1/5] Arret des processus Python existants...
for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set COUNT=%%a

if not "%COUNT%"=="0" (
    echo       %COUNT% processus Python en cours - Arret...
    taskkill /F /IM python.exe >nul 2>&1
    timeout /t 3 /nobreak >nul
    echo       Processus arretes.
) else (
    echo       Aucun processus Python en cours. OK!
)
echo.

:: ETAPE 2: Activer MODE PRODUCTION dans le fichier
echo [2/5] Activation du MODE PRODUCTION dans le code...
powershell -Command "(Get-Content 'LAUNCH\launch_production_CLEAN_v2.py') -replace 'test_mode=True.*MODE TEST.*', 'test_mode=False  # MODE PRODUCTION: Restrictions horaires ACTIVES' | Set-Content 'LAUNCH\launch_production_CLEAN_v2.py'"
echo       test_mode = False (MODE PRODUCTION active)
echo.

:: ETAPE 3: Verification du mode
echo [3/5] Verification du mode actif...
powershell -Command "Select-String -Path 'LAUNCH\launch_production_CLEAN_v2.py' -Pattern 'test_mode=' | Select-Object -First 1 -ExpandProperty Line"
echo.

:: ETAPE 4: Lancer le bot
echo [4/5] Demarrage du bot MIA en MODE PRODUCTION...
if not exist "logs" mkdir logs

:: Lancer en arriere-plan
powershell -Command "Start-Process python -ArgumentList 'LAUNCH\launch_production_CLEAN_v2.py' -WorkingDirectory 'D:\MIA_IA_system' -WindowStyle Hidden"

echo       Bot lance en arriere-plan (MODE PRODUCTION)
timeout /t 5 /nobreak >nul

:: ETAPE 5: Verification du demarrage
echo [5/5] Verification du demarrage...
for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set RUNNING=%%a

if exist "logs\bot.pid" (
    for /f %%p in (logs\bot.pid) do echo       PID: %%p
)

echo.
echo ================================================================
if not "%RUNNING%"=="0" (
    echo   [OK] BOT DEMARRE EN MODE PRODUCTION !
    echo ----------------------------------------------------------------
    echo   Mode: PRODUCTION (restrictions horaires actives)
    echo   Processus Python: %RUNNING%
    echo.
    echo   Sessions de trading:
    echo   - London:        08:00 - 11:00
    echo   - US Morning:    15:50 - 17:00
    echo   - US Power Hour: 20:00 - 21:30
    echo.
    echo   Pour passer en TEST: START_BOT_TEST.bat
    echo.
    echo   Commandes:
    echo   - LOGS_BOT.bat    : Voir les logs
    echo   - STATUS_BOT.bat  : Voir le status
    echo   - STOP_BOT.bat    : Arreter le bot
) else (
    echo   [X] ERREUR: Le bot n'a pas demarre
    echo ----------------------------------------------------------------
    echo   Verifiez les logs pour plus de details
)
echo ================================================================
echo.

pause

