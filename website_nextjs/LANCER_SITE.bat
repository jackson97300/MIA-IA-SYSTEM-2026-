@echo off
title MIA IA SYSTEM - Site Web Next.js
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║              🤖 MIA IA SYSTEM - WEBSITE                      ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

:: Vérifier si Node.js est installé
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo  ❌ ERREUR: Node.js n'est pas installe!
    echo.
    echo  Telecharge Node.js depuis: https://nodejs.org/
    echo  Choisis la version LTS (recommandee)
    echo.
    pause
    exit /b 1
)

:: Afficher les versions
echo  ✅ Node.js detecte:
node --version
echo  ✅ npm detecte:
npm --version
echo.

:: Aller dans le dossier du projet
cd /d "%~dp0"

:: Vérifier si node_modules existe
if not exist "node_modules" (
    echo  📦 Installation des dependances...
    echo  (Cela peut prendre 1-2 minutes la premiere fois)
    echo.
    npm install
    if %errorlevel% neq 0 (
        echo.
        echo  ❌ ERREUR lors de l'installation!
        pause
        exit /b 1
    )
    echo.
    echo  ✅ Dependances installees!
    echo.
)

echo  ══════════════════════════════════════════════════════════════
echo.
echo  🚀 Lancement du serveur de developpement...
echo.
echo  📍 Le site sera accessible sur: http://localhost:3000
echo.
echo  💡 Pour arreter le serveur: Ctrl + C
echo.
echo  ══════════════════════════════════════════════════════════════
echo.

:: Ouvrir le navigateur après 3 secondes
start "" cmd /c "timeout /t 3 >nul && start http://localhost:3000"

:: Lancer le serveur
npm run dev

pause
