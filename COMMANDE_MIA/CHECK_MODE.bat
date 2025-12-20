@echo off
:: MIA BOT - VERIFICATION DU MODE ACTIF
:: Affiche si le bot est en mode TEST ou PRODUCTION

title MIA - CHECK MODE
chcp 65001 >nul

echo.
echo ================================================================
echo          VERIFICATION DU MODE ACTIF
echo ================================================================
echo.

cd /d D:\MIA_IA_system

:: Rechercher le mode dans le fichier
echo Analyse du fichier launch_production_CLEAN_v2.py...
echo.

powershell -Command "$content = Get-Content 'LAUNCH\launch_production_CLEAN_v2.py' -Raw; if ($content -match 'test_mode=True') { Write-Host '  MODE ACTIF: TEST (24/7)' -ForegroundColor Yellow; Write-Host ''; Write-Host '  Le bot trade SANS restriction horaire' -ForegroundColor Yellow } elseif ($content -match 'test_mode=False') { Write-Host '  MODE ACTIF: PRODUCTION' -ForegroundColor Green; Write-Host ''; Write-Host '  Le bot respecte les restrictions horaires' -ForegroundColor Green } else { Write-Host '  MODE: INCONNU' -ForegroundColor Red }"

echo.
echo ----------------------------------------------------------------
echo  Ligne de configuration:
echo ----------------------------------------------------------------
powershell -Command "Select-String -Path 'LAUNCH\launch_production_CLEAN_v2.py' -Pattern 'self.session_monitor = SessionQualityMonitor' -Context 0,2 | ForEach-Object { $_.Context.PostContext }"

echo.
echo ================================================================
echo  Commandes disponibles:
echo ----------------------------------------------------------------
echo  START_BOT_TEST.bat       - Demarrer en MODE TEST
echo  START_BOT_PRODUCTION.bat - Demarrer en MODE PRODUCTION
echo  START_BOT.bat            - Demarrer (mode actuel)
echo  STOP_BOT.bat             - Arreter le bot
echo ================================================================
echo.

pause

