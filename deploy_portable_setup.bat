@echo off
REM 🚀 MIA IA SYSTEM - Déploiement PC Portable
REM Script de déploiement automatique pour PC portable
REM Version: Production Ready v1.0

echo ========================================
echo 💻 DÉPLOIEMENT PC PORTABLE MIA SYSTEM
echo ========================================
echo.

REM Configuration des chemins
set "SOURCE_DIR=D:\MIA_SHARED\MIA_IA_system"
set "TARGET_DIR=C:\MIA_SHARED\MIA_IA_system"
set "BACKUP_DIR=C:\MIA_SHARED\backups"

echo 📁 Source: %SOURCE_DIR%
echo 💻 Destination: %TARGET_DIR%
echo.

REM Vérifier que le dossier source existe
if not exist "%SOURCE_DIR%" (
    echo ❌ ERREUR: Dossier source non trouvé
    echo 💡 Assurez-vous que Syncthing est configuré et synchronisé
    pause
    exit /b 1
)

echo ✅ Dossier source trouvé

REM Créer le dossier de destination
if not exist "C:\MIA_SHARED" (
    echo 📁 Création du dossier MIA_SHARED...
    mkdir "C:\MIA_SHARED"
    echo ✅ Dossier MIA_SHARED créé
)

REM Créer le dossier de sauvegarde
if not exist "%BACKUP_DIR%" (
    echo 📁 Création du dossier de sauvegarde...
    mkdir "%BACKUP_DIR%"
    echo ✅ Dossier de sauvegarde créé
)

echo.
echo 🔄 Début du déploiement...

REM Sauvegarder l'ancienne installation si elle existe
if exist "%TARGET_DIR%" (
    echo 💾 Sauvegarde de l'ancienne installation...
    set "BACKUP_NAME=MIA_BACKUP_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
    set "BACKUP_NAME=%BACKUP_NAME: =0%"
    robocopy "%TARGET_DIR%" "%BACKUP_DIR%\%BACKUP_NAME%" /E /R:3 /W:1
    echo ✅ Ancienne installation sauvegardée
)

REM Copier le système MIA
echo 📊 Copie du système MIA...
robocopy "%SOURCE_DIR%" "%TARGET_DIR%" /E /R:3 /W:1 /MT:8 /XD __pycache__ venv .git /XF *.tmp *.temp *.log

if errorlevel 8 (
    echo ⚠️ Certains fichiers n'ont pas pu être copiés
) else (
    echo ✅ Système MIA copié avec succès
)

REM Copier les données de trading
echo 📈 Copie des données de trading...
if exist "D:\MIA_SHARED\DATA_SIERRA_CHART" (
    robocopy "D:\MIA_SHARED\DATA_SIERRA_CHART" "C:\MIA_SHARED\DATA_SIERRA_CHART" /E /R:3 /W:1 /MT:8
    echo ✅ Données de trading copiées
) else (
    echo ⚠️ Dossier DATA_SIERRA_CHART non trouvé dans MIA_SHARED
)

REM Copier les résultats
echo 📊 Copie des résultats...
if exist "D:\MIA_SHARED\results" (
    robocopy "D:\MIA_SHARED\results" "C:\MIA_SHARED\results" /E /R:3 /W:1
    echo ✅ Résultats copiés
)

REM Copier les logs
echo 📝 Copie des logs...
if exist "D:\MIA_SHARED\logs" (
    robocopy "D:\MIA_SHARED\logs" "C:\MIA_SHARED\logs" /E /R:3 /W:1
    echo ✅ Logs copiés
)

REM Copier les configurations
echo ⚙️ Copie des configurations...
if exist "D:\MIA_SHARED\config" (
    robocopy "D:\MIA_SHARED\config" "C:\MIA_SHARED\config" /E /R:3 /W:1
    echo ✅ Configurations copiées
)

echo.
echo 🔧 Configuration des scripts...

REM Créer le script de démarrage pour le PC portable
echo 📝 Création du script de démarrage...
(
echo @echo off
echo REM 🚀 MIA IA SYSTEM - Démarrage PC Portable
echo REM Script de démarrage pour PC portable
echo REM Version: Production Ready v1.0
echo.
echo echo ========================================
echo echo 💻 DÉMARRAGE MIA SYSTEM - PC PORTABLE
echo echo ========================================
echo echo.
echo.
echo REM Configuration des chemins
echo set "MIA_DIR=C:\MIA_SHARED\MIA_IA_system"
echo set "PYTHON_CMD=python"
echo.
echo echo 📁 Répertoire MIA: %%MIA_DIR%%
echo echo.
echo.
echo REM Vérifier que le dossier existe
echo if not exist "%%MIA_DIR%%" ^(
echo     echo ❌ ERREUR: Dossier MIA non trouvé
echo     echo 💡 Exécutez d'abord deploy_portable_setup.bat
echo     pause
echo     exit /b 1
echo ^)
echo.
echo echo ✅ Dossier MIA trouvé
echo.
echo.
echo REM Vérifier que Python est installé
echo %%PYTHON_CMD%% --version ^>nul 2^>^&1
echo if errorlevel 1 ^(
echo     echo ❌ ERREUR: Python non installé
echo     echo 💡 Installez Python depuis https://python.org
echo     pause
echo     exit /b 1
echo ^)
echo.
echo echo ✅ Python détecté
echo.
echo.
echo REM Changer vers le répertoire MIA
echo cd /d "%%MIA_DIR%%"
echo.
echo echo 🚀 Démarrage du système MIA...
echo echo.
echo.
echo REM Démarrer le système MIA
echo %%PYTHON_CMD%% launch_hybrid_live.py
echo.
echo echo.
echo echo ========================================
echo echo 🎉 SYSTÈME MIA DÉMARRÉ
echo echo ========================================
echo echo.
echo pause
) > "C:\MIA_SHARED\start_mia_portable.bat"

echo ✅ Script de démarrage créé

REM Créer le script de monitoring pour le PC portable
echo 📊 Création du script de monitoring...
(
echo @echo off
echo REM 🚀 MIA IA SYSTEM - Monitoring PC Portable
echo REM Script de monitoring pour PC portable
echo REM Version: Production Ready v1.0
echo.
echo echo ========================================
echo echo 📊 MONITORING MIA SYSTEM - PC PORTABLE
echo echo ========================================
echo echo.
echo.
echo REM Configuration
echo set "MIA_DIR=C:\MIA_SHARED\MIA_IA_system"
echo set "LOG_FILE=%%MIA_DIR%%\logs\monitoring_portable.log"
echo set "ALERT_FILE=%%MIA_DIR%%\logs\alerts_portable.log"
echo.
echo echo 📅 Date de vérification: %%date%% %%time%%
echo echo.
echo.
echo REM Créer le fichier de log s'il n'existe pas
echo if not exist "%%MIA_DIR%%\logs" mkdir "%%MIA_DIR%%\logs"
echo if not exist "%%LOG_FILE%%" echo. ^> "%%LOG_FILE%%"
echo if not exist "%%ALERT_FILE%%" echo. ^> "%%ALERT_FILE%%"
echo.
echo.
echo REM Vérification des processus MIA
echo echo 🔍 Vérification des processus MIA...
echo tasklist /FI "IMAGENAME eq python.exe" ^| find "python.exe" ^>nul
echo if errorlevel 1 ^(
echo     echo ❌ ALERTE: Aucun processus Python détecté
echo     echo %%date%% %%time%% - ALERTE: Aucun processus Python détecté ^>^> "%%ALERT_FILE%%"
echo ^) else ^(
echo     echo ✅ Processus Python détecté
echo ^)
echo.
echo.
echo REM Vérification de l'espace disque
echo echo 💾 Vérification de l'espace disque...
echo for /f "tokens=3" %%%%a in ^('dir C:\ /-c ^| find "bytes free"'^) do set "FREE_SPACE=%%%%a"
echo set /a "FREE_GB=%%FREE_SPACE%% / 1073741824"
echo.
echo if %%FREE_GB%% LSS 2 ^(
echo     echo ❌ ALERTE: Espace disque faible - %%FREE_GB%% GB restants
echo     echo %%date%% %%time%% - ALERTE: Espace disque faible - %%FREE_GB%% GB restants ^>^> "%%ALERT_FILE%%"
echo ^) else ^(
echo     echo ✅ Espace disque suffisant - %%FREE_GB%% GB restants
echo ^)
echo.
echo.
echo REM Vérification de la synchronisation
echo echo 🔄 Vérification de la synchronisation...
echo if exist "C:\MIA_SHARED\MIA_IA_system" ^(
echo     echo ✅ Système MIA synchronisé
echo ^) else ^(
echo     echo ❌ ALERTE: Système MIA non synchronisé
echo     echo %%date%% %%time%% - ALERTE: Système MIA non synchronisé ^>^> "%%ALERT_FILE%%"
echo ^)
echo.
echo.
echo REM Vérification des données de trading
echo echo 📊 Vérification des données de trading...
echo if exist "C:\MIA_SHARED\DATA_SIERRA_CHART" ^(
echo     echo ✅ Données de trading synchronisées
echo ^) else ^(
echo     echo ⚠️ Données de trading non synchronisées
echo ^)
echo.
echo.
echo echo ========================================
echo echo 🎉 MONITORING TERMINÉ
echo echo ========================================
echo echo.
echo pause
) > "C:\MIA_SHARED\monitor_mia_portable.bat"

echo ✅ Script de monitoring créé

REM Créer le script de synchronisation
echo 🔄 Création du script de synchronisation...
(
echo @echo off
echo REM 🚀 MIA IA SYSTEM - Synchronisation PC Portable
echo REM Script de synchronisation pour PC portable
echo REM Version: Production Ready v1.0
echo.
echo echo ========================================
echo echo 🔄 SYNCHRONISATION MIA SYSTEM
echo echo ========================================
echo echo.
echo.
echo REM Configuration
echo set "SOURCE_DIR=D:\MIA_SHARED"
echo set "TARGET_DIR=C:\MIA_SHARED"
echo.
echo echo 📁 Source: %%SOURCE_DIR%%
echo echo 💻 Destination: %%TARGET_DIR%%
echo echo.
echo.
echo REM Vérifier que le dossier source existe
echo if not exist "%%SOURCE_DIR%%" ^(
echo     echo ❌ ERREUR: Dossier source non trouvé
echo     echo 💡 Assurez-vous que Syncthing est configuré et synchronisé
echo     pause
echo     exit /b 1
echo ^)
echo.
echo echo ✅ Dossier source trouvé
echo.
echo.
echo REM Créer le dossier de destination
echo if not exist "%%TARGET_DIR%%" ^(
echo     echo 📁 Création du dossier MIA_SHARED...
echo     mkdir "%%TARGET_DIR%%"
echo     echo ✅ Dossier MIA_SHARED créé
echo ^)
echo.
echo.
echo echo 🔄 Début de la synchronisation...
echo.
echo.
echo REM Synchroniser le système MIA
echo echo 📊 Synchronisation du système MIA...
echo robocopy "%%SOURCE_DIR%%\MIA_IA_system" "%%TARGET_DIR%%\MIA_IA_system" /E /R:3 /W:1 /MT:8 /XD __pycache__ venv .git /XF *.tmp *.temp *.log
echo.
echo.
echo REM Synchroniser les données de trading
echo echo 📈 Synchronisation des données de trading...
echo if exist "%%SOURCE_DIR%%\DATA_SIERRA_CHART" ^(
echo     robocopy "%%SOURCE_DIR%%\DATA_SIERRA_CHART" "%%TARGET_DIR%%\DATA_SIERRA_CHART" /E /R:3 /W:1 /MT:8
echo     echo ✅ Données de trading synchronisées
echo ^) else ^(
echo     echo ⚠️ Dossier DATA_SIERRA_CHART non trouvé
echo ^)
echo.
echo.
echo REM Synchroniser les résultats
echo echo 📊 Synchronisation des résultats...
echo if exist "%%SOURCE_DIR%%\results" ^(
echo     robocopy "%%SOURCE_DIR%%\results" "%%TARGET_DIR%%\results" /E /R:3 /W:1
echo     echo ✅ Résultats synchronisés
echo ^)
echo.
echo.
echo REM Synchroniser les logs
echo echo 📝 Synchronisation des logs...
echo if exist "%%SOURCE_DIR%%\logs" ^(
echo     robocopy "%%SOURCE_DIR%%\logs" "%%TARGET_DIR%%\logs" /E /R:3 /W:1
echo     echo ✅ Logs synchronisés
echo ^)
echo.
echo.
echo REM Synchroniser les configurations
echo echo ⚙️ Synchronisation des configurations...
echo if exist "%%SOURCE_DIR%%\config" ^(
echo     robocopy "%%SOURCE_DIR%%\config" "%%TARGET_DIR%%\config" /E /R:3 /W:1
echo     echo ✅ Configurations synchronisées
echo ^)
echo.
echo.
echo echo ========================================
echo echo 🎉 SYNCHRONISATION TERMINÉE
echo echo ========================================
echo echo.
echo pause
) > "C:\MIA_SHARED\sync_mia_portable.bat"

echo ✅ Script de synchronisation créé

REM Créer un raccourci sur le bureau
echo 🖥️ Création du raccourci sur le bureau...
(
echo [InternetShortcut]
echo URL=file:///C:/MIA_SHARED/start_mia_portable.bat
echo IconFile=C:\MIA_SHARED\MIA_IA_system\start_mia_bot.bat
echo IconIndex=0
) > "%USERPROFILE%\Desktop\MIA System Portable.url"

echo ✅ Raccourci créé sur le bureau

echo.
echo ========================================
echo 🎉 DÉPLOIEMENT TERMINÉ AVEC SUCCÈS
echo ========================================
echo.
echo 📊 Résumé du déploiement:
echo    - Système MIA copié vers C:\MIA_SHARED\
echo    - Scripts de démarrage créés
echo    - Scripts de monitoring créés
echo    - Scripts de synchronisation créés
echo    - Raccourci créé sur le bureau
echo.
echo 💡 Prochaines étapes:
echo    1. Tester le démarrage: C:\MIA_SHARED\start_mia_portable.bat
echo    2. Configurer Syncthing sur le PC portable
echo    3. Tester la synchronisation
echo    4. Programmer les tâches automatiques
echo.
echo 📋 Fichiers créés:
echo    - C:\MIA_SHARED\start_mia_portable.bat
echo    - C:\MIA_SHARED\monitor_mia_portable.bat
echo    - C:\MIA_SHARED\sync_mia_portable.bat
echo    - %USERPROFILE%\Desktop\MIA System Portable.url
echo.

REM Créer un log de déploiement
echo %date% %time% - Déploiement PC portable terminé avec succès >> "C:\MIA_SHARED\deployment_log.txt"

pause



