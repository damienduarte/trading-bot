# 🤖 Bot de Trading ETH/USDC - Bitget

Bot de trading automatique pour ETH/USDC avec calcul des profits en temps réel.

## 🚀 Démarrage Rapide

### 1. Lancer le test 7 jours
```bash
# Méthode simple
Double-cliquez: lancer_test_7jours.bat

# Ou en terminal
python test_with_profits.py
```

### 2. Surveiller les profits
- **Dashboard Web**: http://localhost:5000
- **Terminal**: Affichage temps réel des gains/pertes
- **Rapports**: Dossier `reports/`

### 3. Analyser les résultats
```bash
# Méthode simple
Double-cliquez: voir_profits.bat

# Ou en terminal  
python analyze_profits.py
```

## 📁 Structure du Projet

```
Bot/
├── src/                          # Code source
│   ├── bot.py                   # Bot principal
│   ├── strategies.py            # Stratégies de trading
│   ├── exchange.py              # Interface Bitget
│   ├── portfolio.py             # Gestion portefeuille
│   ├── risk_manager.py          # Gestion des risques
│   ├── config.py                # Configuration
│   ├── bot_logger.py            # Logging
│   ├── dashboard.py             # Dashboard principal
│   └── test_dashboard.py        # Dashboard test
├── test_with_profits.py         # Test avec profits
├── analyze_profits.py           # Analyseur profits
├── analyze_results.py           # Analyseur général
├── lancer_test_7jours.bat      # Lanceur Windows
├── voir_profits.bat            # Voir profits
├── requirements.txt            # Dépendances
├── .env                        # Configuration API
└── GUIDE_PROFITS.md           # Guide détaillé
```

## 🛡️ Sécurité

- ✅ **Mode Paper Trading** par défaut
- ✅ **Capital virtuel**: 10,000 USDC
- ✅ **ETH/USDC** (conforme Europe)
- ✅ **0% risque financier**

## 💰 Fonctionnalités

### Trading
- **4 stratégies**: MA, RSI, MACD, Bollinger Bands
- **Gestion des risques** automatique
- **Stop-loss** et position sizing
- **Simulation réaliste** des prix

### Monitoring
- **Dashboard web** temps réel
- **Calcul des profits** instantané
- **Historique des trades**
- **Statistiques de performance**

### Rapports
- **Profits/Pertes** détaillés
- **Taux de réussite** des trades
- **Performance extrapolée**
- **Recommandations** d'optimisation

## 🎯 Objectifs de Performance

- **Court terme** (1 semaine): +2-5%
- **Moyen terme** (1 mois): +10-20%
- **Risque max**: -5%

## 📊 Exemple de Résultats

```
💰 RÉSULTAT FINANCIER:
   Capital initial: 10,000.00 USDC
   Portefeuille final: 10,247.32 USDC
   📈 PROFIT: +247.32 USDC (+2.47%)
   
📊 STATISTIQUES:
   Trades totaux: 15
   Taux de réussite: 60.0%
   Rendement annuel estimé: +89.5%
```

## ⚙️ Configuration

1. **Copiez** `.env.example` vers `.env`
2. **Ajoutez** vos clés API Bitget (optionnel pour tests)
3. **Mode paper** activé par défaut

## 🔧 Commandes Utiles

```bash
# Lancer test complet
python test_with_profits.py

# Analyser profits
python analyze_profits.py

# Analyser résultats généraux
python analyze_results.py

# Dashboard seul
python src/dashboard.py
```

---

**🎉 Prêt à trader ? Double-cliquez sur `lancer_test_7jours.bat` !**
