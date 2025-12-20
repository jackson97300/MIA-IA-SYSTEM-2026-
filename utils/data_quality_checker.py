#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Quality Checker - Validation des snapshots avant trading
Date: 29 Nov 2025

OBJECTIF: Empêcher le bot de trader avec des données périmées ou invalides

🔧 10/12: Age max importé depuis config/trading_params.py (centralisé)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from core.logger import get_logger

# 🎯 CONFIG CENTRALISÉE - Source unique de vérité
from config.trading_params import GLOBAL_CONFIG, get_max_data_age

logger = get_logger(__name__)


class DataQualityChecker:
    """
    Vérifie la qualité et la fraîcheur des données avant trading

    PROTECTIONS:
    1. Age des données (configurable via trading_params.py)
    2. Champs critiques présents
    3. Valeurs cohérentes
    4. Connexion Sierra Chart
    """

    def __init__(self, max_data_age_seconds: int = None):
        """
        Args:
            max_data_age_seconds: Age maximum des données acceptées
                                  (défaut: depuis config/trading_params.py)
        """
        # 🎯 Utiliser config centralisée si non spécifié
        self.max_data_age_seconds = max_data_age_seconds or get_max_data_age()
        logger.info(f"✅ DataQualityChecker initialisé (max age: {self.max_data_age_seconds}s)")

    def validate_snapshot(self, snapshot: Dict, symbol: str) -> Tuple[bool, str]:
        """
        Valide un snapshot avant de l'utiliser pour trading

        Args:
            snapshot: Snapshot à valider
            symbol: Symbole (ES/NQ/RTY)

        Returns:
            (is_valid, reason) - True si valide, False + raison si invalide
        """
        if not snapshot:
            return False, "Snapshot vide"

        # 1. Vérifier timestamp présent
        timestamp_ms = snapshot.get('t_ms', 0)
        if timestamp_ms == 0:
            return False, "Timestamp manquant"

        # 2. Vérifier age des données
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        age_ms = now_ms - timestamp_ms
        age_seconds = age_ms / 1000.0

        if age_seconds > self.max_data_age_seconds:
            return False, f"Données trop anciennes ({age_seconds:.1f}s > {self.max_data_age_seconds}s)"

        if age_seconds < 0:
            return False, f"Timestamp futur (décalage horloge: {abs(age_seconds):.1f}s)"

        # 3. Vérifier champs critiques pour trading
        required_fields = [
            'mid',           # Prix mid
            'best_bid',      # Meilleur bid
            'best_ask',      # Meilleur ask
            'vwap',          # VWAP
            'delta',         # Delta
            'volume',        # Volume
        ]

        missing_fields = []
        for field in required_fields:
            if field not in snapshot or snapshot[field] is None:
                missing_fields.append(field)

        if missing_fields:
            return False, f"Champs manquants: {', '.join(missing_fields)}"

        # 4. Vérifier valeurs cohérentes
        mid = snapshot.get('mid', 0)
        best_bid = snapshot.get('best_bid', 0)
        best_ask = snapshot.get('best_ask', 0)

        if mid <= 0:
            return False, f"Prix mid invalide: {mid}"

        if best_bid <= 0 or best_ask <= 0:
            return False, f"Bid/Ask invalides: {best_bid}/{best_ask}"

        if best_ask < best_bid:
            return False, f"Ask ({best_ask}) < Bid ({best_bid})"

        # Spread anormal (> 10 ticks pour ES/NQ, > 20 pour RTY)
        spread = best_ask - best_bid
        tick_size = snapshot.get('tick_size', 0.25)
        spread_ticks = spread / tick_size if tick_size > 0 else 999

        max_spread_ticks = 20 if symbol == "RTY" else 10
        if spread_ticks > max_spread_ticks:
            return False, f"Spread anormal: {spread_ticks:.1f} ticks (max {max_spread_ticks})"

        # 5. Vérifier données MenthorQ si présentes
        if 'gex_1' in snapshot:
            gex_1 = snapshot.get('gex_1', 0)
            if gex_1 == 0:
                # GEX à 0 = pas de données options (suspet)
                logger.warning(f"⚠️ [{symbol}] GEX à 0 (pas de données options?)")

        # 6. Vérifier VIX si présent
        if 'vix' in snapshot:
            vix = snapshot.get('vix', 0)
            if vix <= 0:
                return False, f"VIX invalide: {vix}"
            if vix > 100:
                return False, f"VIX anormal: {vix}"

        # 7. Vérifier session_id (London/US/Asia)
        session_id = snapshot.get('session_id', '')
        if not session_id:
            logger.warning(f"⚠️ [{symbol}] Session ID manquant")

        # ✅ TOUTES LES VÉRIFICATIONS PASSÉES
        return True, f"OK (age: {age_seconds:.1f}s)"

    def get_data_quality_report(self, snapshot: Dict, symbol: str) -> Dict:
        """
        Génère un rapport détaillé sur la qualité des données

        Returns:
            Dict avec métriques de qualité
        """
        is_valid, reason = self.validate_snapshot(snapshot, symbol)

        if not snapshot:
            return {
                'is_valid': False,
                'reason': "Snapshot vide",
                'age_seconds': 999,
                'quality_score': 0
            }

        timestamp_ms = snapshot.get('t_ms', 0)
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        age_seconds = (now_ms - timestamp_ms) / 1000.0

        # Calculer score qualité (0-100)
        quality_score = 100

        # Pénalités
        if age_seconds > 1:
            quality_score -= min(30, (age_seconds - 1) * 10)  # -10 par seconde > 1s

        if snapshot.get('gex_1', 0) == 0:
            quality_score -= 10  # Pas de données options

        if snapshot.get('vix', 0) == 0:
            quality_score -= 10  # Pas de VIX

        if not snapshot.get('session_id'):
            quality_score -= 5  # Session ID manquant

        quality_score = max(0, quality_score)

        return {
            'is_valid': is_valid,
            'reason': reason,
            'age_seconds': round(age_seconds, 2),
            'timestamp': datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            'quality_score': quality_score,
            'has_menthorq': snapshot.get('gex_1', 0) != 0,
            'has_vix': snapshot.get('vix', 0) != 0,
            'session_id': snapshot.get('session_id', 'N/A'),
            'mid': snapshot.get('mid', 0),
            'spread': snapshot.get('best_ask', 0) - snapshot.get('best_bid', 0)
        }


def create_data_quality_checker(max_age_seconds: int = None) -> DataQualityChecker:
    """Factory function - utilise config centralisée par défaut"""
    return DataQualityChecker(max_data_age_seconds=max_age_seconds)


# Test unitaire
if __name__ == "__main__":
    import time

    print("=" * 80)
    print("TEST DATA QUALITY CHECKER")
    print("=" * 80)

    checker = DataQualityChecker(max_data_age_seconds=5)

    # Test 1: Données valides
    print("\n1. Test données valides (récentes):")
    valid_snapshot = {
        't_ms': int(time.time() * 1000),  # Maintenant
        'mid': 5000.0,
        'best_bid': 4999.75,
        'best_ask': 5000.25,
        'vwap': 5001.0,
        'delta': 100,
        'volume': 1000,
        'gex_1': 4900.0,
        'vix': 15.5,
        'session_id': 'US'
    }

    is_valid, reason = checker.validate_snapshot(valid_snapshot, 'ES')
    print(f"   Résultat: {is_valid} - {reason}")

    report = checker.get_data_quality_report(valid_snapshot, 'ES')
    print(f"   Qualité: {report['quality_score']}/100")
    print(f"   Age: {report['age_seconds']}s")

    # Test 2: Données trop anciennes
    print("\n2. Test données périmées (10 secondes):")
    old_snapshot = valid_snapshot.copy()
    old_snapshot['t_ms'] = int((time.time() - 10) * 1000)

    is_valid, reason = checker.validate_snapshot(old_snapshot, 'ES')
    print(f"   Résultat: {is_valid} - {reason}")

    # Test 3: Champs manquants
    print("\n3. Test champs manquants:")
    incomplete_snapshot = {
        't_ms': int(time.time() * 1000),
        'mid': 5000.0
        # Manque bid, ask, vwap, etc.
    }

    is_valid, reason = checker.validate_snapshot(incomplete_snapshot, 'ES')
    print(f"   Résultat: {is_valid} - {reason}")

    # Test 4: Spread anormal
    print("\n4. Test spread anormal:")
    wide_spread = valid_snapshot.copy()
    wide_spread['best_bid'] = 4990.0
    wide_spread['best_ask'] = 5010.0  # Spread de 20 points !

    is_valid, reason = checker.validate_snapshot(wide_spread, 'ES')
    print(f"   Résultat: {is_valid} - {reason}")

    print("\n" + "=" * 80)
    print("✅ Tests terminés")
