"""
Configuration avancée pour bot avec levier intelligent
"""

import os
import json
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class TradingConfig:
    """Configuration de trading avec support levier"""
    symbols: list = None
    base_amount: float = 1000.0  # USDC per trade
    max_leverage: int = 20
    min_confidence_for_leverage: float = 75.0
    leverage_risk_per_trade: float = 2.0  # % du portfolio pour trades avec levier
    normal_risk_per_trade: float = 1.0    # % du portfolio pour trades normaux
    
    # Stop Loss et Take Profit
    stop_loss_pct: float = 3.0     # % pour trades normaux
    take_profit_pct: float = 2.5   # % pour trades normaux
    leverage_stop_loss_pct: float = 1.5  # % pour trades avec levier (plus serré)
    leverage_take_profit_pct: float = 2.0 # % pour trades avec levier
    
    # Limites de sécurité
    max_positions: int = 4
    max_simultaneous_leveraged: int = 2
    max_daily_trades: int = 50
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["ETH/USDC", "BTC/USDC", "SOL/USDC", "XRP/USDC"]


@dataclass 
class LeverageConfig:
    """Configuration spécifique au levier"""
    # Limites par crypto
    crypto_max_leverage = {
        "ETH/USDC": 20,
        "BTC/USDC": 25, 
        "SOL/USDC": 15,
        "XRP/USDC": 10
    }
    
    # Seuils de confiance minimum pour activer le levier
    min_confidence_thresholds = {
        "ETH/USDC": 75.0,
        "BTC/USDC": 80.0,
        "SOL/USDC": 70.0,
        "XRP/USDC": 65.0
    }
    
    # Facteurs de volatilité (réduction du levier si volatilité élevée)
    max_volatility_for_full_leverage: float = 5.0
    volatility_reduction_factor: float = 0.5
    
    # Gestion du risque
    max_margin_usage_pct: float = 30.0  # Max 30% du capital en marge
    leverage_cooldown_seconds: int = 300 # 5 min entre trades avec levier


@dataclass
class StrategyConfig:
    """Configuration des stratégies d'IA"""
    # Analyse de tendance
    trend_analysis_periods = [5, 10, 20]
    min_trend_strength: float = 60.0
    
    # Analyse de volatilité
    volatility_window: int = 20
    volatility_threshold_high: float = 10.0
    volatility_threshold_low: float = 2.0
    
    # Score de confiance
    base_confidence: float = 50.0
    trend_bonus: float = 15.0
    volatility_bonus: float = 10.0
    momentum_bonus: float = 10.0
    
    # Filtres de qualité
    min_price_history_length: int = 10
    min_confidence_for_any_trade: float = 40.0


@dataclass
class RiskManagementConfig:
    """Gestion avancée des risques"""
    # Limites globales
    max_portfolio_risk_pct: float = 15.0  # Max 15% du portfolio en risque
    max_drawdown_pct: float = 10.0        # Arrêt si perte > 10%
    
    # Limites par crypto
    max_exposure_per_crypto_pct: float = 25.0  # Max 25% sur une crypto
    
    # Limites temporelles
    daily_loss_limit_pct: float = 5.0     # Arrêt si perte > 5% par jour
    weekly_loss_limit_pct: float = 15.0   # Arrêt si perte > 15% par semaine
    
    # Circuit breakers
    volatility_circuit_breaker: float = 15.0  # Arrêt si volatilité > 15%
    correlation_limit: float = 0.8        # Éviter trades corrélés > 80%


@dataclass
class ExchangeConfig:
    """Configuration exchange pour trading avec levier"""
    name: str = "bitget"
    api_key: str = ""
    secret: str = ""
    passphrase: str = ""
    sandbox: bool = True
    
    # Type de marché
    default_type: str = "future"  # "spot" ou "future"
    margin_mode: str = "isolated"  # "isolated" ou "cross"
    
    # Paramètres de trading
    order_type: str = "market"     # "market" ou "limit"
    time_in_force: str = "GTC"     # Good Till Cancel
    
    # Limites API
    rate_limit: int = 1200  # Requêtes par minute
    retry_attempts: int = 3
    timeout: int = 30


class IntelligentLeverageConfig:
    """Configuration complète du bot avec levier intelligent"""
    
    def __init__(self, config_file: str = "config/intelligent_leverage_config.json"):
        self.config_file = config_file
        self.trading = TradingConfig()
        self.leverage = LeverageConfig()
        self.strategy = StrategyConfig()
        self.risk = RiskManagementConfig()
        self.exchange = ExchangeConfig()
        
        # Charger la config si elle existe
        self.load_config()
    
    def load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config_data = json.load(f)
                
                # Mettre à jour les configs
                for key, value in config_data.get('trading', {}).items():
                    if hasattr(self.trading, key):
                        setattr(self.trading, key, value)
                
                for key, value in config_data.get('strategy', {}).items():
                    if hasattr(self.strategy, key):
                        setattr(self.strategy, key, value)
                        
                for key, value in config_data.get('risk', {}).items():
                    if hasattr(self.risk, key):
                        setattr(self.risk, key, value)
                        
                for key, value in config_data.get('exchange', {}).items():
                    if hasattr(self.exchange, key):
                        setattr(self.exchange, key, value)
                
                print("✅ Configuration chargée depuis", self.config_file)
                
            except Exception as e:
                print(f"⚠️  Erreur chargement config: {e}")
                print("📝 Utilisation configuration par défaut")
    
    def save_config(self):
        """Sauvegarde la configuration dans le fichier JSON"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            config_data = {
                'trading': {
                    'symbols': self.trading.symbols,
                    'base_amount': self.trading.base_amount,
                    'max_leverage': self.trading.max_leverage,
                    'min_confidence_for_leverage': self.trading.min_confidence_for_leverage,
                    'leverage_risk_per_trade': self.trading.leverage_risk_per_trade,
                    'normal_risk_per_trade': self.trading.normal_risk_per_trade,
                    'stop_loss_pct': self.trading.stop_loss_pct,
                    'take_profit_pct': self.trading.take_profit_pct,
                    'leverage_stop_loss_pct': self.trading.leverage_stop_loss_pct,
                    'leverage_take_profit_pct': self.trading.leverage_take_profit_pct,
                    'max_positions': self.trading.max_positions,
                    'max_simultaneous_leveraged': self.trading.max_simultaneous_leveraged,
                    'max_daily_trades': self.trading.max_daily_trades
                },
                'leverage': {
                    'crypto_max_leverage': self.leverage.crypto_max_leverage,
                    'min_confidence_thresholds': self.leverage.min_confidence_thresholds,
                    'max_volatility_for_full_leverage': self.leverage.max_volatility_for_full_leverage,
                    'volatility_reduction_factor': self.leverage.volatility_reduction_factor,
                    'max_margin_usage_pct': self.leverage.max_margin_usage_pct,
                    'leverage_cooldown_seconds': self.leverage.leverage_cooldown_seconds
                },
                'strategy': {
                    'trend_analysis_periods': self.strategy.trend_analysis_periods,
                    'min_trend_strength': self.strategy.min_trend_strength,
                    'volatility_window': self.strategy.volatility_window,
                    'volatility_threshold_high': self.strategy.volatility_threshold_high,
                    'volatility_threshold_low': self.strategy.volatility_threshold_low,
                    'base_confidence': self.strategy.base_confidence,
                    'trend_bonus': self.strategy.trend_bonus,
                    'volatility_bonus': self.strategy.volatility_bonus,
                    'momentum_bonus': self.strategy.momentum_bonus,
                    'min_price_history_length': self.strategy.min_price_history_length,
                    'min_confidence_for_any_trade': self.strategy.min_confidence_for_any_trade
                },
                'risk': {
                    'max_portfolio_risk_pct': self.risk.max_portfolio_risk_pct,
                    'max_drawdown_pct': self.risk.max_drawdown_pct,
                    'max_exposure_per_crypto_pct': self.risk.max_exposure_per_crypto_pct,
                    'daily_loss_limit_pct': self.risk.daily_loss_limit_pct,
                    'weekly_loss_limit_pct': self.risk.weekly_loss_limit_pct,
                    'volatility_circuit_breaker': self.risk.volatility_circuit_breaker,
                    'correlation_limit': self.risk.correlation_limit
                },
                'exchange': {
                    'name': self.exchange.name,
                    'sandbox': self.exchange.sandbox,
                    'default_type': self.exchange.default_type,
                    'margin_mode': self.exchange.margin_mode,
                    'order_type': self.exchange.order_type,
                    'time_in_force': self.exchange.time_in_force,
                    'rate_limit': self.exchange.rate_limit,
                    'retry_attempts': self.exchange.retry_attempts,
                    'timeout': self.exchange.timeout
                }
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            print("✅ Configuration sauvegardée dans", self.config_file)
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde config: {e}")
    
    def get_leverage_for_crypto(self, symbol: str) -> int:
        """Obtient le levier maximum pour une crypto"""
        return self.leverage.crypto_max_leverage.get(symbol, 10)
    
    def get_min_confidence_for_crypto(self, symbol: str) -> float:
        """Obtient le seuil de confiance minimum pour une crypto"""
        return self.leverage.min_confidence_thresholds.get(symbol, 70.0)
    
    def is_leverage_allowed(self, symbol: str, confidence: float, volatility: float) -> bool:
        """Détermine si le levier est autorisé pour une crypto"""
        min_confidence = self.get_min_confidence_for_crypto(symbol)
        max_volatility = self.leverage.max_volatility_for_full_leverage
        
        return confidence >= min_confidence and volatility <= (max_volatility * 2)
    
    def calculate_optimal_leverage(self, symbol: str, confidence: float, volatility: float) -> float:
        """Calcule le levier optimal"""
        if not self.is_leverage_allowed(symbol, confidence, volatility):
            return 1.0
        
        max_leverage = self.get_leverage_for_crypto(symbol)
        min_confidence = self.get_min_confidence_for_crypto(symbol)
        
        # Facteur de confiance (0 à 1)
        confidence_factor = (confidence - min_confidence) / (95 - min_confidence)
        
        # Facteur de volatilité (réduction si volatilité élevée)
        volatility_factor = max(0.5, 1.0 - (volatility / 20))
        
        # Levier optimal
        optimal_leverage = 1.0 + (max_leverage - 1.0) * confidence_factor * volatility_factor
        
        # Limites de sécurité
        if volatility > self.leverage.max_volatility_for_full_leverage:
            optimal_leverage = min(optimal_leverage, 3.0)
        
        return max(1.0, min(max_leverage, optimal_leverage))


# Instance globale
intelligent_config = IntelligentLeverageConfig()

# Fonctions utilitaires
def get_trading_config() -> TradingConfig:
    return intelligent_config.trading

def get_leverage_config() -> LeverageConfig:
    return intelligent_config.leverage

def get_strategy_config() -> StrategyConfig:
    return intelligent_config.strategy

def get_risk_config() -> RiskManagementConfig:
    return intelligent_config.risk

def get_exchange_config() -> ExchangeConfig:
    return intelligent_config.exchange

def save_config():
    intelligent_config.save_config()

def load_config():
    intelligent_config.load_config()

if __name__ == "__main__":
    # Test de la configuration
    print("🔧 Configuration Bot Levier Intelligent")
    print(f"📊 Cryptos: {intelligent_config.trading.symbols}")
    print(f"⚡ Levier max BTC: {intelligent_config.get_leverage_for_crypto('BTC/USDC')}x")
    print(f"🎯 Confiance min ETH: {intelligent_config.get_min_confidence_for_crypto('ETH/USDC')}%")
    print(f"💰 Montant de base: ${intelligent_config.trading.base_amount}")
    print(f"🛡️ Mode marge: {intelligent_config.exchange.margin_mode}")
    
    # Sauvegarder la config par défaut
    intelligent_config.save_config()
    print("\n✅ Configuration sauvegardée!")
