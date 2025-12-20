#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strategies/strategy_helpers.py

HELPERS COMMUNS POUR TOUTES LES STRATÉGIES
===========================================

Fonctions utilitaires partagées entre toutes les stratégies:
1. Volume adaptif par session/symbole
2. Ajustement SL/TP selon VIX/volatilité
3. Bonus/malus inter-markets (NQ↔ES)
4. Headroom GEX dynamique

Date: 10 Novembre 2025
Version: 1.0
"""

from typing import Dict, Any, Tuple


# === 1. VOLUME ADAPTIF PAR SESSION/SYMBOLE ===

def volume_is_high(ml_data: Dict[str, Any]) -> bool:
    """
    Détermine si le volume est élevé selon la session et le symbole.

    Seuils adaptatifs:
    - Asia: volume plus faible acceptable (35 base)
    - EU: volume intermédiaire (45 base)
    - US: volume élevé requis (55 base)
    - NQ: plus actif que ES (-3 ticks)
    - RTY: plus irrégulier (-5 ticks)

    Args:
        ml_data: Données ML_READY

    Returns:
        True si volume considéré comme élevé pour la session/symbole
    """
    vol = ml_data.get('volume', 0)
    sess = ml_data.get('session_id', 'US')   # 'Asia','EU','US'
    sym = (ml_data.get('sym', '') or '').upper()

    # Seuils "safe" par session/symbole (calibrage conservateur)
    base = 35 if sess == 'Asia' else (45 if sess == 'EU' else 55)

    # NQ plus actif que ES en ticks, RTY plus irrégulier
    if 'NQ' in sym:
        base -= 3
    if 'RTY' in sym:
        base -= 5

    # Garde-fou sur le flow: au moins un peu d'activité
    # tick_rate_1s/trade_rate_1s existent dans ML_READY
    if ml_data.get('tick_rate_1s', 0) >= 1 or ml_data.get('trade_rate_1s', 0) >= 1:
        return vol >= base
    return vol >= (base + 5)


# === 2. AJUSTEMENT SL/TP DYNAMIQUE SELON VIX/VOLATILITÉ ===

def adjust_sl_tp_for_volatility(
    ml_data: Dict[str, Any],
    base_sl_ticks: int,
    base_tp_multiplier: float
) -> Tuple[int, float]:
    """
    Ajuste SL/TP selon le régime de volatilité.

    Logique:
    - VIX bas ou volatilité faible → SL plus serré, TP légèrement augmenté
    - VIX élevé ou volatilité forte → SL plus large, TP plus ambitieux
    - Normal → pas de changement

    Args:
        ml_data: Données ML_READY
        base_sl_ticks: SL de base en ticks
        base_tp_multiplier: Multiplicateur TP de base (ex: 2.0 pour 2R)

    Returns:
        (sl_ticks_adjusted, tp_multiplier_adjusted)
    """
    vix = ml_data.get('vix', 18)
    vol_regime = ml_data.get('volatility_regime_cont', 0.15)

    # Marché CALME: SL plus serré (moins de bruit), TP standard+10%
    if vix <= 16 or vol_regime <= 0.12:
        sl_ticks = max(base_sl_ticks - 1, 6)  # Minimum 6 ticks
        tp_mult = base_tp_multiplier * 1.10  # +10% sur TP

    # Marché VOLATIL: SL plus large (éviter stop out), TP plus ambitieux
    elif vix >= 22:
        sl_ticks = base_sl_ticks + 2
        tp_mult = base_tp_multiplier * 1.20  # +20% sur TP

    # Marché NORMAL: pas de changement
    else:
        sl_ticks = base_sl_ticks
        tp_mult = base_tp_multiplier

    return (sl_ticks, tp_mult)


# === 3. BONUS/MALUS INTER-MARKETS (NQ↔ES) ===

def get_intermarket_bonus(ml_data: Dict[str, Any], direction: str) -> float:
    """
    Calcule bonus/malus de confidence basé sur corrélation NQ↔ES.

    Principe:
    - Si NQ surperforme ES (z > 0.5) et signal LONG → +0.03 confidence
    - Si NQ sous-performe ES (z < -0.5) et signal SHORT → +0.03 confidence
    - Si divergence contradictoire → -0.05 confidence (warning)

    Args:
        ml_data: Données ML_READY
        direction: "LONG" ou "SHORT"

    Returns:
        Bonus/malus de confidence (-0.05, 0.0, ou +0.03)
    """
    nq_es_z = ml_data.get('nq_es_rs_z_120s', 0.0)

    if direction == "LONG":
        if nq_es_z > 0.5:
            return +0.03  # NQ surperforme ES, LONG confirmé
        elif nq_es_z < -0.5:
            return -0.05  # NQ sous-performe ES, LONG risqué
    else:  # SHORT
        if nq_es_z < -0.5:
            return +0.03  # NQ sous-performe ES, SHORT confirmé
        elif nq_es_z > 0.5:
            return -0.05  # NQ surperforme ES, SHORT risqué

    return 0.0  # Neutre (−0.5 < z < 0.5)


# === 4. HEADROOM GEX DYNAMIQUE ===

def check_headroom_dynamic(
    ml_data: Dict[str, Any],
    direction: str,
    min_headroom_us: int = 45,
    min_headroom_asia: int = 35
) -> bool:
    """
    Vérifie headroom GEX suffisant avec seuils adaptatifs par session.

    Principe:
    - Asia: accepter headroom plus faible (35 ticks) car moins de liquidité
    - US: exiger headroom plus important (45 ticks) pour sécurité

    Args:
        ml_data: Données ML_READY
        direction: "LONG" ou "SHORT"
        min_headroom_us: Headroom minimum en US (default: 45)
        min_headroom_asia: Headroom minimum en Asia (default: 35)

    Returns:
        True si headroom suffisant
    """
    menthor_dist = ml_data.get('menthor_distances', {})
    if not isinstance(menthor_dist, dict):
        return True  # Pas de data, on accepte

    sess = ml_data.get('session_id', 'US')
    threshold = min_headroom_asia if sess == 'Asia' else min_headroom_us

    if direction == "LONG":
        near_gex_up = menthor_dist.get('near_gex_up', 999)
        return near_gex_up >= threshold
    else:  # SHORT
        near_gex_dn = menthor_dist.get('near_gex_dn', 999)
        return near_gex_dn >= threshold


# === 5. DELTA FLIP BOOST ===

def get_delta_flip_boost(ml_data: Dict[str, Any], direction: str) -> float:
    """
    Bonus léger si delta_flip confirme la direction du trade.

    Args:
        ml_data: Données ML_READY
        direction: "LONG" ou "SHORT"

    Returns:
        +0.05 si delta_flip + imbalance alignés, 0.0 sinon
    """
    if not ml_data.get('delta_flip', False):
        return 0.0

    imbalance = ml_data.get('level1_imbalance', 0.0)

    # Delta flip + imbalance forte dans le bon sens
    if direction == "LONG" and imbalance > 0.12:
        return +0.05
    elif direction == "SHORT" and imbalance < -0.12:
        return +0.05

    return 0.0  # Delta flip sans confirmation imbalance


# === 6. GET TICK SIZE (Utility) ===

def get_tick_size(ml_data: Dict[str, Any]) -> float:
    """
    Retourne le tick size approprié selon le symbole.

    Args:
        ml_data: Données ML_READY

    Returns:
        Tick size (0.25 pour ES/NQ, 0.10 pour RTY, etc.)
    """
    symbol = (ml_data.get('sym', 'NQ') or 'NQ').upper()

    if 'ES' in symbol or 'NQ' in symbol:
        return 0.25
    elif 'RTY' in symbol or 'YM' in symbol:
        return 0.10
    else:
        return 0.25  # Default


# === 7. GET SYMBOL NAME (Utility) ===

def get_symbol_name(ml_data: Dict[str, Any]) -> str:
    """
    Retourne le nom du symbole de façon sûre.

    Args:
        ml_data: Données ML_READY

    Returns:
        Symbole en majuscules (default: 'NQ')
    """
    return (ml_data.get('sym', 'NQ') or 'NQ').upper()


if __name__ == "__main__":
    # Tests simples
    print("=== TEST STRATEGY HELPERS ===")

    # Test 1: Volume Asia NQ
    test_asia_nq = {
        'volume': 40,
        'session_id': 'Asia',
        'sym': 'NQ',
        'tick_rate_1s': 2
    }
    print(f"Asia NQ vol=40: {volume_is_high(test_asia_nq)}")  # Devrait être True (base 32)

    # Test 2: SL/TP volatilité basse
    test_low_vix = {
        'vix': 14,
        'volatility_regime_cont': 0.10
    }
    sl, tp = adjust_sl_tp_for_volatility(test_low_vix, 10, 2.0)
    print(f"Low VIX: SL={sl}, TP_mult={tp:.2f}")  # 9 ticks, 2.20x

    # Test 3: Inter-market LONG avec NQ outperform
    test_long_outperf = {
        'nq_es_rs_z_120s': 0.8
    }
    bonus = get_intermarket_bonus(test_long_outperf, "LONG")
    print(f"LONG + NQ outperform: {bonus:+.2f}")  # +0.03

    # Test 4: Headroom Asia
    test_headroom_asia = {
        'menthor_distances': {'near_gex_up': 38},
        'session_id': 'Asia'
    }
    ok = check_headroom_dynamic(test_headroom_asia, "LONG")
    print(f"Headroom Asia 38t: {ok}")  # True (seuil 35)

    print("=== TESTS TERMINÉS ===")
