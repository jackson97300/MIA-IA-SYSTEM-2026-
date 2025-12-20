#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 DASHBOARD NIVEAUX TEMPS RÉEL - MIA Trading Bot
==================================================

Dashboard Streamlit affichant en temps réel:
- Prix actuel NQ
- Niveaux les plus proches (±50 ticks)
- Confluences détectées
- Distance en ticks et status tradable
- Configuration bot actuelle (Trailing Stop, TP/SL)

Version: 3.0 (Optimisé 25/11/2025 - 13:30)
Lancer avec: streamlit run core/dashboard_niveaux_temps_reel.py

Author: MIA System + Claude Sonnet 4.5
"""

import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import json
import re
import time
from typing import Dict, List, Tuple, Optional

# Configuration page
st.set_page_config(
    page_title="🎯 Dashboard Niveaux NQ - MIA Bot",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

TICK_SIZE_NQ = 0.25
MAX_DISTANCE_TRADABLE = 15  # ticks
REFRESH_INTERVAL = 3  # secondes

# Priorités des niveaux
PRIORITIES = {
    'HVL': (100, '🔥'),
    'VAH': (100, '🔥'),
    'VAL': (100, '🔥'),
    'POC': (100, '🔥'),
    '1D': (100, '🔥'),
    'Gamma Wall': (90, '⭐'),
    'Next Wall': (90, '⭐'),
    'Call Resistance': (90, '⭐'),
    'Put Support': (90, '⭐'),
    'GEX': (85, '⭐'),
    'Blind Spot': (85, '⭐'),
    'VWAP': (70, '📊'),
    'PVWAP': (70, '📊'),
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
        letter-spacing: -0.5px;
    }

    .kpi-value.bullish { color: #0fbf84; }
    .kpi-value.bearish { color: #ef476f; }
    .kpi-value.neutral { color: #f8c36b; }

    /* Pills */
    .pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-size: 13px;
        font-weight: 600;
        margin: 2px;
    }

    .pill.tradable { background: #0fbf84; color: #0e1117; }
    .pill.proche { background: #f8c36b; color: #0e1117; }
    .pill.moyen { background: #8b92a7; color: #0e1117; }
    .pill.loin { background: #ef476f; color: #0e1117; }

    /* Section Titles */
    .section-title {
        font-size: 24px;
        font-weight: 700;
        color: #fafafa;
        margin: 24px 0 16px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #3a3f51;
    }

    /* Table Styling */
    .dataframe {
        background-color: #1e2130 !important;
        border-radius: 8px;
    }

    .dataframe th {
        background-color: #2a2d3a !important;
        color: #fafafa !important;
        font-weight: 600 !important;
        padding: 12px !important;
    }

    .dataframe td {
        background-color: #1e2130 !important;
        color: #fafafa !important;
        padding: 10px !important;
    }

    /* Confluence Badge */
    .confluence-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 14px;
        margin: 4px;
    }

    /* Alert Boxes */
    .alert-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 16px 20px;
        margin: 16px 0;
        border-left: 4px solid #667eea;
    }

    .alert-box.warning {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border-left-color: #f5576c;
    }

    .alert-box.success {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        border-left-color: #00f2fe;
    }
    </style>
    """, unsafe_allow_html=True)

inject_css()

# ═══════════════════════════════════════════════════════════════
# FONCTIONS D'EXTRACTION DES LOGS
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=REFRESH_INTERVAL)
def extract_levels_from_logs(log_file: str) -> Tuple[Dict, List, Optional[float]]:
    """
    Extrait tous les niveaux détectés depuis les logs
    """
    levels = {
        'GEX': [],
        'HVL': [],
        'VWAP': [],
        'PVWAP': [],
        'Gamma Wall': [],
        'Call Resistance': [],
        'Put Support': [],
        'Blind Spot': [],
        'POC': [],
        'VAH': [],
        'VAL': [],
        'Next Wall': [],
        '1D': []
    }

    confluences = []
    current_price = None

    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Lire les dernières 2000 lignes
        recent_lines = lines[-2000:] if len(lines) > 2000 else lines

        for line in recent_lines:
            # Extraire le prix actuel
            if 'Mid @' in line or 'price=' in line:
                price_patterns = [
                    r'Mid @ (\d{5}\.\d{2})',
                    r'price=(\d{5}\.\d{2})',
                ]
                for pattern in price_patterns:
                    match = re.search(pattern, line)
                    if match:
                        price = float(match.group(1))
                        if 24000 < price < 26000:
                            current_price = price
                            break

            # Extraire GEX
            if 'gex_' in line.lower():
                match = re.search(r'gex_\d+[:\s]+(\d+\.\d+)', line, re.IGNORECASE)
                if match:
                    price = float(match.group(1))
                    if price not in levels['GEX'] and 24000 < price < 26000:
                        levels['GEX'].append(price)

            # Extraire HVL
            if 'HVL' in line:
                match = re.search(r'HVL.*?(\d{5}\.\d+)', line)
                if match:
                    price = float(match.group(1))
                    if price not in levels['HVL']:
                        levels['HVL'].append(price)

            # Extraire Next Wall
            if 'next_wall' in line.lower() or 'Next Wall' in line:
                match = re.search(r'(\d{5}\.\d+)', line)
                if match:
                    price = float(match.group(1))
                    if price not in levels['Next Wall'] and 24000 < price < 26000:
                        levels['Next Wall'].append(price)

            # Extraire Call Resistance / Put Support
            if 'call_resistance' in line.lower():
                match = re.search(r'(\d{5}\.\d+)', line)
                if match:
                    price = float(match.group(1))
                    if price not in levels['Call Resistance'] and 24000 < price < 26000:
                        levels['Call Resistance'].append(price)

            if 'put_support' in line.lower():
                match = re.search(r'(\d{5}\.\d+)', line)
                if match:
                    price = float(match.group(1))
                    if price not in levels['Put Support'] and 24000 < price < 26000:
                        levels['Put Support'].append(price)

            # Extraire 1D Max/Min
            if '1-Day Max' in line or '1D Max' in line:
                match = re.search(r'(\d{5}\.\d+)', line)
                if match:
                    price = float(match.group(1))
                    if ('1D Max', price) not in levels['1D']:
                        levels['1D'].append(('1D Max', price))

            if '1-Day Min' in line or '1D Min' in line:
                match = re.search(r'(\d{5}\.\d+)', line)
                if match:
                    price = float(match.group(1))
                    if ('1D Min', price) not in levels['1D']:
                        levels['1D'].append(('1D Min', price))

            # Extraire VWAP levels
            vwap_patterns = [
                (r'VWAP\s+upper\s+SD3.*?(\d{5}\.\d+)', 'VWAP SD+3'),
                (r'VWAP\s+upper\s+SD2.*?(\d{5}\.\d+)', 'VWAP SD+2'),
                (r'VWAP\s+upper\s+SD1.*?(\d{5}\.\d+)', 'VWAP SD+1'),
                (r'VWAP\s+lower\s+SD1.*?(\d{5}\.\d+)', 'VWAP SD-1'),
                (r'VWAP\s+lower\s+SD2.*?(\d{5}\.\d+)', 'VWAP SD-2'),
                (r'VWAP\s+lower\s+SD3.*?(\d{5}\.\d+)', 'VWAP SD-3'),
            ]

            for pattern, name in vwap_patterns:
                match = re.search(pattern, line)
                if match:
                    price = float(match.group(1))
                    if (name, price) not in levels['VWAP']:
                        levels['VWAP'].append((name, price))

            # Détecter confluences
            if 'CONFLUENCE' in line.upper():
                match = re.search(r'(\d+)\s+niveaux\s+@\s*(\d{5}\.\d+)', line)
                if match:
                    count = int(match.group(1))
                    price = float(match.group(2))
                    if not any(c['price'] == price for c in confluences):
                        confluences.append({
                            'price': price,
                            'count': count,
                            'description': line.strip()
                        })

    except Exception as e:
        st.error(f"❌ Erreur lecture logs: {e}")

    return levels, confluences, current_price


def calculate_distance(current_price: float, level_price: float) -> Tuple[float, float, str]:
    """Calcule la distance en ticks et points"""
    distance_ticks = abs(level_price - current_price) / TICK_SIZE_NQ
    distance_points = abs(level_price - current_price)
    direction = "↑" if level_price > current_price else "↓"
    return distance_ticks, distance_points, direction


def get_tradable_status(distance_ticks: float) -> Tuple[str, str]:
    """Retourne le status et la classe CSS"""
    if distance_ticks <= MAX_DISTANCE_TRADABLE:
        return "✅ TRADABLE", "tradable"
    elif distance_ticks <= MAX_DISTANCE_TRADABLE * 2:
        return "⏳ PROCHE", "proche"
    elif distance_ticks <= 100:
        return "⚠️ MOYEN", "moyen"
    else:
        return "❌ LOIN", "loin"


def detect_local_confluences(all_levels: List[Dict], tolerance_ticks: int = 15) -> List[Dict]:
    """Détecte les confluences localement"""
    confluences = []
    sorted_levels = sorted(all_levels, key=lambda x: x['price'])

    i = 0
    while i < len(sorted_levels):
        group = [sorted_levels[i]]
        j = i + 1

        while j < len(sorted_levels):
            distance_ticks = abs(sorted_levels[j]['price'] - sorted_levels[i]['price']) / TICK_SIZE_NQ
            if distance_ticks <= tolerance_ticks:
                group.append(sorted_levels[j])
                j += 1
            else:
                break

        if len(group) >= 2:
            avg_price = sum(l['price'] for l in group) / len(group)
            types = [l['type'] for l in group]

            confluences.append({
                'price': avg_price,
                'count': len(group),
                'types': types,
                'strength': min(1.0, len(group) * 0.3)
            })

        i = j if j > i + 1 else i + 1

    return confluences


# ═══════════════════════════════════════════════════════════════
# INTERFACE PRINCIPALE
# ═══════════════════════════════════════════════════════════════

def main():
    """Interface principale du dashboard"""

    # Header
    st.markdown("<div class='section-title'>🎯 DASHBOARD NIVEAUX NQ - TEMPS RÉEL</div>", unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")

        max_display = st.slider("Niveaux à afficher", 5, 30, 15, 1)
        max_distance_filter = st.slider("Distance max (ticks)", 15, 200, 100, 5)
        auto_refresh = st.checkbox("Auto-refresh", value=True)

        st.markdown("---")
        st.markdown("### 📊 Configuration Bot")
        st.markdown("""
        **Trailing Stop:**
        - Break-even: +10 ticks
        - Start: +25 ticks
        - Distance: 10 ticks

        **TP/SL:**
        - SL optimal: 35 ticks
        - TP optimal: 53 ticks
        - R:R: 1.5:1

        **Filtres:**
        - Distance max: ±15 ticks
        - Cooldown: 90s
        - 1 position à la fois
        """)

    # Trouver le fichier log
    log_dir = Path("LAUNCH/logs")
    console_log = log_dir / "console_output.txt"

    if not console_log.exists():
        st.error("❌ Fichier log introuvable: LAUNCH/logs/console_output.txt")
        st.info("💡 Assurez-vous que le bot est en cours d'exécution.")
        return

    # Extraire les données
    levels, confluences, current_price = extract_levels_from_logs(str(console_log))

    if current_price is None:
        st.warning("⏳ En attente de données de prix...")
        time.sleep(2)
        st.rerun()
        return

    # ═══════════════════════════════════════════════════════════════
    # KPIs HEADER
    # ═══════════════════════════════════════════════════════════════

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Prix Actuel NQ</div>
            <div class="kpi-value neutral">{current_price:.2f}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        # Compter niveaux tradables
        all_levels = []
        for level_type, level_list in levels.items():
            if level_type == '1D':
                for name, price in level_list:
                    dist_ticks, _, _ = calculate_distance(current_price, price)
                    all_levels.append({'price': price, 'distance': dist_ticks})
            elif level_type in ['VWAP', 'PVWAP']:
                for name, price in level_list:
                    dist_ticks, _, _ = calculate_distance(current_price, price)
                    all_levels.append({'price': price, 'distance': dist_ticks})
            else:
                for price in level_list:
                    dist_ticks, _, _ = calculate_distance(current_price, price)
                    all_levels.append({'price': price, 'distance': dist_ticks})

        tradable_count = sum(1 for l in all_levels if l['distance'] <= MAX_DISTANCE_TRADABLE)
        proche_count = sum(1 for l in all_levels if MAX_DISTANCE_TRADABLE < l['distance'] <= MAX_DISTANCE_TRADABLE * 2)

        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Niveaux Tradables</div>
            <div class="kpi-value bullish">{tradable_count}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Niveaux Proches</div>
            <div class="kpi-value neutral">{proche_count}</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        confluence_count = len(confluences)
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Confluences</div>
            <div class="kpi-value bearish">{confluence_count}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"<p style='text-align: center; color: #8b92a7;'>⏰ Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════
    # NIVEAUX LES PLUS PROCHES
    # ═══════════════════════════════════════════════════════════════

    st.markdown("<div class='section-title'>📍 Niveaux les Plus Proches</div>", unsafe_allow_html=True)

    # Construire la liste complète des niveaux
    all_levels_full = []

    for level_type, level_list in levels.items():
        if level_type == '1D':
            for name, price in level_list:
                dist_ticks, dist_pts, direction = calculate_distance(current_price, price)
                priority, emoji = PRIORITIES.get('1D', (50, '⚪'))
                status, css_class = get_tradable_status(dist_ticks)
                all_levels_full.append({
                    'Type': level_type,
                    'Nom': name,
                    'Prix': price,
                    'Distance (ticks)': dist_ticks,
                    'Distance (pts)': dist_pts,
                    'Direction': direction,
                    'Priority': priority,
                    'Emoji': emoji,
                    'Status': status,
                    'CSS': css_class
                })
        elif level_type in ['VWAP', 'PVWAP']:
            for name, price in level_list:
                dist_ticks, dist_pts, direction = calculate_distance(current_price, price)
                priority, emoji = PRIORITIES.get(level_type, (50, '⚪'))
                status, css_class = get_tradable_status(dist_ticks)
                all_levels_full.append({
                    'Type': level_type,
                    'Nom': name,
                    'Prix': price,
                    'Distance (ticks)': dist_ticks,
                    'Distance (pts)': dist_pts,
                    'Direction': direction,
                    'Priority': priority,
                    'Emoji': emoji,
                    'Status': status,
                    'CSS': css_class
                })
        else:
            for price in level_list:
                dist_ticks, dist_pts, direction = calculate_distance(current_price, price)
                priority, emoji = PRIORITIES.get(level_type, (50, '⚪'))
                status, css_class = get_tradable_status(dist_ticks)
                all_levels_full.append({
                    'Type': level_type,
                    'Nom': f"{level_type} @ {price:.2f}",
                    'Prix': price,
                    'Distance (ticks)': dist_ticks,
                    'Distance (pts)': dist_pts,
                    'Direction': direction,
                    'Priority': priority,
                    'Emoji': emoji,
                    'Status': status,
                    'CSS': css_class
                })

    # Filtrer et trier
    filtered_levels = [l for l in all_levels_full if l['Distance (ticks)'] <= max_distance_filter]
    filtered_levels.sort(key=lambda x: x['Distance (ticks)'])

    # Limiter l'affichage
    display_levels = filtered_levels[:max_display]

    if not display_levels:
        st.warning("⚠️ Aucun niveau dans la distance configurée.")
    else:
        # Créer DataFrame pour affichage
        df_display = pd.DataFrame([{
            'Priorité': f"{l['Emoji']} {l['Priority']}",
            'Type': l['Type'],
            'Niveau': l['Nom'],
            'Prix': f"{l['Prix']:.2f}",
            'Distance': f"{l['Direction']} {l['Distance (ticks)']:.0f}t ({l['Distance (pts)']:.2f}pts)",
            'Status': l['Status']
        } for l in display_levels])

        st.dataframe(df_display, use_container_width=True, height=600)

    # ═══════════════════════════════════════════════════════════════
    # CONFLUENCES DÉTECTÉES
    # ═══════════════════════════════════════════════════════════════

    if confluences:
        st.markdown("<div class='section-title'>💎 Confluences Détectées</div>", unsafe_allow_html=True)

        for conf in confluences[:5]:  # Top 5
            dist_ticks, dist_pts, direction = calculate_distance(current_price, conf['price'])
            status, css_class = get_tradable_status(dist_ticks)

            st.markdown(f"""
            <div class="alert-box">
                <strong>💎 Confluence @ {conf['price']:.2f}</strong><br>
                <span class="pill {css_class}">{status}</span>
                <span class="pill neutral">{direction} {dist_ticks:.0f} ticks</span>
                <span class="pill neutral">{conf['count']} niveaux</span>
            </div>
            """, unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════
    # GRAPHIQUE PRIX + NIVEAUX
    # ═══════════════════════════════════════════════════════════════

    st.markdown("<div class='section-title'>📈 Visualisation Prix & Niveaux</div>", unsafe_allow_html=True)

    fig = go.Figure()

    # Ligne de prix actuel
    fig.add_hline(y=current_price, line_dash="dash", line_color="white",
                  annotation_text=f"Prix Actuel: {current_price:.2f}",
                  annotation_position="right")

    # Ajouter les niveaux tradables (vert)
    tradable_levels = [l for l in display_levels if l['CSS'] == 'tradable']
    if tradable_levels:
        fig.add_trace(go.Scatter(
            y=[l['Prix'] for l in tradable_levels],
            x=[l['Type'] for l in tradable_levels],
            mode='markers',
            marker=dict(size=15, color='#0fbf84', symbol='diamond'),
            name='Tradable (≤15t)',
            text=[f"{l['Nom']}<br>{l['Distance (ticks)']:.0f}t" for l in tradable_levels],
            hoverinfo='text'
        ))

    # Ajouter les niveaux proches (jaune)
    proche_levels = [l for l in display_levels if l['CSS'] == 'proche']
    if proche_levels:
        fig.add_trace(go.Scatter(
            y=[l['Prix'] for l in proche_levels],
            x=[l['Type'] for l in proche_levels],
            mode='markers',
            marker=dict(size=12, color='#f8c36b', symbol='circle'),
            name='Proche (≤30t)',
            text=[f"{l['Nom']}<br>{l['Distance (ticks)']:.0f}t" for l in proche_levels],
            hoverinfo='text'
        ))

    fig.update_layout(
        template='plotly_dark',
        height=500,
        xaxis_title="Type de Niveau",
        yaxis_title="Prix (NQ)",
        showlegend=True,
        hovermode='closest'
    )

    st.plotly_chart(fig, use_container_width=True)

    # Auto-refresh
    if auto_refresh:
        time.sleep(REFRESH_INTERVAL)
        st.rerun()


if __name__ == "__main__":
    main()








