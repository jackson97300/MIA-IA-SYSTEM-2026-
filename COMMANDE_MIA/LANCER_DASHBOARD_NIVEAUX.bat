@echo off
REM ========================================
REM LANCER DASHBOARD NIVEAUX MULTI-SYMBOLES
REM ========================================
REM Script pour démarrer le dashboard Streamlit
REM qui affiche les niveaux MenthorQ pour ES/NQ/RTY
REM
REM Créé: 10/12/2025
REM ========================================

echo.
echo ========================================
echo  DASHBOARD NIVEAUX TEMPS REEL
echo  ES / NQ / RTY
echo ========================================
echo.

cd /d D:\MIA_IA_system

echo [INFO] Lancement du dashboard Streamlit...
echo [INFO] URL: http://localhost:8501
echo [INFO] Appuyez sur Ctrl+C pour arreter
echo.

REM Utiliser python -m streamlit car streamlit n'est pas dans PATH
python -m streamlit run core/dashboard_niveaux_multi_symbols.py

pause
