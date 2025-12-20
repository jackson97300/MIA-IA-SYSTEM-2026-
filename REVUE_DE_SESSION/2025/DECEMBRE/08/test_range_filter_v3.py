#!/usr/bin/env python3
"""
TEST RANGE FILTER V3 - CALIBRATION FINALE
==========================================

Corrections:
1. Seuil breakout: < 5 ticks (pas 3)
2. Zones ajustees: < 25% = BOTTOM (pas 20%)
3. Breakout = proche bord + momentum contraire

Date: 08/12/2025
"""

from dataclasses import dataclass
from typing import List, Tuple

# Configuration V3
BOTTOM_ZONE_PCT = 25  # < 25% = BOTTOM
TOP_ZONE_PCT = 75     # > 75% = TOP
BREAKOUT_PROXIMITY_TICKS = 5  # < 5 ticks du bord = danger

@dataclass
class RangeAnalysisV3:
    is_range: bool
    range_type: str
    range_high: float
    range_low: float
    range_size_ticks: float
    position_pct: float
    zone: str
    criteria_met: List[str]
    confidence: float
    breakout_risk: str
    distance_to_low_ticks: float
    distance_to_high_ticks: float
    recommended_action: str

def analyze_range_v3(snapshot: dict, tick_size: float = 0.25) -> RangeAnalysisV3:
    """Analyse V3 avec calibration corrigee"""

    mid = snapshot.get('mid', 0)
    atr = snapshot.get('atr', 2.0)

    structure = snapshot.get('structure', {})
    ibh = structure.get('ibh', 0)
    ibl = structure.get('ibl', 0)

    vva = snapshot.get('vva', {})
    vah = vva.get('vah', 0)
    val = vva.get('val', 0)

    vwap_up1 = snapshot.get('vwap_up1', 0)
    vwap_dn1 = snapshot.get('vwap_dn1', 0)
    d_vwap_ticks = abs(snapshot.get('d_vwap_ticks', 0))

    vol_regime = snapshot.get('volatility_regime', 2.0)
    bullish_score = snapshot.get('mia_bullish_score', 0)

    # Criteres de range
    criteria_met = []
    range_score = 0

    in_ib = False
    if ibh > 0 and ibl > 0:
        in_ib = ibl <= mid <= ibh
        if in_ib:
            range_score += 2
            criteria_met.append("IN_IB")

    in_va = False
    if vah > 0 and val > 0:
        in_va = val <= mid <= vah
        if in_va:
            range_score += 2
            criteria_met.append("IN_VA")

    if vol_regime <= 1.5:
        range_score += 2
        criteria_met.append("LOW_VOL")

    if abs(bullish_score) < 0.25:
        range_score += 2
        criteria_met.append("NEUTRAL")

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

    is_range = range_score >= 6

    # Bornes - PRIORITE IB
    if is_range:
        if ibh > 0 and ibl > 0:
            range_type = "IB"
            range_high = ibh
            range_low = ibl
        elif vah > 0 and val > 0:
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

    # Position + distances
    if is_range and range_high > range_low:
        position_pct = ((mid - range_low) / (range_high - range_low)) * 100
        position_pct = max(0, min(100, position_pct))
        distance_to_low_ticks = (mid - range_low) / tick_size
        distance_to_high_ticks = (range_high - mid) / tick_size
    else:
        position_pct = 50
        distance_to_low_ticks = 999
        distance_to_high_ticks = 999

    # Zones V3
    if position_pct < BOTTOM_ZONE_PCT:
        zone = "BOTTOM"
    elif position_pct > TOP_ZONE_PCT:
        zone = "TOP"
    else:
        zone = "MIDDLE"

    # Detection breakout V3 - PLUS AGRESSIVE
    breakout_risk = "NONE"

    if is_range:
        # Proche du bas + bearish = BREAKOUT DOWN
        # Seuil: < 5 ticks du bord ET score bearish (< -0.10)
        if distance_to_low_ticks < BREAKOUT_PROXIMITY_TICKS and bullish_score < -0.10:
            breakout_risk = "BEARISH"
            criteria_met.append("BREAKOUT_RISK_DOWN")

        # Proche du haut + bullish = BREAKOUT UP
        elif distance_to_high_ticks < BREAKOUT_PROXIMITY_TICKS and bullish_score > 0.10:
            breakout_risk = "BULLISH"
            criteria_met.append("BREAKOUT_RISK_UP")

    # Action recommandee
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

    return RangeAnalysisV3(
        is_range=is_range,
        range_type=range_type,
        range_high=range_high,
        range_low=range_low,
        range_size_ticks=range_size_ticks,
        position_pct=position_pct,
        zone=zone,
        criteria_met=criteria_met,
        confidence=range_score / 12.0,
        breakout_risk=breakout_risk,
        distance_to_low_ticks=distance_to_low_ticks,
        distance_to_high_ticks=distance_to_high_ticks,
        recommended_action=action
    )

def should_block_v3(signal: str, analysis: RangeAnalysisV3) -> tuple:
    """Decide si le trade doit etre bloque"""

    if not analysis.is_range:
        return False, "TREND - Signal autorise"

    if analysis.breakout_risk == "BEARISH":
        return True, f"BREAKOUT DOWN - {analysis.distance_to_low_ticks:.0f}t du bas + bearish"

    if analysis.breakout_risk == "BULLISH":
        return True, f"BREAKOUT UP - {analysis.distance_to_high_ticks:.0f}t du haut + bullish"

    if analysis.zone == "BOTTOM":
        if signal == "SHORT":
            return True, f"RANGE: SHORT interdit au bas ({analysis.position_pct:.0f}%)"
        return False, f"RANGE: LONG OK en bas (FADE)"

    elif analysis.zone == "TOP":
        if signal == "LONG":
            return True, f"RANGE: LONG interdit en haut ({analysis.position_pct:.0f}%)"
        return False, f"RANGE: SHORT OK en haut (FADE)"

    else:
        return True, f"RANGE: Milieu - pas de trade ({analysis.position_pct:.0f}%)"

# ===============================================================
# TESTS
# ===============================================================

def run_power_hour_test():
    """Test sur Power Hour"""

    print("\n" + "="*70)
    print("SIMULATION V3 - POWER HOUR")
    print("="*70)

    context = {
        'atr': 2.39, 'volatility_regime': 1.0,
        'structure': {'ibh': 6850.00, 'ibl': 6840.00},
        'vva': {'vah': 6852.00, 'val': 6842.00},
        'vwap_up1': 6848.00, 'vwap_dn1': 6843.00, 'd_vwap_ticks': 5.0,
    }

    trades = [
        {'time': '20:38', 'dir': 'LONG', 'entry': 6841.00, 'pnl': -256.50, 'bullish': -0.15},
        {'time': '21:16', 'dir': 'LONG', 'entry': 6840.75, 'pnl': -256.50, 'bullish': -0.20},
    ]

    total_saved = 0
    blocked = 0

    for t in trades:
        snap = context.copy()
        snap['mid'] = t['entry']
        snap['mia_bullish_score'] = t['bullish']

        analysis = analyze_range_v3(snap)
        block, reason = should_block_v3(t['dir'], analysis)

        print(f"\n[{t['time']}] {t['dir']} @ {t['entry']:.2f}")
        print(f"   Position: {analysis.position_pct:.0f}% | Zone: {analysis.zone}")
        print(f"   Distance bas: {analysis.distance_to_low_ticks:.1f}t | Bullish: {t['bullish']}")
        print(f"   Breakout Risk: {analysis.breakout_risk}")
        print(f"   PnL reel: ${t['pnl']:+.2f}")

        if block:
            print(f"   => BLOQUE: {reason}")
            print(f"   => ECONOMIE: +${abs(t['pnl']):.2f}")
            total_saved += abs(t['pnl'])
            blocked += 1
        else:
            print(f"   => AUTORISE: {reason}")

    print(f"\n{'='*70}")
    print(f"RESULTAT: {blocked}/2 trades bloques | Economie: +${total_saved:.2f}")
    print(f"{'='*70}")

    return blocked, total_saved

def run_robustness_tests():
    """Tests de robustesse"""

    print("\n" + "="*70)
    print("TESTS ROBUSTESSE V3")
    print("="*70)

    tests = [
        # Power Hour scenario - DOIT BLOQUER
        ("Power Hour Trade 1", {
            'mid': 6841.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': -0.15,
            'structure': {'ibh': 6850.00, 'ibl': 6840.00},
            'vva': {'vah': 6852.00, 'val': 6842.00},
            'vwap_up1': 6848.00, 'vwap_dn1': 6843.00, 'd_vwap_ticks': 8.0
        }, 'LONG', True, 'BREAKOUT'),

        # Range normal - LONG au bas OK (pas bearish)
        ("Range - LONG bas (neutre)", {
            'mid': 6842.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.05,
            'structure': {'ibh': 6850.00, 'ibl': 6840.00},
            'vva': {'vah': 6852.00, 'val': 6842.00},
            'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': 6.0
        }, 'LONG', False, 'FADE'),

        # Range - SHORT au bas BLOQUE
        ("Range - SHORT bas", {
            'mid': 6842.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.05,
            'structure': {'ibh': 6850.00, 'ibl': 6840.00},
            'vva': {'vah': 6852.00, 'val': 6842.00},
            'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': 6.0
        }, 'SHORT', True, 'SHORT'),

        # Range - Milieu BLOQUE
        ("Range - Milieu", {
            'mid': 6846.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.0,
            'structure': {'ibh': 6850.00, 'ibl': 6840.00},
            'vva': {'vah': 6852.00, 'val': 6842.00},
            'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': 2.0
        }, 'LONG', True, 'Milieu'),

        # Tendance - PAS RANGE
        ("Tendance forte", {
            'mid': 6880.00, 'atr': 4.0, 'volatility_regime': 3.0, 'mia_bullish_score': 0.6,
            'structure': {'ibh': 6850.00, 'ibl': 6840.00},
            'vva': {'vah': 6852.00, 'val': 6842.00},
            'vwap_up1': 6870.00, 'vwap_dn1': 6850.00, 'd_vwap_ticks': -40.0
        }, 'LONG', False, 'TREND'),

        # Range - Haut + bullish = BREAKOUT UP
        ("Range - Haut bullish", {
            'mid': 6849.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.20,
            'structure': {'ibh': 6850.00, 'ibl': 6840.00},
            'vva': {'vah': 6852.00, 'val': 6842.00},
            'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': -3.0
        }, 'LONG', True, 'BREAKOUT'),
    ]

    passed = 0

    for name, snap, signal, expect_block, expect_reason in tests:
        analysis = analyze_range_v3(snap)
        block, reason = should_block_v3(signal, analysis)

        match_block = block == expect_block
        match_reason = expect_reason.upper() in reason.upper()

        ok = match_block and match_reason
        status = "[PASS]" if ok else "[FAIL]"
        passed += 1 if ok else 0

        print(f"\n{status} {name}:")
        print(f"   Signal: {signal} @ {snap['mid']:.2f}")
        print(f"   Range: {analysis.is_range} | Zone: {analysis.zone} | Breakout: {analysis.breakout_risk}")
        print(f"   Attendu: block={expect_block} ({expect_reason})")
        print(f"   Obtenu:  block={block} ({reason})")

    print(f"\n{'='*70}")
    print(f"RESULTAT: {passed}/{len(tests)} tests passes ({passed/len(tests)*100:.0f}%)")
    print(f"{'='*70}")

    return passed, len(tests)

# ===============================================================
# MAIN
# ===============================================================

if __name__ == "__main__":
    blocked, saved = run_power_hour_test()
    passed, total = run_robustness_tests()

    print("\n" + "="*70)
    print("VERDICT FINAL V3")
    print("="*70)

    is_ready = passed >= total - 1 and blocked >= 1

    print(f"""
   POWER HOUR:
   - Trades bloques: {blocked}/2
   - Economie: +${saved:.2f}

   ROBUSTESSE:
   - Tests passes: {passed}/{total} ({passed/total*100:.0f}%)

   VERDICT: {"PRET POUR IMPLEMENTATION" if is_ready else "CORRECTIONS NECESSAIRES"}
    """)

