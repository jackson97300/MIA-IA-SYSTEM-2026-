@echo off
REM 🚀 MIA IA SYSTEM - Monitoring et Surveillance
REM Script de monitoring du système MIA
REM Version: Production Ready v1.0

echo ========================================
echo 📊 MONITORING MIA SYSTEM
echo ========================================
echo.

REM Configuration
set "MIA_DIR=D:\MIA_IA_system"
set "LOG_FILE=%MIA_DIR%\logs\monitoring.log"
set "ALERT_FILE=%MIA_DIR%\logs\alerts.log"

REM Créer le fichier de log s'il n'existe pas
if not exist "%MIA_DIR%\logs" mkdir "%MIA_DIR%\logs"
if not exist "%LOG_FILE%" echo. > "%LOG_FILE%"
if not exist "%ALERT_FILE%" echo. > "%ALERT_FILE%"

echo 📅 Date de vérification: %date% %time%
echo.

REM ========================================
REM VÉRIFICATION 1: PROCESSUS MIA
REM ========================================
echo 🔍 Vérification des processus MIA...

tasklist /FI "IMAGENAME eq python.exe" | find "python.exe" >nul
if errorlevel 1 (
    echo ❌ ALERTE: Aucun processus Python détecté
    echo %date% %time% - ALERTE: Aucun processus Python détecté >> "%ALERT_FILE%"
) else (
    echo ✅ Processus Python détecté
    tasklist /FI "IMAGENAME eq python.exe" | find "python.exe"
)

echo.

REM ========================================
REM VÉRIFICATION 2: SYNCING
REM ========================================
echo 🔄 Vérification de Syncthing...

sc query syncthing | find "RUNNING" >nul
if errorlevel 1 (
    echo ❌ ALERTE: Service Syncthing arrêté
    echo %date% %time% - ALERTE: Service Syncthing arrêté >> "%ALERT_FILE%"
) else (
    echo ✅ Service Syncthing en cours d'exécution
)

REM Vérifier l'interface web Syncthing
powershell -Command "& {try { $response = Invoke-WebRequest -Uri 'http://localhost:8384' -TimeoutSec 5; Write-Host '✅ Interface Syncthing accessible' } catch { Write-Host '❌ ALERTE: Interface Syncthing inaccessible' -ForegroundColor Red; echo %date% %time% - ALERTE: Interface Syncthing inaccessible >> '%ALERT_FILE%' }}"

echo.

REM ========================================
REM VÉRIFICATION 3: ESPACE DISQUE
REM ========================================
echo 💾 Vérification de l'espace disque...

for /f "tokens=3" %%a in ('dir D:\ /-c ^| find "bytes free"') do set "FREE_SPACE=%%a"
set /a "FREE_GB=%FREE_SPACE% / 1073741824"

if %FREE_GB% LSS 5 (
    echo ❌ ALERTE: Espace disque faible - %FREE_GB% GB restants
    echo %date% %time% - ALERTE: Espace disque faible - %FREE_GB% GB restants >> "%ALERT_FILE%"
) else (
    echo ✅ Espace disque suffisant - %FREE_GB% GB restants
)

echo.

REM ========================================
REM VÉRIFICATION 4: FICHIERS DE DONNÉES
REM ========================================
echo 📊 Vérification des fichiers de données...

REM Vérifier les données de trading récentes
if exist "D:\DATA_SIERRA_CHART" (
    echo ✅ Dossier DATA_SIERRA_CHART existe
    
    REM Vérifier les fichiers récents (dernières 24h)
    forfiles /p "D:\DATA_SIERRA_CHART" /s /m "*.jsonl" /d -1 >nul 2>&1
    if errorlevel 1 (
        echo ⚠️ Aucun fichier de données récent détecté
        echo %date% %time% - ATTENTION: Aucun fichier de données récent >> "%ALERT_FILE%"
    ) else (
        echo ✅ Fichiers de données récents détectés
    )
) else (
    echo ❌ ALERTE: Dossier DATA_SIERRA_CHART manquant
    echo %date% %time% - ALERTE: Dossier DATA_SIERRA_CHART manquant >> "%ALERT_FILE%"
)

echo.

REM ========================================
REM VÉRIFICATION 5: LOGS SYSTÈME
REM ========================================
echo 📝 Vérification des logs système...

if exist "%MIA_DIR%\logs" (
    echo ✅ Dossier de logs existe
    
    REM Vérifier les logs récents
    forfiles /p "%MIA_DIR%\logs" /m "*.log" /d -1 >nul 2>&1
    if errorlevel 1 (
        echo ⚠️ Aucun log récent détecté
    ) else (
        echo ✅ Logs récents détectés
    )
    
    REM Vérifier la taille des logs
    for /f %%i in ('dir "%MIA_DIR%\logs\*.log" /s /-c ^| find "bytes"') do set "LOG_SIZE=%%i"
    set /a "LOG_MB=%LOG_SIZE% / 1048576"
    
    if %LOG_MB% GTR 100 (
        echo ⚠️ Logs volumineux - %LOG_MB% MB
        echo %date% %time% - ATTENTION: Logs volumineux - %LOG_MB% MB >> "%ALERT_FILE%"
    ) else (
        echo ✅ Taille des logs acceptable - %LOG_MB% MB
    )
) else (
    echo ❌ ALERTE: Dossier de logs manquant
    echo %date% %time% - ALERTE: Dossier de logs manquant >> "%ALERT_FILE%"
)

echo.

REM ========================================
REM VÉRIFICATION 6: RÉSEAU
REM ========================================
echo 🌐 Vérification de la connectivité réseau...

REM Vérifier la connexion Internet
ping -n 1 8.8.8.8 >nul 2>&1
if errorlevel 1 (
    echo ❌ ALERTE: Pas de connexion Internet
    echo %date% %time% - ALERTE: Pas de connexion Internet >> "%ALERT_FILE%"
) else (
    echo ✅ Connexion Internet active
)

REM Vérifier la connectivité locale
ping -n 1 192.168.1.1 >nul 2>&1
if errorlevel 1 (
    echo ⚠️ Connexion réseau local limitée
) else (
    echo ✅ Connexion réseau local active
)

echo.

REM ========================================
REM VÉRIFICATION 7: PERFORMANCES
REM ========================================
echo ⚡ Vérification des performances...

REM Vérifier l'utilisation CPU
powershell -Command "& {Get-WmiObject -Class Win32_Processor | Select-Object @{Name='CPU_Usage';Expression={(Get-Counter '\Processor(_Total)\% Processor Time').CounterSamples.CookedValue}}}"

REM Vérifier l'utilisation mémoire
powershell -Command "& {Get-WmiObject -Class Win32_OperatingSystem | Select-Object @{Name='Memory_Usage';Expression={[math]::Round((($_.TotalVisibleMemorySize - $_.FreePhysicalMemory) / $_.TotalVisibleMemorySize) * 100, 2)}}}"

echo.

REM ========================================
REM RÉSUMÉ ET ALERTES
REM ========================================
echo ========================================
echo 📊 RÉSUMÉ DU MONITORING
echo ========================================

REM Compter les alertes
set /a "ALERT_COUNT=0"
if exist "%ALERT_FILE%" (
    for /f %%i in ('find /c "ALERTE" "%ALERT_FILE%"') do set "ALERT_COUNT=%%i"
)

if %ALERT_COUNT% GTR 0 (
    echo ❌ %ALERT_COUNT% alerte(s) détectée(s)
    echo.
    echo 📋 Dernières alertes:
    type "%ALERT_FILE%" | tail -5
) else (
    echo ✅ Aucune alerte détectée
)

echo.
echo 📝 Log de monitoring: %LOG_FILE%
echo 🚨 Fichier d'alertes: %ALERT_FILE%
echo.

REM Enregistrer le monitoring dans le log
echo %date% %time% - Monitoring terminé - %ALERT_COUNT% alerte(s) >> "%LOG_FILE%"

echo ========================================
echo 🎉 MONITORING TERMINÉ
echo ========================================
echo.

REM Demander si l'utilisateur veut voir les détails
set /p "SHOW_DETAILS=Voulez-vous voir les détails complets ? (O/N): "
if /i "%SHOW_DETAILS%"=="O" (
    echo.
    echo 📋 Détails complets:
    echo.
    echo 🔍 Processus Python:
    tasklist /FI "IMAGENAME eq python.exe"
    echo.
    echo 💾 Espace disque:
    dir D:\ /-c | find "bytes free"
    echo.
    echo 📊 Fichiers de données récents:
    forfiles /p "D:\DATA_SIERRA_CHART" /s /m "*.jsonl" /d -1
    echo.
    echo 📝 Logs récents:
    forfiles /p "%MIA_DIR%\logs" /m "*.log" /d -1
)

pause



