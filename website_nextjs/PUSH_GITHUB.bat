@echo off
title MIA IA SYSTEM - Push GitHub
color 0B

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║                                                              ║
echo  ║         🚀 MIA IA SYSTEM - PUSH GITHUB                       ║
echo  ║                                                              ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.

cd /d "%~dp0"

:: Vérifier si Git est installé
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo  ❌ ERREUR: Git n'est pas installe!
    echo.
    echo  Telecharge Git depuis: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

echo  ✅ Git detecte:
git --version
echo.

:: Vérifier si un remote existe
git remote -v >nul 2>&1
if %errorlevel% neq 0 (
    echo  ⚠️  Aucun remote GitHub configure
    echo.
    echo  📋 INSTRUCTIONS:
    echo.
    echo  1. Va sur https://github.com
    echo  2. Cree un nouveau repository (ex: mia-ia-system-website)
    echo  3. Copie l'URL du repo (ex: https://github.com/ton-user/mia-ia-system-website.git)
    echo  4. Relance ce script et entre l'URL quand demande
    echo.
    set /p REPO_URL="Entrez l'URL du repository GitHub: "
    if "%REPO_URL%"=="" (
        echo  ❌ URL vide, annulation...
        pause
        exit /b 1
    )
    echo.
    echo  🔗 Ajout du remote...
    git remote add origin "%REPO_URL%"
    echo  ✅ Remote ajoute!
    echo.
)

:: Afficher le remote actuel
echo  📍 Remote actuel:
git remote -v
echo.

:: Vérifier s'il y a des changements
git status --short >nul 2>&1
if %errorlevel% equ 0 (
    echo  📝 Changements detectes, ajout au commit...
    git add .
    echo.
    set /p COMMIT_MSG="Message du commit (ou Enter pour 'update'): "
    if "%COMMIT_MSG%"=="" set COMMIT_MSG=update
    git commit -m "%COMMIT_MSG%"
    echo.
)

:: Push vers GitHub
echo  🚀 Push vers GitHub...
echo.
git push -u origin master
if %errorlevel% neq 0 (
    echo.
    echo  ⚠️  Si c'est la premiere fois, essayez:
    echo     git push -u origin main
    echo.
    echo  Ou si le repo utilise 'main' au lieu de 'master':
    git branch -M main
    git push -u origin main
)

echo.
echo  ══════════════════════════════════════════════════════════════
echo.
echo  ✅ PUSH TERMINE!
echo.
echo  📍 Votre code est maintenant sur GitHub
echo.
echo  ══════════════════════════════════════════════════════════════
echo.
pause
