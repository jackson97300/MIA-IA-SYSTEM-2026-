@echo off
:: MIA BOT - ARRET COMPLET + VERIFICATION

title MIA - STOP BOT

echo.
echo ================================================================
echo            ARRET DU BOT MIA
echo ================================================================
echo.

cd /d D:\MIA_IA_system

:: ETAPE 1: Compter les processus AVANT
echo [1/4] Verification des processus en cours...
for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set BEFORE=%%a
echo       Processus Python detectes: %BEFORE%
echo.

:: ETAPE 2: Kill tous les processus Python
echo [2/4] Arret de tous les processus Python...
taskkill /F /IM python.exe >nul 2>&1

:: Attendre 3 secondes
echo       Attente 3 secondes...
timeout /t 3 /nobreak >nul

:: ETAPE 3: Nettoyage fichiers
echo [3/4] Nettoyage des fichiers PID et heartbeat...
if exist "logs\bot.pid" (
    del "logs\bot.pid"
    echo       bot.pid supprime
)
if exist "logs\heartbeat.json" (
    del "logs\heartbeat.json"
    echo       heartbeat.json supprime
)
echo.

:: ETAPE 4: Verification finale
echo [4/4] Verification finale...
for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set AFTER=%%a

echo.
echo ================================================================
if "%AFTER%"=="0" (
    echo   [OK] SUCCES: Tous les processus arretes
    echo ----------------------------------------------------------------
    echo   Avant: %BEFORE% processus
    echo   Apres: 0 processus
) else (
    echo   [!] ATTENTION: %AFTER% processus encore en cours
    echo ----------------------------------------------------------------
    echo   Tentative 2...
    taskkill /F /IM python.exe >nul 2>&1
    timeout /t 2 /nobreak >nul
    for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set AFTER2=%%a
    if "%AFTER2%"=="0" (
        echo   [OK] SUCCES apres 2eme tentative
    ) else (
        echo   [X] ECHEC: %AFTER2% processus resistants
        echo   Utilisez le Gestionnaire des taches
    )
)
echo ================================================================
echo.

pause
