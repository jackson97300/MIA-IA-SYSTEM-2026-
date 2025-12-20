@echo off
echo ========================================
echo    MIA Trading Copilot V7
echo    Version corrigee et amelioree
echo ========================================
echo.
echo Corrections V7:
echo  - Blind Spots BL 1-9 (aligne Sierra)
echo  - Config depuis trading_params.py
echo  - Sessions avec minutes precises
echo  - VIX Regime display
echo  - Intermarket ES/NQ sync
echo  - Gamma Side display
echo.
echo Lancement sur http://localhost:8503
echo.

cd /d D:\MIA_IA_system
python -m streamlit run core/mia_trading_copilot_v7.py --server.port 8503

pause
