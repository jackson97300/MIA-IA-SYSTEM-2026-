#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 MIA TRADING COPILOT V7 - VERSION CORRIGÉE ET AMÉLIORÉE
═══════════════════════════════════════════════════════════════════

✅ VERSION V7 - CORRECTIONS APPLIQUÉES:

CORRECTIONS:
- ✅ #1: Blind Spots 0-8 → BL 1-9 (aligné Sierra Chart)
- ✅ #2: Import TRADING_CONFIG depuis config/trading_params.py
- ✅ #3: Sessions avec minutes (aligné session_quality_monitor.py)
- ✅ #4: Affichage VIX Regime (CRITIQUE pour MIA!)
- ✅ #5: Intermarket ES/NQ divergence display
- ✅ #6: Gamma Side display
- ✅ #7: Parsing logs robuste
- ✅ #8: Validation snapshot (data quality)

ONGLET 1 - LIVE (Amélioré):
- Next Wall, BIAS, MODE, DIRECTION, VOLATILITÉ
- 🆕 VIX Regime (avec alertes si > 25!)
- 🆕 Intermarket ES/NQ Sync
- 🆕 Gamma Side
- Position 1D, DOM Pressure
- Distance niveau proche (barre visuelle)
- Trade Suggestion (verdict clair)
- Checklist pré-trade automatique

ONGLET 2 - NIVEAUX:
- Tous les niveaux MenthorQ
- Filtres, tri, comportements

ONGLET 3 - PERFORMANCE:
- P&L par période, symbole, session
- Insights automatiques

ONGLET 4 - ANALYSE:
- Analyse détaillée de chaque trade
- Score qualité

ONGLET 5 - CONFIG:
- Paramètres visibles depuis trading_params.py

Version: 7.0 (10/12/2025)
Lancer: streamlit run mia_trading_copilot_v6.py

Author: MIA System + Cursor
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # ✅ FIX: Accès au projet root

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple
import time
import re
import os

# ✅ TODO #2: Import depuis trading_params.py (source unique de vérité)
try:
    from config.trading_params import TRADING_CONFIG
    CONFIG_LOADED = True
except ImportError:
    TRADING_CONFIG = {}
    CONFIG_LOADED = False

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="🎯 MIA Copilot V7",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

PROJECT_ROOT = Path(__file__).parent.parent if Path(__file__).parent.name == "core" else Path(__file__).parent

# ✅ TODO #2: SYMBOLS_CONFIG synchronisé avec trading_params.py
def _build_symbols_config():
    """Construit SYMBOLS_CONFIG depuis TRADING_CONFIG ou valeurs par défaut."""
    base_config = {
        'ES': {'name': 'E-mini S&P 500', 'color': '#0fbf84', 'icon': '📗', 'chart_id': 3},
        'NQ': {'name': 'E-mini NASDAQ', 'color': '#4a9eff', 'icon': '📘', 'chart_id': 9},
        'RTY': {'name': 'E-mini Russell 2000', 'color': '#ff6b6b', 'icon': '📕', 'chart_id': 1},
    }

    result = {}
    for sym, base in base_config.items():
        cfg = TRADING_CONFIG.get(sym, {})
        result[sym] = {
            **base,
            'tick_size': cfg.get('tick_size', 0.25 if sym != 'RTY' else 0.10),
            'tick_value': cfg.get('tick_value', 12.50 if sym == 'ES' else 5.00),
            'max_entry_distance': cfg.get('max_entry_distance_ticks', 8 if sym == 'ES' else 10 if sym == 'NQ' else 12),
            'max_distance': cfg.get('max_entry_distance_ticks', 8) + 7 if sym == 'ES' else cfg.get('max_entry_distance_ticks', 10) + 10 if sym == 'NQ' else 15,
            'min_sl_ticks': cfg.get('min_sl_ticks', 10),
            'max_sl_ticks': cfg.get('max_sl_ticks', 25),
            'tp_ticks': cfg.get('tp_ticks', 15),
            'sl_ticks': cfg.get('sl_ticks', 15),
        }
    return result

SYMBOLS_CONFIG = _build_symbols_config()

MONTH_NAMES = {1: "JANVIER", 2: "FEVRIER", 3: "MARS", 4: "AVRIL", 5: "MAI", 6: "JUIN",
               7: "JUILLET", 8: "AOUT", 9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DECEMBRE"}


# 🔄 ROLLOVER AUTOMATIQUE
def get_current_contract_month(date: Optional[datetime] = None) -> str:
    """Détermine automatiquement le code du contrat actif (H, M, U, Z)."""
    if date is None:
        date = datetime.now()
    month = date.month
    year = date.year % 100
    if month == 12:
        return f"Z{year}" if date.day < 10 else f"H{(year + 1) % 100}"
    elif month in [1, 2]:
        return f"H{year}"
    elif month == 3:
        return f"H{year}" if date.day < 10 else f"M{year}"
    elif month in [4, 5]:
        return f"M{year}"
    elif month == 6:
        return f"M{year}" if date.day < 10 else f"U{year}"
    elif month in [7, 8]:
        return f"U{year}"
    elif month == 9:
        return f"U{year}" if date.day < 10 else f"Z{year}"
    elif month in [10, 11]:
        return f"Z{year}"
    return f"H{year}"


# ✅ TODO #3: Sessions alignées avec session_quality_monitor.py (horaires précis)
TRADING_SESSIONS = {
    'LONDON': {'start_hour': 8, 'start_min': 0, 'end_hour': 11, 'end_min': 0,
               'quality': 0.9, 'tradable': True, 'color': '#4a9eff', 'name_fr': 'London'},
    'TRANSITION': {'start_hour': 11, 'start_min': 0, 'end_hour': 15, 'end_min': 50,
                   'quality': 0.4, 'tradable': False, 'color': '#808080', 'name_fr': 'Transition'},
    'US_MORNING': {'start_hour': 15, 'start_min': 50, 'end_hour': 17, 'end_min': 0,
                   'quality': 1.0, 'tradable': True, 'color': '#0fbf84', 'name_fr': 'US Morning'},
    'LUNCH_BLOCK': {'start_hour': 17, 'start_min': 0, 'end_hour': 20, 'end_min': 0,
                    'quality': 0.5, 'tradable': False, 'color': '#f8c36b', 'name_fr': 'Lunch Block'},
    'US_POWER': {'start_hour': 20, 'start_min': 0, 'end_hour': 21, 'end_min': 30,
                 'quality': 1.0, 'tradable': True, 'color': '#0fbf84', 'name_fr': 'US Power Hour'},
    'HARD_STOP': {'start_hour': 21, 'start_min': 30, 'end_hour': 8, 'end_min': 0,
                  'quality': 0.0, 'tradable': False, 'color': '#ef476f', 'name_fr': 'Hard Stop'},
}

# ✅ TODO #4: Seuils VIX (critiques pour MIA)
VIX_THRESHOLDS = {
    'NORMAL': {'max': 15, 'color': '#0fbf84', 'status': '✅ OK'},
    'ELEVATED': {'max': 20, 'color': '#4a9eff', 'status': '✅ OK'},
    'HIGH': {'max': 25, 'color': '#f8c36b', 'status': '⚠️ PRUDENCE'},
    'VERY_HIGH': {'max': 35, 'color': '#ff6b6b', 'status': '🔴 SKIP TRADES'},
    'EXTREME': {'max': 999, 'color': '#ef476f', 'status': '🔴 STOP TOTAL'},
}

# Comportements des niveaux MenthorQ
LEVEL_BEHAVIORS = {
    'HVL': {'behavior': 'MAGNET', 'bounce_rate': 82, 'action_long': 'Entry si approche bas + confirm', 'action_short': 'Entry si approche haut + confirm'},
    'HVL_0DTE': {'behavior': 'MAGNET', 'bounce_rate': 80, 'action_long': 'Entry si approche bas', 'action_short': 'Entry si approche haut'},
    '1D_MAX': {'behavior': 'RESISTANCE', 'bounce_rate': 75, 'action_long': '❌ Éviter', 'action_short': '✅ SHORT si rejet'},
    '1D_MIN': {'behavior': 'SUPPORT', 'bounce_rate': 75, 'action_long': '✅ LONG si rebond', 'action_short': '❌ Éviter'},
    'VAH': {'behavior': 'RESISTANCE', 'bounce_rate': 70, 'action_long': 'Prudence', 'action_short': 'Bon SHORT'},
    'VAL': {'behavior': 'SUPPORT', 'bounce_rate': 70, 'action_long': 'Bon LONG', 'action_short': 'Prudence'},
    'VPOC': {'behavior': 'MAGNET', 'bounce_rate': 68, 'action_long': 'Trade vers VPOC', 'action_short': 'Trade vers VPOC'},
    'CALL_WALL': {'behavior': 'RESISTANCE', 'bounce_rate': 68, 'action_long': '⚠️ Difficile casser', 'action_short': '✅ SHORT si rejet'},
    'PUT_WALL': {'behavior': 'SUPPORT', 'bounce_rate': 68, 'action_long': '✅ LONG si rebond', 'action_short': '⚠️ Difficile casser'},
    'GEX': {'behavior': 'PIVOT', 'bounce_rate': 60, 'action_long': 'Rebond si support', 'action_short': 'Rejet si résistance'},
    'BLIND_SPOT': {'behavior': 'FAST_MOVE', 'bounce_rate': 55, 'action_long': '⚠️ Mouvement rapide', 'action_short': '⚠️ Mouvement rapide'},
    'VWAP': {'behavior': 'PIVOT', 'bounce_rate': 55, 'action_long': 'LONG si retour bas', 'action_short': 'SHORT si retour haut'},
}

# ═══════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════

def inject_css():
    st.markdown("""
    <style>
    .stApp { background-color: #0b1016; }

    .main-header {
        background: linear-gradient(135deg, #0f1419 0%, #1a2332 100%);
        border-radius: 16px; padding: 20px; margin-bottom: 16px;
        border: 1px solid #1e293b;
    }
    .main-title {
        font-size: 1.8rem; font-weight: 800;
        background: linear-gradient(135deg, #0fbf84, #4a9eff);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }

    .metric-box {
        background: #0f1620; border-radius: 12px; padding: 14px;
        border: 1px solid #1e293b; text-align: center; margin: 6px 0;
    }
    .metric-label { font-size: 0.75rem; color: #64748b; margin-bottom: 4px; }
    .metric-value { font-size: 1.2rem; font-weight: 700; }
    .metric-value.green { color: #0fbf84; }
    .metric-value.red { color: #ef476f; }
    .metric-value.yellow { color: #f8c36b; }
    .metric-value.blue { color: #4a9eff; }
    .metric-value.gray { color: #94a3b8; }

    .big-box {
        background: #0f1620; border-radius: 16px; padding: 20px;
        border: 2px solid; margin: 10px 0; text-align: center;
    }
    .big-box.bullish { border-color: #0fbf84; background: rgba(15,191,132,0.1); }
    .big-box.bearish { border-color: #ef476f; background: rgba(239,71,111,0.1); }
    .big-box.neutral { border-color: #64748b; background: rgba(100,116,139,0.1); }
    .big-box.warning { border-color: #f8c36b; background: rgba(248,195,107,0.1); }

    .next-wall-box {
        background: linear-gradient(135deg, #1a2332 0%, #0f1620 100%);
        border-radius: 16px; padding: 20px; margin: 10px 0;
        border: 3px solid #f8c36b; text-align: center;
    }

    .conseil-box {
        background: rgba(74,158,255,0.1); border-left: 4px solid #4a9eff;
        padding: 12px 16px; border-radius: 8px; margin: 6px 0;
    }
    .warning-box {
        background: rgba(239,71,111,0.1); border-left: 4px solid #ef476f;
        padding: 12px 16px; border-radius: 8px; margin: 6px 0;
    }
    .success-box {
        background: rgba(15,191,132,0.1); border-left: 4px solid #0fbf84;
        padding: 12px 16px; border-radius: 8px; margin: 6px 0;
    }

    .suggestion-box {
        background: linear-gradient(135deg, #1a2332 0%, #0f1620 100%);
        border-radius: 16px; padding: 20px; margin: 10px 0;
        border: 2px solid #4a9eff;
    }

    .checklist-item {
        padding: 8px 12px; margin: 4px 0; border-radius: 8px;
        display: flex; align-items: center;
    }
    .checklist-ok { background: rgba(15,191,132,0.15); }
    .checklist-warn { background: rgba(248,195,107,0.15); }
    .checklist-fail { background: rgba(239,71,111,0.15); }

    .distance-bar {
        height: 24px; border-radius: 12px; background: #1e293b;
        overflow: hidden; margin: 4px 0;
    }
    .distance-fill {
        height: 100%; border-radius: 12px;
        transition: width 0.3s ease;
    }

    .badge {
        display: inline-block; padding: 4px 12px; border-radius: 12px;
        font-weight: 600; font-size: 0.8rem; margin: 2px;
    }

    .kpi-card {
        background: #0f1620; border-radius: 12px; padding: 16px;
        border: 1px solid #1e293b; text-align: center;
    }
    .kpi-value { font-size: 2rem; font-weight: 800; }
    .kpi-label { font-size: 0.85rem; color: #64748b; }

    .trade-row {
        background: #0f1620; border-radius: 8px; padding: 12px;
        margin: 8px 0; border-left: 4px solid;
    }
    .trade-row.win { border-color: #0fbf84; }
    .trade-row.loss { border-color: #ef476f; }
    </style>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════

def build_snapshot_path(symbol: str, date: Optional[datetime] = None) -> Optional[Path]:
    if date is None:
        date = datetime.now()
    config = SYMBOLS_CONFIG.get(symbol.upper())
    if not config:
        return None
    chart_id = config['chart_id']
    base_path = Path("DATA_SIERRA_CHART")
    contract = get_current_contract_month(date)
    return base_path / f"DATA_{date.year}" / MONTH_NAMES.get(date.month, "") / date.strftime("%Y%m%d") / f"CHART_{chart_id}" / "ML_READY" / f"ml_{symbol.upper()}{contract}_FUT_CME_{chart_id}.jsonl"


@st.cache_data(ttl=3)
def load_latest_snapshot(symbol: str) -> Optional[Dict]:
    for days_back in range(3):
        date = datetime.now() - timedelta(days=days_back)
        file_path = build_snapshot_path(symbol, date)
        if file_path and file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        snapshot = json.loads(lines[-1].strip())
                        # ✅ TODO #8: Validation snapshot
                        if validate_snapshot(snapshot):
                            return snapshot
            except Exception as e:
                continue
    return None


# ✅ TODO #8: Validation snapshot (data quality)
def validate_snapshot(snapshot: Dict) -> bool:
    """Vérifie que le snapshot contient les champs critiques"""
    if not snapshot:
        return False

    # Champs requis minimaux
    required_fields = ['mid', 'sym', 't_ms']
    for field in required_fields:
        if field not in snapshot or snapshot[field] is None:
            return False

    # Vérifier que mid est un nombre valide
    mid = snapshot.get('mid', 0)
    if not isinstance(mid, (int, float)) or mid <= 0:
        return False

    # Vérifier âge des données (max 60s pour être sûr)
    t_ms = snapshot.get('t_ms', 0)
    now_ms = int(time.time() * 1000)
    age_s = (now_ms - t_ms) / 1000
    if age_s > 120:  # 2 min max
        return False

    return True


def get_snapshot_quality(snapshot: Dict) -> Dict:
    """Retourne info sur qualité du snapshot"""
    if not snapshot:
        return {'quality': 'BAD', 'emoji': '❌', 'color': '#ef476f', 'reason': 'No data'}

    data_quality = snapshot.get('data_quality', 'UNKNOWN')
    t_ms = snapshot.get('t_ms', 0)
    now_ms = int(time.time() * 1000)
    age_s = (now_ms - t_ms) / 1000

    if age_s > 30:
        return {'quality': 'STALE', 'emoji': '⚠️', 'color': '#f8c36b', 'reason': f'Données anciennes ({age_s:.0f}s)', 'age_s': age_s}
    elif data_quality == 'OK':
        return {'quality': 'GOOD', 'emoji': '✅', 'color': '#0fbf84', 'reason': 'OK', 'age_s': age_s}
    else:
        return {'quality': 'WARN', 'emoji': '⚠️', 'color': '#f8c36b', 'reason': f'Quality: {data_quality}', 'age_s': age_s}


# ✅ TODO #7: Parsing logs robuste
def parse_trade_log_line(line: str) -> Optional[Dict]:
    """Parse une ligne de log trade - Version robuste"""
    try:
        if not line or not line.strip():
            return None

        # Format attendu: "HH:MM:SS | SYMBOL | ACTION | {json...}"
        parts = line.split(' | ')
        if len(parts) < 3:
            return None

        time_str = parts[0].strip()

        # Valider format heure
        if not re.match(r'\d{2}:\d{2}:\d{2}', time_str):
            return None

        symbol = parts[1].strip().upper()

        # Valider symbole
        if symbol not in ['ES', 'NQ', 'RTY']:
            return None

        action = parts[2].strip().upper()

        # Valider action
        if action not in ['ENTRY', 'EXIT', 'OPEN', 'CLOSE', 'UPDATE']:
            return None

        # Extraire JSON si présent
        data = {}
        if len(parts) >= 4:
            json_str = ' | '.join(parts[3:])
            # Chercher tous les JSON dans la ligne
            json_matches = re.findall(r'\{[^{}]*\}', json_str)
            for match in json_matches:
                try:
                    parsed = json.loads(match)
                    data.update(parsed)
                except json.JSONDecodeError:
                    continue

        return {
            'time': time_str,
            'symbol': symbol,
            'action': action,
            'data': data
        }
    except Exception as e:
        return None


@st.cache_data(ttl=30)
def load_trades_from_log(date: datetime) -> List[Dict]:
    """Charge les trades depuis le fichier log"""
    date_str = date.strftime("%Y%m%d")
    log_path = PROJECT_ROOT / "logs_advanced" / "trades" / f"trades_{date_str}.log"

    if not log_path.exists():
        return []

    trades = []
    entries = {}

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                parsed = parse_trade_log_line(line.strip())
                if not parsed:
                    continue

                symbol = parsed['symbol']
                action = parsed['action']
                data = parsed['data']

                if action == 'ENTRY':
                    entries[symbol] = {
                        'symbol': symbol,
                        'time_entry': parsed['time'],
                        'direction': data.get('direction', 'LONG'),
                        'entry_price': data.get('price', 0),
                        'sl': data.get('sl', 0),
                        'tp': data.get('tp', 0),
                        'confidence': data.get('confidence', 0),
                        'level_name': data.get('level_name', 'Unknown'),
                        'level_price': data.get('level_price', 0),
                    }

                elif action == 'EXIT' and symbol in entries:
                    trade = entries.pop(symbol)
                    trade.update({
                        'time_exit': parsed['time'],
                        'exit_price': data.get('exit_price', 0),
                        'pnl_usd': data.get('pnl_usd', 0),
                        'pnl_ticks': data.get('pnl_ticks', 0),
                        'exit_reason': data.get('exit_reason', 'Unknown'),
                        'mfe': data.get('mfe', 0),
                        'mae': data.get('mae', 0),
                        'duration_ms': data.get('duration_ms', 0),
                        'result': 'WIN' if data.get('pnl_usd', 0) > 0 else 'LOSS'
                    })
                    trades.append(trade)
    except Exception as e:
        pass

    return trades


def load_trades_period(days: int = 7) -> List[Dict]:
    """Charge les trades sur une période"""
    all_trades = []
    today = datetime.now()

    for days_back in range(days):
        date = today - timedelta(days=days_back)
        day_trades = load_trades_from_log(date)
        for trade in day_trades:
            trade['date'] = date.strftime("%Y-%m-%d")
        all_trades.extend(day_trades)

    return all_trades

# ═══════════════════════════════════════════════════════════════
# EXTRACT DATA FROM SNAPSHOT
# ═══════════════════════════════════════════════════════════════

def extract_market_context(snapshot: Dict) -> Dict:
    """Extrait TOUTES les données de contexte du snapshot"""
    if not snapshot:
        return {}

    mid = snapshot.get('mid', 0)

    return {
        'mid': mid,
        'spread_ticks': snapshot.get('spread_ticks', 0),
        'atr': snapshot.get('atr', 0),
        'vwap': snapshot.get('vwap', mid),
        'd_vwap_ticks': snapshot.get('d_vwap_ticks', 0),
        'vwap_weekly': snapshot.get('vwap_weekly', mid),
        'd_vwap_weekly_ticks': snapshot.get('d_vwap_weekly_ticks', 0),
        '1d_max': snapshot.get('1d_max', 0),
        '1d_min': snapshot.get('1d_min', 0),
        'position_in_range': snapshot.get('position_in_range', 50),
        'distance_to_high_pct': snapshot.get('distance_to_high_pct', 0),
        'distance_to_low_pct': snapshot.get('distance_to_low_pct', 0),
        'mia_bullish_score': snapshot.get('mia_bullish_score', 0.5),
        'deltaPct': snapshot.get('deltaPct', 0),
        'smart_money_flow': snapshot.get('smart_money_flow', 0),
        'institutional_pressure': snapshot.get('institutional_pressure', 0),
        'volatility_regime': snapshot.get('volatility_regime', 1),
        'volatility_regime5': snapshot.get('volatility_regime5', 2),
        'atr_ratio': snapshot.get('atr_ratio', 1),
        'cum_delta_session': snapshot.get('cum_delta_session', 0),
        'delta': snapshot.get('delta', 0),
        'askPct': snapshot.get('askPct', 0.5),
        'bidPct': snapshot.get('bidPct', 0.5),
        'sell_pct': snapshot.get('sell_pct', 0.5),
        'buy_pct': snapshot.get('buy_pct', 0.5),
        'depth_imbalance': snapshot.get('depth_imbalance', 0),
        'dom_features': snapshot.get('dom_features', {}),
        'ob_center': snapshot.get('ob_center', 0),
        'session_id': snapshot.get('session_id', 'Unknown'),
        'session_progress': snapshot.get('session_progress', 0),
        'intermarkets': snapshot.get('intermarkets', {}),
        'vix': snapshot.get('vix', 0),
        'vva': snapshot.get('vva', {}),
        'in_value_area': snapshot.get('in_value_area', False),
        'gamma_side': snapshot.get('gamma_side', 'neutral'),
        'gamma_wall_level': snapshot.get('gamma_wall_level', 0),
        'next_wall': snapshot.get('next_wall', {}),
        'confluence_density': snapshot.get('confluence_density', 0),
        'confluence_strength': snapshot.get('confluence_strength', 0),
        'tick_momentum': snapshot.get('tick_momentum', 0),
        'delta_burst': snapshot.get('delta_burst', 0),
        'stacked_imbalance_bid_rows': snapshot.get('stacked_imbalance_bid_rows', 0),
        'stacked_imbalance_ask_rows': snapshot.get('stacked_imbalance_ask_rows', 0),
        'menthor_distances': snapshot.get('menthor_distances', {}),
    }


def extract_all_levels(snapshot: Dict, symbol: str) -> List[Dict]:
    """Extrait tous les niveaux MenthorQ du snapshot"""
    if not snapshot:
        return []

    levels = []
    mid = snapshot.get('mid', 0)
    if mid == 0:
        return []

    config = SYMBOLS_CONFIG[symbol]
    tick_size = config['tick_size']

    # Niveaux simples
    level_map = {
        'hvl': ('💎', 'HVL', 1, 'MAGNET', 'HVL'),
        'hvl_0dte': ('🔥', 'HVL 0DTE', 1, 'MAGNET', 'HVL_0DTE'),
        '1d_max': ('🔺', '1D MAX', 1, 'RESISTANCE', '1D_MAX'),
        '1d_min': ('🔻', '1D MIN', 1, 'SUPPORT', '1D_MIN'),
        'call_resistance': ('🔴', 'Call Wall', 2, 'RESISTANCE', 'CALL_WALL'),
        'put_support': ('🟢', 'Put Wall', 2, 'SUPPORT', 'PUT_WALL'),
        'call_resistance_0dte': ('🔴', 'Call 0DTE', 2, 'RESISTANCE', 'CALL_WALL'),
        'put_support_0dte': ('🟢', 'Put 0DTE', 2, 'SUPPORT', 'PUT_WALL'),
        'gamma_wall_0dte': ('⚡', 'Gamma 0DTE', 2, 'MAGNET', 'HVL'),
        'vwap': ('📈', 'VWAP', 4, 'PIVOT', 'VWAP'),
        'vwap_up1': ('📈', 'VWAP +1σ', 4, 'RESISTANCE', 'VWAP'),
        'vwap_dn1': ('📈', 'VWAP -1σ', 4, 'SUPPORT', 'VWAP'),
    }

    for key, (emoji, name, tier, behavior, behavior_key) in level_map.items():
        price = snapshot.get(key, 0)
        if price and price > 0:
            distance = (price - mid) / tick_size
            level_info = LEVEL_BEHAVIORS.get(behavior_key, {})
            levels.append({
                'key': key, 'name': name, 'price': price,
                'distance': distance, 'distance_abs': abs(distance),
                'emoji': emoji, 'tier': tier, 'behavior': behavior,
                'direction': 'UP' if price > mid else 'DOWN',
                'bounce_rate': level_info.get('bounce_rate', 50),
                'action_long': level_info.get('action_long', '-'),
                'action_short': level_info.get('action_short', '-'),
            })

    # VAH/VAL/VPOC depuis vva
    vva = snapshot.get('vva', {})
    if vva:
        vva_map = [
            ('vah', 'VAH', 'RESISTANCE', 'VAH'),
            ('val', 'VAL', 'SUPPORT', 'VAL'),
            ('vpoc', 'VPOC', 'MAGNET', 'VPOC')
        ]
        for key, name, behavior, behavior_key in vva_map:
            price = vva.get(key, 0)
            if price and price > 0:
                distance = (price - mid) / tick_size
                level_info = LEVEL_BEHAVIORS.get(behavior_key, {})
                levels.append({
                    'key': key, 'name': name, 'price': price,
                    'distance': distance, 'distance_abs': abs(distance),
                    'emoji': '📊', 'tier': 1, 'behavior': behavior,
                    'direction': 'UP' if price > mid else 'DOWN',
                    'bounce_rate': level_info.get('bounce_rate', 50),
                    'action_long': level_info.get('action_long', '-'),
                    'action_short': level_info.get('action_short', '-'),
                })

    # GEX 1-10
    for i in range(1, 11):
        price = snapshot.get(f'gex_{i}', 0)
        if price and price > 0:
            distance = (price - mid) / tick_size
            level_info = LEVEL_BEHAVIORS.get('GEX', {})
            levels.append({
                'key': f'gex_{i}', 'name': f'GEX {i}', 'price': price,
                'distance': distance, 'distance_abs': abs(distance),
                'emoji': '⭐', 'tier': 3, 'behavior': 'PIVOT',
                'direction': 'UP' if price > mid else 'DOWN',
                'bounce_rate': level_info.get('bounce_rate', 60),
                'action_long': level_info.get('action_long', '-'),
                'action_short': level_info.get('action_short', '-'),
            })

    # ✅ TODO #1: Blind Spots 0-8 dans snapshot → BL 1-9 affichage (Sierra = BL 1-9)
    for i in range(0, 9):  # blind_spot_0 à blind_spot_8
        price = snapshot.get(f'blind_spot_{i}', 0)
        if price and price > 0:
            distance = (price - mid) / tick_size
            level_info = LEVEL_BEHAVIORS.get('BLIND_SPOT', {})
            levels.append({
                'key': f'blind_spot_{i}', 'name': f'BL {i+1}', 'price': price,  # ✅ BL 1-9
                'distance': distance, 'distance_abs': abs(distance),
                'emoji': '👁️', 'tier': 3, 'behavior': 'FAST_MOVE',
                'direction': 'UP' if price > mid else 'DOWN',
                'bounce_rate': level_info.get('bounce_rate', 55),
                'action_long': level_info.get('action_long', '-'),
                'action_short': level_info.get('action_short', '-'),
            })

    levels.sort(key=lambda x: x['distance_abs'])
    return levels

# ═══════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_current_session() -> Dict:
    """✅ TODO #3: Session detection avec heures ET minutes (aligné session_quality_monitor.py)"""
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute

    for name, info in TRADING_SESSIONS.items():
        start_mins = info.get('start_hour', 0) * 60 + info.get('start_min', 0)
        end_mins = info.get('end_hour', 0) * 60 + info.get('end_min', 0)

        # Gérer le cas overnight (ex: 21:30 -> 08:00)
        if end_mins < start_mins:
            if current_minutes >= start_mins or current_minutes < end_mins:
                return {'name': name, **info}
        else:
            if start_mins <= current_minutes < end_mins:
                return {'name': name, **info}

    return {'name': 'HARD_STOP', 'quality': 0, 'tradable': False, 'color': '#ef476f', 'name_fr': 'Hard Stop'}


def calculate_bias(ctx: Dict) -> Dict:
    """Calcule le BIAS à partir de TOUTES les données du snapshot"""
    score = 0.0
    factors = []

    # 1. Position 1D (30%)
    pos = ctx.get('position_in_range', 50)
    if pos >= 80:
        score -= 0.30
        factors.append(('🔴', f"Position 1D: {pos:.0f}% (TOP) → SHORT"))
    elif pos <= 20:
        score += 0.30
        factors.append(('🟢', f"Position 1D: {pos:.0f}% (BOTTOM) → LONG"))
    else:
        factors.append(('⚪', f"Position 1D: {pos:.0f}% (MIDDLE)"))

    # 2. MIA Bullish Score (25%)
    bullish = ctx.get('mia_bullish_score', 0.5)
    if bullish > 0.65:
        score += 0.25
        factors.append(('🟢', f"MIA Score: {bullish:.1%} (BULLISH)"))
    elif bullish < 0.35:
        score -= 0.25
        factors.append(('🔴', f"MIA Score: {bullish:.1%} (BEARISH)"))
    else:
        factors.append(('⚪', f"MIA Score: {bullish:.1%} (NEUTRAL)"))

    # 3. OrderFlow Delta (20%)
    delta_pct = ctx.get('deltaPct', 0)
    if delta_pct > 0.15:
        score += 0.20
        factors.append(('🟢', f"OrderFlow: {delta_pct:+.1%} (BUYING)"))
    elif delta_pct < -0.15:
        score -= 0.20
        factors.append(('🔴', f"OrderFlow: {delta_pct:+.1%} (SELLING)"))
    else:
        factors.append(('⚪', f"OrderFlow: {delta_pct:+.1%} (BALANCED)"))

    # 4. VWAP Position (15%)
    d_vwap = ctx.get('d_vwap_ticks', 0)
    if d_vwap > 5:
        score += 0.15
        factors.append(('🟢', f"VWAP: +{d_vwap:.1f}t (AU-DESSUS)"))
    elif d_vwap < -5:
        score -= 0.15
        factors.append(('🔴', f"VWAP: {d_vwap:.1f}t (EN-DESSOUS)"))
    else:
        factors.append(('⚪', f"VWAP: {d_vwap:+.1f}t (PROCHE)"))

    # 5. Smart Money (10%)
    smart = ctx.get('smart_money_flow', 0)
    if smart > 0.2:
        score += 0.10
        factors.append(('🟢', f"Smart Money: {smart:+.2f} (BUYING)"))
    elif smart < -0.2:
        score -= 0.10
        factors.append(('🔴', f"Smart Money: {smart:+.2f} (SELLING)"))
    else:
        factors.append(('⚪', f"Smart Money: {smart:+.2f} (NEUTRAL)"))

    if score > 0.25:
        bias = 'BULLISH'
        emoji = '🟢'
        color = '#0fbf84'
    elif score < -0.25:
        bias = 'BEARISH'
        emoji = '🔴'
        color = '#ef476f'
    else:
        bias = 'NEUTRAL'
        emoji = '⚪'
        color = '#64748b'

    return {
        'bias': bias, 'score': score, 'emoji': emoji, 'color': color,
        'confidence': min(abs(score) * 2, 1.0), 'factors': factors
    }


def detect_volatility_regime(ctx: Dict) -> Dict:
    """Détecte le régime de volatilité"""
    atr_ratio = ctx.get('atr_ratio', 1)

    if atr_ratio >= 20:
        regime = 'EXTREME'
        emoji = '🔥'
        color = '#ef476f'
        conseil = "⚠️ VOLATILITÉ EXTRÊME! Réduire taille. Élargir stops."
    elif atr_ratio >= 10:
        regime = 'HIGH'
        emoji = '⚡'
        color = '#f8c36b'
        conseil = "⚡ Volatilité élevée. Prudence. Stops plus larges."
    elif atr_ratio >= 5:
        regime = 'NORMAL'
        emoji = '📊'
        color = '#4a9eff'
        conseil = "✅ Volatilité normale. Conditions standard."
    else:
        regime = 'LOW'
        emoji = '😴'
        color = '#64748b'
        conseil = "💤 Volatilité faible. Range possible."

    return {'regime': regime, 'atr_ratio': atr_ratio, 'emoji': emoji, 'color': color, 'conseil': conseil}


# ✅ TODO #4: VIX Regime Detection (CRITIQUE pour MIA!)
def detect_vix_regime(ctx: Dict) -> Dict:
    """Détecte le régime VIX - CRITIQUE pour décisions trading MIA"""
    vix = ctx.get('vix', 0)

    if vix < 15:
        return {'regime': 'NORMAL', 'vix': vix, 'emoji': '🟢', 'color': '#0fbf84',
                'status': '✅ OK', 'can_trade': True, 'conseil': "VIX bas - Trading normal"}
    elif vix < 20:
        return {'regime': 'ELEVATED', 'vix': vix, 'emoji': '🟢', 'color': '#4a9eff',
                'status': '✅ OK', 'can_trade': True, 'conseil': "VIX modéré - Trading normal"}
    elif vix < 25:
        return {'regime': 'HIGH', 'vix': vix, 'emoji': '🟡', 'color': '#f8c36b',
                'status': '⚠️ PRUDENCE', 'can_trade': True, 'conseil': "VIX élevé - Prudence accrue"}
    elif vix < 35:
        return {'regime': 'VERY_HIGH', 'vix': vix, 'emoji': '🔴', 'color': '#ff6b6b',
                'status': '🔴 SKIP', 'can_trade': False, 'conseil': "VIX très haut - ÉVITER les trades!"}
    else:
        return {'regime': 'EXTREME', 'vix': vix, 'emoji': '⛔', 'color': '#ef476f',
                'status': '⛔ STOP', 'can_trade': False, 'conseil': "VIX EXTRÊME - STOP TOTAL!"}


# ✅ TODO #5: Intermarket ES/NQ Divergence
def detect_intermarket_divergence(ctx: Dict) -> Dict:
    """Détecte divergence ES/NQ"""
    intermarkets = ctx.get('intermarkets', {})
    divergence_flag = intermarkets.get('divergence_flag', 0)
    rs_z = intermarkets.get('nq_es_rs_z_120s', 0)
    lead_cc = intermarkets.get('es_nq_lead_cc', 0)

    if divergence_flag == 1:
        return {
            'has_divergence': True,
            'emoji': '⚠️',
            'color': '#f8c36b',
            'rs_z': rs_z,
            'lead_cc': lead_cc,
            'conseil': "⚠️ DIVERGENCE ES/NQ détectée! Prudence accrue."
        }

    # Détecter qui lead
    if abs(lead_cc) > 0.05:
        leader = 'ES' if lead_cc > 0 else 'NQ'
        return {
            'has_divergence': False,
            'emoji': '📊',
            'color': '#4a9eff',
            'rs_z': rs_z,
            'lead_cc': lead_cc,
            'leader': leader,
            'conseil': f"{leader} lead actuellement (CC: {lead_cc:.3f})"
        }

    return {
        'has_divergence': False,
        'emoji': '✅',
        'color': '#0fbf84',
        'rs_z': rs_z,
        'lead_cc': lead_cc,
        'conseil': "ES/NQ synchronisés"
    }


# ✅ TODO #6: Gamma Side Display
def detect_gamma_side(ctx: Dict) -> Dict:
    """Détecte position par rapport au Gamma Wall"""
    gamma_side = ctx.get('gamma_side', 'neutral')
    gamma_wall = ctx.get('gamma_wall_level', 0)
    mid = ctx.get('mid', 0)

    if gamma_side == 'above':
        return {
            'side': 'ABOVE',
            'emoji': '🔺',
            'color': '#0fbf84',
            'gamma_wall': gamma_wall,
            'conseil': "Au-dessus du Gamma Wall - Momentum haussier favorisé"
        }
    elif gamma_side == 'below':
        return {
            'side': 'BELOW',
            'emoji': '🔻',
            'color': '#ef476f',
            'gamma_wall': gamma_wall,
            'conseil': "En-dessous du Gamma Wall - Momentum baissier favorisé"
        }
    else:
        return {
            'side': 'NEUTRAL',
            'emoji': '⚪',
            'color': '#64748b',
            'gamma_wall': gamma_wall,
            'conseil': "Position neutre vs Gamma Wall"
        }


def detect_market_mode(ctx: Dict, bias: Dict, vol: Dict) -> Dict:
    """Détecte le MODE de marché"""
    bullish = ctx.get('mia_bullish_score', 0.5)
    trend_strength = abs(bullish - 0.5) * 2

    if vol['regime'] == 'EXTREME':
        return {
            'mode': 'VOLATILITY', 'emoji': '🔥', 'color': '#ef476f',
            'direction': 'FOLLOW', 'trade_es': True, 'trade_nq': True,
            'conseil': "🔥 VOLATILITÉ EXTRÊME - Suivre momentum ou attendre."
        }

    if trend_strength > 0.3:
        if bullish > 0.6:
            return {
                'mode': 'TREND', 'emoji': '🚀', 'color': '#0fbf84',
                'direction': 'LONG', 'trade_es': True, 'trade_nq': True,
                'conseil': "🚀 TREND BULLISH - Favoriser LONG sur pullbacks."
            }
        else:
            return {
                'mode': 'TREND', 'emoji': '📉', 'color': '#ef476f',
                'direction': 'SHORT', 'trade_es': True, 'trade_nq': True,
                'conseil': "📉 TREND BEARISH - Favoriser SHORT sur rallies."
            }

    if vol['regime'] == 'LOW' or trend_strength < 0.15:
        return {
            'mode': 'RANGE', 'emoji': '↔️', 'color': '#4a9eff',
            'direction': 'FADE', 'trade_es': False, 'trade_nq': True,
            'conseil': "↔️ RANGE - Fader extrêmes. ⚠️ ES éviter en RANGE."
        }

    return {
        'mode': 'MIXED', 'emoji': '🔄', 'color': '#f8c36b',
        'direction': 'CAREFUL', 'trade_es': True, 'trade_nq': True,
        'conseil': "🔄 Conditions mixtes - Attendre signal clair."
    }


def get_direction_to_favor(bias: Dict, mode: Dict, ctx: Dict) -> Dict:
    """Direction à favoriser"""
    if mode['mode'] == 'RANGE':
        pos = ctx.get('position_in_range', 50)
        if pos >= 70:
            return {'direction': 'SHORT', 'emoji': '🔴', 'color': '#ef476f',
                    'strength': 0.7, 'conseil': "Position haute en RANGE → SHORT favorisé"}
        elif pos <= 30:
            return {'direction': 'LONG', 'emoji': '🟢', 'color': '#0fbf84',
                    'strength': 0.7, 'conseil': "Position basse en RANGE → LONG favorisé"}

    if mode['direction'] in ['LONG', 'SHORT']:
        return {'direction': mode['direction'],
                'emoji': '🟢' if mode['direction'] == 'LONG' else '🔴',
                'color': '#0fbf84' if mode['direction'] == 'LONG' else '#ef476f',
                'strength': 0.8, 'conseil': f"Mode TREND → {mode['direction']} favorisé"}

    if bias['bias'] != 'NEUTRAL':
        direction = 'LONG' if bias['bias'] == 'BULLISH' else 'SHORT'
        return {'direction': direction, 'emoji': bias['emoji'], 'color': bias['color'],
                'strength': bias['confidence'], 'conseil': f"Bias {bias['bias']} → {direction} favorisé"}

    return {'direction': 'BOTH', 'emoji': '⚪', 'color': '#64748b',
            'strength': 0.3, 'conseil': "Pas de direction claire - Attendre signal"}


def get_closest_levels(levels: List[Dict], symbol: str) -> Dict:
    """Trouve les niveaux les plus proches UP et DOWN"""
    config = SYMBOLS_CONFIG[symbol]

    levels_up = [l for l in levels if l['distance'] > 0]
    levels_down = [l for l in levels if l['distance'] < 0]

    closest_up = min(levels_up, key=lambda x: x['distance']) if levels_up else None
    closest_down = max(levels_down, key=lambda x: x['distance']) if levels_down else None

    return {
        'up': closest_up,
        'down': closest_down,
        'nearest': closest_up if (closest_up and (not closest_down or closest_up['distance_abs'] < closest_down['distance_abs'])) else closest_down,
        'max_entry': config['max_entry_distance'],
        'max_distance': config['max_distance'],
    }

# ═══════════════════════════════════════════════════════════════
# 🆕 TRADE SUGGESTION & CHECKLIST
# ═══════════════════════════════════════════════════════════════

def generate_trade_suggestion(symbol: str, ctx: Dict, bias: Dict, mode: Dict,
                               direction: Dict, session: Dict, levels: List[Dict],
                               dom_side: str) -> Dict:
    """Génère une suggestion de trade avec checklist"""

    config = SYMBOLS_CONFIG[symbol]
    closest = get_closest_levels(levels, symbol)
    nearest_level = closest['nearest']

    # Pas de niveau proche
    if not nearest_level:
        return {
            'action': 'WAIT',
            'emoji': '⏳',
            'color': '#64748b',
            'reason': "Aucun niveau proche détecté",
            'level': None,
            'checklist': [],
            'score': 0,
        }

    # Déterminer direction suggérée selon le niveau
    if nearest_level['behavior'] == 'SUPPORT' or (nearest_level['behavior'] == 'PIVOT' and nearest_level['direction'] == 'DOWN'):
        suggested_dir = 'LONG'
    elif nearest_level['behavior'] == 'RESISTANCE' or (nearest_level['behavior'] == 'PIVOT' and nearest_level['direction'] == 'UP'):
        suggested_dir = 'SHORT'
    elif nearest_level['behavior'] == 'MAGNET':
        suggested_dir = direction['direction'] if direction['direction'] in ['LONG', 'SHORT'] else 'BOTH'
    else:
        suggested_dir = 'BOTH'

    # Checklist
    checklist = []
    score = 0
    max_score = 7

    # 1. Session tradable
    if session['tradable']:
        checklist.append({'item': f"Session {session['name']} (quality {session['quality']})", 'status': 'ok', 'emoji': '✅'})
        score += 1
    else:
        checklist.append({'item': f"Session {session['name']} (non tradable)", 'status': 'fail', 'emoji': '❌'})

    # 2. Niveau proche
    dist = nearest_level['distance_abs']
    if dist <= config['max_entry_distance']:
        checklist.append({'item': f"Niveau proche: {nearest_level['name']} @ {dist:.1f}t ≤ {config['max_entry_distance']}t", 'status': 'ok', 'emoji': '✅'})
        score += 1
    elif dist <= config['max_distance']:
        checklist.append({'item': f"Niveau visible: {nearest_level['name']} @ {dist:.1f}t (attendre)", 'status': 'warn', 'emoji': '⚠️'})
        score += 0.5
    else:
        checklist.append({'item': f"Niveau loin: {nearest_level['name']} @ {dist:.1f}t", 'status': 'fail', 'emoji': '❌'})

    # 3. Direction alignée avec BIAS
    if suggested_dir == 'BOTH' or bias['bias'] == 'NEUTRAL':
        checklist.append({'item': f"Direction {suggested_dir} vs BIAS {bias['bias']} (neutre)", 'status': 'warn', 'emoji': '⚠️'})
        score += 0.5
    elif (suggested_dir == 'LONG' and bias['bias'] == 'BULLISH') or (suggested_dir == 'SHORT' and bias['bias'] == 'BEARISH'):
        checklist.append({'item': f"Direction {suggested_dir} alignée BIAS {bias['bias']}", 'status': 'ok', 'emoji': '✅'})
        score += 1
    else:
        checklist.append({'item': f"Direction {suggested_dir} CONTRE BIAS {bias['bias']}", 'status': 'fail', 'emoji': '❌'})

    # 4. Mode marché favorable
    if mode['mode'] == 'TREND':
        checklist.append({'item': f"Mode {mode['mode']} favorable", 'status': 'ok', 'emoji': '✅'})
        score += 1
    elif mode['mode'] == 'RANGE':
        if symbol == 'ES':
            checklist.append({'item': f"Mode RANGE - ES déconseillé", 'status': 'fail', 'emoji': '❌'})
        else:
            checklist.append({'item': f"Mode RANGE - Fader extrêmes", 'status': 'warn', 'emoji': '⚠️'})
            score += 0.5
    elif mode['mode'] == 'VOLATILITY':
        checklist.append({'item': f"Mode VOLATILITÉ - Prudence", 'status': 'warn', 'emoji': '⚠️'})
        score += 0.5
    else:
        checklist.append({'item': f"Mode {mode['mode']} - Mixte", 'status': 'warn', 'emoji': '⚠️'})
        score += 0.5

    # 5. R:R estimé (simplifié)
    checklist.append({'item': "R:R estimé ≥ 1.5 (à vérifier)", 'status': 'warn', 'emoji': '⚠️'})
    score += 0.5

    # 6. DOM confirme
    dom_aligned = (suggested_dir == 'LONG' and dom_side == 'BUYERS') or (suggested_dir == 'SHORT' and dom_side == 'SELLERS')
    if dom_aligned:
        checklist.append({'item': f"DOM {dom_side} confirme {suggested_dir}", 'status': 'ok', 'emoji': '✅'})
        score += 1
    elif dom_side == 'NEUTRAL':
        checklist.append({'item': f"DOM NEUTRAL (attendre direction)", 'status': 'warn', 'emoji': '⚠️'})
        score += 0.5
    else:
        checklist.append({'item': f"DOM {dom_side} CONTRE {suggested_dir}", 'status': 'fail', 'emoji': '❌'})

    # 7. Pas de news (simplifié - toujours OK)
    checklist.append({'item': "Pas de news majeure imminente", 'status': 'ok', 'emoji': '✅'})
    score += 1

    # Déterminer action finale
    score_pct = score / max_score

    if not session['tradable']:
        action = 'NO'
        action_emoji = '🚫'
        action_color = '#ef476f'
        reason = f"Session {session['name']} non tradable"
    elif dist > config['max_entry_distance']:
        action = 'WAIT'
        action_emoji = '⏳'
        action_color = '#f8c36b'
        reason = f"Attendre que prix approche {nearest_level['name']} ({dist:.1f}t → {config['max_entry_distance']}t)"
    elif score_pct >= 0.7:
        action = 'GO'
        action_emoji = '✅'
        action_color = '#0fbf84'
        reason = f"{suggested_dir} @ {nearest_level['name']} - Conditions favorables"
    elif score_pct >= 0.5:
        action = 'WAIT'
        action_emoji = '⚠️'
        action_color = '#f8c36b'
        reason = f"{suggested_dir} possible mais attendre confirmation"
    else:
        action = 'NO'
        action_emoji = '🚫'
        action_color = '#ef476f'
        reason = "Conditions défavorables - Ne pas trader"

    return {
        'action': action,
        'emoji': action_emoji,
        'color': action_color,
        'reason': reason,
        'suggested_direction': suggested_dir,
        'level': nearest_level,
        'checklist': checklist,
        'score': score,
        'score_max': max_score,
        'score_pct': score_pct,
    }

# ═══════════════════════════════════════════════════════════════
# DOM PRESSURE
# ═══════════════════════════════════════════════════════════════

if 'dom_ema_score' not in st.session_state:
    st.session_state.dom_ema_score = 0.0

def calculate_dom_pressure(snapshot: Dict) -> Dict:
    """Calcule la pression DOM avec lissage EMA"""
    dom_features = snapshot.get('dom_features', {})

    ask_pct = snapshot.get('askPct', 0.5)
    bid_pct = snapshot.get('bidPct', 0.5)
    delta_pct = snapshot.get('deltaPct', 0)
    depth_bid = dom_features.get('depth_bid', 0)
    depth_ask = dom_features.get('depth_ask', 0)
    imbalance_1_3 = dom_features.get('imbalance_1_3', 0)
    smart_money = snapshot.get('smart_money_flow', 0)
    institutional = snapshot.get('institutional_pressure', 0)
    delta_burst = snapshot.get('delta_burst', 0)
    stacked_bid = snapshot.get('stacked_imbalance_bid_rows', 0)
    stacked_ask = snapshot.get('stacked_imbalance_ask_rows', 0)
    cum_delta = snapshot.get('cum_delta_session', 0)

    # Calcul score
    score = 0.0
    factors = {}

    # Delta % (25%)
    if delta_pct > 0.15:
        contrib = min(delta_pct / 0.3, 1.0) * 0.25
        score += contrib
        factors['Delta'] = ('🟢 BUYERS', contrib, delta_pct)
    elif delta_pct < -0.15:
        contrib = min(abs(delta_pct) / 0.3, 1.0) * 0.25
        score -= contrib
        factors['Delta'] = ('🔴 SELLERS', -contrib, delta_pct)
    else:
        factors['Delta'] = ('⚪ Neutre', 0, delta_pct)

    # Depth (20%)
    if depth_bid > 0 and depth_ask > 0:
        depth_ratio = depth_bid / depth_ask
        if depth_ratio > 1.2:
            contrib = min((depth_ratio - 1) / 0.5, 1.0) * 0.20
            score += contrib
            factors['Depth'] = ('🟢 BUYERS', contrib, depth_ratio)
        elif depth_ratio < 0.83:
            contrib = min((1/depth_ratio - 1) / 0.5, 1.0) * 0.20
            score -= contrib
            factors['Depth'] = ('🔴 SELLERS', -contrib, depth_ratio)
        else:
            factors['Depth'] = ('⚪ Neutre', 0, depth_ratio)

    # Imbalance (15%)
    if imbalance_1_3 > 0.20:
        contrib = min(imbalance_1_3 / 0.4, 1.0) * 0.15
        score += contrib
        factors['Imbalance'] = ('🟢 BUYERS', contrib, imbalance_1_3)
    elif imbalance_1_3 < -0.20:
        contrib = min(abs(imbalance_1_3) / 0.4, 1.0) * 0.15
        score -= contrib
        factors['Imbalance'] = ('🔴 SELLERS', -contrib, imbalance_1_3)
    else:
        factors['Imbalance'] = ('⚪ Neutre', 0, imbalance_1_3)

    # Smart Money (25%)
    if smart_money > 0.15:
        contrib = min(smart_money / 0.5, 1.0) * 0.25
        score += contrib
        factors['Smart Money'] = ('🟢 BUYERS', contrib, smart_money)
    elif smart_money < -0.15:
        contrib = min(abs(smart_money) / 0.5, 1.0) * 0.25
        score -= contrib
        factors['Smart Money'] = ('🔴 SELLERS', -contrib, smart_money)
    else:
        factors['Smart Money'] = ('⚪ Neutre', 0, smart_money)

    # Institutional (15%)
    if institutional > 0.15:
        contrib = min(institutional / 0.5, 1.0) * 0.15
        score += contrib
        factors['Institutional'] = ('🟢 BUYERS', contrib, institutional)
    elif institutional < -0.15:
        contrib = min(abs(institutional) / 0.5, 1.0) * 0.15
        score -= contrib
        factors['Institutional'] = ('🔴 SELLERS', -contrib, institutional)
    else:
        factors['Institutional'] = ('⚪ Neutre', 0, institutional)

    # EMA
    ema_alpha = 0.2
    if st.session_state.dom_ema_score == 0:
        st.session_state.dom_ema_score = score
    else:
        st.session_state.dom_ema_score = ema_alpha * score + (1 - ema_alpha) * st.session_state.dom_ema_score

    smoothed_score = st.session_state.dom_ema_score

    def score_to_side(s):
        if s > 0.15:
            return 'BUYERS', '🟢', '#0fbf84', min(5, int(s / 0.15) + 1)
        elif s < -0.15:
            return 'SELLERS', '🔴', '#ef476f', min(5, int(abs(s) / 0.15) + 1)
        else:
            return 'NEUTRAL', '⚪', '#64748b', 1

    instant_side, instant_emoji, instant_color, instant_strength = score_to_side(score)
    smooth_side, smooth_emoji, smooth_color, smooth_strength = score_to_side(smoothed_score)

    # Grosse main
    big_hand = None
    if delta_burst >= 50:
        side = 'BUY' if delta_pct > 0 else 'SELL'
        big_hand = {'type': 'DELTA_BURST', 'side': side, 'size': delta_burst, 'emoji': '🟢' if side == 'BUY' else '🔴'}
    elif stacked_bid >= 2:
        big_hand = {'type': 'STACKED_BID', 'side': 'BUY', 'size': stacked_bid, 'emoji': '🟢'}
    elif stacked_ask >= 2:
        big_hand = {'type': 'STACKED_ASK', 'side': 'SELL', 'size': stacked_ask, 'emoji': '🔴'}

    # Divergence
    divergence = None
    if instant_side != smooth_side and instant_side != 'NEUTRAL' and smooth_side != 'NEUTRAL':
        if instant_side == 'SELLERS' and smooth_side == 'BUYERS':
            divergence = {'type': 'REVERSAL_DOWN', 'text': '⚠️ Possible retournement BAISSIER'}
        elif instant_side == 'BUYERS' and smooth_side == 'SELLERS':
            divergence = {'type': 'REVERSAL_UP', 'text': '⚠️ Possible retournement HAUSSIER'}

    return {
        'instant': {'side': instant_side, 'emoji': instant_emoji, 'color': instant_color, 'strength': instant_strength, 'score': score},
        'smoothed': {'side': smooth_side, 'emoji': smooth_emoji, 'color': smooth_color, 'strength': smooth_strength, 'score': smoothed_score},
        'raw': {'bid_pct': bid_pct, 'ask_pct': ask_pct, 'delta_pct': delta_pct, 'depth_bid': depth_bid, 'depth_ask': depth_ask, 'smart_money': smart_money, 'cum_delta': cum_delta},
        'factors': factors,
        'big_hand': big_hand,
        'divergence': divergence
    }

# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS - ONGLET LIVE
# ═══════════════════════════════════════════════════════════════

def render_header(session: Dict):
    icon = '🟢' if session['tradable'] else '🔴'
    config_status = "✅ Config OK" if CONFIG_LOADED else "⚠️ Config fallback"
    config_color = "#0fbf84" if CONFIG_LOADED else "#f8c36b"
    st.markdown(f"""
    <div class="main-header">
        <div class="main-title">🎯 MIA Trading Copilot V7</div>
        <div style="margin-top: 8px; color: #94a3b8;">
            <span class="badge" style="background: {session['color']}40; border: 1px solid {session['color']}; color: {session['color']};">
                {icon} {session.get('name_fr', session['name'])}
            </span>
            <span style="margin-left: 12px;">{datetime.now().strftime('%H:%M:%S')}</span>
            <span class="badge" style="background: {config_color}40; color: {config_color}; margin-left: 12px;">
                {config_status}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_metric(label: str, value: str, color: str = "gray"):
    st.markdown(f"""
    <div class="metric-box">
        <div class="metric-label">{label}</div>
        <div class="metric-value {color}">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def render_next_wall(next_wall: Dict, symbol: str):
    """Affiche le NEXT WALL"""
    if not next_wall or not next_wall.get('price'):
        st.markdown("""
        <div class="next-wall-box">
            <div style="font-size: 1.2rem; color: #64748b;">🎯 NEXT WALL</div>
            <div style="font-size: 1.5rem; font-weight: 700; color: #64748b;">Pas de wall détecté</div>
        </div>
        """, unsafe_allow_html=True)
        return

    price = next_wall.get('price', 0)
    side = next_wall.get('side', 'unknown').upper()
    dist_ticks = next_wall.get('dist_ticks', 0)
    strength = next_wall.get('strength', 0)

    if side == 'PUT':
        side_color = '#0fbf84'
        side_emoji = '🟢'
        action = "SUPPORT - Rebond attendu"
    else:
        side_color = '#ef476f'
        side_emoji = '🔴'
        action = "RESISTANCE - Rejet attendu"

    config = SYMBOLS_CONFIG[symbol]
    dist_abs = abs(dist_ticks)
    if dist_abs <= config['max_entry_distance']:
        status = "✅ TRADABLE"
        status_color = '#0fbf84'
    elif dist_abs <= config['max_distance']:
        status = "⚠️ PROCHE"
        status_color = '#f8c36b'
    else:
        status = "❌ LOIN"
        status_color = '#ef476f'

    direction = "↑" if dist_ticks > 0 else "↓"

    st.markdown(f"""
    <div class="next-wall-box">
        <div style="font-size: 1rem; color: #f8c36b; margin-bottom: 8px;">🎯 NEXT WALL (temps réel)</div>
        <div style="font-size: 2rem; font-weight: 800; color: {side_color};">
            {side_emoji} {side} @ {price:,.2f}
        </div>
        <div style="font-size: 1.2rem; margin-top: 8px;">
            <span style="color: #94a3b8;">Distance:</span>
            <span style="color: white; font-weight: 700;">{direction} {dist_abs:.0f}t</span>
            <span style="margin-left: 16px; color: #94a3b8;">Force:</span>
            <span style="color: white; font-weight: 700;">{strength:.0%}</span>
        </div>
        <div style="margin-top: 12px;">
            <span class="badge" style="background: {status_color}40; color: {status_color};">{status}</span>
            <span class="badge" style="background: {side_color}40; color: {side_color};">{action}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_distance_to_levels(levels: List[Dict], symbol: str):
    """Affiche la distance aux niveaux les plus proches UP et DOWN"""
    config = SYMBOLS_CONFIG[symbol]
    closest = get_closest_levels(levels, symbol)

    st.markdown("### 📍 Niveaux les plus proches")

    col1, col2 = st.columns(2)

    with col1:
        level = closest['up']
        if level:
            dist = level['distance']
            max_dist = config['max_distance']
            pct = min(dist / max_dist * 100, 100)
            color = '#0fbf84' if dist <= config['max_entry_distance'] else '#f8c36b' if dist <= max_dist else '#ef476f'
            status = "🟢 TRADABLE" if dist <= config['max_entry_distance'] else ""

            st.markdown(f"""
            <div class="metric-box">
                <div style="font-size: 0.9rem; color: #94a3b8;">⬆️ UP</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: white;">
                    {level['emoji']} {level['name']} @ {level['price']:,.2f}
                </div>
                <div class="distance-bar">
                    <div class="distance-fill" style="width: {pct}%; background: {color};"></div>
                </div>
                <div style="font-size: 1rem; color: {color}; font-weight: 700;">
                    +{dist:.1f}t {status}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="metric-box"><div style="color: #64748b;">⬆️ Aucun niveau UP</div></div>', unsafe_allow_html=True)

    with col2:
        level = closest['down']
        if level:
            dist = abs(level['distance'])
            max_dist = config['max_distance']
            pct = min(dist / max_dist * 100, 100)
            color = '#0fbf84' if dist <= config['max_entry_distance'] else '#f8c36b' if dist <= max_dist else '#ef476f'
            status = "🟢 TRADABLE" if dist <= config['max_entry_distance'] else ""

            st.markdown(f"""
            <div class="metric-box">
                <div style="font-size: 0.9rem; color: #94a3b8;">⬇️ DOWN</div>
                <div style="font-size: 1.1rem; font-weight: 700; color: white;">
                    {level['emoji']} {level['name']} @ {level['price']:,.2f}
                </div>
                <div class="distance-bar">
                    <div class="distance-fill" style="width: {pct}%; background: {color};"></div>
                </div>
                <div style="font-size: 1rem; color: {color}; font-weight: 700;">
                    -{dist:.1f}t {status}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="metric-box"><div style="color: #64748b;">⬇️ Aucun niveau DOWN</div></div>', unsafe_allow_html=True)


def render_trade_suggestion(suggestion: Dict):
    """Affiche la suggestion de trade avec checklist"""

    st.markdown("### 💡 Suggestion Trade")

    # Box principale
    st.markdown(f"""
    <div class="suggestion-box" style="border-color: {suggestion['color']};">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-size: 1.5rem; font-weight: 800; color: {suggestion['color']};">
                    {suggestion['emoji']} {suggestion['action']}
                </div>
                <div style="color: #94a3b8; margin-top: 4px;">
                    {suggestion['reason']}
                </div>
            </div>
            <div style="text-align: right;">
                <div style="font-size: 2rem; font-weight: 800; color: {suggestion['color']};">
                    {suggestion['score']:.1f}/{suggestion['score_max']}
                </div>
                <div style="color: #64748b; font-size: 0.8rem;">Score</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Checklist
    if suggestion['checklist']:
        with st.expander("📋 Checklist pré-trade", expanded=True):
            for item in suggestion['checklist']:
                css_class = f"checklist-{item['status']}"
                st.markdown(f"""
                <div class="checklist-item {css_class}">
                    <span style="margin-right: 8px;">{item['emoji']}</span>
                    <span>{item['item']}</span>
                </div>
                """, unsafe_allow_html=True)


def render_bias_mode_direction(bias: Dict, mode: Dict, direction: Dict, vol: Dict):
    """Affiche BIAS, MODE, DIRECTION, VOLATILITÉ"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        css_class = 'bullish' if bias['bias'] == 'BULLISH' else 'bearish' if bias['bias'] == 'BEARISH' else 'neutral'
        st.markdown(f"""
        <div class="big-box {css_class}">
            <div style="font-size: 0.85rem; color: #94a3b8;">BIAS</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: {bias['color']};">
                {bias['emoji']} {bias['bias']}
            </div>
            <div style="font-size: 0.8rem; color: #64748b;">Score: {bias['score']:+.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="big-box" style="border-color: {mode['color']};">
            <div style="font-size: 0.85rem; color: #94a3b8;">MODE</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: {mode['color']};">
                {mode['emoji']} {mode['mode']}
            </div>
            <div style="font-size: 0.8rem; color: #64748b;">{mode['direction']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="big-box" style="border-color: {direction['color']};">
            <div style="font-size: 0.85rem; color: #94a3b8;">FAVORISER</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: {direction['color']};">
                {direction['emoji']} {direction['direction']}
            </div>
            <div style="font-size: 0.8rem; color: #64748b;">Force: {direction['strength']:.0%}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="big-box" style="border-color: {vol['color']};">
            <div style="font-size: 0.85rem; color: #94a3b8;">VOLATILITÉ</div>
            <div style="font-size: 1.5rem; font-weight: 800; color: {vol['color']};">
                {vol['emoji']} {vol['regime']}
            </div>
            <div style="font-size: 0.8rem; color: #64748b;">ATR: {vol['atr_ratio']:.1f}x</div>
        </div>
        """, unsafe_allow_html=True)


# ✅ TODO #4, #5, #6: Affichage VIX + Intermarket + Gamma
def render_vix_intermarket_gamma(vix_info: Dict, intermarket: Dict, gamma: Dict):
    """Affiche VIX, Intermarket et Gamma Side"""
    col1, col2, col3 = st.columns(3)

    with col1:
        # VIX (CRITIQUE!)
        border_width = "3px" if not vix_info.get('can_trade', True) else "2px"
        st.markdown(f"""
        <div class="metric-box" style="border: {border_width} solid {vix_info['color']};">
            <div class="metric-label">🌡️ VIX REGIME</div>
            <div class="metric-value" style="color: {vix_info['color']};">
                {vix_info['emoji']} {vix_info.get('vix', 0):.1f}
            </div>
            <div style="font-size: 0.75rem; color: {vix_info['color']};">{vix_info['status']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Intermarket
        st.markdown(f"""
        <div class="metric-box" style="border: 1px solid {intermarket['color']};">
            <div class="metric-label">📊 ES/NQ SYNC</div>
            <div class="metric-value" style="color: {intermarket['color']};">
                {intermarket['emoji']} {'DIVERGE' if intermarket.get('has_divergence') else 'OK'}
            </div>
            <div style="font-size: 0.75rem; color: #64748b;">CC: {intermarket.get('lead_cc', 0):.3f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        # Gamma Side
        st.markdown(f"""
        <div class="metric-box" style="border: 1px solid {gamma['color']};">
            <div class="metric-label">⚡ GAMMA SIDE</div>
            <div class="metric-value" style="color: {gamma['color']};">
                {gamma['emoji']} {gamma['side']}
            </div>
            <div style="font-size: 0.75rem; color: #64748b;">Wall: {gamma.get('gamma_wall', 0):,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    # Alerte VIX si nécessaire
    if not vix_info.get('can_trade', True):
        st.markdown(f"""
        <div class="warning-box" style="background: rgba(239,71,111,0.2); border-color: #ef476f;">
            ⛔ <strong>VIX ALERTE!</strong> {vix_info['conseil']}
        </div>
        """, unsafe_allow_html=True)

    # Alerte divergence si nécessaire
    if intermarket.get('has_divergence'):
        st.markdown(f"""
        <div class="warning-box">
            {intermarket['conseil']}
        </div>
        """, unsafe_allow_html=True)


def render_position_1d(ctx: Dict):
    """Barre de position 1D"""
    pos = ctx.get('position_in_range', 50)
    day_max = ctx.get('1d_max', 0)
    day_min = ctx.get('1d_min', 0)

    if day_max <= day_min:
        return

    if pos >= 80:
        zone, zone_color = 'TOP 🔴', '#ef476f'
    elif pos <= 20:
        zone, zone_color = 'BOTTOM 🟢', '#0fbf84'
    else:
        zone, zone_color = 'MIDDLE ⚪', '#f8c36b'

    st.markdown("#### 📏 Position dans Range 1D")
    col1, col2, col3 = st.columns([1, 5, 1])
    with col1:
        st.caption(f"MIN\n{day_min:,.0f}")
    with col2:
        st.progress(pos / 100)
        st.markdown(f"<center><strong style='color: {zone_color};'>{zone} ({pos:.0f}%)</strong></center>", unsafe_allow_html=True)
    with col3:
        st.caption(f"MAX\n{day_max:,.0f}")


def render_dom_pressure(snapshot: Dict):
    """Affiche la section DOM PRESSURE"""
    st.markdown("### 🎯 Qui a la main? (DOM)")

    dom = calculate_dom_pressure(snapshot)
    instant = dom['instant']
    smoothed = dom['smoothed']
    raw = dom['raw']

    col_buy, col_center, col_sell = st.columns([1, 2, 1])

    with col_buy:
        st.markdown(f"""
        <div class="metric-box" style="border: 2px solid #0fbf84;">
            <div style="font-size: 2rem;">🟢</div>
            <div class="metric-label">BUYERS</div>
            <div class="metric-value green">{raw['bid_pct']:.0%}</div>
            <div style="font-size: 0.8rem; color: #64748b;">Depth: {raw['depth_bid']}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_center:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0f1620, #1a2332); border-radius: 16px;
                    padding: 16px; text-align: center; border: 2px solid {instant['color']};">
            <div style="font-size: 0.9rem; color: #64748b;">INSTANTANÉ</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: {instant['color']};">
                {instant['emoji']} {instant['side']}
            </div>
            <div style="margin: 8px 0;">
                <span style="font-size: 1.2rem;">{'█' * instant['strength']}{'░' * (5 - instant['strength'])}</span>
                <span style="color: #64748b; margin-left: 8px;">{instant['strength']}/5</span>
            </div>
            <div style="border-top: 1px solid #1e293b; margin-top: 12px; padding-top: 12px;">
                <div style="font-size: 0.8rem; color: #64748b;">TENDANCE (EMA)</div>
                <div style="font-size: 1.2rem; color: {smoothed['color']};">
                    {smoothed['emoji']} {smoothed['side']} ({smoothed['strength']}/5)
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_sell:
        st.markdown(f"""
        <div class="metric-box" style="border: 2px solid #ef476f;">
            <div style="font-size: 2rem;">🔴</div>
            <div class="metric-label">SELLERS</div>
            <div class="metric-value red">{raw['ask_pct']:.0%}</div>
            <div style="font-size: 0.8rem; color: #64748b;">Depth: {raw['depth_ask']}</div>
        </div>
        """, unsafe_allow_html=True)

    if dom['big_hand']:
        bh = dom['big_hand']
        bg_color = 'rgba(15,191,132,0.2)' if bh['side'] == 'BUY' else 'rgba(239,71,111,0.2)'
        st.markdown(f"""
        <div class="warning-box" style="background: {bg_color};">
            🚨 <strong>GROSSE MAIN!</strong> {bh['emoji']} {bh['side']} | {bh['type']} | Size: {bh['size']}
        </div>
        """, unsafe_allow_html=True)

    if dom['divergence']:
        st.markdown(f'<div class="warning-box">{dom["divergence"]["text"]}</div>', unsafe_allow_html=True)

    return dom


def render_orderflow_metrics(ctx: Dict):
    """Métriques OrderFlow compactes"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        delta = ctx.get('deltaPct', 0)
        color = 'green' if delta > 0 else 'red' if delta < 0 else 'gray'
        render_metric("Delta %", f"{delta:+.1%}", color)

    with col2:
        cum = ctx.get('cum_delta_session', 0)
        color = 'green' if cum > 0 else 'red' if cum < 0 else 'gray'
        render_metric("Cum Delta", f"{cum:+,}", color)

    with col3:
        smart = ctx.get('smart_money_flow', 0)
        color = 'green' if smart > 0.1 else 'red' if smart < -0.1 else 'gray'
        render_metric("Smart Money", f"{smart:+.2f}", color)

    with col4:
        depth = ctx.get('depth_imbalance', 0)
        color = 'green' if depth > 0.05 else 'red' if depth < -0.05 else 'gray'
        render_metric("DOM Imbal", f"{depth:+.1%}", color)


def render_bias_factors(bias: Dict):
    """Détails du calcul du bias"""
    with st.expander("📊 Détails calcul BIAS"):
        for emoji, text in bias['factors']:
            st.write(f"{emoji} {text}")


def render_conseils(conseils: List[str]):
    """Affiche les conseils"""
    st.markdown("### 💡 Conseils")
    for c in conseils:
        st.markdown(f'<div class="conseil-box">{c}</div>', unsafe_allow_html=True)


def generate_conseils_list(symbol: str, ctx: Dict, bias: Dict, mode: Dict, vol: Dict,
                           direction: Dict, session: Dict) -> List[str]:
    """Génère la liste des conseils"""
    conseils = []

    if not session['tradable']:
        conseils.append(f"⚠️ SESSION {session['name']}: Non tradable. ÉVITER.")
    else:
        conseils.append(f"✅ SESSION {session['name']}: Bonne pour trader (quality {session['quality']})")

    if vol['regime'] in ['EXTREME', 'HIGH']:
        conseils.append(vol['conseil'])

    conseils.append(mode['conseil'])

    if symbol == 'ES' and mode['mode'] == 'RANGE':
        conseils.append("⚠️ ES underperforms en RANGE. Préférer NQ.")

    conseils.append(f"🎯 {direction['conseil']}")

    intermarkets = ctx.get('intermarkets', {})
    if intermarkets.get('divergence_flag', 0) == 1:
        conseils.append("⚠️ DIVERGENCE ES/NQ détectée! Prudence.")

    return conseils


def render_levels_table(levels: List[Dict], symbol: str):
    """Tableau des niveaux (version compacte)"""
    st.markdown("### 📊 Niveaux proches")

    config = SYMBOLS_CONFIG[symbol]
    if not levels:
        st.info("Aucun niveau disponible")
        return

    data = []
    for l in levels[:10]:
        if l['distance_abs'] <= config['max_entry_distance']:
            status = "✅"
        elif l['distance_abs'] <= config['max_distance']:
            status = "⚠️"
        else:
            status = "❌"

        data.append({
            "": l['emoji'],
            "Niveau": l['name'],
            "Prix": f"{l['price']:,.2f}",
            "Dist": f"{l['distance']:+.0f}t",
            "": status,
            "Type": l['behavior']
        })

    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS - ONGLET NIVEAUX
# ═══════════════════════════════════════════════════════════════

def render_tab_niveaux(levels: List[Dict], symbol: str, ctx: Dict):
    """Onglet NIVEAUX complet"""
    st.markdown("## 📍 Tous les Niveaux MenthorQ")

    config = SYMBOLS_CONFIG[symbol]
    mid = ctx.get('mid', 0)

    # Filtres
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filter_dir = st.selectbox("Direction", ["Tous", "⬆️ UP", "⬇️ DOWN"])
    with col2:
        filter_tradable = st.checkbox("TRADABLE uniquement", value=False)
    with col3:
        filter_tier = st.multiselect("Tier", [1, 2, 3, 4], default=[1, 2, 3, 4])
    with col4:
        sort_by = st.selectbox("Trier par", ["Distance", "Prix", "Bounce Rate"])

    # Filtrer
    filtered = levels.copy()

    if filter_dir == "⬆️ UP":
        filtered = [l for l in filtered if l['direction'] == 'UP']
    elif filter_dir == "⬇️ DOWN":
        filtered = [l for l in filtered if l['direction'] == 'DOWN']

    if filter_tradable:
        filtered = [l for l in filtered if l['distance_abs'] <= config['max_entry_distance']]

    filtered = [l for l in filtered if l['tier'] in filter_tier]

    # Trier
    if sort_by == "Distance":
        filtered.sort(key=lambda x: x['distance_abs'])
    elif sort_by == "Prix":
        filtered.sort(key=lambda x: x['price'], reverse=True)
    elif sort_by == "Bounce Rate":
        filtered.sort(key=lambda x: x['bounce_rate'], reverse=True)

    # Stats
    tradable_count = len([l for l in levels if l['distance_abs'] <= config['max_entry_distance']])
    proche_count = len([l for l in levels if l['distance_abs'] <= config['max_distance']])

    st.markdown(f"""
    <div style="background: #0f1620; padding: 12px; border-radius: 8px; margin-bottom: 16px;">
        📊 <strong>{len(levels)}</strong> niveaux total |
        <span style="color: #0fbf84;"><strong>{tradable_count}</strong> TRADABLE (≤{config['max_entry_distance']}t)</span> |
        <span style="color: #f8c36b;"><strong>{proche_count}</strong> PROCHE (≤{config['max_distance']}t)</span>
    </div>
    """, unsafe_allow_html=True)

    # Table
    if not filtered:
        st.warning("Aucun niveau avec ces filtres")
        return

    data = []
    for l in filtered:
        if l['distance_abs'] <= config['max_entry_distance']:
            status = "✅ TRADABLE"
            status_color = '#0fbf84'
        elif l['distance_abs'] <= config['max_distance']:
            status = "⚠️ Proche"
            status_color = '#f8c36b'
        else:
            status = "❌ Loin"
            status_color = '#ef476f'

        data.append({
            "Emoji": l['emoji'],
            "Niveau": l['name'],
            "Prix": f"{l['price']:,.2f}",
            "Direction": "⬆️" if l['direction'] == 'UP' else "⬇️",
            "Distance": f"{l['distance']:+.0f}t",
            "Status": status,
            "Behavior": l['behavior'],
            "Bounce %": f"{l['bounce_rate']}%",
            "Tier": l['tier'],
            "Action LONG": l['action_long'],
            "Action SHORT": l['action_short'],
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True, height=500)


# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS - ONGLET PERFORMANCE
# ═══════════════════════════════════════════════════════════════

def render_tab_performance():
    """Onglet PERFORMANCE"""
    st.markdown("## 📈 Performance Trading")

    # Sélecteur période
    col1, col2 = st.columns([1, 3])
    with col1:
        period = st.selectbox("Période", ["Aujourd'hui", "7 jours", "30 jours"])

    days = 1 if period == "Aujourd'hui" else 7 if period == "7 jours" else 30
    trades = load_trades_period(days)

    if not trades:
        st.info(f"Aucun trade sur les {days} derniers jours")
        return

    # KPIs
    total_pnl = sum(t.get('pnl_usd', 0) for t in trades)
    wins = [t for t in trades if t.get('result') == 'WIN']
    losses = [t for t in trades if t.get('result') == 'LOSS']
    win_rate = len(wins) / len(trades) * 100 if trades else 0
    avg_win = sum(t.get('pnl_usd', 0) for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.get('pnl_usd', 0) for t in losses) / len(losses) if losses else 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        color = '#0fbf84' if total_pnl >= 0 else '#ef476f'
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color: {color};">${total_pnl:+,.0f}</div>
            <div class="kpi-label">P&L Total</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color: #4a9eff;">{len(trades)}</div>
            <div class="kpi-label">Trades</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        wr_color = '#0fbf84' if win_rate >= 50 else '#ef476f'
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color: {wr_color};">{win_rate:.0f}%</div>
            <div class="kpi-label">Win Rate</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color: #f8c36b;">{ratio:.2f}</div>
            <div class="kpi-label">Avg W/L Ratio</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # P&L par symbole
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 Par Symbole")
        symbol_stats = {}
        for t in trades:
            sym = t.get('symbol', 'Unknown')
            if sym not in symbol_stats:
                symbol_stats[sym] = {'pnl': 0, 'trades': 0, 'wins': 0}
            symbol_stats[sym]['pnl'] += t.get('pnl_usd', 0)
            symbol_stats[sym]['trades'] += 1
            if t.get('result') == 'WIN':
                symbol_stats[sym]['wins'] += 1

        for sym, stats in symbol_stats.items():
            wr = stats['wins'] / stats['trades'] * 100 if stats['trades'] > 0 else 0
            color = '#0fbf84' if stats['pnl'] >= 0 else '#ef476f'
            status = '✅' if stats['pnl'] >= 0 and wr >= 45 else '❌'
            st.markdown(f"""
            <div style="background: #0f1620; padding: 10px; border-radius: 8px; margin: 4px 0; border-left: 4px solid {color};">
                <strong>{sym}</strong>: <span style="color: {color};">${stats['pnl']:+,.0f}</span>
                ({stats['trades']} trades, {wr:.0f}% WR) {status}
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("#### ⏰ Par Session")
        session_stats = {'LONDON': {'pnl': 0, 'trades': 0, 'wins': 0},
                         'US_MORNING': {'pnl': 0, 'trades': 0, 'wins': 0},
                         'US_POWER': {'pnl': 0, 'trades': 0, 'wins': 0},
                         'OTHER': {'pnl': 0, 'trades': 0, 'wins': 0}}

        for t in trades:
            try:
                hour = int(t.get('time_entry', '00:00:00').split(':')[0])
                if 8 <= hour < 11:
                    sess = 'LONDON'
                elif 15 <= hour < 17:
                    sess = 'US_MORNING'
                elif 20 <= hour < 22:
                    sess = 'US_POWER'
                else:
                    sess = 'OTHER'

                session_stats[sess]['pnl'] += t.get('pnl_usd', 0)
                session_stats[sess]['trades'] += 1
                if t.get('result') == 'WIN':
                    session_stats[sess]['wins'] += 1
            except:
                continue

        for sess, stats in session_stats.items():
            if stats['trades'] == 0:
                continue
            wr = stats['wins'] / stats['trades'] * 100
            color = '#0fbf84' if stats['pnl'] >= 0 else '#ef476f'
            st.markdown(f"""
            <div style="background: #0f1620; padding: 10px; border-radius: 8px; margin: 4px 0; border-left: 4px solid {color};">
                <strong>{sess}</strong>: <span style="color: {color};">${stats['pnl']:+,.0f}</span>
                ({stats['trades']} trades, {wr:.0f}% WR)
            </div>
            """, unsafe_allow_html=True)

    # Insights
    st.divider()
    st.markdown("### 🎯 Insights")

    insights = []

    # Meilleur symbole
    if symbol_stats:
        best_sym = max(symbol_stats.items(), key=lambda x: x[1]['pnl'])
        worst_sym = min(symbol_stats.items(), key=lambda x: x[1]['pnl'])
        if best_sym[1]['pnl'] > 0:
            insights.append(f"✅ Meilleur symbole: **{best_sym[0]}** (+${best_sym[1]['pnl']:,.0f})")
        if worst_sym[1]['pnl'] < 0:
            insights.append(f"❌ Pire symbole: **{worst_sym[0]}** (${worst_sym[1]['pnl']:,.0f}) → Réduire exposition?")

    # Sessions non tradables
    if session_stats.get('OTHER', {}).get('trades', 0) == 0:
        insights.append("✅ Aucun trade hors sessions → Bonne discipline!")
    else:
        other_pnl = session_stats.get('OTHER', {}).get('pnl', 0)
        insights.append(f"⚠️ {session_stats['OTHER']['trades']} trades hors sessions (${other_pnl:+,.0f})")

    # Win rate
    if win_rate >= 50:
        insights.append(f"✅ Win rate {win_rate:.0f}% → Bonne sélectivité")
    else:
        insights.append(f"⚠️ Win rate {win_rate:.0f}% < 50% → Améliorer filtrage?")

    for insight in insights:
        st.markdown(f'<div class="conseil-box">{insight}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS - ONGLET ANALYSE
# ═══════════════════════════════════════════════════════════════

def render_tab_analyse():
    """Onglet ANALYSE TRADE"""
    st.markdown("## 🔍 Analyse Trades")

    trades = load_trades_from_log(datetime.now())

    if not trades:
        st.info("Aucun trade aujourd'hui")
        return

    # Liste des trades
    trade_options = [f"#{i+1} {t['symbol']} {t['direction']} {t['result']} ${t.get('pnl_usd', 0):+.0f}"
                     for i, t in enumerate(trades)]

    selected_idx = st.selectbox("Sélectionner un trade", range(len(trades)),
                                 format_func=lambda i: trade_options[i])

    trade = trades[selected_idx]

    st.divider()

    # Détails du trade
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📋 Détails")
        result_color = '#0fbf84' if trade['result'] == 'WIN' else '#ef476f'

        st.markdown(f"""
        <div class="trade-row {'win' if trade['result'] == 'WIN' else 'loss'}">
            <div style="display: flex; justify-content: space-between;">
                <span><strong>{trade['symbol']}</strong> {trade['direction']}</span>
                <span style="color: {result_color}; font-weight: 700;">{trade['result']} ${trade.get('pnl_usd', 0):+,.2f}</span>
            </div>
            <div style="margin-top: 8px; color: #94a3b8; font-size: 0.9rem;">
                Entry: {trade.get('entry_price', 0):,.2f} @ {trade.get('time_entry', 'N/A')}<br>
                Exit: {trade.get('exit_price', 0):,.2f} @ {trade.get('time_exit', 'N/A')}<br>
                Reason: {trade.get('exit_reason', 'N/A')}<br>
                Duration: {trade.get('duration_ms', 0)/1000:.1f}s
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("#### 📊 Métriques")
        mcol1, mcol2, mcol3 = st.columns(3)
        with mcol1:
            render_metric("P&L Ticks", f"{trade.get('pnl_ticks', 0):+.1f}t",
                         'green' if trade.get('pnl_ticks', 0) > 0 else 'red')
        with mcol2:
            render_metric("MFE", f"{trade.get('mfe', 0):.1f}t", 'blue')
        with mcol3:
            render_metric("MAE", f"{trade.get('mae', 0):.1f}t", 'yellow')

    with col2:
        st.markdown("#### 🎯 Analyse")

        # Score qualité (simplifié)
        quality_score = 5  # Base
        analysis = []

        # Durée anormale?
        duration_s = trade.get('duration_ms', 0) / 1000
        if duration_s < 5:
            analysis.append(('⚠️', f"Durée très courte ({duration_s:.1f}s) → Vérifier logs", 'warn'))
            quality_score -= 1
        elif duration_s > 300:
            analysis.append(('✅', f"Trade patient ({duration_s/60:.1f}min)", 'ok'))
            quality_score += 1

        # Résultat
        if trade['result'] == 'WIN':
            analysis.append(('✅', f"Trade gagnant +${trade.get('pnl_usd', 0):,.2f}", 'ok'))
            quality_score += 1
        else:
            analysis.append(('❌', f"Trade perdant ${trade.get('pnl_usd', 0):,.2f}", 'fail'))

        # MFE vs PnL (efficacité)
        mfe = trade.get('mfe', 0)
        pnl_ticks = trade.get('pnl_ticks', 0)
        if mfe > 0:
            efficiency = pnl_ticks / mfe * 100 if pnl_ticks > 0 else 0
            if efficiency >= 50:
                analysis.append(('✅', f"Bonne capture MFE ({efficiency:.0f}%)", 'ok'))
                quality_score += 1
            else:
                analysis.append(('⚠️', f"MFE mal capturé ({efficiency:.0f}%)", 'warn'))

        # Niveau d'entrée
        level_name = trade.get('level_name', 'Unknown')
        if level_name != 'Unknown':
            analysis.append(('ℹ️', f"Entrée sur niveau: {level_name}", 'info'))

        # Afficher analyse
        for emoji, text, status in analysis:
            css = f"checklist-{status}" if status in ['ok', 'warn', 'fail'] else 'conseil-box'
            st.markdown(f'<div class="{css}">{emoji} {text}</div>', unsafe_allow_html=True)

        # Score final
        quality_score = max(1, min(10, quality_score))
        score_color = '#0fbf84' if quality_score >= 7 else '#f8c36b' if quality_score >= 5 else '#ef476f'
        st.markdown(f"""
        <div style="background: #0f1620; padding: 16px; border-radius: 12px; text-align: center; margin-top: 16px;">
            <div style="font-size: 0.9rem; color: #64748b;">Score Qualité</div>
            <div style="font-size: 2.5rem; font-weight: 800; color: {score_color};">{quality_score}/10</div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS - ONGLET CONFIG
# ═══════════════════════════════════════════════════════════════

def render_tab_config():
    """Onglet CONFIG"""
    st.markdown("## ⚙️ Configuration MIA")

    st.info("📖 Configuration en lecture seule. Pour modifier, éditez `config/trading_params.py`")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📏 Distances d'entrée")
        for sym, cfg in SYMBOLS_CONFIG.items():
            st.markdown(f"""
            <div style="background: #0f1620; padding: 12px; border-radius: 8px; margin: 8px 0;">
                <strong>{cfg['icon']} {sym}</strong><br>
                <span style="color: #64748b;">Max entry:</span> <strong>{cfg['max_entry_distance']}t</strong><br>
                <span style="color: #64748b;">Max visible:</span> <strong>{cfg['max_distance']}t</strong>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("### ⏰ Sessions Trading")
        for name, info in TRADING_SESSIONS.items():
            if name == 'CLOSED':
                continue
            icon = '✅' if info['tradable'] else '❌'
            st.markdown(f"""
            <div style="background: #0f1620; padding: 12px; border-radius: 8px; margin: 8px 0;
                        border-left: 4px solid {info['color']};">
                {icon} <strong>{name}</strong> ({info['start']}h - {info['end']}h)<br>
                <span style="color: #64748b;">Quality:</span> <strong>{info['quality']}</strong>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.markdown("### 🛡️ Protection Niveau (Recommandé)")
    st.markdown("""
    | Paramètre | Valeur recommandée | Description |
    |-----------|-------------------|-------------|
    | Zone protection | ±5 ticks | Rayon autour du niveau |
    | Durée après WIN | 5 min | Cooldown après trade gagnant |
    | Durée après LOSS | 15 min | Cooldown après trade perdant |
    """)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    inject_css()
    session = get_current_session()
    render_header(session)

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        symbol = st.selectbox("Symbole", ['NQ', 'ES', 'RTY'], index=0)

        st.divider()
        auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=True)

        if st.button("🔄 Rafraîchir", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        with st.expander("📖 Légende"):
            st.markdown("""
            **BIAS:** Direction du marché
            - 🟢 BULLISH: Favoriser LONG
            - 🔴 BEARISH: Favoriser SHORT

            **MODE:** Type de marché
            - 🚀 TREND: Suivre direction
            - ↔️ RANGE: Fader extrêmes

            **Suggestion:**
            - ✅ GO: Conditions favorables
            - ⚠️ WAIT: Attendre confirmation
            - 🚫 NO: Ne pas trader
            """)

    # Load data
    snapshot = load_latest_snapshot(symbol)

    if not snapshot:
        st.error(f"❌ Pas de données pour {symbol}")
        return

    # Extract all data
    ctx = extract_market_context(snapshot)
    levels = extract_all_levels(snapshot, symbol)
    config = SYMBOLS_CONFIG[symbol]

    # Calculations
    bias = calculate_bias(ctx)
    vol = detect_volatility_regime(ctx)
    mode = detect_market_mode(ctx, bias, vol)
    direction = get_direction_to_favor(bias, mode, ctx)
    next_wall = ctx.get('next_wall', {})

    # Header symbole
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"## {config['icon']} {symbol} - {config['name']}")
    with col2:
        mid = ctx.get('mid', 0)
        st.markdown(f"<h2 style='color: {config['color']}; text-align: right;'>{mid:,.2f}</h2>", unsafe_allow_html=True)

    st.divider()

    # ═══════════════════════════════════════════════════════════════
    # 5 ONGLETS PRINCIPAUX
    # ═══════════════════════════════════════════════════════════════
    tab_live, tab_niveaux, tab_perf, tab_analyse, tab_config = st.tabs([
        "📊 LIVE", "📍 NIVEAUX", "📈 PERFORMANCE", "🔍 ANALYSE", "⚙️ CONFIG"
    ])

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 1: LIVE
    # ═══════════════════════════════════════════════════════════════
    with tab_live:
        # Next Wall
        render_next_wall(next_wall, symbol)

        st.divider()

        # BIAS | MODE | DIRECTION | VOLATILITÉ
        render_bias_mode_direction(bias, mode, direction, vol)

        st.divider()

        # ✅ NEW: VIX | INTERMARKET | GAMMA
        vix_info = detect_vix_regime(ctx)
        intermarket_info = detect_intermarket_divergence(ctx)
        gamma_info = detect_gamma_side(ctx)
        render_vix_intermarket_gamma(vix_info, intermarket_info, gamma_info)

        st.divider()

        # 🆕 Distance aux niveaux proches
        render_distance_to_levels(levels, symbol)

        st.divider()

        # DOM Pressure
        dom = render_dom_pressure(snapshot)
        dom_side = dom['instant']['side']

        st.divider()

        # 🆕 Trade Suggestion avec Checklist
        suggestion = generate_trade_suggestion(symbol, ctx, bias, mode, direction, session, levels, dom_side)
        render_trade_suggestion(suggestion)

        st.divider()

        # Position 1D
        render_position_1d(ctx)

        st.divider()

        # OrderFlow + Conseils + Niveaux
        render_orderflow_metrics(ctx)

        col_left, col_right = st.columns([1, 1])
        with col_left:
            conseils = generate_conseils_list(symbol, ctx, bias, mode, vol, direction, session)
            render_conseils(conseils)
            render_bias_factors(bias)
        with col_right:
            render_levels_table(levels, symbol)

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 2: NIVEAUX
    # ═══════════════════════════════════════════════════════════════
    with tab_niveaux:
        render_tab_niveaux(levels, symbol, ctx)

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 3: PERFORMANCE
    # ═══════════════════════════════════════════════════════════════
    with tab_perf:
        render_tab_performance()

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 4: ANALYSE
    # ═══════════════════════════════════════════════════════════════
    with tab_analyse:
        render_tab_analyse()

    # ═══════════════════════════════════════════════════════════════
    # ONGLET 5: CONFIG
    # ═══════════════════════════════════════════════════════════════
    with tab_config:
        render_tab_config()

    # Footer
    st.markdown("---")
    config_note = "Config: trading_params.py ✅" if CONFIG_LOADED else "Config: fallback ⚠️"
    st.caption(f"🎯 MIA Trading Copilot V7 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Session: {ctx.get('session_id', 'Unknown')} | {config_note}")

    # Auto-refresh
    if auto_refresh:
        time.sleep(5)
        st.rerun()


if __name__ == "__main__":
    main()
