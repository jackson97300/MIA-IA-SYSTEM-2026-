@echo off
chcp 65001 >nul
echo ========================================
echo    MIA IA SYSTEM - Site Web Officiel
echo    Landing Page + Authentification
echo ========================================
echo.
echo    Site local: http://localhost:8504
echo.
echo    NOTE: Le Copilot V7 tourne sur le port 8503
echo          Le site web tourne sur le port 8504
echo.
echo ========================================
echo.
echo Lancement du site web...
echo.

cd /d D:\MIA_IA_system\website

REM Activer l'environnement virtuel si existant
if exist "..\venv\Scripts\activate.bat" (
    call ..\venv\Scripts\activate.bat
)

REM Lancer Streamlit
python -m streamlit run app.py --server.port 8504 --server.headless true --browser.gatherUsageStats false

pause



