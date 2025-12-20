@echo off
title MIA IA SYSTEM - Build Production
color 0E

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║         🏗️  MIA IA SYSTEM - BUILD PRODUCTION                 ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Vérifier node_modules
if not exist "node_modules" (
    echo  📦 Installation des dependances...
    npm install
)

echo  🔨 Creation du build de production...
echo.

npm run build

if %errorlevel% neq 0 (
    echo.
    echo  ❌ ERREUR lors du build!
    pause
    exit /b 1
)

echo.
echo  ══════════════════════════════════════════════════════════════
echo.
echo  ✅ BUILD TERMINE AVEC SUCCES!
echo.
echo  📁 Le site statique est dans le dossier: out/
echo.
echo  🚀 Prochaines etapes pour Cloudflare Pages:
echo.
echo     1. Push ce projet sur GitHub
echo     2. Va sur https://dash.cloudflare.com
echo     3. Pages → Create a project → Connect to Git
echo     4. Selectionne ton repo GitHub
echo     5. Configure:
echo        - Build command: npm run build
echo        - Output directory: out
echo     6. Deploy!
echo.
echo  ══════════════════════════════════════════════════════════════
echo.
pause
