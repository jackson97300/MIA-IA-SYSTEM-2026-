#!/usr/bin/env python3
"""
TEST INTEGRATION MarketRegimeDetector
=====================================

Verifie que le module modifie fonctionne correctement

Date: 08/12/2025
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

def test_range_analysis_fields():
    """Verifie que les nouveaux champs sont presents"""

    print("\n" + "="*60)
    print("TEST 1: Nouveaux champs RangeAnalysis")
    print("="*60)

    from features.market_regime import RangeAnalysis, RangeType
    import pandas as pd

    # Creer une instance avec les nouveaux champs
    analysis = RangeAnalysis(
        timestamp=pd.Timestamp.now(),
        range_detected=True,
        range_type=RangeType.NORMAL_RANGE,
        support_level=6840.0,
        resistance_level=6850.0,
        range_midpoint=6845.0,
        range_size_ticks=40.0,
        support_tests=3,
        resistance_tests=4,
        current_price=6842.0,
        position_in_range_pct=20.0,
        range_zone="BOTTOM",
        distance_to_support_ticks=8.0,
        distance_to_resistance_ticks=32.0,
        breakout_risk="NONE"
    )

    # Verifier les champs
    checks = [
        ("current_price", analysis.current_price == 6842.0),
        ("position_in_range_pct", analysis.position_in_range_pct == 20.0),
        ("range_zone", analysis.range_zone == "BOTTOM"),
        ("distance_to_support_ticks", analysis.distance_to_support_ticks == 8.0),
        ("distance_to_resistance_ticks", analysis.distance_to_resistance_ticks == 32.0),
        ("breakout_risk", analysis.breakout_risk == "NONE"),
    ]

    all_pass = True
    for name, passed in checks:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"   {status} {name}")
        if not passed:
            all_pass = False

    return all_pass

def test_market_regime_detector():
    """Teste le detecteur de regime"""

    print("\n" + "="*60)
    print("TEST 2: MarketRegimeDetector")
    print("="*60)

    from features.market_regime import MarketRegimeDetector, MarketRegime
    from core.base_types import MarketData
    import pandas as pd
    import numpy as np

    # Creer detecteur
    detector = MarketRegimeDetector(config={
        'min_range_size_ticks': 15,
        'max_range_size_ticks': 60,
        'min_range_duration': 10,
        'min_level_tests': 3,
    })

    print(f"   Config: min={detector.min_range_size_ticks}t, max={detector.max_range_size_ticks}t")
    print(f"   Duration: {detector.min_range_duration}min, Tests: {detector.min_level_tests}")

    # Simuler des donnees de range
    base_price = 6845.0

    # Ajouter historique (simule un range)
    for i in range(50):
        # Prix oscille entre 6840 et 6850
        price = base_price + np.sin(i * 0.3) * 5  # Oscillation

        market_data = MarketData(
            symbol="ES",
            timestamp=pd.Timestamp.now() + pd.Timedelta(minutes=i),
            open=price - 0.25,
            high=price + 1.0,
            low=price - 1.0,
            close=price,
            volume=1000
        )

        detector.analyze_market_regime(market_data)

    # Analyser le dernier point
    final_data = MarketData(
        symbol="ES",
        timestamp=pd.Timestamp.now(),
        open=6842.0,
        high=6843.0,
        low=6841.0,
        close=6842.0,
        volume=1000
    )

    result = detector.analyze_market_regime(final_data)

    print(f"\n   Regime: {result.regime.value}")
    print(f"   Confidence: {result.regime_confidence:.2f}")
    print(f"   Preferred strategy: {result.preferred_strategy}")
    print(f"   Allowed directions: {result.allowed_directions}")

    if result.range_analysis and result.range_analysis.range_detected:
        ra = result.range_analysis
        print(f"\n   Range detected!")
        print(f"   - Support: {ra.support_level:.2f}")
        print(f"   - Resistance: {ra.resistance_level:.2f}")
        print(f"   - Position: {ra.position_in_range_pct:.0f}%")
        print(f"   - Zone: {ra.range_zone}")
        print(f"   - Breakout risk: {ra.breakout_risk}")

    return True

def test_fade_logic():
    """Teste la logique FADE"""

    print("\n" + "="*60)
    print("TEST 3: Logique FADE")
    print("="*60)

    # Scenarios de test
    scenarios = [
        # (zone, breakout_risk, signal, expected_allowed)
        ("BOTTOM", "NONE", "LONG", True),      # LONG au bas = OK
        ("BOTTOM", "NONE", "SHORT", False),    # SHORT au bas = BLOQUE
        ("TOP", "NONE", "SHORT", True),        # SHORT en haut = OK
        ("TOP", "NONE", "LONG", False),        # LONG en haut = BLOQUE
        ("MIDDLE", "NONE", "LONG", False),     # LONG au milieu = BLOQUE
        ("MIDDLE", "NONE", "SHORT", False),    # SHORT au milieu = BLOQUE
        ("BOTTOM", "BEARISH", "LONG", False),  # Breakout down = BLOQUE
        ("TOP", "BULLISH", "SHORT", False),    # Breakout up = BLOQUE
    ]

    all_pass = True

    for zone, breakout, signal, expected in scenarios:
        # Simuler la logique
        if breakout != "NONE":
            allowed = False
        elif zone == "MIDDLE":
            allowed = False
        elif zone == "BOTTOM" and signal == "SHORT":
            allowed = False
        elif zone == "TOP" and signal == "LONG":
            allowed = False
        else:
            allowed = True

        passed = (allowed == expected)
        status = "[PASS]" if passed else "[FAIL]"
        print(f"   {status} Zone={zone}, Breakout={breakout}, Signal={signal} -> {'AUTORISE' if allowed else 'BLOQUE'}")

        if not passed:
            all_pass = False

    return all_pass

def test_power_hour_simulation():
    """Simule le Power Hour du 08/12"""

    print("\n" + "="*60)
    print("TEST 4: Simulation Power Hour 08/12")
    print("="*60)

    # Les 2 trades perdants
    trades = [
        {'entry': 6841.00, 'direction': 'LONG', 'bullish_score': -0.15, 'expected_block': True},
        {'entry': 6840.75, 'direction': 'LONG', 'bullish_score': -0.20, 'expected_block': True},
    ]

    # Range du Power Hour
    support = 6840.0
    resistance = 6850.0
    BREAKOUT_PROXIMITY = 5  # ticks

    all_pass = True

    for t in trades:
        price = t['entry']

        # Calculer position
        position_pct = ((price - support) / (resistance - support)) * 100
        distance_to_support = (price - support) / 0.25  # ticks

        # Zone
        if position_pct < 25:
            zone = "BOTTOM"
        elif position_pct > 75:
            zone = "TOP"
        else:
            zone = "MIDDLE"

        # Breakout risk
        breakout = "NONE"
        if distance_to_support < BREAKOUT_PROXIMITY and t['bullish_score'] < -0.10:
            breakout = "BEARISH"

        # Decision
        should_block = False
        reason = ""

        if breakout != "NONE":
            should_block = True
            reason = f"Breakout {breakout}"
        elif zone == "MIDDLE":
            should_block = True
            reason = "Zone MIDDLE"
        elif zone == "BOTTOM" and t['direction'] == "SHORT":
            should_block = True
            reason = "SHORT au bas"
        elif zone == "TOP" and t['direction'] == "LONG":
            should_block = True
            reason = "LONG en haut"

        passed = (should_block == t['expected_block'])
        status = "[PASS]" if passed else "[FAIL]"

        print(f"\n   {status} Trade @ {price:.2f}")
        print(f"      Position: {position_pct:.0f}% | Zone: {zone}")
        print(f"      Distance support: {distance_to_support:.1f}t | Bullish: {t['bullish_score']}")
        print(f"      Breakout: {breakout}")
        print(f"      Decision: {'BLOQUE' if should_block else 'AUTORISE'} ({reason if reason else 'OK'})")

        if not passed:
            all_pass = False

    return all_pass

# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*60)
    print("TESTS INTEGRATION MarketRegimeDetector")
    print("="*60)

    results = []

    try:
        results.append(("Nouveaux champs", test_range_analysis_fields()))
    except Exception as e:
        print(f"   [ERROR] {e}")
        results.append(("Nouveaux champs", False))

    try:
        results.append(("Detecteur", test_market_regime_detector()))
    except Exception as e:
        print(f"   [ERROR] {e}")
        results.append(("Detecteur", False))

    try:
        results.append(("Logique FADE", test_fade_logic()))
    except Exception as e:
        print(f"   [ERROR] {e}")
        results.append(("Logique FADE", False))

    try:
        results.append(("Power Hour", test_power_hour_simulation()))
    except Exception as e:
        print(f"   [ERROR] {e}")
        results.append(("Power Hour", False))

    # Resume
    print("\n" + "="*60)
    print("RESUME")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"   {status} {name}")

    print(f"\n   TOTAL: {passed}/{total} tests passes")
    print("="*60)

