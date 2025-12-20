#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DASHBOARD TEMPS RÉEL PRO - Monitoring Système MIA V3.3
======================================================

Dashboard enrichi avec :
- PnL temps réel + métriques avancées
- MIA Bullish Score + Sentiment
- Niveaux d'options (GEX, Résistances, Blind Spots)
- Tendance + VIX + Régime de volatilité
- Trades détaillés + Performance
- Drawdown + Latence pipeline
- Signaux ML en temps réel

Lancer avec : streamlit run core/dashboard_realtime.py

Author: MIA System + Claude Sonnet 4.5
Date: 4 Novembre 2025 - Version PRO
"""

import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, Optional
from core.market_context_analyzer import create_market_context_analyzer, MarketContext

# ═══════════════════════════════════════════════════════════════
# 🎨 MIA UI IMPORTS
# ═══════════════════════════════════════════════════════════════
from core.mia_animations import inject_mia_css, mia_header, mia_ticker_pnl, mia_event_toast, mia_kpi_card

# Configuration page
st.set_page_config(
    page_title="🤖 MIA Trading System - Dashboard PRO",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════
# INJECTION CSS PROFESSIONNEL
# ═══════════════════════════════════════════════════════════════

def inject_css():
    """Injecte le CSS professionnel pour le dark theme"""
    css_path = Path("core/dashboard_styles.css")
    if css_path.exists():
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()
            st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)
    else:
        st.warning("⚠️ Fichier CSS non trouvé. Le dashboard utilisera le style par défaut.")

# Injection du CSS
inject_css()

# ═══════════════════════════════════════════════════════════════
# HELPERS UI PROFESSIONNELS
# ═══════════════════════════════════════════════════════════════

def kpi_card(label: str, value: str, tone: str = "neutral") -> None:
    """Affiche une KPI Card professionnelle"""
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {tone}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def pill(label: str, tone: str = "neutral") -> str:
    """Retourne un badge pill stylé"""
    return f'<span class="pill {tone}">{label}</span>'

def section_title(icon: str, title: str) -> None:
    """Affiche un titre de section stylé"""
    st.markdown(f"<div class='section-title'>{icon} {title}</div>", unsafe_allow_html=True)

def bias_box(bias: str, score: float, recommendation: str) -> None:
    """Affiche une box bias stylée et centrée"""
    tone_class = "bullish" if bias == "LONG" else "bearish" if bias == "SHORT" else "neutral"
    tone_color = "#0fbf84" if bias == "LONG" else "#ef476f" if bias == "SHORT" else "#f8c36b"

    emoji = "🟢" if bias == "LONG" else "🔴" if bias == "SHORT" else "🟡"

    st.markdown(f"""
    <div class="bias-box {tone_class}">
        <div class="bias-title" style="color: {tone_color};">{emoji} {bias}</div>
        <div class="bias-subtitle">{recommendation}</div>
        <div class="bias-score">MIA Bullish Score: {score:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# FONCTIONS CHARGEMENT DONNÉES
# ═══════════════════════════════════════════════════════════════

@st.cache_data(ttl=5)  # Cache 5 secondes
def load_live_metrics():
    """Charge métriques temps réel depuis fichier JSON"""
    try:
        metrics_file = Path("data/live_metrics.json")
        if metrics_file.exists():
            with open(metrics_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    except Exception as e:
        st.error(f"Erreur chargement métriques: {e}")
        return None

@st.cache_data(ttl=2)  # Cache 2 secondes pour données les plus récentes
def load_latest_ml_ready(symbol: str) -> Optional[Dict[str, Any]]:
    """Charge les dernières données ML_READY pour un symbole"""
    try:
        today = datetime.now()
        month_map = {
            1: "JANVIER", 2: "FÉVRIER", 3: "MARS", 4: "AVRIL",
            5: "MAI", 6: "JUIN", 7: "JUILLET", 8: "AOÛT",
            9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DÉCEMBRE"
        }
        month_dir = month_map[today.month]
        date_str = today.strftime("%Y%m%d")

        # Déterminer le chart ID selon le symbole
        chart_id = "CHART_3" if symbol == "ES" else "CHART_9"

        # Chemin vers le fichier ML_READY (JSONL format)
        ml_ready_path = Path(f"DATA_SIERRA_CHART/DATA_2025/{month_dir}/{date_str}/{chart_id}/ML_READY")

        if ml_ready_path.exists():
            # Chercher fichiers .jsonl
            files = sorted(ml_ready_path.glob("*.jsonl"))
            if files:
                latest_file = files[-1]

                # Lire la dernière ligne du fichier JSONL
                with open(latest_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        if last_line:
                            latest_row = json.loads(last_line)

                            # Extraire les distances depuis menthor_distances (structure imbriquée)
                            menthor_dist = latest_row.get('menthor_distances', {})

                            # Ajouter les distances au niveau racine pour compatibilité
                            latest_row['dist_gex_call'] = menthor_dist.get('gamma0', 999999)
                            latest_row['dist_gex_put'] = menthor_dist.get('put0', 999999)
                            latest_row['dist_call'] = menthor_dist.get('call0', 999999)
                            latest_row['dist_put'] = menthor_dist.get('put0', 999999)
                            latest_row['dist_hvl'] = menthor_dist.get('hvl0', 999999)
                            latest_row['dist_blind_spot'] = menthor_dist.get('near_blind', 999999)

                            # ═════════════════════════════════════════════════════════
                            # CALCUL MIA BULLISH SCORE (si vide, le recalculer)
                            # ═════════════════════════════════════════════════════════

                            mia_bullish_raw = latest_row.get('mia_bullish_score', None)

                            # Si MIA Bullish Score est vide ou None, le RECALCULER
                            if mia_bullish_raw is None or mia_bullish_raw == 0:
                                # Recalcul basé sur plusieurs indicateurs
                                score_components = 0.0

                                # 1. Delta VWAP/ATR (poids: 40%)
                                d_vwap_atr = latest_row.get('d_vwap_atr', 0)
                                if d_vwap_atr != 0:
                                    # Normaliser entre -1 et 1 (clamp à ±5)
                                    vwap_normalized = max(-1, min(1, d_vwap_atr / 5.0))
                                    score_components += vwap_normalized * 0.4

                                # 2. Cumulative Delta Session (poids: 30%)
                                cum_delta = latest_row.get('cum_delta_session', 0)
                                if cum_delta != 0:
                                    # Normaliser basé sur volume typique (±500 = ±1)
                                    delta_normalized = max(-1, min(1, cum_delta / 500.0))
                                    score_components += delta_normalized * 0.3

                                # 3. Delta Percent (poids: 20%)
                                # NOTE: deltaPct = askPct - bidPct
                                # Positif = plus d'achats, Négatif = plus de ventes
                                delta_pct = latest_row.get('deltaPct', 0.0)  # 0.0 = neutral
                                # deltaPct est déjà dans [-1, 1], pas besoin de normaliser
                                score_components += delta_pct * 0.2

                                # 4. Position vs Value Area (poids: 10%)
                                in_value_area = latest_row.get('in_value_area', False)
                                mid = latest_row.get('mid', 0)
                                vva = latest_row.get('vva', {})
                                vah = vva.get('vah', 0)
                                val = vva.get('val', 0)

                                if vah and val and mid:
                                    if mid > vah:
                                        score_components += 0.1  # Au-dessus VAH = bullish
                                    elif mid < val:
                                        score_components -= 0.1  # En-dessous VAL = bearish

                                # Résultat final (entre -1 et 1)
                                mia_bullish_calculated = max(-1, min(1, score_components))
                                latest_row['mia_bullish_score'] = mia_bullish_calculated
                            else:
                                latest_row['mia_bullish_score'] = mia_bullish_raw

                            # ═════════════════════════════════════════════════════════
                            # CALCUL BIAS DE TRADING (LONG/SHORT/NEUTRAL)
                            # ═════════════════════════════════════════════════════════

                            bias = "NEUTRAL"
                            bias_score = 0

                            # MIA Bullish Score
                            mia_bullish = latest_row.get('mia_bullish_score', 0)
                            if mia_bullish > 0.3:
                                bias_score += 1
                            elif mia_bullish < -0.3:
                                bias_score -= 1

                            # Delta VWAP
                            d_vwap_atr = latest_row.get('d_vwap_atr', 0)
                            if d_vwap_atr > 0.2:
                                bias_score += 1
                            elif d_vwap_atr < -0.2:
                                bias_score -= 1

                            # Order Flow (utiliser deltaPct directement car plus précis que smart_money_flow)
                            # deltaPct est déjà normalisé dans [-1, 1]
                            delta_pct = latest_row.get('deltaPct', 0)
                            if delta_pct > 0.15:  # Plus de 15% de pression acheteuse
                                bias_score += 1
                            elif delta_pct < -0.15:  # Plus de 15% de pression vendeuse
                                bias_score -= 1

                            # Déterminer le bias final
                            if bias_score >= 2:
                                bias = "LONG"
                            elif bias_score <= -2:
                                bias = "SHORT"

                            latest_row['calculated_bias'] = bias
                            latest_row['bias_score'] = bias_score

                            return latest_row
        return None
    except Exception as e:
        st.error(f"Erreur chargement ML_READY: {e}")
        return None

@st.cache_data(ttl=10)
def load_drawdown_history():
    """Charge historique drawdowns"""
    try:
        dd_file = Path("data/drawdown_history.json")
        if dd_file.exists():
            with open(dd_file, 'r') as f:
                data = json.load(f)
            return pd.DataFrame(data)
        return None
    except Exception as e:
        st.error(f"Erreur chargement drawdowns: {e}")
        return None

@st.cache_data(ttl=30)
def load_trade_history():
    """Charge historique trades"""
    try:
        trades_file = Path("data/trade_history.json")
        if trades_file.exists():
            with open(trades_file, 'r') as f:
                data = json.load(f)
            return pd.DataFrame(data)
        return None
    except Exception as e:
        st.error(f"Erreur chargement trades: {e}")
        return None

# ═══════════════════════════════════════════════════════════════
# SIDEBAR - CONFIGURATION
# ═══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("<h2 class='page-title'>🤖 MIA System</h2>", unsafe_allow_html=True)
    st.caption("**V3.3 PRO** • Dashboard Temps Réel")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # Sélection symbole
    symbol = st.selectbox("📊 Symbole", ["ES", "NQ", "ALL"])

    # Période
    period = st.selectbox("📅 Période", ["Aujourd'hui", "7 derniers jours", "30 derniers jours"])

    # Auto-refresh
    auto_refresh = st.checkbox("🔄 Auto-refresh (5s)", value=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # Métriques système (avec KPI Cards)
    section_title("📊", "Métriques Système")

    metrics = load_live_metrics()
    if metrics:
        kpi_card("Status", "🟢 ACTIF", "success")
        kpi_card("Cycles", f"{metrics.get('total_cycles', 0):,}", "info")
        kpi_card("Signaux", str(metrics.get('total_signals', 0)), "accent")
        kpi_card("Uptime", f"{metrics.get('uptime_minutes', 0):.1f} min", "neutral")
        kpi_card("Session", metrics.get('session', 'N/A').upper(), "info")
        kpi_card("Régime Vol", metrics.get('vol_regime', 'N/A').upper(), "info")
    else:
        kpi_card("Status", "🔴 INACTIF", "danger")
        st.info("⚠️ Aucune donnée temps réel. Système démarré ?")

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
    st.caption(f"**Dernière mise à jour**: {datetime.now().strftime('%H:%M:%S')}")

    # Charger métriques pour le sidebar
    metrics = load_live_metrics()
    if metrics:
        st.markdown("---")
        st.markdown("### 📈 Système")
        st.markdown(f"**Cycles**: {metrics.get('total_cycles', 0):,}")
        st.markdown(f"**Signaux**: {metrics.get('total_signals', 0)}")
        st.markdown(f"**Uptime**: {metrics.get('uptime_minutes', 0):.1f} min")

        # Session
        session = metrics.get('session', 'N/A')
        session_emoji = {"ASIA": "🌏", "LONDON": "🇬🇧", "US": "🇺🇸"}.get(session, "🌍")
        st.markdown(f"**Session**: {session_emoji} {session}")

# ═══════════════════════════════════════════════════════════════
# 🎨 MIA THEME & HEADER
# ═══════════════════════════════════════════════════════════════

# Injection du CSS MIA
inject_mia_css()

# Charger données ML_READY pour déterminer états
ml_data_es = load_latest_ml_ready("ES")
ml_data_nq = load_latest_ml_ready("NQ")
ml_data = ml_data_es if ml_data_es else ml_data_nq if ml_data_nq else {}

# Déterminer états pour header
bot_active = metrics.get('total_cycles', 0) > 0 if metrics else False
auto_sig = "WAIT"  # Par défaut
lat_ms = int(metrics.get('avg_latency_ms', 0)) if metrics else None

# Si on a des données ML, analyser pour auto_signal
if ml_data:
    try:
        analyzer_temp = create_market_context_analyzer(symbol)
        ctx_temp = analyzer_temp.analyze(ml_data)
        auto_sig = ctx_temp.auto_signal
    except:
        pass

# Afficher header MIA
mia_header(bot_active=bot_active, auto_signal=auto_sig, latency_ms=lat_ms)

# Ticker PnL animé
pnl_total = metrics.get('total_pnl_net', 0.0) if metrics else 0.0
bias_text = ml_data.get('calculated_bias', 'NEUTRAL') if ml_data else 'NEUTRAL'
pnl_str = f"PNL: {'+' if pnl_total>=0 else ''}{pnl_total:.2f} $  |  Symbole: {symbol}  |  Bias: {bias_text}"
mia_ticker_pnl(pnl_str)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════
# HEADER - MÉTRIQUES PRINCIPALES
# ═══════════════════════════════════════════════════════════════

st.title("📊 Dashboard Temps Réel - MIA Trading System")
st.markdown(f"**{datetime.now().strftime('%A %d %B %Y - %H:%M:%S')}**")

metrics = load_live_metrics()

if metrics:
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        pnl = metrics.get('total_pnl_net', 0)
        pnl_color = "normal" if pnl >= 0 else "inverse"
        st.metric("💰 PnL Net", f"${pnl:.2f}", delta=f"{metrics.get('pnl_delta', 0):.2f}", delta_color=pnl_color)

    with col2:
        win_rate = metrics.get('win_rate', 0)
        st.metric("🎯 Win Rate", f"{win_rate:.1%}", delta=None)

    with col3:
        trades = metrics.get('total_trades', 0)
        st.metric("📝 Trades", f"{trades}", delta=None)

    with col4:
        dd = metrics.get('current_dd_pct', 0)
        dd_color = "normal" if dd < 0.10 else "inverse"
        st.metric("📉 Drawdown", f"{dd:.2%}", delta=None, delta_color=dd_color)

    with col5:
        latency = metrics.get('avg_latency_ms', 0)
        latency_color = "normal" if latency < 100 else "inverse"
        st.metric("⚡ Latence", f"{latency:.1f}ms", delta=None, delta_color=latency_color)

    with col6:
        cycles = metrics.get('total_cycles', 0)
        st.metric("🔄 Cycles", f"{cycles:,}", delta=None)

else:
    st.warning("⚠️ Aucune donnée temps réel disponible. Système démarré ?")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════
# SECTION ENRICHIE - MIA BULLISH, TENDANCE, VIX, NIVEAUX OPTIONS
# ═══════════════════════════════════════════════════════════════

# Charger données ML_READY pour le symbole sélectionné
if symbol in ["ES", "NQ"]:
    ml_data = load_latest_ml_ready(symbol)

    if ml_data:
        st.subheader(f"📊 État du Marché - {symbol}")

        # ═══════════════════════════════════════════════════════════════
        # 🎯 BIAS DE TRADING - SECTION PRINCIPALE
        # ═══════════════════════════════════════════════════════════════

        bias = ml_data.get('calculated_bias', 'NEUTRAL')
        bias_score = ml_data.get('bias_score', 0)

        # Déterminer texte et recommandation
        if bias == "LONG":
            bias_text = "PRIVILÉGIER LONG"
            bias_recommendation = "✅ Favoriser les positions ACHETEUSES (BUY)"
        elif bias == "SHORT":
            bias_text = "PRIVILÉGIER SHORT"
            bias_recommendation = "✅ Favoriser les positions VENDEUSES (SELL)"
        else:
            bias_text = "NEUTRAL - PRUDENCE"
            bias_recommendation = "⚠️ Pas de direction claire - Attendre confirmation"

        # Affichage du BIAS avec le nouveau composant stylé
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        section_title("🎯", "BIAS DE TRADING")

        # Container centré pour le BIAS (nouvelle version stylée)
        col_bias1, col_bias2, col_bias3 = st.columns([1, 2, 1])
        with col_bias2:
            bias_box(bias_text, bias_score, bias_recommendation)

        st.markdown("---")

        # ═══════════════════════════════════════════════════════════════
        # 🧠 ANALYSE CONTEXTUELLE ET PLANS DE TRADING
        # ═══════════════════════════════════════════════════════════════

        st.subheader("🧠 Analyse Contextuelle & Plans de Trading")

        # Créer l'analyseur et générer le contexte
        analyzer = create_market_context_analyzer(symbol)
        market_context = analyzer.analyze(ml_data)

        # ═══════════════════════════════════════════════════════════════
        # 🎨 MIA EVENT TOASTS (Gamma Flip & Alertes)
        # ═══════════════════════════════════════════════════════════════

        # Toasts pour événements Gamma Flip
        for msg in (market_context.proximity_alerts or []):
            if "Gamma Flip" in msg:
                mia_event_toast(msg)
                break  # Éviter la rafale de toasts

        # Onglets pour organiser l'information
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Contexte",
            "🎯 Plans de Trading",
            "🧲 Niveaux Aimants",
            "⚠️ Alertes"
        ])

        with tab1:
            # Contexte de marché
            st.markdown("#### 📍 Position Actuelle")

            col1, col2, col3 = st.columns(3)

            with col1:
                pos_hvl_emoji = "🟢" if market_context.position_vs_hvl == "above" else "🔴" if market_context.position_vs_hvl == "below" else "🟡"
                st.metric(
                    "Position vs HVL",
                    market_context.position_vs_hvl.upper(),
                    delta=None,
                    delta_color="off"
                )
                st.markdown(f"{pos_hvl_emoji} **{market_context.position_vs_hvl.capitalize()}** HVL")

            with col2:
                pos_vwap_emoji = "🟢" if market_context.position_vs_vwap == "above" else "🔴" if market_context.position_vs_vwap == "below" else "🟡"
                st.metric(
                    "Position vs VWAP",
                    market_context.position_vs_vwap.upper(),
                    delta=None,
                    delta_color="off"
                )
                st.markdown(f"{pos_vwap_emoji} **{market_context.position_vs_vwap.capitalize()}** VWAP")

            with col3:
                pos_va_emoji = "🟢" if market_context.position_vs_value_area == "inside" else "🔵" if market_context.position_vs_value_area == "above" else "🔴"
                st.metric(
                    "Position vs Value Area",
                    market_context.position_vs_value_area.upper(),
                    delta=None,
                    delta_color="off"
                )
                st.markdown(f"{pos_va_emoji} **{market_context.position_vs_value_area.capitalize()}** Value Area")

            st.markdown("---")

            # Conditions de marché
            st.markdown("#### 🌡️ Conditions de Marché")

            col1, col2, col3 = st.columns(3)

            with col1:
                bias_emoji = "🟢" if market_context.main_bias == "BULLISH" else "🔴" if market_context.main_bias == "BEARISH" else "🟡"
                bias_color_ctx = "#00e676" if market_context.main_bias == "BULLISH" else "#ff1744" if market_context.main_bias == "BEARISH" else "#ffd600"
                st.markdown(f"**Biais Principal**: {bias_emoji} <span style='color: {bias_color_ctx};'>{market_context.main_bias}</span>", unsafe_allow_html=True)

            with col2:
                of_emoji = "💪" if market_context.orderflow_pressure == "BUYING" else "📉" if market_context.orderflow_pressure == "SELLING" else "⚖️"
                st.markdown(f"**Order Flow**: {of_emoji} {market_context.orderflow_pressure}")

            with col3:
                gamma_emoji = "🔵" if market_context.gamma_condition == "POSITIVE" else "🔴" if market_context.gamma_condition == "NEGATIVE" else "⚪"
                st.markdown(f"**Gamma**: {gamma_emoji} {market_context.gamma_condition}")

            st.markdown("---")

            # ═══════════════════════════════════════════════════════════════
            # 🚀 NOUVELLES FEATURES PRO V3.3
            # ═══════════════════════════════════════════════════════════════

            st.markdown("#### 🚀 Analyse Avancée PRO")

            col1, col2, col3 = st.columns(3)

            with col1:
                # Bias Strength avec barre de progression
                bias_strength = market_context.bias_strength
                strength_pct = (bias_strength + 1.0) / 2.0  # Normaliser de -1/+1 vers 0/1
                strength_color = "#00e676" if bias_strength > 0.4 else "#ff1744" if bias_strength < -0.4 else "#ffd600"

                st.markdown(f"**💪 Bias Strength**: <span style='color: {strength_color};'>{bias_strength:.3f}</span>", unsafe_allow_html=True)
                st.progress(strength_pct)

                # Légende
                if abs(bias_strength) > 0.6:
                    st.markdown(f"<small style='color: {strength_color};'>✅ FORT</small>", unsafe_allow_html=True)
                elif abs(bias_strength) > 0.3:
                    st.markdown(f"<small style='color: {strength_color};'>⚠️ MOYEN</small>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<small style='color: {strength_color};'>❌ FAIBLE</small>", unsafe_allow_html=True)

            with col2:
                # Auto Signal (BUY/SELL/WAIT)
                auto_signal = market_context.auto_signal
                signal_emoji = "🟢" if auto_signal == "BUY" else "🔴" if auto_signal == "SELL" else "🟡"
                signal_color = "#00e676" if auto_signal == "BUY" else "#ff1744" if auto_signal == "SELL" else "#ffd600"

                st.markdown(f"**🤖 Auto Signal**: {signal_emoji} <span style='color: {signal_color}; font-size: 1.2em; font-weight: bold;'>{auto_signal}</span>", unsafe_allow_html=True)

                # Explication
                if auto_signal == "BUY":
                    st.markdown("<small>✅ Conditions réunies pour LONG</small>", unsafe_allow_html=True)
                elif auto_signal == "SELL":
                    st.markdown("<small>✅ Conditions réunies pour SHORT</small>", unsafe_allow_html=True)
                else:
                    st.markdown("<small>⏳ Attendre confirmation</small>", unsafe_allow_html=True)

            with col3:
                # Gamma Flip Detection
                gamma_flip = market_context.gamma_flip_detected
                if gamma_flip:
                    flip_emoji = "🔼" if gamma_flip == "UP" else "🔻"
                    flip_color = "#00e676" if gamma_flip == "UP" else "#ff1744"
                    st.markdown(f"**⚡ Gamma Flip**: {flip_emoji} <span style='color: {flip_color};'>**{gamma_flip}**</span>", unsafe_allow_html=True)

                    if gamma_flip == "UP":
                        st.markdown("<small>📈 Retour zone stable</small>", unsafe_allow_html=True)
                    else:
                        st.markdown("<small>📉 Risque accélération</small>", unsafe_allow_html=True)
                else:
                    st.markdown("**⚡ Gamma Flip**: ⚪ Aucun")
                    st.markdown("<small>Stable (pas de flip)</small>", unsafe_allow_html=True)

            st.markdown("---")

            # ═══════════════════════════════════════════════════════════════
            # 🧭 GRAPHIQUE ZONES VISUELLES (VWAP/VAH/VAL/HVL)
            # ═══════════════════════════════════════════════════════════════

            st.markdown("#### 🧭 Zones Clés & Prix Actuel")

            mid = ml_data.get('mid', 0.0) or 0.0

            # Créer graphique Plotly
            fig_zones = go.Figure()

            # Prix actuel (marker principal)
            fig_zones.add_trace(go.Scatter(
                x=[0],
                y=[mid],
                mode='markers+text',
                text=[f"Prix: {mid:.2f}"],
                textposition="top center",
                textfont=dict(size=14, color='#FFD700'),
                marker=dict(
                    size=20,
                    color='#FFD700',
                    symbol='diamond',
                    line=dict(color='#FFF', width=2)
                ),
                name="Prix Actuel",
                showlegend=False
            ))

            # Ajouter lignes horizontales pour chaque zone
            if market_context.visual_zones:
                for zone in market_context.visual_zones:
                    y_val = zone.get('y')
                    label = zone.get('label', '')
                    color = zone.get('color', '#FFFFFF')

                    if y_val:
                        # Ligne horizontale
                        fig_zones.add_hline(
                            y=y_val,
                            line_dash="dash",
                            line_color=color,
                            line_width=2,
                            annotation_text=f"{label}: {y_val:.2f}",
                            annotation_position="right",
                            annotation_font=dict(size=11, color=color)
                        )

            # Styling du graphique
            ymin = mid - 40  # Range ± 40 points autour du prix
            ymax = mid + 40

            fig_zones.update_layout(
                height=350,
                margin=dict(l=10, r=80, t=10, b=10),
                xaxis=dict(
                    visible=False,
                    range=[-0.5, 0.5]
                ),
                yaxis=dict(
                    range=[ymin, ymax],
                    title="Prix",
                    titlefont=dict(size=12),
                    gridcolor='rgba(128, 128, 128, 0.2)'
                ),
                plot_bgcolor='rgba(0, 0, 0, 0)',
                paper_bgcolor='rgba(0, 0, 0, 0)',
                template="plotly_dark",
                hovermode='y'
            )

            st.plotly_chart(fig_zones, use_container_width=True)

            st.markdown("---")

            # Raisonnement
            st.markdown("#### 💡 Raisonnement")
            st.info(market_context.reasoning)

        with tab2:
            # Plans de trading
            st.markdown("#### 🎯 Scénarios de Trading")

            if not market_context.trading_plans:
                st.warning("Aucun plan de trading disponible pour le moment. Conditions de marché en attente de clarification.")
            else:
                for i, plan in enumerate(market_context.trading_plans, 1):
                    # Déterminer la couleur selon le plan
                    plan_color = "#00e676" if plan.direction == "LONG" else "#ff1744"
                    plan_emoji = "🟢" if plan.direction == "LONG" else "🔴"
                    priority_stars = "⭐" * plan.priority

                    # Créer un expander pour chaque plan
                    with st.expander(f"{plan_emoji} **Plan {i}**: {plan.scenario.value.upper().replace('_', ' ')} - {plan.direction} {priority_stars}", expanded=(i == 1)):
                        col1, col2 = st.columns([2, 1])

                        with col1:
                            st.markdown(f"**🎯 Déclencheur**:")
                            st.markdown(f"> {plan.trigger}")

                            st.markdown(f"**📍 Zone d'Entrée**: {plan.entry_zone[0]:.2f} - {plan.entry_zone[1]:.2f}")
                            st.markdown(f"**🛑 Stop Loss**: {plan.stop_loss:.2f}")
                            st.markdown(f"**🎁 TP1**: {plan.take_profit_1:.2f}")
                            st.markdown(f"**🎁 TP2**: {plan.take_profit_2:.2f}")
                            if plan.take_profit_3:
                                st.markdown(f"**🎁 TP3**: {plan.take_profit_3:.2f}")

                            st.markdown(f"**⚖️ Risk/Reward**: {plan.risk_reward:.2f}:1")
                            st.markdown(f"**📊 Confiance**: {plan.confidence:.0%}")

                        with col2:
                            # Mini graphique du plan
                            import plotly.graph_objects as go

                            entry_avg = (plan.entry_zone[0] + plan.entry_zone[1]) / 2
                            prices = [plan.stop_loss, entry_avg, plan.take_profit_1, plan.take_profit_2]
                            if plan.take_profit_3:
                                prices.append(plan.take_profit_3)

                            fig = go.Figure()

                            # Zone d'entrée
                            fig.add_trace(go.Scatter(
                                x=[0, 1],
                                y=[plan.entry_zone[0], plan.entry_zone[1]],
                                fill='tozeroy',
                                fillcolor='rgba(33, 150, 243, 0.2)',
                                line=dict(color='#2196f3', width=2),
                                name='Zone Entrée',
                                showlegend=False
                            ))

                            # SL
                            fig.add_shape(
                                type="line",
                                x0=0, x1=1,
                                y0=plan.stop_loss, y1=plan.stop_loss,
                                line=dict(color="#ff1744", width=2, dash="dash"),
                            )

                            # TPs
                            for tp in [plan.take_profit_1, plan.take_profit_2, plan.take_profit_3]:
                                if tp:
                                    fig.add_shape(
                                        type="line",
                                        x0=0, x1=1,
                                        y0=tp, y1=tp,
                                        line=dict(color="#00e676", width=1, dash="dot"),
                                    )

                            fig.update_layout(
                                height=250,
                                margin=dict(l=10, r=10, t=10, b=10),
                                showlegend=False,
                                xaxis=dict(showticklabels=False, showgrid=False),
                                yaxis=dict(title="Prix", side="right"),
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                            )

                            st.plotly_chart(fig, use_container_width=True, key=f"plan_{i}")

                        st.markdown("---")
                        st.markdown(f"**❌ Invalidation**: {plan.invalidation}")
                        st.markdown(f"**⚙️ Gestion**: {plan.management}")

        with tab3:
            # Niveaux Aimants
            st.markdown("#### 🧲 Niveaux Aimants (Magnets)")
            st.markdown("*Niveaux susceptibles d'attirer le prix*")

            if not market_context.key_magnets:
                st.info("Aucun niveau aimant identifié pour le moment.")
            else:
                for magnet in market_context.key_magnets[:10]:  # Top 10 magnets
                    dist = magnet['distance']
                    dist_color = "#00e676" if dist > 0 else "#ff1744"
                    dist_sign = "+" if dist > 0 else ""

                    strength_emoji = "🔥" if magnet['strength'] == 'high' else "⚡" if magnet['strength'] == 'medium' else "✨"

                    col1, col2, col3 = st.columns([2, 1, 1])

                    with col1:
                        st.markdown(f"{strength_emoji} **{magnet['type']}**: {magnet['description']}")

                    with col2:
                        st.markdown(f"**{magnet['price']:.2f}**")

                    with col3:
                        st.markdown(f"<span style='color: {dist_color};'>{dist_sign}{dist:.2f} pts</span>", unsafe_allow_html=True)

                    st.markdown("---")

        with tab4:
            # Alertes de proximité
            st.markdown("#### ⚠️ Alertes de Proximité")

            if not market_context.proximity_alerts:
                st.success("✅ Aucune alerte de proximité. Marché dans une zone neutre.")
            else:
                for alert in market_context.proximity_alerts:
                    st.warning(alert)

        st.markdown("---")

        # Ligne 1: MIA Bullish, Tendance, VIX, ATR
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            bullish_score = ml_data.get('mia_bullish_score', 0)
            # Déterminer couleur et emoji
            if bullish_score > 0.6:
                sentiment = "🟢 BULLISH"
                sentiment_color = "#00e676"
            elif bullish_score < -0.6:
                sentiment = "🔴 BEARISH"
                sentiment_color = "#ff1744"
            else:
                sentiment = "🟡 NEUTRAL"
                sentiment_color = "#ffd600"

            st.markdown(f"### 🎯 MIA Bullish")
            st.markdown(f"<h2 style='color: {sentiment_color};'>{bullish_score:.2f}</h2>", unsafe_allow_html=True)
            st.markdown(f"**Sentiment**: {sentiment}")

        with col2:
            # Tendance (Delta VWAP)
            d_vwap = ml_data.get('d_vwap', 0)
            d_vwap_atr = ml_data.get('d_vwap_atr', 0)

            if d_vwap_atr > 0.5:
                trend = "📈 HAUSSE"
                trend_color = "#00e676"
            elif d_vwap_atr < -0.5:
                trend = "📉 BAISSE"
                trend_color = "#ff1744"
            else:
                trend = "➡️ RANGE"
                trend_color = "#ffd600"

            st.markdown(f"### 📊 Tendance")
            st.markdown(f"<h2 style='color: {trend_color};'>{d_vwap:.2f}</h2>", unsafe_allow_html=True)
            st.markdown(f"**Status**: {trend}")
            st.markdown(f"*D_VWAP/ATR: {d_vwap_atr:.2f}*")

        with col3:
            # VIX
            vix = ml_data.get('vix', 0)

            if vix < 15:
                vix_level = "🟢 BAS"
                vix_color = "#00e676"
            elif vix < 20:
                vix_level = "🟡 MOYEN"
                vix_color = "#ffd600"
            elif vix < 30:
                vix_level = "🟠 ÉLEVÉ"
                vix_color = "#ff9100"
            else:
                vix_level = "🔴 TRÈS ÉLEVÉ"
                vix_color = "#ff1744"

            st.markdown(f"### 📊 VIX")
            st.markdown(f"<h2 style='color: {vix_color};'>{vix:.1f}</h2>", unsafe_allow_html=True)
            st.markdown(f"**Niveau**: {vix_level}")

        with col4:
            # ATR
            atr = ml_data.get('atr', 0)
            mid_price = ml_data.get('mid', 0)
            atr_pct = (atr / mid_price * 100) if mid_price > 0 else 0

            st.markdown(f"### 📏 ATR")
            st.markdown(f"<h2 style='color: #2196f3;'>{atr:.2f}</h2>", unsafe_allow_html=True)
            st.markdown(f"**%**: {atr_pct:.2%}")
            st.markdown(f"*Prix: {mid_price:.2f}*")

        st.markdown("---")

        # ═══════════════════════════════════════════════════════════════
        # 🔬 FEATURES AVANCÉES - NOUVELLES MÉTRIQUES V3.1
        # ═══════════════════════════════════════════════════════════════

        st.subheader("🔬 Features Avancées ML (V3.1)")

        # Row 1: MIA Bullish Score + Gamma Flip
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            mia_score = ml_data.get('mia_bullish_score', 0)
            mia_trend = "🟢 BULLISH" if mia_score > 0.3 else "🔴 BEARISH" if mia_score < -0.3 else "🟡 NEUTRAL"
            mia_color = "success" if mia_score > 0.3 else "error" if mia_score < -0.3 else "warning"
            st.metric(
                "🧠 MIA Bullish Score",
                f"{mia_score:.3f}",
                delta=mia_trend,
                delta_color="off"
            )

        with col2:
            gamma_side = ml_data.get('gamma_side', 'unknown')
            gamma_level = ml_data.get('gamma_wall_level', 0)
            gamma_emoji = "🔵" if gamma_side == "above" else "🟠" if gamma_side == "below" else "⚪"
            gamma_text = f"{gamma_emoji} {gamma_side.upper()}"

            flip_up = ml_data.get('gamma_flip_up', False)
            flip_down = ml_data.get('gamma_flip_down', False)
            flip_status = "🔔 FLIP UP!" if flip_up else "🔔 FLIP DOWN!" if flip_down else gamma_text

            st.metric(
                "🎲 Gamma Position",
                f"{gamma_level:.2f}" if gamma_level > 0 else "N/A",
                delta=flip_status,
                delta_color="off"
            )

        with col3:
            sell_pct = ml_data.get('sell_pct', 0) * 100
            buy_pct = ml_data.get('buy_pct', 0) * 100
            flow_emoji = "🟢" if buy_pct > 60 else "🔴" if sell_pct > 60 else "🟡"
            st.metric(
                f"{flow_emoji} Order Flow",
                f"Buy {buy_pct:.1f}%",
                delta=f"Sell {sell_pct:.1f}%",
                delta_color="off"
            )

        with col4:
            delta_flip = ml_data.get('delta_flip', False)
            delta_burst = ml_data.get('delta_burst', 0)
            flip_emoji = "🔄" if delta_flip else "➡️"
            st.metric(
                f"{flip_emoji} Delta Status",
                f"Burst: {delta_burst}",
                delta="FLIP!" if delta_flip else "Stable",
                delta_color="inverse" if delta_flip else "off"
            )

        st.markdown("")

        # Row 2: Wicks + DOM Stacked Imbalance
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            upper_wick = ml_data.get('upper_wick_ticks', 0)
            wick_strength_up = "FORTE" if upper_wick > 5 else "MOYENNE" if upper_wick > 2 else "FAIBLE"
            wick_emoji_up = "🔴" if upper_wick > 5 else "🟠" if upper_wick > 2 else "🟢"
            st.metric(
                f"{wick_emoji_up} Mèche Haute",
                f"{upper_wick:.1f} ticks",
                delta=f"Rejet: {wick_strength_up}",
                delta_color="off"
            )

        with col2:
            lower_wick = ml_data.get('lower_wick_ticks', 0)
            wick_strength_low = "FORTE" if lower_wick > 5 else "MOYENNE" if lower_wick > 2 else "FAIBLE"
            wick_emoji_low = "🟢" if lower_wick > 5 else "🟠" if lower_wick > 2 else "🔴"
            st.metric(
                f"{wick_emoji_low} Mèche Basse",
                f"{lower_wick:.1f} ticks",
                delta=f"Support: {wick_strength_low}",
                delta_color="off"
            )

        with col3:
            total_range = ml_data.get('total_range_ticks', 0)
            range_emoji = "🔥" if total_range > 10 else "🌊" if total_range > 5 else "🟦"
            range_status = "FORTE" if total_range > 10 else "MOYENNE" if total_range > 5 else "FAIBLE"
            st.metric(
                f"{range_emoji} Range Total",
                f"{total_range:.1f} ticks",
                delta=f"Vol: {range_status}",
                delta_color="off"
            )

        with col4:
            stacked_bid = ml_data.get('stacked_imbalance_bid_rows', 0)
            stacked_ask = ml_data.get('stacked_imbalance_ask_rows', 0)
            stack_emoji = "🟢" if stacked_bid > 2 else "🔴" if stacked_ask > 2 else "⚪"
            stack_text = f"BID {stacked_bid} | ASK {stacked_ask}"
            st.metric(
                f"{stack_emoji} Stacked DOM",
                stack_text,
                delta="Murs empilés" if (stacked_bid > 2 or stacked_ask > 2) else "Équilibré",
                delta_color="off"
            )

        st.markdown("---")

        # Ligne 2: Niveaux d'Options Proches
        st.subheader(f"🎯 Niveaux d'Options Proches - {symbol}")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # GEX le plus proche
            st.markdown("### 🔵 GEX Proche")
            dist_gex_call = ml_data.get('dist_gex_call', 999999)
            dist_gex_put = ml_data.get('dist_gex_put', 999999)

            # Vérifier si les données sont valides
            if dist_gex_call == 999999 and dist_gex_put == 999999:
                st.markdown("<p style='color: #9e9e9e;'>Données non disponibles</p>", unsafe_allow_html=True)
            else:
                # Prendre le plus proche
                if abs(dist_gex_call) < abs(dist_gex_put):
                    closest_gex_dist = dist_gex_call
                    gex_type = "CALL"
                else:
                    closest_gex_dist = dist_gex_put
                    gex_type = "PUT"

                # Calculer le niveau absolu
                mid_price = ml_data.get('mid', 0)
                closest_gex_level = mid_price + closest_gex_dist

                dist_color = "#00e676" if closest_gex_dist > 0 else "#ff1744"
                st.markdown(f"<h3 style='color: {dist_color};'>{closest_gex_level:.2f}</h3>", unsafe_allow_html=True)
                st.markdown(f"**Type**: {gex_type}")
                st.markdown(f"**Distance**: {closest_gex_dist:.2f} pts")

        with col2:
            # Résistance CALL la plus proche
            st.markdown("### 🔴 Résistance CALL")
            call_resist = ml_data.get('call_resistance', 0)
            dist_call = ml_data.get('dist_call', 999999)
            mid_price = ml_data.get('mid', 0)

            if dist_call == 999999:
                st.markdown("<p style='color: #9e9e9e;'>Données non disponibles</p>", unsafe_allow_html=True)
            else:
                dist_color = "#00e676" if dist_call > 0 else "#ff1744"
                st.markdown(f"<h3 style='color: {dist_color};'>{call_resist:.2f}</h3>", unsafe_allow_html=True)
                st.markdown(f"**Distance**: {dist_call:.2f} pts")
                st.markdown(f"*Prix actuel: {mid_price:.2f}*")

        with col3:
            # Support PUT le plus proche
            st.markdown("### 🟢 Support PUT")
            put_support = ml_data.get('put_support', 0)
            dist_put = ml_data.get('dist_put', 999999)
            mid_price = ml_data.get('mid', 0)

            if dist_put == 999999:
                st.markdown("<p style='color: #9e9e9e;'>Données non disponibles</p>", unsafe_allow_html=True)
            else:
                dist_color = "#00e676" if dist_put > 0 else "#ff1744"
                st.markdown(f"<h3 style='color: {dist_color};'>{put_support:.2f}</h3>", unsafe_allow_html=True)
                st.markdown(f"**Distance**: {dist_put:.2f} pts")
                st.markdown(f"*Prix actuel: {mid_price:.2f}*")

        with col4:
            # Blind Spot le plus proche
            st.markdown("### ⚪ Blind Spot")
            dist_blind = ml_data.get('dist_blind_spot', 999999)
            mid_price = ml_data.get('mid', 0)

            if dist_blind == 999999:
                st.markdown("<p style='color: #9e9e9e;'>Données non disponibles</p>", unsafe_allow_html=True)
            else:
                blind_spot_level = mid_price + dist_blind
                dist_color = "#2196f3"
                st.markdown(f"<h3 style='color: {dist_color};'>{blind_spot_level:.2f}</h3>", unsafe_allow_html=True)
                st.markdown(f"**Distance**: {dist_blind:.2f} pts")
                st.markdown(f"*Prix actuel: {mid_price:.2f}*")

        st.markdown("---")

        # Ligne 3: Corrélation et Régime
        col1, col2, col3 = st.columns(3)

        with col1:
            # Corrélation ES/NQ
            corr = ml_data.get('corr_es_nq', 0)

            if abs(corr) > 0.7:
                corr_level = "🔴 FORTE"
                corr_color = "#ff1744"
            elif abs(corr) > 0.4:
                corr_level = "🟡 MOYENNE"
                corr_color = "#ffd600"
            else:
                corr_level = "🟢 FAIBLE"
                corr_color = "#00e676"

            st.markdown(f"### 🔗 Corrélation ES/NQ")
            st.markdown(f"<h3 style='color: {corr_color};'>{corr:.3f}</h3>", unsafe_allow_html=True)
            st.markdown(f"**Niveau**: {corr_level}")

        with col2:
            # Régime de volatilité
            vol_regime = metrics.get('vol_regime', 'N/A') if metrics else 'N/A'

            regime_map = {
                "low_vol": ("🟢 FAIBLE", "#00e676"),
                "normal_vol": ("🟡 NORMALE", "#ffd600"),
                "high_vol": ("🔴 ÉLEVÉE", "#ff1744"),
                "transitioning": ("🟠 TRANSITION", "#ff9100")
            }

            regime_text, regime_color = regime_map.get(vol_regime, ("⚪ N/A", "#9e9e9e"))

            st.markdown(f"### 📊 Régime Vol")
            st.markdown(f"<h3 style='color: {regime_color};'>{regime_text}</h3>", unsafe_allow_html=True)

        with col3:
            # Session de trading
            session = metrics.get('session', 'N/A') if metrics else 'N/A'
            session_emoji = {"ASIA": "🌏", "LONDON": "🇬🇧", "US": "🇺🇸"}.get(session, "🌍")

            session_color_map = {
                "ASIA": "#ff9100",
                "LONDON": "#2196f3",
                "US": "#00e676"
            }
            session_color = session_color_map.get(session, "#9e9e9e")

            st.markdown(f"### 🌍 Session")
            st.markdown(f"<h3 style='color: {session_color};'>{session_emoji} {session}</h3>", unsafe_allow_html=True)

        st.markdown("---")
    else:
        st.warning(f"⚠️ Pas de données ML_READY disponibles pour {symbol}")
        st.info("""
        📁 **Chemin attendu des données:**
        - ES: `DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251104/CHART_3/ML_READY/*.jsonl`
        - NQ: `DATA_SIERRA_CHART/DATA_2025/NOVEMBRE/20251104/CHART_9/ML_READY/*.jsonl`

        💡 **Pour afficher les données enrichies:**
        1. Assurez-vous que Sierra Chart est en cours d'exécution
        2. Vérifiez que les fichiers ML_READY (.jsonl) sont générés
        3. Le dashboard se met à jour automatiquement toutes les 2 secondes

        ⏳ **En attendant, vous pouvez voir:**
        - Les métriques système (cycles, signaux, uptime)
        - Les graphiques PnL et Drawdown (si trades disponibles)
        - L'historique des trades
        """)

# ═══════════════════════════════════════════════════════════════
# SECTION 1 - GRAPHIQUE PNL
# ═══════════════════════════════════════════════════════════════

st.subheader("📈 PnL Temps Réel")

# Charger historique drawdown (contient PnL)
dd_history = load_drawdown_history()

if dd_history is not None and not dd_history.empty:
    # Préparer données
    dd_history['timestamp'] = pd.to_datetime(dd_history['timestamp'])
    dd_history = dd_history.sort_values('timestamp')

    # Graphique PnL
    fig_pnl = go.Figure()

    fig_pnl.add_trace(go.Scatter(
        x=dd_history['timestamp'],
        y=dd_history['current_pnl'],
        mode='lines',
        name='PnL Net',
        line=dict(color='rgb(0, 176, 246)', width=2)
    ))

    fig_pnl.add_trace(go.Scatter(
        x=dd_history['timestamp'],
        y=dd_history['peak_pnl'],
        mode='lines',
        name='Peak PnL',
        line=dict(color='rgb(0, 230, 118)', width=1, dash='dash')
    ))

    fig_pnl.update_layout(
        title="PnL & Peak",
        xaxis_title="Temps",
        yaxis_title="PnL ($)",
        height=400,
        hovermode='x unified'
    )

    st.plotly_chart(fig_pnl, use_container_width=True)

else:
    st.info("ℹ️ Pas de données PnL disponibles")

# ═══════════════════════════════════════════════════════════════
# SECTION 2 - DRAWDOWN
# ═══════════════════════════════════════════════════════════════

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔴 Drawdown")

    if dd_history is not None and not dd_history.empty:
        fig_dd = go.Figure()

        fig_dd.add_trace(go.Scatter(
            x=dd_history['timestamp'],
            y=dd_history['current_dd_pct'] * 100,
            mode='lines',
            name='Drawdown %',
            fill='tozeroy',
            line=dict(color='rgb(255, 65, 54)', width=2)
        ))

        # Ligne seuil max DD (15%)
        fig_dd.add_hline(y=15, line_dash="dash", line_color="red",
                         annotation_text="Max DD (15%)")

        fig_dd.update_layout(
            xaxis_title="Temps",
            yaxis_title="Drawdown (%)",
            height=300,
            hovermode='x unified'
        )

        st.plotly_chart(fig_dd, use_container_width=True)
    else:
        st.info("ℹ️ Pas de données drawdown")

with col2:
    st.subheader("⏱️ Latence Pipeline")

    if metrics:
        latency_data = metrics.get('latency_breakdown', {})

        if latency_data:
            stages = list(latency_data.keys())
            values = list(latency_data.values())

            fig_latency = go.Figure(data=[
                go.Bar(x=stages, y=values, marker_color='rgb(158, 202, 225)')
            ])

            fig_latency.update_layout(
                xaxis_title="Stage",
                yaxis_title="Latence (ms)",
                height=300
            )

            st.plotly_chart(fig_latency, use_container_width=True)
        else:
            st.info("ℹ️ Pas de données latence")
    else:
        st.info("ℹ️ Pas de données latence")

# ═══════════════════════════════════════════════════════════════
# SECTION 3 - TRADES RÉCENTS
# ═══════════════════════════════════════════════════════════════

st.markdown("---")
st.subheader("📝 Trades Récents")

trade_history = load_trade_history()

if trade_history is not None and not trade_history.empty:
    # Préparer données
    trade_history['timestamp'] = pd.to_datetime(trade_history['timestamp'])
    trade_history = trade_history.sort_values('timestamp', ascending=False)

    # Filtrer par symbole
    if symbol != "ALL":
        trade_history = trade_history[trade_history['symbol'] == symbol]

    # Afficher 20 derniers trades
    display_trades = trade_history.head(20).copy()

    # Formatter colonnes
    display_trades['pnl_net'] = display_trades['pnl_net'].apply(lambda x: f"${x:.2f}")
    display_trades['entry_price'] = display_trades['entry_price'].apply(lambda x: f"{x:.2f}")
    display_trades['exit_price'] = display_trades['exit_price'].apply(lambda x: f"{x:.2f}")
    display_trades['win'] = display_trades['win'].apply(lambda x: '✅' if x else '❌')

    # Sélectionner colonnes
    columns_to_show = ['timestamp', 'symbol', 'direction', 'entry_price', 'exit_price', 'pnl_net', 'win']

    st.dataframe(
        display_trades[columns_to_show],
        use_container_width=True,
        height=400
    )

    # Stats trades
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Trades", len(trade_history))

    with col2:
        winners = trade_history[trade_history['win'] == True]
        st.metric("Gagnants", len(winners))

    with col3:
        losers = trade_history[trade_history['win'] == False]
        st.metric("Perdants", len(losers))

    with col4:
        avg_pnl = trade_history['pnl_net'].mean()
        st.metric("PnL Moyen", f"${avg_pnl:.2f}")

else:
    st.info("ℹ️ Pas de trades enregistrés")

# ═══════════════════════════════════════════════════════════════
# SECTION 4 - PERFORMANCE PAR SYMBOLE
# ═══════════════════════════════════════════════════════════════

st.markdown("---")
st.subheader("📊 Performance par Symbole")

if trade_history is not None and not trade_history.empty:
    # Grouper par symbole
    symbol_stats = trade_history.groupby('symbol').agg({
        'pnl_net': ['sum', 'mean', 'count'],
        'win': 'mean'
    }).round(2)

    symbol_stats.columns = ['PnL Total', 'PnL Moyen', 'Trades', 'Win Rate']
    symbol_stats['Win Rate'] = symbol_stats['Win Rate'].apply(lambda x: f"{x:.1%}")
    symbol_stats['PnL Total'] = symbol_stats['PnL Total'].apply(lambda x: f"${x:.2f}")
    symbol_stats['PnL Moyen'] = symbol_stats['PnL Moyen'].apply(lambda x: f"${x:.2f}")

    st.dataframe(symbol_stats, use_container_width=True)

else:
    st.info("ℹ️ Pas de données par symbole")

# ═══════════════════════════════════════════════════════════════
# AUTO-REFRESH
# ═══════════════════════════════════════════════════════════════

if auto_refresh:
    import time
    time.sleep(5)
    st.rerun()

# ═══════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("🤖 **MIA Trading System V3.3** | Dashboard temps réel | Auto-refresh: " + ("✅" if auto_refresh else "❌"))
