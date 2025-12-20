@echo off
:: MIA BOT - DEMARRAGE (VERSION ROBUSTE)
:: Le bot tourne en arriere-plan, insensible aux clics

title MIA - START BOT

echo.
echo ================================================================
echo            DEMARRAGE DU BOT MIA
echo            (Mode arriere-plan - insensible aux clics)
echo ================================================================
echo.

cd /d D:\MIA_IA_system

:: ETAPE 1: Verification si deja en cours
echo [1/4] Verification des processus existants...
for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set COUNT=%%a

if not "%COUNT%"=="0" (
    echo       [!] %COUNT% processus Python deja en cours!
    echo.
    choice /C ON /M "      Voulez-vous les arreter et relancer"
    if errorlevel 2 (
        echo       Annulation du demarrage.
        pause
        exit /b
    )
    echo       Arret des processus existants...
    taskkill /F /IM python.exe >nul 2>&1
    timeout /t 3 /nobreak >nul
) else (
    echo       Aucun processus Python en cours. OK!
)
echo.

:: ETAPE 2: Creer dossier logs
echo [2/4] Preparation...
if not exist "logs" mkdir logs

:: ETAPE 3: Lancer le bot EN ARRIERE-PLAN
echo [3/4] Demarrage du bot MIA en arriere-plan...

:: Methode: PowerShell lance Python de maniere detachee
powershell -Command "Start-Process python -ArgumentList 'LAUNCH\launch_production_CLEAN_v2.py' -WorkingDirectory 'D:\MIA_IA_system' -WindowStyle Hidden"

echo       Bot lance en arriere-plan (pas de fenetre visible)
echo       Le bot continue meme si vous fermez cette fenetre!

:: Attendre le demarrage
echo       Attente 5 secondes...
timeout /t 5 /nobreak >nul

:: ETAPE 4: Verification du demarrage
echo [4/4] Verification du demarrage...

:: Compter processus
for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set RUNNING=%%a

:: Verifier le PID
if exist "logs\bot.pid" (
    for /f %%p in (logs\bot.pid) do echo       PID: %%p
) else (
    echo       [!] Fichier PID en cours de creation...
)

:: Verifier heartbeat
if exist "logs\heartbeat.json" (
    echo       Heartbeat: OK
) else (
    echo       [!] Heartbeat en cours de creation...
)

echo.
echo ================================================================
if not "%RUNNING%"=="0" (
    echo   [OK] BOT DEMARRE EN ARRIERE-PLAN !
    echo ----------------------------------------------------------------
    echo   Processus Python: %RUNNING%
    echo.
    echo   Le bot tourne EN ARRIERE-PLAN:
    echo   - Pas de fenetre visible
    echo   - Insensible aux clics
    echo   - Continue meme si vous fermez cette fenetre
    echo.
    echo   Pour voir les logs: LOGS_BOT.bat
    echo   Pour voir le status: STATUS_BOT.bat
    echo   Pour arreter: STOP_BOT.bat
) else (
    echo   [X] ERREUR: Le bot n'a pas demarre
    echo ----------------------------------------------------------------
    echo   Verifiez les logs pour plus de details
)
echo ================================================================
echo.

pause
