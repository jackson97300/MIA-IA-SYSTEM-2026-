"""
Module: dynamic_threshold.py
Description: Calcul du seuil ML dynamique selon conditions marché

Principe:
- Seuil de base: 0.70
- Ajustements selon: volatilité, session, spread, heure
- Range final: [0.60, 0.80]

Auteur: MIA_IA_SYSTEM
Date: 5 Novembre 2025
Version: 1.0 - PATCH R2 GPT
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def compute_dynamic_threshold(snapshot: Dict[str, Any], base_threshold: float = 0.70) -> float:
    """
    Calculer seuil ML dynamique selon conditions marché

    Règle simple:
    - Base: 0.70
    - Volatilité LOW → +0.05 (plus prudent)
    - Session extrêmes (Open/Close) → +0.05
    - Spread large (≥2 ticks) → +0.05
    - Spread 1-tick → -0.05 (plus agressif)
    - Power Hour / Opening Bell → -0.05
    - Range final: [0.60, 0.80]

    Args:
        snapshot: Dict contenant les features du marché
        base_threshold: Seuil de base (défaut: 0.70)

    Returns:
        float: Seuil ajusté entre 0.60 et 0.80

    Exemple:
        >>> snapshot = {"volatility_regime": "LOW", "spread_ticks": 1, "is_1tick_spread": True}
        >>> compute_dynamic_threshold(snapshot)
        0.70  # (base 0.70 + LOW +0.05 + 1-tick -0.05 = 0.70)
    """

    threshold = base_threshold
    adjustments = []

    # ═════════════════════════════════════════════════════════════
    # AJUSTEMENT 1: VOLATILITÉ
    # ═════════════════════════════════════════════════════════════
    vol_regime = snapshot.get('volatility_regime', 'UNKNOWN').upper()

    if vol_regime == 'LOW':
        threshold += 0.05
        adjustments.append("VOL_LOW +0.05")
    elif vol_regime == 'HIGH':
        # Pas d'ajustement (neutre)
        adjustments.append("VOL_HIGH 0.00")

    # ═════════════════════════════════════════════════════════════
    # AJUSTEMENT 2: SESSION PROGRESS
    # ═════════════════════════════════════════════════════════════
    session_progress = snapshot.get('session_progress', 0.5)

    # Session extrêmes: Open (0.0-0.05) ou Close (0.85-1.0)
    if session_progress <= 0.05 or session_progress >= 0.85:
        threshold += 0.05
        adjustments.append(f"SESSION_EXTREME +0.05 (prog={session_progress:.2f})")

    # ═════════════════════════════════════════════════════════════
    # AJUSTEMENT 3: SPREAD
    # ═════════════════════════════════════════════════════════════
    spread_ticks = snapshot.get('spread_ticks', 1)
    is_1tick = snapshot.get('is_1tick_spread', False)

    if spread_ticks >= 2:
        threshold += 0.05
        adjustments.append(f"SPREAD_LARGE +0.05 ({spread_ticks} ticks)")
    elif is_1tick:
        threshold -= 0.05
        adjustments.append("SPREAD_1TICK -0.05")

    # ═════════════════════════════════════════════════════════════
    # AJUSTEMENT 4: HEURE (Power Hour / Opening Bell)
    # ═════════════════════════════════════════════════════════════
    hour = snapshot.get('hour', 12)  # Heure UTC ou locale

    # Power Hour (14-15h CT = volume élevé) ou Opening Bell (9-10h CT)
    # Adapter selon votre timezone
    if hour in [9, 10, 14, 15]:
        threshold -= 0.05
        adjustments.append(f"POWER_HOUR -0.05 (hour={hour})")

    # ═════════════════════════════════════════════════════════════
    # CLIP FINAL: [0.60, 0.80]
    # ═════════════════════════════════════════════════════════════
    threshold_before_clip = threshold
    threshold = max(0.60, min(threshold, 0.80))

    # Log si clipping
    if threshold != threshold_before_clip:
        adjustments.append(f"CLIPPED {threshold_before_clip:.2f} → {threshold:.2f}")

    # Log final
    logger.debug(f"🎯 Seuil dynamique: {base_threshold:.2f} → {threshold:.2f} | {', '.join(adjustments)}")

    return threshold


def compute_segment_threshold(
    volatility_regime: str = None,
    session_progress: float = None,
    spread_ticks: float = None,
    hour: int = None,
    base_threshold: float = 0.70
) -> float:
    """
    Version simplifiée pour segmentation (sans snapshot complet)

    Args:
        volatility_regime: 'LOW', 'MEDIUM', 'HIGH'
        session_progress: 0.0-1.0
        spread_ticks: Spread en nombre de ticks
        hour: Heure de la journée (0-23)
        base_threshold: Seuil de base

    Returns:
        float: Seuil ajusté
    """
    snapshot = {}
    if volatility_regime:
        snapshot['volatility_regime'] = volatility_regime
    if session_progress is not None:
        snapshot['session_progress'] = session_progress
    if spread_ticks is not None:
        snapshot['spread_ticks'] = spread_ticks
    if hour is not None:
        snapshot['hour'] = hour

    return compute_dynamic_threshold(snapshot, base_threshold)


# ═════════════════════════════════════════════════════════════
# FONCTION POUR PROFIT FACTOR PAR SEGMENT
# ═════════════════════════════════════════════════════════════

def compute_pf_by_segment(
    df_test,
    y_test,
    y_proba,
    segment_col: str,
    binary_mode: bool = False
):
    """
    Calculer Profit Factor par segment avec seuil dynamique

    Args:
        df_test: DataFrame test avec features
        y_test: Labels réels
        y_proba: Probabilités prédites
        segment_col: Colonne de segmentation ('volatility_regime', 'session_bucket', etc.)
        binary_mode: Si True, mode binaire

    Returns:
        Dict avec PF par segment
    """
    import pandas as pd
    import numpy as np

    df_test = df_test.copy().reset_index(drop=True)
    df_test['y_true'] = y_test

    if binary_mode and y_proba.ndim > 1:
        df_test['y_proba'] = y_proba[:, 1]  # P(UP)
    elif y_proba.ndim > 1:
        df_test['y_proba'] = y_proba.max(axis=1)
    else:
        df_test['y_proba'] = y_proba

    results = {}

    logger.info(f"\n{'='*70}")
    logger.info(f"📊 PROFIT FACTOR PAR SEGMENT ({segment_col})")
    logger.info(f"{'='*70}")

    for segment_val, grp in df_test.groupby(segment_col):
        if len(grp) < 50:  # Min 50 samples
            continue

        # Calculer seuil dynamique pour ce segment
        if segment_col == 'volatility_regime':
            threshold = compute_segment_threshold(volatility_regime=segment_val)
        elif segment_col == 'session_bucket':
            # Approximation: 'OPEN' → 0.05, 'MID' → 0.5, 'CLOSE' → 0.9
            session_map = {'OPEN': 0.05, 'MID': 0.5, 'CLOSE': 0.9}
            threshold = compute_segment_threshold(session_progress=session_map.get(segment_val, 0.5))
        else:
            threshold = 0.70  # Fallback

        # Simuler trades avec seuil dynamique
        TP_AVG_TICKS = 10
        SL_AVG_TICKS = 5

        wins = []
        losses = []

        for idx in grp.index:
            proba = grp.loc[idx, 'y_proba']
            y_true_val = grp.loc[idx, 'y_true']

            # Appliquer seuil dynamique
            if proba < threshold:
                continue  # Skip

            # Prédiction
            if binary_mode:
                y_pred_val = 1 if proba >= 0.5 else 0
            else:
                y_pred_val = 1 if proba >= 0.5 else 0  # Simplification

            # Simuler résultat
            if y_pred_val == y_true_val:
                wins.append(TP_AVG_TICKS)
            else:
                losses.append(SL_AVG_TICKS)

        # Métriques
        n_trades = len(wins) + len(losses)
        n_wins = len(wins)
        win_rate = n_wins / n_trades if n_trades > 0 else 0

        total_wins = sum(wins)
        total_losses = sum(losses)
        pf = total_wins / total_losses if total_losses > 0 else float('inf')

        results[segment_val] = {
            'threshold': threshold,
            'n_trades': n_trades,
            'win_rate': win_rate,
            'profit_factor': pf,
            'n_samples': len(grp)
        }

        logger.info(f"\n📊 Segment: {segment_val}")
        logger.info(f"   Seuil dynamique: {threshold:.2f}")
        logger.info(f"   Trades: {n_trades:,} ({win_rate:.1%} win-rate)")
        logger.info(f"   PF: {pf:.2f}")

    return results


if __name__ == "__main__":
    # Test unitaire
    import sys
    import io

    # Fix encoding pour Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    logging.basicConfig(level=logging.DEBUG)

    print("\n" + "="*70)
    print("TEST 1: Snapshot neutre (base 0.70)")
    print("="*70)
    snapshot1 = {"volatility_regime": "MEDIUM", "spread_ticks": 1, "session_progress": 0.5, "hour": 12}
    threshold1 = compute_dynamic_threshold(snapshot1)
    print(f"Résultat: {threshold1}")
    assert threshold1 == 0.70

    print("\n" + "="*70)
    print("TEST 2: Vol LOW + Spread 1-tick")
    print("="*70)
    snapshot2 = {"volatility_regime": "LOW", "is_1tick_spread": True, "spread_ticks": 1}
    threshold2 = compute_dynamic_threshold(snapshot2)
    print(f"Résultat: {threshold2}")
    assert threshold2 == 0.70  # +0.05 (LOW) -0.05 (1-tick) = 0.70

    print("\n" + "="*70)
    print("TEST 3: Session OPEN + Spread large")
    print("="*70)
    snapshot3 = {"session_progress": 0.02, "spread_ticks": 2}
    threshold3 = compute_dynamic_threshold(snapshot3)
    print(f"Résultat: {threshold3}")
    assert threshold3 == 0.80  # +0.05 (OPEN) +0.05 (spread) = 0.80

    print("\n" + "="*70)
    print("TEST 4: Power Hour + 1-tick spread")
    print("="*70)
    snapshot4 = {"hour": 14, "is_1tick_spread": True}
    threshold4 = compute_dynamic_threshold(snapshot4)
    print(f"Résultat: {threshold4}")
    assert threshold4 == 0.60  # -0.05 (power) -0.05 (1-tick) = 0.60

    print("\n" + "="*70)
    print("TEST 5: Clipping (trop d'ajustements)")
    print("="*70)
    snapshot5 = {"volatility_regime": "LOW", "session_progress": 0.02, "spread_ticks": 3}
    threshold5 = compute_dynamic_threshold(snapshot5)
    print(f"Résultat: {threshold5}")
    assert threshold5 == 0.80  # 0.70 +0.05 +0.05 +0.05 = 0.85 → clip à 0.80

    print("\n[OK] Tous les tests passes !")
