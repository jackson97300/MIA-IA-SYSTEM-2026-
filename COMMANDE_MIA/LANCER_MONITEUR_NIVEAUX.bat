@echo off
REM ========================================
REM LANCER MONITEUR NIVEAUX STANDALONE
REM ========================================
REM Script qui tourne en parallèle du bot
REM et logue les niveaux tradables en temps réel
REM
REM Créé: 10/12/2025
REM ========================================

echo.
echo ========================================
echo  MONITEUR NIVEAUX TEMPS REEL
echo  ES / NQ / RTY
echo ========================================
echo.
echo [INFO] Ce script tourne en parallele du bot
echo [INFO] Il logue dans: logs/niveaux_monitor.log
echo [INFO] Ctrl+C pour arreter
echo.

cd /d D:\MIA_IA_system

python core/niveaux_monitor.py

pause

