#!/usr/bin/env python3
"""
TEST RANGE FILTER SUR DONNÉES RÉELLES
======================================

Vérifie la solidité du filtre range en testant sur:
1. Les trades réels du 08/12/2025 (Power Hour)
2. Les snapshots disponibles
3. Simulation avec/sans le filtre

Date: 08/12/2025
"""

import os
import json
import glob
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

LOGS_DIR = r"D:\MIA_IA_system\logs"
DATA_DIR = r"D:\MIA_IA_system\DATA_SIERRA_CHART"
SNAPSHOTS_TRADES_DIR = r"D:\MIA_IA_system\snapshots_trades\daily"

TICK_VALUES = {'ES': 12.50, 'NQ': 5.00}
TICK_SIZES = {'ES': 0.25, 'NQ': 0.25}

# ═══════════════════════════════════════════════════════════════════════════════
# RANGE DETECTION (VERSION COMBINÉE)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RangeAnalysis:
    """Résultat de l'analyse de range"""
    is_range: bool
    range_type: str  # 'IB', 'VA', 'VWAP_BANDS', 'NONE'
    range_high: float
    range_low: float
    range_size_ticks: float
    position_pct: float  # 0-100
    zone: str  # 'BOTTOM', 'MIDDLE', 'TOP'
    criteria_met: List[str]
    confidence: float
    recommended_action: str  # 'LONG_FADE', 'SHORT_FADE', 'NO_TRADE', 'FOLLOW_TREND'

def analyze_range_from_snapshot(snapshot: dict, tick_size: float = 0.25) -> RangeAnalysis:
    """
    Analyse si on est en range à partir des données du snapshot

    Utilise:
    - Initial Balance (IBH/IBL)
    - Value Area (VAH/VAL)
    - VWAP Bands (vwap_up1/vwap_dn1)
    - Volatility regime
    - mia_bullish_score
    """

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

    # ═══════════════════════════════════════════════════════════════
    # CRITÈRES DE RANGE
    # ═══════════════════════════════════════════════════════════════

    criteria_met = []
    range_score = 0

    # 1. Prix dans IB?
    in_ib = False
    ib_size_ticks = 0
    if ibh > 0 and ibl > 0:
        in_ib = ibl <= mid <= ibh
        ib_size_ticks = (ibh - ibl) / tick_size
        if in_ib:
            range_score += 2
            criteria_met.append(f"IN_IB({ib_size_ticks:.0f}t)")

    # 2. Prix dans VA?
    in_va = False
    va_size_ticks = 0
    if vah > 0 and val > 0:
        in_va = val <= mid <= vah
        va_size_ticks = (vah - val) / tick_size
        if in_va:
            range_score += 2
            criteria_met.append(f"IN_VA({va_size_ticks:.0f}t)")

    # 3. Volatilité basse?
    if vol_regime <= 1.5:
        range_score += 2
        criteria_met.append(f"LOW_VOL({vol_regime:.1f})")

    # 4. Score bullish neutre?
    if abs(bullish_score) < 0.25:
        range_score += 2
        criteria_met.append(f"NEUTRAL({bullish_score:.2f})")

    # 5. VWAP plat (bandes serrées)?
    if vwap_up1 > 0 and vwap_dn1 > 0 and atr > 0:
        vwap_band_width = vwap_up1 - vwap_dn1
        if (vwap_band_width / atr) < 2.5:
            range_score += 2
            criteria_met.append(f"VWAP_FLAT({vwap_band_width/atr:.1f}x)")

        # Prix dans les bandes SD±1?
        if vwap_dn1 <= mid <= vwap_up1:
            range_score += 1
            criteria_met.append("IN_VWAP_BANDS")

    # 6. Prix proche du VWAP?
    if d_vwap_ticks < 15:
        range_score += 1
        criteria_met.append(f"CLOSE_VWAP({d_vwap_ticks:.0f}t)")

    # ═══════════════════════════════════════════════════════════════
    # DÉCISION RANGE
    # ═══════════════════════════════════════════════════════════════

    is_range = range_score >= 6  # Au moins 6 points sur 12

    # Déterminer les bornes du range
    if is_range:
        # Priorité: VA > IB > VWAP Bands
        if in_va and va_size_ticks >= 12:
            range_type = "VA"
            range_high = vah
            range_low = val
            range_size = va_size_ticks
        elif in_ib and ib_size_ticks >= 12:
            range_type = "IB"
            range_high = ibh
            range_low = ibl
            range_size = ib_size_ticks
        elif vwap_up1 > 0 and vwap_dn1 > 0:
            range_type = "VWAP_BANDS"
            range_high = vwap_up1
            range_low = vwap_dn1
            range_size = (vwap_up1 - vwap_dn1) / tick_size
        else:
            is_range = False
            range_type = "NONE"
            range_high = range_low = range_size = 0
    else:
        range_type = "NONE"
        range_high = range_low = range_size = 0

    # ═══════════════════════════════════════════════════════════════
    # POSITION DANS LE RANGE
    # ═══════════════════════════════════════════════════════════════

    if is_range and range_high > range_low:
        position_pct = ((mid - range_low) / (range_high - range_low)) * 100
        position_pct = max(0, min(100, position_pct))
    else:
        position_pct = 50

    # Zones avec BUFFER
    BOTTOM_ZONE = 25
    TOP_ZONE = 75

    if position_pct < BOTTOM_ZONE:
        zone = "BOTTOM"
    elif position_pct > TOP_ZONE:
        zone = "TOP"
    else:
        zone = "MIDDLE"

    # ═══════════════════════════════════════════════════════════════
    # RECOMMANDATION
    # ═══════════════════════════════════════════════════════════════

    if not is_range:
        action = "FOLLOW_TREND"
    elif zone == "BOTTOM":
        action = "LONG_FADE"
    elif zone == "TOP":
        action = "SHORT_FADE"
    else:
        action = "NO_TRADE"

    confidence = range_score / 12.0

    return RangeAnalysis(
        is_range=is_range,
        range_type=range_type,
        range_high=range_high,
        range_low=range_low,
        range_size_ticks=range_size,
        position_pct=position_pct,
        zone=zone,
        criteria_met=criteria_met,
        confidence=confidence,
        recommended_action=action
    )

def should_block_trade(signal: str, range_analysis: RangeAnalysis) -> Tuple[bool, str]:
    """
    Détermine si le trade doit être bloqué basé sur l'analyse de range

    Returns: (should_block, reason)
    """

    if not range_analysis.is_range:
        return False, "TREND - Signal autorisé"

    zone = range_analysis.zone

    if zone == "BOTTOM":
        if signal == "SHORT":
            return True, f"RANGE: Pas de SHORT en bas ({range_analysis.position_pct:.0f}%)"
        else:
            return False, f"RANGE: LONG OK en bas - FADE vers {range_analysis.range_high:.2f}"

    elif zone == "TOP":
        if signal == "LONG":
            return True, f"RANGE: Pas de LONG en haut ({range_analysis.position_pct:.0f}%)"
        else:
            return False, f"RANGE: SHORT OK en haut - FADE vers {range_analysis.range_low:.2f}"

    else:  # MIDDLE
        return True, f"RANGE: Pas de trade au MILIEU ({range_analysis.position_pct:.0f}%)"

# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTION DONNÉES RÉELLES
# ═══════════════════════════════════════════════════════════════════════════════

def extract_trades_with_snapshots() -> List[Dict]:
    """Extrait les trades avec leurs snapshots associés"""

    trades = []

    # Chercher les fichiers de résultat
    result_files = glob.glob(os.path.join(SNAPSHOTS_TRADES_DIR, "TRADE_20251208*_final_result.json"))

    for filepath in result_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            result = data.get('result', {})
            entry = data.get('entry', {})
            ml_scores = data.get('ml_scores', {})

            # Extraire l'heure du filename
            filename = os.path.basename(filepath)
            time_match = re.search(r'TRADE_\d{8}_(\d{6})', filename)
            entry_time = time_match.group(1) if time_match else "000000"

            trades.append({
                'time': entry_time,
                'symbol': entry.get('symbol', 'ES'),
                'direction': entry.get('direction', 'LONG'),
                'pnl': result.get('pnl', 0),
                'exit_reason': result.get('exit_reason', 'unknown'),
                'ml_scores': ml_scores,
                'entry_context': entry
            })

        except Exception as e:
            pass

    return sorted(trades, key=lambda x: x['time'])

def get_snapshot_for_time(symbol: str, time_str: str) -> Optional[Dict]:
    """Récupère un snapshot proche d'un moment donné"""

    # Chercher dans les snapshots disponibles
    # Note: Les snapshots sont générés en temps réel, on utilise les données du trade

    return None  # Pour l'instant, on n'a pas accès aux snapshots historiques

# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION SUR DONNÉES POWER HOUR
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_power_hour_trades():
    """
    Simule le filtre range sur les trades du Power Hour
    Utilise les données réelles du graphique montré
    """

    print("\n" + "="*80)
    print("SIMULATION FILTRE RANGE - POWER HOUR 08/12/2025")
    print("="*80)

    # Données du Power Hour basées sur le graphique
    # Range observé: ~6840 - 6850 (40 ticks)
    power_hour_context = {
        'mid': 6845.00,
        'atr': 2.39,
        'volatility_regime': 1.0,
        'mia_bullish_score': -0.11,
        'structure': {
            'ibh': 6850.00,
            'ibl': 6840.00,
        },
        'vva': {
            'vah': 6852.00,
            'val': 6842.00,
            'vpoc': 6845.00
        },
        'vwap_up1': 6848.00,
        'vwap_dn1': 6843.00,
        'd_vwap_ticks': 5.0,
    }

    # Trades réels perdants du Power Hour
    power_hour_trades = [
        {'time': '203808', 'direction': 'LONG', 'entry': 6841.00, 'pnl': -256.50, 'actual': 'SL Hit'},
        {'time': '211628', 'direction': 'LONG', 'entry': 6840.75, 'pnl': -256.50, 'actual': 'SL Hit'},
    ]

    print(f"\n📊 CONTEXTE POWER HOUR:")
    print(f"   Range observé: {power_hour_context['structure']['ibl']:.2f} - {power_hour_context['structure']['ibh']:.2f}")
    print(f"   Volatilité: {power_hour_context['volatility_regime']}")
    print(f"   Score bullish: {power_hour_context['mia_bullish_score']:.2f}")

    # Analyser le contexte
    range_analysis = analyze_range_from_snapshot(power_hour_context)

    print(f"\n📈 ANALYSE RANGE:")
    print(f"   Est un range: {range_analysis.is_range}")
    print(f"   Type: {range_analysis.range_type}")
    print(f"   Bornes: {range_analysis.range_low:.2f} - {range_analysis.range_high:.2f}")
    print(f"   Taille: {range_analysis.range_size_ticks:.0f} ticks")
    print(f"   Critères: {', '.join(range_analysis.criteria_met)}")
    print(f"   Confidence: {range_analysis.confidence:.0%}")

    # Simuler chaque trade
    print(f"\n{'─'*80}")
    print(f"SIMULATION DES TRADES:")
    print(f"{'─'*80}")

    total_saved = 0
    trades_blocked = 0

    for trade in power_hour_trades:
        # Créer un snapshot avec le prix d'entrée
        trade_snapshot = power_hour_context.copy()
        trade_snapshot['mid'] = trade['entry']

        # Analyser
        trade_range = analyze_range_from_snapshot(trade_snapshot)
        should_block, reason = should_block_trade(trade['direction'], trade_range)

        print(f"\n   Trade @ {trade['time']}:")
        print(f"   ├─ Direction: {trade['direction']}")
        print(f"   ├─ Entry: {trade['entry']:.2f}")
        print(f"   ├─ Position dans range: {trade_range.position_pct:.0f}% ({trade_range.zone})")
        print(f"   ├─ Résultat réel: {trade['actual']} (${trade['pnl']:+.2f})")

        if should_block:
            print(f"   ├─ FILTRE: ❌ BLOQUÉ - {reason}")
            print(f"   └─ ÉCONOMIE: +${abs(trade['pnl']):.2f}")
            total_saved += abs(trade['pnl'])
            trades_blocked += 1
        else:
            print(f"   └─ FILTRE: ✅ AUTORISÉ - {reason}")

    print(f"\n{'='*80}")
    print(f"RÉSUMÉ SIMULATION:")
    print(f"{'='*80}")
    print(f"   Trades analysés: {len(power_hour_trades)}")
    print(f"   Trades bloqués: {trades_blocked}")
    print(f"   ÉCONOMIE TOTALE: +${total_saved:.2f}")

    return total_saved, trades_blocked

# ═══════════════════════════════════════════════════════════════════════════════
# TEST ROBUSTESSE SUR DIFFÉRENTS SCÉNARIOS
# ═══════════════════════════════════════════════════════════════════════════════

def test_robustness():
    """Teste la robustesse du filtre sur différents scénarios"""

    print("\n" + "="*80)
    print("TEST DE ROBUSTESSE - DIFFÉRENTS SCÉNARIOS")
    print("="*80)

    test_cases = [
        # Scénarios RANGE (doivent être détectés)
        {
            'name': 'Range serré (20t)',
            'snapshot': {
                'mid': 6845.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.05,
                'structure': {'ibh': 6850.00, 'ibl': 6845.00},
                'vva': {'vah': 6852.00, 'val': 6843.00},
                'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': 3.0
            },
            'signal': 'LONG',
            'entry_price': 6845.00,
            'expected_block': True,
            'expected_reason': 'MIDDLE'
        },
        {
            'name': 'Range - Bas (LONG OK)',
            'snapshot': {
                'mid': 6841.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': -0.1,
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': 8.0
            },
            'signal': 'LONG',
            'entry_price': 6841.00,
            'expected_block': False,
            'expected_reason': 'BOTTOM'
        },
        {
            'name': 'Range - Bas (SHORT bloqué)',
            'snapshot': {
                'mid': 6841.00, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': -0.1,
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': 8.0
            },
            'signal': 'SHORT',
            'entry_price': 6841.00,
            'expected_block': True,
            'expected_reason': 'BOTTOM'
        },
        {
            'name': 'Range - Haut (SHORT OK)',
            'snapshot': {
                'mid': 6849.50, 'atr': 2.0, 'volatility_regime': 1.0, 'mia_bullish_score': 0.1,
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6848.00, 'vwap_dn1': 6842.00, 'd_vwap_ticks': -3.0
            },
            'signal': 'SHORT',
            'entry_price': 6849.50,
            'expected_block': False,
            'expected_reason': 'TOP'
        },
        # Scénarios TREND (ne doivent PAS être bloqués)
        {
            'name': 'Tendance haussière forte',
            'snapshot': {
                'mid': 6880.00, 'atr': 4.0, 'volatility_regime': 2.5, 'mia_bullish_score': 0.6,
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6870.00, 'vwap_dn1': 6850.00, 'd_vwap_ticks': -40.0
            },
            'signal': 'LONG',
            'entry_price': 6880.00,
            'expected_block': False,
            'expected_reason': 'TREND'
        },
        {
            'name': 'Tendance baissière forte',
            'snapshot': {
                'mid': 6800.00, 'atr': 4.0, 'volatility_regime': 2.5, 'mia_bullish_score': -0.6,
                'structure': {'ibh': 6850.00, 'ibl': 6840.00},
                'vva': {'vah': 6852.00, 'val': 6842.00},
                'vwap_up1': 6830.00, 'vwap_dn1': 6810.00, 'd_vwap_ticks': 50.0
            },
            'signal': 'SHORT',
            'entry_price': 6800.00,
            'expected_block': False,
            'expected_reason': 'TREND'
        },
    ]

    passed = 0
    failed = 0

    for tc in test_cases:
        snapshot = tc['snapshot']
        snapshot['mid'] = tc['entry_price']

        range_analysis = analyze_range_from_snapshot(snapshot)
        should_block, reason = should_block_trade(tc['signal'], range_analysis)

        # Vérifier
        if should_block == tc['expected_block']:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"\n{status} {tc['name']}:")
        print(f"   Signal: {tc['signal']} @ {tc['entry_price']:.2f}")
        print(f"   Range: {range_analysis.is_range} | Zone: {range_analysis.zone}")
        print(f"   Attendu: block={tc['expected_block']} | Obtenu: block={should_block}")
        print(f"   Raison: {reason}")

    print(f"\n{'='*80}")
    print(f"RÉSULTAT: {passed}/{len(test_cases)} tests passés")
    print(f"{'='*80}")

    return passed, len(test_cases)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*80)
    print("TEST FILTRE RANGE SUR DONNÉES RÉELLES")
    print("="*80)

    # Test 1: Simulation Power Hour
    saved, blocked = simulate_power_hour_trades()

    # Test 2: Robustesse
    passed, total = test_robustness()

    # Résumé final
    print("\n" + "="*80)
    print("VERDICT FINAL")
    print("="*80)

    print(f"""
    📊 SIMULATION POWER HOUR:
    └─ Économie potentielle: +${saved:.2f}
    └─ Trades bloqués: {blocked}

    🧪 TESTS ROBUSTESSE:
    └─ Tests passés: {passed}/{total}
    └─ Taux réussite: {passed/total*100:.0f}%

    ✅ VERDICT:
    └─ Le filtre est SOLIDE si tous les tests passent
    └─ Prêt pour implémentation: {"OUI" if passed == total else "NON - Corriger d'abord"}
    """)

    print("="*80)

