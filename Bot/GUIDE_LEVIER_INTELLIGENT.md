# 🚀 Guide du Bot Levier Intelligent

## 🎯 Fonctionnalités Avancées

### ⚡ Système de Lev### Métriques de Performance

### Indicateurs Clés
- **Win Rate** : Taux de trades gagnants
- **P&L Global** : Profit/Perte total (après frais de funding)
- **P&L Net** : Profit/Perte après déduction des funding rates
- **Max Levier Utilisé** : Levier maximum atteint (max 10x)
- **Trades avec Levier** : Nombre de trades amplifiés
- **Marge Utilisée** : Capital en garantie
- **Frais Funding Totaux** : Coûts cumulés des positions longuestatif
- **ETH**: Levier max 10x (confiance min 75%)
- **BTC**: Levier max 10x (confiance min 80%)  
- **SOL**: Levier max 10x (confiance min 70%)
- **XRP**: Levier max 10x (confiance min 65%)

### 🧠 Intelligence Artificielle
Le bot analyse en temps réel :
- 📈 **Tendances** : Analyse multi-périodes (5, 10, 20 points)
- 📊 **Volatilité** : Calcul dynamique sur 20 derniers prix
- 🎯 **Score de confiance** : IA combine tous les signaux
- ⚡ **Levier optimal** : Adapté selon confiance et volatilité
- 💰 **Funding rates** : Prise en compte des frais de financement réels

### 🛡️ Gestion des Risques
- **Position sizing** : Max 10% capital par trade avec levier
- **Stop loss serré** : 1.5% pour trades avec levier
- **Volatilité** : Réduction automatique du levier si > 8%
- **Circuit breaker** : Arrêt si volatilité > 15%
- **Funding rates** : Calcul automatique des frais sur positions longues
- **Levier max global** : Limité à 10x pour sécurité optimale

## 🚀 Comment Utiliser

### 1. Lancement Simple
```bash
double-click: lancer_levier_intelligent.bat
```

### 2. Interface Web
- **URL** : http://localhost:5005
- **Actualisation** : Automatique toutes les 25 secondes
- **API** : http://localhost:5005/api/intelligent-crypto

### 3. Supervision
Le dashboard affiche :
- 💰 **Portefeuille global** avec P&L
- 📊 **Score de confiance** par crypto
- ⚡ **Levier recommandé vs utilisé**
- 📈 **Statistiques de trading**
- 🛡️ **Niveau de risque global**

## 📊 Stratégie de Trading

### Conditions pour Levier
1. **Score confiance** ≥ seuil minimum crypto
2. **Levier recommandé** > 2.0x
3. **Capital disponible** > $500
4. **Aucune position ouverte**

### Exemple de Décision IA
```
ETH/USDC à $4,400
- Tendance: STRONG_UP (80% confiance)
- Volatilité: 3.2% (acceptable)
- Score global: 85%
- Levier recommandé: 8.5x
- Funding rate: +0.015% (8h)
- Coût funding/jour: $3.60
→ ACHAT avec 8x de levier
```

### Types de Trades
- **🔵 SPOT** : Confiance 60-75%, pas de levier
- **⚡ LEVIER** : Confiance >75%, levier 2x-10x avec calcul funding

## ⚙️ Configuration Avancée

### Modifier les Paramètres
Éditer `config/intelligent_leverage_config.json` :
```json
{
  "trading": {
    "max_leverage": 20,
    "min_confidence_for_leverage": 75.0,
    "base_amount": 1000.0
  },
  "risk": {
    "max_portfolio_risk_pct": 15.0,
    "daily_loss_limit_pct": 5.0
  }
}
```

### Limites de Sécurité
- **Marge max** : 30% du capital total
- **Perte quotidienne** : Arrêt si > 5%
- **Positions simultanées** : Max 2 avec levier
- **Exposition par crypto** : Max 25% du portfolio

## 📈 Métriques de Performance

### Indicateurs Clés
- **Win Rate** : Taux de trades gagnants
- **P&L Global** : Profit/Perte total
- **Max Levier Utilisé** : Levier maximum atteint
- **Trades avec Levier** : Nombre de trades amplifiés
- **Marge Utilisée** : Capital en garantie

### Analyse des Risques
- 🟢 **FAIBLE** : Levier < 2x, marge < 10%
- 🟡 **MOYEN** : Levier 2-5x, marge 10-20%  
- 🔴 **ÉLEVÉ** : Levier > 5x, marge > 20%

## 🔧 Dépannage

### Problèmes Courants
1. **Prix non récupérés** : Vérifier connexion internet
2. **Levier non appliqué** : Score confiance trop bas
3. **Erreur API** : Attendre cooldown (5 min)

### Logs Utiles
```bash
python diagnostic.py  # Diagnostic complet
```

### Support APIs
- **Bitget** : Prix temps réel primaire
- **Binance** : Prix temps réel backup
- **Mode Paper Trading** : Simulation sans risque

## 🎯 Conseils d'Utilisation

### Pour Débuter
1. **Observer** d'abord les recommandations IA
2. **Comprendre** les scores de confiance
3. **Analyser** les corrélations prix/levier
4. **Ajuster** les seuils selon votre profil

### Optimisation
- **Crypto stable** → Augmenter levier max
- **Marché volatil** → Réduire seuils confiance
- **Bull market** → Augmenter exposition
- **Bear market** → Réduire tous les paramètres

## 🚨 Avertissements

⚠️ **RISQUES DU LEVIER**
- Amplification des gains ET des pertes
- Liquidation possible si stop loss touché
- Volatilité élevée = risque élevé

💡 **RECOMMANDATIONS**
- Commencer avec levier faible (2-3x)
- Surveiller en permanence le dashboard
- Respecter la gestion des risques
- Ne jamais risquer plus que votre tolérance

---

🤖 **Bot Levier Intelligent v2.0**  
📧 Support : Consultez diagnostic.py pour aide  
🌐 Dashboard : localhost:5005  
⚡ Trading intelligent avec IA
