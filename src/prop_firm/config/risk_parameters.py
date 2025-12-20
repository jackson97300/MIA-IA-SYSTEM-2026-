"""
Paramètres de risque pour le trading prop firm
RÈGLE D'OR: Même configuration en EVAL et en FUNDED!
"""
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class RiskParameters:
    """Paramètres de risque pour un mode de trading"""

    # Risque par trade
    risk_per_trade_percent: float = 1.0      # % du drawdown disponible
    max_risk_per_trade_dollars: Optional[float] = None  # Override en $

    # Limites journalières
    max_daily_loss_percent: float = 50.0     # % du trailing DD
    max_trades_per_day: int = 10
    max_loss_streak_before_stop: int = 5     # Stop après X pertes consécutives

    # R:R et qualité
    min_rr_ratio: float = 2.0                # Minimum Risk:Reward
    min_confidence: float = 0.0              # Confidence minimum pour trader

    # Contrats
    use_micros: bool = True                  # Utiliser micros par défaut
    max_contracts_per_trade: Optional[int] = None  # Override max contrats

    # Consistency
    consistency_mode: bool = True            # Éviter gros jours (règle 30%)
    max_single_day_profit_percent: float = 30.0  # Max % du target en un jour

    # Protection profits
    protect_profits: bool = True             # Lock profits rapidement
    profit_lock_threshold: float = 0.5       # Lock à 50% du TP

    # Sessions autorisées
    allowed_sessions: List[str] = field(default_factory=lambda: ["LONDON", "US_MORNING", "POWER_HOUR"])


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIONS PAR MODE
# ═══════════════════════════════════════════════════════════════════════════════

# IMPORTANT: Les deux modes ont les MÊMES paramètres!
# "Treat the evaluation as you would your funded account"

EVALUATION_RISK_PARAMS = RiskParameters(
    risk_per_trade_percent=1.0,
    max_daily_loss_percent=50.0,
    max_trades_per_day=10,
    max_loss_streak_before_stop=5,
    min_rr_ratio=2.0,
    use_micros=True,
    consistency_mode=True,
    max_single_day_profit_percent=30.0,
    protect_profits=True,
    profit_lock_threshold=0.5,
)

FUNDED_RISK_PARAMS = RiskParameters(
    risk_per_trade_percent=1.0,       # IDENTIQUE!
    max_daily_loss_percent=50.0,      # IDENTIQUE!
    max_trades_per_day=10,            # IDENTIQUE!
    max_loss_streak_before_stop=5,    # IDENTIQUE!
    min_rr_ratio=2.0,                 # IDENTIQUE!
    use_micros=True,                  # IDENTIQUE!
    consistency_mode=True,            # IDENTIQUE!
    max_single_day_profit_percent=30.0,  # IDENTIQUE!
    protect_profits=True,             # IDENTIQUE!
    profit_lock_threshold=0.5,        # IDENTIQUE!
)

# Configuration agressive (NON RECOMMANDÉE - pour référence seulement)
AGGRESSIVE_RISK_PARAMS = RiskParameters(
    risk_per_trade_percent=2.0,       # ⚠️ Plus risqué
    max_daily_loss_percent=75.0,      # ⚠️ Plus risqué
    max_trades_per_day=15,
    max_loss_streak_before_stop=3,
    min_rr_ratio=1.5,
    use_micros=False,                 # ⚠️ Minis = plus risqué
    consistency_mode=False,
    protect_profits=False,
)

# Configuration conservative (pour débuter)
CONSERVATIVE_RISK_PARAMS = RiskParameters(
    risk_per_trade_percent=0.5,       # Très conservateur
    max_daily_loss_percent=30.0,
    max_trades_per_day=5,
    max_loss_streak_before_stop=3,
    min_rr_ratio=2.5,
    use_micros=True,
    consistency_mode=True,
    max_single_day_profit_percent=20.0,
    protect_profits=True,
    profit_lock_threshold=0.3,
)


def get_risk_params(mode: str) -> RiskParameters:
    """Récupère les paramètres de risque selon le mode"""
    modes = {
        "EVALUATION": EVALUATION_RISK_PARAMS,
        "FUNDED": FUNDED_RISK_PARAMS,
        "AGGRESSIVE": AGGRESSIVE_RISK_PARAMS,
        "CONSERVATIVE": CONSERVATIVE_RISK_PARAMS,
    }
    if mode not in modes:
        raise ValueError(f"Mode '{mode}' non reconnu. Options: {list(modes.keys())}")
    return modes[mode]

