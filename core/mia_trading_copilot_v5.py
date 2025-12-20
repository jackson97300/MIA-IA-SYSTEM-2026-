#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 MIA TRADING COPILOT V5 - UTILISE TOUTES LES DONNÉES DU SNAPSHOT
═══════════════════════════════════════════════════════════════════

✅ VERSION V5 - DONNÉES COMPLÈTES:
- NEXT_WALL (donnée la plus importante!)
- Position 1D avec bias automatique
- MIA Bullish Score + OrderFlow + Smart Money
- Régime de volatilité (atr_ratio)
- Données intermarkets (divergence ES/NQ)
- DOM imbalance et depth
- Tous les niveaux MenthorQ

Version: 5.0 (10/12/2025)
Lancer: streamlit run mia_trading_copilot_v5.py

Author: MIA System + Claude
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional
import time
import re
import os

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="🎯 MIA Copilot V5",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

SYMBOLS_CONFIG = {
    'ES': {'name': 'E-mini S&P 500', 'tick_size': 0.25, 'tick_value': 12.50,
           'max_entry_distance': 8, 'max_distance': 15, 'color': '#0fbf84', 'icon': '📗', 'chart_id': 3},
    'NQ': {'name': 'E-mini NASDAQ', 'tick_size': 0.25, 'tick_value': 5.00,
           'max_entry_distance': 10, 'max_distance': 20, 'color': '#4a9eff', 'icon': '📘', 'chart_id': 9},
    'RTY': {'name': 'E-mini Russell 2000', 'tick_size': 0.10, 'tick_value': 5.00,
            'max_entry_distance': 12, 'max_distance': 15, 'color': '#ff6b6b', 'icon': '📕', 'chart_id': 1},
}

MONTH_NAMES = {1: "JANVIER", 2: "FEVRIER", 3: "MARS", 4: "AVRIL", 5: "MAI", 6: "JUIN",
               7: "JUILLET", 8: "AOUT", 9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DECEMBRE"}


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


TRADING_SESSIONS = {
    'LONDON': {'start': 8, 'end': 11, 'quality': 0.9, 'tradable': True, 'color': '#4a9eff'},
    'TRANSITION': {'start': 11, 'end': 15, 'quality': 0.4, 'tradable': False, 'color': '#808080'},
    'US_MORNING': {'start': 15, 'end': 17, 'quality': 1.0, 'tradable': True, 'color': '#0fbf84'},
    'LUNCH_BLOCK': {'start': 17, 'end': 20, 'quality': 0.5, 'tradable': False, 'color': '#f8c36b'},
    'US_POWER': {'start': 20, 'end': 22, 'quality': 1.0, 'tradable': True, 'color': '#0fbf84'},
    'CLOSED': {'start': 22, 'end': 8, 'quality': 0.0, 'tradable': False, 'color': '#ef476f'},
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

    .badge {
        display: inline-block; padding: 4px 12px; border-radius: 12px;
        font-weight: 600; font-size: 0.8rem; margin: 2px;
    }
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
                        return json.loads(lines[-1].strip())
            except:
                continue
    return None

# ═══════════════════════════════════════════════════════════════
# EXTRACT ALL DATA FROM SNAPSHOT
# ═══════════════════════════════════════════════════════════════

def extract_market_context(snapshot: Dict) -> Dict:
    """Extrait TOUTES les données de contexte du snapshot"""
    if not snapshot:
        return {}

    mid = snapshot.get('mid', 0)

    return {
        # Prix de base
        'mid': mid,
        'spread_ticks': snapshot.get('spread_ticks', 0),
        'atr': snapshot.get('atr', 0),

        # VWAP
        'vwap': snapshot.get('vwap', mid),
        'd_vwap_ticks': snapshot.get('d_vwap_ticks', 0),
        'vwap_weekly': snapshot.get('vwap_weekly', mid),
        'd_vwap_weekly_ticks': snapshot.get('d_vwap_weekly_ticks', 0),

        # Position 1D
        '1d_max': snapshot.get('1d_max', 0),
        '1d_min': snapshot.get('1d_min', 0),
        'position_in_range': snapshot.get('position_in_range', 50),
        'distance_to_high_pct': snapshot.get('distance_to_high_pct', 0),
        'distance_to_low_pct': snapshot.get('distance_to_low_pct', 0),

        # BIAS indicators
        'mia_bullish_score': snapshot.get('mia_bullish_score', 0.5),
        'deltaPct': snapshot.get('deltaPct', 0),
        'smart_money_flow': snapshot.get('smart_money_flow', 0),
        'institutional_pressure': snapshot.get('institutional_pressure', 0),

        # Volatilité
        'volatility_regime': snapshot.get('volatility_regime', 1),
        'volatility_regime5': snapshot.get('volatility_regime5', 2),
        'atr_ratio': snapshot.get('atr_ratio', 1),

        # OrderFlow
        'cum_delta_session': snapshot.get('cum_delta_session', 0),
        'delta': snapshot.get('delta', 0),
        'askPct': snapshot.get('askPct', 0.5),
        'bidPct': snapshot.get('bidPct', 0.5),
        'sell_pct': snapshot.get('sell_pct', 0.5),
        'buy_pct': snapshot.get('buy_pct', 0.5),

        # DOM
        'depth_imbalance': snapshot.get('depth_imbalance', 0),
        'dom_features': snapshot.get('dom_features', {}),
        'ob_center': snapshot.get('ob_center', 0),

        # Session
        'session_id': snapshot.get('session_id', 'Unknown'),
        'session_progress': snapshot.get('session_progress', 0),

        # Intermarkets
        'intermarkets': snapshot.get('intermarkets', {}),
        'vix': snapshot.get('vix', 0),

        # Value Area
        'vva': snapshot.get('vva', {}),
        'in_value_area': snapshot.get('in_value_area', False),

        # Gamma
        'gamma_side': snapshot.get('gamma_side', 'neutral'),
        'gamma_wall_level': snapshot.get('gamma_wall_level', 0),

        # 🔥 NEXT WALL - LE PLUS IMPORTANT!
        'next_wall': snapshot.get('next_wall', {}),

        # Confluence
        'confluence_density': snapshot.get('confluence_density', 0),
        'confluence_strength': snapshot.get('confluence_strength', 0),

        # Momentum
        'tick_momentum': snapshot.get('tick_momentum', 0),
        'delta_burst': snapshot.get('delta_burst', 0),
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
        'hvl': ('💎', 'HVL', 1, 'MAGNET'),
        'hvl_0dte': ('🔥', 'HVL 0DTE', 1, 'MAGNET'),
        '1d_max': ('🔺', '1D MAX', 1, 'RESISTANCE'),
        '1d_min': ('🔻', '1D MIN', 1, 'SUPPORT'),
        'call_resistance': ('🔴', 'Call Wall', 2, 'RESISTANCE'),
        'put_support': ('🟢', 'Put Wall', 2, 'SUPPORT'),
        'call_resistance_0dte': ('🔴', 'Call 0DTE', 2, 'RESISTANCE'),
        'put_support_0dte': ('🟢', 'Put 0DTE', 2, 'SUPPORT'),
        'gamma_wall_0dte': ('⚡', 'Gamma 0DTE', 2, 'MAGNET'),
        'vwap': ('📈', 'VWAP', 4, 'PIVOT'),
        'vwap_up1': ('📈', 'VWAP +1σ', 4, 'RESISTANCE'),
        'vwap_dn1': ('📈', 'VWAP -1σ', 4, 'SUPPORT'),
    }

    for key, (emoji, name, tier, behavior) in level_map.items():
        price = snapshot.get(key, 0)
        if price and price > 0:
            distance = abs(price - mid) / tick_size
            levels.append({
                'key': key, 'name': name, 'price': price, 'distance': distance,
                'emoji': emoji, 'tier': tier, 'behavior': behavior,
                'direction': 'UP' if price > mid else 'DOWN'
            })

    # VAH/VAL/VPOC depuis vva
    vva = snapshot.get('vva', {})
    if vva:
        for key, name, behavior in [('vah', 'VAH', 'RESISTANCE'), ('val', 'VAL', 'SUPPORT'), ('vpoc', 'VPOC', 'PIVOT')]:
            price = vva.get(key, 0)
            if price and price > 0:
                distance = abs(price - mid) / tick_size
                levels.append({
                    'key': key, 'name': name, 'price': price, 'distance': distance,
                    'emoji': '📊', 'tier': 1, 'behavior': behavior,
                    'direction': 'UP' if price > mid else 'DOWN'
                })

    # GEX 1-10
    for i in range(1, 11):
        price = snapshot.get(f'gex_{i}', 0)
        if price and price > 0:
            distance = abs(price - mid) / tick_size
            levels.append({
                'key': f'gex_{i}', 'name': f'GEX {i}', 'price': price, 'distance': distance,
                'emoji': '⭐', 'tier': 3, 'behavior': 'PIVOT',
                'direction': 'UP' if price > mid else 'DOWN'
            })

    # Blind Spots - Snapshot: blind_spot_0 à blind_spot_8 → Affichage: BL 1 à BL 9
    for i in range(9):  # 0 à 8
        price = snapshot.get(f'blind_spot_{i}', 0)
        if price and price > 0:
            distance = abs(price - mid) / tick_size
            levels.append({
                'key': f'blind_spot_{i}', 'name': f'BL {i+1}', 'price': price, 'distance': distance,
                'emoji': '👁️', 'tier': 3, 'behavior': 'FAST_MOVE',
                'direction': 'UP' if price > mid else 'DOWN'
            })

    levels.sort(key=lambda x: x['distance'])
    return levels

# ═══════════════════════════════════════════════════════════════
# ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def get_current_session() -> Dict:
    hour = datetime.now().hour
    for name, info in TRADING_SESSIONS.items():
        if info['start'] <= hour < info['end']:
            return {'name': name, **info}
    return {'name': 'CLOSED', 'quality': 0, 'tradable': False, 'color': '#ef476f'}


def calculate_bias(ctx: Dict) -> Dict:
    """Calcule le BIAS à partir de TOUTES les données du snapshot"""
    score = 0.0
    factors = []

    # 1. Position 1D (30%) - LE PLUS IMPORTANT
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

    # Déterminer le bias final
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
        'bias': bias,
        'score': score,
        'emoji': emoji,
        'color': color,
        'confidence': min(abs(score) * 2, 1.0),
        'factors': factors
    }


def detect_volatility_regime(ctx: Dict) -> Dict:
    """Détecte le régime de volatilité"""
    atr_ratio = ctx.get('atr_ratio', 1)
    vol_regime = ctx.get('volatility_regime', 1)

    if atr_ratio >= 20:
        regime = 'EXTREME'
        emoji = '🔥'
        color = '#ef476f'
        conseil = "⚠️ VOLATILITÉ EXTRÊME! Réduire taille. Élargir stops. Risque élevé."
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
        conseil = "💤 Volatilité faible. Range possible. Attendre expansion."

    return {
        'regime': regime,
        'atr_ratio': atr_ratio,
        'emoji': emoji,
        'color': color,
        'conseil': conseil
    }


def detect_market_mode(ctx: Dict, bias: Dict, vol: Dict) -> Dict:
    """Détecte le MODE de marché"""
    pos = ctx.get('position_in_range', 50)
    bullish = ctx.get('mia_bullish_score', 0.5)
    trend_strength = abs(bullish - 0.5) * 2

    # Priorité volatilité extrême
    if vol['regime'] == 'EXTREME':
        return {
            'mode': 'VOLATILITY', 'emoji': '🔥', 'color': '#ef476f',
            'direction': 'FOLLOW', 'trade_es': True, 'trade_nq': True,
            'conseil': "🔥 VOLATILITÉ EXTRÊME - Suivre momentum ou attendre."
        }

    # Trend détecté
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

    # Range
    if vol['regime'] == 'LOW' or trend_strength < 0.15:
        return {
            'mode': 'RANGE', 'emoji': '↔️', 'color': '#4a9eff',
            'direction': 'FADE', 'trade_es': False, 'trade_nq': True,
            'conseil': "↔️ RANGE - Fader extrêmes. ⚠️ ES éviter en RANGE."
        }

    # Par défaut
    return {
        'mode': 'MIXED', 'emoji': '🔄', 'color': '#f8c36b',
        'direction': 'CAREFUL', 'trade_es': True, 'trade_nq': True,
        'conseil': "🔄 Conditions mixtes - Attendre signal clair."
    }


def get_direction_to_favor(bias: Dict, mode: Dict, ctx: Dict) -> Dict:
    """Direction à favoriser"""

    # Mode RANGE = direction opposée à position
    if mode['mode'] == 'RANGE':
        pos = ctx.get('position_in_range', 50)
        if pos >= 70:
            return {'direction': 'SHORT', 'emoji': '🔴', 'color': '#ef476f',
                    'strength': 0.7, 'conseil': "Position haute en RANGE → SHORT favorisé"}
        elif pos <= 30:
            return {'direction': 'LONG', 'emoji': '🟢', 'color': '#0fbf84',
                    'strength': 0.7, 'conseil': "Position basse en RANGE → LONG favorisé"}

    # Mode TREND = suivre le trend
    if mode['direction'] in ['LONG', 'SHORT']:
        return {'direction': mode['direction'],
                'emoji': '🟢' if mode['direction'] == 'LONG' else '🔴',
                'color': '#0fbf84' if mode['direction'] == 'LONG' else '#ef476f',
                'strength': 0.8, 'conseil': f"Mode TREND → {mode['direction']} favorisé"}

    # Utiliser le bias
    if bias['bias'] != 'NEUTRAL':
        direction = 'LONG' if bias['bias'] == 'BULLISH' else 'SHORT'
        return {'direction': direction,
                'emoji': bias['emoji'], 'color': bias['color'],
                'strength': bias['confidence'],
                'conseil': f"Bias {bias['bias']} → {direction} favorisé"}

    return {'direction': 'BOTH', 'emoji': '⚪', 'color': '#64748b',
            'strength': 0.3, 'conseil': "Pas de direction claire - Attendre signal"}


def generate_conseils(symbol: str, ctx: Dict, bias: Dict, mode: Dict, vol: Dict,
                      direction: Dict, session: Dict, levels: List[Dict], next_wall: Dict) -> List[Dict]:
    """Génère les conseils dynamiques"""
    conseils = []

    # 1. Session
    if not session['tradable']:
        conseils.append({'type': 'warning', 'text': f"⚠️ SESSION {session['name']}: Non tradable. ÉVITER."})
    else:
        conseils.append({'type': 'success', 'text': f"✅ SESSION {session['name']}: Bonne pour trader."})

    # 2. Volatilité
    if vol['regime'] in ['EXTREME', 'HIGH']:
        conseils.append({'type': 'warning', 'text': vol['conseil']})

    # 3. Mode
    conseils.append({'type': 'info', 'text': mode['conseil']})

    # 4. Symbole ES en RANGE
    if symbol == 'ES' and mode['mode'] == 'RANGE':
        conseils.append({'type': 'warning', 'text': "⚠️ ES underperforms en RANGE. Préférer NQ."})

    # 5. Direction
    conseils.append({'type': 'info', 'text': f"🎯 {direction['conseil']}"})

    # 6. Next Wall (LE PLUS IMPORTANT!)
    if next_wall and next_wall.get('price'):
        dist = abs(next_wall.get('dist_ticks', 999))
        side = next_wall.get('side', 'unknown').upper()
        strength = next_wall.get('strength', 0)
        config = SYMBOLS_CONFIG[symbol]

        if dist <= config['max_entry_distance']:
            conseils.append({'type': 'success',
                'text': f"🔥 NEXT WALL TRADABLE: {side} @ {dist:.0f}t (Force: {strength:.0%})"})
        elif dist <= config['max_distance']:
            conseils.append({'type': 'info',
                'text': f"📍 Next Wall proche: {side} @ {dist:.0f}t - Surveiller approche"})

    # 7. Niveaux
    config = SYMBOLS_CONFIG[symbol]
    tradable = [l for l in levels if l['distance'] <= config['max_entry_distance']]
    if tradable:
        best = tradable[0]
        conseils.append({'type': 'success',
            'text': f"🎯 NIVEAU TRADABLE: {best['emoji']} {best['name']} @ {best['distance']:.1f}t ({best['behavior']})"})
    else:
        proche = [l for l in levels if l['distance'] <= config['max_distance']]
        if proche:
            best = proche[0]
            conseils.append({'type': 'info',
                'text': f"⏳ Niveau proche: {best['emoji']} {best['name']} @ {best['distance']:.1f}t - Attendre"})
        else:
            conseils.append({'type': 'warning',
                'text': "💤 Aucun niveau proche. Attendre que le prix s'approche."})

    # 8. Intermarkets
    intermarkets = ctx.get('intermarkets', {})
    if intermarkets.get('divergence_flag', 0) == 1:
        conseils.append({'type': 'warning', 'text': "⚠️ DIVERGENCE ES/NQ détectée! Prudence."})

    return conseils

# ═══════════════════════════════════════════════════════════════
# UI COMPONENTS
# ═══════════════════════════════════════════════════════════════

def render_header(session: Dict):
    icon = '🟢' if session['tradable'] else '🔴'
    st.markdown(f"""
    <div class="main-header">
        <div class="main-title">🎯 MIA Trading Copilot V5</div>
        <div style="margin-top: 8px; color: #94a3b8;">
            <span class="badge" style="background: {session['color']}40; border: 1px solid {session['color']}; color: {session['color']};">
                {icon} {session['name']}
            </span>
            <span style="margin-left: 12px;">{datetime.now().strftime('%H:%M:%S')}</span>
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
    """Affiche le NEXT WALL - L'info la plus importante!"""
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

    # Couleur selon side
    if side == 'PUT':
        side_color = '#0fbf84'
        side_emoji = '🟢'
        action = "SUPPORT - Rebond attendu"
    else:
        side_color = '#ef476f'
        side_emoji = '🔴'
        action = "RESISTANCE - Rejet attendu"

    # Status selon distance
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
        <div style="font-size: 1rem; color: #f8c36b; margin-bottom: 8px;">🎯 NEXT WALL (données temps réel)</div>
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
            <div style="font-size: 0.8rem; color: #64748b;">ATR Ratio: {vol['atr_ratio']:.1f}</div>
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
        st.markdown(f"<center><strong style='color: {zone_color};'>{zone} ({pos:.0f}%)</strong></center>",
                    unsafe_allow_html=True)
    with col3:
        st.caption(f"MAX\n{day_max:,.0f}")


def render_bias_factors(bias: Dict):
    """Détails du calcul du bias"""
    with st.expander("📊 Détails calcul BIAS"):
        for emoji, text in bias['factors']:
            st.write(f"{emoji} {text}")


def render_conseils(conseils: List[Dict]):
    """Affiche les conseils"""
    st.markdown("### 💡 Conseils Trading")
    for c in conseils:
        css_class = c['type'] + '-box'
        st.markdown(f'<div class="{css_class}">{c["text"]}</div>', unsafe_allow_html=True)


def render_levels_table(levels: List[Dict], symbol: str):
    """Tableau des niveaux"""
    st.markdown("### 📊 Niveaux MenthorQ")

    config = SYMBOLS_CONFIG[symbol]
    if not levels:
        st.info("Aucun niveau disponible")
        return

    data = []
    for l in levels[:15]:
        if l['distance'] <= config['max_entry_distance']:
            status = "✅ TRADABLE"
        elif l['distance'] <= config['max_distance']:
            status = "⚠️ Proche"
        else:
            status = "❌ Loin"

        data.append({
            "": l['emoji'],
            "Niveau": l['name'],
            "Prix": f"{l['price']:,.2f}",
            "↕": "🔼" if l['direction'] == 'UP' else "🔽",
            "Dist": f"{l['distance']:.1f}t",
            "Status": status,
            "Type": l['behavior']
        })

    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


def render_orderflow_metrics(ctx: Dict):
    """Métriques OrderFlow"""
    st.markdown("### 📈 OrderFlow & Market Data")

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


# ═══════════════════════════════════════════════════════════════
# 🎯 DOM PRESSURE ANALYSIS - QUI A LA MAIN?
# ═══════════════════════════════════════════════════════════════

# Historique pour le lissage EMA
if 'dom_history' not in st.session_state:
    st.session_state.dom_history = []
    st.session_state.ema_score = 0.0

def calculate_dom_pressure(snapshot: Dict) -> Dict:
    """
    Calcule la pression DOM avec:
    - Score instantané
    - Score lissé (EMA)
    - Détection grosses mains
    """
    dom_features = snapshot.get('dom_features', {})

    # Données brutes
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

    # ═══════════════════════════════════════════════════════════
    # CALCUL SCORE INSTANTANÉ (pondéré)
    # ═══════════════════════════════════════════════════════════
    score = 0.0
    factors = {}

    # 1. Delta % (25%) - Le plus important
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

    # 2. Depth Ratio (20%)
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

    # 3. Imbalance proche (15%)
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

    # 4. Smart Money (25%)
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

    # 5. Institutional (15%)
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

    # ═══════════════════════════════════════════════════════════
    # LISSAGE EMA
    # ═══════════════════════════════════════════════════════════
    ema_alpha = 0.2  # EMA ~10 périodes
    if st.session_state.ema_score == 0:
        st.session_state.ema_score = score
    else:
        st.session_state.ema_score = ema_alpha * score + (1 - ema_alpha) * st.session_state.ema_score

    smoothed_score = st.session_state.ema_score

    # ═══════════════════════════════════════════════════════════
    # DÉTERMINER SIDE ET STRENGTH
    # ═══════════════════════════════════════════════════════════
    def score_to_side(s):
        if s > 0.15:
            return 'BUYERS', '🟢', '#0fbf84', min(5, int(s / 0.15) + 1)
        elif s < -0.15:
            return 'SELLERS', '🔴', '#ef476f', min(5, int(abs(s) / 0.15) + 1)
        else:
            return 'NEUTRAL', '⚪', '#64748b', 1

    instant_side, instant_emoji, instant_color, instant_strength = score_to_side(score)
    smooth_side, smooth_emoji, smooth_color, smooth_strength = score_to_side(smoothed_score)

    # ═══════════════════════════════════════════════════════════
    # DÉTECTION GROSSES MAINS
    # ═══════════════════════════════════════════════════════════
    big_hand = None

    # Delta Burst
    if delta_burst >= 50:
        side = 'BUY' if delta_pct > 0 else 'SELL'
        big_hand = {'type': 'DELTA_BURST', 'side': side, 'size': delta_burst,
                    'emoji': '🟢' if side == 'BUY' else '🔴'}

    # Stacked Imbalances
    elif stacked_bid >= 2:
        big_hand = {'type': 'STACKED_BID', 'side': 'BUY', 'size': stacked_bid, 'emoji': '🟢'}
    elif stacked_ask >= 2:
        big_hand = {'type': 'STACKED_ASK', 'side': 'SELL', 'size': stacked_ask, 'emoji': '🔴'}

    # ═══════════════════════════════════════════════════════════
    # DIVERGENCE
    # ═══════════════════════════════════════════════════════════
    divergence = None
    if instant_side != smooth_side and instant_side != 'NEUTRAL' and smooth_side != 'NEUTRAL':
        if instant_side == 'SELLERS' and smooth_side == 'BUYERS':
            divergence = {'type': 'REVERSAL_DOWN', 'text': '⚠️ Possible retournement BAISSIER'}
        elif instant_side == 'BUYERS' and smooth_side == 'SELLERS':
            divergence = {'type': 'REVERSAL_UP', 'text': '⚠️ Possible retournement HAUSSIER'}

    return {
        'instant': {
            'side': instant_side, 'emoji': instant_emoji, 'color': instant_color,
            'strength': instant_strength, 'score': score
        },
        'smoothed': {
            'side': smooth_side, 'emoji': smooth_emoji, 'color': smooth_color,
            'strength': smooth_strength, 'score': smoothed_score
        },
        'raw': {
            'bid_pct': bid_pct, 'ask_pct': ask_pct, 'delta_pct': delta_pct,
            'depth_bid': depth_bid, 'depth_ask': depth_ask,
            'smart_money': smart_money, 'cum_delta': cum_delta
        },
        'factors': factors,
        'big_hand': big_hand,
        'divergence': divergence
    }


def render_dom_pressure(snapshot: Dict):
    """Affiche la section DOM PRESSURE - QUI A LA MAIN?"""

    st.markdown("### 🎯 QUI A LA MAIN? (DOM Pressure)")

    dom = calculate_dom_pressure(snapshot)
    instant = dom['instant']
    smoothed = dom['smoothed']
    raw = dom['raw']

    # ═══════════════════════════════════════════════════════════
    # LAYOUT PRINCIPAL: BUYERS | CENTRE | SELLERS
    # ═══════════════════════════════════════════════════════════
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
        # Box principale avec le verdict
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0f1620, #1a2332); border-radius: 16px;
                    padding: 16px; text-align: center; border: 2px solid {instant['color']};">
            <div style="font-size: 0.9rem; color: #64748b;">INSTANTANÉ</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: {instant['color']};">
                {instant['emoji']} {instant['side']}
            </div>
            <div style="margin: 8px 0;">
                <span style="font-size: 1.2rem;">{'█' * instant['strength']}{'░' * (5 - instant['strength'])}</span>
                <span style="color: #64748b; margin-left: 8px;">Force: {instant['strength']}/5</span>
            </div>
            <div style="border-top: 1px solid #1e293b; margin-top: 12px; padding-top: 12px;">
                <div style="font-size: 0.8rem; color: #64748b;">TENDANCE (EMA)</div>
                <div style="font-size: 1.2rem; color: {smoothed['color']};">
                    {smoothed['emoji']} {smoothed['side']} ({smoothed['strength']}/5)
                </div>
            </div>
            <div style="margin-top: 8px; font-size: 0.9rem; color: #94a3b8;">
                Delta: {raw['delta_pct']:+.1%} | Cum: {raw['cum_delta']:+,}
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

    # ═══════════════════════════════════════════════════════════
    # ALERTES: GROSSE MAIN ET DIVERGENCE
    # ═══════════════════════════════════════════════════════════
    if dom['big_hand']:
        bh = dom['big_hand']
        st.markdown(f"""
        <div class="warning-box" style="border-color: {bh['emoji'].replace('🟢', '#0fbf84').replace('🔴', '#ef476f')};
                    background: {'rgba(15,191,132,0.2)' if bh['side'] == 'BUY' else 'rgba(239,71,111,0.2)'};">
            🚨 <strong>GROSSE MAIN DÉTECTÉE!</strong> {bh['emoji']} {bh['side']} |
            Type: {bh['type']} | Size: {bh['size']}
        </div>
        """, unsafe_allow_html=True)

    if dom['divergence']:
        st.markdown(f"""
        <div class="warning-box">
            {dom['divergence']['text']} (Instantané ≠ Tendance)
        </div>
        """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    # DÉTAILS DES FACTEURS (Expander)
    # ═══════════════════════════════════════════════════════════
    with st.expander("📊 Détails des facteurs"):
        for factor_name, (side, contrib, value) in dom['factors'].items():
            bar_len = int(abs(contrib) * 40) if contrib != 0 else 0
            bar_color = '#0fbf84' if contrib > 0 else '#ef476f' if contrib < 0 else '#64748b'
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin: 4px 0;">
                <span style="width: 100px;">{factor_name}</span>
                <span style="width: 100px; color: {bar_color};">{side}</span>
                <span style="flex: 1; background: #1e293b; height: 8px; border-radius: 4px; overflow: hidden;">
                    <span style="display: block; width: {bar_len}%; height: 100%; background: {bar_color};"></span>
                </span>
                <span style="width: 80px; text-align: right; color: #94a3b8;">
                    {value:+.2f}
                </span>
            </div>
            """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# 📊 TRADES - Chargement et analyse des trades
# ═══════════════════════════════════════════════════════════════

def parse_trade_log_line(line: str) -> Optional[Dict]:
    """Parse une ligne de log de trade"""
    try:
        match = re.match(r'(\d{2}:\d{2}:\d{2}) - INFO - \[(\w+)\] (ENTRY|EXIT) \| (.+)', line)
        if not match:
            return None
        time_str, symbol, action, data_str = match.groups()
        data = eval(data_str)
        return {'time': time_str, 'symbol': symbol, 'action': action, 'data': data}
    except:
        return None


@st.cache_data(ttl=10)
def load_trades_from_log(date: datetime) -> List[Dict]:
    """Charge les trades depuis le fichier log"""
    date_str = date.strftime("%Y%m%d")
    log_path = Path("logs_advanced") / "trades" / f"trades_{date_str}.log"

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
                        'result': 'WIN' if data.get('pnl_usd', 0) > 0 else 'LOSS'
                    })
                    trades.append(trade)
    except Exception as e:
        pass

    return trades


def load_trades_week() -> List[Dict]:
    """Charge les trades de la semaine"""
    all_trades = []
    today = datetime.now()
    for days_back in range(7):
        date = today - timedelta(days=days_back)
        day_trades = load_trades_from_log(date)
        for trade in day_trades:
            trade['date'] = date.strftime("%Y-%m-%d")
        all_trades.extend(day_trades)
    return all_trades


def calculate_session_pnl(trades: List[Dict]) -> Dict:
    """Calcule le P&L par session"""
    sessions = {
        'LONDON': {'start': 8, 'end': 11},
        'US_MORNING': {'start': 15, 'end': 17},
        'LUNCH': {'start': 17, 'end': 20},
        'US_POWER': {'start': 20, 'end': 22},
    }
    session_pnl = {s: {'pnl': 0, 'trades': 0, 'wins': 0} for s in sessions}

    for trade in trades:
        try:
            hour = int(trade.get('time_entry', '00:00:00').split(':')[0])
            pnl = trade.get('pnl_usd', 0)
            is_win = pnl > 0
            for session_name, times in sessions.items():
                if times['start'] <= hour < times['end']:
                    session_pnl[session_name]['pnl'] += pnl
                    session_pnl[session_name]['trades'] += 1
                    if is_win:
                        session_pnl[session_name]['wins'] += 1
                    break
        except:
            continue
    return session_pnl


def calculate_symbol_pnl(trades: List[Dict]) -> Dict:
    """Calcule le P&L par symbole"""
    symbol_pnl = {}
    for trade in trades:
        symbol = trade.get('symbol', 'Unknown')
        pnl = trade.get('pnl_usd', 0)
        is_win = pnl > 0
        if symbol not in symbol_pnl:
            symbol_pnl[symbol] = {'pnl': 0, 'trades': 0, 'wins': 0}
        symbol_pnl[symbol]['pnl'] += pnl
        symbol_pnl[symbol]['trades'] += 1
        if is_win:
            symbol_pnl[symbol]['wins'] += 1
    return symbol_pnl


def render_trades_section():
    """Affiche la section Trades avec P&L"""
    st.markdown("## 📊 Historique Trades & P&L")

    today = datetime.now()
    trades_today = load_trades_from_log(today)
    trades_week = load_trades_week()

    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)

    # P&L Jour
    pnl_today = sum(t.get('pnl_usd', 0) for t in trades_today)
    wins_today = sum(1 for t in trades_today if t.get('pnl_usd', 0) > 0)
    wr_today = (wins_today / len(trades_today) * 100) if trades_today else 0

    with col1:
        color = '#0fbf84' if pnl_today >= 0 else '#ef476f'
        st.markdown(f"""
        <div class="metric-box" style="border: 2px solid {color};">
            <div class="metric-label">💰 P&L JOUR</div>
            <div class="metric-value" style="color: {color}; font-size: 1.8rem;">${pnl_today:+,.0f}</div>
            <div style="font-size: 0.8rem; color: #64748b;">{len(trades_today)} trades | WR {wr_today:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    # P&L Semaine
    pnl_week = sum(t.get('pnl_usd', 0) for t in trades_week)
    wins_week = sum(1 for t in trades_week if t.get('pnl_usd', 0) > 0)
    wr_week = (wins_week / len(trades_week) * 100) if trades_week else 0

    with col2:
        color = '#0fbf84' if pnl_week >= 0 else '#ef476f'
        st.markdown(f"""
        <div class="metric-box" style="border: 2px solid {color};">
            <div class="metric-label">📅 P&L SEMAINE</div>
            <div class="metric-value" style="color: {color}; font-size: 1.8rem;">${pnl_week:+,.0f}</div>
            <div style="font-size: 0.8rem; color: #64748b;">{len(trades_week)} trades | WR {wr_week:.0f}%</div>
        </div>
        """, unsafe_allow_html=True)

    # Meilleur/Pire trade
    if trades_today:
        best_trade = max(trades_today, key=lambda x: x.get('pnl_usd', 0))
        worst_trade = min(trades_today, key=lambda x: x.get('pnl_usd', 0))

        with col3:
            st.markdown(f"""
            <div class="metric-box" style="border: 2px solid #0fbf84;">
                <div class="metric-label">🏆 BEST TRADE</div>
                <div class="metric-value green">${best_trade.get('pnl_usd', 0):+,.0f}</div>
                <div style="font-size: 0.8rem; color: #64748b;">{best_trade.get('symbol', '')} {best_trade.get('direction', '')}</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-box" style="border: 2px solid #ef476f;">
                <div class="metric-label">💀 WORST TRADE</div>
                <div class="metric-value red">${worst_trade.get('pnl_usd', 0):+,.0f}</div>
                <div style="font-size: 0.8rem; color: #64748b;">{worst_trade.get('symbol', '')} {worst_trade.get('direction', '')}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        with col3:
            st.info("Aucun trade")
        with col4:
            st.info("Aucun trade")

    st.divider()

    # Sous-tabs
    tab1, tab2, tab3 = st.tabs(["📋 Trades du Jour", "📊 P&L par Session", "📈 P&L par Symbole"])

    with tab1:
        if not trades_today:
            st.info("📭 Aucun trade aujourd'hui")
        else:
            data = []
            for trade in reversed(trades_today):
                pnl = trade.get('pnl_usd', 0)
                data.append({
                    "⏰": trade.get('time_entry', ''),
                    "Sym": trade.get('symbol', ''),
                    "Dir": '🟢 L' if trade.get('direction') == 'LONG' else '🔴 S',
                    "Entry": f"{trade.get('entry_price', 0):,.2f}",
                    "Exit": f"{trade.get('exit_price', 0):,.2f}",
                    "P&L": f"${pnl:+,.0f}",
                    "Result": "✅" if pnl > 0 else "❌",
                    "Exit": trade.get('exit_reason', '')[:10],
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

    with tab2:
        session_pnl = calculate_session_pnl(trades_today)
        cols = st.columns(4)
        session_order = ['LONDON', 'US_MORNING', 'LUNCH', 'US_POWER']
        emojis = {'LONDON': '🇬🇧', 'US_MORNING': '🇺🇸', 'LUNCH': '🍔', 'US_POWER': '⚡'}

        for i, sess in enumerate(session_order):
            data = session_pnl.get(sess, {'pnl': 0, 'trades': 0, 'wins': 0})
            pnl = data['pnl']
            trades_count = data['trades']
            wins = data['wins']
            wr = (wins / trades_count * 100) if trades_count > 0 else 0
            color = '#0fbf84' if pnl >= 0 else '#ef476f'

            with cols[i]:
                st.markdown(f"""
                <div class="metric-box">
                    <div style="font-size: 1.2rem;">{emojis.get(sess, '📊')} {sess}</div>
                    <div class="metric-value" style="color: {color};">${pnl:+,.0f}</div>
                    <div style="font-size: 0.8rem; color: #64748b;">{trades_count}T | WR {wr:.0f}%</div>
                </div>
                """, unsafe_allow_html=True)

    with tab3:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📅 Aujourd'hui")
            symbol_pnl = calculate_symbol_pnl(trades_today)
            for sym in ['ES', 'NQ', 'RTY']:
                data = symbol_pnl.get(sym, {'pnl': 0, 'trades': 0, 'wins': 0})
                if data['trades'] > 0:
                    pnl = data['pnl']
                    wr = (data['wins'] / data['trades'] * 100)
                    color = '#0fbf84' if pnl >= 0 else '#ef476f'
                    icon = SYMBOLS_CONFIG.get(sym, {}).get('icon', '📊')
                    st.markdown(f"""
                    <div class="metric-box" style="display: flex; justify-content: space-between;">
                        <span>{icon} <strong>{sym}</strong></span>
                        <span style="color: {color}; font-weight: 700;">${pnl:+,.0f}</span>
                        <span style="color: #64748b;">{data['trades']}T | {wr:.0f}%</span>
                    </div>
                    """, unsafe_allow_html=True)

        with col2:
            st.markdown("#### 📅 Semaine")
            symbol_pnl = calculate_symbol_pnl(trades_week)
            for sym in ['ES', 'NQ', 'RTY']:
                data = symbol_pnl.get(sym, {'pnl': 0, 'trades': 0, 'wins': 0})
                if data['trades'] > 0:
                    pnl = data['pnl']
                    wr = (data['wins'] / data['trades'] * 100)
                    color = '#0fbf84' if pnl >= 0 else '#ef476f'
                    icon = SYMBOLS_CONFIG.get(sym, {}).get('icon', '📊')
                    st.markdown(f"""
                    <div class="metric-box" style="display: flex; justify-content: space-between;">
                        <span>{icon} <strong>{sym}</strong></span>
                        <span style="color: {color}; font-weight: 700;">${pnl:+,.0f}</span>
                        <span style="color: #64748b;">{data['trades']}T | {wr:.0f}%</span>
                    </div>
                    """, unsafe_allow_html=True)


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
            - 🔥 VOLATILITY: Prudence!

            **NEXT WALL:** Niveau gamma le plus proche (temps réel)
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
    conseils = generate_conseils(symbol, ctx, bias, mode, vol, direction, session, levels, next_wall)

    # Header symbole
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"## {config['icon']} {symbol} - {config['name']}")
    with col2:
        mid = ctx.get('mid', 0)
        st.markdown(f"<h2 style='color: {config['color']}; text-align: right;'>{mid:,.2f}</h2>",
                    unsafe_allow_html=True)

    st.divider()

    # ═══════════════════════════════════════════════════════════════
    # ONGLETS PRINCIPAUX
    # ═══════════════════════════════════════════════════════════════
    main_tab1, main_tab2 = st.tabs(["🎯 Analyse Marché", "📊 Trades & P&L"])

    with main_tab1:
        # 🔥 NEXT WALL - LE PLUS IMPORTANT!
        render_next_wall(next_wall, symbol)

        st.divider()

        # BIAS | MODE | DIRECTION | VOLATILITÉ
        render_bias_mode_direction(bias, mode, direction, vol)

        st.divider()

        # Position 1D
        render_position_1d(ctx)

        st.divider()

        # 🎯 DOM PRESSURE - QUI A LA MAIN?
        render_dom_pressure(snapshot)

        st.divider()

        # OrderFlow metrics (version compacte)
        render_orderflow_metrics(ctx)

        st.divider()

        # Conseils | Niveaux
        col_left, col_right = st.columns([1, 1])

        with col_left:
            render_conseils(conseils)
            render_bias_factors(bias)

        with col_right:
            render_levels_table(levels, symbol)

    with main_tab2:
        render_trades_section()

    # Footer
    st.markdown("---")
    st.caption(f"🎯 MIA Trading Copilot V5 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Session: {ctx.get('session_id', 'Unknown')}")

    # Auto-refresh
    if auto_refresh:
        time.sleep(5)
        st.rerun()


if __name__ == "__main__":
    main()
