@echo off
cls

echo ================================================================
echo           MISE A JOUR ROLLOVER CONTRATS FUTURES
echo ================================================================
echo.
echo  CALENDRIER DES ROLLOVERS 2025:
echo     Mars (H)      - Mi-mars     - Passer a Juin (M)
echo     Juin (M)      - Mi-juin     - Passer a Septembre (U)
echo     Septembre (U) - Mi-sept     - Passer a Decembre (Z)
echo     Decembre (Z)  - Mi-dec      - Passer a Mars (H) annee suivante
echo.
echo ================================================================
echo.
echo  ETAPES A SUIVRE:
echo.
echo  1. ARRETER le bot MIA (STOP_MIA.bat)
echo.
echo  2. Dans SIERRA CHART, changer les symboles:
echo     ESZ24  -  ESH25  (ou le nouveau contrat)
echo     NQZ24  -  NQH25
echo     RTYZ24 -  RTYH25
echo.
echo  3. Ouvrir config\futures_rollover.py et modifier:
echo     ACTIVE_CONTRACTS = {
echo         'ES': 'ESH25',   -- Nouveau symbole
echo         'NQ': 'NQH25',
echo         'RTY': 'RTYH25',
echo     }
echo.
echo  4. Modifier aussi ACTIVE_YEAR si changement d'annee:
echo     ACTIVE_YEAR = 25  -- Annee du contrat (25 = 2025)
echo.
echo  5. REDEMARRER le bot (START_MIA_VISIBLE.bat)
echo.
echo ================================================================
echo.

REM Afficher le status actuel
echo  STATUS ACTUEL:
python -c "from config.futures_rollover import get_rollover_status; import json; print(json.dumps(get_rollover_status(), indent=2, default=str))" 2>nul
if errorlevel 1 (
    echo     Impossible de lire le status.
)

echo.
echo ================================================================
pause
