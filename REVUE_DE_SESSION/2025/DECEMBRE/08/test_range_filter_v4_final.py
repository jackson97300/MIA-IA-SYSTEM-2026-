#!/usr/bin/env python3
"""
RANGE FILTER V4 FINAL - ES + NQ
================================

Solution complete et solide:
1. Filtre taille minimum/maximum par instrument
2. Detection breakout
3. Zones FADE (25%/75%)
4. Configuration specifique ES vs NQ

Date: 08/12/2025
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional

# ===============================================================
# CONFIGURATION PAR INSTRUMENT
# ===============================================================

INSTRUMENT_CONFIG = {
    'ES': {
        'tick_size': 0.25,
        'tick_value': 12.50,

        # Taille range
        'min_range_ticks': 15,    # Minimum 15 ticks (3.75 pts)
        'max_range_ticks': 60,    # Maximum 60 ticks (15 pts)
        'ideal_range_ticks': (20, 40),  # Range ideal

        # Zones
        'bottom_zone_pct': 25,
        'top_zone_pct': 75,

        # Breakout
        'breakout_proximity_ticks': 5,
        'breakout_momentum_threshold': 0.10,
    },
    'NQ': {
        'tick_size': 0.25,
        'tick_value': 5.00,

        # NQ est plus volatil -> ranges plus larges
        'min_range_ticks': 20,    # Minimum 20 ticks (5 pts)
        'max_range_ticks': 80,    # Maximum 80 ticks (20 pts)
        'ideal_range_ticks': (30, 60),  # Range ideal

        # Zones
        'bottom_zone_pct': 25,
        'top_zone_pct': 75,

        # Breakout - NQ bouge plus vite
        'breakout_proximity_ticks': 8,
        'breakout_momentum_threshold': 0.10,
    }
}

# ===============================================================
# DATACLASS RESULTAT
# ===============================================================

@dataclass
class RangeAnalysisV4:
    """Resultat analyse range V4"""
    symbol: str
    is_range: bool
    range_type: str              # 'IB', 'VA', 'VWAP_BANDS', 'NONE'
    range_quality: str           # 'IDEAL', 'ACCEPTABLE', 'TOO_SMALL', 'TOO_LARGE'

    range_high: float
    range_low: float
    range_size_ticks: float
    range_size_points: float

    position_pct: float
    zone: str                    # 'BOTTOM', 'MIDDLE', 'TOP'

    distance_to_low_ticks: float
    distance_to_high_ticks: float

    breakout_risk: str           # 'NONE', 'BEARISH', 'BULLISH'

    criteria_met: List[str] = field(default_factory=list)
    confidence: float = 0.0
    recommended_action: str = ""
    reason: str = ""

# ===============================================================
# ANALYSE RANGE V4
# ===============================================================

def analyze_range_v4(snapshot: dict, symbol: str = 'ES') -> RangeAnalysisV4:
    """
    Analyse range V4 - Version complete

    Args:
        snapshot: Donnees du snapshot
        symbol: 'ES' ou 'NQ'

    Returns:
        RangeAnalysisV4 avec tous les details
    """

    config = INSTRUMENT_CONFIG.get(symbol, INSTRUMENT_CONFIG['ES'])
    tick_size = config['tick_size']

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

    # ═══════════════════════════════════════════════════════════
    # CRITERES DE RANGE
    # ═══════════════════════════════════════════════════════════

    criteria_met = []
    range_score = 0

    # Prix dans IB?
    in_ib = False
    ib_size_ticks = 0
    if ibh > 0 and ibl > 0:
        in_ib = ibl <= mid <= ibh
        ib_size_ticks = (ibh - ibl) / tick_size
        if in_ib:
            range_score += 2
            criteria_met.append(f"IN_IB({ib_size_ticks:.0f}t)")

    # Prix dans VA?
    in_va = False
    va_size_ticks = 0
    if vah > 0 and val > 0:
        in_va = val <= mid <= vah
        va_size_ticks = (vah - val) / tick_size
        if in_va:
            range_score += 2
            criteria_met.append(f"IN_VA({va_size_ticks:.0f}t)")

    # Volatilite basse?
    if vol_regime <= 1.5:
        range_score += 2
        criteria_met.append(f"LOW_VOL({vol_regime:.1f})")

    # Score bullish neutre?
    if abs(bullish_score) < 0.25:
        range_score += 2
        criteria_met.append(f"NEUTRAL({bullish_score:.2f})")

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
        criteria_met.append(f"CLOSE_VWAP({d_vwap_ticks:.0f}t)")

    # ═══════════════════════════════════════════════════════════
    # SELECTION DES BORNES (priorite: IB > VA > VWAP)
    # ═══════════════════════════════════════════════════════════

    is_range_candidate = range_score >= 6

    if is_range_candidate:
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
            range_type = "NONE"
            range_high = range_low = 0
    else:
        range_type = "NONE"
        range_high = range_low = 0

    range_size_ticks = (range_high - range_low) / tick_size if range_high > range_low else 0
    range_size_points = range_size_ticks * tick_size

    # ═══════════════════════════════════════════════════════════
    # FILTRE TAILLE - NOUVEAU V4!
    # ═══════════════════════════════════════════════════════════

    min_ticks = config['min_range_ticks']
    max_ticks = config['max_range_ticks']
    ideal_min, ideal_max = config['ideal_range_ticks']

    if range_size_ticks < min_ticks:
        range_quality = "TOO_SMALL"
        is_range = False
        reason = f"Range trop petit: {range_size_ticks:.0f}t < {min_ticks}t minimum"
    elif range_size_ticks > max_ticks:
        range_quality = "TOO_LARGE"
        is_range = False
        reason = f"Range trop large: {range_size_ticks:.0f}t > {max_ticks}t (tendance?)"
    elif ideal_min <= range_size_ticks <= ideal_max:
        range_quality = "IDEAL"
        is_range = is_range_candidate
        reason = f"Range ideal: {range_size_ticks:.0f}t"
    else:
        range_quality = "ACCEPTABLE"
        is_range = is_range_candidate
        reason = f"Range acceptable: {range_size_ticks:.0f}t"

    # ═══════════════════════════════════════════════════════════
    # POSITION DANS LE RANGE
    # ═══════════════════════════════════════════════════════════

    if is_range and range_high > range_low:
        position_pct = ((mid - range_low) / (range_high - range_low)) * 100
        position_pct = max(0, min(100, position_pct))
        distance_to_low_ticks = (mid - range_low) / tick_size
        distance_to_high_ticks = (range_high - mid) / tick_size
    else:
        position_pct = 50
        distance_to_low_ticks = 999
        distance_to_high_ticks = 999

    # Zones
    bottom_pct = config['bottom_zone_pct']
    top_pct = config['top_zone_pct']

    if position_pct < bottom_pct:
        zone = "BOTTOM"
    elif position_pct > top_pct:
        zone = "TOP"
    else:
        zone = "MIDDLE"

    # ═══════════════════════════════════════════════════════════
    # DETECTION BREAKOUT
    # ═══════════════════════════════════════════════════════════

    breakout_risk = "NONE"
    proximity_ticks = config['breakout_proximity_ticks']
    momentum_threshold = config['breakout_momentum_threshold']

    if is_range:
        # Proche du bas + bearish = breakout down
        if distance_to_low_ticks < proximity_ticks and bullish_score < -momentum_threshold:
            breakout_risk = "BEARISH"
            criteria_met.append("BREAKOUT_DOWN")

        # Proche du haut + bullish = breakout up
        elif distance_to_high_ticks < proximity_ticks and bullish_score > momentum_threshold:
            breakout_risk = "BULLISH"
            criteria_met.append("BREAKOUT_UP")

    # ═══════════════════════════════════════════════════════════
    # ACTION RECOMMANDEE
    # ═══════════════════════════════════════════════════════════

    if not is_range:
        if range_quality == "TOO_SMALL":
            action = "SKIP_TOO_SMALL"
        elif range_quality == "TOO_LARGE":
            action = "FOLLOW_TREND"
        else:
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

    return RangeAnalysisV4(
        symbol=symbol,
        is_range=is_range,
        range_type=range_type,
        range_quality=range_quality,
        range_high=range_high,
        range_low=range_low,
        range_size_ticks=range_size_ticks,
        range_size_points=range_size_points,
        position_pct=position_pct,
        zone=zone,
        distance_to_low_ticks=distance_to_low_ticks,
        distance_to_high_ticks=distance_to_high_ticks,
        breakout_risk=breakout_risk,
        criteria_met=criteria_met,
        confidence=range_score / 12.0,
        recommended_action=action,
        reason=reason
    )

def should_block_trade_v4(signal: str, analysis: RangeAnalysisV4) -> Tuple[bool, str]:
    """
    Decide si le trade doit etre bloque

    Returns: (should_block, reason)
    """

    if not analysis.is_range:
        if analysis.range_quality == "TOO_SMALL":
            return False, f"Micro-range ignore ({analysis.range_size_ticks:.0f}t)"
        return False, "TENDANCE - Signal autorise"

    # Breakout risk
    if analysis.breakout_risk == "BEARISH":
        return True, f"BREAKOUT DOWN - {analysis.distance_to_low_ticks:.0f}t du bas"

    if analysis.breakout_risk == "BULLISH":
        return True, f"BREAKOUT UP - {analysis.distance_to_high_ticks:.0f}t du haut"

    # Zones
    if analysis.zone == "BOTTOM":
        if signal == "SHORT":
            return True, f"RANGE {analysis.range_size_ticks:.0f}t: SHORT interdit au bas ({analysis.position_pct:.0f}%)"
        return False, f"RANGE: LONG OK en bas - FADE vers {analysis.range_high:.2f}"

    elif analysis.zone == "TOP":
        if signal == "LONG":
            return True, f"RANGE {analysis.range_size_ticks:.0f}t: LONG interdit en haut ({analysis.position_pct:.0f}%)"
        return False, f"RANGE: SHORT OK en haut - FADE vers {analysis.range_low:.2f}"

    else:  # MIDDLE
        return True, f"RANGE {analysis.range_size_ticks:.0f}t: Milieu - pas de trade ({analysis.position_pct:.0f}%)"

# ===============================================================
# TESTS
# ===============================================================

def test_es_power_hour():
    """Test ES Power Hour"""

    print("\n" + "="*70)
    print("TEST ES - POWER HOUR 08/12/2025")
    print("="*70)

    trades = [
        {'time': '20:38', 'dir': 'LONG', 'entry': 6841.00, 'pnl': -256.50, 'bullish': -0.15},
        {'time': '21:16', 'dir': 'LONG', 'entry': 6840.75, 'pnl': -256.50, 'bullish': -0.20},
    ]

    context = {
        'atr': 2.39, 'volatility_regime': 1.0,
        'structure': {'ibh': 6850.00, 'ibl': 6840.00},
        'vva': {'vah': 6852.00, 'val': 6842.00},
        'vwap_up1': 6848.00, 'vwap_dn1': 6843.00, 'd_vwap_ticks': 5.0,
    }

    total_saved = 0
    blocked = 0

    for t in trades:
        snap = context.copy()
        snap['mid'] = t['entry']
        snap['mia_bullish_score'] = t['bullish']

        analysis = analyze_range_v4(snap, 'ES')
        block, reason = should_block_trade_v4(t['dir'], analysis)

        print(f"\n[{t['time']}] {t['dir']} @ {t['entry']:.2f}")
        print(f"   Range: {analysis.range_size_ticks:.0f}t ({analysis.range_quality})")
        print(f"   Position: {analysis.position_pct:.0f}% | Zone: {analysis.zone}")
        print(f"   Breakout: {analysis.breakout_risk}")
        print(f"   PnL reel: ${t['pnl']:+.2f}")

        if block:
            print(f"   => BLOQUE: {reason}")
            total_saved += abs(t['pnl'])
            blocked += 1
        else:
            print(f"   => AUTORISE: {reason}")

    print(f"\n{'─'*70}")
    print(f"ES: {blocked}/2 bloques | Economie: +${total_saved:.2f}")

    return blocked, total_saved

def test_nq_scenarios():
    """Test NQ avec differents scenarios"""

    print("\n" + "="*70)
    print("TEST NQ - SCENARIOS")
    print("="*70)

    scenarios = [
        # Range trop petit pour NQ (< 20 ticks)
        {
            'name': 'NQ - Range trop petit (15t)',
            'snapshot': {
                'mid': 21205.00, 'atr': 8.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.0,
                'structure': {'ibh': 21210.00, 'ibl': 21206.25},  # 15 ticks
                'vva': {'vah': 21212.00, 'val': 21205.00},
                'vwap_up1': 21208.00, 'vwap_dn1': 21203.00, 'd_vwap_ticks': 3.0
            },
            'signal': 'LONG',
            'expect_block': False,
            'expect_reason': 'petit'
        },
        # Range ideal NQ (40 ticks)
        {
            'name': 'NQ - Range ideal (40t) - Milieu',
            'snapshot': {
                'mid': 21225.00, 'atr': 8.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.05,
                'structure': {'ibh': 21230.00, 'ibl': 21220.00},  # 40 ticks
                'vva': {'vah': 21232.00, 'val': 21218.00},
                'vwap_up1': 21228.00, 'vwap_dn1': 21222.00, 'd_vwap_ticks': 2.0
            },
            'signal': 'LONG',
            'expect_block': True,
            'expect_reason': 'Milieu'
        },
        # Range NQ - Bas (FADE OK)
        {
            'name': 'NQ - Range 40t - Bas (LONG OK)',
            'snapshot': {
                'mid': 21221.00, 'atr': 8.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.05,
                'structure': {'ibh': 21230.00, 'ibl': 21220.00},  # 40 ticks
                'vva': {'vah': 21232.00, 'val': 21218.00},
                'vwap_up1': 21228.00, 'vwap_dn1': 21222.00, 'd_vwap_ticks': 5.0
            },
            'signal': 'LONG',
            'expect_block': False,
            'expect_reason': 'FADE'
        },
        # Range NQ - Breakout down
        {
            'name': 'NQ - Breakout DOWN',
            'snapshot': {
                'mid': 21221.50, 'atr': 8.0, 'volatility_regime': 1.0, 'mia_bullish_score': -0.20,
                'structure': {'ibh': 21230.00, 'ibl': 21220.00},
                'vva': {'vah': 21232.00, 'val': 21218.00},
                'vwap_up1': 21228.00, 'vwap_dn1': 21222.00, 'd_vwap_ticks': 5.0
            },
            'signal': 'LONG',
            'expect_block': True,
            'expect_reason': 'BREAKOUT'
        },
    ]

    passed = 0

    for s in scenarios:
        analysis = analyze_range_v4(s['snapshot'], 'NQ')
        block, reason = should_block_trade_v4(s['signal'], analysis)

        match = (block == s['expect_block']) and (s['expect_reason'].upper() in reason.upper())
        status = "[PASS]" if match else "[FAIL]"
        passed += 1 if match else 0

        print(f"\n{status} {s['name']}:")
        print(f"   Range: {analysis.range_size_ticks:.0f}t ({analysis.range_quality})")
        print(f"   Zone: {analysis.zone} | Breakout: {analysis.breakout_risk}")
        print(f"   Attendu: block={s['expect_block']} | Obtenu: block={block}")
        print(f"   Raison: {reason}")

    print(f"\n{'─'*70}")
    print(f"NQ: {passed}/{len(scenarios)} tests passes")

    return passed, len(scenarios)

def test_size_filters():
    """Test des filtres de taille"""

    print("\n" + "="*70)
    print("TEST FILTRES TAILLE")
    print("="*70)

    tests = [
        # ES
        ('ES', 10, 'TOO_SMALL'),
        ('ES', 15, 'ACCEPTABLE'),
        ('ES', 25, 'IDEAL'),
        ('ES', 50, 'ACCEPTABLE'),
        ('ES', 65, 'TOO_LARGE'),

        # NQ
        ('NQ', 15, 'TOO_SMALL'),
        ('NQ', 25, 'ACCEPTABLE'),
        ('NQ', 40, 'IDEAL'),
        ('NQ', 70, 'ACCEPTABLE'),
        ('NQ', 85, 'TOO_LARGE'),
    ]

    passed = 0

    for symbol, size_ticks, expected_quality in tests:
        config = INSTRUMENT_CONFIG[symbol]
        tick_size = config['tick_size']

        # Creer un range de la taille voulue
        range_low = 6000 if symbol == 'ES' else 21000
        range_high = range_low + (size_ticks * tick_size)
        mid = (range_low + range_high) / 2

        snapshot = {
            'mid': mid, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.0,
            'structure': {'ibh': range_high, 'ibl': range_low},
            'vva': {'vah': range_high + 1, 'val': range_low - 1},
            'vwap_up1': range_high - 1, 'vwap_dn1': range_low + 1, 'd_vwap_ticks': 2.0
        }

        analysis = analyze_range_v4(snapshot, symbol)

        match = analysis.range_quality == expected_quality
        status = "[PASS]" if match else "[FAIL]"
        passed += 1 if match else 0

        print(f"{status} {symbol} {size_ticks}t -> {analysis.range_quality} (attendu: {expected_quality})")

    print(f"\n{'─'*70}")
    print(f"Filtres: {passed}/{len(tests)} tests passes")

    return passed, len(tests)

# ===============================================================
# MAIN
# ===============================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("RANGE FILTER V4 FINAL - ES + NQ")
    print("="*70)

    # Afficher configuration
    print("\nCONFIGURATION:")
    for sym, cfg in INSTRUMENT_CONFIG.items():
        print(f"\n{sym}:")
        print(f"   Range: {cfg['min_range_ticks']}-{cfg['max_range_ticks']} ticks")
        print(f"   Ideal: {cfg['ideal_range_ticks'][0]}-{cfg['ideal_range_ticks'][1]} ticks")
        print(f"   Breakout proximity: {cfg['breakout_proximity_ticks']} ticks")

    # Tests
    es_blocked, es_saved = test_es_power_hour()
    nq_passed, nq_total = test_nq_scenarios()
    size_passed, size_total = test_size_filters()

    # Verdict
    print("\n" + "="*70)
    print("VERDICT FINAL V4")
    print("="*70)

    total_tests = 2 + nq_total + size_total
    total_passed = es_blocked + nq_passed + size_passed

    all_good = (es_blocked >= 1) and (nq_passed >= nq_total - 1) and (size_passed >= size_total - 1)

    print(f"""
   ES POWER HOUR:
   - Trades bloques: {es_blocked}/2
   - Economie: +${es_saved:.2f}

   NQ SCENARIOS:
   - Tests passes: {nq_passed}/{nq_total}

   FILTRES TAILLE:
   - Tests passes: {size_passed}/{size_total}

   ════════════════════════════════════
   TOTAL: {total_passed}/{total_tests} reussis

   VERDICT: {"PRET POUR IMPLEMENTATION" if all_good else "CORRECTIONS NECESSAIRES"}
   ════════════════════════════════════
    """)

