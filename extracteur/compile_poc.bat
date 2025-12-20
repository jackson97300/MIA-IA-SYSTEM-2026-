@echo off
REM ============================================================================
REM Script de compilation pour Test_DayChangePct_POC.cpp
REM ============================================================================

echo.
echo ========================================
echo COMPILATION POC DAY CHANGE PCT
echo ========================================
echo.

REM Vérifier si Developer Command Prompt est configuré
where cl.exe >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Compilateur MSVC non trouvé !
    echo.
    echo SOLUTION 1 : Utiliser "Developer Command Prompt for VS"
    echo SOLUTION 2 : Utiliser la compilation intégrée de Sierra Chart
    echo              (Analysis ^> Build Custom Studies DLL)
    echo.
    pause
    exit /b 1
)

echo [OK] Compilateur MSVC détecté
echo.

REM Définir les chemins
set SOURCE=Test_DayChangePct_POC.cpp
set OUTPUT=Test_DayChangePct_POC.dll
set SIERRA_PATH=C:\SierraChart

REM Vérifier que le fichier source existe
if not exist "%SOURCE%" (
    echo [ERREUR] Fichier source non trouvé : %SOURCE%
    echo.
    echo Assurez-vous d'exécuter ce script depuis le dossier extracteur
    echo.
    pause
    exit /b 1
)

echo [OK] Fichier source trouvé : %SOURCE%
echo.

REM Vérifier que Sierra Chart est installé
if not exist "%SIERRA_PATH%" (
    echo [ATTENTION] Sierra Chart non trouvé dans %SIERRA_PATH%
    echo.
    set /p SIERRA_PATH="Entrez le chemin de Sierra Chart (ex: C:\SC) : "
)

echo [OK] Sierra Chart path : %SIERRA_PATH%
echo.

REM Compiler
echo [COMPILATION] En cours...
echo.

cl.exe /LD /EHsc /O2 /MD ^
  /I"%SIERRA_PATH%" ^
  /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /D "_USRDLL" ^
  "%SOURCE%" ^
  /link /OUT:"%OUTPUT%" ^
  /MACHINE:X64 ^
  /SUBSYSTEM:WINDOWS ^
  /DLL

if %errorlevel% neq 0 (
    echo.
    echo [ERREUR] Compilation échouée !
    echo.
    echo VÉRIFICATIONS :
    echo - scsf.h existe dans %SIERRA_PATH%
    echo - Utilisez Developer Command Prompt for VS
    echo - Ou utilisez Build Custom Studies DLL de Sierra Chart
    echo.
    pause
    exit /b 1
)

echo.
echo [OK] Compilation réussie !
echo.

REM Copier dans Sierra Chart (optionnel)
set /p COPY_TO_SC="Copier la DLL dans Sierra Chart ? (O/N) : "
if /i "%COPY_TO_SC%"=="O" (
    if not exist "%SIERRA_PATH%\Data" mkdir "%SIERRA_PATH%\Data"
    copy /Y "%OUTPUT%" "%SIERRA_PATH%\Data\%OUTPUT%"

    if %errorlevel% equ 0 (
        echo.
        echo [OK] DLL copiée dans %SIERRA_PATH%\Data\
        echo.
    ) else (
        echo.
        echo [ATTENTION] Copie échouée - copiez manuellement
        echo.
    )
)

echo.
echo ========================================
echo PROCHAINES ÉTAPES :
echo ========================================
echo.
echo 1. Dans Sierra Chart, créer un Daily Chart pour NQ (ex: Chart #10)
echo 2. Sur votre chart intraday NQ, ajouter l'étude "Test Day Change %% POC"
echo 3. Configurer Input "Daily Chart Number" = 10
echo 4. Vérifier les logs dans Global Settings ^> Message Log
echo 5. Comparer avec CME/TradingView
echo.
echo Voir README_POC_TEST.md pour instructions détaillées
echo.
echo ========================================

pause
