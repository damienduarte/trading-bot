#!/usr/bin/env python3
"""
🚀 BOT MULTI-CRYPTOS AVEC LEVIER INTELLIGENT
Trading avec analyse des signaux et levier adaptatif
"""

from flask import Flask, jsonify, render_template_string
from flask_cors import CORS
import requests
import time
import threading
from datetime import datetime, timedelta
import ccxt
import random
import math

app = Flask(__name__)
CORS(app)

# Configuration des paires avec levier max autorisé (Plus de risque)
TRADING_PAIRS = {
    'ETH/USDC': {'name': 'Ethereum', 'icon': '🔸', 'max_leverage': 10, 'min_confidence': 65},
    'BTC/USDC': {'name': 'Bitcoin', 'icon': '₿', 'max_leverage': 10, 'min_confidence': 70},
    'SOL/USDC': {'name': 'Solana', 'icon': '◐', 'max_leverage': 10, 'min_confidence': 60},
    'XRP/USDC': {'name': 'Ripple', 'icon': '◇', 'max_leverage': 10, 'min_confidence': 55}
}

# Données globales
dashboard_data = {
    'portfolio': {
        'total_value': 40000.00,
        'total_profit_loss': 0.00,
        'total_profit_percent': 0.0,
        'total_trades': 0,
        'leveraged_trades': 0,
        'total_margin_used': 0.0,
        'max_leverage_used': 1.0,
        'risk_level': 'MEDIUM',  # Plus de risque par défaut
        'last_update': datetime.now().isoformat(),
        'value_history': [],  # Historique de la valeur du portefeuille
        'pnl_history': []     # Historique du P&L
    },
    'trades_history': [],  # Historique complet des trades
    'active_positions': {},  # Positions ouvertes actuellement
    'cryptos': {}
}

# Initialisation des données par crypto
for pair, config in TRADING_PAIRS.items():
    dashboard_data['cryptos'][pair] = {
        'symbol': pair,
        'name': config['name'],
        'icon': config['icon'],
        'price': 0.0,
        'price_history': [],  # Pour analyser la tendance
        'price_change_24h': 0.0,
        'volatility': 0.0,  # Volatilité calculée
        'confidence_score': 50.0,  # Score de confiance du signal
        'recommended_leverage': 1.0,  # Levier recommandé
        'current_leverage': 1.0,  # Levier actuel utilisé
        'max_leverage': config['max_leverage'],
        'min_confidence': config['min_confidence'],
        
        # Portfolio
        'portfolio_value': 10000.00,
        'profit_loss': 0.00,
        'profit_percent': 0.0,
        'usdc_balance': 10000.00,
        'crypto_balance': 0.0,
        'margin_used': 0.0,  # Marge utilisée
        
        # Funding et frais
        'funding_rate': 0.0,  # Taux de funding actuel (%)
        'funding_history': [],  # Historique des funding rates
        'total_funding_paid': 0.0,  # Total des frais de funding payés
        'entry_time': None,  # Timestamp d'entrée position
        'funding_interval_hours': 8,  # Intervalle de funding (8h standard)
        
        # Trading stats
        'total_trades': 0,
        'leveraged_trades': 0,
        'win_rate': 0.0,
        'winning_trades': 0,
        'losing_trades': 0,
        'last_trade': None,
        'trade_id': 0,  # Compteur pour IDs uniques des trades
        'price_source': 'simulation',
        'status': 'active'
    }

class FundingRateManager:
    """Gestionnaire des taux de funding"""
    
    def __init__(self):
        self.exchanges = []
        self.setup_exchanges()
        # Taux de funding moyens historiques (en % par période de 8h)
        self.historical_funding_rates = {
            'ETH/USDC': 0.01,   # 0.01% toutes les 8h en moyenne
            'BTC/USDC': 0.005,  # 0.005% toutes les 8h en moyenne  
            'SOL/USDC': 0.02,   # 0.02% toutes les 8h en moyenne
            'XRP/USDC': 0.015   # 0.015% toutes les 8h en moyenne
        }
    
    def setup_exchanges(self):
        """Configure les exchanges pour récupérer les funding rates"""
        try:
            bitget = ccxt.bitget({'sandbox': False, 'enableRateLimit': True})
            self.exchanges.append(('Bitget', bitget))
        except Exception as e:
            print(f"⚠️  Bitget funding: {e}")
        
        try:
            binance = ccxt.binance({'sandbox': False, 'enableRateLimit': True})
            self.exchanges.append(('Binance', binance))
        except Exception as e:
            print(f"⚠️  Binance funding: {e}")
    
    def get_funding_rate(self, symbol):
        """Récupère le taux de funding actuel"""
        for name, exchange in self.exchanges:
            try:
                # Essayer différentes variantes du symbol
                symbols_to_try = [
                    symbol.replace('USDC', 'USDT'), 
                    symbol.replace('USDC', 'USD'),
                    symbol
                ]
                
                for test_symbol in symbols_to_try:
                    try:
                        if hasattr(exchange, 'fetch_funding_rate'):
                            funding_info = exchange.fetch_funding_rate(test_symbol)
                            funding_rate = funding_info['fundingRate']
                            if funding_rate is not None:
                                # Convertir en pourcentage pour période de 8h
                                return funding_rate * 100, f"{name} ({test_symbol})"
                    except Exception:
                        continue
            except Exception:
                continue
        
        # Si pas de données réelles, utiliser la moyenne historique
        historical_rate = self.historical_funding_rates.get(symbol, 0.01)
        return historical_rate, "Historical Average"
    
    def calculate_funding_cost(self, symbol, position_size_usd, leverage, hours_held):
        """Calcule le coût de funding pour une position"""
        funding_rate_per_8h, _ = self.get_funding_rate(symbol)
        
        # Nombre de périodes de funding (8h chacune)
        funding_periods = hours_held / 8
        
        # Coût total de funding
        # Funding = Position_Size * Funding_Rate * Nombre_Périodes
        total_funding_cost = position_size_usd * (funding_rate_per_8h / 100) * funding_periods
        
        return total_funding_cost
    
    def estimate_daily_funding(self, symbol, position_size_usd):
        """Estime le coût de funding quotidien"""
        return self.calculate_funding_cost(symbol, position_size_usd, 1, 24)


class IntelligentLeverageAnalyzer:
    """Analyseur intelligent pour déterminer le levier optimal"""
    
    def __init__(self):
        self.min_history_length = 10
    
    def calculate_volatility(self, prices):
        """Calcule la volatilité sur les derniers prix"""
        if len(prices) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(prices)):
            returns.append((prices[i] - prices[i-1]) / prices[i-1])
        
        if not returns:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        return math.sqrt(variance) * 100  # En pourcentage
    
    def analyze_trend(self, prices):
        """Analyse la tendance des prix"""
        if len(prices) < 5:
            return 'NEUTRAL', 50.0
        
        recent_prices = prices[-5:]
        trend_score = 0
        
        # Calcul de la tendance
        for i in range(1, len(recent_prices)):
            if recent_prices[i] > recent_prices[i-1]:
                trend_score += 1
            elif recent_prices[i] < recent_prices[i-1]:
                trend_score -= 1
        
        # Déterminer la direction et la force
        if trend_score >= 3:
            return 'STRONG_UP', 80.0
        elif trend_score == 2:
            return 'UP', 65.0
        elif trend_score == -2:
            return 'DOWN', 65.0
        elif trend_score <= -3:
            return 'STRONG_DOWN', 80.0
        else:
            return 'NEUTRAL', 50.0
    
    def calculate_confidence_score(self, pair, crypto_data):
        """Calcule le score de confiance pour un signal"""
        prices = crypto_data['price_history']
        if len(prices) < 5:
            return 40.0
        
        # Facteurs de confiance
        trend, trend_strength = self.analyze_trend(prices)
        volatility = crypto_data['volatility']
        price_change_24h = abs(crypto_data['price_change_24h'])
        
        # Score de base selon la tendance
        base_score = trend_strength
        
        # Ajustements
        # Volatilité modérée = bon
        if 2 <= volatility <= 5:
            base_score += 10
        elif volatility > 10:
            base_score -= 15  # Trop volatile = risqué
        
        # Mouvement 24h significatif = bon signal
        if 3 <= price_change_24h <= 8:
            base_score += 15
        elif price_change_24h > 15:
            base_score -= 10  # Trop de mouvement = risqué
        
        # Bonus pour certaines cryptos plus stables
        if pair in ['BTC/USDC', 'ETH/USDC']:
            base_score += 5
        
        return max(30.0, min(95.0, base_score))
    
    def recommend_leverage(self, pair, crypto_data):
        """Recommande le levier optimal"""
        confidence = crypto_data['confidence_score']
        max_leverage = crypto_data['max_leverage']
        min_confidence = crypto_data['min_confidence']
        volatility = crypto_data['volatility']
        
        # Pas de levier si confiance trop faible
        if confidence < min_confidence:
            return 1.0
        
        # Calcul du levier basé sur la confiance
        confidence_ratio = (confidence - min_confidence) / (95 - min_confidence)
        
        # Ajustement selon la volatilité
        volatility_factor = max(0.5, 1.0 - (volatility / 20))
        
        # Levier recommandé
        recommended = 1.0 + (max_leverage - 1.0) * confidence_ratio * volatility_factor
        
        # Limites de sécurité
        if volatility > 8:
            recommended = min(recommended, 3.0)  # Max 3x si très volatile
        
        # Limite globale à 10x maximum
        recommended = min(recommended, 10.0)
        
        return max(1.0, min(max_leverage, recommended))

class MultiCryptoPriceFeeder:
    """Récupère les prix réels pour toutes les cryptos"""
    
    def __init__(self):
        self.exchanges = []
        self.setup_exchanges()
    
    def setup_exchanges(self):
        """Configure les exchanges"""
        try:
            bitget = ccxt.bitget({'sandbox': False, 'enableRateLimit': True})
            self.exchanges.append(('Bitget', bitget))
            print("✅ Bitget connecté")
        except Exception as e:
            print(f"⚠️  Bitget: {e}")
        
        try:
            binance = ccxt.binance({'sandbox': False, 'enableRateLimit': True})
            self.exchanges.append(('Binance', binance))
            print("✅ Binance connecté")
        except Exception as e:
            print(f"⚠️  Binance: {e}")
    
    def get_crypto_price(self, symbol):
        """Récupère le prix d'une crypto"""
        for name, exchange in self.exchanges:
            try:
                symbols_to_try = [symbol, symbol.replace('USDC', 'USDT'), symbol.replace('USDC', 'USD')]
                
                for test_symbol in symbols_to_try:
                    try:
                        ticker = exchange.fetch_ticker(test_symbol)
                        price = ticker['last']
                        change_24h = ticker['percentage'] or 0
                        
                        if price and price > 0:
                            return price, change_24h, f"{name} ({test_symbol})"
                    except Exception:
                        continue
                        
            except Exception as e:
                continue
        
        return None, 0, "Error"

# Instances
price_feeder = MultiCryptoPriceFeeder()
leverage_analyzer = IntelligentLeverageAnalyzer()
funding_manager = FundingRateManager()

@app.route('/')
def index():
    return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>⚡ Bot Multi-Cryptos avec Levier Intelligent - Dashboard Avancé</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1800px; margin: 0 auto; }
        .header { background: rgba(255,255,255,0.95); color: #333; padding: 25px; border-radius: 15px; 
                 margin-bottom: 25px; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
        
        .navigation {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 20px 0;
        }
        
        .nav-btn {
            padding: 12px 24px;
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 500;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .nav-btn:hover {
            background: linear-gradient(135deg, #0056b3, #004085);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,123,255,0.4);
        }
        
        .nav-btn.active {
            background: linear-gradient(135deg, #28a745, #20c997);
        }
        .risk-indicator { display: inline-block; padding: 8px 16px; border-radius: 20px; color: white; font-weight: bold; margin: 10px; }
        .risk-low { background: #4CAF50; }
        .risk-medium { background: #FF9800; }
        .risk-high { background: #f44336; }
        
        .main-grid { display: block; margin-bottom: 20px; }
        .portfolio-section { background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; box-shadow: 0 6px 25px rgba(0,0,0,0.1); }
        
        .portfolio-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); 
                           gap: 15px; margin-bottom: 20px; }
        .summary-card { background: #f8f9fa; padding: 15px; border-radius: 10px; text-align: center; }
        .summary-value { font-size: 1.5em; font-weight: bold; margin-bottom: 5px; }
        .summary-label { color: #666; font-size: 0.85em; }
        
        .chart-container { height: 300px; margin: 20px 0; }
        
        .trades-section { background: rgba(255,255,255,0.95); padding: 25px; border-radius: 15px; box-shadow: 0 6px 25px rgba(0,0,0,0.1); }
        .trades-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
        .trades-filter { display: flex; gap: 10px; }
        .filter-btn { padding: 8px 16px; border: none; border-radius: 20px; cursor: pointer; font-size: 0.9em; transition: all 0.3s; }
        .filter-btn.active { background: #667eea; color: white; }
        .filter-btn:not(.active) { background: #e9ecef; color: #666; }
        
        .trades-list { max-height: 400px; overflow-y: auto; }
        .trade-item { display: grid; grid-template-columns: 80px 120px 100px 90px 90px 100px 80px 120px; 
                     gap: 10px; padding: 12px; margin-bottom: 8px; background: #f8f9fa; border-radius: 10px; 
                     align-items: center; font-size: 0.9em; }
        .trade-item.leverage { border-left: 4px solid #FF9800; }
        .trade-item.spot { border-left: 4px solid #2196F3; }
        .trade-item.closed { opacity: 0.8; }
        .trade-id { font-weight: bold; font-size: 0.8em; color: #666; }
        .trade-pair { font-weight: bold; color: #333; }
        .trade-type { padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
        .type-leverage { background: #fff3e0; color: #ff9800; }
        .type-spot { background: #e3f2fd; color: #2196f3; }
        .trade-status { padding: 3px 8px; border-radius: 10px; font-size: 0.8em; font-weight: bold; }
        .status-open { background: #e8f5e8; color: #4caf50; }
        .status-closed { background: #ffebee; color: #f44336; }
        .pnl-positive { color: #4CAF50; font-weight: bold; }
        .pnl-negative { color: #f44336; font-weight: bold; }
        .pnl-neutral { color: #666; }
        
        .cryptos-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 20px; margin-top: 20px; }
        .crypto-card { background: rgba(255,255,255,0.95); padding: 20px; border-radius: 15px; 
                      box-shadow: 0 6px 25px rgba(0,0,0,0.1); transition: transform 0.3s; }
        .crypto-card:hover { transform: translateY(-3px); }
        
        .crypto-header { display: flex; justify-content: space-between; margin-bottom: 15px; }
        .crypto-name { display: flex; align-items: center; gap: 10px; }
        .crypto-icon { font-size: 1.5em; }
        .crypto-title { font-size: 1.1em; font-weight: bold; color: #333; }
        .price { font-size: 1.8em; font-weight: bold; color: #2196F3; }
        .price-change { font-size: 0.85em; margin-left: 10px; padding: 4px 8px; border-radius: 12px; }
        .positive { background: #e8f5e8; color: #4CAF50; }
        .negative { background: #ffebee; color: #f44336; }
        
        .leverage-section { margin: 15px 0; padding: 15px; background: #f8f9fa; border-radius: 10px; }
        .leverage-indicator { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .leverage-value { font-size: 1.2em; font-weight: bold; color: #FF9800; }
        .confidence-bar { width: 100%; height: 6px; background: #e0e0e0; border-radius: 3px; overflow: hidden; }
        .confidence-fill { height: 100%; transition: width 0.3s; }
        .confidence-high { background: #4CAF50; }
        .confidence-medium { background: #FF9800; }
        .confidence-low { background: #f44336; }
        
        .stats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top: 10px; }
        .stat { text-align: center; padding: 8px; background: #f8f9fa; border-radius: 6px; }
        .stat-value { font-size: 1.1em; font-weight: bold; color: #333; }
        .stat-label { color: #666; font-size: 0.75em; margin-top: 2px; }
        
        .trade-details-btn {
            width: 100%;
            padding: 8px;
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            transition: all 0.3s ease;
            margin-top: 10px;
        }
        
        .trade-details-btn:hover {
            background: linear-gradient(135deg, #0056b3, #004085);
            transform: translateY(-1px);
        }
        
        /* Modal pour les détails des trades */
        .trade-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            animation: fadeIn 0.3s ease;
        }
        
        .trade-modal-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border-radius: 12px;
            padding: 25px;
            min-width: 600px;
            max-width: 90vw;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        .trade-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #eee;
        }
        
        .trade-modal-title {
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
        }
        
        .close-modal {
            background: #f44336;
            color: white;
            border: none;
            border-radius: 50%;
            width: 35px;
            height: 35px;
            cursor: pointer;
            font-size: 1.2em;
            font-weight: bold;
            transition: all 0.3s ease;
        }
        
        .close-modal:hover {
            background: #d32f2f;
            transform: scale(1.1);
        }
        
        .active-trade-card {
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border: 2px solid #007bff;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            position: relative;
            overflow: hidden;
        }
        
        .active-trade-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: linear-gradient(180deg, #4CAF50, #007bff, #FF9800);
            animation: pulse 2s infinite;
        }
        
        .trade-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .trade-id-badge {
            background: #007bff;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }
        
        .trade-status-badge {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }
        
        .trade-status-badge.open {
            background: #4CAF50;
            color: white;
        }
        
        .trade-status-badge.closed {
            background: #666;
            color: white;
        }
        
        .trade-details-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }
        
        .trade-detail-item {
            background: white;
            padding: 12px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .trade-detail-label {
            font-size: 0.8em;
            color: #666;
            margin-bottom: 5px;
            font-weight: 500;
        }
        
        .trade-detail-value {
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
        }
        
        .trade-detail-value.positive {
            color: #4CAF50;
        }
        
        .trade-detail-value.negative {
            color: #f44336;
        }
        
        .trade-detail-value.leverage {
            color: #FF9800;
        }
        
        .no-active-trades {
            text-align: center;
            padding: 40px;
            color: #666;
            font-size: 1.1em;
        }
        
        .no-active-trades-icon {
            font-size: 3em;
            margin-bottom: 15px;
            opacity: 0.5;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .refresh-btn { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; 
                      border: none; padding: 15px 30px; border-radius: 25px; font-size: 1.1em; 
                      cursor: pointer; margin: 20px auto; display: block; transition: all 0.3s; }
        .refresh-btn:hover { transform: scale(1.05); box-shadow: 0 5px 20px rgba(0,0,0,0.2); }
        
        .status { text-align: center; color: white; margin-top: 20px; background: rgba(255,255,255,0.1); 
                 padding: 15px; border-radius: 10px; }
        
        /* Responsive */
        @media (max-width: 1200px) {
            .main-grid { grid-template-columns: 1fr; }
            .trade-item { grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; font-size: 0.8em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ Bot Multi-Cryptos avec Levier Intelligent - Dashboard Pro</h1>
            <p>🎯 Trading Agressif • 📊 Analyse IA • 🛡️ Gestion Avancée des Risques</p>
            <span id="risk-level" class="risk-indicator risk-medium">Risque: MOYEN</span>
        </div>
        
        <div class="navigation">
            <a href="/" class="nav-btn active">📊 Dashboard</a>
            <a href="/trades" class="nav-btn">💱 Trades</a>
            <a href="#" class="nav-btn" onclick="updateAllData()">🔄 Actualiser</a>
        </div>
        
        <div class="main-grid">
            <!-- Section Portefeuille avec graphiques -->
            <div class="portfolio-section">
                <h3>📊 Évolution du Portefeuille</h3>
                
                <div class="portfolio-summary">
                    <div class="summary-card">
                        <div id="total-value" class="summary-value">$40,000</div>
                        <div class="summary-label">💰 Valeur</div>
                    </div>
                    <div class="summary-card">
                        <div id="total-pnl" class="summary-value">+$0</div>
                        <div class="summary-label">📈 P&L</div>
                    </div>
                    <div class="summary-card">
                        <div id="total-trades" class="summary-value">0</div>
                        <div class="summary-label">💱 Trades</div>
                    </div>
                    <div class="summary-card">
                        <div id="leveraged-trades" class="summary-value">0</div>
                        <div class="summary-label">⚡ Levier</div>
                    </div>
                    <div class="summary-card">
                        <div id="max-leverage" class="summary-value">1.0x</div>
                        <div class="summary-label">🚀 Max Lev</div>
                    </div>
                    <div class="summary-card">
                        <div id="margin-used" class="summary-value">$0</div>
                        <div class="summary-label">💸 Marge</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <canvas id="portfolioChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Cryptos Grid -->
        <div class="cryptos-grid" id="cryptos-grid">
            <div style="text-align: center; padding: 40px; color: red; background: yellow; border-radius: 15px; font-size: 20px; font-weight: bold;">
                🔄 SECTION CRYPTOS VISIBLE - JAVASCRIPT PAS ENCORE CHARGÉ
            </div>
        </div>
        
        <div class="status">
            <div>🕒 Dernière analyse: <span id="last-update">-</span></div>
            <div>🤖 Bot en mode agressif - Levier intelligent jusqu'à 10x</div>
        </div>
    </div>
    
    <!-- Modal pour les détails des trades -->
    <div id="tradeModal" class="trade-modal">
        <div class="trade-modal-content">
            <div class="trade-modal-header">
                <div class="trade-modal-title" id="modalTitle">📊 Trades Actifs - ETH</div>
                <button class="close-modal" onclick="closeTradeModal()">&times;</button>
            </div>
            <div id="modalContent">
                <!-- Le contenu sera généré dynamiquement -->
            </div>
        </div>
    </div>

    <script>
        let portfolioChart;
        // Fonctions pour le modal des trades
        let currentDashboardData = null;
        
        function initPortfolioChart() {
            const ctx = document.getElementById('portfolioChart').getContext('2d');
            portfolioChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Valeur Portefeuille ($)',
                        data: [],
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4,
                        fill: true
                    }, {
                        label: 'P&L ($)',
                        data: [],
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        tension: 0.4,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: { display: true, text: 'Valeur ($)' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: { display: true, text: 'P&L ($)' },
                            grid: { drawOnChartArea: false }
                        }
                    },
                    plugins: {
                        legend: { position: 'top' }
                    }
                }
            });
        }
        
        function updatePortfolioChart(valueHistory, pnlHistory) {
            if (!portfolioChart) return;
            
            const labels = valueHistory.map(item => 
                new Date(item.timestamp).toLocaleTimeString('fr-FR', {hour: '2-digit', minute: '2-digit'})
            );
            const values = valueHistory.map(item => item.value);
            const pnls = pnlHistory.map(item => item.pnl);
            
            portfolioChart.data.labels = labels;
            portfolioChart.data.datasets[0].data = values;
            portfolioChart.data.datasets[1].data = pnls;
            portfolioChart.update('none');
        }
        
        function updateAllData() {
            console.log('🔄 Début updateAllData');
            fetch('/api/intelligent-crypto')
                .then(response => {
                    console.log('📡 Réponse API reçue:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('📊 Données reçues:', data);
                    currentDashboardData = data; // Sauvegarder les données pour le modal
                    
                    console.log('💰 Mise à jour portefeuille...');
                    updatePortfolioSummary(data.portfolio, data.cryptos);
                    
                    console.log('📈 Mise à jour graphique...');
                    updatePortfolioChart(data.portfolio.value_history, data.portfolio.pnl_history);
                    
                    console.log('🪙 Mise à jour cryptos...', Object.keys(data.cryptos));
                    updateCryptosGrid(data.cryptos);
                    
                    document.getElementById('last-update').textContent = 
                        new Date(data.portfolio.last_update).toLocaleString();
                    console.log('✅ updateAllData terminé');
                })
                .catch(error => {
                    console.error('❌ Erreur:', error);
                });
        }
        
        function updatePortfolioSummary(portfolio, cryptos) {
            document.getElementById('total-value').textContent = 
                '$' + portfolio.total_value.toLocaleString(undefined, {maximumFractionDigits: 0});
            
            const pnlElement = document.getElementById('total-pnl');
            const pnlValue = portfolio.total_profit_loss;
            pnlElement.textContent = (pnlValue >= 0 ? '+$' : '-$') + 
                Math.abs(pnlValue).toLocaleString(undefined, {maximumFractionDigits: 0});
            pnlElement.style.color = pnlValue >= 0 ? '#4CAF50' : '#f44336';
            
            document.getElementById('total-trades').textContent = portfolio.total_trades;
            document.getElementById('leveraged-trades').textContent = portfolio.leveraged_trades;
            document.getElementById('max-leverage').textContent = portfolio.max_leverage_used.toFixed(1) + 'x';
            document.getElementById('margin-used').textContent = 
                '$' + portfolio.total_margin_used.toLocaleString(undefined, {maximumFractionDigits: 0});
            
            // Risk level
            const riskElement = document.getElementById('risk-level');
            riskElement.textContent = 'Risque: ' + portfolio.risk_level;
            riskElement.className = 'risk-indicator risk-' + portfolio.risk_level.toLowerCase();
        }
        
        function updateCryptosGrid(cryptos) {
            const grid = document.getElementById('cryptos-grid');
            console.log('Updating cryptos grid:', cryptos);
            grid.innerHTML = '';
            
            if (!cryptos || Object.keys(cryptos).length === 0) {
                console.log('No cryptos data available');
                grid.innerHTML = '<div style="text-align: center; padding: 40px; color: #666;">Chargement des cryptos...</div>';
                return;
            }
            
            Object.values(cryptos).forEach(crypto => {
                console.log('Creating card for:', crypto.name);
                const card = createCryptoCard(crypto);
                grid.appendChild(card);
            });
        }
        
        function createCryptoCard(crypto) {
            const card = document.createElement('div');
            card.className = 'crypto-card';
            
            const changeClass = crypto.price_change_24h >= 0 ? 'positive' : 'negative';
            const pnlColor = crypto.profit_loss >= 0 ? '#4CAF50' : '#f44336';
            
            let confidenceClass = 'confidence-low';
            if (crypto.confidence_score >= 75) confidenceClass = 'confidence-high';
            else if (crypto.confidence_score >= 60) confidenceClass = 'confidence-medium';
            
            const leverageColor = crypto.current_leverage > 1 ? '#FF9800' : '#666';
            
            card.innerHTML = `
                <div class="crypto-header">
                    <div class="crypto-name">
                        <span class="crypto-icon">${crypto.icon}</span>
                        <div>
                            <div class="crypto-title">${crypto.name}</div>
                            <div style="font-size: 0.9em; color: #666;">${crypto.symbol}</div>
                        </div>
                    </div>
                    <div style="text-align: right;">
                        <div class="price">$${crypto.price.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                        <span class="price-change ${changeClass}">
                            ${crypto.price_change_24h >= 0 ? '+' : ''}${crypto.price_change_24h.toFixed(2)}%
                        </span>
                    </div>
                </div>
                
                <div class="leverage-section">
                    <div class="leverage-indicator">
                        <span>🎯 Confiance:</span>
                        <span style="font-weight: bold; color: ${confidenceClass === 'confidence-high' ? '#4CAF50' : confidenceClass === 'confidence-medium' ? '#FF9800' : '#f44336'}">
                            ${crypto.confidence_score.toFixed(1)}%
                        </span>
                    </div>
                    <div class="confidence-bar">
                        <div class="confidence-fill ${confidenceClass}" style="width: ${crypto.confidence_score}%"></div>
                    </div>
                    
                    <div class="leverage-indicator" style="margin-top: 8px;">
                        <span>⚡ Levier Rec:</span>
                        <span class="leverage-value">${crypto.recommended_leverage.toFixed(1)}x</span>
                    </div>
                    <div class="leverage-indicator">
                        <span>🚀 Utilisé:</span>
                        <span style="font-weight: bold; color: ${leverageColor}">${crypto.current_leverage.toFixed(1)}x</span>
                    </div>
                    
                    <div style="margin-top: 6px; font-size: 0.85em; color: #666;">
                        📊 Vol: ${crypto.volatility.toFixed(1)}% • 💰 Fund: ${crypto.funding_rate >= 0 ? '+' : ''}${crypto.funding_rate.toFixed(3)}%/8h
                    </div>
                </div>
                
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value">$${crypto.portfolio_value.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
                        <div class="stat-label">💰 Valeur</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" style="color: ${pnlColor}">
                            ${crypto.profit_loss >= 0 ? '+' : ''}$${crypto.profit_loss.toLocaleString(undefined, {maximumFractionDigits: 0})}
                        </div>
                        <div class="stat-label">📈 P&L</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value">${crypto.total_trades}</div>
                        <div class="stat-label">💱 Trades</div>
                    </div>
                </div>
                
                <div style="margin-top: 12px;">
                    <button onclick="showTradeDetails('${crypto.symbol}')" 
                            class="trade-details-btn">
                        📊 Voir Trades Actifs
                    </button>
                </div>
            `;
            
            return card;
        }
        
        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🚀 DOM chargé - Initialisation...');
            
            // Test basique pour voir si le script fonctionne
            const gridTest = document.getElementById('cryptos-grid');
            console.log('🔍 Cryptos-grid trouvé:', gridTest);
            if (gridTest) {
                gridTest.innerHTML = '<div style="background: yellow; padding: 20px; color: black; text-align: center;">⚡ SCRIPT JAVASCRIPT FONCTIONNE ⚡</div>';
            }
            
            initPortfolioChart();
            updateAllData();
            setInterval(updateAllData, 20000); // 20 secondes
        });
        
        // Fonctions pour le modal des trades
        
        function showTradeDetails(cryptoSymbol) {
            const modal = document.getElementById('tradeModal');
            const modalTitle = document.getElementById('modalTitle');
            const modalContent = document.getElementById('modalContent');
            
            // Mettre à jour le titre
            const cryptoName = getCryptoName(cryptoSymbol);
            modalTitle.textContent = `📊 Trades Actifs - ${cryptoName} (${cryptoSymbol})`;
            
            // Récupérer les données actuelles
            if (!currentDashboardData) {
                modalContent.innerHTML = `
                    <div class="no-active-trades">
                        <div class="no-active-trades-icon">⏳</div>
                        <div>Chargement des données...</div>
                    </div>
                `;
                modal.style.display = 'block';
                return;
            }
            
            // Filtrer les trades pour cette crypto
            const cryptoTrades = currentDashboardData.trades_history.filter(trade => 
                trade.pair.includes(cryptoSymbol) && trade.status === 'OUVERT'
            );
            
            // Générer le contenu
            if (cryptoTrades.length === 0) {
                modalContent.innerHTML = `
                    <div class="no-active-trades">
                        <div class="no-active-trades-icon">💤</div>
                        <div>Aucun trade actif pour ${cryptoName}</div>
                        <div style="font-size: 0.9em; color: #999; margin-top: 10px;">
                            Le bot analyse en continu les signaux pour cette crypto
                        </div>
                    </div>
                `;
            } else {
                modalContent.innerHTML = cryptoTrades.map(trade => createTradeDetailCard(trade)).join('');
            }
            
            // Afficher le modal
            modal.style.display = 'block';
            document.body.style.overflow = 'hidden'; // Empêcher le scroll en arrière-plan
        }
        
        function closeTradeModal() {
            const modal = document.getElementById('tradeModal');
            modal.style.display = 'none';
            document.body.style.overflow = 'auto'; // Réactiver le scroll
        }
        
        function createTradeDetailCard(trade) {
            const leverageDisplay = trade.leverage > 1 ? trade.leverage.toFixed(1) + 'x' : 'Spot';
            const pnlClass = trade.pnl > 0 ? 'positive' : trade.pnl < 0 ? 'negative' : '';
            const leverageClass = trade.leverage > 1 ? 'leverage' : '';
            
            // Calculer le temps depuis ouverture
            const openTime = new Date(trade.timestamp);
            const now = new Date();
            const duration = Math.floor((now - openTime) / 1000 / 60); // en minutes
            const durationText = duration > 60 ? 
                Math.floor(duration / 60) + 'h ' + (duration % 60) + 'min' : 
                duration + ' minutes';
            
            // Calculer le coût de funding estimé
            const fundingCost = trade.leverage > 1 ? 
                (trade.effective_size * 0.0001 * Math.floor(duration / 480)).toFixed(2) : 0;
            
            return `
                <div class="active-trade-card">
                    <div class="trade-card-header">
                        <div class="trade-id-badge">ID: ${trade.id}</div>
                        <div class="trade-status-badge ${trade.status.toLowerCase()}">
                            ${trade.status}
                        </div>
                    </div>
                    
                    <div class="trade-details-grid">
                        <div class="trade-detail-item">
                            <div class="trade-detail-label">💱 Paire de Trading</div>
                            <div class="trade-detail-value">${trade.pair}</div>
                        </div>
                        
                        <div class="trade-detail-item">
                            <div class="trade-detail-label">📊 Type de Trade</div>
                            <div class="trade-detail-value ${leverageClass}">
                                ${trade.type.includes('LEVIER') ? '⚡ AVEC LEVIER' : '🔵 SPOT'}
                            </div>
                        </div>
                        
                        <div class="trade-detail-item">
                            <div class="trade-detail-label">🚀 Levier Appliqué</div>
                            <div class="trade-detail-value ${leverageClass}">
                                ${leverageDisplay}
                            </div>
                        </div>
                        
                        <div class="trade-detail-item">
                            <div class="trade-detail-label">💰 Prix d'Entrée</div>
                            <div class="trade-detail-value">
                                $${trade.price.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                            </div>
                        </div>
                        
                        <div class="trade-detail-item">
                            <div class="trade-detail-label">💵 Montant Investi</div>
                            <div class="trade-detail-value">
                                $${trade.effective_size.toLocaleString(undefined, {maximumFractionDigits: 0})}
                            </div>
                        </div>
                        
                        <div class="trade-detail-item">
                            <div class="trade-detail-label">📈 P&L Actuel</div>
                            <div class="trade-detail-value ${pnlClass}">
                                ${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}
                                ${trade.return_pct ? ' (' + trade.return_pct.toFixed(1) + '%)' : ''}
                            </div>
                        </div>
                        
                        <div class="trade-detail-item">
                            <div class="trade-detail-label">⏱️ Durée</div>
                            <div class="trade-detail-value">${durationText}</div>
                        </div>
                        
                        <div class="trade-detail-item">
                            <div class="trade-detail-label">💸 Coût Funding Est.</div>
                            <div class="trade-detail-value ${trade.leverage > 1 ? 'negative' : ''}">
                                ${trade.leverage > 1 ? '-$' + fundingCost : '$0.00'}
                            </div>
                        </div>
                        
                        <div class="trade-detail-item">
                            <div class="trade-detail-label">🕒 Ouvert à</div>
                            <div class="trade-detail-value">
                                ${openTime.toLocaleTimeString()} - ${openTime.toLocaleDateString()}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        function getCryptoName(symbol) {
            const cryptoMap = {
                'ETH': 'Ethereum',
                'BTC': 'Bitcoin', 
                'SOL': 'Solana',
                'XRP': 'Ripple'
            };
            return cryptoMap[symbol] || symbol;
        }
        
        // Fermer le modal si on clique en dehors
        window.onclick = function(event) {
            const modal = document.getElementById('tradeModal');
            if (event.target === modal) {
                closeTradeModal();
            }
        }
    </script>
</body>
</html>
    ''')

@app.route('/api/intelligent-crypto')
def api_intelligent_crypto():
    """API pour bot avec levier intelligent"""
    print(f"🔍 API appelée - Cryptos disponibles: {list(dashboard_data['cryptos'].keys())}")
    for pair, crypto in dashboard_data['cryptos'].items():
        print(f"  {pair}: {crypto['name']} - Prix: ${crypto['price']:.2f}")
    return jsonify(dashboard_data)

@app.route('/trades')
def trades_page():
    """Page dédiée aux trades"""
    return f'''
<!DOCTYPE html>
<html>
<head>
    <title>⚡ Bot Trading - Vue Trades</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
        .container {{ max-width: 1800px; margin: 0 auto; }}
        .header {{ background: rgba(255,255,255,0.95); color: #333; padding: 25px; border-radius: 15px; 
                 margin-bottom: 25px; text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }}
        
        .navigation {{
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 20px 0;
        }}
        
        .nav-btn {{
            padding: 12px 24px;
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 500;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }}
        
        .nav-btn:hover {{
            background: linear-gradient(135deg, #0056b3, #004085);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,123,255,0.4);
        }}
        
        .nav-btn.active {{
            background: linear-gradient(135deg, #28a745, #20c997);
        }}
        
        .trades-section {{ 
            background: rgba(255,255,255,0.95); 
            padding: 25px; 
            border-radius: 15px; 
            box-shadow: 0 6px 25px rgba(0,0,0,0.1); 
            margin-bottom: 20px;
        }}
        
        .trades-header {{ 
            display: flex; 
            justify-content: space-between; 
            align-items: center; 
            margin-bottom: 20px; 
        }}
        
        .trades-filter {{ 
            display: flex; 
            gap: 10px; 
        }}
        
        .filter-btn {{ 
            padding: 8px 16px; 
            border: none; 
            border-radius: 20px; 
            cursor: pointer; 
            font-size: 0.9em; 
            transition: all 0.3s; 
        }}
        
        .filter-btn.active {{ 
            background: #667eea; 
            color: white; 
        }}
        
        .filter-btn:not(.active) {{ 
            background: #e9ecef; 
            color: #666; 
        }}
        
        .trades-list {{ 
            max-height: 600px; 
            overflow-y: auto; 
        }}
        
        .trade-item {{ 
            display: grid; 
            grid-template-columns: 80px 120px 100px 120px 120px 100px 80px 150px; 
            gap: 15px; 
            padding: 15px; 
            margin-bottom: 12px; 
            background: #f8f9fa; 
            border-radius: 12px; 
            align-items: center; 
            font-size: 0.95em; 
            transition: all 0.3s ease;
        }}
        
        .trade-item:hover {{
            background: #e9ecef;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .trade-item.leverage {{ 
            border-left: 4px solid #FF9800; 
            background: linear-gradient(90deg, #fff3e0, #f8f9fa);
        }}
        
        .trade-item.spot {{ 
            border-left: 4px solid #2196F3; 
            background: linear-gradient(90deg, #e3f2fd, #f8f9fa);
        }}
        
        .trade-item.closed {{ 
            opacity: 0.7; 
        }}
        
        .trade-id {{ 
            font-weight: bold; 
            font-size: 0.85em; 
            color: #666; 
            font-family: monospace;
        }}
        
        .trade-pair {{ 
            font-weight: bold; 
            color: #333; 
            font-size: 1.1em;
        }}
        
        .trade-type {{ 
            padding: 6px 12px; 
            border-radius: 15px; 
            font-size: 0.8em; 
            font-weight: bold; 
        }}
        
        .type-leverage {{ 
            background: #fff3e0; 
            color: #ff9800; 
        }}
        
        .type-spot {{ 
            background: #e3f2fd; 
            color: #2196f3; 
        }}
        
        .trade-status {{ 
            padding: 6px 12px; 
            border-radius: 12px; 
            font-size: 0.8em; 
            font-weight: bold; 
        }}
        
        .status-open {{ 
            background: #e8f5e8; 
            color: #4caf50; 
        }}
        
        .status-closed {{ 
            background: #ffebee; 
            color: #f44336; 
        }}
        
        .pnl-positive {{ 
            color: #4CAF50; 
            font-weight: bold; 
        }}
        
        .pnl-negative {{ 
            color: #f44336; 
            font-weight: bold; 
        }}
        
        .pnl-neutral {{ 
            color: #666; 
        }}
        
        .trade-details {{
            font-size: 0.9em;
            color: #666;
            line-height: 1.4;
        }}
        
        .leverage-badge {{
            background: #FF9800;
            color: white;
            padding: 4px 8px;
            border-radius: 8px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        
        .no-trades {{
            text-align: center;
            padding: 60px 20px;
            color: #666;
            font-size: 1.2em;
        }}
        
        .no-trades-icon {{
            font-size: 4em;
            margin-bottom: 20px;
            opacity: 0.5;
        }}
        
        .refresh-btn {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            color: white; 
            border: none; 
            padding: 15px 30px; 
            border-radius: 25px; 
            font-size: 1.1em; 
            cursor: pointer; 
            margin: 20px auto; 
            display: block; 
            transition: all 0.3s; 
        }}
        
        .refresh-btn:hover {{ 
            transform: scale(1.05); 
            box-shadow: 0 5px 20px rgba(0,0,0,0.2); 
        }}
        
        .status {{ 
            text-align: center; 
            color: white; 
            margin-top: 20px; 
            background: rgba(255,255,255,0.1); 
            padding: 15px; 
            border-radius: 10px; 
        }}
        
        /* Responsive */
        @media (max-width: 1200px) {{
            .trade-item {{ 
                grid-template-columns: 1fr 1fr 1fr 1fr; 
                gap: 8px; 
                font-size: 0.8em; 
            }}
        }}
        
        @media (max-width: 768px) {{
            .navigation {{
                flex-wrap: wrap;
                gap: 10px;
            }}
            .nav-btn {{
                font-size: 0.9em;
                padding: 10px 18px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ Bot Multi-Cryptos - Vue Trades</h1>
            <p>💱 Historique complet de tous les trades • 📊 Suivi en temps réel</p>
        </div>
        
        <div class="navigation">
            <a href="/" class="nav-btn">📊 Dashboard</a>
            <a href="/trades" class="nav-btn active">💱 Trades</a>
            <a href="#" class="nav-btn" onclick="updateTradesData()">🔄 Actualiser</a>
        </div>
        
        <div class="trades-section">
            <div class="trades-header">
                <h3>📋 Historique des Trades</h3>
                <div class="trades-filter">
                    <button class="filter-btn active" onclick="filterTrades('all')">Tous</button>
                    <button class="filter-btn" onclick="filterTrades('open')">Ouverts</button>
                    <button class="filter-btn" onclick="filterTrades('closed')">Fermés</button>
                    <button class="filter-btn" onclick="filterTrades('leverage')">Levier</button>
                    <button class="filter-btn" onclick="filterTrades('spot')">Spot</button>
                </div>
            </div>
            
            <div class="trades-list" id="trades-list">
                <div class="trade-item" style="font-weight: bold; background: #e9ecef;">
                    <div>ID</div>
                    <div>Paire</div>
                    <div>Type</div>
                    <div>Prix / Montant</div>
                    <div>Détails Trade</div>
                    <div>Levier</div>
                    <div>Statut</div>
                    <div>P&L & Performance</div>
                </div>
            </div>
        </div>
        
        <div class="status">
            <div>🕒 Dernière analyse: <span id="last-update">-</span></div>
            <div>🤖 Bot en mode agressif - Levier intelligent jusqu'à 10x</div>
        </div>
    </div>
    
    <script>
        let currentFilter = 'all';
        
        function updateTradesData() {{
            fetch('/api/intelligent-crypto')
                .then(response => response.json())
                .then(data => {{
                    updateTradesDisplay(data);
                    document.getElementById('last-update').textContent = 
                        new Date(data.portfolio.last_update).toLocaleString();
                }})
                .catch(error => {{
                    console.error('Erreur:', error);
                }});
        }}
        
        function updateTradesDisplay(data) {{
            const tradesList = document.getElementById('trades-list');
            
            // Combiner tous les trades (historique + positions actives)
            const allTrades = [...data.trades_history];
            
            // Ajouter les positions actives
            Object.values(data.active_positions).forEach(trade => {{
                if (!allTrades.find(t => t.id === trade.id)) {{
                    allTrades.push(trade);
                }}
            }});
            
            // Trier par timestamp (plus récent en premier)
            allTrades.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
            // Vider la liste (sauf header)
            while (tradesList.children.length > 1) {{
                tradesList.removeChild(tradesList.lastChild);
            }}
            
            if (allTrades.length === 0) {{
                const noTradesDiv = document.createElement('div');
                noTradesDiv.className = 'no-trades';
                noTradesDiv.innerHTML = `
                    <div class="no-trades-icon">💤</div>
                    <div>Aucun trade pour le moment</div>
                    <div style="font-size: 0.9em; margin-top: 10px;">Le bot analyse en continu les signaux de trading</div>
                `;
                tradesList.appendChild(noTradesDiv);
                return;
            }}
            
            // Ajouter les trades
            allTrades.forEach(trade => {{
                const tradeItem = document.createElement('div');
                tradeItem.className = 'trade-item ' + 
                    (trade.type && trade.type.includes('LEVIER') ? 'leverage' : 'spot') + 
                    (trade.status === 'FERMÉ' ? ' closed' : '');
                tradeItem.dataset.type = trade.type || 'SPOT';
                tradeItem.dataset.status = trade.status || 'OUVERT';
                
                const pnlClass = (trade.pnl || 0) > 0 ? 'pnl-positive' : 
                                (trade.pnl || 0) < 0 ? 'pnl-negative' : 'pnl-neutral';
                const leverageDisplay = (trade.leverage || 1) > 1 ? 
                    `<span class="leverage-badge">${{(trade.leverage || 1).toFixed(1)}}x</span>` : 
                    '<span style="color: #666;">Spot</span>';
                
                const openDate = new Date(trade.timestamp);
                const duration = trade.status === 'FERMÉ' && trade.close_timestamp ? 
                    Math.floor((new Date(trade.close_timestamp) - openDate) / 1000 / 60) : 
                    Math.floor((new Date() - openDate) / 1000 / 60);
                
                const durationText = duration > 60 ? 
                    Math.floor(duration / 60) + 'h ' + (duration % 60) + 'min' : 
                    duration + ' min';
                
                tradeItem.innerHTML = `
                    <div class="trade-id">${{trade.id || 'N/A'}}</div>
                    <div class="trade-pair">${{(trade.pair || 'N/A').split('/')[0]}}</div>
                    <div class="trade-type ${{trade.type && trade.type.includes('LEVIER') ? 'type-leverage' : 'type-spot'}}">
                        ${{trade.type && trade.type.includes('LEVIER') ? '⚡ LEV' : '🔵 SPOT'}}
                    </div>
                    <div class="trade-details">
                        ${{trade.price ? '$' + trade.price.toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}}) : 'N/A'}}<br>
                        <small>${{trade.effective_size ? '$' + trade.effective_size.toLocaleString(undefined, {{maximumFractionDigits: 0}}) : 'N/A'}}</small>
                    </div>
                    <div class="trade-details">
                        Durée: ${{durationText}}<br>
                        <small>Ouvert: ${{openDate.toLocaleTimeString()}}</small>
                    </div>
                    <div>${{leverageDisplay}}</div>
                    <div class="trade-status ${{(trade.status || 'OUVERT') === 'OUVERT' ? 'status-open' : 'status-closed'}}">
                        ${{trade.status || 'OUVERT'}}
                    </div>
                    <div class="trade-details">
                        <span class="${{pnlClass}}">
                            ${{(trade.pnl || 0) >= 0 ? '+' : ''}}${{(trade.pnl || 0).toFixed(2)}}
                        </span><br>
                        <small>${{trade.return_pct ? '(' + trade.return_pct.toFixed(1) + '%)' : ''}}</small>
                        ${{trade.funding_cost ? '<br><small>Fund: -$' + trade.funding_cost.toFixed(2) + '</small>' : ''}}
                    </div>
                `;
                
                tradesList.appendChild(tradeItem);
            }});
            
            // Réappliquer le filtre
            filterTrades(currentFilter);
        }}
        
        function filterTrades(filter) {{
            currentFilter = filter;
            
            // Mise à jour des boutons de filtre
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            
            // Trouver et activer le bon bouton
            const buttons = document.querySelectorAll('.filter-btn');
            const filterMap = {{
                'all': 'Tous',
                'open': 'Ouverts', 
                'closed': 'Fermés',
                'leverage': 'Levier',
                'spot': 'Spot'
            }};
            
            buttons.forEach(btn => {{
                if (btn.textContent === filterMap[filter]) {{
                    btn.classList.add('active');
                }}
            }});
            
            // Filtrer les trades
            const items = document.querySelectorAll('.trade-item:not(:first-child)');
            items.forEach(item => {{
                let show = true;
                
                if (filter === 'open') {{
                    show = item.dataset.status === 'OUVERT';
                }} else if (filter === 'closed') {{
                    show = item.dataset.status === 'FERMÉ';
                }} else if (filter === 'leverage') {{
                    show = item.dataset.type && item.dataset.type.includes('LEVIER');
                }} else if (filter === 'spot') {{
                    show = !item.dataset.type || !item.dataset.type.includes('LEVIER');
                }}
                
                item.style.display = show ? 'grid' : 'none';
            }});
        }}
        
        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {{
            updateTradesData();
            setInterval(updateTradesData, 30000); // 30 secondes
        }});
    </script>
</body>
</html>
    '''

def update_crypto_analysis():
    """Met à jour l'analyse de toutes les cryptos"""
    while True:
        try:
            print(f"\n🧠 Analyse IA des signaux - {datetime.now().strftime('%H:%M:%S')}")
            
            for pair in TRADING_PAIRS.keys():
                try:
                    # Récupérer le prix
                    price, change_24h, source = price_feeder.get_crypto_price(pair)
                    
                    if price:
                        crypto_data = dashboard_data['cryptos'][pair]
                        
                        # Mettre à jour prix et historique
                        crypto_data['price'] = price
                        crypto_data['price_change_24h'] = change_24h
                        crypto_data['price_source'] = source
                        
                        # Ajouter à l'historique (garder 20 derniers prix)
                        crypto_data['price_history'].append(price)
                        if len(crypto_data['price_history']) > 20:
                            crypto_data['price_history'].pop(0)
                        
                        # Calculer volatilité
                        crypto_data['volatility'] = leverage_analyzer.calculate_volatility(
                            crypto_data['price_history']
                        )
                        
                        # Calculer score de confiance
                        crypto_data['confidence_score'] = leverage_analyzer.calculate_confidence_score(
                            pair, crypto_data
                        )
                        
                        # Recommander levier
                        crypto_data['recommended_leverage'] = leverage_analyzer.recommend_leverage(
                            pair, crypto_data
                        )
                        
                        # Récupérer le taux de funding
                        funding_rate, funding_source = funding_manager.get_funding_rate(pair)
                        crypto_data['funding_rate'] = funding_rate
                        
                        # Ajouter à l'historique des funding rates
                        crypto_data['funding_history'].append({
                            'timestamp': datetime.now().isoformat(),
                            'rate': funding_rate,
                            'source': funding_source
                        })
                        if len(crypto_data['funding_history']) > 24:  # Garder 24 derniers points
                            crypto_data['funding_history'].pop(0)
                        
                        print(f"🎯 {pair}: ${price:,.2f} | Confiance: {crypto_data['confidence_score']:.1f}% | "
                              f"Levier rec.: {crypto_data['recommended_leverage']:.1f}x | "
                              f"Volatilité: {crypto_data['volatility']:.1f}% | "
                              f"Funding: {funding_rate:+.3f}%")
                
                except Exception as e:
                    print(f"❌ Erreur analyse {pair}: {e}")
            
            # Mettre à jour le portefeuille global
            update_global_portfolio()
            dashboard_data['portfolio']['last_update'] = datetime.now().isoformat()
            
        except Exception as e:
            print(f"❌ Erreur analyse globale: {e}")
        
        time.sleep(30)  # Analyse toutes les 30 secondes

def intelligent_leveraged_trading():
    """Trading intelligent avec levier"""
    while True:
        try:
            for pair, crypto_data in dashboard_data['cryptos'].items():
                # Analyser si on doit trader avec levier
                confidence = crypto_data['confidence_score']
                recommended_leverage = crypto_data['recommended_leverage']
                min_confidence = crypto_data['min_confidence']
                current_price = crypto_data['price']
                
                # Conditions pour un trade avec levier (plus agressif)
                should_leverage_trade = (
                    confidence >= min_confidence and 
                    recommended_leverage > 1.5 and  # Seuil plus bas
                    crypto_data['crypto_balance'] == 0 and  # Pas de position ouverte
                    crypto_data['usdc_balance'] > 300 and   # Capital réduit pour plus de trades
                    random.random() < 0.08  # 8% chance par cycle (plus élevé)
                )
                
                # Conditions pour un trade normal (sans levier)
                should_normal_trade = (
                    confidence >= (min_confidence - 15) and  # Seuil encore plus bas
                    crypto_data['crypto_balance'] == 0 and
                    crypto_data['usdc_balance'] > 200 and   # Capital réduit
                    random.random() < 0.06  # 6% chance par cycle (plus élevé)
                )
                
                if should_leverage_trade:
                    # TRADE AVEC LEVIER (Plus agressif)
                    leverage_used = min(recommended_leverage, crypto_data['max_leverage'])
                    leverage_used = round(leverage_used, 1)
                    
                    # Montant de base (plus agressif)
                    base_amount = min(2000, crypto_data['usdc_balance'] * 0.15)  # Jusqu'à 15% du capital
                    
                    # Montant effectif avec levier
                    effective_amount = base_amount * leverage_used
                    crypto_bought = effective_amount / current_price
                    
                    # Générer ID unique pour le trade
                    crypto_data['trade_id'] += 1
                    trade_id = f"{pair.split('/')[0]}-{crypto_data['trade_id']:03d}"
                    
                    # Enregistrer le trade d'ouverture
                    trade_record = {
                        'id': trade_id,
                        'pair': pair,
                        'type': 'ACHAT_LEVIER',
                        'timestamp': datetime.now().isoformat(),
                        'price': current_price,
                        'amount': crypto_bought,
                        'leverage': leverage_used,
                        'margin_used': base_amount,
                        'effective_size': effective_amount,
                        'confidence': confidence,
                        'funding_rate': crypto_data['funding_rate'],
                        'status': 'OUVERT',
                        'entry_price': current_price,
                        'pnl': 0.0,
                        'funding_cost': 0.0
                    }
                    
                    dashboard_data['trades_history'].insert(0, trade_record)  # Ajouter en premier
                    dashboard_data['active_positions'][trade_id] = trade_record
                    
                    # Marge utilisée = montant de base
                    crypto_data['usdc_balance'] -= base_amount
                    crypto_data['crypto_balance'] += crypto_bought
                    crypto_data['current_leverage'] = leverage_used
                    crypto_data['margin_used'] = base_amount
                    crypto_data['entry_time'] = datetime.now()  # Timestamp d'entrée
                    crypto_data['current_trade_id'] = trade_id  # Stocker l'ID du trade actuel
                    crypto_data['total_trades'] += 1
                    crypto_data['leveraged_trades'] += 1
                    
                    dashboard_data['portfolio']['leveraged_trades'] += 1
                    dashboard_data['portfolio']['max_leverage_used'] = max(
                        dashboard_data['portfolio']['max_leverage_used'], leverage_used
                    )
                    
                    # Estimer le coût de funding quotidien
                    daily_funding = funding_manager.estimate_daily_funding(pair, effective_amount)
                    
                    print(f"⚡ ACHAT LEVIER {pair}: {crypto_bought:.6f} à ${current_price:.2f} "
                          f"(ID: {trade_id}, Levier: {leverage_used:.1f}x, Confiance: {confidence:.1f}%, "
                          f"Funding/jour: ${daily_funding:+.2f})")
                    
                elif should_normal_trade:
                    # TRADE NORMAL (SPOT) - Plus agressif
                    base_amount = min(800, crypto_data['usdc_balance'] * 0.08)  # 8% du capital
                    crypto_bought = base_amount / current_price
                    
                    # Générer ID unique pour le trade
                    crypto_data['trade_id'] += 1
                    trade_id = f"{pair.split('/')[0]}-{crypto_data['trade_id']:03d}"
                    
                    # Enregistrer le trade d'ouverture
                    trade_record = {
                        'id': trade_id,
                        'pair': pair,
                        'type': 'ACHAT_SPOT',
                        'timestamp': datetime.now().isoformat(),
                        'price': current_price,
                        'amount': crypto_bought,
                        'leverage': 1.0,
                        'margin_used': 0,
                        'effective_size': base_amount,
                        'confidence': confidence,
                        'funding_rate': 0,
                        'status': 'OUVERT',
                        'entry_price': current_price,
                        'pnl': 0.0,
                        'funding_cost': 0.0
                    }
                    
                    dashboard_data['trades_history'].insert(0, trade_record)
                    dashboard_data['active_positions'][trade_id] = trade_record
                    
                    crypto_data['usdc_balance'] -= base_amount
                    crypto_data['crypto_balance'] += crypto_bought
                    crypto_data['current_leverage'] = 1.0
                    crypto_data['margin_used'] = 0
                    crypto_data['current_trade_id'] = trade_id
                    crypto_data['total_trades'] += 1
                    
                    print(f"🔵 ACHAT SPOT {pair}: {crypto_bought:.6f} à ${current_price:.2f} "
                          f"(ID: {trade_id}, Confiance: {confidence:.1f}%)")
                
                # Vente (si on a une position) - Plus fréquente
                elif crypto_data['crypto_balance'] > 0 and random.random() < 0.12:  # 12% chance de vendre (plus élevé)
                    crypto_to_sell = crypto_data['crypto_balance']
                    usdc_received = crypto_to_sell * current_price
                    trade_id = crypto_data.get('current_trade_id', 'UNKNOWN')
                    
                    # Calculer les frais de funding si position avec levier
                    funding_cost = 0.0
                    if crypto_data['current_leverage'] > 1 and crypto_data['entry_time']:
                        # Calculer le temps écoulé en heures
                        time_held = (datetime.now() - crypto_data['entry_time']).total_seconds() / 3600
                        position_size = crypto_data['margin_used'] * crypto_data['current_leverage']
                        funding_cost = funding_manager.calculate_funding_cost(
                            pair, position_size, crypto_data['current_leverage'], time_held
                        )
                        crypto_data['total_funding_paid'] += funding_cost
                    
                    # Calculer P&L
                    if crypto_data['current_leverage'] > 1:
                        # Trade avec levier
                        initial_investment = crypto_data['margin_used']
                        profit_with_leverage = usdc_received - (initial_investment * crypto_data['current_leverage'])
                        # Soustraire les frais de funding
                        net_profit = profit_with_leverage - funding_cost
                        final_amount = initial_investment + net_profit
                        
                        crypto_data['usdc_balance'] += final_amount
                        crypto_data['profit_loss'] += net_profit
                        
                        # Enregistrer la clôture du trade
                        if trade_id in dashboard_data['active_positions']:
                            trade_record = dashboard_data['active_positions'][trade_id].copy()
                            trade_record.update({
                                'type': 'VENTE_LEVIER',
                                'close_timestamp': datetime.now().isoformat(),
                                'close_price': current_price,
                                'pnl': net_profit,
                                'pnl_brut': profit_with_leverage,
                                'funding_cost': funding_cost,
                                'status': 'FERMÉ',
                                'duration_hours': time_held,
                                'return_pct': (net_profit / initial_investment) * 100
                            })
                            
                            # Mise à jour dans l'historique
                            for i, trade in enumerate(dashboard_data['trades_history']):
                                if trade['id'] == trade_id:
                                    dashboard_data['trades_history'][i] = trade_record
                                    break
                            
                            del dashboard_data['active_positions'][trade_id]
                        
                        print(f"⚡ VENTE LEVIER {pair}: {crypto_to_sell:.6f} à ${current_price:.2f} "
                              f"(ID: {trade_id}, Levier: {crypto_data['current_leverage']:.1f}x, "
                              f"P&L brut: ${profit_with_leverage:+.2f}, "
                              f"Funding: ${funding_cost:+.2f}, "
                              f"P&L net: ${net_profit:+.2f})")
                    else:
                        # Trade normal
                        crypto_data['usdc_balance'] += usdc_received
                        trade_pnl = usdc_received - (dashboard_data['active_positions'].get(trade_id, {}).get('effective_size', 500))
                        crypto_data['profit_loss'] += trade_pnl
                        
                        # Enregistrer la clôture du trade
                        if trade_id in dashboard_data['active_positions']:
                            trade_record = dashboard_data['active_positions'][trade_id].copy()
                            trade_record.update({
                                'type': 'VENTE_SPOT',
                                'close_timestamp': datetime.now().isoformat(),
                                'close_price': current_price,
                                'pnl': trade_pnl,
                                'status': 'FERMÉ',
                                'return_pct': (trade_pnl / trade_record['effective_size']) * 100
                            })
                            
                            # Mise à jour dans l'historique
                            for i, trade in enumerate(dashboard_data['trades_history']):
                                if trade['id'] == trade_id:
                                    dashboard_data['trades_history'][i] = trade_record
                                    break
                            
                            del dashboard_data['active_positions'][trade_id]
                        
                        print(f"🔵 VENTE SPOT {pair}: {crypto_to_sell:.6f} à ${current_price:.2f} "
                              f"(ID: {trade_id}, P&L: ${trade_pnl:+.2f})")
                    
                    # Mise à jour des stats
                    final_value = usdc_received if crypto_data['current_leverage'] == 1 else final_amount
                    initial_value = dashboard_data['active_positions'].get(trade_id, {}).get('effective_size', 500) if crypto_data['current_leverage'] == 1 else crypto_data['margin_used']
                    
                    if final_value > initial_value:
                        crypto_data['winning_trades'] += 1
                    else:
                        crypto_data['losing_trades'] += 1
                    
                    crypto_data['win_rate'] = (crypto_data['winning_trades'] / 
                                             max(1, crypto_data['winning_trades'] + crypto_data['losing_trades'])) * 100
                    
                    # Reset position
                    crypto_data['crypto_balance'] = 0
                    crypto_data['current_leverage'] = 1.0
                    crypto_data['margin_used'] = 0
                    crypto_data['entry_time'] = None
                    crypto_data['current_trade_id'] = None
                    
                    # Mettre à jour la valeur du portefeuille
                    crypto_data['portfolio_value'] = crypto_data['usdc_balance'] + (crypto_data['crypto_balance'] * current_price)
                    crypto_data['profit_percent'] = ((crypto_data['portfolio_value'] - 10000) / 10000) * 100
            
        except Exception as e:
            print(f"❌ Erreur trading intelligent: {e}")
        
        time.sleep(30)  # Trading toutes les 30 secondes (plus fréquent)

def update_global_portfolio():
    """Met à jour les statistiques globales avec gestion du risque"""
    total_value = sum(crypto['portfolio_value'] for crypto in dashboard_data['cryptos'].values())
    total_pnl = total_value - 40000
    total_trades = sum(crypto['total_trades'] for crypto in dashboard_data['cryptos'].values())
    leveraged_trades = sum(crypto['leveraged_trades'] for crypto in dashboard_data['cryptos'].values())
    total_margin = sum(crypto['margin_used'] for crypto in dashboard_data['cryptos'].values())
    
    # Enregistrer l'évolution du portefeuille
    timestamp = datetime.now().isoformat()
    dashboard_data['portfolio']['value_history'].append({
        'timestamp': timestamp,
        'value': total_value,
        'pnl': total_pnl
    })
    
    # Garder seulement les 100 derniers points (≈ 50 minutes d'historique)
    if len(dashboard_data['portfolio']['value_history']) > 100:
        dashboard_data['portfolio']['value_history'].pop(0)
    
    # Enregistrer l'évolution du P&L
    dashboard_data['portfolio']['pnl_history'].append({
        'timestamp': timestamp,
        'pnl': total_pnl,
        'pnl_percent': (total_pnl / 40000) * 100
    })
    
    # Garder seulement les 100 derniers points
    if len(dashboard_data['portfolio']['pnl_history']) > 100:
        dashboard_data['portfolio']['pnl_history'].pop(0)
    
    # Déterminer le niveau de risque (plus agressif)
    max_leverage_used = dashboard_data['portfolio']['max_leverage_used']
    risk_level = 'MEDIUM'  # Par défaut plus de risque
    if max_leverage_used > 7:
        risk_level = 'HIGH'
    elif max_leverage_used > 3 or total_margin > 4000:
        risk_level = 'HIGH'
    elif total_margin < 1000:
        risk_level = 'LOW'
    
    dashboard_data['portfolio'].update({
        'total_value': total_value,
        'total_profit_loss': total_pnl,
        'total_profit_percent': (total_pnl / 40000) * 100,
        'total_trades': total_trades,
        'leveraged_trades': leveraged_trades,
        'total_margin_used': total_margin,
        'risk_level': risk_level
    })
    
    # Garder seulement les 50 derniers trades dans l'historique
    if len(dashboard_data['trades_history']) > 50:
        dashboard_data['trades_history'] = dashboard_data['trades_history'][:50]

if __name__ == '__main__':
    print("⚡ BOT MULTI-CRYPTOS AVEC LEVIER INTELLIGENT")
    print("🌐 http://localhost:5005")
    print("🎯 Analyse IA des signaux en temps réel")
    print("📊 Levier adaptatif selon la confiance")
    print("🛡️ Gestion intelligente des risques")
    print("💰 ETH • BTC • SOL • XRP")
    print()
    
    # Lancer les threads
    analysis_thread = threading.Thread(target=update_crypto_analysis, daemon=True)
    analysis_thread.start()
    
    trading_thread = threading.Thread(target=intelligent_leveraged_trading, daemon=True)
    trading_thread.start()
    
    # Lancer le serveur
    app.run(host='0.0.0.0', port=5005, debug=False)
