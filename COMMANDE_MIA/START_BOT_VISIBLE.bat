@echo off
:: MIA BOT - DEMARRAGE AVEC FENETRE VISIBLE
:: Fenetre visible mais protegee contre les clics

title MIA - START BOT (Visible)

echo.
echo ================================================================
echo            DEMARRAGE DU BOT MIA
echo            (Mode visible - fenetre separee)
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

:: ETAPE 3: Lancer le bot avec fenetre visible
echo [3/4] Demarrage du bot MIA...

:: Lancer dans une nouvelle fenetre CMD
start "MIA Trading Bot - NE PAS CLIQUER DANS CETTE FENETRE" cmd /k "cd /d D:\MIA_IA_system && python LAUNCH\launch_production_CLEAN_v2.py"

echo       Fenetre du bot ouverte
echo.
echo       [!] ATTENTION: NE CLIQUEZ PAS dans la fenetre du bot!
echo       [!] Cliquer met le bot en pause (bug Windows)
echo.

:: Attendre le demarrage
echo       Attente 5 secondes...
timeout /t 5 /nobreak >nul

:: ETAPE 4: Verification du demarrage
echo [4/4] Verification du demarrage...

:: Compter processus
for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set RUNNING=%%a

echo.
echo ================================================================
if not "%RUNNING%"=="0" (
    echo   [OK] BOT DEMARRE !
    echo ----------------------------------------------------------------
    echo   Processus Python: %RUNNING%
    echo.
    echo   [!] RAPPEL: NE CLIQUEZ PAS dans la fenetre du bot!
    echo.
    echo   Pour voir le status: STATUS_BOT.bat
    echo   Pour arreter: STOP_BOT.bat
) else (
    echo   [X] ERREUR: Le bot n'a pas demarre
)
echo ================================================================
echo.

pause
