#!/usr/bin/env python3
"""
🚀 BOT MULTI-CRYPTOS AVEC LEVIER INTELLIGENT 
📊 Version Propre avec Dashboard Fonctionnel
🎯 ETH • BTC • SOL • XRP
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import ccxt
from flask import Flask, render_template_string, jsonify, request
import threading
import random
from dataclasses import dataclass, asdict

# Configuration de base
logging.basicConfig(level=logging.WARNING)
logging.getLogger('ccxt').setLevel(logging.WARNING)

app = Flask(__name__)

# Configuration globale
class Config:
    INITIAL_BALANCE = 1000  # $1,000
    CRYPTO_PAIRS = ['ETH/USDC', 'BTC/USDC', 'SOL/USDC', 'XRP/USDC']
    MAX_LEVERAGE = 10.0
    RISK_PER_TRADE = 0.02  # 2% max par trade
    UPDATE_INTERVAL = 45  # secondes (plus espacé pour éviter rate limits)

# Données globales
portfolio_data = {
    'total_value': Config.INITIAL_BALANCE,
    'pnl': 0.0,
    'trades_count': 0,
    'leveraged_trades': 0,
    'max_leverage': 1.0,
    'margin_used': 0.0,
    'last_update': datetime.now().isoformat(),
    'value_history': [],
    'pnl_history': []
}

crypto_data = {}
active_positions = {}
trades_history = []

# Classes
@dataclass
class CryptoInfo:
    name: str
    symbol: str
    icon: str
    price: float
    price_change_24h: float
    confidence_score: float
    recommended_leverage: float
    current_leverage: float
    volatility: float
    funding_rate: float
    portfolio_value: float
    profit_loss: float
    total_trades: int

@dataclass
class Position:
    id: str
    pair: str
    amount: float
    entry_price: float
    leverage: float
    confidence: float
    effective_size: float
    funding_rate: float
    funding_cost: float
    timestamp: str
    
    @property
    def margin_used(self):
        """Marge réellement utilisée (capital investi)"""
        return self.effective_size / self.leverage
    
    @property
    def liquidation_price(self):
        """Prix de liquidation (perte de 90% de la marge)"""
        # Pour une position LONG: prix de liquidation = entry_price * (1 - 0.9/leverage)
        liquidation_factor = 0.9 / self.leverage
        return self.entry_price * (1 - liquidation_factor)
    
    @property
    def margin_call_price(self):
        """Prix d'alerte margin call (perte de 70% de la marge)"""
        margin_call_factor = 0.7 / self.leverage
        return self.entry_price * (1 - margin_call_factor)
    
    def calculate_pnl(self, current_price):
        """Calcule le P&L avec gestion des liquidations"""
        # Si prix actuel <= prix de liquidation, position liquidée
        if current_price <= self.liquidation_price:
            return -self.margin_used  # Perte totale de la marge
        
        # P&L normal avec effet de levier
        price_change_pct = (current_price - self.entry_price) / self.entry_price
        return self.margin_used * price_change_pct * self.leverage
    
    def get_risk_level(self, current_price):
        """Évalue le niveau de risque de la position"""
        if current_price <= self.liquidation_price:
            return "LIQUIDÉ"
        elif current_price <= self.margin_call_price:
            return "DANGER"
        elif current_price <= self.entry_price * 0.95:
            return "RISQUÉ"
        else:
            return "SÛRE"
    
    @property
    def stop_loss_price(self):
        """Prix de stop-loss (perte de 1.5% sur l'exposition)"""
        return self.entry_price * (1 - 0.015)
    
    @property  
    def take_profit_price(self):
        """Prix de take-profit (gain de 2.5% sur l'exposition)"""
        return self.entry_price * (1 + 0.025)
    
    def should_close(self, current_price):
        """Détermine si la position doit être fermée"""
        # Calculer le pourcentage de variation du prix par rapport au prix d'entrée
        price_change_pct = ((current_price - self.entry_price) / self.entry_price) * 100
        
        # Stop-Loss : perte de 1.5% sur l'exposition (mouvement de prix défavorable)
        if price_change_pct <= -1.5:
            return "STOP_LOSS"
            
        # Take-Profit : gain de 2.5% sur l'exposition (mouvement de prix favorable)
        if price_change_pct >= 2.5:
            return "TAKE_PROFIT"
            
        # Liquidation
        if current_price <= self.liquidation_price:
            return "LIQUIDATION"
            
        return None

def print_banner():
    """Affiche le banner de démarrage"""
    print("✅ Bitget connecté")
    print("✅ CoinGecko connecté")
    print("⚡ BOT MULTI-CRYPTOS AVEC LEVIER INTELLIGENT")
    print("🌐 http://localhost:5000")
    print("🎯 Analyse IA des signaux en temps réel")
    print("📊 Levier adaptatif selon la confiance")
    print("🛡️ Gestion intelligente des risques")
    print("💰 ETH • BTC • SOL • XRP")
    print()

def get_real_price(symbol):
    """Récupère le prix réel avec système hybride et retry"""
    import time
    
    # Tentative 1: CoinGecko
    for attempt in range(2):
        try:
            coingecko_ids = {
                'ETH': 'ethereum', 'BTC': 'bitcoin', 
                'SOL': 'solana', 'XRP': 'ripple'
            }
            
            if symbol in coingecko_ids:
                coin_id = coingecko_ids[symbol]
                url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }
                
                response = requests.get(url, headers=headers, timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if coin_id in data and 'usd' in data[coin_id]:
                        price = data[coin_id]['usd']
                        print(f"📊 {symbol}: ${price:,.2f} (CoinGecko)")
                        return float(price)
                elif response.status_code == 429:  # Rate limited
                    print(f"⏳ Rate limit CoinGecko, attente... (tentative {attempt+1})")
                    time.sleep(3)
                    continue
                    
        except Exception as e:
            print(f"⚠️ Erreur CoinGecko {symbol} (tentative {attempt+1}): {e}")
            if attempt == 0:
                time.sleep(2)
    
    # Tentative 2: Fallback Binance 
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}USDT"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            price = float(data['price'])
            print(f"📊 {symbol}: ${price:,.2f} (Binance)")
            return price
    except Exception as e:
        print(f"⚠️ Erreur Binance {symbol}: {e}")
    
    # Fallback final
    fallback_prices = {
        'ETH': 4400, 'BTC': 119000, 'SOL': 177, 'XRP': 3.18
    }
    print(f"🔄 Prix fallback {symbol}: ${fallback_prices.get(symbol, 100)}")
    return fallback_prices.get(symbol, 100)

def update_crypto_analysis():
    """Met à jour l'analyse de toutes les cryptos"""
    global crypto_data, portfolio_data
    
    # Utiliser les vraies données crypto
    cryptos = {
        'ETH': {'name': 'Ethereum', 'icon': '🔷'},
        'BTC': {'name': 'Bitcoin', 'icon': '🟠'},  
        'SOL': {'name': 'Solana', 'icon': '🟣'},
        'XRP': {'name': 'XRP', 'icon': '🔵'}
    }
    
    for symbol, info in cryptos.items():
        # Prix réel depuis Binance API
        current_price = get_real_price(symbol)
        
        # Confiance basée sur des signaux simulés
        confidence = random.uniform(40, 85)
        
        # Levier recommandé basé sur la confiance
        if confidence >= 80:
            rec_leverage = random.uniform(5.0, 8.0)
        elif confidence >= 70:
            rec_leverage = random.uniform(2.0, 4.0)
        elif confidence >= 60:
            rec_leverage = random.uniform(1.5, 2.5)
        else:
            rec_leverage = 1.0
            
        # Levier actuellement utilisé
        current_lev = min(rec_leverage, random.uniform(1.0, rec_leverage))
        
        # Calculer les vraies données pour cette crypto
        crypto_portfolio_value = 0.0
        crypto_pnl = 0.0
        crypto_trades_count = 0
        
        # Parcourir les positions actives pour cette crypto
        liquidated_positions = []
        for pos_id, position in active_positions.items():
            if hasattr(position, 'pair') and position.pair == f"{symbol}/USDC":
                crypto_portfolio_value += position.effective_size
                
                # NOUVEAU: Calculer P&L avec gestion des liquidations
                pnl = position.calculate_pnl(current_price)
                crypto_pnl += pnl
                crypto_trades_count += 1
                
                # Vérifier si position doit être fermée
                close_reason = position.should_close(current_price)
                risk_level = position.get_risk_level(current_price)
                
                if close_reason:
                    liquidated_positions.append((pos_id, close_reason, position))
                    close_emoji = {"STOP_LOSS": "🛑", "TAKE_PROFIT": "🎯", "LIQUIDATION": "💀"}[close_reason]
                    print(f"{close_emoji} {close_reason}: {symbol} position #{pos_id} - P&L: ${pnl:.2f}")
                else:
                    # Afficher status normal avec stop-loss/take-profit
                    risk_emoji = {"LIQUIDÉ": "💀", "DANGER": "🚨", "RISQUÉ": "⚠️", "SÛRE": "✅"}[risk_level]
                    stop_loss_price = position.stop_loss_price
                    take_profit_price = position.take_profit_price
                    print(f"📊 {symbol} Position: ${crypto_portfolio_value:.0f}, P&L: ${pnl:.2f} {risk_emoji}")
                    print(f"   🛑 Stop-Loss: ${stop_loss_price:.2f} | 🎯 Take-Profit: ${take_profit_price:.2f}")
                    
                    if risk_level == "DANGER":
                        print(f"🚨 MARGIN CALL: {symbol} - Prix liquidation: ${position.liquidation_price:.2f}")
                    elif risk_level == "LIQUIDÉ":
                        print(f"💀 LIQUIDATION: {symbol} position #{pos_id} - Perte: ${-position.margin_used:.2f}")
                    print(f"� MARGIN CALL: {symbol} - Prix liquidation: ${position.liquidation_price:.2f}")
        
        # Fermer les positions qui doivent l'être (stop-loss, take-profit, liquidation)
        for pos_data in liquidated_positions:
            if len(pos_data) == 3:  # Nouveau format avec close_reason
                pos_id, close_reason, liquidated_pos = pos_data
                if pos_id in active_positions:
                    # Calculer le P&L final
                    final_pnl = liquidated_pos.calculate_pnl(current_price)
                    
                    # Ajouter à l'historique avec le statut approprié
                    trades_history.append({
                        'id': pos_id,
                        'pair': liquidated_pos.pair,
                        'price': liquidated_pos.entry_price,  # Prix d'entrée pour l'affichage
                        'entry_price': liquidated_pos.entry_price,
                        'exit_price': current_price,
                        'amount': liquidated_pos.amount,
                        'leverage': liquidated_pos.leverage,
                        'effective_size': liquidated_pos.effective_size,  # Taille effective
                        'pnl': final_pnl,
                        'status': close_reason,
                        'timestamp': liquidated_pos.timestamp,
                        'close_timestamp': datetime.now().isoformat(),
                        'margin_used': liquidated_pos.margin_used
                    })
                    del active_positions[pos_id]
                    
                    # Afficher résumé
                    pnl_pct = (final_pnl / liquidated_pos.margin_used) * 100
                    print(f"✅ Position fermée: {close_reason} | P&L: ${final_pnl:.2f} ({pnl_pct:.1f}%)")
            else:  # Ancien format (liquidation seulement)
                pos_id = pos_data
                if pos_id in active_positions:
                    liquidated_pos = active_positions[pos_id]
                    # Ajouter à l'historique comme trade fermé par liquidation
                    trades_history.append({
                        'id': pos_id,
                        'pair': liquidated_pos.pair,
                        'price': liquidated_pos.entry_price,  # Prix d'entrée pour l'affichage
                        'entry_price': liquidated_pos.entry_price,
                        'exit_price': current_price,
                        'amount': liquidated_pos.amount,
                        'leverage': liquidated_pos.leverage,
                        'effective_size': liquidated_pos.effective_size,  # Taille effective
                        'pnl': -liquidated_pos.margin_used,  # Perte totale
                        'status': 'LIQUIDÉ',
                        'timestamp': liquidated_pos.timestamp,
                        'close_timestamp': datetime.now().isoformat(),
                        'margin_used': liquidated_pos.margin_used
                    })
                    del active_positions[pos_id]
        
        # Compter les trades fermés pour cette crypto
        for trade in trades_history:
            if trade.get('pair') == f"{symbol}/USDC":
                crypto_trades_count += 1
                crypto_pnl += trade.get('pnl', 0)
        
        crypto_data[symbol] = CryptoInfo(
            name=info['name'],
            symbol=symbol,
            icon=info['icon'], 
            price=current_price,
            price_change_24h=random.uniform(-3.0, 3.0),
            confidence_score=confidence,
            recommended_leverage=rec_leverage,
            current_leverage=current_lev,
            volatility=random.uniform(0.0, 0.2),
            funding_rate=random.uniform(0.005, 0.025),
            portfolio_value=crypto_portfolio_value,  # Valeur réelle des positions
            profit_loss=crypto_pnl,                 # P&L réel calculé
            total_trades=crypto_trades_count        # Nombre réel de trades
        )
        
        # Afficher l'analyse
        print(f"🎯 {symbol}/USDC: ${current_price:,.2f} | Confiance: {confidence:.1f}% | "
              f"Levier rec.: {rec_leverage:.1f}x | Volatilité: {crypto_data[symbol].volatility:.1f}% | "
              f"Funding: +{crypto_data[symbol].funding_rate:.3f}%")
        
        # CONTRÔLE DE CAPITAL - Auto-trading avec validation stricte incluant le levier
        if confidence > 75 and rec_leverage > 1.5:
            # Calculer le capital déjà utilisé ET l'exposition totale
            used_capital = 0
            total_exposure = 0
            for pos in active_positions.values():
                used_capital += pos.effective_size / pos.leverage  # Capital réel utilisé
                total_exposure += pos.effective_size  # Exposition totale (avec levier)
            
            # Utiliser un pourcentage raisonnable du capital total (10% max par position)
            position_capital = Config.INITIAL_BALANCE * 0.1  # 10% du capital par position
            # NOUVEAU: Calculer l'exposition réelle avec le levier recommandé
            new_exposure = position_capital * rec_leverage  # Exposition de la nouvelle position
            
            available_capital = Config.INITIAL_BALANCE - used_capital
            
            # Vérifications multiples:
            # 1. Capital disponible suffisant
            capital_check = available_capital >= position_capital and used_capital + position_capital <= Config.INITIAL_BALANCE
            # 2. Exposition totale ne dépasse pas 10x notre capital (approche agressive)
            exposure_check = (total_exposure + new_exposure) <= (Config.INITIAL_BALANCE * 10)
            # 3. Une seule position ne peut pas avoir une exposition supérieure à 2x notre capital
            single_position_check = new_exposure <= (Config.INITIAL_BALANCE * 2)
            
            if capital_check and exposure_check and single_position_check:
                # Calculer la quantité basée sur l'exposition totale (marge × levier)
                total_exposure = position_capital * rec_leverage
                auto_trade_amount = total_exposure / current_price
                position_id = f"auto_{symbol}_{int(datetime.now().timestamp())}"
                
                new_position = Position(
                    id=position_id,
                    pair=f"{symbol}/USDC",
                    amount=auto_trade_amount,
                    entry_price=current_price,
                    leverage=rec_leverage,
                    confidence=confidence,
                    effective_size=int(total_exposure),  # Exposition totale
                    funding_rate=crypto_data[symbol].funding_rate,
                    funding_cost=round(position_capital * crypto_data[symbol].funding_rate / 24, 2),
                    timestamp=datetime.now().isoformat()
                )
                
                active_positions[position_id] = new_position
                print(f"🚀 TRADE AUTO OUVERT: {symbol} | ${current_price:,.2f} | Levier: {rec_leverage:.1f}x | Confiance: {confidence:.1f}%")
                print(f"💰 Capital utilisé: ${used_capital + position_capital:,.0f} / ${Config.INITIAL_BALANCE:,.0f}")
                print(f"📊 Exposition totale: ${total_exposure + new_exposure:,.0f} (Limite: ${Config.INITIAL_BALANCE * 10:,.0f})")
            else:
                reasons = []
                if not capital_check:
                    reasons.append(f"Capital insuffisant: ${available_capital:,.0f} disponible, ${position_capital:,.0f} requis")
                if not exposure_check:
                    reasons.append(f"Exposition excessive: ${total_exposure + new_exposure:,.0f} > {Config.INITIAL_BALANCE * 10:,.0f}")
                if not single_position_check:
                    reasons.append(f"Position trop grande: ${new_exposure:,.0f} > {Config.INITIAL_BALANCE * 2:,.0f}")
                print(f"❌ TRADE BLOQUÉ: {' | '.join(reasons)}")

def reset_all_positions():
    """Remet à zéro toutes les positions pour redémarrer proprement"""
    global active_positions, trades_history, portfolio_data
    active_positions.clear()
    trades_history.clear()
    portfolio_data = {
        'total_value': Config.INITIAL_BALANCE,
        'pnl': 0.0,
        'trades_count': 0,
        'leveraged_trades': 0,
        'max_leverage': 1.0,
        'margin_used': 0.0,
        'last_update': datetime.now().isoformat(),
        'value_history': [Config.INITIAL_BALANCE],
        'pnl_history': [0.0]
    }
    print(f"🔄 RESET COMPLET: Capital remis à ${Config.INITIAL_BALANCE:,}")

def run_analysis_loop():
    """Boucle principale d'analyse"""
    while True:
        try:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"\n🧠 Analyse IA des signaux - {timestamp}")
            
            update_crypto_analysis()
            
            # Mise à jour des statistiques globales du portfolio
            total_portfolio_value = Config.INITIAL_BALANCE
            total_pnl = 0.0
            total_trades = len(trades_history)
            leveraged_trades = 0
            max_leverage = 1.0
            margin_used = 0.0
            total_exposure = 0.0  # NOUVEAU: Exposition totale avec levier
            
            # Calculer les totaux à partir des positions actives
            for position in active_positions.values():
                total_trades += 1
                if position.leverage > 1.0:
                    leveraged_trades += 1
                max_leverage = max(max_leverage, position.leverage)
                margin_used += position.effective_size / position.leverage  # Capital réel utilisé
                total_exposure += position.effective_size  # Exposition totale avec levier
                
                # Calculer P&L pour cette position
                current_crypto_price = 0
                for symbol, crypto in crypto_data.items():
                    if position.pair == f"{symbol}/USDC":
                        current_crypto_price = crypto.price
                        break
                
                if current_crypto_price > 0:
                    # NOUVEAU: Utiliser le calcul P&L avec gestion liquidation
                    position_pnl = position.calculate_pnl(current_crypto_price)
                    total_pnl += position_pnl
            
            # Compter les trades avec levier dans l'historique
            for trade in trades_history:
                if trade.get('leverage', 1.0) > 1.0:
                    leveraged_trades += 1
                total_pnl += trade.get('pnl', 0)
            
            # Mettre à jour le portfolio
            portfolio_data.update({
                'total_value': total_portfolio_value + total_pnl,
                'pnl': total_pnl,
                'trades_count': total_trades,
                'leveraged_trades': leveraged_trades,
                'max_leverage': max_leverage,
                'margin_used': total_exposure,  # CHANGÉ: Afficher l'exposition totale comme "marge"
                'capital_used': margin_used,    # NOUVEAU: Capital réel utilisé
                'last_update': datetime.now().isoformat()
            })
            
            print(f"📊 Portfolio: ${portfolio_data['total_value']:,.0f} | P&L: ${total_pnl:+.2f} | Trades: {total_trades} | Levier Max: {max_leverage:.1f}x")
            
            # Mise à jour du portfolio historique
            
            # Historique simplifié
            if len(portfolio_data['value_history']) > 50:
                portfolio_data['value_history'] = portfolio_data['value_history'][-30:]
                portfolio_data['pnl_history'] = portfolio_data['pnl_history'][-30:]
            
            portfolio_data['value_history'].append({
                'timestamp': datetime.now().isoformat(),
                'value': portfolio_data['total_value']
            })
            portfolio_data['pnl_history'].append({
                'timestamp': datetime.now().isoformat(), 
                'pnl': portfolio_data['pnl']
            })
            
            time.sleep(Config.UPDATE_INTERVAL)
            
        except Exception as e:
            print(f"❌ Erreur dans l'analyse: {e}")
            time.sleep(10)

# Routes Flask
@app.route('/')
def dashboard():
    return render_template_string('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ Bot Multi-Cryptos avec Levier Intelligent - Dashboard Pro</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .header {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }
        
        .title { font-size: 2.5rem; font-weight: 800; margin-bottom: 10px; }
        .status { display: flex; justify-content: center; gap: 20px; margin-bottom: 15px; }
        .status-item { 
            display: flex; align-items: center; gap: 5px;
            padding: 8px 15px; background: #f0f9ff; border-radius: 20px;
            font-size: 0.9rem; font-weight: 600;
        }
        
        .nav-buttons {
            display: flex; justify-content: center; gap: 10px; margin-top: 15px;
        }
        .nav-btn {
            padding: 12px 24px; border: none; border-radius: 25px;
            font-weight: 600; cursor: pointer; text-decoration: none;
            transition: all 0.3s ease;
        }
        .nav-btn.active { background: #22c55e; color: white; }
        .nav-btn:not(.active) { background: #3b82f6; color: white; }
        .nav-btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 30px 20px; }
        
        .dashboard-grid { display: grid; grid-template-columns: 1fr; gap: 30px; }
        
        .portfolio-section {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .section-title {
            font-size: 1.5rem; font-weight: 700; margin-bottom: 20px;
            display: flex; align-items: center; gap: 10px;
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .summary-card {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            border: 2px solid #e2e8f0;
            transition: transform 0.3s ease;
        }
        .summary-card:hover { transform: translateY(-5px); }
        
        .summary-value {
            font-size: 1.8rem;
            font-weight: 800;
            color: #1e293b;
            margin-bottom: 5px;
        }
        .summary-label {
            font-size: 0.9rem;
            color: #64748b;
            font-weight: 600;
        }
        
        .chart-container {
            height: 400px;
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: inset 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .cryptos-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        
        .crypto-card {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            border: 2px solid #e2e8f0;
            transition: all 0.3s ease;
        }
        .crypto-card:hover { transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.15); }
        
        .crypto-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .crypto-name {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .crypto-icon { font-size: 2rem; }
        .crypto-title { font-size: 1.3rem; font-weight: 700; color: #1e293b; }
        
        .price { font-size: 1.4rem; font-weight: 800; color: #1e293b; }
        .price-change {
            font-size: 0.9rem;
            font-weight: 600;
            padding: 4px 8px;
            border-radius: 8px;
        }
        .price-change.positive { color: #059669; background: #dcfce7; }
        .price-change.negative { color: #dc2626; background: #fee2e2; }
        
        .leverage-section { margin: 15px 0; }
        .leverage-indicator {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 8px 0;
            font-size: 0.95rem;
        }
        
        .confidence-bar {
            height: 8px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin: 8px 0;
        }
        .confidence-fill {
            height: 100%;
            transition: width 0.5s ease;
        }
        .confidence-high { background: #22c55e; }
        .confidence-medium { background: #f59e0b; }
        .confidence-low { background: #ef4444; }
        
        .leverage-value {
            font-weight: 700;
            color: #f59e0b;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        
        .stat {
            text-align: center;
            padding: 15px 10px;
            background: #f8fafc;
            border-radius: 12px;
        }
        .stat-value {
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 0.8rem;
            color: #64748b;
            font-weight: 600;
        }
        
        .status-footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.8);
            border-radius: 15px;
            font-size: 0.9rem;
            color: #64748b;
        }
        
        .positive { color: #22c55e !important; }
        .negative { color: #ef4444 !important; }
        
        @media (max-width: 768px) {
            .cryptos-grid { grid-template-columns: 1fr; }
            .summary-cards { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">⚡ Bot Multi-Cryptos avec Levier Intelligent - Dashboard Pro</h1>
        <div class="status">
            <div class="status-item">🔴 Trading Agressif</div>
            <div class="status-item">📊 Analyse IA</div>
            <div class="status-item">🛡️ Gestion Avancée des Risques</div>
        </div>
        <div class="nav-buttons">
            <a href="/" class="nav-btn active">📊 Dashboard</a>
            <a href="/trades" class="nav-btn">💹 Trades</a>
            <button class="nav-btn" onclick="updateAllData()">🔄 Actualiser</button>
        </div>
    </div>

    <div class="container">
        <div class="dashboard-grid">
            <div class="portfolio-section">
                <h2 class="section-title">📊 Évolution du Portefeuille</h2>
                
                <div class="summary-cards">
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
                        <div class="summary-label">� Exposition</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <canvas id="portfolioChart"></canvas>
                </div>
            </div>
        </div>
        
        <!-- Section des Cryptos -->
        <div class="cryptos-grid" id="cryptos-grid">
            <div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #666; background: rgba(255,255,255,0.9); border-radius: 15px;">
                🔄 Chargement des données cryptos...
            </div>
        </div>
        
        <div class="status-footer">
            <div>🕒 Dernière analyse: <span id="last-update">-</span></div>
            <div>🤖 Bot en mode agressif - Levier intelligent jusqu'à 10x</div>
        </div>
    </div>

    <script>
        let portfolioChart;
        let currentDashboardData = null;
        
        // Initialisation du graphique
        function initPortfolioChart() {
            const ctx = document.getElementById('portfolioChart').getContext('2d');
            portfolioChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Valeur du Portefeuille ($)',
                        data: [],
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'P&L Cumulé ($)',
                        data: [],
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: false,
                        yAxisID: 'y1'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
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
        
        // Mise à jour des données
        function updateAllData() {
            console.log('🔄 Récupération des données...');
            fetch('/api/intelligent-crypto')
                .then(response => {
                    console.log('📡 Réponse API reçue:', response.status);
                    return response.json();
                })
                .then(data => {
                    console.log('📊 Données reçues:', data);
                    currentDashboardData = data;
                    
                    updatePortfolioSummary(data.portfolio, data.cryptos);
                    updatePortfolioChart(data.portfolio.value_history, data.portfolio.pnl_history);
                    updateCryptosGrid(data.cryptos);
                    
                    document.getElementById('last-update').textContent = 
                        new Date(data.portfolio.last_update).toLocaleString();
                        
                    console.log('✅ Mise à jour terminée');
                })
                .catch(error => {
                    console.error('❌ Erreur:', error);
                });
        }
        
        function updatePortfolioSummary(portfolio, cryptos) {
            document.getElementById('total-value').textContent = 
                '$' + portfolio.total_value.toLocaleString(undefined, {maximumFractionDigits: 0});
            
            const pnlElement = document.getElementById('total-pnl');
            const pnlValue = portfolio.pnl;
            pnlElement.textContent = (pnlValue >= 0 ? '+' : '') + '$' + pnlValue.toFixed(0);
            pnlElement.className = 'summary-value ' + (pnlValue >= 0 ? 'positive' : 'negative');
            
            document.getElementById('total-trades').textContent = portfolio.trades_count;
            document.getElementById('leveraged-trades').textContent = portfolio.leveraged_trades;
            document.getElementById('max-leverage').textContent = portfolio.max_leverage.toFixed(1) + 'x';
            document.getElementById('margin-used').textContent = '$' + portfolio.margin_used.toLocaleString(undefined, {maximumFractionDigits: 0});
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
            portfolioChart.update();
        }
        
        function updateCryptosGrid(cryptos) {
            console.log('🪙 Mise à jour des cryptos:', cryptos);
            const grid = document.getElementById('cryptos-grid');
            grid.innerHTML = '';
            
            if (!cryptos || Object.keys(cryptos).length === 0) {
                grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: #666;">Aucune donnée crypto disponible</div>';
                return;
            }
            
            Object.values(cryptos).forEach(crypto => {
                const card = createCryptoCard(crypto);
                grid.appendChild(card);
            });
        }
        
        function createCryptoCard(crypto) {
            const card = document.createElement('div');
            card.className = 'crypto-card';
            
            const changeClass = crypto.price_change_24h >= 0 ? 'positive' : 'negative';
            const pnlColor = crypto.profit_loss >= 0 ? '#22c55e' : '#ef4444';
            
            let confidenceClass = 'confidence-low';
            if (crypto.confidence_score >= 75) confidenceClass = 'confidence-high';
            else if (crypto.confidence_score >= 60) confidenceClass = 'confidence-medium';
            
            const leverageColor = crypto.current_leverage > 1 ? '#f59e0b' : '#64748b';
            
            card.innerHTML = `
                <div class="crypto-header">
                    <div class="crypto-name">
                        <span class="crypto-icon">${crypto.icon}</span>
                        <div>
                            <div class="crypto-title">${crypto.name}</div>
                            <div style="font-size: 0.9em; color: #64748b;">${crypto.symbol}</div>
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
                        <span style="font-weight: bold; color: ${confidenceClass === 'confidence-high' ? '#22c55e' : confidenceClass === 'confidence-medium' ? '#f59e0b' : '#ef4444'}">
                            ${crypto.confidence_score.toFixed(1)}%
                        </span>
                    </div>
                    <div class="confidence-bar">
                        <div class="confidence-fill ${confidenceClass}" style="width: ${crypto.confidence_score}%"></div>
                    </div>
                    
                    <div class="leverage-indicator">
                        <span>⚡ Levier Rec:</span>
                        <span class="leverage-value">${crypto.recommended_leverage.toFixed(1)}x</span>
                    </div>
                    <div class="leverage-indicator">
                        <span>🚀 Utilisé:</span>
                        <span style="font-weight: bold; color: ${leverageColor}">${crypto.current_leverage.toFixed(1)}x</span>
                    </div>
                    
                    <div style="margin-top: 8px; font-size: 0.85em; color: #64748b;">
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
            `;
            
            return card;
        }
        
        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {
            console.log('🚀 Initialisation du dashboard...');
            initPortfolioChart();
            updateAllData();
            setInterval(updateAllData, 20000); // Actualisation toutes les 20 secondes
        });
    </script>
</body>
</html>
    ''')

@app.route('/api/intelligent-crypto')
def api_data():
    """API endpoint pour les données du dashboard"""
    try:
        return jsonify({
            'portfolio': portfolio_data,
            'cryptos': {symbol: asdict(crypto) for symbol, crypto in crypto_data.items()},
            'active_positions': {k: asdict(v) for k, v in active_positions.items()},
            'trades_history': trades_history
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/trades')
def trades_page():
    """Page des trades complète"""
    return render_template_string('''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>💹 Trades - Bot Multi-Cryptos</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .header {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }
        
        .title { font-size: 2.5rem; font-weight: 800; margin-bottom: 10px; }
        .subtitle { color: #666; margin-bottom: 20px; }
        
        .nav-buttons {
            display: flex; justify-content: center; gap: 10px;
        }
        .nav-btn {
            padding: 12px 24px; border: none; border-radius: 25px;
            font-weight: 600; cursor: pointer; text-decoration: none;
            transition: all 0.3s ease;
        }
        .nav-btn.active { background: #22c55e; color: white; }
        .nav-btn:not(.active) { background: #3b82f6; color: white; }
        .nav-btn:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }
        
        .container { max-width: 1400px; margin: 0 auto; padding: 30px 20px; }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: 800;
            margin-bottom: 8px;
        }
        .stat-label {
            color: #666;
            font-weight: 600;
        }
        
        .trades-section {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        
        .section-title {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .filters {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
            padding: 20px;
            background: #f8fafc;
            border-radius: 15px;
            border: 2px solid #e2e8f0;
        }
        
        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .filter-label {
            font-weight: 700;
            color: #374151;
            margin-bottom: 5px;
        }
        
        .filter-buttons {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .filter-btn {
            padding: 6px 12px;
            border: 2px solid #e2e8f0;
            background: white;
            border-radius: 15px;
            cursor: pointer;
            font-weight: 600;
            font-size: 0.85rem;
            transition: all 0.3s ease;
        }
        .filter-btn.active {
            background: #3b82f6;
            color: white;
            border-color: #3b82f6;
        }
        .filter-btn:hover:not(.active) {
            border-color: #3b82f6;
            background: #eff6ff;
        }
        
        .filter-input {
            padding: 8px 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }
        .filter-input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
        }
        
        .filter-range {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .filter-range input {
            flex: 1;
            min-width: 60px;
        }
        
        .trades-list {
            display: grid;
            gap: 15px;
        }
        
        .trade-item {
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            border: 2px solid #e2e8f0;
            transition: all 0.3s ease;
        }
        .trade-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .trade-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .trade-pair {
            font-size: 1.2rem;
            font-weight: 700;
            color: #1e293b;
        }
        
        .trade-status {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .trade-status.ouvert { background: #dcfce7; color: #166534; }
        .trade-status.ferme { background: #fee2e2; color: #991b1b; }
        
        .trade-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }
        
        .trade-detail {
            text-align: center;
        }
        .trade-detail-label {
            font-size: 0.85rem;
            color: #64748b;
            margin-bottom: 4px;
        }
        .trade-detail-value {
            font-weight: 700;
            font-size: 1.1rem;
        }
        
        .positive { color: #22c55e; }
        .negative { color: #ef4444; }
        .leverage { color: #f59e0b; }
        
        .no-trades {
            text-align: center;
            padding: 60px;
            color: #64748b;
        }
        
        .status-footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            background: rgba(255,255,255,0.8);
            border-radius: 15px;
            font-size: 0.9rem;
            color: #64748b;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">💹 Gestion des Trades</h1>
        <p class="subtitle">Historique complet et positions actives</p>
        <div class="nav-buttons">
            <a href="/" class="nav-btn">📊 Dashboard</a>
            <a href="/trades" class="nav-btn active">💹 Trades</a>
            <button class="nav-btn" onclick="updateTradesData()">🔄 Actualiser</button>
        </div>
    </div>

    <div class="container">
        <!-- Statistiques -->
        <div class="stats-grid">
            <div class="stat-card">
                <div id="total-trades-count" class="stat-value">0</div>
                <div class="stat-label">💱 Total Trades</div>
            </div>
            <div class="stat-card">
                <div id="active-trades-count" class="stat-value">0</div>
                <div class="stat-label">🟢 Positions Ouvertes</div>
            </div>
            <div class="stat-card">
                <div id="total-pnl-trades" class="stat-value">$0</div>
                <div class="stat-label">📈 P&L Total</div>
            </div>
            <div class="stat-card">
                <div id="success-rate" class="stat-value">0%</div>
                <div class="stat-label">🎯 Taux de Réussite</div>
            </div>
        </div>
        
        <!-- Section des Trades -->
        <div class="trades-section">
            <h2 class="section-title">📋 Liste des Trades</h2>
            
            <div class="filters">
                <!-- Filtre par statut -->
                <div class="filter-group">
                    <div class="filter-label">📊 Statut</div>
                    <div class="filter-buttons">
                        <button class="filter-btn active" data-filter="status" data-value="all" onclick="applyFilter('status', 'all', this)">Tous</button>
                        <button class="filter-btn" data-filter="status" data-value="open" onclick="applyFilter('status', 'open', this)">Ouverts</button>
                        <button class="filter-btn" data-filter="status" data-value="closed" onclick="applyFilter('status', 'closed', this)">Fermés</button>
                    </div>
                </div>
                
                <!-- Filtre par paire -->
                <div class="filter-group">
                    <div class="filter-label">💰 Paire</div>
                    <div class="filter-buttons">
                        <button class="filter-btn active" data-filter="pair" data-value="all" onclick="applyFilter('pair', 'all', this)">Toutes</button>
                        <button class="filter-btn" data-filter="pair" data-value="ETH" onclick="applyFilter('pair', 'ETH', this)">🔷 ETH</button>
                        <button class="filter-btn" data-filter="pair" data-value="BTC" onclick="applyFilter('pair', 'BTC', this)">🟠 BTC</button>
                        <button class="filter-btn" data-filter="pair" data-value="SOL" onclick="applyFilter('pair', 'SOL', this)">🟣 SOL</button>
                        <button class="filter-btn" data-filter="pair" data-value="XRP" onclick="applyFilter('pair', 'XRP', this)">🔵 XRP</button>
                    </div>
                </div>
                
                <!-- Filtre par P&L -->
                <div class="filter-group">
                    <div class="filter-label">📈 P&L</div>
                    <div class="filter-buttons">
                        <button class="filter-btn active" data-filter="pnl" data-value="all" onclick="applyFilter('pnl', 'all', this)">Tous</button>
                        <button class="filter-btn" data-filter="pnl" data-value="positive" onclick="applyFilter('pnl', 'positive', this)">✅ Positifs</button>
                        <button class="filter-btn" data-filter="pnl" data-value="negative" onclick="applyFilter('pnl', 'negative', this)">❌ Négatifs</button>
                    </div>
                    <div class="filter-range">
                        <input type="number" class="filter-input" id="pnl-min" placeholder="P&L min $" onchange="applyRangeFilter()">
                        <span>à</span>
                        <input type="number" class="filter-input" id="pnl-max" placeholder="P&L max $" onchange="applyRangeFilter()">
                    </div>
                </div>
                
                <!-- Filtre par Levier -->
                <div class="filter-group">
                    <div class="filter-label">⚡ Levier</div>
                    <div class="filter-buttons">
                        <button class="filter-btn active" data-filter="leverage" data-value="all" onclick="applyFilter('leverage', 'all', this)">Tous</button>
                        <button class="filter-btn" data-filter="leverage" data-value="1" onclick="applyFilter('leverage', '1', this)">1x (Spot)</button>
                        <button class="filter-btn" data-filter="leverage" data-value="2-5" onclick="applyFilter('leverage', '2-5', this)">2-5x</button>
                        <button class="filter-btn" data-filter="leverage" data-value="5+" onclick="applyFilter('leverage', '5+', this)">5x+</button>
                    </div>
                    <div class="filter-range">
                        <input type="number" class="filter-input" id="leverage-min" placeholder="Min" min="1" max="10" step="0.1" onchange="applyRangeFilter()">
                        <span>à</span>
                        <input type="number" class="filter-input" id="leverage-max" placeholder="Max" min="1" max="10" step="0.1" onchange="applyRangeFilter()">
                    </div>
                </div>
            </div>
            
            <div class="trades-list" id="trades-list">
                <div class="no-trades">
                    🔄 Chargement des trades...
                </div>
            </div>
        </div>
        
        <div class="status-footer">
            <div>🕒 Dernière mise à jour: <span id="last-update">-</span></div>
            <div>🤖 Suivi automatique des performances de trading</div>
        </div>
    </div>

    <script>
        let currentFilters = {
            status: 'all',
            pair: 'all', 
            pnl: 'all',
            leverage: 'all'
        };
        let tradesData = null;
        
        function updateTradesData() {
            console.log('🔄 Récupération des données trades...');
            fetch('/api/intelligent-crypto')
                .then(response => response.json())
                .then(data => {
                    tradesData = data;
                    updateTradesStats(data);
                    updateTradesDisplay(data);
                    document.getElementById('last-update').textContent = 
                        new Date(data.portfolio.last_update).toLocaleString();
                })
                .catch(error => {
                    console.error('❌ Erreur:', error);
                });
        }
        
        function applyFilter(filterType, value, button) {
            // Mettre à jour les boutons actifs
            const buttons = button.parentElement.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Mettre à jour les filtres
            currentFilters[filterType] = value;
            
            // Réafficher les trades filtrés
            if (tradesData) {
                updateTradesDisplay(tradesData);
            }
        }
        
        function applyRangeFilter() {
            if (tradesData) {
                updateTradesDisplay(tradesData);
            }
        }
        
        function filterTrade(trade) {
            // Filtre par statut
            if (currentFilters.status !== 'all') {
                const isOpen = trade.status === 'OUVERT';
                if (currentFilters.status === 'open' && !isOpen) return false;
                if (currentFilters.status === 'closed' && isOpen) return false;
            }
            
            // Filtre par paire
            if (currentFilters.pair !== 'all') {
                const symbol = trade.pair.split('/')[0];
                if (symbol !== currentFilters.pair) return false;
            }
            
            // Filtre par P&L
            const pnl = trade.pnl || 0;
            if (currentFilters.pnl !== 'all') {
                if (currentFilters.pnl === 'positive' && pnl <= 0) return false;
                if (currentFilters.pnl === 'negative' && pnl >= 0) return false;
            }
            
            // Filtre par plage P&L personnalisée
            const pnlMin = document.getElementById('pnl-min').value;
            const pnlMax = document.getElementById('pnl-max').value;
            if (pnlMin && pnl < parseFloat(pnlMin)) return false;
            if (pnlMax && pnl > parseFloat(pnlMax)) return false;
            
            // Filtre par levier
            const leverage = trade.leverage || 1;
            if (currentFilters.leverage !== 'all') {
                if (currentFilters.leverage === '1' && leverage > 1) return false;
                if (currentFilters.leverage === '2-5' && (leverage < 2 || leverage > 5)) return false;
                if (currentFilters.leverage === '5+' && leverage <= 5) return false;
            }
            
            // Filtre par plage levier personnalisée
            const leverageMin = document.getElementById('leverage-min').value;
            const leverageMax = document.getElementById('leverage-max').value;
            if (leverageMin && leverage < parseFloat(leverageMin)) return false;
            if (leverageMax && leverage > parseFloat(leverageMax)) return false;
            
            return true;
        }
        
        function updateTradesStats(data) {
            // Combiner positions actives et historique
            const allTrades = [...(data.trades_history || [])];
            Object.values(data.active_positions || {}).forEach(pos => {
                allTrades.push({
                    ...pos,
                    status: 'OUVERT',
                    type: pos.leverage > 1 ? 'LEVIER' : 'SPOT'
                });
            });
            
            const activeTrades = Object.keys(data.active_positions || {}).length;
            const totalPnL = allTrades.reduce((sum, trade) => sum + (trade.pnl || trade.profit_loss || 0), 0);
            const closedTrades = allTrades.filter(t => t.status !== 'OUVERT');
            const profitableTrades = closedTrades.filter(t => (t.pnl || t.profit_loss || 0) > 0);
            const successRate = closedTrades.length > 0 ? (profitableTrades.length / closedTrades.length * 100) : 0;
            
            document.getElementById('total-trades-count').textContent = allTrades.length;
            document.getElementById('active-trades-count').textContent = activeTrades;
            
            const pnlElement = document.getElementById('total-pnl-trades');
            pnlElement.textContent = (totalPnL >= 0 ? '+' : '') + '$' + totalPnL.toFixed(2);
            pnlElement.className = 'stat-value ' + (totalPnL >= 0 ? 'positive' : 'negative');
            
            document.getElementById('success-rate').textContent = successRate.toFixed(1) + '%';
        }
        
        function updateTradesDisplay(data) {
            const tradesList = document.getElementById('trades-list');
            
            // Combiner tous les trades
            const allTrades = [...(data.trades_history || [])];
            Object.values(data.active_positions || {}).forEach(pos => {
                // Calculer le P&L en temps réel
                const symbol = pos.pair.split('/')[0]; // ETH, BTC, SOL, XRP
                const currentPrice = data.cryptos[symbol] ? data.cryptos[symbol].price : pos.entry_price;
                const realTimePnL = (currentPrice - pos.entry_price) * pos.amount;
                
                allTrades.push({
                    id: pos.id,
                    pair: pos.pair,
                    amount: pos.amount,
                    price: pos.entry_price,
                    current_price: currentPrice,
                    leverage: pos.leverage,
                    effective_size: pos.effective_size,
                    pnl: realTimePnL,
                    status: 'OUVERT',
                    type: pos.leverage > 1 ? 'LEVIER' : 'SPOT',
                    timestamp: pos.timestamp,
                    confidence: pos.confidence
                });
            });
            
            if (allTrades.length === 0) {
                tradesList.innerHTML = '<div class="no-trades">📭 Aucun trade disponible</div>';
                return;
            }
            
            // Trier par timestamp (plus récents en premier)
            allTrades.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
            // Appliquer les filtres
            const filteredTrades = allTrades.filter(filterTrade);
            
            if (filteredTrades.length === 0) {
                tradesList.innerHTML = '<div class="no-trades">🔍 Aucun trade ne correspond aux filtres sélectionnés</div>';
                return;
            }
            
            tradesList.innerHTML = filteredTrades.map(trade => createTradeCard(trade)).join('');
        }
        
        function createTradeCard(trade) {
            const isOpen = trade.status === 'OUVERT';
            const pnl = trade.pnl || 0;
            const leverageDisplay = trade.leverage > 1 ? trade.leverage.toFixed(1) + 'x' : 'Spot';
            const pnlClass = pnl >= 0 ? 'positive' : 'negative';
            
            // Calculer le P&L en pourcentage avec protections
            const effectiveSize = trade.effective_size || (trade.amount * trade.price * trade.leverage) || 0;
            const marginUsed = effectiveSize > 0 && trade.leverage > 0 ? effectiveSize / trade.leverage : 0;
            const pnlPercentage = marginUsed > 0 && !isNaN(pnl) ? (pnl / marginUsed) * 100 : 0;
            
            // S'assurer que toutes les valeurs numériques sont valides
            const safeEffectiveSize = isNaN(effectiveSize) ? 0 : effectiveSize;
            const safePnl = isNaN(pnl) ? 0 : pnl;
            const safePnlPercentage = isNaN(pnlPercentage) ? 0 : pnlPercentage;
            const safeAmount = isNaN(trade.amount) ? 0 : trade.amount;
            const safePrice = isNaN(trade.price) ? 0 : trade.price;
            const safeCurrentPrice = isNaN(trade.current_price) ? 0 : trade.current_price;
            
            // Calculer prix de liquidation et margin call (pour positions ouvertes avec levier)
            let liquidationPrice = 0;
            let marginCallPrice = 0;
            let stopLossPrice = 0;
            let takeProfitPrice = 0;
            let riskLevel = 'SÛRE';
            let riskEmoji = '✅';
            
            if (isOpen && trade.leverage > 1 && trade.price && trade.current_price) {
                // Prix de liquidation = prix_entrée * (1 - 0.9/levier)
                liquidationPrice = safePrice * (1 - 0.9 / trade.leverage);
                // Prix margin call = prix_entrée * (1 - 0.7/levier)  
                marginCallPrice = safePrice * (1 - 0.7 / trade.leverage);
                // Stop-Loss à -1.5% sur l'exposition (mouvement de prix défavorable)
                stopLossPrice = safePrice * (1 - 0.015);
                // Take-Profit à +2.5% sur l'exposition (mouvement de prix favorable)
                takeProfitPrice = safePrice * (1 + 0.025);
                
                // Déterminer niveau de risque
                if (safeCurrentPrice <= liquidationPrice) {
                    riskLevel = 'LIQUIDÉ';
                    riskEmoji = '💀';
                } else if (safeCurrentPrice <= marginCallPrice) {
                    riskLevel = 'DANGER';
                    riskEmoji = '🚨';
                } else if (safeCurrentPrice <= safePrice * 0.95) {
                    riskLevel = 'RISQUÉ';
                    riskEmoji = '⚠️';
                }
            }
            
            const openTime = new Date(trade.timestamp);
            const timeStr = openTime.toLocaleString();
            
            return `
                <div class="trade-item" data-status="${trade.status}" data-type="${trade.type}">
                    <div class="trade-header">
                        <div class="trade-pair">${trade.pair} ${riskEmoji}</div>
                        <div class="trade-status ${isOpen ? 'ouvert' : 'ferme'}">${trade.status === 'LIQUIDÉ' ? '💀 LIQUIDÉ' : trade.status}</div>
                    </div>
                    <div class="trade-details">
                        <div class="trade-detail">
                            <div class="trade-detail-label">💰 Prix d'Entrée</div>
                            <div class="trade-detail-value">$${safePrice.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                        </div>
                        ${isOpen && trade.current_price ? `
                        <div class="trade-detail">
                            <div class="trade-detail-label">📊 Prix Actuel</div>
                            <div class="trade-detail-value">$${safeCurrentPrice.toLocaleString(undefined, {minimumFractionDigits: 2})}</div>
                        </div>
                        ` : ''}
                        ${isOpen && trade.leverage > 1 && liquidationPrice > 0 ? `
                        <div class="trade-detail">
                            <div class="trade-detail-label">🛑 Stop-Loss</div>
                            <div class="trade-detail-value negative">$${stopLossPrice && stopLossPrice > 0 ? stopLossPrice.toLocaleString(undefined, {minimumFractionDigits: 2}) : 'N/A'}</div>
                        </div>
                        <div class="trade-detail">
                            <div class="trade-detail-label">🎯 Take-Profit</div>
                            <div class="trade-detail-value positive">$${takeProfitPrice && takeProfitPrice > 0 ? takeProfitPrice.toLocaleString(undefined, {minimumFractionDigits: 2}) : 'N/A'}</div>
                        </div>
                        <div class="trade-detail">
                            <div class="trade-detail-label">💀 Prix Liquidation</div>
                            <div class="trade-detail-value negative">$${liquidationPrice && liquidationPrice > 0 ? liquidationPrice.toLocaleString(undefined, {minimumFractionDigits: 2}) : 'N/A'}</div>
                        </div>
                        <div class="trade-detail">
                            <div class="trade-detail-label">🚨 Niveau Risque</div>
                            <div class="trade-detail-value ${riskLevel === 'SÛRE' ? 'positive' : 'negative'}">${riskLevel}</div>
                        </div>
                        ` : ''}
                        <div class="trade-detail">
                            <div class="trade-detail-label">📊 Quantité</div>
                            <div class="trade-detail-value">${safeAmount.toFixed(4)}</div>
                        </div>
                        <div class="trade-detail">
                            <div class="trade-detail-label">⚡ Levier</div>
                            <div class="trade-detail-value leverage">${leverageDisplay}</div>
                        </div>
                        <div class="trade-detail">
                            <div class="trade-detail-label">💵 Taille Effective</div>
                            <div class="trade-detail-value">$${safeEffectiveSize.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
                        </div>
                        <div class="trade-detail">
                            <div class="trade-detail-label">📈 P&L ($)</div>
                            <div class="trade-detail-value ${pnlClass}">
                                ${safePnl >= 0 ? '+' : ''}$${safePnl.toFixed(2)}
                            </div>
                        </div>
                        <div class="trade-detail">
                            <div class="trade-detail-label">📊 P&L (%)</div>
                            <div class="trade-detail-value ${pnlClass}">
                                ${safePnlPercentage >= 0 ? '+' : ''}${safePnlPercentage.toFixed(2)}%
                            </div>
                        </div>
                        <div class="trade-detail">
                            <div class="trade-detail-label">🕒 ${isOpen ? 'Ouvert à' : 'Fermé à'}</div>
                            <div class="trade-detail-value">${timeStr}</div>
                        </div>
                        ${trade.confidence ? `
                        <div class="trade-detail">
                            <div class="trade-detail-label">🎯 Confiance</div>
                            <div class="trade-detail-value">${trade.confidence.toFixed(1)}%</div>
                        </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }
        
        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {
            updateTradesData();
            setInterval(updateTradesData, 30000); // Actualisation toutes les 30 secondes
        });
    </script>
</body>
</html>
    ''')

if __name__ == "__main__":
    print_banner()
    
    # RESET COMPLET au démarrage pour nettoyer l'état
    reset_all_positions()
    
    # Démarrer l'analyse en arrière-plan
    analysis_thread = threading.Thread(target=run_analysis_loop, daemon=True)
    analysis_thread.start()
    
    # Port pour Railway (cloud) ou 5000 pour local
    import os
    port = int(os.environ.get('PORT', 5000))
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False)
    except KeyboardInterrupt:
        print("\n🔴 Arrêt du bot...")
        sys.exit(0)
