@echo off
REM ═══════════════════════════════════════════════════════════════════════════════
REM              CONFIGURATION REDÉMARRAGE AUTO APRÈS BSOD
REM ═══════════════════════════════════════════════════════════════════════════════
REM
REM Ce script configure Windows pour:
REM 1. Redémarrer automatiquement après un écran bleu (BSOD)
REM 2. Ne pas attendre indéfiniment sur l'écran d'erreur
REM
REM EXÉCUTER EN ADMINISTRATEUR!
REM
REM ═══════════════════════════════════════════════════════════════════════════════

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                                                              ║
echo ║     🔄 CONFIGURATION REDÉMARRAGE AUTO WINDOWS               ║
echo ║                                                              ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Vérifier les droits admin
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ ERREUR: Ce script doit être exécuté en ADMINISTRATEUR!
    echo.
    echo    Clic droit sur le fichier ^> "Exécuter en tant qu'administrateur"
    echo.
    pause
    exit /b 1
)

echo ✅ Droits administrateur OK
echo.

REM ═══════════════════════════════════════════════════════════════
REM              CONFIGURATION REGISTRE
REM ═══════════════════════════════════════════════════════════════

echo 📝 Configuration du redémarrage automatique...
echo.

REM Activer le redémarrage automatique après crash
reg add "HKLM\SYSTEM\CurrentControlSet\Control\CrashControl" /v AutoReboot /t REG_DWORD /d 1 /f
if %errorLevel% neq 0 (
    echo ❌ Erreur configuration AutoReboot
) else (
    echo ✅ AutoReboot activé
)

REM Écrire un mini dump (pour diagnostic si besoin)
reg add "HKLM\SYSTEM\CurrentControlSet\Control\CrashControl" /v CrashDumpEnabled /t REG_DWORD /d 3 /f
if %errorLevel% neq 0 (
    echo ❌ Erreur configuration CrashDump
) else (
    echo ✅ Mini dump activé (pour diagnostic)
)

REM Désactiver l'affichage de l'écran bleu pendant longtemps
reg add "HKLM\SYSTEM\CurrentControlSet\Control\CrashControl" /v DisplayParameters /t REG_DWORD /d 0 /f

echo.

REM ═══════════════════════════════════════════════════════════════
REM              PARAMÈTRES SYSTÈME
REM ═══════════════════════════════════════════════════════════════

echo 📝 Configuration des paramètres système...
echo.

REM Utiliser wmic pour configurer (méthode alternative)
wmic recoveros set AutoReboot = True >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ WMIC AutoReboot configuré
)

echo.

REM ═══════════════════════════════════════════════════════════════
REM              VÉRIFICATION
REM ═══════════════════════════════════════════════════════════════

echo ════════════════════════════════════════════════════════════════
echo    VÉRIFICATION DE LA CONFIGURATION:
echo ════════════════════════════════════════════════════════════════
echo.

echo 🔍 Lecture des paramètres actuels...
echo.

reg query "HKLM\SYSTEM\CurrentControlSet\Control\CrashControl" /v AutoReboot 2>nul
reg query "HKLM\SYSTEM\CurrentControlSet\Control\CrashControl" /v CrashDumpEnabled 2>nul

echo.
echo ════════════════════════════════════════════════════════════════
echo    RÉSUMÉ:
echo ════════════════════════════════════════════════════════════════
echo    ✅ Windows redémarrera automatiquement après un BSOD
echo    ✅ Un mini dump sera créé pour diagnostic
echo    ✅ L'écran bleu ne restera pas affiché indéfiniment
echo ════════════════════════════════════════════════════════════════
echo.
echo ✅ CONFIGURATION TERMINÉE!
echo.
echo ⚠️  Un redémarrage de Windows est recommandé pour appliquer
echo     tous les changements.
echo.
set /p REBOOT_NOW="🔄 Redémarrer Windows maintenant? (O/N): "
if /i "%REBOOT_NOW%"=="O" (
    echo.
    echo 🔄 Redémarrage dans 10 secondes...
    shutdown /r /t 10 /c "Redémarrage pour appliquer configuration anti-BSOD"
)
echo.
pause
