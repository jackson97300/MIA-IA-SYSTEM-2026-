@echo off
:: MIA BOT - STATUS

title MIA - STATUS

echo.
echo ================================================================
echo            STATUS DU BOT MIA
echo ================================================================
echo.

cd /d D:\MIA_IA_system

:: PROCESSUS PYTHON
echo ----------------------------------------------------------------
echo  PROCESSUS PYTHON EN COURS
echo ----------------------------------------------------------------

for /f %%a in ('tasklist /FI "IMAGENAME eq python.exe" 2^>nul ^| find /c "python"') do set COUNT=%%a

if "%COUNT%"=="0" (
    echo   Aucun processus Python en cours
    echo   STATUS: [X] BOT ARRETE
) else (
    echo   Nombre de processus: %COUNT%
    echo.
    echo   Details:
    tasklist /FI "IMAGENAME eq python.exe" /FO TABLE
    echo.
    echo   STATUS: [OK] BOT EN COURS
)
echo.

:: FICHIER PID
echo ----------------------------------------------------------------
echo  FICHIER PID
echo ----------------------------------------------------------------

if exist "logs\bot.pid" (
    set /p PID=<logs\bot.pid
    echo   PID enregistre: %PID%
) else (
    echo   Fichier PID: Non trouve
)
echo.

:: HEARTBEAT
echo ----------------------------------------------------------------
echo  HEARTBEAT
echo ----------------------------------------------------------------

if exist "logs\heartbeat.json" (
    echo   Fichier: logs\heartbeat.json
    echo.
    echo   Contenu:
    type "logs\heartbeat.json"
    echo.
) else (
    echo   Heartbeat: Non trouve
)
echo.

:: DERNIERS LOGS
echo ----------------------------------------------------------------
echo  DERNIERS LOGS (5 lignes)
echo ----------------------------------------------------------------

:: Trouver le dernier fichier log
for /f "delims=" %%f in ('dir /b /o-d "logs\__main__*.log" 2^>nul') do (
    echo   Fichier: logs\%%f
    echo.
    powershell -Command "Get-Content 'logs\%%f' -Tail 5"
    goto :done_logs
)
echo   Aucun fichier log trouve

:done_logs
echo.

echo ================================================================
echo  Commandes disponibles:
echo ----------------------------------------------------------------
echo  START_BOT.bat   - Demarrer le bot
echo  STOP_BOT.bat    - Arreter le bot
echo  STATUS_BOT.bat  - Ce status
echo  LOGS_BOT.bat    - Voir les logs en temps reel
echo  RESTART_BOT.bat - Restart complet
echo ================================================================
echo.

pause
