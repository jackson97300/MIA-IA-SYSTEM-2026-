@echo off
REM ═══════════════════════════════════════════════════════════════
REM  🎯 MIA TRADING COPILOT V5 - LAUNCHER
REM  Version avec DOM PRESSURE + NEXT WALL + TOUTES DONNEES
REM ═══════════════════════════════════════════════════════════════

echo.
echo  🎯 MIA TRADING COPILOT V5
echo  ══════════════════════════════════════════════════════════════
echo  Features: NEXT WALL, DOM Pressure, Grosses Mains, EMA lisse
echo.

cd /d D:\MIA_IA_system

echo  Lancement sur http://localhost:8503
echo  Appuyez sur Ctrl+C pour arreter
echo.

python -m streamlit run core/mia_trading_copilot_v5.py --server.port 8503

pause
