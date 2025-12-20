# -*- coding: utf-8 -*-
"""
MIA IA SYSTEM - Animations & UI Helpers
========================================

Helpers pour header, badges, toasts et animations du dashboard
"""

from __future__ import annotations
from typing import Optional
import streamlit as st
from datetime import datetime
from pathlib import Path


def inject_mia_css(css_path: str = "core/mia_styles.css"):
    """Injecte les styles CSS MIA dans le dashboard"""
    try:
        css_file = Path(css_path)
        if css_file.exists():
            with open(css_file, "r", encoding="utf-8") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        else:
            # Fallback: chercher à la racine
            alt_path = Path("mia_styles.css")
            if alt_path.exists():
                with open(alt_path, "r", encoding="utf-8") as f:
                    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
            else:
                # Fallback minimaliste
                st.markdown("<style>.mia-title{font-weight:800;color:#00e5ff}</style>", unsafe_allow_html=True)
    except Exception as e:
        # Fallback ultra simple en cas d'erreur
        st.markdown("<style>.mia-title{font-weight:800;color:#00e5ff}</style>", unsafe_allow_html=True)


def mia_header(bot_active: bool, auto_signal: str, latency_ms: Optional[int] = None):
    """
    Affiche le header MIA IA SYSTEM avec avatar, statut bot, signal auto et latence
    
    Args:
        bot_active: True si le bot est actif (avatar pulse)
        auto_signal: "BUY", "SELL", "WAIT"
        latency_ms: Latence moyenne en ms (optionnel)
    """
    # Badge statut bot
    status_badge = (
        '<span class="mia-badge ok">BOT ACTIF</span>' if bot_active
        else '<span class="mia-badge warn">PAUSE</span>'
    )
    
    # Badge signal automatique
    sig_map = {"BUY": "ok", "SELL": "danger", "WAIT": "info"}
    sig_badge = f'<span class="mia-badge {sig_map.get(auto_signal, "info")}">AUTO: {auto_signal}</span>'
    
    # Badge latence (si fourni)
    lat = f'<span class="mia-badge info">LAT {latency_ms} ms</span>' if latency_ms is not None else ""
    
    st.markdown(
        f"""
        <div class="mia-header">
          <div class="mia-avatar {'mia-pulse' if bot_active else ''}"></div>
          <div style="flex:1">
            <p class="mia-title">MIA IA SYSTEM — Live Control</p>
            <p class="mia-sub">Cockpit temps réel — exécution, signaux & contextes</p>
          </div>
          <div style="display:flex; gap:8px; align-items:center;">
            {sig_badge}{status_badge}{lat}
          </div>
        </div>
        """, 
        unsafe_allow_html=True
    )


def mia_ticker_pnl(pnl_str: str):
    """
    Affiche un ticker marquee animé avec PnL et infos système
    
    Args:
        pnl_str: Texte à afficher (ex: "PNL: +250.00 $ | Bias: BULLISH")
    """
    timestamp = datetime.now().strftime('%H:%M:%S')
    st.markdown(
        f"""
        <div class="mia-ticker">
          <div class="mia-ticker-inner">
            💹&nbsp;&nbsp;{pnl_str}&nbsp;&nbsp;•&nbsp;&nbsp;
            MIA IA SYSTEM RUNNING&nbsp;&nbsp;•&nbsp;&nbsp;
            Stay in flow&nbsp;&nbsp;•&nbsp;&nbsp;
            {timestamp}
          </div>
        </div>
        """, 
        unsafe_allow_html=True
    )


def mia_event_toast(event: str, detail: str = ""):
    """
    Affiche un toast Streamlit avec icône selon le type d'événement
    
    Args:
        event: Type d'événement (ex: "Gamma Flip UP", "TRADE FILLED")
        detail: Détails supplémentaires (optionnel)
    """
    # Déterminer l'icône selon l'événement
    icon = "✅"
    if "Gamma Flip DOWN" in event or "DOWN" in event:
        icon = "⚠️"
    elif "Gamma Flip UP" in event or "UP" in event:
        icon = "🔔"
    elif "FILLED" in event or "TRADE" in event or "ORDER" in event:
        icon = "💥"
    elif "SIGNAL" in event:
        icon = "📡"
    elif "ERROR" in event or "FAIL" in event:
        icon = "❌"
    
    # Afficher toast
    message = f"{icon} {event}"
    if detail:
        message += f" {detail}"
    
    st.toast(message, icon=None)


def mia_kpi_card(label: str, value: str, col):
    """
    Affiche une carte KPI stylée MIA
    
    Args:
        label: Label de la KPI
        value: Valeur à afficher
        col: Colonne Streamlit où afficher
    """
    with col:
        st.markdown(
            f'<div class="mia-card mia-kpi">'
            f'<div class="mia-kpi-label">{label}</div>'
            f'<div class="mia-kpi-value">{value}</div>'
            f'</div>', 
            unsafe_allow_html=True
        )


