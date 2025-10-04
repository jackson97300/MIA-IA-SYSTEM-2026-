@echo off
REM 🚀 MIA IA SYSTEM - Configuration Tâches Automatiques
REM Script de configuration des tâches planifiées pour PC fixe et portable
REM Version: Production Ready v1.0

echo ========================================
echo ⚙️ CONFIGURATION TÂCHES AUTOMATIQUES
echo ========================================
echo.

REM Vérifier les privilèges administrateur
net session >nul 2>&1
if errorlevel 1 (
    echo ❌ ERREUR: Privilèges administrateur requis
    echo 💡 Exécutez ce script en tant qu'administrateur
    pause
    exit /b 1
)

echo ✅ Privilèges administrateur confirmés
echo.

REM Configuration des chemins
set "MIA_DIR=D:\MIA_IA_system"
set "MIA_SHARED=D:\MIA_SHARED"
set "PYTHON_CMD=python"

echo 📁 Répertoire MIA: %MIA_DIR%
echo 📁 Répertoire partagé: %MIA_SHARED%
echo.

REM ========================================
REM TÂCHE 1: DÉMARRAGE AUTOMATIQUE BOT
REM ========================================
echo 🔧 Configuration du démarrage automatique du bot...

REM Supprimer l'ancienne tâche si elle existe
schtasks /delete /tn "MIA_Bot_Startup" /f >nul 2>&1

REM Créer la nouvelle tâche
schtasks /create /tn "MIA_Bot_Startup" /tr "\"%MIA_DIR%\start_mia_bot.bat\"" /sc onstart /ru "SYSTEM" /f

if errorlevel 1 (
    echo ❌ Erreur lors de la création de la tâche de démarrage
) else (
    echo ✅ Tâche de démarrage automatique créée
)

echo.

REM ========================================
REM TÂCHE 2: SAUVEGARDE QUOTIDIENNE
REM ========================================
echo 💾 Configuration de la sauvegarde quotidienne...

REM Supprimer l'ancienne tâche si elle existe
schtasks /delete /tn "MIA_Backup_Daily" /f >nul 2>&1

REM Créer la nouvelle tâche
schtasks /create /tn "MIA_Backup_Daily" /tr "\"%MIA_DIR%\backup_mia_daily.bat\"" /sc daily /st 02:00 /ru "SYSTEM" /f

if errorlevel 1 (
    echo ❌ Erreur lors de la création de la tâche de sauvegarde
) else (
    echo ✅ Tâche de sauvegarde quotidienne créée (02:00)
)

echo.

REM ========================================
REM TÂCHE 3: MONITORING SYSTÈME
REM ========================================
echo 📊 Configuration du monitoring système...

REM Supprimer l'ancienne tâche si elle existe
schtasks /delete /tn "MIA_System_Monitor" /f >nul 2>&1

REM Créer la nouvelle tâche
schtasks /create /tn "MIA_System_Monitor" /tr "\"%MIA_DIR%\monitor_mia_system.bat\"" /sc minute /mo 30 /ru "SYSTEM" /f

if errorlevel 1 (
    echo ❌ Erreur lors de la création de la tâche de monitoring
) else (
    echo ✅ Tâche de monitoring créée (toutes les 30 minutes)
)

echo.

REM ========================================
REM TÂCHE 4: SYNCHRONISATION SYNCING
REM ========================================
echo 🔄 Configuration de la synchronisation Syncthing...

REM Supprimer l'ancienne tâche si elle existe
schtasks /delete /tn "MIA_Syncthing_Check" /f >nul 2>&1

REM Créer la nouvelle tâche
schtasks /create /tn "MIA_Syncthing_Check" /tr "net start syncthing" /sc minute /mo 15 /ru "SYSTEM" /f

if errorlevel 1 (
    echo ❌ Erreur lors de la création de la tâche Syncthing
) else (
    echo ✅ Tâche de vérification Syncthing créée (toutes les 15 minutes)
)

echo.

REM ========================================
REM TÂCHE 5: NETTOYAGE DES LOGS
REM ========================================
echo 🧹 Configuration du nettoyage des logs...

REM Supprimer l'ancienne tâche si elle existe
schtasks /delete /tn "MIA_Logs_Cleanup" /f >nul 2>&1

REM Créer la nouvelle tâche
schtasks /create /tn "MIA_Logs_Cleanup" /tr "forfiles /p \"%MIA_DIR%\\logs\" /m *.log /d -7 /c \"cmd /c del @path\"" /sc daily /st 03:00 /ru "SYSTEM" /f

if errorlevel 1 (
    echo ❌ Erreur lors de la création de la tâche de nettoyage
) else (
    echo ✅ Tâche de nettoyage des logs créée (03:00)
)

echo.

REM ========================================
REM TÂCHE 6: VÉRIFICATION ESPACE DISQUE
REM ========================================
echo 💾 Configuration de la vérification d'espace disque...

REM Supprimer l'ancienne tâche si elle existe
schtasks /delete /tn "MIA_Disk_Space_Check" /f >nul 2>&1

REM Créer la nouvelle tâche
schtasks /create /tn "MIA_Disk_Space_Check" /tr "powershell -Command \"& {Get-WmiObject -Class Win32_LogicalDisk -Filter 'DeviceID=\\\"D:\\\\\\\"' | Where-Object {$_.FreeSpace -lt 5GB} | ForEach-Object {Write-Host 'ALERTE: Espace disque faible -' $_.FreeSpace/1GB 'GB restants'}}\"" /sc hourly /ru "SYSTEM" /f

if errorlevel 1 (
    echo ❌ Erreur lors de la création de la tâche de vérification d'espace
) else (
    echo ✅ Tâche de vérification d'espace disque créée (toutes les heures)
)

echo.

REM ========================================
REM TÂCHE 7: REDÉMARRAGE SYSTÈME (OPTIONNEL)
REM ========================================
echo 🔄 Configuration du redémarrage système (optionnel)...

set /p "ENABLE_RESTART=Voulez-vous activer le redémarrage automatique hebdomadaire ? (O/N): "
if /i "%ENABLE_RESTART%"=="O" (
    REM Supprimer l'ancienne tâche si elle existe
    schtasks /delete /tn "MIA_Weekly_Restart" /f >nul 2>&1
    
    REM Créer la nouvelle tâche
    schtasks /create /tn "MIA_Weekly_Restart" /tr "shutdown /r /t 60 /c \"Redémarrage automatique MIA System\"" /sc weekly /d SUN /st 04:00 /ru "SYSTEM" /f
    
    if errorlevel 1 (
        echo ❌ Erreur lors de la création de la tâche de redémarrage
    ) else (
        echo ✅ Tâche de redémarrage hebdomadaire créée (Dimanche 04:00)
    )
) else (
    echo ⏭️ Redémarrage automatique désactivé
)

echo.

REM ========================================
REM VÉRIFICATION DES TÂCHES
REM ========================================
echo 🔍 Vérification des tâches créées...

echo.
echo 📋 Tâches planifiées MIA:
schtasks /query /tn "MIA_Bot_Startup" /fo list | find "Task Name"
schtasks /query /tn "MIA_Backup_Daily" /fo list | find "Task Name"
schtasks /query /tn "MIA_System_Monitor" /fo list | find "Task Name"
schtasks /query /tn "MIA_Syncthing_Check" /fo list | find "Task Name"
schtasks /query /tn "MIA_Logs_Cleanup" /fo list | find "Task Name"
schtasks /query /tn "MIA_Disk_Space_Check" /fo list | find "Task Name"
if /i "%ENABLE_RESTART%"=="O" (
    schtasks /query /tn "MIA_Weekly_Restart" /fo list | find "Task Name"
)

echo.

REM ========================================
REM CONFIGURATION PC PORTABLE
REM ========================================
echo 💻 Configuration pour PC portable...

set /p "CONFIGURE_PORTABLE=Voulez-vous configurer les tâches pour PC portable ? (O/N): "
if /i "%CONFIGURE_PORTABLE%"=="O" (
    echo.
    echo 🔧 Configuration des tâches PC portable...
    
    REM Tâche de synchronisation pour PC portable
    schtasks /delete /tn "MIA_Portable_Sync" /f >nul 2>&1
    schtasks /create /tn "MIA_Portable_Sync" /tr "\"C:\\MIA_SHARED\\sync_mia_portable.bat\"" /sc minute /mo 60 /ru "SYSTEM" /f
    
    if errorlevel 1 (
        echo ❌ Erreur lors de la création de la tâche de synchronisation portable
    ) else (
        echo ✅ Tâche de synchronisation portable créée (toutes les heures)
    )
    
    REM Tâche de monitoring pour PC portable
    schtasks /delete /tn "MIA_Portable_Monitor" /f >nul 2>&1
    schtasks /create /tn "MIA_Portable_Monitor" /tr "\"C:\\MIA_SHARED\\monitor_mia_portable.bat\"" /sc minute /mo 30 /ru "SYSTEM" /f
    
    if errorlevel 1 (
        echo ❌ Erreur lors de la création de la tâche de monitoring portable
    ) else (
        echo ✅ Tâche de monitoring portable créée (toutes les 30 minutes)
    )
)

echo.

REM ========================================
REM CRÉATION DU SCRIPT DE GESTION
REM ========================================
echo 📝 Création du script de gestion des tâches...

(
echo @echo off
echo REM 🚀 MIA IA SYSTEM - Gestion des Tâches
echo REM Script de gestion des tâches planifiées
echo REM Version: Production Ready v1.0
echo.
echo echo ========================================
echo echo ⚙️ GESTION DES TÂCHES MIA SYSTEM
echo echo ========================================
echo echo.
echo echo 1. Voir le statut des tâches
echo echo 2. Démarrer une tâche
echo echo 3. Arrêter une tâche
echo echo 4. Voir les logs
echo echo 5. Quitter
echo echo.
echo set /p "CHOICE=Choisissez une option (1-5): "
echo.
echo if "%%CHOICE%%"=="1" goto STATUS
echo if "%%CHOICE%%"=="2" goto START
echo if "%%CHOICE%%"=="3" goto STOP
echo if "%%CHOICE%%"=="4" goto LOGS
echo if "%%CHOICE%%"=="5" goto EXIT
echo.
echo :STATUS
echo echo 📊 Statut des tâches:
echo schtasks /query /tn "MIA_Bot_Startup" /fo list ^| find "Status"
echo schtasks /query /tn "MIA_Backup_Daily" /fo list ^| find "Status"
echo schtasks /query /tn "MIA_System_Monitor" /fo list ^| find "Status"
echo schtasks /query /tn "MIA_Syncthing_Check" /fo list ^| find "Status"
echo schtasks /query /tn "MIA_Logs_Cleanup" /fo list ^| find "Status"
echo schtasks /query /tn "MIA_Disk_Space_Check" /fo list ^| find "Status"
echo pause
echo goto MENU
echo.
echo :START
echo echo 🚀 Démarrage des tâches...
echo schtasks /run /tn "MIA_Bot_Startup"
echo schtasks /run /tn "MIA_System_Monitor"
echo schtasks /run /tn "MIA_Syncthing_Check"
echo echo ✅ Tâches démarrées
echo pause
echo goto MENU
echo.
echo :STOP
echo echo ⏹️ Arrêt des tâches...
echo schtasks /end /tn "MIA_Bot_Startup"
echo schtasks /end /tn "MIA_System_Monitor"
echo schtasks /end /tn "MIA_Syncthing_Check"
echo echo ✅ Tâches arrêtées
echo pause
echo goto MENU
echo.
echo :LOGS
echo echo 📝 Logs des tâches:
echo type "%MIA_DIR%\logs\monitoring.log" ^| tail -20
echo pause
echo goto MENU
echo.
echo :EXIT
echo echo 👋 Au revoir!
echo exit
) > "%MIA_DIR%\manage_tasks.bat"

echo ✅ Script de gestion des tâches créé

echo.
echo ========================================
echo 🎉 CONFIGURATION TERMINÉE AVEC SUCCÈS
echo ========================================
echo.
echo 📊 Résumé des tâches configurées:
echo    - Démarrage automatique du bot
echo    - Sauvegarde quotidienne (02:00)
echo    - Monitoring système (toutes les 30 min)
echo    - Vérification Syncthing (toutes les 15 min)
echo    - Nettoyage des logs (03:00)
echo    - Vérification espace disque (toutes les heures)
if /i "%ENABLE_RESTART%"=="O" (
    echo    - Redémarrage hebdomadaire (Dimanche 04:00)
)
if /i "%CONFIGURE_PORTABLE%"=="O" (
    echo    - Synchronisation portable (toutes les heures)
    echo    - Monitoring portable (toutes les 30 min)
)
echo.
echo 💡 Commandes utiles:
echo    - Gérer les tâches: %MIA_DIR%\manage_tasks.bat
echo    - Voir le statut: schtasks /query /tn "MIA_*"
echo    - Démarrer une tâche: schtasks /run /tn "MIA_Bot_Startup"
echo    - Arrêter une tâche: schtasks /end /tn "MIA_Bot_Startup"
echo.
echo 📋 Prochaines étapes:
echo    1. Tester le démarrage automatique
echo    2. Vérifier les sauvegardes
echo    3. Monitorer les performances
echo    4. Configurer les alertes
echo.

REM Créer un log de configuration
echo %date% %time% - Configuration des tâches automatiques terminée >> "%MIA_DIR%\logs\setup_log.txt"

pause



