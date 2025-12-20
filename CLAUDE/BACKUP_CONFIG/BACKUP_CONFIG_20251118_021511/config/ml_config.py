"""
Configuration ML pour MIA_IA_SYSTEM
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from enum import Enum

class ValidationMethod(Enum):
    """Méthodes de validation (copie locale pour éviter import circulaire)"""
    HOLDOUT = "holdout"
    CROSS_VALIDATION = "cross_validation"
    TIME_SERIES_SPLIT = "time_series_split"

@dataclass
class MLConfig:
    """Configuration pour le machine learning"""
    # Model settings
    model_type: str = "linear"
    model_params: Dict[str, Any] = None
    
    # Training settings
    train_test_split: float = 0.8
    validation_split: float = 0.2
    validation_method: str = "holdout"
    n_splits: int = 5
    
    # Training parameters
    max_epochs: int = 100
    batch_size: int = 32
    learning_rate: float = 0.001
    early_stopping_patience: int = 10
    
    # Feature settings
    feature_columns: List[str] = None
    target_column: str = "signal_quality"
    
    # Performance thresholds
    min_accuracy: float = 0.65
    min_profit_factor: float = 1.5
    
    def __post_init__(self):
        if self.model_params is None:
            self.model_params = {}
        if self.feature_columns is None:
            self.feature_columns = [
                'delta_ratio', 'volume_imbalance', 'bid_ask_spread',
                'trade_intensity', 'regime_trend_strength', 'vwap_distance'
            ]

def get_ml_config() -> MLConfig:
    """Retourne la configuration ML"""
    return MLConfig()
