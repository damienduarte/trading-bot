@echo off
echo.
echo ======================================
echo   🧹 NETTOYAGE DU PROJET
echo ======================================
echo.
echo ⚠️  ATTENTION: Ce script va supprimer les fichiers obsolètes
echo 📁 Seuls les fichiers du bot levier intelligent seront conservés
echo.
echo 🗑️  Fichiers qui seront supprimés:
echo    • Anciens bots (multi_crypto_bot.py, test_*.py, etc.)
echo    • Scripts obsolètes (lancer_test_7jours.bat, etc.)
echo    • Guides obsolètes (GUIDE_*.md sauf levier intelligent)
echo    • Modules src/ non utilisés
echo.
set /p confirm="Voulez-vous continuer? (O/N): "
if /i not "%confirm%"=="O" if /i not "%confirm%"=="OUI" (
    echo.
    echo ❌ Nettoyage annulé
    pause
    exit /b 0
)

echo.
echo 🧹 Lancement du nettoyage...
echo.

cd /d "%~dp0"
python nettoyer_projet.py

if errorlevel 1 (
    echo.
    echo ❌ Erreur pendant le nettoyage
    pause
    exit /b 1
)

echo.
echo ✅ Nettoyage terminé avec succès!
echo 🎯 Projet optimisé pour le bot levier intelligent
echo.
pause
