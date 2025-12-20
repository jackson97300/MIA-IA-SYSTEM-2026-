#!/usr/bin/env python3
"""
TEST RANGE FILTER V2 - AVEC DÉTECTION BREAKOUT
===============================================

Corrections:
1. Zones ajustées: BOTTOM <20%, TOP >80%
2. Ajout détection breakout (cassure potentielle)
3. SL adaptatif pour range

Date: 08/12/2025
"""

import os
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION V2
# ═══════════════════════════════════════════════════════════════════════════════

# Zones ajustées - plus conservatrices
BOTTOM_ZONE_PCT = 20  # < 20% = BOTTOM
TOP_ZONE_PCT = 80     # > 80% = TOP

# Seuil de breakout
BREAKOUT_PROXIMITY_TICKS = 3  # Si < 3 ticks du bord = danger breakout

# ═══════════════════════════════════════════════════════════════════════════════
# RANGE ANALYSIS V2
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RangeAnalysisV2:
    """Résultat de l'analyse de range V2"""
    is_range: bool
    range_type: str
    range_high: float
    range_low: float
    range_size_ticks: float
    position_pct: float
    zone: str  # 'BOTTOM', 'MIDDLE', 'TOP'
    criteria_met: List[str]
    confidence: float

    # Nouveaux champs V2
    breakout_risk: str  # 'NONE', 'BEARISH', 'BULLISH'
    distance_to_low_ticks: float
    distance_to_high_ticks: float
    recommended_action: str

def analyze_range_v2(snapshot: dict, tick_size: float = 0.25) -> RangeAnalysisV2:
    """Analyse de range V2 avec détection breakout"""

    mid = snapshot.get('mid', 0)
    atr = snapshot.get('atr', 2.0)

    # Structure
    structure = snapshot.get('structure', {})
    ibh = structure.get('ibh', 0)
    ibl = structure.get('ibl', 0)

    # Value Area
    vva = snapshot.get('vva', {})
    vah = vva.get('vah', 0)
    val = vva.get('val', 0)

    # VWAP Bands
    vwap_up1 = snapshot.get('vwap_up1', 0)
    vwap_dn1 = snapshot.get('vwap_dn1', 0)
    d_vwap_ticks = abs(snapshot.get('d_vwap_ticks', 0))

    # Indicateurs
    vol_regime = snapshot.get('volatility_regime', 2.0)
    bullish_score = snapshot.get('mia_bullish_score', 0)
    cum_delta = snapshot.get('cum_delta_day', 0)

    # ═══════════════════════════════════════════════════════════════
    # CRITÈRES DE RANGE (même logique que V1)
    # ═══════════════════════════════════════════════════════════════

    criteria_met = []
    range_score = 0

    # Prix dans IB?
    in_ib = False
    if ibh > 0 and ibl > 0:
        in_ib = ibl <= mid <= ibh
        if in_ib:
            range_score += 2
            criteria_met.append("IN_IB")

    # Prix dans VA?
    in_va = False
    if vah > 0 and val > 0:
        in_va = val <= mid <= vah
        if in_va:
            range_score += 2
            criteria_met.append("IN_VA")

    # Volatilité basse?
    if vol_regime <= 1.5:
        range_score += 2
        criteria_met.append("LOW_VOL")

    # Score bullish neutre?
    if abs(bullish_score) < 0.25:
        range_score += 2
        criteria_met.append("NEUTRAL")

    # VWAP plat?
    if vwap_up1 > 0 and vwap_dn1 > 0 and atr > 0:
        vwap_band_width = vwap_up1 - vwap_dn1
        if (vwap_band_width / atr) < 2.5:
            range_score += 2
            criteria_met.append("VWAP_FLAT")
        if vwap_dn1 <= mid <= vwap_up1:
            range_score += 1
            criteria_met.append("IN_VWAP_BANDS")

    if d_vwap_ticks < 15:
        range_score += 1
        criteria_met.append("CLOSE_VWAP")

    # ═══════════════════════════════════════════════════════════════
    # DÉCISION RANGE
    # ═══════════════════════════════════════════════════════════════

    is_range = range_score >= 6

    # Bornes du range - UTILISER LES MÊMES pour cohérence!
    if is_range:
        if in_ib and ibh > 0 and ibl > 0:
            range_type = "IB"
            range_high = ibh
            range_low = ibl
        elif in_va and vah > 0 and val > 0:
            range_type = "VA"
            range_high = vah
            range_low = val
        elif vwap_up1 > 0 and vwap_dn1 > 0:
            range_type = "VWAP_BANDS"
            range_high = vwap_up1
            range_low = vwap_dn1
        else:
            is_range = False
            range_type = "NONE"
            range_high = range_low = 0
    else:
        range_type = "NONE"
        range_high = range_low = 0

    range_size_ticks = (range_high - range_low) / tick_size if range_high > range_low else 0

    # ═══════════════════════════════════════════════════════════════
    # POSITION DANS LE RANGE + DISTANCES
    # ═══════════════════════════════════════════════════════════════

    if is_range and range_high > range_low:
        position_pct = ((mid - range_low) / (range_high - range_low)) * 100
        position_pct = max(0, min(100, position_pct))
        distance_to_low_ticks = (mid - range_low) / tick_size
        distance_to_high_ticks = (range_high - mid) / tick_size
    else:
        position_pct = 50
        distance_to_low_ticks = 999
        distance_to_high_ticks = 999

    # Zones V2 - PLUS CONSERVATRICES
    if position_pct < BOTTOM_ZONE_PCT:
        zone = "BOTTOM"
    elif position_pct > TOP_ZONE_PCT:
        zone = "TOP"
    else:
        zone = "MIDDLE"

    # ═══════════════════════════════════════════════════════════════
    # DÉTECTION BREAKOUT V2 - NOUVEAU!
    # ═══════════════════════════════════════════════════════════════

    breakout_risk = "NONE"

    if is_range:
        # Trop proche du bas + momentum baissier = risque breakout baissier
        if distance_to_low_ticks < BREAKOUT_PROXIMITY_TICKS and bullish_score < -0.1:
            breakout_risk = "BEARISH"
            criteria_met.append("⚠️BREAKOUT_RISK_DOWN")

        # Trop proche du haut + momentum haussier = risque breakout haussier
        elif distance_to_high_ticks < BREAKOUT_PROXIMITY_TICKS and bullish_score > 0.1:
            breakout_risk = "BULLISH"
            criteria_met.append("⚠️BREAKOUT_RISK_UP")

    # ═══════════════════════════════════════════════════════════════
    # RECOMMANDATION V2
    # ═══════════════════════════════════════════════════════════════

    if not is_range:
        action = "FOLLOW_TREND"
    elif breakout_risk == "BEARISH":
        action = "NO_TRADE_BREAKOUT_DOWN"
    elif breakout_risk == "BULLISH":
        action = "NO_TRADE_BREAKOUT_UP"
    elif zone == "BOTTOM":
        action = "LONG_FADE"
    elif zone == "TOP":
        action = "SHORT_FADE"
    else:
        action = "NO_TRADE_MIDDLE"

    confidence = range_score / 12.0

    return RangeAnalysisV2(
        is_range=is_range,
        range_type=range_type,
        range_high=range_high,
        range_low=range_low,
        range_size_ticks=range_size_ticks,
        position_pct=position_pct,
        zone=zone,
        criteria_met=criteria_met,
        confidence=confidence,
        breakout_risk=breakout_risk,
        distance_to_low_ticks=distance_to_low_ticks,
        distance_to_high_ticks=distance_to_high_ticks,
        recommended_action=action
    )

def should_block_trade_v2(signal: str, range_analysis: RangeAnalysisV2) -> Tuple[bool, str]:
    """V2 avec détection breakout"""

    if not range_analysis.is_range:
        return False, "TREND - Signal autorisé"

    # NOUVEAU: Bloquer si risque de breakout!
    if range_analysis.breakout_risk == "BEARISH":
        return True, f"⚠️ BREAKOUT RISK DOWN - Prix à {range_analysis.distance_to_low_ticks:.0f}t du bas + bearish"

    if range_analysis.breakout_risk == "BULLISH":
        return True, f"⚠️ BREAKOUT RISK UP - Prix à {range_analysis.distance_to_high_ticks:.0f}t du haut + bullish"

    zone = range_analysis.zone

    if zone == "BOTTOM":
        if signal == "SHORT":
            return True, f"RANGE: Pas de SHORT en bas ({range_analysis.position_pct:.0f}%)"
        else:
            return False, f"RANGE: LONG OK en bas - FADE"

    elif zone == "TOP":
        if signal == "LONG":
            return True, f"RANGE: Pas de LONG en haut ({range_analysis.position_pct:.0f}%)"
        else:
            return False, f"RANGE: SHORT OK en haut - FADE"

    else:  # MIDDLE
        return True, f"RANGE: Pas de trade au MILIEU ({range_analysis.position_pct:.0f}%)"

# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION POWER HOUR V2
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_power_hour_v2():
    """Simulation avec détection breakout"""

    print("\n" + "="*80)
    print("SIMULATION V2 - POWER HOUR AVEC DÉTECTION BREAKOUT")
    print("="*80)

    # Contexte Power Hour avec score bearish
    power_hour_context = {
        'mid': 6845.00,
        'atr': 2.39,
        'volatility_regime': 1.0,
        'mia_bullish_score': -0.11,  # Légèrement bearish!
        'cum_delta_day': 625,
        'structure': {
            'ibh': 6850.00,
            'ibl': 6840.00,
        },
        'vva': {
            'vah': 6852.00,
            'val': 6842.00,
        },
        'vwap_up1': 6848.00,
        'vwap_dn1': 6843.00,
        'd_vwap_ticks': 5.0,
    }

    # Trades réels avec contexte précis
    power_hour_trades = [
        {
            'time': '203808',
            'direction': 'LONG',
            'entry': 6841.00,  # Proche du bas!
            'pnl': -256.50,
            'context': {'mia_bullish_score': -0.15}  # Score bearish au moment du trade
        },
        {
            'time': '211628',
            'direction': 'LONG',
            'entry': 6840.75,  # Très proche du bas!
            'pnl': -256.50,
            'context': {'mia_bullish_score': -0.20}  # Score plus bearish
        },
    ]

    print(f"\n📊 CONTEXTE POWER HOUR:")
    print(f"   Range IB: {power_hour_context['structure']['ibl']:.2f} - {power_hour_context['structure']['ibh']:.2f}")
    print(f"   Score bullish: {power_hour_context['mia_bullish_score']:.2f} (légèrement bearish)")

    # Simuler chaque trade
    print(f"\n{'─'*80}")
    print(f"SIMULATION V2 DES TRADES:")
    print(f"{'─'*80}")

    total_saved = 0
    trades_blocked = 0

    for trade in power_hour_trades:
        # Créer snapshot avec contexte du trade
        trade_snapshot = power_hour_context.copy()
        trade_snapshot['mid'] = trade['entry']
        trade_snapshot['mia_bullish_score'] = trade['context'].get('mia_bullish_score', -0.11)

        # Analyser V2
        analysis = analyze_range_v2(trade_snapshot)
        should_block, reason = should_block_trade_v2(trade['direction'], analysis)

        print(f"\n   Trade @ {trade['time']}:")
        print(f"   ├─ Direction: {trade['direction']}")
        print(f"   ├─ Entry: {trade['entry']:.2f}")
        print(f"   ├─ Position: {analysis.position_pct:.0f}% ({analysis.zone})")
        print(f"   ├─ Distance bas: {analysis.distance_to_low_ticks:.1f} ticks")
        print(f"   ├─ Score bullish: {trade_snapshot['mia_bullish_score']:.2f}")
        print(f"   ├─ Breakout Risk: {analysis.breakout_risk}")
        print(f"   ├─ Résultat réel: ${trade['pnl']:+.2f}")

        if should_block:
            print(f"   ├─ V2 FILTRE: ❌ BLOQUÉ")
            print(f"   └─ Raison: {reason}")
            print(f"       💰 ÉCONOMIE: +${abs(trade['pnl']):.2f}")
            total_saved += abs(trade['pnl'])
            trades_blocked += 1
        else:
            print(f"   └─ V2 FILTRE: ✅ AUTORISÉ - {reason}")

    print(f"\n{'='*80}")
    print(f"RÉSUMÉ V2:")
    print(f"{'='*80}")
    print(f"   Trades bloqués: {trades_blocked}/{len(power_hour_trades)}")
    print(f"   ÉCONOMIE TOTALE: +${total_saved:.2f}")

    return total_saved, trades_blocked

# ═══════════════════════════════════════════════════════════════════════════════
# TESTS ROBUSTESSE V2
# ═══════════════════════════════════════════════════════════════════════════════

def test_robustness_v2():
    """Tests V2 avec breakout detection"""

    print("\n" + "="*80)
    print("TEST ROBUSTESSE V2")
    print("="*80)

    test_cases = [
        # Scénario clé: Proche du bas + bearish = BREAKOUT RISK
        {
            'name': 'Power Hour - Proche bas + bearish (DOIT BLOQUER)',
            'snapshot': {
                'mid': 6841.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': -0.15,
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6848.00, 'vwap_dn1': 6843.00, 'd_vwap_ticks': 8.0
            },
            'signal': 'LONG',
            'expected_block': True,
            'expected_reason': 'BREAKOUT'
        },
        # Range safe - LONG OK au bas
        {
            'name': 'Range safe - Bas + neutre (LONG OK)',
            'snapshot': {
                'mid': 6842.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.05,  # Neutre
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': 6.0
            },
            'signal': 'LONG',
            'expected_block': False,
            'expected_reason': 'FADE'
        },
        # Range - SHORT au bas BLOQUÉ
        {
            'name': 'Range - SHORT au bas (BLOQUÉ)',
            'snapshot': {
                'mid': 6842.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.05,
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': 6.0
            },
            'signal': 'SHORT',
            'expected_block': True,
            'expected_reason': 'BOTTOM'
        },
        # Range - MILIEU
        {
            'name': 'Range - Milieu (TOUT BLOQUÉ)',
            'snapshot': {
                'mid': 6846.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.0,
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': 2.0
            },
            'signal': 'LONG',
            'expected_block': True,
            'expected_reason': 'MIDDLE'
        },
        # Tendance - PAS DE RANGE
        {
            'name': 'Tendance forte (SIGNAL OK)',
            'snapshot': {
                'mid': 6880.00, 'atr': 4.0, 'volatility_regime': 3.0, 'mia_bullish_score': 0.6,
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6870.00, 'vwap_dn1': 6850.00, 'd_vwap_ticks': -40.0
            },
            'signal': 'LONG',
            'expected_block': False,
            'expected_reason': 'TREND'
        },
        # Proche du haut + bullish = breakout up risk
        {
            'name': 'Proche haut + bullish (BREAKOUT UP)',
            'snapshot': {
                'mid': 6849.50, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.20,
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': -3.0
            },
            'signal': 'SHORT',
            'expected_block': True,
            'expected_reason': 'BREAKOUT'
        },
    ]

    passed = 0
    failed = 0

    for tc in test_cases:
        analysis = analyze_range_v2(tc['snapshot'])
        should_block, reason = should_block_trade_v2(tc['signal'], analysis)

        # Vérification avec raison
        reason_matches = tc['expected_reason'].upper() in reason.upper()

        if should_block == tc['expected_block'] and reason_matches:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"\n{status} {tc['name']}:")
        print(f"   Signal: {tc['signal']} @ {tc['snapshot']['mid']:.2f}")
        print(f"   Range: {analysis.is_range} | Zone: {analysis.zone} | Breakout: {analysis.breakout_risk}")
        print(f"   Attendu: block={tc['expected_block']} ({tc['expected_reason']})")
        print(f"   Obtenu:  block={should_block}")
        print(f"   Raison: {reason}")

    print(f"\n{'='*80}")
    print(f"RÉSULTAT V2: {passed}/{len(test_cases)} tests passés ({passed/len(test_cases)*100:.0f}%)")
    print(f"{'='*80}")

    return passed, len(test_cases)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*80)
    print("TEST FILTRE RANGE V2 - AVEC DÉTECTION BREAKOUT")
    print("="*80)

    # Test 1: Simulation Power Hour avec breakout detection
    saved, blocked = simulate_power_hour_v2()

    # Test 2: Tests robustesse
    passed, total = test_robustness_v2()

    # Verdict
    print("\n" + "="*80)
    print("VERDICT FINAL V2")
    print("="*80)

    is_ready = passed >= total - 1 and blocked >= 1  # Au moins 1 trade Power Hour bloqué

    print(f"""
    📊 SIMULATION POWER HOUR:
    └─ Trades bloqués: {blocked}/2
    └─ Économie: +${saved:.2f}

    🧪 TESTS ROBUSTESSE:
    └─ Tests passés: {passed}/{total} ({passed/total*100:.0f}%)

    ✅ VERDICT:
    └─ Détection breakout: {"✅ FONCTIONNE" if blocked >= 1 else "❌ NE FONCTIONNE PAS"}
    └─ Prêt pour implémentation: {"✅ OUI" if is_ready else "❌ NON"}
    """)

    print("="*80)

