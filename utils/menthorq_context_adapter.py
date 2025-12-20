"""
menthorq_context_adapter.py

🎯 ADAPTER ML_READY → MENTHORQ FORMAT

Convertit les données ML_READY (49 features Sierra Chart) vers le format
attendu par MenthorQDecisionEngine.

Version: 1.0
Date: 7 Novembre 2025
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def ml_ready_to_menthorq(ml_data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """
    Convertit ML_READY → MenthorQ format complet

    Args:
        ml_data: Données ML_READY du dumper Sierra Chart
        symbol: ES / NQ / RTY

    Returns:
        Dict compatible avec MenthorQDecisionEngine.decide()

    Format MenthorQ attendu:
    {
      "sym": "ES"|"NQ",
      "t": timestamp,
      "price": float,
      "session": {"phase": str, "regime": str},
      "macro": {"vix": float, "vix_trend": str},
      "mentorq": {
          "gamma": {...},
          "swing": {...},
          "blind": {...},
          "scanner": {...},
          "qscore": float
      },
      "micro": {"vwap": {...}, "vp": {...}},
      "ofdom": {...},
      "lead": {...},
      "cluster": {...},
      "mia": {"score": float, "state": str},
      "prev": {"state": str}
    }
    """

    # ═══════════════════════════════════════════════════════════════
    # 1️⃣ INFOS DE BASE
    # ═══════════════════════════════════════════════════════════════

    price = ml_data.get('mid', 0.0)
    timestamp = ml_data.get('timestamp', datetime.now().timestamp())

    # ═══════════════════════════════════════════════════════════════
    # 2️⃣ SESSION
    # ═══════════════════════════════════════════════════════════════

    session = _extract_session(ml_data)

    # ═══════════════════════════════════════════════════════════════
    # 3️⃣ MACRO
    # ═══════════════════════════════════════════════════════════════

    macro = _extract_macro(ml_data)

    # ═══════════════════════════════════════════════════════════════
    # 4️⃣ MENTORQ (Gamma, Swing, Blind, Scanner, QScore)
    # ═══════════════════════════════════════════════════════════════

    mentorq = _extract_mentorq(ml_data, symbol)

    # ═══════════════════════════════════════════════════════════════
    # 5️⃣ MICRO (VWAP, Volume Profile)
    # ═══════════════════════════════════════════════════════════════

    micro = _extract_micro(ml_data)

    # ═══════════════════════════════════════════════════════════════
    # 6️⃣ OFDOM (OrderFlow + DOM)
    # ═══════════════════════════════════════════════════════════════

    ofdom = _extract_ofdom(ml_data)

    # ═══════════════════════════════════════════════════════════════
    # 7️⃣ LEADERSHIP (ES vs NQ)
    # ═══════════════════════════════════════════════════════════════

    lead = _extract_leadership(ml_data, symbol)

    # ═══════════════════════════════════════════════════════════════
    # 8️⃣ CLUSTER (Confluence signals)
    # ═══════════════════════════════════════════════════════════════

    cluster = _extract_cluster(ml_data)

    # ═══════════════════════════════════════════════════════════════
    # 9️⃣ MIA (Bullish Score)
    # ═══════════════════════════════════════════════════════════════

    mia = _extract_mia(ml_data)

    # ═══════════════════════════════════════════════════════════════
    # 🔟 PREV STATE (État précédent)
    # ═══════════════════════════════════════════════════════════════

    prev = _extract_prev(ml_data)

    # ═══════════════════════════════════════════════════════════════
    # 📦 ASSEMBLER
    # ═══════════════════════════════════════════════════════════════

    menthorq_context = {
        "sym": symbol,
        "t": timestamp,
        "price": price,
        "session": session,
        "macro": macro,
        "mentorq": mentorq,
        "micro": micro,
        "ofdom": ofdom,
        "lead": lead,
        "cluster": cluster,
        "mia": mia,
        "prev": prev
    }

    logger.debug(
        f"[{symbol}] ML_READY -> MenthorQ: "
        f"price={price:.2f}, qscore={mentorq['qscore']:.1f}, "
        f"mia={mia['score']:.1f}"
    )

    return menthorq_context


# ═══════════════════════════════════════════════════════════════════
# 🔧 EXTRACTEURS PAR COMPOSANT
# ═══════════════════════════════════════════════════════════════════

def _extract_session(ml_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extrait infos session

    Returns:
        {"phase": "OPEN|MID|POWER|OFF", "regime": "TREND|RANGE|DEFENSIF"}
    """
    # Session phase depuis ML_READY
    session_id = ml_data.get('session_id', 'Unknown')
    session_progress = ml_data.get('session_progress', 0.5)

    # Mapper session_id → phase MenthorQ
    if 'Open' in session_id or session_progress < 0.15:
        phase = "OPEN"
    elif 'Close' in session_id or session_progress > 0.85:
        phase = "POWER"
    elif 'Mid' in session_id or 0.15 <= session_progress <= 0.85:
        phase = "MID"
    else:
        phase = "OFF"

    # Régime depuis ATR / volatilité
    atr = ml_data.get('atr', 0)
    atr_pct = ml_data.get('atr_pct', 0)

    if atr_pct > 1.5:  # Haute volatilité
        regime = "TREND"
    elif atr_pct < 0.8:  # Basse volatilité
        regime = "RANGE"
    else:
        regime = "DEFENSIF"

    return {"phase": phase, "regime": regime}


def _extract_macro(ml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait macro (VIX)

    Returns:
        {"vix": float, "vix_trend": "up|down|flat"}
    """
    vix = ml_data.get('vix', 20.0)

    # VIX trend depuis day_change_pct ou historique
    vix_change = ml_data.get('day_change_pct', 0.0)

    if vix_change > 5:
        vix_trend = "up"
    elif vix_change < -5:
        vix_trend = "down"
    else:
        vix_trend = "flat"

    return {"vix": float(vix), "vix_trend": vix_trend}


def _extract_mentorq(ml_data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """
    Extrait composants MentorQ (Gamma, Swing, Blind, Scanner, QScore)

    Returns:
        {
            "gamma": {"dist_to_HVL_pts": float, "flip_active": bool, "wall_side": str},
            "swing": {"avail": bool, "state": str, "dist_pts": float, "retest_ok": bool},
            "blind": {"nearby": bool, "distance_ticks": int, "direction": str},
            "scanner": {"recent": {...}},
            "qscore": float
        }
    """
    # GAMMA
    gamma = _extract_gamma(ml_data)

    # SWING
    swing = _extract_swing(ml_data)

    # BLIND
    blind = _extract_blind(ml_data)

    # SCANNER
    scanner = _extract_scanner(ml_data)

    # QSCORE (Quality Score MenthorQ)
    qscore = _calculate_qscore(ml_data)

    return {
        "gamma": gamma,
        "swing": swing,
        "blind": blind,
        "scanner": scanner,
        "qscore": qscore
    }


def _extract_gamma(ml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait données Gamma

    Returns:
        {"dist_to_HVL_pts": float, "flip_active": bool, "wall_side": str}
    """
    hvl = ml_data.get('hvl', 0)
    mid = ml_data.get('mid', 0)

    dist_to_HVL_pts = abs(mid - hvl) if hvl else 999.0

    # Gamma flip
    gamma_flip = ml_data.get('gamma_flip', None)
    flip_active = gamma_flip is not None

    # Wall side depuis net_gex
    net_gex = ml_data.get('net_gex', 0)
    if net_gex > 0:
        wall_side = "CALL"
    elif net_gex < 0:
        wall_side = "PUT"
    else:
        wall_side = "None"

    return {
        "dist_to_HVL_pts": dist_to_HVL_pts,
        "flip_active": flip_active,
        "wall_side": wall_side
    }


def _extract_swing(ml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait Swing Level

    Returns:
        {"avail": bool, "state": str, "dist_pts": float, "retest_ok": bool}
    """
    # Swing high/low depuis ML_READY
    swing_high = ml_data.get('swing_high', 0)
    swing_low = ml_data.get('swing_low', 0)
    mid = ml_data.get('mid', 0)

    avail = swing_high > 0 or swing_low > 0

    if not avail:
        return {"avail": False, "state": "None", "dist_pts": 999.0, "retest_ok": False}

    # Déterminer state (below/at/above)
    if mid < swing_low - 2:
        state = "below"
        dist_pts = abs(mid - swing_low)
    elif mid > swing_high + 2:
        state = "above"
        dist_pts = abs(mid - swing_high)
    else:
        state = "at"
        dist_pts = 0.0

    # Retest OK si proche d'un swing level
    retest_ok = dist_pts < 5.0

    return {
        "avail": avail,
        "state": state,
        "dist_pts": dist_pts,
        "retest_ok": retest_ok
    }


def _extract_blind(ml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait Blind Spot (zones aveugles GEX)

    Returns:
        {"nearby": bool, "distance_ticks": int, "direction": str}
    """
    # Blind spot depuis menthor_distances
    menthor_dist = ml_data.get('menthor_distances', {})

    near_gex_up = menthor_dist.get('near_gex_up', 999)
    near_gex_dn = menthor_dist.get('near_gex_dn', -999)

    # Distance minimale en ticks (1 tick = 0.25 pour ES/NQ)
    tick_size = 0.25
    dist_up_ticks = int(abs(near_gex_up) / tick_size)
    dist_dn_ticks = int(abs(near_gex_dn) / tick_size)

    # Choisir la plus proche
    if dist_up_ticks < dist_dn_ticks:
        distance_ticks = dist_up_ticks
        direction = "up"
    else:
        distance_ticks = dist_dn_ticks
        direction = "down"

    nearby = distance_ticks < 50  # < 50 ticks = proche

    return {
        "nearby": nearby,
        "distance_ticks": distance_ticks,
        "direction": direction if nearby else "None"
    }


def _extract_scanner(ml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait Scanner (événements récents)

    Returns:
        {"recent": {"HVL_BREAK": {"age": int}, ...}}
    """
    # TODO: Implémenter détection événements depuis historique
    # Pour l'instant, retour vide
    return {"recent": {}}


def _calculate_qscore(ml_data: Dict[str, Any]) -> float:
    """
    Calcule Quality Score MenthorQ (0-5)

    Basé sur:
    - Confluence signaux
    - Proximité niveaux clés
    - Alignement gamma + orderflow
    - Qualité session
    """
    score = 0.0

    # 1. Confluence (max 1.5 pts)
    confluence = ml_data.get('confluence', 0.0)
    score += confluence * 1.5

    # 2. Proximité HVL (max 1.0 pt)
    hvl = ml_data.get('hvl', 0)
    mid = ml_data.get('mid', 0)
    atr = ml_data.get('atr', 1.0)

    if hvl and atr:
        dist_hvl_atr = abs(mid - hvl) / atr
        if dist_hvl_atr < 0.5:
            score += 1.0
        elif dist_hvl_atr < 1.0:
            score += 0.5

    # 3. Alignement gamma + orderflow (max 1.5 pts)
    net_gex = ml_data.get('net_gex', 0)
    delta_pct = ml_data.get('deltaPct', 0.5)

    # Si net_gex positif (call wall) ET delta buying → bullish aligné
    if net_gex > 0 and delta_pct > 0.6:
        score += 1.5
    elif net_gex < 0 and delta_pct < 0.4:
        score += 1.5
    elif abs(net_gex) < 100:  # Neutre
        score += 0.5

    # 4. Session quality (max 1.0 pt)
    session_progress = ml_data.get('session_progress', 0.5)
    if 0.1 < session_progress < 0.9:  # Éviter début/fin session
        score += 1.0
    else:
        score += 0.3

    return min(5.0, score)  # Cap à 5.0


def _extract_micro(ml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait micro (VWAP, Volume Profile)

    Returns:
        {
            "vwap": {"above": bool, "slope": str, "band": str},
            "vp": {"at_level": str, "reclaim": bool}
        }
    """
    # VWAP
    vwap = ml_data.get('vwap', 0)
    mid = ml_data.get('mid', 0)

    above = mid > vwap if vwap else False

    # VWAP slope depuis d_vwap_atr
    d_vwap_atr = ml_data.get('d_vwap_atr', 0)
    if d_vwap_atr > 0.5:
        slope = "up"
    elif d_vwap_atr < -0.5:
        slope = "down"
    else:
        slope = "flat"

    # Band (inside SD1, SD2, etc.)
    # Simplifié: si d_vwap_atr < 1 → inside, sinon sd1/sd2
    if abs(d_vwap_atr) < 1.0:
        band = "inside"
    elif abs(d_vwap_atr) < 2.0:
        band = "sd1"
    else:
        band = "sd2"

    # Volume Profile
    vva = ml_data.get('vva', {})
    vah = vva.get('vah', 0) if isinstance(vva, dict) else 0
    val = vva.get('val', 0) if isinstance(vva, dict) else 0
    poc = vva.get('poc', 0) if isinstance(vva, dict) else 0

    # Déterminer at_level
    at_level = "none"
    if poc and abs(mid - poc) < 2:
        at_level = "POC"
    elif vah and abs(mid - vah) < 2:
        at_level = "VAH"
    elif val and abs(mid - val) < 2:
        at_level = "VAL"

    # Reclaim (si prix repassé au-dessus VWAP récemment)
    # Simplifié: True si proche VWAP
    reclaim = abs(d_vwap_atr) < 0.3

    return {
        "vwap": {"above": above, "slope": slope, "band": band},
        "vp": {"at_level": at_level, "reclaim": reclaim}
    }


def _extract_ofdom(ml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait OrderFlow + DOM

    Returns:
        {
            "ask_imbalance": float,
            "seller_absorption": bool,
            "l1_eq_bbo": bool,
            "spread_ticks": int
        }
    """
    # Ask/Bid imbalance depuis DOM
    dom = ml_data.get('dom', {})

    if isinstance(dom, dict):
        ask_size = dom.get('ask_size', 1)
        bid_size = dom.get('bid_size', 1)
        ask_imbalance = ask_size / bid_size if bid_size > 0 else 1.0
    else:
        ask_imbalance = 1.0

    # Seller absorption (delta négatif fort)
    delta_pct = ml_data.get('deltaPct', 0.5)
    seller_absorption = delta_pct < 0.35

    # L1 equilibrium (spread serré)
    spread = ml_data.get('spread', 1)
    tick_size = 0.25
    spread_ticks = int(spread / tick_size) if spread else 1

    l1_eq_bbo = spread_ticks <= 1

    return {
        "ask_imbalance": ask_imbalance,
        "seller_absorption": seller_absorption,
        "l1_eq_bbo": l1_eq_bbo,
        "spread_ticks": spread_ticks
    }


def _extract_leadership(ml_data: Dict[str, Any], symbol: str) -> Dict[str, Any]:
    """
    Extrait Leadership (ES vs NQ)

    Returns:
        {"nq_stronger_than_es": bool, "sync_ok": bool}
    """
    # TODO: Nécessite données ES + NQ simultanées
    # Pour l'instant, valeurs neutres

    return {
        "nq_stronger_than_es": symbol == "NQ",  # Simplifié
        "sync_ok": True  # Assume sync OK
    }


def _extract_cluster(ml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait Cluster (confluence signaux)

    Returns:
        {
            "signals": {
                "cluster_confluence": bool,
                "cluster_strong": bool,
                "status": "inside|outside"
            }
        }
    """
    confluence = ml_data.get('confluence', 0.0)

    cluster_confluence = confluence > 0.65
    cluster_strong = confluence > 0.80

    # Status (inside/outside cluster)
    # Simplifié: si confluence haute → inside
    status = "inside" if cluster_confluence else "outside"

    return {
        "signals": {
            "cluster_confluence": cluster_confluence,
            "cluster_strong": cluster_strong,
            "status": status
        }
    }


def _extract_mia(ml_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrait MIA Score

    Returns:
        {"score": float (0-100), "state": "BULLISH|NEUTRE|BEARISH"}
    """
    # MIA score depuis mia_bullish_score (-1 à +1 → 0 à 100)
    mia_score_raw = ml_data.get('mia_bullish_score', 0.0)
    mia_score = (mia_score_raw + 1.0) * 50.0  # Convertir -1..+1 → 0..100

    # État
    if mia_score > 65:
        state = "BULLISH"
    elif mia_score < 35:
        state = "BEARISH"
    else:
        state = "NEUTRE"

    return {"score": mia_score, "state": state}


def _extract_prev(ml_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extrait état précédent (pour continuité)

    Returns:
        {"state": "NEUTRE|BULLISH|BEARISH"}
    """
    # TODO: Tracker état précédent
    # Pour l'instant, neutre
    return {"state": "NEUTRE"}


# ═══════════════════════════════════════════════════════════════════
# 🧪 TESTS
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    logging.basicConfig(level=logging.DEBUG)

    # Test data
    test_ml_data = {
        'mid': 6050.25,
        'atr': 12.5,
        'vix': 18.2,
        'hvl': 6045.0,
        'net_gex': 1500,
        'vwap': 6048.0,
        'deltaPct': 0.68,
        'confluence': 0.75,
        'session_id': 'US Open',
        'session_progress': 0.25,
        'mia_bullish_score': 0.45,
        'day_change_pct': -2.5,
        'vva': {'vah': 6055.0, 'val': 6040.0, 'poc': 6048.0},
        'menthor_distances': {'near_gex_up': 8.5, 'near_gex_dn': -12.0},
        'dom': {'ask_size': 50, 'bid_size': 30},
        'spread': 0.25,
        'd_vwap_atr': 0.18,
        'atr_pct': 1.1,
        'gamma_flip': None,
        'swing_high': 6060.0,
        'swing_low': 6035.0
    }

    print("=" * 60)
    print("TEST ML_READY -> MenthorQ")
    print("=" * 60)

    result = ml_ready_to_menthorq(test_ml_data, "ES")

    print("\nMenthorQ Context:")
    print(json.dumps(result, indent=2, default=str))

    print("\n" + "=" * 60)
    print("TEST TERMINE")
    print("=" * 60)


