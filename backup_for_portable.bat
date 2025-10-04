@echo off
echo ========================================
echo    SAUVEGARDE MIA_IA_SYSTEM POUR PORTABLE
echo ========================================
echo.

REM Créer le dossier de sauvegarde
set BACKUP_DIR=D:\MIA_IA_system_BACKUP_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set BACKUP_DIR=%BACKUP_DIR: =0%
mkdir "%BACKUP_DIR%"

echo [1/6] Copie des fichiers du projet...
xcopy "D:\MIA_IA_system\*" "%BACKUP_DIR%\" /E /I /H /Y /EXCLUDE:backup_exclude.txt

echo [2/6] Sauvegarde des settings Cursor...
if exist "%APPDATA%\Cursor\User\settings.json" (
    copy "%APPDATA%\Cursor\User\settings.json" "%BACKUP_DIR%\cursor_settings_backup.json"
    echo   ✓ Settings Cursor sauvegardés
) else (
    echo   ⚠ Settings Cursor non trouvés
)

if exist "%APPDATA%\Cursor\User\keybindings.json" (
    copy "%APPDATA%\Cursor\User\keybindings.json" "%BACKUP_DIR%\cursor_keybindings_backup.json"
    echo   ✓ Keybindings Cursor sauvegardés
) else (
    echo   ⚠ Keybindings Cursor non trouvés
)

echo [3/6] Création de l'archive légère (sans gros fichiers)...
powershell -Command "Compress-Archive -Path 'D:\MIA_IA_system' -DestinationPath 'D:\MIA_IA_system_LIGHT_BACKUP.zip' -Exclude @('DATA_SIERRA_CHART\*', 'venv\*', '__pycache__\*', '*.log', '*.parquet', 'models\*.pkl', 'results\*', '*.zip') -Force"

echo [4/6] Création de l'archive complète...
powershell -Command "Compress-Archive -Path 'D:\MIA_IA_system' -DestinationPath 'D:\MIA_IA_system_FULL_BACKUP.zip' -CompressionLevel Optimal -Force"

echo [5/6] Génération du rapport de sauvegarde...
echo Sauvegarde MIA_IA_system - %date% %time% > "%BACKUP_DIR%\backup_report.txt"
echo. >> "%BACKUP_DIR%\backup_report.txt"
echo Fichiers sauvegardés: >> "%BACKUP_DIR%\backup_report.txt"
dir "D:\MIA_IA_system" /S /B | find /C /V "" >> "%BACKUP_DIR%\backup_report.txt"
echo. >> "%BACKUP_DIR%\backup_report.txt"
echo Taille totale: >> "%BACKUP_DIR%\backup_report.txt"
powershell -Command "(Get-ChildItem 'D:\MIA_IA_system' -Recurse | Measure-Object -Property Length -Sum).Sum / 1GB" >> "%BACKUP_DIR%\backup_report.txt"
echo GB >> "%BACKUP_DIR%\backup_report.txt"

echo [6/6] Création des instructions de migration...
echo # INSTRUCTIONS DE MIGRATION VERS PORTABLE > "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo. >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo ## 1. Installation sur le portable >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo - Installer Cursor depuis https://cursor.sh/ >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo - Installer Python 3.11 depuis python.org >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo - Installer Git depuis git-scm.com >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo. >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo ## 2. Clonage du repository >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo ```bash >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo git clone https://github.com/jackson97300/MIA_IA_system_mentor_q.git >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo ``` >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo. >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo ## 3. Installation des dépendances >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo ```bash >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo pip install xgboost lightgbm catboost scikit-learn pandas numpy >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo pip install stable-baselines3 torch gymnasium >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo ``` >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo. >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo ## 4. Restauration des settings Cursor >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo - Copier cursor_settings_backup.json vers %%APPDATA%%\Cursor\User\settings.json >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"
echo - Copier cursor_keybindings_backup.json vers %%APPDATA%%\Cursor\User\keybindings.json >> "%BACKUP_DIR%\MIGRATION_INSTRUCTIONS.md"

echo.
echo ========================================
echo           SAUVEGARDE TERMINÉE
echo ========================================
echo.
echo Fichiers créés:
echo - %BACKUP_DIR%
echo - D:\MIA_IA_system_LIGHT_BACKUP.zip
echo - D:\MIA_IA_system_FULL_BACKUP.zip
echo.
echo Prochaines étapes:
echo 1. Transférer les fichiers vers le portable
echo 2. Suivre les instructions dans MIGRATION_INSTRUCTIONS.md
echo 3. Tester le pipeline ML sur le portable
echo.
pause
