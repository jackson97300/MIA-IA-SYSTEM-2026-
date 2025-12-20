# trading_dashboard_app.py
# Streamlit dashboard to visualize Market Context Analyzer outputs
import json
from datetime import datetime
from typing import Any, Dict, List, Tuple

import streamlit as st

# Local import of the analyzer (expects market_context_analyzer.py in the same folder or path)
from market_context_analyzer import create_market_context_analyzer, TradingPlan, MarketContext

# -----------------------------
# ---------- THEME ------------
# -----------------------------

def inject_css():
    css = Path("dashboard_styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# -----------------------------
# ---------- UTILS ------------
# -----------------------------

def pill(text: str, tone: str) -> str:
    """tone in ['info','success','warn','danger','neutral','accent']"""
    return f'<span class="pill {tone}">{text}</span>'

def status_badge(label: str, value: str) -> str:
    tone = "neutral"
    val = value.upper()
    if val in ("BULLISH", "BUYING", "POSITIVE", "ABOVE"):
        tone = "success"
    elif val in ("BEARISH", "SELLING", "NEGATIVE", "BELOW"):
        tone = "danger"
    elif val in ("AT", "INSIDE", "BALANCED", "NEUTRAL"):
        tone = "info"
    return f'''
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value {tone}">{value}</div>
    </div>
    '''

def two_col_label_value(label: str, value: str) -> None:
    c1, c2 = st.columns([1.2, 2])
    with c1:
        st.markdown(f"**{label}**")
    with c2:
        st.markdown(value, unsafe_allow_html=True)

def render_key_magnets(magnets: List[Dict[str, Any]], price: float):
    st.markdown("### 🎯 Niveaux *magnets* (par proximité)")
    if not magnets:
        st.info("Aucun niveau détecté.")
        return
    rows = []
    for m in magnets:
        rows.append({
            "Type": m["type"],
            "Prix": f'{m["price"]:.2f}',
            "Δ vs prix": f'{m["distance"]:+.2f}',
            "Force": m["strength"],
            "Description": m["description"],
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

def render_alerts(alerts: List[str]):
    st.markdown("### 🚨 Alertes de proximité")
    if not alerts:
        st.success("Aucune alerte pour l'instant.")
        return
    for a in alerts:
        st.markdown(f"- {a}")

def render_trading_plan(plan: TradingPlan):
    # Card
    with st.container():
        st.markdown(f"""
        <div class="plan-card">
            <div class="plan-header">
                <div>
                    <div class="plan-title">{plan.scenario.value.replace('_',' ').title()}</div>
                    <div class="plan-sub">Priorité {plan.priority} • {plan.direction}</div>
                </div>
                <div class="plan-rr">{pill(f"RR {plan.risk_reward:.2f}x",'accent')} {pill(f"Confiance {int(plan.confidence*100)}%",'info')}</div>
            </div>
            <div class="divider"></div>
        </div>
        """, unsafe_allow_html=True)

        # Grid details
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Déclencheur**")
            st.markdown(plan.trigger)
            st.markdown("**Invalidation**")
            st.markdown(plan.invalidation)
        with c2:
            st.markdown("**Entrée (zone)**")
            st.markdown(f"{plan.entry_zone[0]:.2f} → {plan.entry_zone[1]:.2f}")
            st.markdown("**Stop-Loss**")
            st.markdown(f"{plan.stop_loss:.2f}")
        with c3:
            st.markdown("**Take Profits**")
            st.markdown(f"TP1: **{plan.take_profit_1:.2f}**")
            st.markdown(f"TP2: **{plan.take_profit_2:.2f}**")
            if plan.take_profit_3 is not None:
                st.markdown(f"TP3: **{plan.take_profit_3:.2f}**")
            st.markdown("**Management**")
            st.markdown(plan.management)
        st.markdown("<div class='card-spacer'></div>", unsafe_allow_html=True)

def load_snapshot(path: str) -> Dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}

def example_snapshot() -> Dict[str, Any]:
    # Compact version of the user's ES snapshot for demo
    return {
        "mid": 6863.00,
        "hvl": 6865.00,
        "vwap": 6878.48,
        "atr": 1.13,
        "vva": {"vah": 6890.25, "val": 6870.25, "vpoc": 6882.75},
        "menthor_distances": {"near_blind": 1.37, "near_gex_up": 48, "near_gex_dn": -93},
        "call_resistance": 7000.00,
        "put_support": 6700.00,
        "deltaPct": 0.60,
        "cum_delta_session": -187,
        "tsec": 1762222688.12,
        "spread": 0.25,
        "confluence_strength": 0.35,
        "menthorq_proximity_strength": 0.12,
        "smart_money_flow": 0.6,
        "depth_imbalance": 0.20,
    }

# -----------------------------
# ----------- APP -------------
# -----------------------------

st.set_page_config(page_title="MIA • Market Context", page_icon="📊", layout="wide")
inject_css()

st.markdown("<h1 class='app-title'>📊 MIA • Market Context Dashboard</h1>", unsafe_allow_html=True)
colA, colB = st.columns([2, 1])
with colA:
    st.markdown("Visualisation professionnelle du contexte de marché et des plans de trading générés automatiquement.")
with colB:
    st.markdown(pill("v2.0", "neutral"), unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Options")
    source = st.radio("Source des données", ["Exemple (démo)", "Fichier JSON"], index=0)
    path = None
    if source == "Fichier JSON":
        path = st.text_input("Chemin du snapshot JSON", value="snapshot.json", help="Fichier contenant un dict ML_READY")
    st.divider()
    st.caption("Astuce: glissez votre JSON intraday pour voir le rendu en temps réel.")

data = example_snapshot() if source == "Exemple (démo)" else load_snapshot(path or "snapshot.json")
analyzer = create_market_context_analyzer("ES")
context = analyzer.analyze(data)

# Header KPIs
st.markdown("## 🧠 Contexte Marché")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(status_badge("Bias", context.main_bias), unsafe_allow_html=True)
with c2:
    st.markdown(status_badge("Orderflow", context.orderflow_pressure), unsafe_allow_html=True)
with c3:
    st.markdown(status_badge("Gamma", context.gamma_condition), unsafe_allow_html=True)
with c4:
    st.markdown(status_badge("vs HVL", context.position_vs_hvl), unsafe_allow_html=True)
with c5:
    st.markdown(status_badge("vs VWAP", context.position_vs_vwap), unsafe_allow_html=True)

cL, cR = st.columns([1.3, 1])
with cL:
    st.markdown("### 🧩 Raisonnement")
    st.write(context.reasoning)

with cR:
    st.markdown("### 🎯 Prix")
    st.metric("Prix actuel", f"{context.current_price:.2f}")
    # Show nearest magnet
    nearest = context.key_magnets[0] if context.key_magnets else None
    if nearest:
        st.metric("Aimant le plus proche", f'{nearest["type"]} @ {nearest["price"]:.2f}', delta=f'{nearest["distance"]:+.2f}')

# Alerts + Magnets
c1, c2 = st.columns(2)
with c1:
    render_alerts(context.proximity_alerts)
with c2:
    render_key_magnets(context.key_magnets, context.current_price)

# Trading plans
st.markdown("## 🗺️ Plans de Trading (triés par priorité)")
if not context.trading_plans:
    st.info("Aucun plan actif (horaires ? niveaux manquants ?).")
else:
    for plan in context.trading_plans:
        render_trading_plan(plan)

st.markdown("<div class='footer'>© MIA System — Dashboard v2.0</div>", unsafe_allow_html=True)
