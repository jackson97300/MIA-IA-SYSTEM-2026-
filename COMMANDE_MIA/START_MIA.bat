@echo off
REM ============================================
REM  SCRIPT DE LANCEMENT RAPIDE MIA BOT
REM  Double-cliquez pour lancer le bot
REM ============================================

echo.
echo  ========================================
echo       MIA TRADING BOT - LANCEMENT
echo  ========================================
echo.

cd /d D:\MIA_IA_system

REM Vérifier si Python tourne déjà
tasklist /FI "IMAGENAME eq python.exe" 2>NUL | find /I "python.exe" >NUL
if %ERRORLEVEL%==0 (
    echo [WARNING] Python deja en cours d'execution!
    echo Voulez-vous arreter les processus existants? (O/N^)
    choice /C ON /N /M "Choix: "
    if errorlevel 2 goto :launch
    if errorlevel 1 (
        echo Arret des processus Python...
        taskkill /F /IM python.exe >NUL 2>&1
        timeout /t 2 /nobreak >NUL
    )
)

:launch
echo.
echo [INFO] Lancement du watchdog MIA...
echo.

"C:\Program Files\Python313\python.exe" "D:\MIA_IA_system\LAUNCH\mia_watchdog.py"

pause
