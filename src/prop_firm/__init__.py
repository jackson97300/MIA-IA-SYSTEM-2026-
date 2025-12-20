"""
Module Prop Firm pour MIA IA
Trading automatisé avec gestion des risques prop firm
"""

from .prop_firm_manager import PropFirmManager

from .config.prop_firm_rules import (
    PROP_FIRM_RULES,
    DrawdownType,
    PropFirmType,
    get_prop_firm_config,
    get_account_config,
)

from .config.contract_specs import (
    CONTRACT_SPECS,
    ContractSpec,
    get_contract_spec,
    calculate_pnl_from_ticks,
)

from .config.risk_parameters import (
    RiskParameters,
    EVALUATION_RISK_PARAMS,
    FUNDED_RISK_PARAMS,
    get_risk_params,
)

from .core.position_sizer import PropFirmPositionSizer, PositionSize
from .core.drawdown_tracker import DrawdownTracker, DrawdownState, DrawdownStatus

from .stats.trade_stats import Trade, TradeStats, TradeDirection, TradeResult
from .stats.daily_stats import DailyStats
from .stats.evaluation_tracker import EvaluationTracker, EvaluationStatus

from .alerts.risk_alerts import RiskAlertManager, Alert, AlertLevel, AlertType
from .dashboard.discord_dashboard import DiscordDashboard

__version__ = "1.0.0"
__author__ = "MIA IA System"

__all__ = [
    # Manager principal
    "PropFirmManager",

    # Config
    "PROP_FIRM_RULES",
    "CONTRACT_SPECS",
    "RiskParameters",
    "DrawdownType",
    "PropFirmType",

    # Core
    "PropFirmPositionSizer",
    "PositionSize",
    "DrawdownTracker",
    "DrawdownState",
    "DrawdownStatus",

    # Stats
    "Trade",
    "TradeStats",
    "TradeDirection",
    "TradeResult",
    "DailyStats",
    "EvaluationTracker",
    "EvaluationStatus",

    # Alerts
    "RiskAlertManager",
    "Alert",
    "AlertLevel",
    "AlertType",

    # Dashboard
    "DiscordDashboard",
]

