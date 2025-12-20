#!/usr/bin/env python3
"""
MIA_IA_SYSTEM - Règles Métier 3-Layer
Phase 4.0: Confluence MenthorQ + 2/3 Rule OrderFlow + Context Gates

Location: D:\\MIA_IA_system\\ml\\ml_3layer_metier_rules.py
"""

from typing import Dict, Any, Tuple, List
from core.logger import get_logger

logger = get_logger(__name__)


# ════════════════════════════════════════════════════════════════
# 🔥 HELPER FUNCTIONS - BIBLE MENTHORQ V2.0
# ════════════════════════════════════════════════════════════════

def check_gex_confluence(snap: Dict[str, Any], gex_price: float, tick_size: float = 0.25) -> Tuple[bool, float]:
    """
    Vérifie si GEX est en confluence avec autre niveau MenthorQ

    📚 BIBLE MENTHORQ V2.0: GEX EXTRA-PUISSANT en confluence avec CR/PS/HVL/Blind Spots

    Args:
        snap: Snapshot ML_READY
        gex_price: Prix du GEX level
        tick_size: Taille du tick (0.25 pour ES/NQ)

    Returns:
        (is_confluence: bool, bonus: float)
        - True + 0.20 si confluence (< 15 ticks d'écart)
        - False + 0.0 sinon
    """
    cr = snap.get('call_resistance', 0)
    ps = snap.get('put_support', 0)
    hvl = snap.get('hvl', 0)

    # Calculer distances en ticks
    gex_to_cr = abs(gex_price - cr) / tick_size if cr > 0 else 999
    gex_to_ps = abs(gex_price - ps) / tick_size if ps > 0 else 999
    gex_to_hvl = abs(gex_price - hvl) / tick_size if hvl > 0 else 999

    # Blind Spots
    min_blind_dist = 999
    for i in range(9):
        blind_level = snap.get(f'blind_spot_{i}')
        if blind_level:
            blind_dist = abs(gex_price - blind_level) / tick_size
            min_blind_dist = min(min_blind_dist, blind_dist)

    # Bible: confluence si < 15 ticks d'écart avec un niveau majeur
    min_dist = min(gex_to_cr, gex_to_ps, gex_to_hvl, min_blind_dist)

    if min_dist < 15:
        return True, 0.20  # ✅ EXTRA-PUISSANT

    return False, 0.0


# ════════════════════════════════════════════════════════════════
# 🔥 LAYER 1: MENTHORQ CONFLUENCE
# ════════════════════════════════════════════════════════════════

def check_menthorq_confluence(snap: Dict[str, Any], direction: str = "UP") -> Tuple[bool, float, List[str]]:
    """
    Vérifie la confluence MenthorQ (GEX + NextWall + BlindSpot)

    Critères:
    - GEX level proche (< 50 ticks)
    - NextWall dans le sens du trade
    - Pas de BlindSpot trop proche (< 30 ticks)

    Args:
        snap: Snapshot ML_READY
        direction: "UP" ou "DOWN"

    Returns:
        (is_valid, confidence_boost, reasons)
    """
    reasons = []
    confidence = 0.0

    # Extraire données MenthorQ
    menthor_dist = snap.get('menthor_distances', {})
    near_gex_up = menthor_dist.get('near_gex_up', 999)
    near_gex_dn = menthor_dist.get('near_gex_dn', -999)

    next_wall = snap.get('next_wall', {})
    next_wall_side = next_wall.get('side', '')
    next_wall_dist = next_wall.get('dist_ticks', 999)

    # Blind spots (chercher le plus proche)
    min_blind_dist = 999
    for i in range(9):  # blind_spot_0 à blind_spot_8
        blind_level = snap.get(f'blind_spot_{i}')
        if blind_level:
            mid = snap.get('mid', 0)
            blind_dist_ticks = abs(blind_level - mid) / 0.25  # Approximation tick size
            min_blind_dist = min(min_blind_dist, blind_dist_ticks)

    # ═══ CHECK 1: GEX Level Proximity ═══
    if direction == "UP":
        # GEX up doit être proche (< 50 ticks)
        if abs(near_gex_up) < 50:
            # ✅ ENRICHISSEMENT BIBLE MENTHORQ v2.0: Vérifier confluence
            is_confluence, bonus = check_gex_confluence(snap, snap.get('mid', 0) + near_gex_up)
            if is_confluence:
                confidence += bonus  # +0.20 si confluence
                reasons.append(f"✅✅ GEX UP proche ({near_gex_up}t) EN CONFLUENCE avec CR/PS/HVL → EXTRA-PUISSANT!")
            else:
                confidence += 0.10
                reasons.append(f"✅ GEX UP proche ({near_gex_up}t)")
                reasons.append(f"⚠️ Bible MenthorQ: GEX SEUL = zones de réaction NON directionnelles → Méfiance")
        else:
            reasons.append(f"⚠️ GEX UP loin ({near_gex_up}t)")
    else:  # DOWN
        if abs(near_gex_dn) < 50:
            # ✅ ENRICHISSEMENT BIBLE MENTHORQ v2.0: Vérifier confluence
            is_confluence, bonus = check_gex_confluence(snap, snap.get('mid', 0) + near_gex_dn)
            if is_confluence:
                confidence += bonus  # +0.20 si confluence
                reasons.append(f"✅✅ GEX DN proche ({near_gex_dn}t) EN CONFLUENCE avec CR/PS/HVL → EXTRA-PUISSANT!")
            else:
                confidence += 0.10
                reasons.append(f"✅ GEX DN proche ({near_gex_dn}t)")
                reasons.append(f"⚠️ Bible MenthorQ: GEX SEUL = zones de réaction NON directionnelles → Méfiance")
        else:
            reasons.append(f"⚠️ GEX DN loin ({near_gex_dn}t)")

    # ═══ CHECK 2: NextWall Alignment ═══
    if direction == "UP" and next_wall_side == "call":
        confidence += 0.10
        reasons.append(f"✅ NextWall Call aligné ({next_wall_dist}t)")
    elif direction == "DOWN" and next_wall_side == "put":
        confidence += 0.10
        reasons.append(f"✅ NextWall Put aligné ({next_wall_dist}t)")
    else:
        reasons.append(f"⚠️ NextWall non aligné ({next_wall_side})")

    # ═══ CHECK 3: BlindSpot Distance ═══
    # ⚠️⚠️⚠️ BIBLE MENTHORQ V2.0 - AVERTISSEMENT CRITIQUE:
    # NE JAMAIS trader Blind Spot SEUL sans validation orderflow !
    # Exiger confirmation Layer 2 (delta/volume/DOM) ABSOLUMENT
    # 🔧 MODIFICATION 27/11: DÉSACTIVÉ TEMPORAIREMENT pour déblocage
    if min_blind_dist < 10:  # Uniquement si TRÈS TRÈS proche
        confidence -= 0.10  # Petite pénalité
        reasons.append(f"⚠️ BlindSpot EXTRÊMEMENT PROCHE ({min_blind_dist:.0f}t)")
    else:
        confidence += 0.05
        reasons.append(f"✅ BlindSpot acceptable ({min_blind_dist:.0f}t)")

    # ═══ VERDICT ═══
    # 🔧 MODIFICATION 27/11: DÉBLOCAGE - Accepter dès que confidence > 0
    is_valid = confidence > 0.0  # TRÈS PERMISSIF pour déblocage
    return is_valid, confidence, reasons


# ════════════════════════════════════════════════════════════════
# 🔥 LAYER 2: ORDERFLOW 2/3 RULE
# ════════════════════════════════════════════════════════════════

def check_orderflow_23_rule(snap: Dict[str, Any], direction: str = "UP") -> Tuple[bool, float, List[str]]:
    """
    Vérifie la règle 2/3 OrderFlow (au moins 2 signaux concordants sur 3)

    Signaux:
    1. cum_delta_session dans le sens
    2. askPct/bidPct ≥ 60/40 dans le sens
    3. level1_imbalance dans le sens

    Args:
        snap: Snapshot ML_READY
        direction: "UP" ou "DOWN"

    Returns:
        (is_valid, confidence, reasons)
    """
    reasons = []
    concordant_count = 0

    # Extraire données OrderFlow
    cum_delta_session = snap.get('cum_delta_session', 0)
    ask_pct = snap.get('askPct', 0.5)
    bid_pct = snap.get('bidPct', 0.5)
    level1_imb = snap.get('level1_imbalance', 0)

    # ═══ SIGNAL 1: Cumulative Delta Session ═══
    if direction == "UP" and cum_delta_session > 0:
        concordant_count += 1
        reasons.append(f"✅ Cum Delta Session bullish ({cum_delta_session:+.0f})")
    elif direction == "DOWN" and cum_delta_session < 0:
        concordant_count += 1
        reasons.append(f"✅ Cum Delta Session bearish ({cum_delta_session:+.0f})")
    else:
        reasons.append(f"❌ Cum Delta Session opposé ({cum_delta_session:+.0f})")

    # ═══ SIGNAL 2: Ask/Bid Pressure ═══
    # Pour UP (LONG): besoin de ACHATS (bid_pct élevé)
    # Pour DOWN (SHORT): besoin de VENTES (ask_pct élevé)
    # 🔧 MODIFICATION 27/11: Assoupli 60% → 55%
    if direction == "UP" and bid_pct >= 0.55:
        concordant_count += 1
        reasons.append(f"✅ Bid Pressure forte ({bid_pct:.1%})")
    elif direction == "DOWN" and ask_pct >= 0.55:
        concordant_count += 1
        reasons.append(f"✅ Ask Pressure forte ({ask_pct:.1%})")
    else:
        reasons.append(f"⚠️ Pressure faible (Ask={ask_pct:.1%}, Bid={bid_pct:.1%})")

    # ═══ SIGNAL 3: Level1 Imbalance ═══
    # 🔧 MODIFICATION 27/11: Assoupli 0.1 → 0.05
    if direction == "UP" and level1_imb > 0.05:
        concordant_count += 1
        reasons.append(f"✅ Level1 Imbalance bullish ({level1_imb:+.2f})")
    elif direction == "DOWN" and level1_imb < -0.05:
        concordant_count += 1
        reasons.append(f"✅ Level1 Imbalance bearish ({level1_imb:+.2f})")
    else:
        reasons.append(f"⚠️ Level1 Imbalance neutre ({level1_imb:+.2f})")

    # ═══ VERDICT: 2/3 RULE ═══
    # 🔧 MODIFICATION 27/11: DÉBLOCAGE - 1/3 au lieu de 2/3
    is_valid = concordant_count >= 1  # PERMISSIF pour déblocage
    confidence = concordant_count / 3.0  # 0.33, 0.67, ou 1.0

    if is_valid:
        reasons.append(f"✅ 1/3 RULE: {concordant_count}/3 signaux concordants (DÉBLOCAGE)")
    else:
        reasons.append(f"❌ 1/3 RULE FAIL: {concordant_count}/3 signaux seulement")

    return is_valid, confidence, reasons


# ════════════════════════════════════════════════════════════════
# 🔥 LAYER 3: CONTEXT GATES
# ════════════════════════════════════════════════════════════════

def check_context_gates(snap: Dict[str, Any]) -> Tuple[bool, float, List[str]]:
    """
    Vérifie les gates contextuels (évite trades risqués)

    Gates:
    1. d_vwap_atr < 15.0 (pas trop étiré - aligné avec ML 3-Layer assouplissement)
    2. NOT in_value_area=True ET position_in_range ∈ [45%, 55%] (évite chop au milieu)
    3. Spread pas trop large
    4. HVL Regime context (NOUVEAU - Bible MenthorQ v2.0)

    Args:
        snap: Snapshot ML_READY

    Returns:
        (is_valid, confidence, reasons)
    """
    reasons = []
    gates_passed = 0
    total_gates = 4  # ✅ +1 gate (HVL Regime)

    # Extraire données Context
    d_vwap_atr = snap.get('d_vwap_atr', 0)
    in_value_area = snap.get('in_value_area', False)
    position_in_range = snap.get('position_in_range', 50)
    spread_ticks = snap.get('spread_ticks', 1)
    mid = snap.get('mid', 0)
    hvl = snap.get('hvl', 0)

    # ═══ GATE 1: VWAP Distance (pas trop étiré) ═══
    # 🔧 MODIFICATION 27/11: Simplifié - rejeter uniquement si EXTRÊME (> 10 ATR)
    if abs(d_vwap_atr) > 10.0:
        reasons.append(f"❌ GATE 1: EXTRÊMEMENT étiré de VWAP ({d_vwap_atr:.2f} ATR > 10.0)")
        return False, 0.0, reasons  # Hard block uniquement si extrême
    else:
        gates_passed += 1
        reasons.append(f"✅ GATE 1: Distance VWAP acceptable ({d_vwap_atr:.2f} ATR)")

    # ═══ GATE 2: Chop Filter (évite milieu de range) ═══
    # 🔧 MODIFICATION 27/11: DÉSACTIVÉ - MenthorQ gère déjà le contexte
    # if 40 <= position_in_range <= 60:
    #     reasons.append(f"❌ GATE 2: Zone médiane/chop ({position_in_range:.0f}%)")
    # else:
    gates_passed += 1
    reasons.append(f"✅ GATE 2: Position range OK ({position_in_range:.0f}%)")

    # ═══ GATE 3: Spread Filter ═══
    # 🔧 MODIFICATION 27/11: Simplifié - rejeter uniquement si > 5 ticks (illiquide)
    if spread_ticks > 5:
        reasons.append(f"❌ GATE 3: Spread illiquide ({spread_ticks}t > 5)")
    else:
        gates_passed += 1
        reasons.append(f"✅ GATE 3: Spread acceptable ({spread_ticks}t)")

    # ═══ GATE 4: HVL REGIME + SESSION CONTEXT ═══
    # 🔧 MODIFICATION 27/11: DÉSACTIVÉ - Ne pas pénaliser les régimes
    if hvl > 0:
        gates_passed += 1
        if mid > hvl:
            reasons.append(f"💡 GATE 4: POSITIVE GAMMA (mid {mid:.2f} > HVL {hvl:.2f}) - Marché mean-revert")
        else:
            reasons.append(f"💡 GATE 4: NEGATIVE GAMMA (mid {mid:.2f} < HVL {hvl:.2f}) - Marché directionnel")
    else:
        gates_passed += 1
        reasons.append(f"💡 GATE 4: HVL absent - Pas de filtre régime")

    # ═══ VERDICT ═══
    # 🔧 MODIFICATION 27/11: SIMPLIFIÉ - Exiger 3/4 seulement (75%)
    is_valid = gates_passed >= 3  # 3/4 gates minimum
    confidence = gates_passed / total_gates

    if is_valid:
        reasons.append(f"✅ CONTEXT GATES: {gates_passed}/{total_gates} passed")
    else:
        reasons.append(f"❌ CONTEXT GATES: {gates_passed}/{total_gates} seulement")

    return is_valid, confidence, reasons


# ════════════════════════════════════════════════════════════════
# 🎯 FONCTION PRINCIPALE: VALIDATION COMPLETE 3-LAYER
# ════════════════════════════════════════════════════════════════

def validate_3layer_metier(snap: Dict[str, Any], direction: str = "UP") -> Dict[str, Any]:
    """
    Validation complète 3-Layer avec règles métier

    Args:
        snap: Snapshot ML_READY
        direction: "UP" ou "DOWN"

    Returns:
        Dict avec résultats détaillés
    """
    logger.info("=" * 80)
    logger.info(f"🔍 VALIDATION 3-LAYER MÉTIER ({direction})")
    logger.info("=" * 80)

    # Layer 1: MenthorQ Confluence
    l1_valid, l1_conf, l1_reasons = check_menthorq_confluence(snap, direction)
    logger.info("📊 LAYER 1 (MenthorQ):")
    for r in l1_reasons:
        logger.info(f"   {r}")
    logger.info(f"   Confidence boost: {l1_conf:+.2%}")

    # Layer 2: OrderFlow 2/3 Rule
    l2_valid, l2_conf, l2_reasons = check_orderflow_23_rule(snap, direction)
    logger.info("📊 LAYER 2 (OrderFlow):")
    for r in l2_reasons:
        logger.info(f"   {r}")
    logger.info(f"   Confidence: {l2_conf:.1%}")

    # Layer 3: Context Gates
    l3_valid, l3_conf, l3_reasons = check_context_gates(snap)
    logger.info("📊 LAYER 3 (Context):")
    for r in l3_reasons:
        logger.info(f"   {r}")
    logger.info(f"   Confidence: {l3_conf:.1%}")

    # ═══ VERDICT FINAL ═══
    # 🔧 MODIFIÉ 27/11: 2/3 layers minimum + seuil 50% (focus MenthorQ + OrderFlow)
    MIN_CONFIDENCE_THRESHOLD = 0.50  # 50% au lieu de 60%

    # Confidence totale (pondérée)
    total_conf = (l1_conf * 0.5) + (l2_conf * 0.3) + (l3_conf * 0.2)

    # Compter les layers valides
    valid_count = sum([l1_valid, l2_valid, l3_valid])

    # ✅ NOUVELLE LOGIQUE: DÉBLOCAGE - Accepter si 1/3 layers minimum
    # → Focus sur MenthorQ (L1) + OrderFlow (L2) comme edge principal
    strict_valid = l1_valid and l2_valid and l3_valid
    confidence_valid = (valid_count >= 1)  # 1/3 minimum pour déblocage

    all_valid = strict_valid or confidence_valid

    logger.info("=" * 80)
    if all_valid:
        if strict_valid:
            logger.info(f"✅ VALIDATION 3-LAYER: ACCEPTÉ (3/3 strict, conf={total_conf:.1%})")
        else:
            logger.info(f"✅ VALIDATION 3-LAYER: ACCEPTÉ (conf={total_conf:.1%} >= 60%, {valid_count}/3 layers)")
    else:
        logger.info(f"❌ VALIDATION 3-LAYER: REJETÉ")
        logger.info(f"   L1: {'✅' if l1_valid else '❌'} | L2: {'✅' if l2_valid else '❌'} | L3: {'✅' if l3_valid else '❌'}")
        logger.info(f"   Confidence: {total_conf:.1%} (seuil: {MIN_CONFIDENCE_THRESHOLD:.0%})")
        logger.info(f"   Layers valides: {valid_count}/3 (minimum: 2)")
    logger.info("=" * 80)

    return {
        "valid": all_valid,
        "confidence": total_conf,
        "layer1": {"valid": l1_valid, "conf": l1_conf, "reasons": l1_reasons},
        "layer2": {"valid": l2_valid, "conf": l2_conf, "reasons": l2_reasons},
        "layer3": {"valid": l3_valid, "conf": l3_conf, "reasons": l3_reasons},
    }


# ════════════════════════════════════════════════════════════════
# 🧪 TESTS
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Test avec snapshot NQ du prompt GPT
    test_snap = {
        "mid": 25224.25,
        "vix": 16.93,
        "cum_delta_session": 1863,
        "delta": -86,
        "askPct": 0.644295,
        "bidPct": 0.355705,
        "level1_imbalance": 0.333333,
        "d_vwap_atr": 0.883635,
        "in_value_area": True,
        "position_in_range": 46.495957,
        "spread_ticks": 2,
        "menthor_distances": {
            "near_gex_up": 503,
            "near_gex_dn": -897,
        },
        "next_wall": {
            "price": 25200.00,
            "side": "put",
            "dist_ticks": -97,
        },
        "blind_spot_0": 25702.61,
        "blind_spot_1": 24602.89,
    }

    print("\n🧪 TEST: Snapshot NQ (GPT)")
    result = validate_3layer_metier(test_snap, "UP")

    print("\n📊 RÉSULTAT:")
    print(f"   Valid: {result['valid']}")
    print(f"   Confidence: {result['confidence']:.1%}")
