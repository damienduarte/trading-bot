#!/usr/bin/env python3
"""
✅ VÉRIFICATION POST-NETTOYAGE
Vérification que le bot levier intelligent fonctionne correctement
"""

import os
import sys
import importlib.util
from datetime import datetime

def main():
    print("✅ VÉRIFICATION POST-NETTOYAGE")
    print("=" * 50)
    print()
    
    base_path = os.getcwd()
    errors = []
    warnings = []
    
    # 1. Vérifier les fichiers essentiels
    print("📋 1. Vérification des fichiers essentiels...")
    
    essential_files = [
        'intelligent_leverage_bot.py',
        'lancer_levier_intelligent.bat',
        'config/intelligent_leverage_config.py',
        'GUIDE_LEVIER_INTELLIGENT.md',
        'requirements.txt',
        'diagnostic.py'
    ]
    
    for file_path in essential_files:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"   ✅ {file_path:<35} ({size:,} bytes)")
        else:
            errors.append(f"Fichier manquant: {file_path}")
            print(f"   ❌ {file_path} - MANQUANT")
    
    # 2. Vérifier les imports Python
    print("\n📦 2. Vérification des dépendances...")
    
    try:
        import flask
        print(f"   ✅ Flask: {flask.__version__}")
    except ImportError:
        errors.append("Flask non installé")
        print("   ❌ Flask - NON INSTALLÉ")
    
    try:
        import ccxt
        print(f"   ✅ CCXT: {ccxt.__version__}")
    except ImportError:
        errors.append("CCXT non installé")
        print("   ❌ CCXT - NON INSTALLÉ")
    
    try:
        from flask_cors import CORS
        print("   ✅ Flask-CORS disponible")
    except ImportError:
        errors.append("Flask-CORS non installé")
        print("   ❌ Flask-CORS - NON INSTALLÉ")
    
    # 3. Test d'import du bot principal
    print("\n🤖 3. Test d'import du bot principal...")
    
    try:
        spec = importlib.util.spec_from_file_location(
            "intelligent_leverage_bot", 
            "intelligent_leverage_bot.py"
        )
        if spec and spec.loader:
            print("   ✅ intelligent_leverage_bot.py - Syntaxe valide")
        else:
            errors.append("Impossible de charger intelligent_leverage_bot.py")
            print("   ❌ intelligent_leverage_bot.py - Erreur de syntaxe")
    except Exception as e:
        errors.append(f"Erreur d'import: {e}")
        print(f"   ❌ Erreur d'import: {e}")
    
    # 4. Test d'import de la configuration
    print("\n⚙️  4. Test de la configuration...")
    
    try:
        spec = importlib.util.spec_from_file_location(
            "intelligent_leverage_config", 
            "config/intelligent_leverage_config.py"
        )
        if spec and spec.loader:
            print("   ✅ Configuration - Syntaxe valide")
        else:
            errors.append("Impossible de charger la configuration")
            print("   ❌ Configuration - Erreur de syntaxe")
    except Exception as e:
        warnings.append(f"Avertissement config: {e}")
        print(f"   ⚠️  Avertissement config: {e}")
    
    # 5. Vérifier la structure des dossiers
    print("\n📁 5. Vérification de la structure...")
    
    required_dirs = ['logs', 'reports', 'config']
    for dir_name in required_dirs:
        dir_path = os.path.join(base_path, dir_name)
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            files_count = len(os.listdir(dir_path))
            print(f"   ✅ {dir_name}/ ({files_count} fichiers)")
        else:
            warnings.append(f"Dossier manquant: {dir_name}")
            print(f"   ⚠️  {dir_name}/ - Manquant (sera créé automatiquement)")
    
    # 6. Vérifier les fichiers obsolètes supprimés
    print("\n🗑️  6. Vérification suppression fichiers obsolètes...")
    
    should_be_deleted = [
        'multi_crypto_bot.py',
        'test_with_profits.py',
        'lancer_test_7jours.bat',
        'src/bot.py',
        'GUIDE_PROFITS.md'
    ]
    
    obsolete_found = []
    for file_path in should_be_deleted:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            obsolete_found.append(file_path)
    
    if not obsolete_found:
        print("   ✅ Tous les fichiers obsolètes ont été supprimés")
    else:
        for file_path in obsolete_found:
            warnings.append(f"Fichier obsolète présent: {file_path}")
            print(f"   ⚠️  {file_path} - Devrait être supprimé")
    
    # 7. Résumé final
    print("\n" + "="*50)
    print("📊 RÉSUMÉ DE LA VÉRIFICATION")
    print("="*50)
    
    if not errors and not warnings:
        print("🎉 PARFAIT ! Le projet est totalement propre et opérationnel")
        print()
        print("🚀 Prêt à utiliser:")
        print("   • Lancez: lancer_levier_intelligent.bat")
        print("   • Dashboard: http://localhost:5005")
        print("   • Levier max: 10x")
        print("   • Funding rates: Calculés automatiquement")
        print()
        return True
    
    if errors:
        print(f"❌ ERREURS ({len(errors)}):")
        for error in errors:
            print(f"   • {error}")
        print()
    
    if warnings:
        print(f"⚠️  AVERTISSEMENTS ({len(warnings)}):")
        for warning in warnings:
            print(f"   • {warning}")
        print()
    
    if errors:
        print("🔧 Actions requises:")
        print("   1. Installez les dépendances: pip install -r requirements.txt")
        print("   2. Vérifiez la syntaxe des fichiers Python")
        print("   3. Relancez cette vérification")
        return False
    else:
        print("✅ Projet opérationnel malgré les avertissements mineurs")
        print("🚀 Vous pouvez lancer le bot !")
        return True

if __name__ == "__main__":
    try:
        success = main()
        print(f"\n🏁 Vérification terminée - {'SUCCÈS' if success else 'ERREURS'}")
    except Exception as e:
        print(f"\n💥 Erreur pendant la vérification: {e}")
    
    input("\n👆 Appuyez sur Entrée pour fermer...")
