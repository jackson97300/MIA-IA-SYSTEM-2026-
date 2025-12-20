"""
Configuration des règles par Prop Firm
Chaque prop firm a ses propres règles de drawdown, profit target, etc.
"""
from typing import Dict, Any
from enum import Enum


class DrawdownType(Enum):
    """Types de calcul du drawdown"""
    TRAILING = "TRAILING"      # Se met à jour à chaque nouveau high (intraday)
    EOD = "EOD"                # Se met à jour seulement en fin de journée
    STATIC = "STATIC"          # Fixe depuis le starting balance


class PropFirmType(Enum):
    """Prop firms supportées"""
    APEX = "APEX"
    TOPSTEP = "TOPSTEP"
    PHIDIAS = "PHIDIAS"
    MYFUNDEDFUTURES = "MYFUNDEDFUTURES"
    TRADEIFY = "TRADEIFY"


# ═══════════════════════════════════════════════════════════════════════════════
# RÈGLES PAR PROP FIRM
# ═══════════════════════════════════════════════════════════════════════════════

PROP_FIRM_RULES: Dict[str, Dict[str, Any]] = {

    # ─────────────────────────────────────────────────────────────────────────────
    # APEX TRADER FUNDING
    # ─────────────────────────────────────────────────────────────────────────────
    "APEX": {
        "name": "Apex Trader Funding",
        "accounts": {
            "25K": {
                "starting_balance": 25000,
                "profit_target": 1500,
                "trailing_dd": 1500,
                "daily_loss_limit": None,  # Pas de daily loss limit
                "max_contracts": 4,
                "max_micros": 40,
                "evaluation_fee": 147,
                "reset_fee": 80,
            },
            "50K": {
                "starting_balance": 50000,
                "profit_target": 3000,
                "trailing_dd": 2500,
                "daily_loss_limit": None,
                "max_contracts": 10,
                "max_micros": 100,
                "evaluation_fee": 167,
                "reset_fee": 80,
            },
            "100K": {
                "starting_balance": 100000,
                "profit_target": 6000,
                "trailing_dd": 3000,
                "daily_loss_limit": None,
                "max_contracts": 14,
                "max_micros": 140,
                "evaluation_fee": 207,
                "reset_fee": 80,
            },
            "150K": {
                "starting_balance": 150000,
                "profit_target": 9000,
                "trailing_dd": 5000,
                "daily_loss_limit": None,
                "max_contracts": 17,
                "max_micros": 170,
                "evaluation_fee": 297,
                "reset_fee": 80,
            },
            "250K": {
                "starting_balance": 250000,
                "profit_target": 15000,
                "trailing_dd": 6500,
                "daily_loss_limit": None,
                "max_contracts": 27,
                "max_micros": 270,
                "evaluation_fee": 517,
                "reset_fee": 80,
            },
            "300K": {
                "starting_balance": 300000,
                "profit_target": 20000,
                "trailing_dd": 7500,
                "daily_loss_limit": None,
                "max_contracts": 35,
                "max_micros": 350,
                "evaluation_fee": 657,
                "reset_fee": 80,
            },
        },
        "drawdown_type": DrawdownType.TRAILING,
        "drawdown_calculation": "INTRADAY",  # Calculé en temps réel
        "min_trading_days": 7,
        "max_trading_days": None,  # Pas de limite
        "consistency_rule": None,  # Pas de règle de consistance
        "news_trading": True,
        "weekend_holding": True,
        "holiday_trading": True,
        "profit_split_first": 100,  # 100% des premiers $25K
        "profit_split_after": 90,   # 90% ensuite
        "payout_frequency": "TWICE_MONTHLY",
        "min_payout": 500,
        "scaling_plan": False,
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # TOPSTEP
    # ─────────────────────────────────────────────────────────────────────────────
    "TOPSTEP": {
        "name": "Topstep",
        "accounts": {
            "50K": {
                "starting_balance": 50000,
                "profit_target": 3000,
                "trailing_dd": 2000,  # Max Loss Limit
                "daily_loss_limit": 1000,  # Topstep a un daily loss
                "max_contracts": 5,
                "max_micros": 50,
                "evaluation_fee": 49,
                "activation_fee": 149,
            },
            "100K": {
                "starting_balance": 100000,
                "profit_target": 6000,
                "trailing_dd": 3000,
                "daily_loss_limit": 2000,
                "max_contracts": 10,
                "max_micros": 100,
                "evaluation_fee": 99,
                "activation_fee": 149,
            },
            "150K": {
                "starting_balance": 150000,
                "profit_target": 9000,
                "trailing_dd": 4500,
                "daily_loss_limit": 3000,
                "max_contracts": 15,
                "max_micros": 150,
                "evaluation_fee": 149,
                "activation_fee": 149,
            },
        },
        "drawdown_type": DrawdownType.EOD,
        "drawdown_calculation": "END_OF_DAY",  # Calculé à 17h CT
        "min_trading_days": 0,  # Pas de minimum
        "max_trading_days": None,
        "consistency_rule": 0.50,  # 50% rule (aucun jour > 50% du profit total)
        "news_trading": True,
        "weekend_holding": False,  # Doit fermer avant weekend
        "holiday_trading": False,
        "profit_split_first": 100,  # 100% des premiers $10K
        "profit_split_after": 90,
        "payout_frequency": "DAILY",
        "min_payout": 0,
        "scaling_plan": True,  # Scaling progressif des contrats
    },

    # ─────────────────────────────────────────────────────────────────────────────
    # PHIDIAS
    # ─────────────────────────────────────────────────────────────────────────────
    "PHIDIAS": {
        "name": "Phidias Propfirm",
        "accounts": {
            "50K": {
                "starting_balance": 50000,
                "profit_target": 3000,
                "trailing_dd": 2500,
                "daily_loss_limit": None,
                "max_contracts": 10,
                "max_micros": 100,
                "evaluation_fee": 115,
            },
            "100K": {
                "starting_balance": 100000,
                "profit_target": 5000,
                "trailing_dd": 3000,
                "daily_loss_limit": None,
                "max_contracts": 20,
                "max_micros": 200,
                "evaluation_fee": 185,
            },
            "150K": {
                "starting_balance": 150000,
                "profit_target": 9000,
                "trailing_dd": 4500,
                "daily_loss_limit": None,
                "max_contracts": 30,
                "max_micros": 300,
                "evaluation_fee": 265,
            },
        },
        "drawdown_type": DrawdownType.EOD,
        "drawdown_calculation": "END_OF_DAY",  # 22h UTC+2
        "min_trading_days": 3,
        "max_trading_days": None,
        "consistency_rule": 0.30,  # 30% rule (aucun jour > 30% du profit total)
        "news_trading": True,
        "weekend_holding": True,  # Compte Swing uniquement
        "holiday_trading": True,
        "profit_split_first": 80,
        "profit_split_after": 80,
        "payout_frequency": "ON_DEMAND",
        "min_payout": 100,
        "scaling_plan": False,
    },
}


def get_prop_firm_config(prop_firm: str) -> Dict[str, Any]:
    """Récupère la configuration d'une prop firm"""
    if prop_firm not in PROP_FIRM_RULES:
        raise ValueError(f"Prop firm '{prop_firm}' non supportée. Options: {list(PROP_FIRM_RULES.keys())}")
    return PROP_FIRM_RULES[prop_firm]


def get_account_config(prop_firm: str, account_size: str) -> Dict[str, Any]:
    """Récupère la configuration d'un compte spécifique"""
    firm_config = get_prop_firm_config(prop_firm)
    if account_size not in firm_config["accounts"]:
        raise ValueError(f"Taille de compte '{account_size}' non disponible pour {prop_firm}. "
                        f"Options: {list(firm_config['accounts'].keys())}")
    return firm_config["accounts"][account_size]


def list_available_accounts(prop_firm: str) -> list:
    """Liste les comptes disponibles pour une prop firm"""
    return list(get_prop_firm_config(prop_firm)["accounts"].keys())

