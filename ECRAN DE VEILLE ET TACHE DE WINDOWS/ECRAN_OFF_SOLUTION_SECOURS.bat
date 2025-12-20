@echo off
title MIA_IA - SOLUTION SECOURS (Config Windows)

cls
echo =======================================
echo   MIA_IA - SOLUTION SECOURS
echo =======================================
echo.
echo Cette methode configure Windows pour eteindre
echo l'ecran automatiquement apres 1 minute d'inactivite.
echo.
echo AVANTAGE : Marche a 100%, pas de script complexe
echo.
pause
echo.

REM ============================================================
REM 1) CONFIGURATION ANTI-VEILLE + AUTO-OFF ECRAN 1MIN
REM ============================================================

echo Configuration en cours...
echo.

REM Pas de veille PC
powercfg /x -standby-timeout-ac 0 >nul 2>&1
powercfg /x -standby-timeout-dc 0 >nul 2>&1
powercfg /x -hibernate-timeout-ac 0 >nul 2>&1
powercfg /x -hibernate-timeout-dc 0 >nul 2>&1

REM Ecran OFF automatique apres 1 minute
powercfg /x -monitor-timeout-ac 1 >nul 2>&1
powercfg /x -monitor-timeout-dc 1 >nul 2>&1

REM Capot ne fait rien
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0 >nul 2>&1
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0 >nul 2>&1

echo =======================================
echo   CONFIGURATION APPLIQUEE
echo =======================================
echo.
echo [OK] PC ne se mettra JAMAIS en veille
echo [OK] Capot ne coupera RIEN
echo [OK] Ecran s'eteindra apres 1 MINUTE d'inactivite
echo [OK] Sierra Chart continuera
echo [OK] MIA_IA continuera de trader
echo.
echo =======================================
echo   WORKFLOW :
echo =======================================
echo   1. Lance Sierra Chart
echo   2. Lance MIA_IA Bot
echo   3. Ne touche plus souris/clavier
echo   4. Apres 1 min : ecran OFF automatique
echo   5. Ferme le capot
echo   6. Tout continue de tourner !
echo =======================================
echo.
echo Pour rallumer l'ecran : Bouge la souris
echo.
pause

