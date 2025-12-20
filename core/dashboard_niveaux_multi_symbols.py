#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 DASHBOARD NIVEAUX MULTI-SYMBOLES - MIA Trading Bot
======================================================

Dashboard Streamlit affichant en temps réel pour ES, NQ, RTY:
- Prix actuel
- Niveaux les plus proches (distance tradable)
- Confluences détectées
- Status tradable selon max_entry_distance

Version: 1.0 (Créé 10/12/2025)
Lancer avec: streamlit run core/dashboard_niveaux_multi_symbols.py

Author: MIA System + Claude Sonnet 4.5
"""

import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
from datetime import datetime
import json
from typing import Dict, List, Tuple
from collections import defaultdict

# Import du data loader dynamique
from core.data_loader import find_latest_snapshot, validate_snapshot

# Configuration page
st.set_page_config(
    page_title="🎯 Dashboard Niveaux ES/NQ/RTY - MIA Bot",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

SYMBOLS_CONFIG = {
    'ES': {
        'tick_size': 0.25,
        'max_distance': 15,  # Config après corrections 10/12
        'color': '#0fbf84',
        'icon': '📗'
    },
    'NQ': {
        'tick_size': 0.25,
        'max_distance': 20,  # Config après corrections 10/12
        'color': '#4a9eff',
        'icon': '📘'
    },
    'RTY': {
        'tick_size': 0.10,
        'max_distance': 15,  # Config après corrections 10/12
        'color': '#ff6b6b',
        'icon': '📕'
    }
}

REFRESH_INTERVAL = 3  # secondes

# Priorités des niveaux
LEVEL_PRIORITIES = {
    'hvl': (100, '🔥'),
    'hvl_0dte': (98, '🔥'),
    'vah': (100, '🔥'),
    'val': (100, '🔥'),
    'poc': (100, '🔥'),
    '1d_max': (100, '🔥'),
    '1d_min': (100, '🔥'),
    'call_resistance_0dte': (98, '🔥'),
    'put_support_0dte': (98, '🔥'),
    'gamma_wall_0dte': (95, '⭐'),
    'gamma_wall': (90, '⭐'),
    'gex': (85, '⭐'),
    'blind_spot': (85, '⭐'),
    'vwap': (70, '📊'),
}

# ═══════════════════════════════════════════════════════════════
# INJECTION CSS DARK THEME
# ═══════════════════════════════════════════════════════════════

def inject_css():
    """Injecte le CSS dark theme professionnel"""
    st.markdown("""
    <style>
    /* Dark Theme Global */
    .stApp {
        background-color: #0e1117;
        color: #fafafa;
    }

    /* KPI Cards */
    .kpi-card {
        background: linear-gradient(135deg, #1e2130 0%, #2a2d3a 100%);
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #3a3f51;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        text-align: center;
        margin: 10px 0;
    }

    .kpi-label {
        font-size: 14px;
        color: #8b92a7;
        font-weight: 500;
        margin-bottom: 8px;
    }

    .kpi-value {
        font-size: 32px;
        font-weight: 700;
        line-height: 1.2;
    }

    .bullish { color: #0fbf84; }
    .bearish { color: #f54257; }
    .neutral { color: #f8c36b; }

    /* Section Titles */
    .section-title {
        font-size: 24px;
        font-weight: 700;
        color: #fafafa;
        margin: 30px 0 15px 0;
        padding-bottom: 10px;
        border-bottom: 2px solid #3a3f51;
    }

    /* Pills */
    .pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin: 4px;
    }

    .pill.tradable {
        background-color: #0fbf84;
        color: white;
    }

    .pill.proche {
        background-color: #f8c36b;
        color: black;
    }

    .pill.loin {
        background-color: #8b92a7;
        color: white;
    }

    /* Alert Boxes */
    .alert-box {
        background: rgba(15, 191, 132, 0.1);
        border-left: 4px solid #0fbf84;
        padding: 15px;
        border-radius: 8px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

# find_latest_snapshot est maintenant importé de data_loader.py (voir import en haut)

def calculate_distance(current_price: float, level_price: float, tick_size: float) -> Tuple[float, float, str]:
    """Calcule la distance en ticks et points"""
    dist_pts = level_price - current_price
    dist_ticks = abs(dist_pts) / tick_size
    direction = "🔼" if dist_pts > 0 else "🔽"
    return dist_ticks, dist_pts, direction


def get_tradable_status(dist_ticks: float, max_distance: int) -> Tuple[str, str]:
    """Retourne le status et la classe CSS selon la distance"""
    if dist_ticks <= max_distance:
        return "✅ TRADABLE", "tradable"
    elif dist_ticks <= max_distance * 2:
        return "⚠️ PROCHE", "proche"
    else:
        return "❌ LOIN", "loin"


def extract_levels_from_snapshot(snapshot: Dict, symbol: str) -> Dict[str, List]:
    """Extrait tous les niveaux du snapshot"""
    levels = defaultdict(list)

    if not snapshot:
        return levels

    # HVL
    if 'hvl' in snapshot and snapshot['hvl']:
        levels['HVL'].append(snapshot['hvl'])

    if 'hvl_0dte' in snapshot and snapshot['hvl_0dte']:
        levels['HVL_0DTE'].append(snapshot['hvl_0dte'])

    # Value Area
    if 'vah' in snapshot and snapshot['vah']:
        levels['VAH'].append(snapshot['vah'])

    if 'val' in snapshot and snapshot['val']:
        levels['VAL'].append(snapshot['val'])

    if 'poc' in snapshot and snapshot['poc']:
        levels['POC'].append(snapshot['poc'])

    # 1D extremes
    if '1d_max' in snapshot and snapshot['1d_max']:
        levels['1D_MAX'].append(snapshot['1d_max'])

    if '1d_min' in snapshot and snapshot['1d_min']:
        levels['1D_MIN'].append(snapshot['1d_min'])

    # GEX Levels
    for i in range(1, 11):
        gex_key = f'gex_{i}'
        if gex_key in snapshot and snapshot[gex_key]:
            levels[f'GEX_{i}'].append(snapshot[gex_key])

    # Blind Spots - Snapshot: blind_spot_0 à blind_spot_8 → Affichage: BL 1 à BL 9
    for i in range(9):  # 0 à 8
        bs_key = f'blind_spot_{i}'
        if bs_key in snapshot and snapshot[bs_key]:
            levels[f'BL_{i+1}'].append(snapshot[bs_key])

    # 0DTE Levels
    if 'call_resistance_0dte' in snapshot and snapshot['call_resistance_0dte']:
        levels['CR_0DTE'].append(snapshot['call_resistance_0dte'])

    if 'put_support_0dte' in snapshot and snapshot['put_support_0dte']:
        levels['PS_0DTE'].append(snapshot['put_support_0dte'])

    if 'gamma_wall_0dte' in snapshot and snapshot['gamma_wall_0dte']:
        levels['GW_0DTE'].append(snapshot['gamma_wall_0dte'])

    # Gamma Walls
    for i in range(1, 6):
        gw_key = f'gamma_wall_{i}'
        if gw_key in snapshot and snapshot[gw_key]:
            levels[f'GAMMA_{i}'].append(snapshot[gw_key])

    return dict(levels)


def detect_confluences(all_levels: List[Dict], confluence_threshold: float = 5.0) -> List[Dict]:
    """Détecte les confluences (niveaux groupés)"""
    if len(all_levels) < 2:
        return []

    # Trier par prix
    sorted_levels = sorted(all_levels, key=lambda x: x['prix'])

    confluences = []
    i = 0

    while i < len(sorted_levels):
        group = [sorted_levels[i]]
        j = i + 1

        while j < len(sorted_levels):
            if abs(sorted_levels[j]['prix'] - group[0]['prix']) <= confluence_threshold:
                group.append(sorted_levels[j])
                j += 1
            else:
                break

        if len(group) >= 3:  # Au moins 3 niveaux pour confluence
            avg_price = sum(l['prix'] for l in group) / len(group)
            confluences.append({
                'prix': avg_price,
                'count': len(group),
                'types': [l['type'] for l in group]
            })

        i = j if j > i + 1 else i + 1

    return confluences


# ═══════════════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════════════

def main():
    inject_css()

    # Header
    st.markdown("""
    <h1 style='text-align: center; color: #0fbf84;'>
        🎯 DASHBOARD NIVEAUX TEMPS RÉEL
    </h1>
    <p style='text-align: center; color: #8b92a7; font-size: 14px;'>
        MIA Trading Bot - Niveaux MenthorQ ES/NQ/RTY
    </p>
    """, unsafe_allow_html=True)

    # Sidebar config
    st.sidebar.markdown("### ⚙️ Configuration")

    selected_symbol = st.sidebar.selectbox(
        "Symbole",
        options=['ES', 'NQ', 'RTY'],
        index=0
    )

    max_display = st.sidebar.slider(
        "Niveaux à afficher",
        min_value=10,
        max_value=50,
        value=20,
        step=5
    )

    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh", value=True)

    if auto_refresh:
        st.sidebar.info(f"⏱️ Refresh toutes les {REFRESH_INTERVAL}s")

    # Charger snapshot
    snapshot = find_latest_snapshot(selected_symbol)

    if not snapshot:
        st.error(f"❌ Aucun snapshot trouvé pour {selected_symbol}")
        st.info("📁 Vérifiez que DATA_SIERRA_CHART/ml_ready/ contient des fichiers JSON")
        return

    # Extraire données
    current_price = snapshot.get('mid', 0)
    if current_price == 0:
        st.error(f"❌ Prix invalide dans snapshot {selected_symbol}")
        return

    config = SYMBOLS_CONFIG[selected_symbol]
    tick_size = config['tick_size']
    max_distance = config['max_distance']

    # Extraire niveaux
    levels = extract_levels_from_snapshot(snapshot, selected_symbol)

    # ═══════════════════════════════════════════════════════════════
    # KPIs
    # ═══════════════════════════════════════════════════════════════

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{config['icon']} {selected_symbol} Prix</div>
            <div class="kpi-value neutral">{current_price:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    # Construire liste complète des niveaux
    all_levels_list = []
    for level_type, prices in levels.items():
        for price in prices:
            dist_ticks, dist_pts, direction = calculate_distance(current_price, price, tick_size)
            status, css_class = get_tradable_status(dist_ticks, max_distance)

            all_levels_list.append({
                'type': level_type,
                'prix': price,
                'distance_ticks': dist_ticks,
                'distance_pts': dist_pts,
                'direction': direction,
                'status': status,
                'css': css_class
            })

    # Compter niveaux tradables
    tradable_count = sum(1 for l in all_levels_list if l['css'] == 'tradable')
    proche_count = sum(1 for l in all_levels_list if l['css'] == 'proche')

    # Détecter confluences
    confluences = detect_confluences(all_levels_list, confluence_threshold=5.0)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">✅ Niveaux Tradables</div>
            <div class="kpi-value bullish">{tradable_count}</div>
            <div class="kpi-label">≤ {max_distance} ticks</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">⚠️ Niveaux Proches</div>
            <div class="kpi-value neutral">{proche_count}</div>
            <div class="kpi-label">{max_distance+1}-{max_distance*2} ticks</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">💎 Confluences</div>
            <div class="kpi-value bearish">{len(confluences)}</div>
            <div class="kpi-label">3+ niveaux groupés</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"<p style='text-align: center; color: #8b92a7;'>⏰ Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════
    # NIVEAUX LES PLUS PROCHES
    # ═══════════════════════════════════════════════════════════════

    st.markdown("<div class='section-title'>📍 Niveaux les Plus Proches</div>", unsafe_allow_html=True)

    # Trier par distance
    all_levels_list.sort(key=lambda x: x['distance_ticks'])

    # Limiter affichage
    display_levels = all_levels_list[:max_display]

    if not display_levels:
        st.warning("⚠️ Aucun niveau trouvé.")
    else:
        # Créer DataFrame
        df_display = pd.DataFrame([{
            'Type': l['type'],
            'Prix': f"{l['prix']:.2f}",
            'Distance': f"{l['direction']} {l['distance_ticks']:.0f}t ({l['distance_pts']:.2f}pts)",
            'Status': l['status']
        } for l in display_levels])

        # Fonction de coloration
        def color_status(val):
            if '✅' in val:
                return 'background-color: rgba(15, 191, 132, 0.2)'
            elif '⚠️' in val:
                return 'background-color: rgba(248, 195, 107, 0.2)'
            else:
                return 'background-color: rgba(139, 146, 167, 0.1)'

        styled_df = df_display.style.applymap(color_status, subset=['Status'])

        st.dataframe(styled_df, use_container_width=True, height=600)

    # ═══════════════════════════════════════════════════════════════
    # CONFLUENCES DÉTECTÉES
    # ═══════════════════════════════════════════════════════════════

    if confluences:
        st.markdown("<div class='section-title'>💎 Confluences Détectées</div>", unsafe_allow_html=True)

        for conf in confluences[:5]:  # Top 5
            dist_ticks, dist_pts, direction = calculate_distance(current_price, conf['prix'], tick_size)
            status, css_class = get_tradable_status(dist_ticks, max_distance)

            types_str = ', '.join(conf['types'][:3])
            if len(conf['types']) > 3:
                types_str += f" +{len(conf['types']) - 3} autres"

            st.markdown(f"""
            <div class="alert-box">
                <strong>💎 Confluence @ {conf['prix']:.2f}</strong><br>
                <span class="pill {css_class}">{status}</span>
                <span class="pill neutral">{direction} {dist_ticks:.0f} ticks</span>
                <span class="pill neutral">{conf['count']} niveaux</span>
                <br><small style="color: #8b92a7;">{types_str}</small>
            </div>
            """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════
    # CONFIG BOT
    # ═══════════════════════════════════════════════════════════════

    st.markdown("<div class='section-title'>⚙️ Configuration Bot</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Max Entry Distance</div>
            <div class="kpi-value neutral">{max_distance} ticks</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Tick Size</div>
            <div class="kpi-value neutral">{tick_size}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Tick Value</div>
            <div class="kpi-value neutral">${5 if selected_symbol == 'NQ' else 12.50 if selected_symbol == 'ES' else 5}</div>
        </div>
        """, unsafe_allow_html=True)

    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(REFRESH_INTERVAL)
        st.rerun()


if __name__ == "__main__":
    main()
