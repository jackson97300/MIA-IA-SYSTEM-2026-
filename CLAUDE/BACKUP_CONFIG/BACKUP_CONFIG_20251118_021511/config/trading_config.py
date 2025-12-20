"""
Configuration trading amelioree - Support complet SignalGenerator
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class TradingConfig:
    """Configuration trading avec support .get() et attributs complets"""
    
    # Symboles
    primary_symbol: str = "ES"
    secondary_symbol: str = "NQ"
    
    # Risk management
    max_position_size: int = 3
    daily_loss_limit: float = 1000.0
    daily_profit_target: float = 500.0
    
    # Features
    min_confidence: float = 0.65
    lookback_periods: int = 20
    feature_lookback: int = 20
    
    # Sessions
    trading_start_hour: int = 9
    trading_end_hour: int = 16
    
    # Signal thresholds
    signal_threshold: float = 0.65
    
    # Cache configuration
    cache_config: Dict[str, Any] = field(default_factory=lambda: {
        'enabled': True,
        'ttl_seconds': 60,
        'max_size': 500
    })
    
    # Elite techniques
    enable_mtf_confluence: bool = True
    enable_smart_money: bool = True
    enable_ml_ensemble: bool = True
    enable_gamma_cycles: bool = True
    
    # ML Ensemble config
    ml_confidence_threshold: float = 0.70
    
    # Performance config
    enable_cache: bool = True
    cache_ttl: int = 60
    max_cache_size: int = 500
    
    def get(self, key: str, default=None):
        """Methode get pour compatibilite dict-like"""
        return getattr(self, key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion en dictionnaire"""
        result = {}
        for field_name in self.__dataclass_fields__:
            result[field_name] = getattr(self, field_name)
        return result
    
    def update(self, updates: Dict[str, Any]):
        """Mise a jour depuis dictionnaire"""
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)

def get_trading_config() -> TradingConfig:
    """Factory function pour TradingConfig"""
    return TradingConfig()

def get_risk_config() -> Dict[str, float]:
    """Configuration risque"""
    config = get_trading_config()
    return {
        'max_position': config.max_position_size,
        'daily_loss': config.daily_loss_limit,
        'daily_target': config.daily_profit_target
    }

def get_feature_config() -> Dict[str, Any]:
    """Configuration des features avancées"""
    config = get_trading_config()
    return {
        'enable_mtf_confluence': config.enable_mtf_confluence,
        'enable_smart_money': config.enable_smart_money,
        'enable_ml_ensemble': config.enable_ml_ensemble,
        'enable_gamma_cycles': config.enable_gamma_cycles,
        'ml_confidence_threshold': config.ml_confidence_threshold,
        'min_confidence': config.min_confidence,
        'lookback_periods': config.lookback_periods,
        'feature_lookback': config.feature_lookback
    }

# Test auto-validation
if __name__ == "__main__":
    config = TradingConfig()
    
    # Test .get()
    symbol = config.get('primary_symbol', 'DEFAULT')
    cache_cfg = config.get('cache_config', {})
    missing = config.get('non_existent_key', 'FALLBACK')
    
    print(f"✅ Config OK: {symbol}")
    print(f"✅ Cache config: {type(cache_cfg)}")
    print(f"✅ Missing key: {missing}")
    print(f"✅ Risk config: {get_risk_config()}")
    print("🎯 TradingConfig ameliore pret!")
