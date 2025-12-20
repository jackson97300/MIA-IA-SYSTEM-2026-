#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 MIA TRADING COPILOT - Dashboard Complet pour Trading Manuel
===============================================================

Dashboard Streamlit PRO servant de COPILOTE pour le trading manuel:

📊 FONCTIONNALITÉS:
- Vue d'ensemble multi-symboles (ES, NQ, RTY)
- Niveaux MenthorQ en temps réel avec priorités
- Suggestions LONG/SHORT basées sur proximité niveaux
- Calcul SL/TP automatique basé sur structure
- Checklist de validation avant trade
- Alertes visuelles et warnings
- Contexte marché (session, tendance, corrélation)
- Position dans le range 1D
- Historique des signaux

Version: 3.0 COPILOT (10/12/2025)
Lancer avec: streamlit run mia_trading_copilot.py

Author: MIA System + Claude
"""

import sys
from pathlib import Path

# Ajouter les répertoires au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import time
import math

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION GLOBALE
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="🎯 MIA Trading Copilot",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔴 Configuration symboles - EXACTEMENT ALIGNÉE avec trading_params.py (10/12/2025)
# ⚠️ NE PAS MODIFIER - Source de vérité = config/trading_params.py
SYMBOLS_CONFIG = {
    'ES': {
        'name': 'E-mini S&P 500',
        'tick_size': 0.25,
        'tick_value': 12.50,
        # 📍 DISTANCES (strictes!)
        'max_distance': 15,           # level_proximity_validator.py
        'max_entry_distance': 8,      # MENTHORQ_DISTANCE_CONFIG
        'max_entry_confluence': 13,   # +5 si 3+ niveaux groupés
        # 🛡️ SL/TP
        'sl_buffer_ticks': 3,
        'tp_buffer_ticks': 2,
        'min_sl_ticks': 10,
        'max_sl_ticks': 25,
        'default_sl_ticks': 15,
        'default_tp_ticks': 15,
        'min_rr_ratio': 0.7,
        # 🎨 UI
        'color': '#0fbf84',
        'color_dark': '#0a8f62',
        'icon': '📗',
        'chart_id': 3
    },
    'NQ': {
        'name': 'E-mini NASDAQ',
        'tick_size': 0.25,
        'tick_value': 5.00,
        # 📍 DISTANCES (strictes!)
        'max_distance': 20,           # level_proximity_validator.py
        'max_entry_distance': 10,     # MENTHORQ_DISTANCE_CONFIG (PAS 20!)
        'max_entry_confluence': 15,   # +5 si 3+ niveaux groupés
        # 🛡️ SL/TP
        'sl_buffer_ticks': 5,
        'tp_buffer_ticks': 3,
        'min_sl_ticks': 10,
        'max_sl_ticks': 35,
        'default_sl_ticks': 25,
        'default_tp_ticks': 31,
        'min_rr_ratio': 0.7,
        # 🎨 UI
        'color': '#4a9eff',
        'color_dark': '#2a7edf',
        'icon': '📘',
        'chart_id': 9
    },
    'RTY': {
        'name': 'E-mini Russell 2000',
        'tick_size': 0.10,
        'tick_value': 5.00,
        # 📍 DISTANCES (strictes!)
        'max_distance': 15,           # level_proximity_validator.py
        'max_entry_distance': 12,     # MENTHORQ_DISTANCE_CONFIG
        'max_entry_confluence': 17,   # +5 si 3+ niveaux groupés
        # 🛡️ SL/TP
        'sl_buffer_ticks': 3,
        'tp_buffer_ticks': 3,
        'min_sl_ticks': 20,
        'max_sl_ticks': 60,
        'default_sl_ticks': 30,
        'default_tp_ticks': 40,
        'min_rr_ratio': 1.0,
        # 🎨 UI
        'color': '#ff6b6b',
        'color_dark': '#df4b4b',
        'icon': '📕',
        'chart_id': 1
    }
}

# Mapping mois
MONTH_NAMES = {
    1: "JANVIER", 2: "FEVRIER", 3: "MARS", 4: "AVRIL",
    5: "MAI", 6: "JUIN", 7: "JUILLET", 8: "AOUT",
    9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DECEMBRE"
}


# 🔄 ROLLOVER AUTOMATIQUE
def get_current_contract_month(date = None) -> str:
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


# Configuration niveaux MenthorQ avec priorités
LEVEL_CONFIG = {
    # TIER 1 - CRITIQUES (Priority 95-100)
    'hvl': {'priority': 100, 'emoji': '💎', 'name': 'HVL', 'color': '#FFD700', 'tier': 1},
    'hvl_0dte': {'priority': 98, 'emoji': '🔥', 'name': 'HVL 0DTE', 'color': '#FF4500', 'tier': 1},
    '1d_max': {'priority': 100, 'emoji': '🔺', 'name': '1D MAX', 'color': '#FF0000', 'tier': 1},
    '1d_min': {'priority': 100, 'emoji': '🔻', 'name': '1D MIN', 'color': '#00FF00', 'tier': 1},
    'vah': {'priority': 95, 'emoji': '📊', 'name': 'VAH', 'color': '#FFA500', 'tier': 1},
    'val': {'priority': 95, 'emoji': '📊', 'name': 'VAL', 'color': '#FFA500', 'tier': 1},
    'poc': {'priority': 95, 'emoji': '📊', 'name': 'POC', 'color': '#FFA500', 'tier': 1},

    # TIER 2 - OPTIONS WALLS (Priority 85-94)
    'call_resistance': {'priority': 92, 'emoji': '🔴', 'name': 'Call Wall', 'color': '#FF4444', 'tier': 2},
    'put_support': {'priority': 92, 'emoji': '🟢', 'name': 'Put Wall', 'color': '#44FF44', 'tier': 2},
    'call_resistance_0dte': {'priority': 94, 'emoji': '🔴', 'name': 'Call 0DTE', 'color': '#FF0000', 'tier': 2},
    'put_support_0dte': {'priority': 94, 'emoji': '🟢', 'name': 'Put 0DTE', 'color': '#00FF00', 'tier': 2},
    'gamma_wall_0dte': {'priority': 90, 'emoji': '⚡', 'name': 'Gamma 0DTE', 'color': '#FFD700', 'tier': 2},

    # TIER 3 - GEX & BLIND SPOTS (Priority 75-84)
    'gex': {'priority': 82, 'emoji': '⭐', 'name': 'GEX', 'color': '#9370DB', 'tier': 3},
    'blind_spot': {'priority': 80, 'emoji': '👁️', 'name': 'Blind Spot', 'color': '#4169E1', 'tier': 3},

    # TIER 4 - VWAP (Priority 65-74)
    'vwap': {'priority': 70, 'emoji': '📈', 'name': 'VWAP', 'color': '#808080', 'tier': 4},
    'vwap_up1': {'priority': 68, 'emoji': '📈', 'name': 'VWAP +1σ', 'color': '#808080', 'tier': 4},
    'vwap_dn1': {'priority': 68, 'emoji': '📈', 'name': 'VWAP -1σ', 'color': '#808080', 'tier': 4},
}

# Sessions de trading
TRADING_SESSIONS = {
    'ASIA': {'start': 0, 'end': 8, 'color': '#9370DB', 'quality': 0.6},
    'LONDON': {'start': 8, 'end': 11, 'color': '#4a9eff', 'quality': 0.9},
    'PRE_US': {'start': 11, 'end': 15, 'color': '#808080', 'quality': 0.5},
    'US_OPEN': {'start': 15, 'end': 17, 'color': '#0fbf84', 'quality': 1.0},
    'US_LUNCH': {'start': 17, 'end': 20, 'color': '#f8c36b', 'quality': 0.7},
    'US_POWER': {'start': 20, 'end': 22, 'color': '#0fbf84', 'quality': 1.0},
    'CLOSED': {'start': 22, 'end': 24, 'color': '#ef476f', 'quality': 0.0},
}

REFRESH_INTERVAL = 3

# ═══════════════════════════════════════════════════════════════
# CSS PROFESSIONNEL DARK THEME
# ═══════════════════════════════════════════════════════════════

def inject_css():
    st.markdown("""
    <style>
    /* ═══ GLOBAL DARK THEME ═══ */
    .stApp {
        background: linear-gradient(180deg, #0a0e14 0%, #0f1419 100%);
        color: #e6eef7;
    }

    [data-testid="stSidebar"] {
        background: #0f1419;
        border-right: 1px solid #1e293b;
    }

    /* ═══ MAIN HEADER ═══ */
    .main-header {
        background: linear-gradient(135deg, #0f1419 0%, #1a2332 100%);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
        border: 1px solid #1e293b;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #0fbf84, #4a9eff, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 8px 0;
    }

    .session-badge {
        display: inline-block;
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.9rem;
        margin-right: 12px;
    }

    .session-badge.active {
        background: rgba(15, 191, 132, 0.2);
        border: 2px solid #0fbf84;
        color: #0fbf84;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(15, 191, 132, 0.4); }
        50% { box-shadow: 0 0 0 10px rgba(15, 191, 132, 0); }
    }

    /* ═══ SYMBOL CARDS ═══ */
    .symbol-card {
        background: linear-gradient(135deg, #0f1419 0%, #1a2332 100%);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #1e293b;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        margin-bottom: 16px;
        transition: all 0.3s ease;
    }

    .symbol-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 12px 40px rgba(59, 130, 246, 0.15);
    }

    .symbol-card.has-signal {
        border: 2px solid #0fbf84;
        animation: glow 2s infinite;
    }

    @keyframes glow {
        0%, 100% { box-shadow: 0 0 20px rgba(15, 191, 132, 0.3); }
        50% { box-shadow: 0 0 40px rgba(15, 191, 132, 0.5); }
    }

    .symbol-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 16px;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 16px;
    }

    .symbol-name {
        font-size: 1.5rem;
        font-weight: 700;
    }

    .symbol-price {
        font-size: 2rem;
        font-weight: 800;
        font-family: 'SF Mono', 'Consolas', monospace;
    }

    .price-change {
        font-size: 0.9rem;
        margin-left: 8px;
    }

    .price-change.up { color: #0fbf84; }
    .price-change.down { color: #ef476f; }

    /* ═══ KPI CARDS ═══ */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 12px;
        margin: 16px 0;
    }

    .kpi-card {
        background: #0a0e14;
        border-radius: 12px;
        padding: 14px;
        border: 1px solid #1e293b;
        text-align: center;
        transition: all 0.2s ease;
    }

    .kpi-card:hover {
        border-color: #3b82f6;
        transform: translateY(-2px);
    }

    .kpi-label {
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 6px;
    }

    .kpi-value {
        font-size: 1.3rem;
        font-weight: 700;
        font-family: 'SF Mono', 'Consolas', monospace;
    }

    .kpi-value.success { color: #0fbf84; }
    .kpi-value.danger { color: #ef476f; }
    .kpi-value.warning { color: #f8c36b; }
    .kpi-value.info { color: #4a9eff; }
    .kpi-value.neutral { color: #64748b; }
    .kpi-value.accent { color: #a78bfa; }

    /* ═══ SIGNAL BOX ═══ */
    .signal-box {
        background: linear-gradient(135deg, #0a0e14 0%, #1a2332 100%);
        border-radius: 16px;
        padding: 20px;
        margin: 16px 0;
        border: 2px solid;
        text-align: center;
    }

    .signal-box.long {
        border-color: #0fbf84;
        background: linear-gradient(135deg, rgba(15,191,132,0.05) 0%, rgba(15,191,132,0.1) 100%);
    }

    .signal-box.short {
        border-color: #ef476f;
        background: linear-gradient(135deg, rgba(239,71,111,0.05) 0%, rgba(239,71,111,0.1) 100%);
    }

    .signal-box.neutral {
        border-color: #64748b;
    }

    .signal-direction {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .signal-box.long .signal-direction { color: #0fbf84; }
    .signal-box.short .signal-direction { color: #ef476f; }
    .signal-box.neutral .signal-direction { color: #64748b; }

    .signal-details {
        font-size: 0.9rem;
        color: #94a3b8;
    }

    /* ═══ LEVEL ROWS ═══ */
    .levels-container {
        max-height: 400px;
        overflow-y: auto;
        padding-right: 8px;
    }

    .level-row {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        border-radius: 10px;
        margin: 6px 0;
        background: #0a0e14;
        border: 1px solid #1e293b;
        transition: all 0.2s ease;
    }

    .level-row:hover {
        background: #1a2332;
        border-color: #3b82f6;
    }

    .level-row.tier1 { border-left: 4px solid #FFD700; }
    .level-row.tier2 { border-left: 4px solid #0fbf84; }
    .level-row.tier3 { border-left: 4px solid #4a9eff; }
    .level-row.tier4 { border-left: 4px solid #64748b; }

    .level-row.tradable {
        background: rgba(15, 191, 132, 0.1);
        border-color: #0fbf84;
    }

    .level-emoji { font-size: 1.2rem; width: 30px; }
    .level-name { font-weight: 600; width: 100px; }
    .level-price { font-family: monospace; width: 90px; color: #e6eef7; }
    .level-distance { width: 70px; text-align: right; }
    .level-direction { width: 40px; text-align: center; }

    /* ═══ PILLS / BADGES ═══ */
    .pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 700;
        margin: 2px;
    }

    .pill.tradable {
        background: rgba(15, 191, 132, 0.2);
        border: 1px solid #0fbf84;
        color: #0fbf84;
    }

    .pill.proche {
        background: rgba(248, 195, 107, 0.2);
        border: 1px solid #f8c36b;
        color: #f8c36b;
    }

    .pill.loin {
        background: rgba(239, 71, 111, 0.2);
        border: 1px solid #ef476f;
        color: #ef476f;
    }

    .pill.long {
        background: rgba(15, 191, 132, 0.3);
        color: #0fbf84;
    }

    .pill.short {
        background: rgba(239, 71, 111, 0.3);
        color: #ef476f;
    }

    /* ═══ CHECKLIST ═══ */
    .checklist {
        background: #0a0e14;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #1e293b;
    }

    .checklist-item {
        display: flex;
        align-items: center;
        padding: 8px 0;
        border-bottom: 1px solid #1e293b;
    }

    .checklist-item:last-child {
        border-bottom: none;
    }

    .checklist-icon {
        width: 24px;
        font-size: 1.1rem;
    }

    .checklist-text {
        flex: 1;
        margin-left: 8px;
    }

    .checklist-item.pass .checklist-icon { color: #0fbf84; }
    .checklist-item.fail .checklist-icon { color: #ef476f; }
    .checklist-item.warn .checklist-icon { color: #f8c36b; }

    /* ═══ TRADE SUGGESTION BOX ═══ */
    .trade-suggestion {
        background: linear-gradient(135deg, #0f1419 0%, #1a2332 100%);
        border-radius: 16px;
        padding: 24px;
        margin: 20px 0;
        border: 2px solid #0fbf84;
        box-shadow: 0 0 30px rgba(15, 191, 132, 0.2);
    }

    .trade-suggestion.no-trade {
        border-color: #64748b;
        box-shadow: none;
    }

    .suggestion-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
    }

    .suggestion-title {
        font-size: 1.3rem;
        font-weight: 700;
    }

    .suggestion-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin-top: 16px;
    }

    .suggestion-item {
        text-align: center;
        padding: 12px;
        background: #0a0e14;
        border-radius: 10px;
    }

    .suggestion-label {
        font-size: 0.75rem;
        color: #64748b;
        text-transform: uppercase;
    }

    .suggestion-value {
        font-size: 1.2rem;
        font-weight: 700;
        margin-top: 4px;
    }

    .entry-value { color: #4a9eff; }
    .sl-value { color: #ef476f; }
    .tp-value { color: #0fbf84; }

    /* ═══ ALERTS ═══ */
    .alert-box {
        padding: 16px 20px;
        border-radius: 12px;
        margin: 12px 0;
        border-left: 4px solid;
        display: flex;
        align-items: center;
    }

    .alert-box.success {
        background: rgba(15, 191, 132, 0.1);
        border-color: #0fbf84;
    }

    .alert-box.warning {
        background: rgba(248, 195, 107, 0.1);
        border-color: #f8c36b;
    }

    .alert-box.danger {
        background: rgba(239, 71, 111, 0.1);
        border-color: #ef476f;
    }

    .alert-box.info {
        background: rgba(74, 158, 255, 0.1);
        border-color: #4a9eff;
    }

    .alert-icon {
        font-size: 1.5rem;
        margin-right: 12px;
    }

    .alert-content {
        flex: 1;
    }

    .alert-title {
        font-weight: 700;
        margin-bottom: 4px;
    }

    .alert-text {
        font-size: 0.9rem;
        color: #94a3b8;
    }

    /* ═══ PROGRESS BARS ═══ */
    .progress-container {
        margin: 16px 0;
    }

    .progress-label {
        display: flex;
        justify-content: space-between;
        margin-bottom: 6px;
        font-size: 0.85rem;
    }

    .progress-bar {
        height: 8px;
        background: #1e293b;
        border-radius: 4px;
        overflow: hidden;
    }

    .progress-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }

    .progress-fill.green { background: linear-gradient(90deg, #0fbf84, #10d88d); }
    .progress-fill.red { background: linear-gradient(90deg, #ef476f, #ff5a7d); }
    .progress-fill.yellow { background: linear-gradient(90deg, #f8c36b, #ffd080); }
    .progress-fill.blue { background: linear-gradient(90deg, #4a9eff, #60a8ff); }

    /* ═══ SECTION TITLES ═══ */
    .section-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #e6eef7;
        margin: 20px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 1px solid #1e293b;
        display: flex;
        align-items: center;
    }

    .section-title-icon {
        margin-right: 8px;
    }

    /* ═══ MINI CHART ═══ */
    .mini-chart-container {
        background: #0a0e14;
        border-radius: 12px;
        padding: 12px;
        border: 1px solid #1e293b;
        margin: 12px 0;
    }

    /* ═══ FOOTER ═══ */
    .footer {
        text-align: center;
        padding: 24px;
        color: #64748b;
        font-size: 0.85rem;
        border-top: 1px solid #1e293b;
        margin-top: 40px;
    }

    /* ═══ SCROLLBAR ═══ */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }

    ::-webkit-scrollbar-track {
        background: #0a0e14;
    }

    ::-webkit-scrollbar-thumb {
        background: #1e293b;
        border-radius: 3px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #3b82f6;
    }
    </style>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# DATA LOADING FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def build_snapshot_path(symbol: str, date: Optional[datetime] = None) -> Optional[Path]:
    """Construit le chemin vers le fichier JSONL"""
    if date is None:
        date = datetime.now()

    config = SYMBOLS_CONFIG.get(symbol.upper())
    if not config:
        return None

    chart_id = config['chart_id']
    base_path = Path("DATA_SIERRA_CHART")
    year_dir = f"DATA_{date.year}"
    month_name = MONTH_NAMES.get(date.month, "")
    date_str = date.strftime("%Y%m%d")
    # 🔄 ROLLOVER AUTOMATIQUE
    contract = get_current_contract_month(date)
    filename = f"ml_{symbol.upper()}{contract}_FUT_CME_{chart_id}.jsonl"

    return base_path / year_dir / month_name / date_str / f"CHART_{chart_id}" / "ML_READY" / filename


@st.cache_data(ttl=3)
def load_latest_snapshot(symbol: str) -> Optional[Dict]:
    """Charge le dernier snapshot pour un symbole (cache 3s)"""
    for days_back in range(3):
        date = datetime.now() - timedelta(days=days_back)
        file_path = build_snapshot_path(symbol, date)

        if file_path is None or not file_path.exists():
            continue

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    return json.loads(lines[-1].strip())
        except Exception:
            continue

    return None


def extract_all_levels(snapshot: Dict, symbol: str) -> List[Dict]:
    """Extrait tous les niveaux MenthorQ du snapshot"""
    if not snapshot:
        return []

    levels = []
    current_price = snapshot.get('mid', 0)
    if current_price == 0:
        return []

    config = SYMBOLS_CONFIG[symbol]
    tick_size = config['tick_size']

    # Niveaux uniques
    single_levels = [
        'hvl', 'hvl_0dte', 'vah', 'val', 'poc', '1d_max', '1d_min',
        'call_resistance', 'put_support', 'call_resistance_0dte',
        'put_support_0dte', 'gamma_wall_0dte', 'vwap', 'vwap_up1', 'vwap_dn1'
    ]

    for level_key in single_levels:
        if level_key in snapshot and snapshot[level_key]:
            price = snapshot[level_key]
            if price > 0:
                distance = abs(price - current_price) / tick_size
                level_cfg = LEVEL_CONFIG.get(level_key, LEVEL_CONFIG.get('vwap'))

                # Déterminer le type de support/résistance
                if 'max' in level_key or 'call' in level_key or 'vah' in level_key:
                    level_type = 'resistance'
                elif 'min' in level_key or 'put' in level_key or 'val' in level_key:
                    level_type = 'support'
                else:
                    level_type = 'pivot'

                levels.append({
                    'key': level_key,
                    'name': level_cfg['name'],
                    'price': price,
                    'distance': distance,
                    'priority': level_cfg['priority'],
                    'emoji': level_cfg['emoji'],
                    'color': level_cfg['color'],
                    'tier': level_cfg['tier'],
                    'type': level_type,
                    'direction': 'UP' if price > current_price else 'DOWN'
                })

    # GEX levels (1-10)
    for i in range(1, 11):
        gex_key = f'gex_{i}'
        if gex_key in snapshot and snapshot[gex_key]:
            price = snapshot[gex_key]
            if price > 0:
                distance = abs(price - current_price) / tick_size
                gex_cfg = LEVEL_CONFIG['gex']

                levels.append({
                    'key': gex_key,
                    'name': f'GEX {i}',
                    'price': price,
                    'distance': distance,
                    'priority': gex_cfg['priority'] - i,
                    'emoji': gex_cfg['emoji'],
                    'color': gex_cfg['color'],
                    'tier': gex_cfg['tier'],
                    'type': 'pivot',
                    'direction': 'UP' if price > current_price else 'DOWN'
                })

    # Blind Spots - Snapshot: blind_spot_0 à blind_spot_8 → Affichage: BL 1 à BL 9
    for i in range(9):  # 0 à 8
        bs_key = f'blind_spot_{i}'
        if bs_key in snapshot and snapshot[bs_key]:
            price = snapshot[bs_key]
            if price > 0:
                distance = abs(price - current_price) / tick_size
                bs_cfg = LEVEL_CONFIG['blind_spot']

                levels.append({
                    'key': bs_key,
                    'name': f'BL {i+1}',
                    'price': price,
                    'distance': distance,
                    'priority': bs_cfg['priority'],
                    'emoji': bs_cfg['emoji'],
                    'color': bs_cfg['color'],
                    'tier': bs_cfg['tier'],
                    'type': 'pivot',
                    'direction': 'UP' if price > current_price else 'DOWN'
                })

    # Trier par distance
    levels.sort(key=lambda x: x['distance'])

    return levels


# ═══════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_current_session() -> Dict:
    """Retourne la session de trading actuelle"""
    now = datetime.now()
    hour = now.hour

    for session_name, session_info in TRADING_SESSIONS.items():
        if session_info['start'] <= hour < session_info['end']:
            return {
                'name': session_name,
                'color': session_info['color'],
                'quality': session_info['quality'],
                'tradable': session_info['quality'] >= 0.7
            }

    return {'name': 'CLOSED', 'color': '#ef476f', 'quality': 0, 'tradable': False}


def calculate_1d_position(snapshot: Dict) -> Optional[Dict]:
    """Calcule la position dans le range 1D"""
    if not snapshot:
        return None

    current = snapshot.get('mid', 0)
    day_max = snapshot.get('1d_max', 0)
    day_min = snapshot.get('1d_min', 0)

    if not all([current, day_max, day_min]) or day_max <= day_min:
        return None

    range_size = day_max - day_min
    position_pct = ((current - day_min) / range_size) * 100

    # Déterminer zone
    if position_pct >= 80:
        zone = 'TOP'
        zone_color = '#ef476f'
        bias = 'SHORT'
    elif position_pct <= 20:
        zone = 'BOTTOM'
        zone_color = '#0fbf84'
        bias = 'LONG'
    else:
        zone = 'MIDDLE'
        zone_color = '#f8c36b'
        bias = 'NEUTRAL'

    return {
        'position_pct': position_pct,
        'zone': zone,
        'zone_color': zone_color,
        'bias': bias,
        'day_max': day_max,
        'day_min': day_min,
        'range_size': range_size
    }


def generate_trade_suggestion(symbol: str, snapshot: Dict, levels: List[Dict]) -> Dict:
    """Génère une suggestion de trade basée sur les niveaux"""
    if not snapshot or not levels:
        return {'has_signal': False, 'reason': 'Pas de données'}

    config = SYMBOLS_CONFIG[symbol]
    current_price = snapshot.get('mid', 0)
    tick_size = config['tick_size']
    max_entry = config['max_entry_distance']

    # Trouver les niveaux tradables
    tradable_levels = [l for l in levels if l['distance'] <= max_entry]

    if not tradable_levels:
        return {'has_signal': False, 'reason': f'Aucun niveau à ≤{max_entry}t'}

    # Prendre le niveau le plus proche avec la plus haute priorité
    best_level = max(tradable_levels, key=lambda x: (x['priority'], -x['distance']))

    # Déterminer direction
    if best_level['direction'] == 'DOWN':
        # Prix au-dessus du niveau = potentiel LONG sur rebond
        direction = 'LONG'
        entry = current_price
        sl_level = best_level['price'] - (config['sl_buffer_ticks'] * tick_size)
        sl_distance = abs(entry - sl_level) / tick_size
    else:
        # Prix en-dessous du niveau = potentiel SHORT sur rejet
        direction = 'SHORT'
        entry = current_price
        sl_level = best_level['price'] + (config['sl_buffer_ticks'] * tick_size)
        sl_distance = abs(entry - sl_level) / tick_size

    # Calculer TP basé sur R:R minimum 1.5
    tp_distance = sl_distance * 1.5
    if direction == 'LONG':
        tp = entry + (tp_distance * tick_size)
    else:
        tp = entry - (tp_distance * tick_size)

    # Calculer R:R
    rr_ratio = tp_distance / sl_distance if sl_distance > 0 else 0

    # Score de qualité du setup
    quality_score = 0
    quality_reasons = []

    # +30 si niveau Tier 1
    if best_level['tier'] == 1:
        quality_score += 30
        quality_reasons.append("Niveau Tier 1 (critique)")
    elif best_level['tier'] == 2:
        quality_score += 20
        quality_reasons.append("Niveau Tier 2 (options)")

    # +20 si très proche (<5t)
    if best_level['distance'] <= 5:
        quality_score += 20
        quality_reasons.append(f"Très proche ({best_level['distance']:.1f}t)")
    elif best_level['distance'] <= 10:
        quality_score += 10
        quality_reasons.append(f"Proche ({best_level['distance']:.1f}t)")

    # +15 si bon R:R
    if rr_ratio >= 2.0:
        quality_score += 15
        quality_reasons.append(f"Excellent R:R ({rr_ratio:.1f}:1)")
    elif rr_ratio >= 1.5:
        quality_score += 10
        quality_reasons.append(f"Bon R:R ({rr_ratio:.1f}:1)")

    # +15 si SL raisonnable
    if sl_distance <= config['default_sl_ticks']:
        quality_score += 15
        quality_reasons.append(f"SL serré ({sl_distance:.0f}t)")

    # +10 si session favorable
    session = get_current_session()
    if session['quality'] >= 0.9:
        quality_score += 10
        quality_reasons.append(f"Session {session['name']} favorable")

    # Déterminer grade
    if quality_score >= 70:
        grade = 'A'
        grade_color = '#0fbf84'
    elif quality_score >= 50:
        grade = 'B'
        grade_color = '#4a9eff'
    elif quality_score >= 30:
        grade = 'C'
        grade_color = '#f8c36b'
    else:
        grade = 'D'
        grade_color = '#ef476f'

    return {
        'has_signal': True,
        'direction': direction,
        'entry': entry,
        'sl': sl_level,
        'tp': tp,
        'sl_ticks': sl_distance,
        'tp_ticks': tp_distance,
        'rr_ratio': rr_ratio,
        'level': best_level,
        'quality_score': quality_score,
        'quality_reasons': quality_reasons,
        'grade': grade,
        'grade_color': grade_color
    }


def generate_checklist(symbol: str, snapshot: Dict, suggestion: Dict) -> List[Dict]:
    """Génère une checklist de validation avant trade"""
    checklist = []

    if not suggestion.get('has_signal'):
        return [{'icon': '⚠️', 'text': 'Pas de signal actif', 'status': 'warn'}]

    config = SYMBOLS_CONFIG[symbol]
    session = get_current_session()

    # 1. Session de trading
    if session['quality'] >= 0.9:
        checklist.append({'icon': '✅', 'text': f"Session {session['name']} - Qualité optimale", 'status': 'pass'})
    elif session['quality'] >= 0.7:
        checklist.append({'icon': '✅', 'text': f"Session {session['name']} - Qualité acceptable", 'status': 'pass'})
    else:
        checklist.append({'icon': '❌', 'text': f"Session {session['name']} - Éviter de trader", 'status': 'fail'})

    # 2. Proximité niveau
    level = suggestion.get('level', {})
    distance = level.get('distance', 999)
    if distance <= config['max_entry_distance']:
        checklist.append({'icon': '✅', 'text': f"Niveau {level['name']} à {distance:.1f}t (≤{config['max_entry_distance']}t)", 'status': 'pass'})
    else:
        checklist.append({'icon': '❌', 'text': f"Niveau trop loin: {distance:.1f}t (>{config['max_entry_distance']}t)", 'status': 'fail'})

    # 3. R:R ratio
    rr = suggestion.get('rr_ratio', 0)
    if rr >= 1.5:
        checklist.append({'icon': '✅', 'text': f"R:R ratio {rr:.1f}:1 (≥1.5:1)", 'status': 'pass'})
    else:
        checklist.append({'icon': '⚠️', 'text': f"R:R ratio faible: {rr:.1f}:1 (<1.5:1)", 'status': 'warn'})

    # 4. SL distance
    sl_ticks = suggestion.get('sl_ticks', 0)
    if sl_ticks <= config['default_sl_ticks']:
        checklist.append({'icon': '✅', 'text': f"SL raisonnable: {sl_ticks:.0f}t (≤{config['default_sl_ticks']}t)", 'status': 'pass'})
    else:
        checklist.append({'icon': '⚠️', 'text': f"SL large: {sl_ticks:.0f}t (>{config['default_sl_ticks']}t)", 'status': 'warn'})

    # 5. Tier du niveau
    tier = level.get('tier', 4)
    if tier <= 2:
        checklist.append({'icon': '✅', 'text': f"Niveau Tier {tier} (haute priorité)", 'status': 'pass'})
    else:
        checklist.append({'icon': '⚠️', 'text': f"Niveau Tier {tier} (priorité moyenne)", 'status': 'warn'})

    # 6. Position 1D
    pos_1d = calculate_1d_position(snapshot)
    if pos_1d:
        direction = suggestion.get('direction', '')
        if direction == 'LONG' and pos_1d['zone'] in ['BOTTOM', 'MIDDLE']:
            checklist.append({'icon': '✅', 'text': f"Position 1D favorable pour LONG ({pos_1d['position_pct']:.0f}%)", 'status': 'pass'})
        elif direction == 'SHORT' and pos_1d['zone'] in ['TOP', 'MIDDLE']:
            checklist.append({'icon': '✅', 'text': f"Position 1D favorable pour SHORT ({pos_1d['position_pct']:.0f}%)", 'status': 'pass'})
        else:
            checklist.append({'icon': '⚠️', 'text': f"Position 1D défavorable ({pos_1d['position_pct']:.0f}%)", 'status': 'warn'})

    return checklist


# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

def render_header():
    """Affiche l'en-tête principal"""
    session = get_current_session()

    st.markdown(f"""
    <div class="main-header">
        <h1 class="main-title">🎯 MIA Trading Copilot</h1>
        <div style="display: flex; align-items: center; margin-top: 12px;">
            <span class="session-badge {'active' if session['tradable'] else ''}"
                  style="background: {session['color']}20; border-color: {session['color']}; color: {session['color']};">
                {'🟢' if session['tradable'] else '🔴'} {session['name']}
            </span>
            <span style="color: #64748b; margin-left: 16px;">
                {datetime.now().strftime('%H:%M:%S')} •
                🎯 Entry Max: ES≤8t, NQ≤10t, RTY≤12t (STRICT!)
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_card(label: str, value: str, tone: str = "neutral"):
    """Affiche une KPI card"""
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {tone}">{value}</div>
    </div>
    """, unsafe_allow_html=True)


def render_trade_suggestion_box(symbol: str, suggestion: Dict):
    """Affiche la boîte de suggestion de trade"""
    if not suggestion.get('has_signal'):
        st.markdown(f"""
        <div class="trade-suggestion no-trade">
            <div class="suggestion-header">
                <span class="suggestion-title">💤 Pas de signal actif</span>
            </div>
            <p style="color: #64748b; margin: 0;">{suggestion.get('reason', 'Attendre un niveau tradable')}</p>
        </div>
        """, unsafe_allow_html=True)
        return

    direction = suggestion['direction']
    direction_emoji = '🟢' if direction == 'LONG' else '🔴'
    direction_color = '#0fbf84' if direction == 'LONG' else '#ef476f'

    st.markdown(f"""
    <div class="trade-suggestion">
        <div class="suggestion-header">
            <span class="suggestion-title">
                {direction_emoji} SIGNAL {direction} - {symbol}
            </span>
            <span class="pill" style="background: {suggestion['grade_color']}30; color: {suggestion['grade_color']}; font-size: 1.1rem;">
                Grade {suggestion['grade']} ({suggestion['quality_score']}/100)
            </span>
        </div>

        <p style="color: #94a3b8; margin: 8px 0;">
            📍 Niveau: <strong>{suggestion['level']['emoji']} {suggestion['level']['name']}</strong>
            @ {suggestion['level']['price']:,.2f} ({suggestion['level']['distance']:.1f}t)
        </p>

        <div class="suggestion-grid">
            <div class="suggestion-item">
                <div class="suggestion-label">Entry</div>
                <div class="suggestion-value entry-value">{suggestion['entry']:,.2f}</div>
            </div>
            <div class="suggestion-item">
                <div class="suggestion-label">Stop Loss</div>
                <div class="suggestion-value sl-value">{suggestion['sl']:,.2f}</div>
                <div style="font-size: 0.75rem; color: #64748b;">{suggestion['sl_ticks']:.0f} ticks</div>
            </div>
            <div class="suggestion-item">
                <div class="suggestion-label">Take Profit</div>
                <div class="suggestion-value tp-value">{suggestion['tp']:,.2f}</div>
                <div style="font-size: 0.75rem; color: #64748b;">R:R {suggestion['rr_ratio']:.1f}:1</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_checklist(checklist: List[Dict]):
    """Affiche la checklist de validation"""
    st.markdown('<div class="section-title"><span class="section-title-icon">✅</span> Checklist Validation</div>', unsafe_allow_html=True)

    checklist_html = '<div class="checklist">'
    for item in checklist:
        checklist_html += f"""
        <div class="checklist-item {item['status']}">
            <span class="checklist-icon">{item['icon']}</span>
            <span class="checklist-text">{item['text']}</span>
        </div>
        """
    checklist_html += '</div>'

    st.markdown(checklist_html, unsafe_allow_html=True)


def render_levels_table(levels: List[Dict], symbol: str):
    """Affiche le tableau des niveaux"""
    config = SYMBOLS_CONFIG[symbol]
    max_entry = config['max_entry_distance']
    max_distance = config['max_distance']

    st.markdown('<div class="section-title"><span class="section-title-icon">📊</span> Niveaux MenthorQ</div>', unsafe_allow_html=True)

    html = '<div class="levels-container">'

    for level in levels[:15]:  # Top 15
        # Déterminer le status
        if level['distance'] <= max_entry:
            status_class = 'tradable'
            status_pill = f'<span class="pill tradable">{level["distance"]:.1f}t ✓</span>'
        elif level['distance'] <= max_distance:
            status_class = ''
            status_pill = f'<span class="pill proche">{level["distance"]:.1f}t</span>'
        else:
            status_class = ''
            status_pill = f'<span class="pill loin">{level["distance"]:.1f}t</span>'

        direction_arrow = '🔼' if level['direction'] == 'UP' else '🔽'

        html += f"""
        <div class="level-row tier{level['tier']} {status_class}">
            <span class="level-emoji">{level['emoji']}</span>
            <span class="level-name">{level['name']}</span>
            <span class="level-price">{level['price']:,.2f}</span>
            <span class="level-direction">{direction_arrow}</span>
            <span class="level-distance">{status_pill}</span>
        </div>
        """

    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_1d_position(snapshot: Dict, symbol: str):
    """Affiche la position dans le range 1D"""
    pos = calculate_1d_position(snapshot)

    if not pos:
        return

    st.markdown('<div class="section-title"><span class="section-title-icon">📏</span> Position 1D Range</div>', unsafe_allow_html=True)

    # Barre de progression
    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-label">
            <span>1D MIN: {pos['day_min']:,.2f}</span>
            <span style="color: {pos['zone_color']}; font-weight: 700;">{pos['zone']} ({pos['position_pct']:.0f}%)</span>
            <span>1D MAX: {pos['day_max']:,.2f}</span>
        </div>
        <div class="progress-bar">
            <div class="progress-fill {'green' if pos['position_pct'] < 30 else 'red' if pos['position_pct'] > 70 else 'yellow'}"
                 style="width: {pos['position_pct']}%;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Suggestion basée sur position
    if pos['bias'] != 'NEUTRAL':
        bias_emoji = '🟢' if pos['bias'] == 'LONG' else '🔴'
        st.markdown(f"""
        <div class="alert-box info">
            <span class="alert-icon">{bias_emoji}</span>
            <div class="alert-content">
                <div class="alert-title">Biais {pos['bias']}</div>
                <div class="alert-text">Position {pos['zone']} du range 1D suggère potentiel {pos['bias']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_symbol_full(symbol: str, snapshot: Dict, levels: List[Dict]):
    """Affiche la vue complète pour un symbole"""
    config = SYMBOLS_CONFIG[symbol]

    if not snapshot:
        st.warning(f"⚠️ Pas de données pour {symbol}")
        return

    current_price = snapshot.get('mid', 0)

    # Calculer stats
    tradable_count = len([l for l in levels if l['distance'] <= config['max_entry_distance']])
    proche_count = len([l for l in levels if config['max_entry_distance'] < l['distance'] <= config['max_distance']])

    # Générer suggestion
    suggestion = generate_trade_suggestion(symbol, snapshot, levels)
    checklist = generate_checklist(symbol, snapshot, suggestion)

    # Header symbole
    has_signal_class = 'has-signal' if suggestion.get('has_signal') else ''

    st.markdown(f"""
    <div class="symbol-card {has_signal_class}">
        <div class="symbol-header">
            <div>
                <span class="symbol-name" style="color: {config['color']};">
                    {config['icon']} {symbol}
                </span>
                <span style="color: #64748b; font-size: 0.9rem; margin-left: 12px;">
                    {config['name']}
                </span>
            </div>
            <div>
                <span class="symbol-price" style="color: {config['color']};">
                    {current_price:,.2f}
                </span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # KPIs row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_kpi_card("Tradables", str(tradable_count),
                       "success" if tradable_count > 0 else "danger")
    with col2:
        render_kpi_card("Proches", str(proche_count),
                       "warning" if proche_count > 0 else "neutral")
    with col3:
        if levels:
            nearest = levels[0]
            render_kpi_card("Plus proche", f"{nearest['name']} ({nearest['distance']:.1f}t)",
                           "success" if nearest['distance'] <= config['max_entry_distance'] else "warning")
    with col4:
        atr = snapshot.get('atr', 0)
        render_kpi_card("ATR", f"{atr:.2f}", "info")

    # Deux colonnes: Suggestion + Checklist | Niveaux
    col_left, col_right = st.columns([1, 1])

    with col_left:
        render_trade_suggestion_box(symbol, suggestion)
        render_checklist(checklist)
        render_1d_position(snapshot, symbol)

    with col_right:
        render_levels_table(levels, symbol)


def render_multi_symbol_overview(all_data: Dict):
    """Affiche la vue d'ensemble multi-symboles"""
    st.markdown('<div class="section-title"><span class="section-title-icon">🎯</span> Vue d\'ensemble</div>', unsafe_allow_html=True)

    cols = st.columns(3)

    for i, (symbol, data) in enumerate(all_data.items()):
        with cols[i]:
            config = SYMBOLS_CONFIG[symbol]
            snapshot = data.get('snapshot')
            levels = data.get('levels', [])

            if not snapshot:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">{config['icon']} {symbol}</div>
                    <div class="kpi-value danger">No Data</div>
                </div>
                """, unsafe_allow_html=True)
                continue

            price = snapshot.get('mid', 0)
            tradable = len([l for l in levels if l['distance'] <= config['max_entry_distance']])
            nearest = levels[0] if levels else None

            # Déterminer si signal
            suggestion = generate_trade_suggestion(symbol, snapshot, levels)
            signal_badge = ""
            if suggestion.get('has_signal'):
                direction = suggestion['direction']
                signal_badge = f'<span class="pill {direction.lower()}">{direction}</span>'

            st.markdown(f"""
            <div class="symbol-card" style="padding: 16px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                    <span style="font-size: 1.2rem; font-weight: 700; color: {config['color']};">
                        {config['icon']} {symbol}
                    </span>
                    {signal_badge}
                </div>
                <div style="font-size: 1.8rem; font-weight: 800; color: {config['color']}; margin-bottom: 8px;">
                    {price:,.2f}
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.85rem; color: #64748b;">
                    <span>Tradables: <strong style="color: {'#0fbf84' if tradable > 0 else '#ef476f'};">{tradable}</strong></span>
                    <span>Proche: <strong>{nearest['name'] if nearest else 'N/A'}</strong> ({nearest['distance']:.1f}t if nearest else '')</span>
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_alerts_global(all_data: Dict):
    """Affiche les alertes globales"""
    alerts = []

    for symbol, data in all_data.items():
        levels = data.get('levels', [])
        snapshot = data.get('snapshot')

        if not levels or not snapshot:
            continue

        config = SYMBOLS_CONFIG[symbol]
        suggestion = generate_trade_suggestion(symbol, snapshot, levels)

        if suggestion.get('has_signal') and suggestion.get('quality_score', 0) >= 50:
            alerts.append({
                'type': 'success',
                'icon': '🎯',
                'title': f"{config['icon']} {symbol} - Signal {suggestion['direction']}",
                'text': f"Grade {suggestion['grade']} | {suggestion['level']['name']} @ {suggestion['level']['distance']:.1f}t | R:R {suggestion['rr_ratio']:.1f}:1"
            })

    # Session warning si non tradable
    session = get_current_session()
    if not session['tradable']:
        alerts.insert(0, {
            'type': 'warning',
            'icon': '⚠️',
            'title': f"Session {session['name']}",
            'text': "Session à faible qualité - Trading déconseillé"
        })

    if not alerts:
        alerts.append({
            'type': 'info',
            'icon': '💤',
            'title': 'Aucun signal actif',
            'text': 'Attendre que le prix s\'approche d\'un niveau clé'
        })

    for alert in alerts:
        st.markdown(f"""
        <div class="alert-box {alert['type']}">
            <span class="alert-icon">{alert['icon']}</span>
            <div class="alert-content">
                <div class="alert-title">{alert['title']}</div>
                <div class="alert-text">{alert['text']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════

def main():
    inject_css()
    render_header()

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")

        view_mode = st.radio(
            "Mode d'affichage",
            ["🎯 Vue unique (détaillée)", "📊 Multi-symboles"],
            index=0
        )

        if "Vue unique" in view_mode:
            selected_symbol = st.selectbox(
                "Symbole principal",
                ['NQ', 'ES', 'RTY'],
                index=0
            )
        else:
            selected_symbols = st.multiselect(
                "Symboles",
                ['ES', 'NQ', 'RTY'],
                default=['ES', 'NQ', 'RTY']
            )

        st.markdown("---")

        auto_refresh = st.checkbox("🔄 Auto-refresh (3s)", value=True)

        if st.button("🔄 Rafraîchir maintenant", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")

        with st.expander("📚 Guide rapide"):
            st.markdown("""
            **🎯 Interprétation des signaux:**
            - **Grade A** (≥70): Excellent setup
            - **Grade B** (≥50): Bon setup
            - **Grade C** (≥30): Setup moyen
            - **Grade D** (<30): Éviter

            **✅ Checklist verte = GO**
            - Tous les critères validés
            - Session favorable
            - Niveau proche

            **⚠️ Attention si:**
            - Session ASIA/Lunch
            - R:R < 1.5
            - Niveau Tier 3-4

            **📊 Tiers des niveaux:**
            - T1: HVL, VAH/VAL, 1D Max/Min
            - T2: Call/Put Walls, Gamma
            - T3: GEX, Blind Spots
            - T4: VWAP
            """)

        with st.expander("⚙️ Config RÉELLES du Bot (10/12)"):
            st.markdown("""
            ### 📍 Distances Entry (STRICTES!)
            | Symbole | Entry Max | +Confluence | Proximity |
            |---------|-----------|-------------|-----------|
            | **ES** | **8t** | 13t | 15t |
            | **NQ** | **10t** | 15t | 20t |
            | **RTY** | **12t** | 17t | 15t |

            ### 🛡️ SL/TP Config
            | Symbole | SL | TP | R:R Min |
            |---------|----|----|---------|
            | ES | 15t | 15t | 0.7 |
            | NQ | 25t | 31t | 0.7 |
            | RTY | 30t | 40t | 1.0 |

            ⚠️ **Config stricte = moins de trades mais meilleure qualité!**
            """)

    # Main content
    if "Vue unique" in view_mode:
        # Vue détaillée pour un symbole
        snapshot = load_latest_snapshot(selected_symbol)
        levels = extract_all_levels(snapshot, selected_symbol) if snapshot else []

        render_symbol_full(selected_symbol, snapshot, levels)

    else:
        # Vue multi-symboles
        all_data = {}
        for symbol in selected_symbols:
            snapshot = load_latest_snapshot(symbol)
            levels = extract_all_levels(snapshot, symbol) if snapshot else []
            all_data[symbol] = {'snapshot': snapshot, 'levels': levels}

        # Alertes globales
        render_alerts_global(all_data)

        # Vue d'ensemble
        render_multi_symbol_overview(all_data)

        # Détails par symbole
        st.markdown("---")

        for symbol in selected_symbols:
            with st.expander(f"{SYMBOLS_CONFIG[symbol]['icon']} {symbol} - Détails", expanded=False):
                render_symbol_full(symbol, all_data[symbol]['snapshot'], all_data[symbol]['levels'])

    # Footer
    st.markdown(f"""
    <div class="footer">
        🎯 MIA Trading Copilot v3.0 •
        Corrections 10/12/2025 appliquées •
        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </div>
    """, unsafe_allow_html=True)

    # Auto-refresh
    if auto_refresh:
        time.sleep(REFRESH_INTERVAL)
        st.rerun()


if __name__ == "__main__":
    main()
