@echo off
cls

echo ================================================================
echo                STATUS MIA
echo ================================================================
echo.

cd /d D:\MIA_IA_system

echo  Processus Python en cours:
echo  ----------------------------------------------------------------
tasklist /FI "IMAGENAME eq python.exe" 2>nul | find "python.exe" >nul
if %errorlevel% == 0 (
    tasklist /FI "IMAGENAME eq python.exe"
    echo.
    echo  MIA est en cours d'execution
) else (
    echo  Aucun processus Python - MIA n'est pas lance
)

echo.
echo  ----------------------------------------------------------------
echo  Derniers logs (5 lignes):
echo  ----------------------------------------------------------------

powershell -Command "Get-ChildItem logs\__main__*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { Get-Content $_.FullName -Tail 5 }"

echo.
echo  ----------------------------------------------------------------
echo  Status contrats futures:
echo  ----------------------------------------------------------------
python -c "from config.futures_rollover import get_rollover_status; s=get_rollover_status(); print(f'   ES: {s[\"active_contracts\"][\"ES\"]}'); print(f'   NQ: {s[\"active_contracts\"][\"NQ\"]}'); print(f'   Prochain rollover: {s[\"days_until_rollover\"]} jours')" 2>nul

echo.
echo ================================================================
pause
