@echo off
echo ========================================
echo    INSTALLATION MIA_IA_SYSTEM SUR PORTABLE
echo ========================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python n'est pas installé!
    echo Veuillez installer Python 3.11 depuis https://python.org
    echo Assurez-vous de cocher "Add to PATH" lors de l'installation
    pause
    exit /b 1
)

REM Vérifier si Git est installé
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Git n'est pas installé!
    echo Veuillez installer Git depuis https://git-scm.com
    pause
    exit /b 1
)

echo [1/8] Création du dossier de travail...
if not exist "D:\MIA_IA_system" mkdir "D:\MIA_IA_system"
cd /d "D:\MIA_IA_system"

echo [2/8] Clonage du repository GitHub...
git clone https://github.com/jackson97300/MIA_IA_system_mentor_q.git .
if %errorlevel% neq 0 (
    echo ❌ Erreur lors du clonage Git!
    pause
    exit /b 1
)

echo [3/8] Création de l'environnement virtuel Python...
python -m venv venv
if %errorlevel% neq 0 (
    echo ❌ Erreur lors de la création de l'environnement virtuel!
    pause
    exit /b 1
)

echo [4/8] Activation de l'environnement virtuel...
call venv\Scripts\activate.bat

echo [5/8] Mise à jour de pip...
python -m pip install --upgrade pip

echo [6/8] Installation des dépendances de base...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ⚠ Erreur lors de l'installation des dépendances de base
    echo Continuons avec les dépendances ML...
)

echo [7/8] Installation des dépendances ML...
pip install xgboost lightgbm catboost scikit-learn pandas numpy
pip install stable-baselines3 torch gymnasium
pip install psutil matplotlib seaborn
if %errorlevel% neq 0 (
    echo ⚠ Erreur lors de l'installation des dépendances ML
    echo Vérifiez manuellement les installations
)

echo [8/8] Test de l'installation...
cd DATASET
python -c "import xgboost, lightgbm, sklearn, pandas, numpy; print('✅ Toutes les dépendances ML sont installées!')"
if %errorlevel% neq 0 (
    echo ⚠ Certaines dépendances ML ne sont pas installées correctement
)

echo.
echo ========================================
echo        INSTALLATION TERMINÉE
echo ========================================
echo.
echo Prochaines étapes:
echo 1. Transférer les données depuis le PC fixe
echo 2. Configurer Cursor avec vos settings
echo 3. Tester le pipeline ML
echo.
echo Commandes de test:
echo   cd DATASET
echo   python policy_overlay_v2.py
echo   python test_pipeline.py
echo.
echo Pour activer l'environnement virtuel:
echo   D:\MIA_IA_system\venv\Scripts\activate.bat
echo.
pause
