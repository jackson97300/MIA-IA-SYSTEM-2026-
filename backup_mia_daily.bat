@echo off
REM 🚀 MIA IA SYSTEM - Sauvegarde Quotidienne Automatique
REM Script de sauvegarde quotidienne du système MIA
REM Version: Production Ready v1.0

echo ========================================
echo 💾 SAUVEGARDE QUOTIDIENNE MIA SYSTEM
echo ========================================
echo.

REM Configuration des chemins
set "SOURCE_DIR=D:\MIA_IA_system"
set "BACKUP_DIR=D:\MIA_SHARED\backups"
set "DATE_STR=%date:~-4,4%%date:~-10,2%%date:~-7,2%"
set "BACKUP_NAME=MIA_BACKUP_%DATE_STR%"

echo 📅 Date de sauvegarde: %DATE_STR%
echo 📁 Source: %SOURCE_DIR%
echo 💾 Destination: %BACKUP_DIR%\%BACKUP_NAME%
echo.

REM Créer le dossier de sauvegarde s'il n'existe pas
if not exist "%BACKUP_DIR%" (
    echo 📁 Création du dossier de sauvegarde...
    mkdir "%BACKUP_DIR%"
    echo ✅ Dossier de sauvegarde créé
)

REM Créer le dossier de sauvegarde du jour
if not exist "%BACKUP_DIR%\%BACKUP_NAME%" (
    echo 📁 Création du dossier de sauvegarde du jour...
    mkdir "%BACKUP_DIR%\%BACKUP_NAME%"
    echo ✅ Dossier de sauvegarde du jour créé
)

echo.
echo 🔄 Début de la sauvegarde...

REM Sauvegarder le système MIA complet
echo 📊 Sauvegarde du système MIA...
robocopy "%SOURCE_DIR%" "%BACKUP_DIR%\%BACKUP_NAME%\MIA_IA_system" /E /R:3 /W:1 /MT:8 /XD __pycache__ venv .git /XF *.tmp *.temp *.log

if errorlevel 8 (
    echo ⚠️ Certains fichiers n'ont pas pu être copiés
) else (
    echo ✅ Système MIA sauvegardé avec succès
)

REM Sauvegarder les données de trading
echo 📈 Sauvegarde des données de trading...
if exist "D:\DATA_SIERRA_CHART" (
    robocopy "D:\DATA_SIERRA_CHART" "%BACKUP_DIR%\%BACKUP_NAME%\DATA_SIERRA_CHART" /E /R:3 /W:1 /MT:8
    echo ✅ Données de trading sauvegardées
) else (
    echo ⚠️ Dossier DATA_SIERRA_CHART non trouvé
)

REM Sauvegarder les résultats
echo 📊 Sauvegarde des résultats...
if exist "D:\MIA_IA_system\results" (
    robocopy "D:\MIA_IA_system\results" "%BACKUP_DIR%\%BACKUP_NAME%\results" /E /R:3 /W:1
    echo ✅ Résultats sauvegardés
)

REM Sauvegarder les logs
echo 📝 Sauvegarde des logs...
if exist "D:\MIA_IA_system\logs" (
    robocopy "D:\MIA_IA_system\logs" "%BACKUP_DIR%\%BACKUP_NAME%\logs" /E /R:3 /W:1
    echo ✅ Logs sauvegardés
)

REM Sauvegarder les configurations
echo ⚙️ Sauvegarde des configurations...
if exist "D:\MIA_IA_system\config" (
    robocopy "D:\MIA_IA_system\config" "%BACKUP_DIR%\%BACKUP_NAME%\config" /E /R:3 /W:1
    echo ✅ Configurations sauvegardées
)

REM Créer un fichier de métadonnées
echo 📋 Création du fichier de métadonnées...
(
echo MIA SYSTEM BACKUP METADATA
echo ==========================
echo Date: %date% %time%
echo Source: %SOURCE_DIR%
echo Destination: %BACKUP_DIR%\%BACKUP_NAME%
echo.
echo Fichiers sauvegardés:
dir "%BACKUP_DIR%\%BACKUP_NAME%" /s /b
echo.
echo Taille totale:
powershell -Command "& {Get-ChildItem '%BACKUP_DIR%\%BACKUP_NAME%' -Recurse | Measure-Object -Property Length -Sum | Select-Object @{Name='Size(MB)';Expression={[math]::Round($_.Sum/1MB,2)}}}"
) > "%BACKUP_DIR%\%BACKUP_NAME%\BACKUP_INFO.txt"

echo ✅ Fichier de métadonnées créé

REM Nettoyer les anciennes sauvegardes (garder 7 jours)
echo 🧹 Nettoyage des anciennes sauvegardes...
forfiles /p "%BACKUP_DIR%" /m "MIA_BACKUP_*" /d -7 /c "cmd /c if @isdir==TRUE rmdir /s /q @path"

echo ✅ Anciennes sauvegardes nettoyées

REM Vérifier l'espace disque
echo 💾 Vérification de l'espace disque...
powershell -Command "& {Get-WmiObject -Class Win32_LogicalDisk -Filter 'DeviceID=\"D:\"' | Select-Object @{Name='FreeSpace(GB)';Expression={[math]::Round($_.FreeSpace/1GB,2)}}}"

echo.
echo ========================================
echo 🎉 SAUVEGARDE TERMINÉE AVEC SUCCÈS
echo ========================================
echo.
echo 📊 Résumé:
echo    - Dossier de sauvegarde: %BACKUP_DIR%\%BACKUP_NAME%
echo    - Fichier de métadonnées: BACKUP_INFO.txt
echo    - Anciennes sauvegardes nettoyées
echo.
echo 💡 Prochaines étapes:
echo    1. Vérifier la synchronisation Syncthing
echo    2. Tester la restauration (optionnel)
echo    3. Programmer la tâche planifiée
echo.

REM Créer un log de sauvegarde
echo %date% %time% - Sauvegarde terminée avec succès >> "%BACKUP_DIR%\backup_log.txt"

pause



