@echo off
:: MIA BOT - LOGS EN TEMPS REEL

title MIA - LOGS

echo.
echo ================================================================
echo            LOGS DU BOT MIA (Temps Reel)
echo            Appuyez sur Ctrl+C pour arreter
echo ================================================================
echo.

cd /d D:\MIA_IA_system

:: Trouver le dernier fichier log
for /f "delims=" %%f in ('dir /b /o-d "logs\__main__*.log" 2^>nul') do (
    echo Lecture de: logs\%%f
    echo ================================================================
    echo.
    powershell -Command "Get-Content 'logs\%%f' -Wait -Tail 50"
    goto :end
)

echo Aucun fichier log trouve!
echo Assurez-vous que le bot est demarre.

:end
pause
