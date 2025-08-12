#!/usr/bin/env python3
print("=== TEST DE DIAGNOSTIC ===")

try:
    print("1. Test des imports de base...")
    import os, sys, time
    print("   ✅ Imports standard OK")
    
    print("2. Test ajout path src...")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(current_dir, 'src')
    sys.path.insert(0, src_path)
    print(f"   ✅ Path src ajouté: {src_path}")
    
    print("3. Test import config...")
    from config import Config
    print("   ✅ Config importée")
    
    print("4. Test import logger...")
    from bot_logger import Logger
    print("   ✅ Logger importé")
    
    print("5. Test Flask...")
    from flask import Flask
    print("   ✅ Flask importé")
    
    print("6. Test dashboard...")
    from test_dashboard import TestDashboard
    print("   ✅ TestDashboard importé")
    
    print("7. Test création config...")
    config = Config()
    print(f"   ✅ Config créée, mode: {config.mode}")
    
    print("\n🎉 TOUS LES TESTS PASSÉS!")
    print("Le problème n'est pas dans les imports.")
    
except Exception as e:
    print(f"❌ Erreur: {e}")
    import traceback
    traceback.print_exc()
