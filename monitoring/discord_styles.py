#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Discord Styles & Embeds
Phase 1: Embeds professionnels avec couleurs et emojis cohérents
Phase 2: Session timezone + stats par session
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import SessionAnalyzer pour détection sessions
try:
    from core.session_analyzer import SessionAnalyzer
    SESSION_ANALYZER_AVAILABLE = True
    _session_analyzer = SessionAnalyzer()
except ImportError:
    SESSION_ANALYZER_AVAILABLE = False
    _session_analyzer = None

# 🎯 16/12/2025: Import rollover automatique pour affichage correct du contrat
try:
    from config.futures_rollover import get_active_contract
    ROLLOVER_AVAILABLE = True
except ImportError:
    ROLLOVER_AVAILABLE = False
    def get_active_contract(symbol: str) -> str:
        return f"{symbol}H26"  # Fallback

# ═══════════════════════════════════════════════════════════════
# 🎨 COULEURS DISCORD (format décimal pour embeds)
# ═══════════════════════════════════════════════════════════════

class DiscordColor(Enum):
    """Couleurs Discord en format décimal"""
    # Trading
    BUY_GREEN = 0x10B981      # Vert brillant pour BUY
    SELL_RED = 0xEF4444       # Rouge vif pour SELL
    WIN_GREEN = 0x22C55E      # Vert succès pour WIN
    LOSS_RED = 0xF43F5E       # Rouge perte pour LOSS

    # Status
    INFO_BLUE = 0x3B82F6      # Bleu info
    WARNING_ORANGE = 0xF59E0B # Orange warning
    ERROR_RED = 0xDC2626      # Rouge erreur
    SUCCESS_GREEN = 0x10B981  # Vert succès

    # Heartbeat
    HEARTBEAT_CYAN = 0x06B6D4  # Cyan pour heartbeat
    NEUTRAL_GRAY = 0x6B7280    # Gris neutre

    # Risk
    RISK_ORANGE = 0xF59E0B     # Orange pour risk events
    CRITICAL_RED = 0xB91C1C    # Rouge critique


# ═══════════════════════════════════════════════════════════════
# 😀 EMOJIS COHÉRENTS (système centralisé)
# ═══════════════════════════════════════════════════════════════

class Emoji:
    """Emojis cohérents pour tous les messages Discord"""

    # Trading direction
    BUY_UP = "🟢"
    SELL_DOWN = "🔴"
    ARROW_UP = "⬆️"
    ARROW_DOWN = "⬇️"

    # P&L
    MONEY_WIN = "💰"
    MONEY_LOSS = "🩸"
    MONEY_NEUTRAL = "💵"
    FEES = "💸"

    # Trading elements
    TARGET_TP = "🎯"
    STOP_SL = "🛑"
    ENTRY = "📍"
    EXIT = "🚪"

    # Analysis
    CONFLUENCE = "🧩"
    ML_BRAIN = "🤖"
    STRATEGY = "🎲"
    CHART = "📈"
    CHART_DOWN = "📉"

    # Time & Session
    CLOCK = "🕒"
    TIMER = "⏱️"
    DURATION = "⏳"

    # Status
    HEARTBEAT = "💓"
    ONLINE = "✅"
    OFFLINE = "❌"
    WARNING = "⚠️"
    ERROR = "🚨"
    INFO = "ℹ️"

    # Risk & Protection
    SHIELD = "🛡️"
    LOCK = "🔒"
    FIRE = "🔥"
    ALERT = "🔔"

    # Performance
    TROPHY = "🏆"
    STAR = "⭐"
    ROCKET = "🚀"
    CHART_UP = "📊"
    WIN = "✅"
    LOSS = "❌"
    SUMMARY = "🧾"  # ✨ Pour Daily Summary

    # Markets
    ES = "📘"  # Bleu pour ES
    NQ = "📗"  # Vert pour NQ
    RTY = "📙"  # Jaune pour RTY

    # Health
    HEALTH = "🏥"
    BATTERY = "🔋"
    SIGNAL_STRENGTH = "📡"


# ═══════════════════════════════════════════════════════════════
# 🎯 HELPERS POUR EMBEDS
# ═══════════════════════════════════════════════════════════════

def get_market_emoji(symbol: str) -> str:
    """Retourne l'emoji du marché"""
    emoji_map = {
        "ES": Emoji.ES,
        "NQ": Emoji.NQ,
        "RTY": Emoji.RTY
    }
    return emoji_map.get(symbol, Emoji.CHART)


def get_side_emoji(side: str) -> str:
    """Retourne l'emoji de direction"""
    if side.upper() == "BUY":
        return f"{Emoji.BUY_UP} {Emoji.ARROW_UP}"
    elif side.upper() == "SELL":
        return f"{Emoji.SELL_DOWN} {Emoji.ARROW_DOWN}"
    return "⚪"


def get_pnl_emoji(pnl: float) -> str:
    """Retourne l'emoji selon P&L"""
    # ✅ CORRIGÉ 17/11: Vérifier que pnl est un nombre (éviter erreur 'dict' vs 'int')
    if isinstance(pnl, dict):
        # Si c'est un dict, essayer d'extraire la valeur
        pnl = pnl.get('pnl', 0.0) if isinstance(pnl.get('pnl'), (int, float)) else 0.0
    elif not isinstance(pnl, (int, float)):
        # Si ce n'est ni un dict ni un nombre, retourner 0.0
        pnl = 0.0

    if pnl > 0:
        return Emoji.MONEY_WIN
    elif pnl < 0:
        return Emoji.MONEY_LOSS
    return Emoji.MONEY_NEUTRAL


def format_pnl(pnl: float, pnl_ticks: float, fees: float = 0.0) -> str:
    """
    Formate P&L avec emoji, brut, ticks et fees

    ✅ PATCH: pnl reçu = BRUT, on calcule net et affiche emoji sur net

    Exemple: "💰 P&L: +$152.60 (+30.5 tks) | 💸 Fees: $2.50 | **Net: +$150.10**"
    """
    net_pnl = pnl - fees  # Calculer net
    net_emoji = get_pnl_emoji(net_pnl)  # Emoji sur NET (pas sur brut)

    if fees > 0:
        return (
            f"💵 P&L Brut: ${pnl:+.2f} ({pnl_ticks:+.1f} tks)\n"
            f"{Emoji.FEES} Fees: ${fees:.2f}\n"
            f"**{net_emoji} Net: ${net_pnl:+.2f}**"
        )
    else:
        # Si pas de fees, on affiche juste le P&L
        emoji = get_pnl_emoji(pnl)
        return f"{emoji} P&L: ${pnl:+.2f} ({pnl_ticks:+.1f} tks)"


def format_setup_line(strategy: str, confluence: float, ml_confidence: float) -> str:
    """
    Formate ligne setup

    Exemple: "🧩 Conf: 0.78 | 🤖 ML: 0.67 | 🎯 liquidity_sweep_reversal"
    """
    return (
        f"{Emoji.CONFLUENCE} Conf: **{confluence:.2f}** | "
        f"{Emoji.ML_BRAIN} ML: **{ml_confidence:.2f}** | "
        f"{Emoji.STRATEGY} {strategy}"
    )


def format_routing_line(symbol: str, side: str, qty: float, entry: float, tp: float, sl: float) -> str:
    """
    Formate ligne routing

    Exemple: "📈 NQ (NQU5-CME-SIM) | ⬆️ BUY x1 @ 25179.38 | 🎯 25189.50 | 🛑 25171.25"
    """
    market_emoji = get_market_emoji(symbol)
    side_emoji = get_side_emoji(side)

    # ✅ FIX 27/11: Protection contre None
    entry = entry if entry is not None else 0
    tp = tp if tp is not None else 0
    sl = sl if sl is not None else 0
    qty = qty if qty is not None else 1

    # 🎯 16/12/2025: Utiliser rollover automatique pour affichage correct
    contract = get_active_contract(symbol)  # Ex: ES → ESH26
    return (
        f"{market_emoji} **{symbol}** ({contract}-CME-SIM) | "
        f"{side_emoji} **{side}** x{qty:.0f} @ **{entry:.2f}** | "
        f"{Emoji.TARGET_TP} {tp:.2f} | "
        f"{Emoji.STOP_SL} {sl:.2f}"
    )


def calculate_fees(symbol: str, qty: float = 1.0) -> float:
    """
    Calcule les fees (entrée + sortie)

    ✅ CORRIGÉ 17/11: Aligné avec launch_ml_v3_production.py
    Fees réelles PropFirms (Apex/TopStep/Elite):
    - ES: $1.40 round-turn (0.12 ticks)
    - NQ: $1.40 round-turn (0.28 ticks)
    - RTY: $1.40 round-turn
    """
    fee_per_contract = {
        "ES": 1.40,   # ✅ CORRIGÉ: Aligné avec launch_ml_v3_production.py
        "NQ": 1.40,   # ✅ CORRIGÉ: Aligné avec launch_ml_v3_production.py
        "RTY": 1.40   # ✅ CORRIGÉ: Aligné avec launch_ml_v3_production.py
    }
    return fee_per_contract.get(symbol, 1.40) * qty


def get_sim_account(symbol: str) -> str:
    """Retourne le compte SIM pour le symbole"""
    sim_map = {
        "ES": "SIM1",
        "NQ": "SIM2",
        "RTY": "SIM3"
    }
    return sim_map.get(symbol, "SIM?")


def _format_strategy_name_for_discord(strategy: str) -> str:
    """
    ✅ CORRIGÉ 19/11: Formate le nom de stratégie pour affichage Discord.

    Args:
        strategy: Nom de stratégie brut (technique)

    Returns:
        Nom de stratégie formaté (lisible)
    """
    if not strategy or strategy == '' or strategy == 'UNKNOWN':
        return 'UNKNOWN'

    # Mapping des noms techniques vers noms lisibles
    strategy_mapping = {
        'vwap_sd_options_confluence_strategy': 'VWAP SD Options',
        'menthorq_3layer_strategy': 'MenthorQ 3-Layer',
        'ml_3layer_strategy': 'ML 3-Layer',
        'unknown': 'UNKNOWN',
        'UNKNOWN': 'UNKNOWN',
        'ConfluenceSignal': 'VWAP SD Options'  # Fallback pour anciens trades
    }

    # Vérifier mapping
    if strategy in strategy_mapping:
        return strategy_mapping[strategy]
    # ✅ FIX: Vérifier que strategy est une string avant .lower()
    elif isinstance(strategy, str) and strategy.lower() in strategy_mapping:
        return strategy_mapping[strategy.lower()]

    # Si pas dans mapping, nettoyer le nom (enlever _strategy, remplacer _ par espace)
    cleaned = strategy.replace('_strategy', '').replace('_', ' ').title()
    return cleaned


def get_current_session() -> str:
    """
    Retourne la session actuelle (Europe/Paris timezone)

    Returns:
        "EU Pre-Market" / "US Open" / "US Mid-Session" / "US Close" / "After Hours"
    """
    if not SESSION_ANALYZER_AVAILABLE or not _session_analyzer:
        return "Unknown Session"

    try:
        now = datetime.now()
        session_analysis = _session_analyzer.analyze_session(now, vix_level=20.0)  # VIX dummy
        session_state = session_analysis.get('session_state', {})

        window = session_state.get('window', 'mid')
        is_rth = session_state.get('is_rth', False)
        hot_zone = session_state.get('hot_zone', False)

        # Déterminer session friendly
        if hot_zone and window == "hot":
            if "15:" in now.strftime("%H:%M"):
                return "US Open (Hot Zone)"
            elif "21:" in now.strftime("%H:%M"):
                return "US Close (Hot Zone)"

        if window == "open":
            return "US Open"
        elif window == "close":
            return "US Close"
        elif is_rth:
            return "US Mid-Session"
        else:
            hour = now.hour
            if 8 <= hour < 15:
                return "EU Pre-Market"
            elif hour >= 22:
                return "After Hours"
            else:
                return "Off-Hours"

    except Exception as e:
        return "Unknown Session"


def _normalize_session_for_discord(session_raw: str) -> str:
    """
    ✅ CORRIGÉ 17/11: Normalise la session pour Discord (éviter "Unknown" avec casse mixte)

    Args:
        session_raw: Session brute depuis trade_data

    Returns:
        Session normalisée (US, LONDON, ASIA, etc.) ou "UNKNOWN" si non trouvé
    """
    if not session_raw or session_raw == '':
        return get_current_session()

    session_upper = session_raw.upper()

    # Normaliser les variantes
    if session_upper in ['UNKNOWN', 'UNKNOWN SESSION']:
        return get_current_session()  # Utiliser session actuelle si inconnue

    # Mapper les sessions standards
    if session_upper in ['US', 'RTH', 'REGULAR']:
        return 'US'
    elif session_upper in ['LONDON', 'EU', 'EUROPE']:
        return 'LONDON'
    elif session_upper in ['ASIA', 'ASIAN']:
        return 'ASIA'
    elif session_upper in ['ETH', 'EXTENDED']:
        return 'ETH'
    else:
        # Retourner la session telle quelle si déjà formatée correctement
        return session_raw


# ═══════════════════════════════════════════════════════════════
# 🔧 FONCTIONS UTILITAIRES DE VALIDATION ET ENRICHISSEMENT
# ═══════════════════════════════════════════════════════════════

def validate_and_fix_trade_data(trade_data: Dict) -> Dict:
    """
    ✅ NOUVELLE FONCTION 20/11: Valide et corrige les incohérences

    Corrige automatiquement:
    - Bias/Régime incohérents
    - MenthorQ invalide
    - Scores manquants
    - Valeurs par défaut suspectes (999, 0, etc.)
    """
    fixed_data = trade_data.copy()
    issues_found = []

    # ✅ 27/11: Ne valider que si trade_id valide (éviter warnings au démarrage)
    trade_id = fixed_data.get('trade_id', 'UNKNOWN')
    if trade_id == 'UNKNOWN' or not trade_id:
        # Données incomplètes (probablement démarrage/test)
        # Corriger silencieusement sans logger
        if fixed_data.get('menthorq_level_type') in ['UNKNOWN', 'N/A', None, '']:
            fixed_data['menthorq_level_entry'] = 0
            fixed_data['menthorq_strength'] = 0
            fixed_data['menthorq_distance'] = 999
        if fixed_data.get('menthorq_distance', 0) >= 999:
            fixed_data['menthorq_distance'] = None
        if fixed_data.get('d1_proximity', 0) >= 999:
            fixed_data['d1_proximity'] = None
        return fixed_data  # Retour silencieux

    # 1. Fix MenthorQ cohérence (seulement pour trades réels)
    if fixed_data.get('menthorq_level_type') in ['UNKNOWN', 'N/A', None, '']:
        # Si pas de niveau, tout est N/A
        fixed_data['menthorq_level_entry'] = 0
        fixed_data['menthorq_strength'] = 0
        fixed_data['menthorq_distance'] = 999
        issues_found.append("MenthorQ invalide → tout mis à N/A")

    # 2. Fix Bias/Régime cohérence
    bias = fixed_data.get('market_bias', 'UNKNOWN')
    regime = fixed_data.get('regime', 'unknown')
    bullish = fixed_data.get('bullish_score', 50)

    # Convertir bullish_score en pourcentage si nécessaire
    if -1 <= bullish <= 1:
        bullish_percent = (bullish + 1) * 50
    else:
        bullish_percent = bullish

    # Si bias neutre mais régime momentum
    # ✅ FIX: Vérifier que regime est une string avant .lower()
    if bias == 'NEUTRAL' and isinstance(regime, str) and 'momentum' in regime.lower():
        if abs(bullish_percent - 50) < 20:  # Vraiment neutre
            fixed_data['regime'] = 'range'
            issues_found.append(f"Régime {regime} → range (bias neutre)")

    # 3. Fix valeurs par défaut suspectes
    if fixed_data.get('menthorq_distance', 0) >= 999:
        fixed_data['menthorq_distance'] = None  # Sera affiché comme N/A
        issues_found.append("Distance 999 → N/A")

    if fixed_data.get('d1_proximity', 0) >= 999:
        fixed_data['d1_proximity'] = None
        issues_found.append("D1 proximity 999 → N/A")

    # 4. Valider scores minimum
    # ✅ MODIFIÉ 27/11: Seuils qualité améliorés pour trades de meilleure qualité
    MIN_SCORES = {
        'confluence': 0.60,
        'menthorq_score': 0.30,  # ✅ MODIFIÉ 27/11: MenthorQ minimum 0.30
        'orderflow_score': 0.17,  # ✅ MODIFIÉ 27/11: OrderFlow minimum 0.17
        'context_score': 0.20   # ✅ MODIFIÉ 27/11: Context minimum 0.20
    }

    for score_name, min_val in MIN_SCORES.items():
        if score_name in fixed_data:
            if fixed_data[score_name] < min_val * 0.5:
                issues_found.append(f"{score_name} TRÈS FAIBLE: {fixed_data[score_name]:.2f}")

    # Logger les corrections (DEBUG car ce sont des corrections automatiques normales)
    if issues_found:
        trade_id = fixed_data.get('trade_id', 'UNKNOWN')
        logger.debug(f"📝 [DISCORD] Corrections appliquées pour {trade_id}:")
        for issue in issues_found:
            logger.debug(f"   - {issue}")

    return fixed_data


def get_quality_bar(value: float, max_value: float = 1.0) -> str:
    """
    Retourne une barre visuelle de qualité
    Ex: ████████░░ pour 80%
    """
    if value is None:
        return "❓ N/A"

    percentage = (value / max_value) * 100
    filled = int(percentage / 10)
    empty = 10 - filled

    if percentage >= 80:
        color = "🟩"  # Vert
    elif percentage >= 60:
        color = "🟨"  # Jaune
    elif percentage >= 40:
        color = "🟧"  # Orange
    else:
        color = "🟥"  # Rouge

    bar = "█" * filled + "░" * empty
    return f"{color} {bar} {percentage:.0f}%"


def _format_d1_proximity_display(trade_data: Dict) -> str:
    """
    ✅ FIX 27/11: Formate d1_proximity pour affichage Discord
    Retourne "N/A" si valeur invalide (0, None, >= 999)
    """
    d1_proximity = trade_data.get('d1_proximity')
    d1_level_type = trade_data.get('d1_level_type', 'N/A')

    if d1_proximity is None or d1_proximity == 0.0 or d1_proximity >= 999:
        return f"N/A ({d1_level_type})"

    return f"{d1_proximity:.1f}t ({d1_level_type})"


def _format_swing_distance_display(trade_data: Dict) -> str:
    """
    ✅ FIX 27/11: Formate swing_distance pour affichage Discord
    Retourne "N/A" si valeur invalide (0, None, >= 999)
    """
    swing_distance = trade_data.get('swing_distance')

    if swing_distance is None or swing_distance == 0.0 or swing_distance >= 999:
        return "N/A"

    return f"{swing_distance:.1f}t"


def _format_trigger_level_display(trade_data: Dict) -> str:
    """
    🔧 12/12: Affiche le NIVEAU VALIDATEUR (le plus proche qui a validé le trade)
    C'est le niveau utilisé pour la validation de proximité, pas forcément le niveau MenthorQ
    """
    # 🆕 12/12: Utiliser nearest_level si disponible (niveau validateur)
    nearest_type = trade_data.get('nearest_level_type', 'N/A')
    nearest_price = trade_data.get('nearest_level_price', 0)
    nearest_distance = trade_data.get('nearest_level_distance', 0)

    # Si nearest_level disponible, l'afficher
    if nearest_type != 'N/A' and nearest_price > 0:
        # Formater le type de niveau de manière lisible
        type_display = nearest_type.replace('_', ' ')
        if 'BL' in type_display:
            type_display = f"Blind Spot ({nearest_type})"
        elif 'GEX' in type_display:
            type_display = type_display.upper()
        elif 'VPOC' in type_display.upper():
            type_display = 'VPOC'
        elif 'VAH' in type_display.upper():
            type_display = 'VAH'
        elif 'VAL' in type_display.upper():
            type_display = 'VAL'

        return f"{type_display} @ {nearest_price:.2f}\nDistance: {nearest_distance:.1f}t"

    # Fallback: utiliser trigger_level (ancien comportement)
    trigger_level = trade_data.get('trigger_level', 0)
    trigger_type = trade_data.get('trigger_type', 'UNKNOWN')
    trigger_distance = trade_data.get('trigger_distance', 999.0)

    if trigger_level == 0 or trigger_type == 'UNKNOWN' or trigger_distance >= 999:
        return "N/A (niveau non identifié)"

    # Formater le type de niveau de manière lisible
    type_display = trigger_type.replace('_', ' ').title()
    if 'Gex' in type_display:
        type_display = type_display.replace('Gex', 'GEX')

    return f"{type_display} @ {trigger_level:.2f}\nDistance: {trigger_distance:.1f}t"


def format_risk_indicators(trade_data: Dict) -> str:
    """
    Génère des indicateurs de risque visuels
    """
    indicators = []

    # SL distance
    sl_ticks = trade_data.get('sl_ticks', 0) or 0  # ✅ FIX 17/12: Protection None
    if sl_ticks < 20:
        indicators.append("⚠️ SL PROCHE")
    elif sl_ticks > 40:
        indicators.append("✅ SL SÉCURISÉ")

    # Session
    session = trade_data.get('session', '')
    if session == 'ASIA':
        indicators.append("🌏 SESSION RISQUÉE")
    elif session in ['US_OPEN', 'EU_OPEN']:
        indicators.append("💧 LIQUIDITÉ OK")

    # Confluence
    confluence = trade_data.get('confluence', 0) or 0  # ✅ FIX 17/12: Protection None
    if confluence < 0.60:
        indicators.append("⚠️ CONFLUENCE FAIBLE")
    elif confluence > 0.75:
        indicators.append("✅ FORTE CONFLUENCE")

    return " | ".join(indicators) if indicators else "✅ Risque normal"


def format_score_visual(value, threshold, name):
    """Formate un score avec emoji visuel"""
    if value is None:
        return f"❓ {name}: N/A"

    if value < threshold * 0.5:
        return f"🔴 {name}: {value:.2f}"  # Très mauvais
    elif value < threshold:
        return f"🟠 {name}: {value:.2f}"  # Sous seuil
    elif value < threshold * 1.5:
        return f"🟡 {name}: {value:.2f}"  # Acceptable
    else:
        return f"🟢 {name}: {value:.2f}"  # Bon


def format_1d_position_bar(entry: float, day_min: float, day_max: float, trade_data: Optional[Dict[str, Any]] = None) -> tuple:
    """
    ✅ NOUVEAU 21/11 03:30: Crée une barre 3 zones : SOUS MIN | RANGE | AU-DESSUS MAX

    Format: [ZONE_BASSE|ZONE_RANGE|ZONE_HAUTE] Position% Emoji Label

    Args:
        entry: Prix d'entrée
        day_min: 1D MIN
        day_max: 1D MAX
        trade_data: Dict optionnel pour fallback (contient '1d_min', '1d_max')

    Returns:
        tuple: (bar_string, position_pct, zone_label, is_breakout)
    """
    # ✅ FIX 21/11 04:45: Fallback avec trade_data si day_min/day_max sont 0
    # ✅ FIX 17/12: Gestion des valeurs None
    if day_min is None or day_max is None or day_min <= 0 or day_max <= 0:
        if trade_data:
            day_min = trade_data.get('day_low', 0) or 0
            day_max = trade_data.get('day_high', 0) or 0
            if day_min is None or day_max is None or day_min <= 0 or day_max <= 0:
                return "Données 1D indisponibles", 0, "N/A", False
        else:
            if entry is not None and entry > 0:
                return "Données 1D indisponibles", 0, "N/A", False
            return "N/A", 0, "N/A", False

    range_total = day_max - day_min
    is_breakout = False

    # Calculer position
    if entry < day_min:
        # 🔴 SOUS MIN (breakout bearish)
        position_pct = -abs(entry - day_min) / range_total * 100
        zone_emoji = "⚠️"
        zone_label = "SOUS MIN"
        is_breakout = True

        # Barre: [░░🔻|          |    ]
        below_blocks = min(int(abs(position_pct) / 10), 3)  # Max 3 blocs sous MIN
        empty_blocks = 3 - below_blocks
        bar = f"[{'░' * below_blocks}{'🔻' if below_blocks > 0 else ' '}{'·' * empty_blocks}|{'          '}|{'    '}]"

    elif entry > day_max:
        # 🔵 AU-DESSUS MAX (breakout bullish)
        position_pct = 100 + abs(entry - day_max) / range_total * 100
        zone_emoji = "⚠️"
        zone_label = "AU-DESSUS MAX"
        is_breakout = True

        # Barre: [   |          |🔺░░]
        above_blocks = min(int((position_pct - 100) / 10), 3)  # Max 3 blocs au-dessus MAX
        empty_blocks = 3 - above_blocks
        bar = f"[{'    '}|{'          '}|{'·' * empty_blocks}{'🔺' if above_blocks > 0 else ' '}{'░' * above_blocks}]"

    else:
        # ⚪ DANS LE RANGE (0-100%)
        position_pct = (entry - day_min) / range_total * 100

        # Déterminer zone et emoji
        if position_pct < 25:
            zone_emoji = "🔻"
            zone_label = "BAS"
        elif position_pct < 40:
            zone_emoji = "⬇️"
            zone_label = "BAS-MOYEN"
        elif position_pct < 60:
            zone_emoji = "⚡"
            zone_label = "MILIEU"
        elif position_pct < 75:
            zone_emoji = "⬆️"
            zone_label = "HAUT-MOYEN"
        else:
            zone_emoji = "🔺"
            zone_label = "HAUT"

        # Barre: [   |▓▓▓▓▓░░░░░|    ] (10 blocs dans le range)
        filled = int(position_pct / 10)
        empty = 10 - filled
        bar = f"[{'    '}|{'▓' * filled}{'░' * empty}|{'    '}]"

    bar_display = f"{bar} {position_pct:.0f}% {zone_emoji} {zone_label}"
    return bar_display, position_pct, zone_label, is_breakout


def format_win_streak(streak: Dict[str, Any]) -> str:
    """
    ✅ NOUVEAU 21/11 04:10: Formate une série Win/Loss pour Discord

    Args:
        streak: {'type': 'WIN'|'LOSS', 'count': int}

    Returns:
        str: "🔥 3W" ou "❄️ 2L" ou "—"
    """
    if not streak or streak.get('count', 0) == 0:
        return "—"

    streak_type = streak.get('type')
    count = streak.get('count', 0)

    if streak_type == 'WIN':
        emoji = '🔥' if count >= 3 else '✅'
        return f"{emoji} {count}W"
    elif streak_type == 'LOSS':
        emoji = '❄️' if count >= 3 else '❌'
        return f"{emoji} {count}L"
    else:
        return "—"


def analyze_exit_type(trade_data: Dict[str, Any]) -> tuple:
    """
    ✅ NOUVEAU 21/11 04:35: Analyse le type de sortie pour un trade fermé
    ✅ AMÉLIORÉ 21/11 05:00: Format avec pourcentage de réalisation TP/SL

    Args:
        trade_data: Données du trade avec 'exit_price', 'tp_price', 'sl_price', 'side', 'pnl_ticks', 'exit_reason'

    Returns:
        tuple: (exit_type_str, exit_emoji, detailed_message)

    Format:
        - "TP 100%", "✅", "TP target atteint @ 20327.25"
        - "TP 120%", "✨", "TP dépassé de +20% @ 20330.00"
        - "TP 75%", "⚡", "Sortie anticipée (75% du TP) @ 20325.00"
        - "SL 100%", "❌", "SL atteint @ 20310.00"
        - "SL 60%", "🛡️", "SL protégé (60% seulement) @ 20314.00"
    """
    exit_price = trade_data.get('exit_price', 0)
    tp_price = trade_data.get('tp_price', 0)
    sl_price = trade_data.get('sl_price', 0)
    fill_price = trade_data.get('fill_price', exit_price)  # Entry price
    side = trade_data.get('side', 'UNKNOWN')
    pnl_ticks = trade_data.get('pnl_ticks', 0)

    # Tolérance pour considérer TP/SL atteint (1 tick)
    tolerance = 1.0

    if pnl_ticks > 0:
        # ═══════════════════════════════════════════════════════════
        # TRADE GAGNANT - Calculer % réalisation TP
        # ═══════════════════════════════════════════════════════════
        if tp_price > 0 and fill_price > 0:
            if side == 'LONG':
                tp_range = tp_price - fill_price
                exit_range = exit_price - fill_price
            else:  # SHORT
                tp_range = fill_price - tp_price
                exit_range = fill_price - exit_price

            if tp_range > 0:
                tp_percent = (exit_range / tp_range) * 100
            else:
                tp_percent = 100  # Fallback

            # Déterminer type et emoji
            if abs(exit_price - tp_price) <= tolerance:
                # TP atteint exactement
                return f"TP {tp_percent:.0f}%", "✅", f"TP target atteint @ {exit_price:.2f}"
            elif tp_percent > 100:
                # TP dépassé
                overrun_pct = tp_percent - 100
                return f"TP {tp_percent:.0f}%", "✨", f"TP dépassé de +{overrun_pct:.0f}% @ {exit_price:.2f}"
            else:
                # Sortie anticipée
                return f"TP {tp_percent:.0f}%", "⚡", f"Sortie anticipée ({tp_percent:.0f}% du TP) @ {exit_price:.2f}"
        else:
            # Pas de TP défini (fallback)
            return "WIN", "✅", f"Sortie gagnante @ {exit_price:.2f}"

    else:
        # ═══════════════════════════════════════════════════════════
        # TRADE PERDANT - Calculer % perte par rapport au SL
        # ═══════════════════════════════════════════════════════════
        if sl_price > 0 and fill_price > 0:
            if side == 'LONG':
                sl_range = fill_price - sl_price
                exit_range = fill_price - exit_price
            else:  # SHORT
                sl_range = sl_price - fill_price
                exit_range = exit_price - fill_price

            if sl_range > 0:
                sl_percent = (exit_range / sl_range) * 100
            else:
                sl_percent = 100  # Fallback

            # Déterminer type et emoji
            if abs(exit_price - sl_price) <= tolerance:
                # SL atteint exactement
                return f"SL {sl_percent:.0f}%", "❌", f"SL atteint @ {exit_price:.2f}"
            elif sl_percent < 100:
                # Sorti avant SL (protection)
                return f"SL {sl_percent:.0f}%", "🛡️", f"SL protégé ({sl_percent:.0f}% seulement) @ {exit_price:.2f}"
            else:
                # Dépassé le SL (pire que prévu)
                return f"SL {sl_percent:.0f}%", "💀", f"SL dépassé ({sl_percent:.0f}%) @ {exit_price:.2f}"
        else:
            # Pas de SL défini (fallback)
            return "LOSS", "❌", f"Sortie perdante @ {exit_price:.2f}"


# ═══════════════════════════════════════════════════════════════
# 🏗️ EMBED BUILDERS
# ═══════════════════════════════════════════════════════════════

def build_trade_opened_embed(trade_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ✅ CORRIGÉ 20/11: Validation cohérence et enrichissement visuel

    Construit un embed Discord pour trade ouvert avec validation et corrections automatiques

    Args:
        trade_data: {
            'symbol': str,
            'side': str,
            'quantity': float,
            'fill_price': float,
            'tp_price': float,
            'sl_price': float,
            'strategy': str,
            'confluence': float,
            'ml_confidence': float,
            'trade_id': str (optionnel)
        }

    Returns:
        Dict compatible avec Discord webhook embed
    """
    # ✅ VALIDER ET CORRIGER D'ABORD
    trade_data = validate_and_fix_trade_data(trade_data)

    symbol = trade_data['symbol']
    side = trade_data['side']
    entry = trade_data.get('fill_price', 0)  # ✅ FIX 21/11 04:15: .get() avec fallback
    tp = trade_data.get('tp_price', 0)  # ✅ PATCH: .get() avec fallback
    sl = trade_data.get('sl_price', 0)  # ✅ PATCH: .get() avec fallback

    # ✅ PATCH: Si tp/sl/entry sont None, mettre 0
    if entry is None or entry == 0:
        logger.error(f"❌ [DISCORD] fill_price invalide pour {trade_data.get('trade_id', 'N/A')}: {entry}")
        # ✅ FIX 27/11: Utiliser fallback si entry invalide
        entry = (tp + sl) / 2 if (tp and sl and tp > 0 and sl > 0) else 0
        if entry == 0:
            logger.error(f"❌ [DISCORD] Impossible de calculer fill_price, abandon embed")
            # Retourner un embed minimal d'erreur
            return {
                "embeds": [{
                    "title": f"❌ ERREUR EMBED - {symbol} {side}",
                    "description": f"Données trade invalides (fill_price=0)\nTrade ID: {trade_data.get('trade_id', 'N/A')}",
                    "color": 0xFF0000,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
    if tp is None:
        tp = 0
    if sl is None:
        sl = 0

    # ✅ CORRIGÉ 19/11: Validation et logging du nom de stratégie
    strategy_raw = trade_data.get('strategy', 'UNKNOWN')
    # ✅ FIX: Convertir en string si nécessaire
    if not isinstance(strategy_raw, str):
        strategy_raw = str(strategy_raw) if strategy_raw else 'UNKNOWN'
    if strategy_raw and strategy_raw.lower() == 'unknown':
        strategy = 'UNKNOWN'
    elif not strategy_raw or strategy_raw == '':
        strategy = 'UNKNOWN'
    else:
        strategy = strategy_raw

    # ⚠️ WARNING si UNKNOWN (pour traçabilité)
    if strategy == 'UNKNOWN':
        trade_id = trade_data.get('trade_id', 'N/A')
        logger.warning(f"⚠️ [DISCORD] Strategy UNKNOWN pour trade {trade_id}")
        logger.debug(f"[DISCORD] Trade data complète: {list(trade_data.keys())}")

    # ⭐ FORMATER POUR AFFICHAGE DISCORD (nom lisible)
    strategy = _format_strategy_name_for_discord(strategy)
    confluence = trade_data.get('confluence', 0.0)
    ml_conf = trade_data.get('ml_confidence', 0.0)
    qty = trade_data.get('quantity', 1.0)
    trade_id = trade_data.get('trade_id', 'N/A')

    # Calculer distances TP/SL en ticks
    tick_sizes = {"ES": 0.25, "NQ": 0.25, "RTY": 0.10}
    tick_size = tick_sizes.get(symbol, 0.25)

    # ✅ FIX 27/11: Protection contre valeurs None/0 dans calcul ticks
    try:
        if side.upper() == "BUY":
            tp_ticks = (tp - entry) / tick_size if (tp and entry and tp > 0 and entry > 0) else 0
            sl_ticks = (entry - sl) / tick_size if (entry and sl and entry > 0 and sl > 0) else 0
        else:  # SELL
            tp_ticks = (entry - tp) / tick_size if (entry and tp and entry > 0 and tp > 0) else 0
            sl_ticks = (sl - entry) / tick_size if (sl and entry and sl > 0 and entry > 0) else 0
    except (TypeError, ZeroDivisionError) as e:
        logger.error(f"❌ [DISCORD] Erreur calcul ticks: {e}")
        tp_ticks = 0
        sl_ticks = 0

    # ✅ FIX 17/12: Protection finale contre None
    tp_ticks = tp_ticks if tp_ticks is not None else 0
    sl_ticks = sl_ticks if sl_ticks is not None else 0

    # ========== VALIDATION DONNÉES ==========

    # 1. VALIDATION MENTHORQ
    menthorq_type = trade_data.get('menthorq_level_type', 'UNKNOWN')
    menthorq_level = trade_data.get('menthorq_level_entry', 0)
    menthorq_strength = trade_data.get('menthorq_strength', 0)
    menthorq_distance = trade_data.get('menthorq_distance', 999)

    # ✅ FIX 27/11: Protection contre None AVANT validation
    if menthorq_level is None:
        menthorq_level = 0
    if menthorq_strength is None:
        menthorq_strength = 0
    if menthorq_distance is None:
        menthorq_distance = 999

    # ✅ SI PAS DE NIVEAU VALIDE, TOUT EST INVALIDE
    menthorq_valid = (
        menthorq_type not in ['UNKNOWN', 'N/A', None, ''] and
        menthorq_level > 0 and
        menthorq_distance < 500  # Distance raisonnable
    )

    if not menthorq_valid:
        # FORCER COHÉRENCE: Pas de niveau = pas de données
        menthorq_display_type = "N/A"
        menthorq_display_level = "N/A"
        menthorq_display_strength = "N/A"
        menthorq_display_distance = "N/A"
        # ✅ CORRIGÉ 21/11 02:52: Log DEBUG au lieu de WARNING (pas toujours une erreur)
        logger.debug(f"ℹ️ [DISCORD] MenthorQ non disponible: type={menthorq_type}, level={menthorq_level}, distance={menthorq_distance:.1f}t")
    else:
        # ✅ CORRIGÉ 21/11 03:03: Gérer QSCORE spécialement (pas de prix exact)
        if menthorq_type == 'QSCORE':
            menthorq_display_type = "QSCORE (global)"
            menthorq_display_level = "N/A"  # QSCORE n'a pas de niveau de prix spécifique
        else:
            menthorq_display_type = menthorq_type
            menthorq_display_level = f"{menthorq_level:.2f}"

        menthorq_display_strength = f"{menthorq_strength:.0f}%"
        menthorq_display_distance = f"{menthorq_distance:.1f}t" if menthorq_distance and menthorq_distance < 999 else "N/A"

    # 2. VALIDATION SCORES AVEC INDICATEURS VISUELS
    confluence = trade_data.get('confluence', 0)
    menthorq_score = trade_data.get('menthorq_score', 0)
    orderflow_score = trade_data.get('orderflow_score', 0)
    context_score = trade_data.get('context_score', 0)

    # ✅ FIX 27/11: Protection contre None
    if confluence is None:
        confluence = 0
    if menthorq_score is None:
        menthorq_score = 0
    if orderflow_score is None:
        orderflow_score = 0
    if context_score is None:
        context_score = 0

    confluence_display = format_score_visual(confluence, 0.60, "Confluence")
    menthorq_score_display = format_score_visual(menthorq_score, 0.25, "MenthorQ")
    orderflow_display = format_score_visual(orderflow_score, 0.20, "OrderFlow")
    context_display = format_score_visual(context_score, 0.15, "Context")

    # Vérifier si tous les scores sont valides
    scores_valid = (
        confluence >= 0.60 and
        menthorq_score >= 0.25 and
        orderflow_score >= 0.20 and
        context_score >= 0.15
    )

    # 3. VALIDATION COHÉRENCE BIAS/RÉGIME
    market_bias = trade_data.get('market_bias', 'UNKNOWN')
    bullish_score = trade_data.get('bullish_score', 0)
    regime = trade_data.get('regime', 'unknown')

    # ✅ FIX 27/11: Protection contre None
    if bullish_score is None:
        bullish_score = 0

    # Convertir bullish_score en pourcentage si nécessaire
    if -1 <= bullish_score <= 1:
        bullish_percent = (bullish_score + 1) * 50
    else:
        bullish_percent = bullish_score

    # ✅ FIX 21/11 03:15: Normaliser -0.0 → 0.0 (artefact flottant Python)
    if bullish_percent == 0:
        bullish_percent = abs(bullish_percent)  # Forcer signe positif

    # Détecter incohérence
    # ✅ FIX: Vérifier que regime est une string avant .lower()
    if market_bias == 'NEUTRAL' and isinstance(regime, str) and 'momentum' in regime.lower():
        logger.warning(f"⚠️ [DISCORD] Incohérence détectée: Bias NEUTRAL avec régime {regime}")
        # Corriger automatiquement
        regime = 'range' if 'extended' not in regime else 'range_extended'
        regime_corrected = True
    else:
        regime_corrected = False

    # Emoji de direction
    side_emoji = get_side_emoji(side)
    market_emoji = get_market_emoji(symbol)
    sim_account = get_sim_account(symbol)

    # Couleur selon direction
    color = DiscordColor.BUY_GREEN.value if side.upper() == "BUY" else DiscordColor.SELL_RED.value

    # 🔥 09/12: Récupérer le mode TREND/RANGE
    trading_mode = trade_data.get('trading_mode', 'TREND')
    mode_emoji = "📈" if trading_mode == "TREND" else "🔄"

    # Modifier le titre si problèmes détectés
    title = f"{side_emoji} TRADE OUVERT — {side.upper()}"

    # Ajouter alertes au titre
    alerts = []

    # 🔥 09/12: Ajouter le MODE en premier
    alerts.append(f"{mode_emoji} {trading_mode}")

    if not menthorq_valid:
        alerts.append("⚠️ SANS MENTHORQ")
    if not scores_valid:
        alerts.append("⚠️ SCORES FAIBLES")
    session = trade_data.get('session', get_current_session())
    if session == 'ASIA':
        alerts.append("🌏 ASIA")
    if regime_corrected:
        alerts.append("🔧 RÉGIME CORRIGÉ")

    if alerts:
        title = f"[{' | '.join(alerts)}] {title}"

    # Construire embed
    embed = {
        "title": title,
        "description": format_routing_line(symbol, side, qty, entry, tp, sl),
        "color": color,
        "fields": [
            {
                "name": f"{Emoji.TARGET_TP} TP / {Emoji.STOP_SL} SL",
                "value": f"{tp:.2f} (+{tp_ticks:.1f} tks) · {sl:.2f} (-{sl_ticks:.1f} tks)",
                "inline": False
            },
            {
                "name": f"{Emoji.CLOCK} Session",
                "value": _normalize_session_for_discord(session),
                "inline": True
            },
            {
                "name": f"{Emoji.STRATEGY} Setup",
                "value": strategy,
                "inline": True
            },
            {
                "name": "📊 Scores Qualité",
                "value": (
                    f"{confluence_display}\n"
                    f"{menthorq_score_display}\n"
                    f"{orderflow_display}\n"
                    f"{context_display}"
                ),
                "inline": True
            },
            {
                "name": "✅ Validations",
                "value": (
                    f"{'✅' if menthorq_valid else '❌'} MenthorQ valide\n"
                    f"{'✅' if scores_valid else '❌'} Scores minimum\n"
                    f"{'✅' if (sl_ticks or 0) >= 25 else '❌'} SL protection\n"
                    f"{'✅' if not regime_corrected else '🔧'} Cohérence marché"
                ),
                "inline": True
            },
            {
                "name": "🌐 Market Context",
                "value": (
                    f"Bias: {market_bias} ({bullish_percent:.0f}%)\n"
                    f"Régime: {regime}{'*' if regime_corrected else ''}\n"
                    f"Trend: {trade_data.get('trend_bias', 'UNKNOWN')} {trade_data.get('trend_aligned', '')}\n"
                    f"Session: {session}\n"
                    f"1D Position: {format_1d_position_bar(entry, trade_data.get('day_low', 0), trade_data.get('day_high', 0), trade_data)[0]}"
                ),
                "inline": False
            },
            {
                "name": "📍 Entry Context",
                "value": (
                    f"MenthorQ: {menthorq_display_type} @ {menthorq_display_level}\n"
                    f"Force: {menthorq_display_strength} | Distance: {menthorq_display_distance}"
                ),
                "inline": False
            },
            {
                "name": "✅ Niveau Validateur",
                "value": _format_trigger_level_display(trade_data),
                "inline": False
            },
            {
                "name": "🎯 Risk Management",
                "value": (
                    f"R:R: {trade_data.get('rr_ratio', (tp_ticks/(sl_ticks or 1) if (sl_ticks or 0) > 0 else 0)):.2f}:1\n"
                    f"1D Proximity: {_format_d1_proximity_display(trade_data)}\n"
                    f"Swing Distance: {_format_swing_distance_display(trade_data)}"
                ),
                "inline": False
            },
            {
                "name": f"{Emoji.INFO} Trade ID",
                "value": f"`{trade_id}`",
                "inline": False
            }
        ],
        "footer": {
            "text": f"{Emoji.FEES} Fees (~${calculate_fees(symbol, qty) * 2:.2f}) inclus dans P&L final (Entrée + Sortie)"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"embeds": [embed]}


def build_trade_closed_embed(trade_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ✅ CORRIGÉ 20/11: Cohérence avec ouverture + détection anomalies

    Construit un embed Discord pour trade fermé avec détection de stop hunts

    Args:
        trade_data: {
            'symbol': str,
            'side': str,
            'pnl': float,
            'pnl_ticks': float,
            'exit_price': float,
            'duration_minutes': float,
            'exit_reason': str,
            'strategy': str,
            'confluence': float,
            'ml_confidence': float,
            'max_profit_ticks': float (optionnel),
            'max_loss_ticks': float (optionnel)
        }

    Returns:
        Dict compatible avec Discord webhook embed
    """
    # ✅ VALIDER ET CORRIGER D'ABORD
    trade_data = validate_and_fix_trade_data(trade_data)

    symbol = trade_data['symbol']
    side = trade_data.get('side', 'UNKNOWN')

    # Durée du trade
    duration_minutes = trade_data.get('duration_minutes', 0)

    # ⚠️ DÉTECTION STOP HUNT
    is_stop_hunt = (
        trade_data.get('exit_reason') == 'SL' and
        duration_minutes < 1.0
    )

    # ✅ CORRIGÉ 18/11: Normaliser pnl (peut être un dict)
    pnl_raw = trade_data.get('pnl', 0.0)
    if isinstance(pnl_raw, dict):
        # Si c'est un dict, essayer d'extraire la valeur
        pnl = pnl_raw.get('pnl', 0.0) if isinstance(pnl_raw.get('pnl'), (int, float)) else 0.0
    elif isinstance(pnl_raw, (int, float)):
        pnl = float(pnl_raw)
    else:
        pnl = 0.0

    # ✅ CORRIGÉ 28/11: Utiliser pnl_net si disponible (depuis launch_ml_v3_production.py)
    # Sinon calculer depuis pnl brut - fees
    pnl_net_raw = trade_data.get('pnl_net', None)
    if pnl_net_raw is not None and isinstance(pnl_net_raw, (int, float)):
        net_pnl = float(pnl_net_raw)
        # Si pnl_net fourni, utiliser les fees fournies ou calculer
        fees_provided = trade_data.get('fees', None)
        if fees_provided is not None and isinstance(fees_provided, (int, float)):
            fees = float(fees_provided)
        else:
            # Calculer fees si non fournies
            qty = trade_data.get('quantity', 1.0)
            fees = calculate_fees(symbol, qty)
    else:
        # Fallback: calculer net_pnl depuis pnl brut
        qty = trade_data.get('quantity', 1.0)
        fees = calculate_fees(symbol, qty)
        net_pnl = pnl - fees

    # ✅ CORRIGÉ 18/11: Normaliser pnl_ticks (peut être un dict)
    pnl_ticks_raw = trade_data.get('pnl_ticks', 0.0)
    if isinstance(pnl_ticks_raw, dict):
        pnl_ticks = pnl_ticks_raw.get('pnl_ticks', 0.0) if isinstance(pnl_ticks_raw.get('pnl_ticks'), (int, float)) else 0.0
    elif isinstance(pnl_ticks_raw, (int, float)):
        pnl_ticks = float(pnl_ticks_raw)
    else:
        pnl_ticks = 0.0

    # ✅ CORRIGÉ 18/11: Normaliser exit_price (peut être un dict)
    exit_price_raw = trade_data.get('exit_price', 0.0)
    if isinstance(exit_price_raw, dict):
        exit_price = exit_price_raw.get('exit_price', 0.0) if isinstance(exit_price_raw.get('exit_price'), (int, float)) else 0.0
    elif isinstance(exit_price_raw, (int, float)):
        exit_price = float(exit_price_raw)
    else:
        exit_price = 0.0
    duration = trade_data.get('duration_minutes', 0)
    exit_reason = trade_data.get('exit_reason', 'N/A')
    # ✅ CORRIGÉ 19/11: Validation et logging du nom de stratégie
    strategy_raw = trade_data.get('strategy', 'UNKNOWN')
    # ✅ FIX: Convertir en string si nécessaire
    if not isinstance(strategy_raw, str):
        strategy_raw = str(strategy_raw) if strategy_raw else 'UNKNOWN'
    if strategy_raw and strategy_raw.lower() == 'unknown':
        strategy = 'UNKNOWN'
    elif not strategy_raw or strategy_raw == '':
        strategy = 'UNKNOWN'
    else:
        strategy = strategy_raw

    # ⚠️ WARNING si UNKNOWN (pour traçabilité)
    if strategy == 'UNKNOWN':
        trade_id = trade_data.get('trade_id', 'N/A')
        logger.warning(f"⚠️ [DISCORD] Strategy UNKNOWN pour trade {trade_id}")
        logger.debug(f"[DISCORD] Trade data complète: {list(trade_data.keys())}")

    # ⭐ FORMATER POUR AFFICHAGE DISCORD (nom lisible)
    strategy = _format_strategy_name_for_discord(strategy)
    confluence = trade_data.get('confluence')  # ✅ AMÉLIORÉ: Peut être None
    ml_conf = trade_data.get('ml_confidence', 0.0)

    # ✅ CORRIGÉ 18/11: Normaliser mfe et mae (peuvent être des dicts)
    mfe_raw = trade_data.get('max_profit_ticks', 0.0)
    if isinstance(mfe_raw, dict):
        mfe = mfe_raw.get('max_profit_ticks', 0.0) if isinstance(mfe_raw.get('max_profit_ticks'), (int, float)) else 0.0
    elif isinstance(mfe_raw, (int, float)):
        mfe = float(mfe_raw)
    else:
        mfe = 0.0

    mae_raw = trade_data.get('max_loss_ticks', 0.0)
    if isinstance(mae_raw, dict):
        mae = mae_raw.get('max_loss_ticks', 0.0) if isinstance(mae_raw.get('max_loss_ticks'), (int, float)) else 0.0
    elif isinstance(mae_raw, (int, float)):
        mae = float(mae_raw)
    else:
        mae = 0.0

    is_winner = net_pnl > 0  # ✅ WIN/LOSS basé sur NET (après fees)

    # Emojis
    pnl_emoji = get_pnl_emoji(net_pnl)  # ✅ Emoji sur NET
    side_emoji = get_side_emoji(side)
    market_emoji = get_market_emoji(symbol)
    sim_account = get_sim_account(symbol)

    # ⚠️ DÉTECTION STOP HUNT
    is_stop_hunt = (
        exit_reason == 'SL' and
        duration < 1.0
    )

    # Couleur selon résultat
    color = DiscordColor.WIN_GREEN.value if is_winner else DiscordColor.LOSS_RED.value

    # Titre avec alerte si nécessaire
    if is_winner:
        title = f"{pnl_emoji} TRADE FERMÉ — WIN"
    else:
        if is_stop_hunt:
            title = f"🚨 STOP HUNT — LOSS"
        else:
            title = f"{pnl_emoji} TRADE FERMÉ — LOSS"

    # Description
    description = (
        f"{market_emoji} **{symbol}** ({sim_account}) | "
        f"{side_emoji} {side} | "
        f"{Emoji.EXIT} Sortie **{exit_price:.2f}**"
    )

    # Fields
    # Calcul données enrichies
    # ✅ CORRIGÉ 18/11: Normaliser daily_pnl (peut être un dict)
    daily_pnl_raw = trade_data.get('daily_pnl_usd', 0.0)
    if isinstance(daily_pnl_raw, dict):
        daily_pnl = daily_pnl_raw.get('daily_pnl_usd', 0.0) if isinstance(daily_pnl_raw.get('daily_pnl_usd'), (int, float)) else 0.0
    elif isinstance(daily_pnl_raw, (int, float)):
        daily_pnl = float(daily_pnl_raw)
    else:
        daily_pnl = 0.0
    daily_winrate = trade_data.get('daily_winrate', 0.0)
    daily_trades = trade_data.get('daily_trades', 0)
    daily_wins = trade_data.get('daily_wins', 0)
    daily_losses = daily_trades - daily_wins

    # ✅ CORRIGÉ 18/11: Extraire daily_fees (total journalier) au lieu de fees du trade actuel
    daily_fees = trade_data.get('daily_fees', 0.0)
    if daily_fees == 0.0:
        # Fallback: calculer si non fourni (pour compatibilité)
        daily_fees = fees * daily_trades if daily_trades > 0 else fees

    # ✅ CORRIGÉ 21/11 03:05: Calculer efficiency correctement
    if mfe > 0:
        if pnl_ticks > 0:
            # Trade gagnant : efficiency = P&L / MFE * 100
            efficiency = (pnl_ticks / mfe * 100)
        else:
            # Trade perdant avec MFE > 0 : N/A (n'a pas capturé le profit)
            # Note: Afficher "N/A" au lieu de "0%" car c'est plus clair
            efficiency = None  # Sera affiché comme "N/A"
    elif abs(mae) > 0:
        # Trade perdant sans MFE : efficiency = P&L / MAE (négatif)
        efficiency = (pnl_ticks / abs(mae) * 100)
    else:
        efficiency = None

    fields = [
        {
            "name": f"{pnl_emoji} P&L Trade + Jour",
            "value": (
                f"Trade: ${net_pnl:+,.2f} ({pnl_ticks:+.1f}t)\n"
                f"Jour: ${daily_pnl:+,.2f} | WR: {daily_winrate:.0f}%"
            ),
            "inline": False
        },
        {
            "name": f"{Emoji.TIMER} Durée",
            "value": f"**{duration:.2f}** min",
            "inline": True
        },
        {
            "name": "📊 Exit Analysis",
            "value": (
                f"Type: {exit_reason}\n"
                f"MFE: {mfe:.1f}t / MAE: {abs(mae):.1f}t\n"
                f"Efficiency: {efficiency:.0f}%" if efficiency is not None else "Efficiency: N/A"
            ),
            "inline": True
        }
    ]

    # ✅ NOUVEAU 21/11 04:40: Analyse détaillée du type de sortie
    # ✅ AMÉLIORÉ 21/11 05:05: Format "Exit: TP 100% ✅" plus explicite
    exit_type, exit_emoji, exit_detail = analyze_exit_type(trade_data)

    # Remplacer le champ "Exit Analysis" avec analyse améliorée
    for i, field in enumerate(fields):
        if field.get('name') == '📊 Exit Analysis':
            fields[i] = {
                "name": f"📊 Exit Analysis",
                "value": (
                    f"Exit: {exit_type} {exit_emoji}\n"
                    f"{exit_detail}\n"
                    f"MFE: {mfe:.1f}t / MAE: {abs(mae):.1f}t"
                ),
                "inline": True
            }
            break

    # Si stop hunt, ajouter section spéciale
    if is_stop_hunt:
        fields.insert(1, {
            "name": "🚨 ALERTE STOP HUNT",
            "value": (
                f"⚠️ Trade fermé en {duration*60:.1f} secondes!\n"
                f"❌ MFE: {mfe:.1f}t (jamais en profit)\n"
                f"❌ MAE: {abs(mae):.1f}t (perte immédiate)\n"
                f"🔍 Analyse requise: SL trop proche ou mauvaise entrée"
            ),
            "inline": False
        })

    # Ajouter MFE/MAE si disponibles
    if mfe != 0 or mae != 0:
        fields.append({
            "name": f"{Emoji.CHART_UP} MFE / MAE",
            "value": f"**+{mfe:.1f}** tks / **{mae:.1f}** tks",
            "inline": True
        })

    # Ajouter setup
    # ✅ CORRIGÉ 17/11: Normaliser session (éviter "Unknown" avec casse mixte)
    session_raw = trade_data.get('session', get_current_session())
    if session_raw and session_raw.upper() == 'UNKNOWN':
        session = 'UNKNOWN'
    elif not session_raw or session_raw == '':
        session = get_current_session()
    else:
        # Normaliser en majuscules pour cohérence
        session = session_raw.upper() if session_raw not in ['US', 'LONDON', 'ASIA', 'ETH'] else session_raw

    fields.append({
        "name": f"{Emoji.CLOCK} Session",
        "value": session,
        "inline": True
    })

    fields.append({
        "name": f"{Emoji.STRATEGY} Setup",
        "value": strategy,
        "inline": True
    })

    # ✅ NOUVEAU 21/11 04:45: Ajouter Trade ID pour tracking
    trade_id = trade_data.get('trade_id', 'N/A')
    fields.append({
        "name": f"{Emoji.INFO} Trade ID",
        "value": f"`{trade_id}`",
        "inline": True
    })

    # ✅ CORRIGÉ 17/11: Ajouter tous les scores détaillés comme dans TRADE OUVERT
    # ✅ AMÉLIORÉ: Gestion None et validation des données
    menthorq_score = trade_data.get('menthorq_score')
    orderflow_score = trade_data.get('orderflow_score')
    context_score = trade_data.get('context_score')

    # Formatage avec gestion None
    menthorq_str = f"**{menthorq_score:.2f}**" if menthorq_score is not None else "**N/A**"
    orderflow_str = f"**{orderflow_score:.2f}**" if orderflow_score is not None else "**N/A**"
    context_str = f"**{context_score:.2f}**" if context_score is not None else "**N/A**"
    confluence_str = f"**{confluence:.2f}**" if confluence is not None and confluence != 0.0 else "**N/A**"

    fields.append({
        "name": f"{Emoji.CONFLUENCE} / {Emoji.ML_BRAIN} Scores",
        "value": (
            f"{Emoji.CONFLUENCE} Confluence: {confluence_str}\n"
            f"🎯 MenthorQ: {menthorq_str}\n"
            f"📊 OrderFlow: {orderflow_str}\n"
            f"🌍 Context: {context_str}"
        ),
        "inline": True
    })

    # ✅ CORRIGÉ 17/11: Ajouter Market Context comme dans TRADE OUVERT
    # ✅ AMÉLIORÉ: Validation cohérence bias/bullish_score
    market_bias = trade_data.get('market_bias', 'UNKNOWN')
    bullish_score = trade_data.get('bullish_score')
    regime = trade_data.get('regime', 'Unknown')
    session = trade_data.get('session', 'UNKNOWN')

    # ✅ VALIDATION: Si bias BULLISH mais bullish_score = 0 ou None, corriger
    if market_bias == 'BULLISH' and (bullish_score is None or bullish_score == 0):
        market_bias = 'NEUTRE'  # Corriger incohérence
        bullish_score = 0

    # ✅ FIX 21/11 03:12: Normaliser -0.0 → 0.0 (artefact flottant Python)
    if bullish_score == 0:
        bullish_score = abs(bullish_score)  # Forcer signe positif

    # Formatage bullish_score
    if bullish_score is not None:
        bias_str = f"{market_bias} ({bullish_score:.0f}%)"
    else:
        bias_str = f"{market_bias} (N/A)"

    fields.append({
        "name": "🌐 Market Context",
        "value": (
            f"Bias: {bias_str}\n"
            f"Régime: {regime} | Session: {session}\n"
            f"1D Position: {format_1d_position_bar(trade_data.get('fill_price', 0), trade_data.get('day_low', 0), trade_data.get('day_high', 0), trade_data)[0]}"
        ),
        "inline": False
    })

    # ✅ CORRIGÉ 17/11: Ajouter Entry Context comme dans TRADE OUVERT
    # ✅ AMÉLIORÉ: Gestion None et distance 999.0t
    menthorq_level_type = trade_data.get('menthorq_level_type', 'N/A')
    menthorq_level_entry = trade_data.get('menthorq_level_entry')
    menthorq_strength = trade_data.get('menthorq_strength')
    menthorq_distance = trade_data.get('menthorq_distance')

    # Formatage niveau MenthorQ
    if menthorq_level_entry is not None and menthorq_level_entry > 0:
        level_str = f"{menthorq_level_type} @ {menthorq_level_entry:.2f}"
    else:
        level_str = f"{menthorq_level_type} @ N/A"

    # Formatage strength et distance
    if menthorq_strength is not None:
        strength_str = f"{menthorq_strength:.0f}%"
    else:
        strength_str = "N/A"

    # ✅ VALIDATION: Distance 999.0t = valeur par défaut suspecte → afficher N/A
    if menthorq_distance is not None and menthorq_distance > 0 and menthorq_distance < 500:  # Distance raisonnable
        distance_str = f"{menthorq_distance:.1f}t"
    else:
        distance_str = "N/A"

    fields.append({
        "name": "📍 Entry Context",
        "value": (
            f"MenthorQ Level: {level_str}\n"
            f"Strength: {strength_str} | Distance: {distance_str}"
        ),
        "inline": False
    })

    # Footer avec stats jour
    # ✅ CORRIGÉ 18/11: Afficher daily_fees (total journalier) au lieu de fees (trade actuel)
    footer_text = (
        f"📊 Jour: {daily_trades} trades | "
        f"✅ {daily_wins}W-❌{daily_losses}L | "
        f"💰 ${daily_pnl:+,.2f} | "
        f"Fees: ${daily_fees:.2f}"
    )

    # ✅ NOUVEAU 21/11 04:20: Ajouter séries Win/Loss
    win_streak_es = trade_data.get('win_streak_es', {'type': None, 'count': 0})
    win_streak_nq = trade_data.get('win_streak_nq', {'type': None, 'count': 0})

    streak_es_str = format_win_streak(win_streak_es)
    streak_nq_str = format_win_streak(win_streak_nq)

    # Ajouter séries (toujours afficher ES et NQ pour ALL TRADES)
    if streak_es_str != "—" or streak_nq_str != "—":
        footer_text += f"\nSéries: ES {streak_es_str} | NQ {streak_nq_str}"

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "fields": fields,
        "footer": {
            "text": footer_text
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"embeds": [embed]}


def build_heartbeat_embed(heartbeat_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construit un embed Discord pour heartbeat

    Args:
        heartbeat_data: {
            'uptime_hours': int,
            'uptime_minutes': int,
            'cycles': int,
            'positions': Dict[str, Any],  # {symbol: {...}}
            'daily_pnl': float,
            'pnl_by_market': Dict[str, float],  # {symbol: pnl}
            'trades_by_market': Dict[str, Dict],  # {symbol: {'wins': x, 'losses': y}}
            'can_trade': bool,
            'kill_switch_reason': str (optionnel)
        }

    Returns:
        Dict compatible avec Discord webhook embed
    """
    uptime_h = heartbeat_data['uptime_hours']
    uptime_m = heartbeat_data['uptime_minutes']
    cycles = heartbeat_data['cycles']
    positions = heartbeat_data['positions']

    # ✅ CORRIGÉ 18/11: Normaliser daily_pnl (peut être un dict)
    daily_pnl_raw = heartbeat_data.get('daily_pnl', 0.0)
    if isinstance(daily_pnl_raw, dict):
        daily_pnl = daily_pnl_raw.get('daily_pnl', 0.0) if isinstance(daily_pnl_raw.get('daily_pnl'), (int, float)) else 0.0
    elif isinstance(daily_pnl_raw, (int, float)):
        daily_pnl = float(daily_pnl_raw)
    else:
        daily_pnl = 0.0
    pnl_by_market = heartbeat_data.get('pnl_by_market', {})
    trades_by_market = heartbeat_data.get('trades_by_market', {})
    can_trade = heartbeat_data.get('can_trade', True)
    kill_reason = heartbeat_data.get('kill_switch_reason', '')

    # Couleur selon status
    color = DiscordColor.HEARTBEAT_CYAN.value if can_trade else DiscordColor.ERROR_RED.value

    # Description
    status_emoji = Emoji.ONLINE if can_trade else Emoji.OFFLINE
    description = (
        f"{Emoji.TIMER} Uptime: **{uptime_h}h {uptime_m}min** · "
        f"Cycles: **{cycles:,}** · "
        f"Status: {status_emoji} **{'Trading actif' if can_trade else f'Stopped ({kill_reason})'}**"
    )

    # Positions par marché
    positions_lines = []
    sim_map = {"ES": "SIM1", "NQ": "SIM2", "RTY": "SIM3"}

    for sym in ["ES", "NQ", "RTY"]:
        market_emoji = get_market_emoji(sym)
        sim_account = sim_map.get(sym, "SIM?")
        pos = positions.get(sym)

        if pos:
            side = pos['side']
            entry = pos['entry_price']
            tp = pos.get('tp_price', 0)
            sl = pos.get('sl_price', 0)
            strategy = pos.get('strategy', 'UNKNOWN')

            # Calculer durée
            entry_time = pos.get('entry_time')
            if entry_time:
                # ✅ PATCH: Ne pas importer datetime localement (déjà importé globalement)
                duration_min = (datetime.now() - entry_time).total_seconds() / 60
            else:
                duration_min = 0

            # Emoji direction
            side_emoji = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "⚪"

            positions_lines.append(
                f"• {market_emoji} **{sym}** [{sim_account}]: {side_emoji} {side} @ **{entry:.2f}** "
                f"(TP:{tp:.2f} SL:{sl:.2f}) | {strategy} | {duration_min:.0f}min"
            )
        else:
            positions_lines.append(f"• {market_emoji} **{sym}** [{sim_account}]: **FLAT** {Emoji.ONLINE}")

    positions_text = "\n".join(positions_lines)

    # P&L par marché
    pnl_lines = []
    for sym in ["ES", "NQ", "RTY"]:
        sim_account = sim_map.get(sym, "SIM?")
        pnl = pnl_by_market.get(sym, 0.0)
        trades = trades_by_market.get(sym, {'wins': 0, 'losses': 0})
        wins = trades.get('wins', 0)
        losses = trades.get('losses', 0)

        pnl_emoji = get_pnl_emoji(pnl)
        pnl_lines.append(
            f"  • **{sym}** ({sim_account}): {pnl_emoji} **${pnl:+.2f}** ({wins}W / {losses}L)"
        )

    pnl_text = "\n".join(pnl_lines)

    # Emoji P&L total
    total_pnl_emoji = get_pnl_emoji(daily_pnl)

    # Fields
    fields = [
        {
            "name": f"{Emoji.CHART} Positions",
            "value": positions_text,
            "inline": False
        },
        {
            "name": f"{total_pnl_emoji} P&L Jour",
            "value": f"**${daily_pnl:+.2f}** {total_pnl_emoji}",
            "inline": False
        },
        {
            "name": f"{Emoji.CHART_UP} P&L par marché",
            "value": pnl_text,
            "inline": False
        }
    ]

    embed = {
        "title": f"{Emoji.HEARTBEAT} HEARTBEAT — MIA en ligne",
        "description": description,
        "color": color,
        "fields": fields,
        "footer": {
            "text": "Europe/Paris"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"embeds": [embed]}


# ══════════════════════════════════════════════════════════════════════════════
# ✨ DAILY SUMMARY EMBED (Phase 2.3)
# ══════════════════════════════════════════════════════════════════════════════

def build_daily_summary_embed(daily_data: Dict) -> Dict:
    """
    ✨ Phase 2.3: Construit l'embed pour le Daily Summary (23h59)

    Args:
        daily_data: {
            'trades': list[trade_record],
            'by_market': {'ES': [...], 'NQ': [...], 'RTY': [...]},
            'by_session': {'US': [...], 'EU': [...]},
            'by_strategy': {'liquidity_sweep_reversal': [...]},
            'total_pnl': float,
            'total_fees': float,
            'date': datetime,
            'issues': list[str]  # Problèmes détectés
        }

    Returns:
        Discord embed payload
    """
    # ✅ PATCH: datetime déjà importé globalement, pas besoin de réimporter

    trades = daily_data.get('trades', [])
    by_market = daily_data.get('by_market', {})
    by_session = daily_data.get('by_session', {})
    by_strategy = daily_data.get('by_strategy', {})

    # ✅ CORRIGÉ 18/11: Normaliser total_pnl (peut être un dict)
    total_pnl_raw = daily_data.get('total_pnl', 0.0)
    if isinstance(total_pnl_raw, dict):
        total_pnl = total_pnl_raw.get('total_pnl', 0.0) if isinstance(total_pnl_raw.get('total_pnl'), (int, float)) else 0.0
    elif isinstance(total_pnl_raw, (int, float)):
        total_pnl = float(total_pnl_raw)
    else:
        total_pnl = 0.0

    # ✅ CORRIGÉ 18/11: Normaliser total_fees (peut être un dict)
    total_fees_raw = daily_data.get('total_fees', 0.0)
    if isinstance(total_fees_raw, dict):
        total_fees = total_fees_raw.get('total_fees', 0.0) if isinstance(total_fees_raw.get('total_fees'), (int, float)) else 0.0
    elif isinstance(total_fees_raw, (int, float)):
        total_fees = float(total_fees_raw)
    else:
        total_fees = 0.0
    date_str = daily_data.get('date', datetime.now()).strftime('%d %B %Y')
    issues = daily_data.get('issues', [])

    # ✅ CORRIGÉ 20/11: Calculer stats globales depuis by_market (contient TOUS les trades)
    # Le problème était que 'trades' peut être incomplet, mais 'by_market' contient tous les trades
    all_trades_from_markets = []
    for symbol in ['ES', 'NQ', 'RTY']:
        market_trades = by_market.get(symbol, [])
        if isinstance(market_trades, list):
            all_trades_from_markets.extend(market_trades)

    # Utiliser by_market si disponible, sinon fallback sur trades
    if all_trades_from_markets:
        all_trades = all_trades_from_markets
    else:
        all_trades = trades

    # Calculer stats globales depuis tous les trades
    total_trades = len(all_trades)
    total_wins = sum(1 for t in all_trades if t.get('is_win', False))
    total_losses = total_trades - total_wins
    win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0

    # Profit Factor
    gross_wins = sum(t.get('pnl_net', 0) for t in all_trades if t.get('is_win', False))
    gross_losses = abs(sum(t.get('pnl_net', 0) for t in all_trades if not t.get('is_win', False)))
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else 0

    # ✅ CORRIGÉ 20/11: Calculer P&L Net correctement (total_pnl est brut, soustraire fees)
    # total_pnl dans daily_stats est le P&L brut (avant fees)
    # P&L Net = P&L Brut - Fees
    pnl_net = total_pnl - total_fees

    # Description
    pnl_emoji = Emoji.WIN if pnl_net > 0 else Emoji.LOSS if pnl_net < 0 else "⚪"
    description = (
        f"{pnl_emoji} **P&L Net: ${pnl_net:+,.2f}** (fees: ${total_fees:.2f})\n"
        f"{Emoji.CHART} **{total_trades} trades** | WR **{win_rate:.0f}%** | PF **{profit_factor:.1f}**"
    )

    fields = []

    # ══════════════════════════════════════════════════════════════════════════
    # 📈 STATS PAR MARCHÉ
    # ══════════════════════════════════════════════════════════════════════════

    market_lines = []
    market_emojis = {'ES': '📘', 'NQ': '📗', 'RTY': '📙'}

    for symbol in ['ES', 'NQ', 'RTY']:
        market_trades = by_market.get(symbol, [])
        if not market_trades:
            market_lines.append(f"{market_emojis[symbol]} **{symbol}**: Aucun trade")
            continue

        m_total = len(market_trades)
        m_wins = sum(1 for t in market_trades if t['is_win'])
        m_losses = m_total - m_wins
        m_wr = (m_wins / m_total * 100) if m_total > 0 else 0
        m_pnl = sum(t['pnl_net'] for t in market_trades)

        m_gross_wins = sum(t['pnl_net'] for t in market_trades if t['is_win'])
        m_gross_losses = abs(sum(t['pnl_net'] for t in market_trades if not t['is_win']))
        m_pf = (m_gross_wins / m_gross_losses) if m_gross_losses > 0 else 0

        pnl_display = f"${m_pnl:+,.2f}" if m_pnl >= 0 else f"${m_pnl:,.2f}"

        market_lines.append(
            f"{market_emojis[symbol]} **{symbol}**: {m_total}T | WR **{m_wr:.0f}%** | "
            f"PF **{m_pf:.1f}** | P&L **{pnl_display}**"
        )

    fields.append({
        "name": f"{Emoji.CHART} Performance par marché",
        "value": "\n".join(market_lines),
        "inline": False
    })

    # ══════════════════════════════════════════════════════════════════════════
    # 🕒 STATS PAR SESSION
    # ══════════════════════════════════════════════════════════════════════════

    session_lines = []
    session_names = {
        'US': 'US Session',
        'EU': 'EU Session',
        'ASIA': 'Asia Session',
        'Unknown': 'Hors session'
    }

    for session_id, session_name in session_names.items():
        session_trades = by_session.get(session_id, [])
        if not session_trades:
            continue

        s_count = len(session_trades)
        s_pnl = sum(t['pnl_net'] for t in session_trades)
        pnl_display = f"${s_pnl:+,.2f}" if s_pnl >= 0 else f"${s_pnl:,.2f}"

        session_lines.append(f"• **{session_name}**: {pnl_display} ({s_count}T)")

    if session_lines:
        # Trouver meilleure session
        best_session = max(by_session.items(), key=lambda x: sum(t['pnl_net'] for t in x[1]))
        best_session_name = session_names.get(best_session[0], best_session[0])

        fields.append({
            "name": f"{Emoji.CLOCK} Performance par session",
            "value": "\n".join(session_lines) + f"\n\n⭐ **Meilleure**: {best_session_name}",
            "inline": False
        })

    # ══════════════════════════════════════════════════════════════════════════
    # 🏆 TOP 3 STRATÉGIES
    # ══════════════════════════════════════════════════════════════════════════

    # Calculer performance par stratégie
    strategy_performance = []
    for strategy, strat_trades in by_strategy.items():
        if not strat_trades:
            continue

        st_total = len(strat_trades)
        st_wins = sum(1 for t in strat_trades if t['is_win'])
        st_wr = (st_wins / st_total * 100) if st_total > 0 else 0
        st_pnl = sum(t['pnl_net'] for t in strat_trades)

        st_gross_wins = sum(t['pnl_net'] for t in strat_trades if t['is_win'])
        st_gross_losses = abs(sum(t['pnl_net'] for t in strat_trades if not t['is_win']))
        st_pf = (st_gross_wins / st_gross_losses) if st_gross_losses > 0 else 0

        # ✅ CORRIGÉ 17/11: Normaliser nom de stratégie (éviter "unknown" lowercase)
        strategy_normalized = strategy
        if strategy and strategy.lower() == 'unknown':
            strategy_normalized = 'UNKNOWN'
        elif not strategy or strategy == '':
            strategy_normalized = 'UNKNOWN'

        strategy_performance.append({
            'name': strategy_normalized,
            'trades': st_total,
            'wr': st_wr,
            'pf': st_pf,
            'pnl': st_pnl
        })

    # Trier par P&L
    strategy_performance.sort(key=lambda x: x['pnl'], reverse=True)

    top_strategies = []
    for i, strat in enumerate(strategy_performance[:3], 1):
        pnl_display = f"${strat['pnl']:+,.2f}" if strat['pnl'] >= 0 else f"${strat['pnl']:,.2f}"
        top_strategies.append(
            f"{i}) **{strat['name']}** (WR {strat['wr']:.0f}%, PF {strat['pf']:.1f}, {pnl_display})"
        )

    if top_strategies:
        fields.append({
            "name": f"{Emoji.WIN} Top 3 stratégies",
            "value": "\n".join(top_strategies),
            "inline": False
        })

    # ══════════════════════════════════════════════════════════════════════════
    # ⚠️ PROBLÈMES DÉTECTÉS
    # ══════════════════════════════════════════════════════════════════════════

    if issues:
        issue_lines = [f"• {issue}" for issue in issues[:5]]  # Max 5 problèmes
        fields.append({
            "name": f"{Emoji.ERROR} Problèmes détectés",
            "value": "\n".join(issue_lines),
            "inline": False
        })

    # ✅ CORRIGÉ 20/11: Couleur selon P&L Net (pas brut)
    if pnl_net > 0:
        color = DiscordColor.WIN_GREEN.value  # ✅ PATCH: .value ajouté
    elif pnl_net < 0:
        color = DiscordColor.LOSS_RED.value   # ✅ PATCH: .value ajouté
    else:
        color = DiscordColor.INFO_BLUE.value

    embed = {
        "title": f"{Emoji.SUMMARY} DAILY SUMMARY — {date_str}",
        "description": description,
        "color": color,
        "fields": fields,
        "footer": {
            "text": f"Généré à 23:59 (Europe/Paris) | Total fees: ${total_fees:.2f}"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"embeds": [embed]}


# ══════════════════════════════════════════════════════════════════════════
# 🆕 NOUVEL EMBED - SIGNAL REJETÉ - 15 NOV 2025
# ══════════════════════════════════════════════════════════════════════════

def build_signal_rejected_embed(rejection_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construit un embed Discord pour signal rejeté (monitoring filtres)

    Args:
        rejection_data: {
            'symbol': str,
            'side': str,
            'price': float,
            'rejection_reason': str,
            'confluence': float,
            'strategy': str,
            'filter_details': dict (optionnel)
        }

    Returns:
        Dict compatible avec Discord webhook embed
    """
    symbol = rejection_data['symbol']
    side = rejection_data.get('side', 'UNKNOWN')
    price = rejection_data.get('price', 0.0)
    reason = rejection_data.get('rejection_reason', 'N/A')
    confluence = rejection_data.get('confluence', 0.0)
    # ✅ CORRIGÉ 19/11: Normaliser et formater stratégie
    strategy_raw = rejection_data.get('strategy', 'UNKNOWN')
    # ✅ FIX: Convertir en string si nécessaire
    if not isinstance(strategy_raw, str):
        strategy_raw = str(strategy_raw) if strategy_raw else 'UNKNOWN'
    if strategy_raw and strategy_raw.lower() == 'unknown':
        strategy = 'UNKNOWN'
    elif not strategy_raw or strategy_raw == '':
        strategy = 'UNKNOWN'
    else:
        strategy = strategy_raw

    # ⭐ FORMATER POUR AFFICHAGE DISCORD (nom lisible)
    strategy = _format_strategy_name_for_discord(strategy)

    filter_details = rejection_data.get('filter_details', {})

    # Emojis
    side_emoji = get_side_emoji(side)
    market_emoji = get_market_emoji(symbol)

    # Couleur warning
    color = DiscordColor.WARNING_YELLOW.value

    # Description
    description = (
        f"{market_emoji} **{symbol}** | "
        f"{side_emoji} {side} @ **{price:.2f}** | "
        f"{Emoji.CONFLUENCE} {confluence:.2f}"
    )

    # Fields
    fields = [
        {
            "name": "🚫 Raison du rejet",
            "value": reason,
            "inline": False
        },
        {
            "name": f"{Emoji.STRATEGY} Setup",
            "value": strategy,
            "inline": True
        },
        {
            "name": f"{Emoji.CLOCK} Session",
            "value": get_current_session(),
            "inline": True
        }
    ]

    # Ajouter détails filtre si disponibles
    if filter_details:
        details_text = "\n".join([f"• {k}: {v}" for k, v in filter_details.items()])
        fields.append({
            "name": "📋 Détails Filtres",
            "value": details_text,
            "inline": False
        })

    embed = {
        "title": f"⚠️ SIGNAL REJETÉ",
        "description": description,
        "color": color,
        "fields": fields,
        "footer": {
            "text": "Monitoring filtres actifs"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    return {"embeds": [embed]}
