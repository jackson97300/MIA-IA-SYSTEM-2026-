#!/usr/bin/env python3
"""
AUDIT COMPLET: DÉTECTION DE RANGE ET SOLUTION TESTABLE
======================================================

VÉRIFICATION:
1. Qu'est-ce que position_in_range VRAIMENT?
2. Quelles données sont disponibles pour détecter un range?
3. Comment implémenter une détection efficace?
4. Solution testable avec backtest

Date: 08/12/2025
"""

import os
import json
import glob
from typing import Dict, List, Tuple
from dataclasses import dataclass

# ═══════════════════════════════════════════════════════════════════════════════
# PARTIE 1: AUDIT DES DONNÉES DISPONIBLES
# ═══════════════════════════════════════════════════════════════════════════════

def audit_snapshot_data():
    """Analyse un snapshot réel pour voir les données disponibles"""

    print("\n" + "="*80)
    print("PARTIE 1: AUDIT DES DONNÉES DISPONIBLES")
    print("="*80)

    # Chercher un snapshot récent
    data_dir = r"D:\MIA_IA_system\DATA_SIERRA_CHART"

    # Parcourir pour trouver un JSON
    json_files = []
    for root, dirs, files in os.walk(data_dir):
        for f in files:
            if f.endswith('.json'):
                json_files.append(os.path.join(root, f))
        if len(json_files) > 5:
            break

    if not json_files:
        # Utiliser les données du snapshot fourni par l'utilisateur
        print("\n[INFO] Utilisation des données connues du dumper C++")

        # D'après le code C++ du dumper:
        data_available = {
            'position_in_range': {
                'source': 'MIA_Dumper_G3_Unifier.cpp ligne 2770',
                'calcul': '((current_price - day_low) / day_range) * 100.0',
                'unité': '0-100 (pourcentage)',
                'description': 'Position dans le range JOURNALIER (day_high - day_low)',
                'attention': '⚠️ Cest le range JOURNALIER, pas un range de consolidation!'
            },
            'day_range_pct': {
                'source': 'MIA_Dumper_G3_Unifier.cpp ligne 2767',
                'calcul': '(day_range / day_open) * 100.0',
                'unité': 'pourcentage',
                'description': 'Taille du range journalier vs prix ouverture'
            },
            'distance_to_high_pct': {
                'source': 'MIA_Dumper_G3_Unifier.cpp',
                'description': 'Distance au plus haut du jour en %'
            },
            'distance_to_low_pct': {
                'source': 'MIA_Dumper_G3_Unifier.cpp',
                'description': 'Distance au plus bas du jour en %'
            },
            'structure.ibh': {
                'source': 'MIA_Dumper_G3_Unifier.cpp',
                'description': 'Initial Balance High (1ère heure de trading)'
            },
            'structure.ibl': {
                'source': 'MIA_Dumper_G3_Unifier.cpp',
                'description': 'Initial Balance Low (1ère heure de trading)'
            },
            'volatility_regime': {
                'source': 'MIA_Dumper_G3_Unifier.cpp',
                'description': '1.0=basse, 2.0=moyenne, 3.0+=haute volatilité'
            },
            'mia_bullish_score': {
                'source': 'MIA_Dumper_G3_Unifier.cpp',
                'description': 'Score bullish, proche de 0 = neutre/range'
            },
            'atr': {
                'source': 'MIA_Dumper_G3_Unifier.cpp',
                'description': 'Average True Range'
            },
            'vva.vah': {
                'description': 'Value Area High'
            },
            'vva.val': {
                'description': 'Value Area Low'
            },
            'vva.vpoc': {
                'description': 'Volume Point of Control'
            },
            'hvl': {
                'description': 'High Volume Level (niveau magnétique)'
            }
        }

        print("\n📊 DONNÉES DISPONIBLES POUR RANGE DETECTION:")
        print("-"*60)

        for key, info in data_available.items():
            print(f"\n  {key}:")
            for k, v in info.items():
                print(f"    {k}: {v}")

        return data_available

    # Lire un snapshot
    with open(json_files[-1], 'r') as f:
        snapshot = json.load(f)

    print(f"\n[INFO] Snapshot analysé: {json_files[-1]}")

    # Afficher les champs pertinents
    range_fields = [
        'position_in_range', 'day_range_pct',
        'distance_to_high_pct', 'distance_to_low_pct',
        'volatility_regime', 'mia_bullish_score', 'atr',
        'structure', 'vva', 'hvl'
    ]

    print("\n📊 VALEURS ACTUELLES:")
    for field in range_fields:
        if field in snapshot:
            val = snapshot[field]
            if isinstance(val, dict):
                print(f"\n  {field}:")
                for k, v in val.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {field}: {val}")

    return snapshot

# ═══════════════════════════════════════════════════════════════════════════════
# PARTIE 2: PROBLÈME AVEC position_in_range
# ═══════════════════════════════════════════════════════════════════════════════

def explain_position_in_range_problem():
    """Explique pourquoi position_in_range seul ne suffit pas"""

    print("\n" + "="*80)
    print("PARTIE 2: PROBLÈME AVEC position_in_range")
    print("="*80)

    print("""
⚠️ ATTENTION: position_in_range EST LE RANGE JOURNALIER!

Calcul C++:
    position_in_range = ((current_price - day_low) / day_range) * 100.0

PROBLÈME:
    - C'est la position dans le range du JOUR ENTIER
    - PAS dans un range de consolidation court terme

EXEMPLE:
    Jour: High 6900, Low 6800 (range 100 points)
    Prix actuel: 6850
    position_in_range = (6850-6800)/(6900-6800)*100 = 50%

    MAIS: Le marché peut être en consolidation entre 6840-6860
    Dans CE range, le prix à 6850 est au MILIEU (50%)
    Dans le range JOURNALIER, le prix à 6850 est à 50% aussi

    → position_in_range ne détecte PAS un range intraday!

SOLUTION:
    1. Détecter SI on est en range (pas seulement où)
    2. Calculer les bornes du range ACTUEL (pas journalier)
    3. Puis calculer la position dans CE range
    """)

# ═══════════════════════════════════════════════════════════════════════════════
# PARTIE 3: SOLUTION DE DÉTECTION DE RANGE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RangeDetection:
    """Résultat de la détection de range"""
    is_range: bool
    range_type: str  # 'IB_RANGE', 'VA_RANGE', 'TIGHT_RANGE', 'TRENDING'
    range_high: float
    range_low: float
    range_size_ticks: float
    position_in_range_pct: float  # 0-100
    zone: str  # 'BOTTOM', 'MIDDLE', 'TOP'
    recommended_action: str  # 'LONG_FADE', 'SHORT_FADE', 'NO_TRADE', 'FOLLOW_TREND'
    confidence: float  # 0-1


def detect_range_pro(snapshot: dict, tick_size: float = 0.25) -> RangeDetection:
    """
    Détection de range PROFESSIONNELLE

    Utilise plusieurs critères pour déterminer si on est en range:
    1. Initial Balance (IB) - 1ère heure de trading
    2. Value Area (VA) - Zone de 70% du volume
    3. Volatilité - Régime de volatilité bas
    4. Score bullish - Proche de 0 = neutre
    5. Prix vs HVL - Attraction vers le centre

    Args:
        snapshot: Données du snapshot
        tick_size: Taille du tick (0.25 pour ES/NQ)

    Returns:
        RangeDetection avec tous les détails
    """

    # Extraire les données
    mid = snapshot.get('mid', 0)
    atr = snapshot.get('atr', 2.0)
    vol_regime = snapshot.get('volatility_regime', 2.0)
    bullish_score = snapshot.get('mia_bullish_score', 0)

    # Structure
    structure = snapshot.get('structure', {})
    ibh = structure.get('ibh', 0)  # Initial Balance High
    ibl = structure.get('ibl', 0)  # Initial Balance Low

    # Value Area
    vva = snapshot.get('vva', {})
    vah = vva.get('vah', 0)  # Value Area High
    val = vva.get('val', 0)  # Value Area Low
    vpoc = vva.get('vpoc', 0)  # Point of Control

    # HVL
    hvl = snapshot.get('hvl', 0)

    # ═══════════════════════════════════════════════════════════════
    # CRITÈRE 1: RANGE IB (Initial Balance)
    # ═══════════════════════════════════════════════════════════════

    ib_range = 0
    ib_range_ticks = 0
    in_ib_range = False

    if ibh > 0 and ibl > 0:
        ib_range = ibh - ibl
        ib_range_ticks = ib_range / tick_size
        in_ib_range = ibl <= mid <= ibh

    # ═══════════════════════════════════════════════════════════════
    # CRITÈRE 2: RANGE VALUE AREA
    # ═══════════════════════════════════════════════════════════════

    va_range = 0
    va_range_ticks = 0
    in_va_range = False

    if vah > 0 and val > 0:
        va_range = vah - val
        va_range_ticks = va_range / tick_size
        in_va_range = val <= mid <= vah

    # ═══════════════════════════════════════════════════════════════
    # CRITÈRE 3: VOLATILITÉ BASSE
    # ═══════════════════════════════════════════════════════════════

    is_low_vol = vol_regime <= 1.5

    # ═══════════════════════════════════════════════════════════════
    # CRITÈRE 4: SCORE BULLISH NEUTRE
    # ═══════════════════════════════════════════════════════════════

    is_neutral = abs(bullish_score) < 0.20

    # ═══════════════════════════════════════════════════════════════
    # CRITÈRE 5: RANGE SERRÉ (< 3x ATR)
    # ═══════════════════════════════════════════════════════════════

    is_tight_ib = ib_range_ticks > 0 and ib_range < (atr * 3)
    is_tight_va = va_range_ticks > 0 and va_range < (atr * 3)

    # ═══════════════════════════════════════════════════════════════
    # CRITÈRE 6: VWAP PLAT (bandes SD±1 serrées)  🔥 NOUVEAU!
    # ═══════════════════════════════════════════════════════════════

    vwap_up1 = snapshot.get('vwap_up1', 0)
    vwap_dn1 = snapshot.get('vwap_dn1', 0)
    d_vwap_ticks = abs(snapshot.get('d_vwap_ticks', 0))

    is_vwap_flat = False
    price_in_vwap_bands = False

    if vwap_up1 > 0 and vwap_dn1 > 0 and atr > 0:
        vwap_band_width = vwap_up1 - vwap_dn1
        # Bandes serrées si < 2x ATR
        is_vwap_flat = (vwap_band_width / atr) < 2.5
        # Prix dans les bandes SD±1
        price_in_vwap_bands = vwap_dn1 <= mid <= vwap_up1

    # Prix proche du VWAP = Range (< 15 ticks)
    is_close_to_vwap = d_vwap_ticks < 15

    # ═══════════════════════════════════════════════════════════════
    # DÉCISION: EST-CE UN RANGE?
    # ═══════════════════════════════════════════════════════════════

    # Score de range (0-16) - 8 critères possibles
    range_score = 0
    criteria_met = []

    if in_ib_range:
        range_score += 2
        criteria_met.append("IN_IB")
    if in_va_range:
        range_score += 2
        criteria_met.append("IN_VA")
    if is_low_vol:
        range_score += 2
        criteria_met.append("LOW_VOL")
    if is_neutral:
        range_score += 2
        criteria_met.append("NEUTRAL_SCORE")
    if is_tight_ib or is_tight_va:
        range_score += 2
        criteria_met.append("TIGHT_RANGE")

    # 🔥 NOUVEAUX CRITÈRES VWAP
    if is_vwap_flat:
        range_score += 2
        criteria_met.append("VWAP_FLAT")
    if price_in_vwap_bands:
        range_score += 1
        criteria_met.append("IN_VWAP_BANDS")
    if is_close_to_vwap:
        range_score += 1
        criteria_met.append("CLOSE_TO_VWAP")

    is_range = range_score >= 6  # Au moins 6 points sur 16

    # Déterminer le type de range et les bornes
    if is_range:
        # Utiliser le range le plus pertinent
        if in_va_range and va_range > 0:
            range_type = 'VA_RANGE'
            range_high = vah
            range_low = val
            range_size = va_range_ticks
        elif in_ib_range and ib_range > 0:
            range_type = 'IB_RANGE'
            range_high = ibh
            range_low = ibl
            range_size = ib_range_ticks
        else:
            # Fallback: créer un range autour du HVL
            range_type = 'HVL_RANGE'
            buffer = atr * 1.5
            range_high = hvl + buffer if hvl > 0 else mid + buffer
            range_low = hvl - buffer if hvl > 0 else mid - buffer
            range_size = (range_high - range_low) / tick_size
    else:
        range_type = 'TRENDING'
        range_high = 0
        range_low = 0
        range_size = 0

    # Calculer la position dans le range actuel
    if is_range and range_high > range_low:
        position_pct = ((mid - range_low) / (range_high - range_low)) * 100
        position_pct = max(0, min(100, position_pct))
    else:
        position_pct = 50

    # ═══════════════════════════════════════════════════════════════
    # ZONES AVEC BUFFER (pas juste un niveau!)
    # ═══════════════════════════════════════════════════════════════

    # Zone BOTTOM: 0-25% (avec buffer)
    # Zone MIDDLE: 25-75%
    # Zone TOP: 75-100% (avec buffer)

    BOTTOM_ZONE = 25  # < 25%
    TOP_ZONE = 75     # > 75%

    if position_pct < BOTTOM_ZONE:
        zone = 'BOTTOM'
    elif position_pct > TOP_ZONE:
        zone = 'TOP'
    else:
        zone = 'MIDDLE'

    # ═══════════════════════════════════════════════════════════════
    # RECOMMANDATION D'ACTION
    # ═══════════════════════════════════════════════════════════════

    if not is_range:
        action = 'FOLLOW_TREND'
    elif zone == 'BOTTOM':
        action = 'LONG_FADE'  # Acheter en bas, vendre vers le milieu
    elif zone == 'TOP':
        action = 'SHORT_FADE'  # Vendre en haut, acheter vers le milieu
    else:
        action = 'NO_TRADE'  # Milieu = pas de trade

    # Confidence
    confidence = range_score / 10.0

    return RangeDetection(
        is_range=is_range,
        range_type=range_type,
        range_high=range_high,
        range_low=range_low,
        range_size_ticks=range_size,
        position_in_range_pct=position_pct,
        zone=zone,
        recommended_action=action,
        confidence=confidence
    )

# ═══════════════════════════════════════════════════════════════════════════════
# PARTIE 4: ADAPTATION DU SIGNAL
# ═══════════════════════════════════════════════════════════════════════════════

def adapt_signal_for_range(original_signal: str, range_detection: RangeDetection) -> Tuple[str, str]:
    """
    Adapte le signal selon si on est en range ou tendance

    Args:
        original_signal: 'LONG' ou 'SHORT'
        range_detection: Résultat de detect_range_pro()

    Returns:
        (signal_adapté, raison)
    """

    if not range_detection.is_range:
        # Pas en range = suivre le signal original
        return original_signal, f"TREND - Suivre signal {original_signal}"

    # EN RANGE
    zone = range_detection.zone
    action = range_detection.recommended_action

    if zone == 'BOTTOM':
        # En bas du range
        if original_signal == 'SHORT':
            return 'BLOCKED', f"❌ RANGE: Pas de SHORT en bas ({range_detection.position_in_range_pct:.0f}%)"
        elif original_signal == 'LONG':
            return 'LONG', f"✅ RANGE: LONG OK en bas ({range_detection.position_in_range_pct:.0f}%) - FADE vers {range_detection.range_high:.2f}"

    elif zone == 'TOP':
        # En haut du range
        if original_signal == 'LONG':
            return 'BLOCKED', f"❌ RANGE: Pas de LONG en haut ({range_detection.position_in_range_pct:.0f}%)"
        elif original_signal == 'SHORT':
            return 'SHORT', f"✅ RANGE: SHORT OK en haut ({range_detection.position_in_range_pct:.0f}%) - FADE vers {range_detection.range_low:.2f}"

    else:
        # Au milieu
        return 'BLOCKED', f"❌ RANGE: Pas de trade au MILIEU ({range_detection.position_in_range_pct:.0f}%)"

    return original_signal, "Signal inchangé"

# ═══════════════════════════════════════════════════════════════════════════════
# PARTIE 5: TEST AVEC DONNÉES SIMULÉES
# ═══════════════════════════════════════════════════════════════════════════════

def test_range_detection():
    """Test la détection de range avec des données simulées"""

    print("\n" + "="*80)
    print("PARTIE 5: TEST DE LA DÉTECTION DE RANGE")
    print("="*80)

    # Scénarios de test basés sur le graphique montré
    # 🔥 AJOUT: Données VWAP pour chaque test
    test_cases = [
        {
            'name': 'RANGE Power Hour (pertes réelles) - SD-1 PLAT',
            'mid': 6845.00,
            'atr': 2.39,
            'volatility_regime': 1.0,
            'mia_bullish_score': -0.11,
            'structure': {'ibh': 6850.00, 'ibl': 6840.00},
            'vva': {'vah': 6852.00, 'val': 6842.00, 'vpoc': 6845.00},
            'hvl': 6845.00,
            # 🔥 VWAP DATA - Bandes serrées = RANGE
            'vwap_up1': 6848.00,  # SD+1
            'vwap_dn1': 6843.00,  # SD-1 (ta ligne marron!)
            'd_vwap_ticks': 5.0,   # Proche du VWAP
            'expected': 'RANGE au milieu - NO_TRADE'
        },
        {
            'name': 'RANGE bas (proche support)',
            'mid': 6841.00,
            'atr': 2.39,
            'volatility_regime': 1.0,
            'mia_bullish_score': -0.05,
            'structure': {'ibh': 6850.00, 'ibl': 6840.00},
            'vva': {'vah': 6852.00, 'val': 6842.00, 'vpoc': 6845.00},
            'hvl': 6845.00,
            'vwap_up1': 6848.00,
            'vwap_dn1': 6843.00,
            'd_vwap_ticks': 8.0,
            'expected': 'RANGE en bas - LONG_FADE OK, SHORT BLOCKED'
        },
        {
            'name': 'RANGE haut (proche résistance)',
            'mid': 6849.50,
            'atr': 2.39,
            'volatility_regime': 1.0,
            'mia_bullish_score': 0.08,
            'structure': {'ibh': 6850.00, 'ibl': 6840.00},
            'vva': {'vah': 6852.00, 'val': 6842.00, 'vpoc': 6845.00},
            'hvl': 6845.00,
            'vwap_up1': 6848.00,
            'vwap_dn1': 6843.00,
            'd_vwap_ticks': -3.0,  # Au-dessus du VWAP
            'expected': 'RANGE en haut - SHORT_FADE OK, LONG BLOCKED'
        },
        {
            'name': 'TENDANCE (breakout) - VWAP en pente',
            'mid': 6865.00,
            'atr': 3.5,
            'volatility_regime': 2.5,
            'mia_bullish_score': 0.45,
            'structure': {'ibh': 6850.00, 'ibl': 6840.00},
            'vva': {'vah': 6852.00, 'val': 6842.00, 'vpoc': 6845.00},
            'hvl': 6845.00,
            # 🔥 VWAP DATA - Bandes larges + prix hors bandes = TENDANCE
            'vwap_up1': 6858.00,  # SD+1 large
            'vwap_dn1': 6840.00,  # SD-1 large
            'd_vwap_ticks': 40.0,  # LOIN du VWAP = tendance
            'expected': 'TENDANCE - Suivre le signal'
        }
    ]

    print("\n📊 TESTS DE DÉTECTION:")
    print("-"*80)

    for i, tc in enumerate(test_cases):
        print(f"\n{'─'*80}")
        print(f"TEST {i+1}: {tc['name']}")
        print(f"{'─'*80}")
        print(f"  Prix: {tc['mid']}")
        print(f"  Attendu: {tc['expected']}")

        # Créer snapshot
        snapshot = {
            'mid': tc['mid'],
            'atr': tc['atr'],
            'volatility_regime': tc['volatility_regime'],
            'mia_bullish_score': tc['mia_bullish_score'],
            'structure': tc['structure'],
            'vva': tc['vva'],
            'hvl': tc['hvl']
        }

        # Détecter
        result = detect_range_pro(snapshot)

        print(f"\n  RÉSULTAT:")
        print(f"    Est un range: {result.is_range}")
        print(f"    Type: {result.range_type}")
        print(f"    Bornes: {result.range_low:.2f} - {result.range_high:.2f}")
        print(f"    Taille: {result.range_size_ticks:.0f} ticks")
        print(f"    Position: {result.position_in_range_pct:.1f}%")
        print(f"    Zone: {result.zone}")
        print(f"    Action recommandée: {result.recommended_action}")
        print(f"    Confidence: {result.confidence:.0%}")

        # Tester adaptation de signal
        for signal in ['LONG', 'SHORT']:
            adapted, reason = adapt_signal_for_range(signal, result)
            status = "✅" if adapted != 'BLOCKED' else "❌"
            print(f"    Signal {signal} → {status} {adapted}: {reason}")

# ═══════════════════════════════════════════════════════════════════════════════
# PARTIE 6: CODE À INTÉGRER DANS LE BOT
# ═══════════════════════════════════════════════════════════════════════════════

def generate_integration_code():
    """Génère le code à intégrer dans le bot"""

    print("\n" + "="*80)
    print("PARTIE 6: CODE À INTÉGRER")
    print("="*80)

    print("""
# À ajouter dans utils/range_detector.py:

from dataclasses import dataclass
from typing import Tuple

@dataclass
class RangeDetection:
    is_range: bool
    range_type: str
    range_high: float
    range_low: float
    range_size_ticks: float
    position_in_range_pct: float
    zone: str
    recommended_action: str
    confidence: float

class RangeDetector:
    '''Détecteur de range professionnel'''

    def __init__(self, config: dict = None):
        self.config = config or {
            'bottom_zone_pct': 25,    # < 25% = bas
            'top_zone_pct': 75,       # > 75% = haut
            'vol_regime_max': 1.5,    # Volatilité basse
            'bullish_neutral': 0.20,  # Score neutre si |x| < 0.20
            'range_vs_atr_max': 3.0,  # Range < 3x ATR
        }

    def detect(self, snapshot: dict, tick_size: float = 0.25) -> RangeDetection:
        '''Détecte si on est en range et retourne les infos'''
        # ... (code de detect_range_pro ci-dessus)
        pass

    def adapt_signal(self, signal: str, detection: RangeDetection) -> Tuple[str, str]:
        '''Adapte le signal selon le range'''
        # ... (code de adapt_signal_for_range ci-dessus)
        pass

# À ajouter dans launch_production_CLEAN_v2.py:

from utils.range_detector import RangeDetector

# Dans __init__:
self.range_detector = RangeDetector()

# Dans _process_signal, AVANT d'envoyer le trade:
range_result = self.range_detector.detect(snapshot)
if range_result.is_range:
    adapted_signal, reason = self.range_detector.adapt_signal(
        signal.action,
        range_result
    )
    if adapted_signal == 'BLOCKED':
        logger.warning(f"🔲 [{symbol}] RANGE FILTER: {reason}")
        return
    """)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*80)
    print("AUDIT COMPLET: DÉTECTION DE RANGE")
    print("="*80)

    # Partie 1: Audit données
    audit_snapshot_data()

    # Partie 2: Problème position_in_range
    explain_position_in_range_problem()

    # Partie 5: Tests
    test_range_detection()

    # Partie 6: Code à intégrer
    generate_integration_code()

    print("\n" + "="*80)
    print("AUDIT TERMINÉ")
    print("="*80)
