#!/usr/bin/env python3
"""
🧹 NETTOYAGE DU PROJET - Tri et suppression des fichiers obsolètes
Version Bot Levier Intelligent uniquement
"""

import os
import shutil
from datetime import datetime

def main():
    print("🧹 NETTOYAGE DU PROJET BOT LEVIER INTELLIGENT")
    print("=" * 60)
    print()
    
    # Fichiers ESSENTIELS à garder
    FICHIERS_ESSENTIELS = {
        # Bot principal
        'intelligent_leverage_bot.py',
        'lancer_levier_intelligent.bat',
        
        # Configuration
        'config/intelligent_leverage_config.py',
        
        # Documentation
        'GUIDE_LEVIER_INTELLIGENT.md',
        'README.md',
        
        # Dépendances
        'requirements.txt',
        
        # Utilitaires
        'diagnostic.py',
        
        # Git et environnement
        '.gitignore',
        '.env',
        '.env.example',
        
        # Dossiers de données
        'logs/',
        'reports/',
        '.github/',
        '.venv/',
        '__pycache__/',
        'config/',
        'src/__pycache__/'
    }
    
    # Fichiers OBSOLÈTES à supprimer
    FICHIERS_OBSOLETES = [
        # Anciens bots
        'multi_crypto_bot.py',
        'test_with_profits.py', 
        'dashboard_real_prices.py',
        'dashboard_profits.py',
        'test_dashboard_simple.py',
        'test_profits_simple.py',
        'auto_start_7days.py',
        'real_week_test.py',
        'test_final.py',
        'test_data_sources.py',
        'analyze_profits.py',
        'analyze_results.py',
        'analyze_trading_setup.py',
        
        # Scripts obsolètes
        'lancer_test_7jours.bat',
        'voir_profits.bat',
        'creer_package_portable.bat',
        'installer_linux.sh',
        'installer_windows.bat',
        
        # Guides obsolètes
        'GUIDE_DEMARRAGE.md',
        'GUIDE_DEPLOYMENT.md',
        'GUIDE_PROFITS.md',
        'GUIDE_TEST_7JOURS.md',
        'README_FINAL.md',
        
        # Modules src/ obsolètes
        'src/bot.py',
        'src/bot_logger.py',
        'src/config.py',
        'src/dashboard.py',
        'src/exchange.py',
        'src/portfolio.py',
        'src/risk_manager.py',
        'src/strategies.py',
        'src/test_dashboard.py',
        'src/__init__.py',
        
        # Fichiers de version
        '1.0.0', '1.24.0', '2.0.0', '2.3.0', '4.0.0', '41.0.0'
    ]
    
    base_path = os.getcwd()
    files_deleted = []
    files_kept = []
    
    print("📋 Analyse des fichiers...")
    print()
    
    # Supprimer les fichiers obsolètes
    for file_path in FICHIERS_OBSOLETES:
        full_path = os.path.join(base_path, file_path)
        
        if os.path.exists(full_path):
            try:
                if os.path.isfile(full_path):
                    os.remove(full_path)
                    files_deleted.append(file_path)
                    print(f"🗑️  Supprimé: {file_path}")
                elif os.path.isdir(full_path):
                    shutil.rmtree(full_path)
                    files_deleted.append(file_path)
                    print(f"📁 Dossier supprimé: {file_path}")
            except Exception as e:
                print(f"❌ Erreur suppression {file_path}: {e}")
    
    # Lister les fichiers conservés
    print("\n" + "="*60)
    print("✅ FICHIERS CONSERVÉS (Essentiels)")
    print("="*60)
    
    for root, dirs, files in os.walk(base_path):
        # Ignorer certains dossiers
        dirs[:] = [d for d in dirs if not d.startswith('.') or d in ['.github']]
        
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), base_path)
            rel_path = rel_path.replace('\\', '/')
            
            # Vérifier si c'est un fichier essentiel
            is_essential = False
            for essential in FICHIERS_ESSENTIELS:
                if essential.endswith('/'):
                    if rel_path.startswith(essential):
                        is_essential = True
                        break
                elif rel_path == essential:
                    is_essential = True
                    break
            
            if is_essential or file.endswith(('.log', '.json')):
                files_kept.append(rel_path)
                size = os.path.getsize(os.path.join(root, file))
                size_str = f"{size:,} bytes" if size < 1024 else f"{size/1024:.1f} KB"
                print(f"✅ {rel_path:<40} ({size_str})")
    
    # Nettoyer le dossier src/ complètement s'il est vide
    src_path = os.path.join(base_path, 'src')
    if os.path.exists(src_path):
        try:
            # Vérifier si le dossier src est presque vide (juste __pycache__)
            src_contents = os.listdir(src_path)
            if not src_contents or src_contents == ['__pycache__']:
                shutil.rmtree(src_path)
                files_deleted.append('src/')
                print(f"📁 Dossier vide supprimé: src/")
        except Exception as e:
            print(f"⚠️  Impossible de supprimer src/: {e}")
    
    # Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DU NETTOYAGE")
    print("="*60)
    print(f"🗑️  Fichiers supprimés: {len(files_deleted)}")
    print(f"✅ Fichiers conservés: {len(files_kept)}")
    print()
    
    if files_deleted:
        print("🗑️  FICHIERS SUPPRIMÉS:")
        for file in sorted(files_deleted):
            print(f"   • {file}")
        print()
    
    print("🎯 STRUCTURE FINALE DU PROJET:")
    print("   📂 Bot Levier Intelligent")
    print("   ├── intelligent_leverage_bot.py    (Bot principal)")
    print("   ├── lancer_levier_intelligent.bat  (Lanceur)")
    print("   ├── config/")
    print("   │   └── intelligent_leverage_config.py")
    print("   ├── GUIDE_LEVIER_INTELLIGENT.md    (Documentation)")
    print("   ├── requirements.txt               (Dépendances)")
    print("   ├── diagnostic.py                  (Diagnostic)")
    print("   ├── logs/                          (Journaux)")
    print("   └── reports/                       (Rapports)")
    print()
    
    print("✨ Nettoyage terminé ! Projet optimisé pour le bot levier intelligent.")
    print("🚀 Utilisez: lancer_levier_intelligent.bat")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Nettoyage interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur pendant le nettoyage: {e}")
    
    input("\n👆 Appuyez sur Entrée pour fermer...")
