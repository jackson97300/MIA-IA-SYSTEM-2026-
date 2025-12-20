@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM              INSTALLATION WATCHDOG MIA - TÂCHE PLANIFIÉE WINDOWS
REM ═══════════════════════════════════════════════════════════════════════════════
REM
REM Ce script crée une tâche planifiée qui:
REM 1. Démarre le watchdog au démarrage de Windows (après reboot/bluescreen)
REM 2. Le watchdog surveille et redémarre le bot si crash
REM
REM UTILISE LE WATCHDOG EXISTANT: LAUNCH\mia_watchdog.py (482 lignes, complet)
REM
REM EXÉCUTER EN ADMINISTRATEUR!
REM
REM ═══════════════════════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║     🐕 INSTALLATION WATCHDOG MIA v2.0                       ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Vérifier les droits admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ ERREUR: Ce script doit être exécuté en ADMINISTRATEUR!
    echo.
    echo    Clic droit sur le fichier ^> "Exécuter en tant qu'administrateur"
    echo.
    pause
    exit /b 1
)

echo ✅ Droits administrateur OK
echo.

REM Variables - UTILISE LE WATCHDOG EXISTANT!
set TASK_NAME=MIA_Watchdog
set MIA_DIR=D:\MIA_IA_system
set WATCHDOG_SCRIPT=%MIA_DIR%\LAUNCH\mia_watchdog.py

REM Détecter Python automatiquement
where python >nul 2>&1
if %errorLevel% equ 0 (
    for /f "delims=" %%i in ('where python') do set PYTHON_PATH=%%i
    goto :python_found
)

REM Chemins Python courants
if exist "C:\Python311\python.exe" (
    set PYTHON_PATH=C:\Python311\python.exe
    goto :python_found
)
if exist "C:\Python312\python.exe" (
    set PYTHON_PATH=C:\Python312\python.exe
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    set PYTHON_PATH=%LOCALAPPDATA%\Programs\Python\Python311\python.exe
    goto :python_found
)
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    set PYTHON_PATH=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
    goto :python_found
)

echo ❌ ERREUR: Python non trouvé!
echo    Installe Python ou modifie ce script avec le bon chemin
pause
exit /b 1

:python_found
echo ✅ Python trouvé: %PYTHON_PATH%
echo.

REM Vérifier que le script watchdog existe
if not exist "%WATCHDOG_SCRIPT%" (
    echo ❌ ERREUR: Script watchdog non trouvé!
    echo    Chemin: %WATCHDOG_SCRIPT%
    echo.
    pause
    exit /b 1
)

echo ✅ Script watchdog trouvé: %WATCHDOG_SCRIPT%
echo.

REM Supprimer l'ancienne tâche si existe
echo 🗑️ Suppression ancienne tâche (si existe)...
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

REM Créer la nouvelle tâche
echo 📝 Création de la tâche planifiée...
echo.

schtasks /create ^
    /tn "%TASK_NAME%" ^
    /tr "\"%PYTHON_PATH%\" \"%WATCHDOG_SCRIPT%\"" ^
    /sc onstart ^
    /delay 0001:00 ^
    /ru "%USERNAME%" ^
    /rl highest ^
    /f

if %errorLevel% neq 0 (
    echo.
    echo ❌ ERREUR: Impossible de créer la tâche planifiée!
    pause
    exit /b 1
)

echo.
echo ✅ Tâche planifiée créée avec succès!
echo.
echo ════════════════════════════════════════════════════════════════
echo    CONFIGURATION:
echo ════════════════════════════════════════════════════════════════
echo    Nom:        %TASK_NAME%
echo    Démarrage:  Au démarrage de Windows (délai 1 min)
echo    Script:     %WATCHDOG_SCRIPT%
echo    Python:     %PYTHON_PATH%
echo ════════════════════════════════════════════════════════════════
echo.

REM Demander si démarrer maintenant
set /p START_NOW="🚀 Démarrer le watchdog maintenant? (O/N): "
if /i "%START_NOW%"=="O" (
    echo.
    echo 🐕 Démarrage du watchdog...
    start "MIA Watchdog" "%PYTHON_PATH%" "%WATCHDOG_SCRIPT%"
    echo ✅ Watchdog démarré!
)

echo.
echo ════════════════════════════════════════════════════════════════
echo    COMMANDES UTILES:
echo ════════════════════════════════════════════════════════════════
echo    Voir la tâche:         schtasks /query /tn "%TASK_NAME%"
echo    Démarrer manuellement: schtasks /run /tn "%TASK_NAME%"
echo    Supprimer:             schtasks /delete /tn "%TASK_NAME%" /f
echo ════════════════════════════════════════════════════════════════
echo.
echo ✅ INSTALLATION TERMINÉE!
echo.
echo 📌 Le watchdog démarrera automatiquement après chaque reboot Windows
echo 📌 Il surveille le bot et le redémarre si crash
echo.
pause


