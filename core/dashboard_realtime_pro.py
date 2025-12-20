# dashboard_realtime_pro.py
# -*- coding: utf-8 -*-
"""
Dashboard PRO - MIA System (V4.0)
Refonte UI/UX + composants reutilisables, compatible avec votre flux existant.

Run:  streamlit run dashboard_realtime_pro.py
Required folder: data/ (live_metrics.json, drawdown_history.json, trade_history.json)
Optional: DATA_SIERRA_CHART/... for ML_READY (same as current)
"""
from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional, List, Tuple

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ====== Project imports (unchanged) ======
try:
    from market_context_analyzer import create_market_context_analyzer
except Exception:
    from core.market_context_analyzer import create_market_context_analyzer  # type: ignore

# Import module collecte
try:
    from data_collection_monitor import create_collection_monitor
except Exception:
    from core.data_collection_monitor import create_collection_monitor  # type: ignore

# Global config
st.set_page_config(
    page_title="MIA • Dashboard PRO Phase 3.5",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS_PATH = Path("ui_styles.css")

def inject_css() -> None:
    if CSS_PATH.exists():
        st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

inject_css()

# Helpers UI
def pill(label: str, tone: str = "neutral") -> str:
    return f'<span class="pill {tone}">{label}</span>'

def kpi(label: str, value: str, tone: str = "neutral") -> None:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {tone}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def section_title(icon: str, title: str):
    st.markdown(f"<div class='section-title'>{icon} {title}</div>", unsafe_allow_html=True)

def fmt_money(x: float) -> str:
    return f"${x:,.2f}"

def fmt_pct(x: float) -> str:
    return f"{x:.1%}"

# Data loaders
@st.cache_data(ttl=5)
def load_live_metrics() -> Optional[Dict[str, Any]]:
    try:
        p = Path("data/live_metrics.json")
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    except Exception as e:
        st.error(f"Erreur metriques: {e}")
        return None

@st.cache_data(ttl=10)
def load_drawdown_history() -> Optional[pd.DataFrame]:
    try:
        p = Path("data/drawdown_history.json")
        if not p.exists():
            return None
        df = pd.DataFrame(json.loads(p.read_text(encoding="utf-8")))
        if "timestamp" in df:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        st.error(f"Erreur drawdown: {e}")
        return None

@st.cache_data(ttl=30)
def load_trade_history() -> Optional[pd.DataFrame]:
    try:
        p = Path("data/trade_history.json")
        if not p.exists():
            return None
        df = pd.DataFrame(json.loads(p.read_text(encoding="utf-8")))
        if "timestamp" in df:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        st.error(f"Erreur trades: {e}")
        return None

@st.cache_data(ttl=2)
def load_latest_ml_ready(symbol: str) -> Optional[Dict[str, Any]]:
    try:
        now = datetime.utcnow()
        month_map = {
            1: "JANVIER", 2: "FEVRIER", 3: "MARS", 4: "AVRIL",
            5: "MAI", 6: "JUIN", 7: "JUILLET", 8: "AOUT",
            9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DECEMBRE"
        }
        chart_id = {"ES": "CHART_3", "NQ": "CHART_9", "RTY": "CHART_1"}.get(symbol, "CHART_3")
        date_str = now.strftime("%Y%m%d")
        month_dir = month_map[now.month]
        base = Path(f"DATA_SIERRA_CHART/DATA_2025/{month_dir}/{date_str}/{chart_id}/ML_READY")
        if not base.exists():
            return None
        files = sorted(base.glob("*.jsonl"))
        if not files:
            return None
        last = files[-1]
        lines = last.read_text(encoding="utf-8").strip().splitlines()
        if not lines:
            return None
        row = json.loads(lines[-1])
        md = row.get("menthor_distances", {})
        row["dist_gex_up"] = md.get("near_gex_up", 9e9)
        row["dist_gex_dn"] = md.get("near_gex_dn", 9e9)
        row["dist_blind"] = md.get("near_blind", 9e9)
        return row
    except Exception as e:
        st.error(f"Erreur ML_READY: {e}")
        return None

# Sidebar
with st.sidebar:
    st.markdown("<div class='brand'>🤖 MIA • Dashboard PRO</div>", unsafe_allow_html=True)
    st.caption("V4.0 Phase 3.5 — 130 Features ML • ES+NQ+RTY")
    symbol = st.selectbox("Symbole", ["ES", "NQ", "RTY"], index=0)
    auto_refresh = st.toggle("Auto-refresh (5s)", value=True)
    st.divider()
    st.markdown("### 📊 Phase 3.5")
    st.markdown("✅ 130 features sélectionnées par importance")
    st.markdown("✅ 3 marchés (ES, NQ, RTY)")
    st.markdown("✅ Comptes: Sim1, Sim2, Sim3")
    st.divider()
    metrics = load_live_metrics()
    if metrics:
        kpi("Status", "🟢 ACTIF", "success")
        kpi("Cycles", f"{metrics.get('total_cycles', 0):,}", "info")
        kpi("Signaux", str(metrics.get('total_signals', 0)), "accent")
        kpi("Uptime", f"{metrics.get('uptime_minutes', 0):.1f} min", "neutral")
    else:
        kpi("Status", "🔴 INACTIF", "danger")

# Header
st.markdown("<h1 class='page-title'>📊 Market & Performance Overview - Phase 3.5</h1>", unsafe_allow_html=True)
st.caption(datetime.now().strftime("%A %d %B %Y • %H:%M:%S"))

# ✅ NOUVEAU: Affichage info Phase 3.5
col_info1, col_info2, col_info3 = st.columns(3)
with col_info1:
    st.info("**🧠 Modèles ML Phase 3.5**\n\n✅ 130 features sélectionnées par importance\n\n✅ 2 passes d'entraînement (200 puis 5000 estimateurs)")
with col_info2:
    ml_stats = {"ES": "63.8% Acc | PF 4.56", "NQ": "68.8% Acc | PF 37.56", "RTY": "61.8% Acc | PF 8.19"}
    st.success(f"**📈 Performances**\n\n**ES:** {ml_stats['ES']}\n**NQ:** {ml_stats['NQ']}\n**RTY:** {ml_stats['RTY']}")
with col_info3:
    st.warning("**🎯 Comptes Simulation**\n\n**ES** → Sim1 (Chart 3)\n**NQ** → Sim2 (Chart 9)\n**RTY** → Sim3 (Chart 1)")

met = metrics or {}
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1: st.metric("💰 PnL Net", fmt_money(met.get("total_pnl_net", 0.0)), delta=fmt_money(met.get("pnl_delta", 0.0)))
with c2: st.metric("🎯 Win Rate", fmt_pct(met.get("win_rate", 0.0)))
with c3: st.metric("📝 Trades", f"{met.get('total_trades', 0)}")
with c4: st.metric("📉 Drawdown", fmt_pct(met.get("current_dd_pct", 0.0)))
with c5: st.metric("⚡ Latence", f"{met.get('avg_latency_ms', 0.0):.1f} ms")
with c6: st.metric("🔄 Cycles", f"{met.get('total_cycles', 0):,}")

st.divider()

# ====== ONGLETS ======
tab_trading, tab_collecte = st.tabs(["📊 Trading Live", "📦 Collecte Données"])

# ====== ONGLET TRADING ======
with tab_trading:
    # Market context + plans
    ml = load_latest_ml_ready(symbol)
    if ml:
        section_title("🧠", f"Contexte Marché — {symbol}")
        analyzer = create_market_context_analyzer(symbol)
        ctx = analyzer.analyze(ml)

        k1, k2, k3, k4, k5, k6 = st.columns(6)
        with k1: kpi("Bias", ctx.main_bias, "success" if ctx.main_bias=="BULLISH" else "danger" if ctx.main_bias=="BEARISH" else "info")
        with k2: kpi("Orderflow", ctx.orderflow_pressure, "success" if ctx.orderflow_pressure=="BUYING" else "danger" if ctx.orderflow_pressure=="SELLING" else "info")
        with k3: kpi("Gamma", ctx.gamma_condition, "info")
        with k4: kpi("vs HVL", ctx.position_vs_hvl.upper(), "info")
        with k5: kpi("vs VWAP", ctx.position_vs_vwap.upper(), "info")

        # ✅ PATCH V3.5: Affichage variation journalière
        day_change_pct = ml.get("day_change_pct", 0.0)
        day_change_pts = ml.get("day_change_points", 0.0) if "day_change_points" in ml else 0.0
        day_tone = "success" if day_change_pct >= 0 else "danger"
        with k6: kpi(f"{symbol} Jour", f"{day_change_pct:+.2f}%", day_tone)

        # ✅ PATCH V3.5: Position in Range visuel (barre de progression)
        st.markdown("**Position dans le Range du Jour**")
        position_in_range = ml.get("position_in_range", 50.0)  # 0-100%

        # Couleur selon position (< 20% = oversold, > 80% = overbought, sinon neutre)
        if position_in_range < 20:
            pos_color = "#00ff00"  # Vert (oversold, signal long potentiel)
            pos_label = "🟢 OVERSOLD (signal LONG)"
        elif position_in_range > 80:
            pos_color = "#ff0000"  # Rouge (overbought, signal short potentiel)
            pos_label = "🔴 OVERBOUGHT (signal SHORT)"
        else:
            pos_color = "#ffaa00"  # Orange (neutre)
            pos_label = "🟡 NEUTRE"

        # Barre de progression HTML/CSS
        st.markdown(f"""
        <div style="margin: 10px 0;">
            <div style="font-size: 14px; color: #888; margin-bottom: 5px;">{pos_label}</div>
            <div style="background: #333; border-radius: 5px; height: 20px; overflow: hidden; position: relative;">
                <div style="background: {pos_color}; height: 100%; width: {position_in_range:.1f}%; transition: width 0.3s;"></div>
                <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); height: 100%; width: 2px; background: #fff; opacity: 0.5;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 12px; color: #888; margin-top: 3px;">
                <span>0% (Low)</span>
                <span style="font-weight: bold; color: {pos_color};">{position_in_range:.1f}%</span>
                <span>100% (High)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.write("**Raisonnement**")
        st.info(ctx.reasoning)

        t1, t2 = st.columns(2)
        with t1:
            section_title("🧲", "Niveaux Magnets")
            if ctx.key_magnets:
                rows = [{"Type": m["type"], "Prix": f'{m["price"]:.2f}', "Δ": f'{m["distance"]:+.2f}', "Force": m.get("strength",""), "Description": m.get("description","")} for m in ctx.key_magnets[:12]]
                st.dataframe(rows, use_container_width=True, hide_index=True)
            else:
                st.info("Aucun niveau detecte.")
        with t2:
            section_title("⚠️", "Alertes")
            if ctx.proximity_alerts:
                for a in ctx.proximity_alerts: st.warning(a)
            else:
                st.success("Aucune alerte.")

        section_title("🗺️", "Plans de Trading")
        if not ctx.trading_plans:
            st.info("Aucun plan actif pour l'instant.")
        else:
            for i, p in enumerate(ctx.trading_plans, 1):
                with st.expander(f"{i}. {p.scenario.value.upper()} • {p.direction} • RR {p.risk_reward:.2f}x • Conf {int(p.confidence*100)}%", expanded=(i==1)):
                    cL, cR = st.columns([2,1])
                    with cL:
                        st.markdown(f"**Declencheur** : {p.trigger}")
                        st.markdown(f"**Entree** : {p.entry_zone[0]:.2f} → {p.entry_zone[1]:.2f}")
                        st.markdown(f"**Stop** : {p.stop_loss:.2f}")
                        st.markdown(f"**TP1/TP2/TP3** : {p.take_profit_1:.2f} / {p.take_profit_2:.2f}" + (f" / {p.take_profit_3:.2f}" if p.take_profit_3 is not None else ""))
                        st.markdown(f"**Invalidation** : {p.invalidation}")
                        st.markdown(f"**Management** : {p.management}")
                    with cR:
                        entry_avg = (p.entry_zone[0]+p.entry_zone[1])/2
                        names = ["SL","Entry","TP1","TP2"] + (["TP3"] if p.take_profit_3 else [])
                        yvals = [p.stop_loss, entry_avg, p.take_profit_1, p.take_profit_2] + ([p.take_profit_3] if p.take_profit_3 else [])
                        fig = go.Figure(go.Bar(x=names, y=yvals))
                        fig.update_layout(height=240, margin=dict(l=10,r=10,t=10,b=10))
                        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnee ML_READY detectee pour l'instant.")

    st.divider()

    # Performance
    section_title("📈", "Performance & Systeme")
    dd = load_drawdown_history()
    m = metrics or {}

    cA, cB = st.columns(2)
    with cA:
        st.markdown("**PnL Net**")
        if dd is not None and not dd.empty and "current_pnl" in dd:
            dd = dd.sort_values("timestamp")
            fig = go.Figure(go.Scatter(x=dd["timestamp"], y=dd["current_pnl"], mode="lines", name="PnL"))
            if "peak_pnl" in dd:
                fig.add_trace(go.Scatter(x=dd["timestamp"], y=dd["peak_pnl"], mode="lines", name="Peak", line=dict(dash="dash")))
            fig.update_layout(height=340, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas de donnees PnL.")

    with cB:
        st.markdown("**Drawdown %**")
        if dd is not None and not dd.empty and "current_dd_pct" in dd:
            fig = go.Figure(go.Scatter(x=dd["timestamp"], y=dd["current_dd_pct"]*100, mode="lines", fill="tozeroy"))
            fig.add_hline(y=15, line_dash="dash", line_color="red", annotation_text="Max DD 15%" )
            fig.update_layout(height=340, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Pas de donnees DD.")

    st.markdown("**Latence Pipeline**")
    if m and m.get("latency_breakdown"):
        lb = m["latency_breakdown"]
        fig = go.Figure(go.Bar(x=list(lb.keys()), y=list(lb.values())))
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Pas de donnees de latence.")

    st.markdown("**Trades recents**")
    trades = load_trade_history()
    if trades is not None and not trades.empty:
        trades = trades.sort_values("timestamp", ascending=False).head(50).copy()
        for col in ("entry_price","exit_price","pnl_net"):
            if col in trades: trades[col] = trades[col].map(lambda x: f"{x:.2f}" if isinstance(x,(int,float)) else x)
        st.dataframe(trades, use_container_width=True, height=420)
    else:
        st.info("Pas d'historique de trades.")

# ====== ONGLET COLLECTE ======
with tab_collecte:
    section_title("📦", "Monitoring Collecte de Données")
    st.caption("Suivi de la collecte passive pour les marchés en pré-production (GC, CL, RTY)")

    # Charger monitor
    monitor = create_collection_monitor()
    summary = monitor.get_summary()

    # KPIs globaux
    st.markdown("### 📊 Résumé Global")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🎯 Marchés en Collecte", summary['markets_collecting'])
    with col2:
        st.metric("✅ Marchés Prêts", summary['markets_ready'])
    with col3:
        st.metric("📈 Total Samples", f"{summary['total_samples_collected']:,}")
    with col4:
        st.metric("💾 Taille Totale", f"{summary['total_size_mb']:.2f} MB")

    st.divider()

    # Détail par marché
    st.markdown("### 📈 Progression par Marché")

    collecting_markets = monitor.get_all_collecting_markets()

    if not collecting_markets:
        st.info("✅ Aucun marché en collecte active. Tous les marchés sont en production ou non configurés.")
    else:
        for market in collecting_markets:
            with st.expander(f"{market['symbol']} - {market['name']}", expanded=True):
                # Progress bar
                progress_value = min(market['completion_pct'] / 100, 1.0)
                st.progress(progress_value, text=f"Progression: {market['completion_pct']:.1f}%")

                # Métriques
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("📊 Samples Collectés",
                             f"{market['total_samples']:,}",
                             delta=f"Target: {market['min_samples_target']:,}")
                with m2:
                    st.metric("📅 Jours de Collecte",
                             f"{market['days_collected']}",
                             delta=f"Avg: {market['avg_samples_per_day']:,}/jour")
                with m3:
                    status_color = "🟢" if market['status'] == "ready" else "🟡" if market['status'] == "minimum_reached" else "🔵"
                    st.metric("🎯 Statut",
                             f"{status_color} {market['status'].upper()}")

                # Info détaillée
                st.markdown(f"**Phase:** {market['phase']}")
                st.markdown(f"**Prochain Objectif:** {market['next_milestone']}")
                st.markdown(f"**ETA Ready:** {market['eta_ready']}")

                # Barre objectifs
                st.markdown("**Objectifs:**")
                obj_col1, obj_col2 = st.columns(2)
                with obj_col1:
                    st.caption(f"Minimum Training: {market['min_samples_target']:,} samples")
                with obj_col2:
                    st.caption(f"Recommandé: {market['recommended_target']:,} samples")

    st.divider()

    # Instructions
    st.markdown("### 💡 Actions Recommandées")

    markets_ready = [m for m in collecting_markets if m['status'] in ['ready', 'minimum_reached']]
    markets_collecting = [m for m in collecting_markets if m['status'] == 'collecting']

    if markets_ready:
        st.success("✅ **Marchés Prêts pour Training ML:**")
        for m in markets_ready:
            st.markdown(f"- **{m['symbol']}**: {m['total_samples']:,} samples collectés → Lancer `train_ml_direction_15min.py` pour {m['symbol']}")

    if markets_collecting:
        st.info("🔵 **Marchés en Collecte Active:**")
        for m in markets_collecting:
            remaining = m['min_samples_target'] - m['total_samples']
            st.markdown(f"- **{m['symbol']}**: {remaining:,} samples restants ({m['eta_ready']} estimé)")

    st.markdown("""
    **📝 Notes:**
    - La collecte s'effectue automatiquement pendant le trading ES/NQ
    - Vérifiez quotidiennement que les charts Sierra sont actifs
    - 20,000 samples = minimum pour training
    - 40,000 samples = recommandé pour performance optimale
    """)

# Auto-refresh
if auto_refresh:
    import time
    time.sleep(5)
    st.rerun()
