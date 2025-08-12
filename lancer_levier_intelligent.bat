@echo off
echo.
echo ======================================
echo   🚀 BOT LEVIER INTELLIGENT
echo ======================================
echo.
echo 🎯 Lancement du bot multi-cryptos avec levier adaptatif...
echo 📊 ETH • BTC • SOL • XRP
echo ⚡ Levier intelligent jusqu'à 25x
echo 🧠 IA d'analyse des signaux
echo.

cd /d "%~dp0"

echo 🔍 Vérification de l'environnement Python...
python --version
if errorlevel 1 (
    echo ❌ Python n'est pas installé ou accessible
    pause
    exit /b 1
)

echo.
echo 📦 Installation/mise à jour des dépendances...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Erreur installation des dépendances
    pause
    exit /b 1
)

echo.
echo 🔧 Création de la configuration...
python config\intelligent_leverage_config.py
if errorlevel 1 (
    echo ⚠️  Erreur configuration, continuation avec config par défaut
)

echo.
echo ⚡ LANCEMENT DU BOT LEVIER INTELLIGENT
echo 🌐 Dashboard: http://localhost:5005
echo 📊 Analyse IA en temps réel
echo.

timeout /t 3 /nobreak

python intelligent_leverage_bot.py

if errorlevel 1 (
    echo.
    echo ❌ Erreur lors de l'exécution du bot
    echo 📋 Diagnostic en cours...
    echo.
    timeout /t 2 /nobreak
    python diagnostic.py
    echo.
    echo 💡 Solutions suggérées:
    echo    1. Vérifier la connexion internet
    echo    2. Réinstaller les dépendances: pip install -r requirements.txt
    echo    3. Vérifier les APIs Bitget/Binance
    echo.
)

echo.
echo 🏁 Bot arrêté
pause
