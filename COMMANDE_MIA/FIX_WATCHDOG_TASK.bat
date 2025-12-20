@echo off
REM ============================================
REM  CORRECTION TACHE PLANIFIEE MIA_Watchdog
REM  EXECUTER EN TANT QU'ADMINISTRATEUR !
REM ============================================

echo.
echo  ========================================
echo   FIX MIA_Watchdog - TACHE PLANIFIEE
echo  ========================================
echo.

REM Vérifier les droits admin
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERREUR] Ce script doit etre execute en tant qu'administrateur!
    echo.
    echo Clic droit sur ce fichier ^> "Executer en tant qu'administrateur"
    echo.
    pause
    exit /b 1
)

echo [INFO] Suppression de l'ancienne tache...
schtasks /delete /tn "MIA_Watchdog" /f 2>NUL

echo [INFO] Creation de la nouvelle tache avec le bon chemin Python...
schtasks /create /tn "MIA_Watchdog" /tr "\"C:\Program Files\Python313\python.exe\" \"D:\MIA_IA_system\LAUNCH\mia_watchdog.py\"" /sc onstart /delay 0001:00 /ru "%USERNAME%" /rl highest /it

if %ERRORLEVEL%==0 (
    echo.
    echo [OK] Tache MIA_Watchdog mise a jour avec succes!
    echo.
    echo Le bot demarrera automatiquement 1 minute apres le demarrage de Windows.
    echo.
    echo Pour lancer manuellement:
    echo   schtasks /run /tn "MIA_Watchdog"
    echo   OU double-cliquez sur START_MIA.bat
) else (
    echo.
    echo [ERREUR] Echec de la creation de la tache.
)

echo.
pause
