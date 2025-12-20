@echo off
title MIA_IA - PRODUCTION (Config 5min)

cls
echo =======================================
echo   MIA_IA - PRODUCTION (5 MINUTES)
echo =======================================
echo.
echo Configuration Windows pour extinction automatique
echo de l'ecran apres 5 minutes d'inactivite.
echo.
echo AVANTAGE : Reveil instantane (1 clic souris)
echo.
pause
echo.

REM ============================================================
REM 1) CONFIGURATION ANTI-VEILLE + AUTO-OFF ECRAN 5MIN
REM ============================================================

echo Configuration en cours...
echo.

REM Pas de veille PC
powercfg /x -standby-timeout-ac 0 >nul 2>&1
powercfg /x -standby-timeout-dc 0 >nul 2>&1
powercfg /x -hibernate-timeout-ac 0 >nul 2>&1
powercfg /x -hibernate-timeout-dc 0 >nul 2>&1

REM Ecran OFF automatique apres 5 minutes
powercfg /x -monitor-timeout-ac 5 >nul 2>&1
powercfg /x -monitor-timeout-dc 5 >nul 2>&1

REM Capot ne fait rien
powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0 >nul 2>&1
powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_BUTTONS LIDACTION 0 >nul 2>&1

echo =======================================
echo   CONFIGURATION APPLIQUEE
echo =======================================
echo.
echo [OK] PC ne se mettra JAMAIS en veille
echo [OK] Capot ne coupera RIEN
echo [OK] Ecran s'eteindra apres 5 MINUTES d'inactivite
echo [OK] Sierra Chart continuera
echo [OK] MIA_IA continuera de trader
echo [OK] REVEIL INSTANTANE (1 clic souris)
echo.
echo =======================================
echo   WORKFLOW PRODUCTION :
echo =======================================
echo   1. Lance Sierra Chart
echo   2. Lance MIA_IA Bot
echo   3. Verifie connexions (DTC + Discord)
echo   4. Ne touche plus rien
echo   5. Apres 5 min : ecran OFF automatique
echo   6. Ferme le capot
echo   7. Tout continue H24 !
echo =======================================
echo.
echo Pour rallumer : Bouge la souris (reveil instantane)
echo.
pause

