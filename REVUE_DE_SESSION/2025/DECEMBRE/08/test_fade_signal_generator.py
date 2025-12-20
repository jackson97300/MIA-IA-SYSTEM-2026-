#!/usr/bin/env python3
"""
Test du generateur de signaux FADE sur ranges "purs"
08-09 Dec 2025

V2: Test du filtre BIAS + TP au milieu
"""

import sys
sys.path.insert(0, 'D:/MIA_IA_system')

from features.market_regime import MarketRegimeDetector, MarketRegime, MarketData
import pandas as pd

def test_fade_signal_generation():
    """Test la generation de signaux FADE avec BIAS filter et TP milieu"""

    print("=" * 60)
    print("TEST GENERATEUR SIGNAUX FADE V2")
    print("Modifications 09/12:")
    print("  - TP au MILIEU du range (aimant)")
    print("  - Filtre BIAS (seulement dans le sens du bias)")
    print("  - Trailing desactive pour RANGE_FADE")
    print("=" * 60)

    # Creer detecteur
    detector = MarketRegimeDetector(config={
        'min_range_size_ticks': 15,
        'max_range_size_ticks': 60,
        'min_range_duration': 10,
        'min_level_tests': 3,
    })

    # Simuler un range 6855-6865 (40 ticks - dans la limite) pour ES
    print("\n1) SIMULATION RANGE ES: 6855-6865 (40 ticks)")
    print("-" * 40)

    support = 6855.0
    resistance = 6865.0

    # Simuler 40 barres avec oscillation dans le range
    # Pour avoir des tests valides sur support et resistance
    for i in range(40):
        # Alterner entre support, milieu et resistance
        phase = i % 8
        if phase < 2:  # Test support
            price = support + 0.25
            high = support + 1.0
            low = support - 0.5  # Touche le support
        elif phase < 4:  # Montee
            price = (support + resistance) / 2
            high = price + 1.0
            low = price - 1.0
        elif phase < 6:  # Test resistance
            price = resistance - 0.25
            high = resistance + 0.5  # Touche la resistance
            low = resistance - 1.0
        else:  # Descente
            price = (support + resistance) / 2
            high = price + 1.0
            low = price - 1.0

        market_data = MarketData(
            timestamp=pd.Timestamp.now() + pd.Timedelta(minutes=i),
            symbol="ES",
            open=price,
            high=high,
            low=low,
            close=price,
            volume=1000
        )
        regime = detector.analyze_market_regime(market_data)

    print(f"Regime detecte: {regime.regime.value}")
    print(f"Range detecte: {regime.range_analysis.range_detected if regime.range_analysis else 'NON'}")

    if regime.range_analysis and regime.range_analysis.range_detected:
        print(f"Support: {regime.range_analysis.support_level:.2f}")
        print(f"Resistance: {regime.range_analysis.resistance_level:.2f}")
        print(f"Zone: {regime.range_analysis.range_zone}")
        print(f"Position: {regime.range_analysis.position_in_range_pct:.1f}%")

    # Test signal FADE au bas du range (zone BOTTOM)
    print("\n2) TEST SIGNAL FADE EN ZONE BOTTOM")
    print("-" * 40)

    snapshot_bottom = {
        'mid': 6851.25,  # Proche du support
        'delta': 150,    # Delta positif (acheteurs)
        'cum_delta_session': 500,
        'bidvol': 1000,
        'askvol': 1800,  # Plus d'achats
        'level1_imbalance': 0.3,  # Imbalance acheteur
        'institutional_pressure': 0.1,  # Pression acheteuse
    }

    fade_signal = detector.generate_fade_signal(snapshot_bottom, "ES")

    if fade_signal:
        print("SIGNAL FADE GENERE!")
        print(f"  Action: {fade_signal['action']}")
        print(f"  Entry: {fade_signal['entry_price']:.2f}")
        print(f"  TP: {fade_signal['tp_price']:.2f} (MILIEU: {fade_signal.get('range_midpoint', 'N/A')})")
        print(f"  SL: {fade_signal['sl_price']:.2f}")
        print(f"  Confidence: {fade_signal['confidence']:.2%}")
        print(f"  Confirmations OF: {fade_signal['orderflow_confirmations']}/4")
        print(f"  Bias: {fade_signal.get('underlying_bias', 'N/A')}")
        print(f"  Disable Trailing: {fade_signal.get('disable_trailing', False)}")
        print(f"  Raison: {fade_signal['reason']}")
    else:
        print("Pas de signal genere (peut-etre pas en zone extremes)")

    # Test signal FADE en haut du range (zone TOP)
    print("\n3) TEST SIGNAL FADE EN ZONE TOP")
    print("-" * 40)

    # Bouger le prix vers le haut
    for i in range(5):
        market_data = MarketData(
            timestamp=pd.Timestamp.now() + pd.Timedelta(minutes=30+i),
            symbol="ES",
            open=resistance - 1,
            high=resistance,
            low=resistance - 2,
            close=resistance - 0.5,
            volume=1000
        )
        detector.analyze_market_regime(market_data)

    snapshot_top = {
        'mid': 6868.75,  # Proche de la resistance
        'delta': -200,   # Delta negatif (vendeurs)
        'cum_delta_session': -300,
        'bidvol': 1800,  # Plus de ventes
        'askvol': 1000,
        'level1_imbalance': -0.4,  # Imbalance vendeur
        'institutional_pressure': -0.15,  # Pression vendeuse
    }

    fade_signal = detector.generate_fade_signal(snapshot_top, "ES")

    if fade_signal:
        print("SIGNAL FADE GENERE!")
        print(f"  Action: {fade_signal['action']}")
        print(f"  Entry: {fade_signal['entry_price']:.2f}")
        print(f"  TP: {fade_signal['tp_price']:.2f} (MILIEU: {fade_signal.get('range_midpoint', 'N/A')})")
        print(f"  SL: {fade_signal['sl_price']:.2f}")
        print(f"  Confidence: {fade_signal['confidence']:.2%}")
        print(f"  Confirmations OF: {fade_signal['orderflow_confirmations']}/4")
        print(f"  Bias: {fade_signal.get('underlying_bias', 'N/A')}")
        print(f"  Disable Trailing: {fade_signal.get('disable_trailing', False)}")
        print(f"  Raison: {fade_signal['reason']}")
    else:
        print("Pas de signal genere")

    # Test PAS de signal au MILIEU
    print("\n4) TEST PAS DE SIGNAL EN ZONE MIDDLE")
    print("-" * 40)

    # Bouger vers le milieu
    for i in range(5):
        market_data = MarketData(
            timestamp=pd.Timestamp.now() + pd.Timedelta(minutes=40+i),
            symbol="ES",
            open=6860,
            high=6861,
            low=6859,
            close=6860,
            volume=1000
        )
        detector.analyze_market_regime(market_data)

    snapshot_middle = {
        'mid': 6860.0,  # Milieu du range
        'delta': 100,
        'cum_delta_session': 200,
        'bidvol': 1200,
        'askvol': 1400,
        'level1_imbalance': 0.1,
        'institutional_pressure': 0.05,
    }

    fade_signal = detector.generate_fade_signal(snapshot_middle, "ES")

    if fade_signal:
        print("SIGNAL GENERE (INATTENDU AU MILIEU!)")
        print(f"  Action: {fade_signal['action']}")
    else:
        print("Pas de signal genere (CORRECT - milieu du range)")

    # Test sans confirmations OrderFlow
    print("\n5) TEST SANS CONFIRMATIONS ORDERFLOW")
    print("-" * 40)

    # Retour en bas
    for i in range(5):
        market_data = MarketData(
            timestamp=pd.Timestamp.now() + pd.Timedelta(minutes=50+i),
            symbol="ES",
            open=support + 1,
            high=support + 2,
            low=support,
            close=support + 0.5,
            volume=1000
        )
        detector.analyze_market_regime(market_data)

    snapshot_no_of = {
        'mid': 6851.0,  # Zone bottom
        'delta': -50,   # Delta NEGATIF (pas de confirmation)
        'cum_delta_session': -100,
        'bidvol': 1500, # Ventes > Achats
        'askvol': 1000,
        'level1_imbalance': -0.2,  # Imbalance vendeur
        'institutional_pressure': -0.1,  # Pression vendeuse
    }

    fade_signal = detector.generate_fade_signal(snapshot_no_of, "ES")

    if fade_signal:
        print("SIGNAL GENERE (INATTENDU SANS CONFIRMATION!)")
        print(f"  Action: {fade_signal['action']}")
    else:
        print("Pas de signal genere (CORRECT - pas de confirmation OF)")

    # Stats
    print("\n" + "=" * 60)
    print("STATS DETECTEUR")
    print("=" * 60)
    stats = detector.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Signaux FADE generes
    fade_count = detector.stats.get('fade_signals_generated', 0)
    print(f"\n  SIGNAUX FADE GENERES: {fade_count}")

    print("\n" + "=" * 60)
    print("TEST TERMINE")
    print("=" * 60)

if __name__ == "__main__":
    test_fade_signal_generation()
