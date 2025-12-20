"""
TEST TREND FILTER SUR DONNÉES RÉELLES - 05/12/2025
====================================================

Objectif: Comparer l'ancienne logique vs la nouvelle logique
sur les trades qui ont perdu à cause de "Direction incorrecte"

Trades à analyser:
- 20:00 NQ SHORT @ 25727.75 → WIN (+$250) - TP Hit
- 20:13 NQ SHORT @ 25727.25 → LOSS (-$125) - Direction incorrecte
- 20:23 NQ SHORT @ 25726.75 → WIN (+$250) - TP Hit
- 20:32 NQ SHORT @ 25720.00 → WIN (+$120) - BE Hit
- 20:50 NQ SHORT @ 25710.88 → LOSS (-$127) - Direction incorrecte
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
from collections import deque

# Configuration
DATA_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE\20251205\CHART_9\ML_READY\ml_NQZ25_FUT_CME_9.jsonl")

# Trades du 5 décembre (heures en timestamp ms approximatif)
# 20:00 Paris = 19:00 UTC = environ 1764957600000 ms
TRADES_05DEC = [
    {"time": "20:00", "direction": "SHORT", "price": 25727.75, "result": "WIN", "pnl": 250},
    {"time": "20:13", "direction": "SHORT", "price": 25727.25, "result": "LOSS", "pnl": -125},
    {"time": "20:23", "direction": "SHORT", "price": 25726.75, "result": "WIN", "pnl": 250},
    {"time": "20:32", "direction": "SHORT", "price": 25720.00, "result": "WIN", "pnl": 120},
    {"time": "20:50", "direction": "SHORT", "price": 25710.88, "result": "LOSS", "pnl": -127},
]

class TrendBias:
    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    WEAK_BULLISH = "WEAK_BULLISH"
    NEUTRAL = "NEUTRAL"
    WEAK_BEARISH = "WEAK_BEARISH"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"
    UNKNOWN = "UNKNOWN"


class OldTrendFilter:
    """
    ANCIENNE LOGIQUE (celle qui a causé les pertes)
    - Ne regarde QUE la position vs HVL et VWAP
    """

    def analyze(self, snapshot: Dict) -> Tuple[str, str]:
        mid = snapshot.get('mid', 0)
        hvl = snapshot.get('hvl', 0)
        vwap = snapshot.get('vwap', 0)
        cum_delta = snapshot.get('cum_delta_session', 0)

        if not mid or not hvl or not vwap:
            return TrendBias.UNKNOWN, "Données manquantes"

        above_hvl = mid > hvl
        above_vwap = mid > vwap

        hvl_distance = (mid - hvl) / 0.25  # ticks
        vwap_distance = (mid - vwap) / 0.25  # ticks

        hvl_significant = abs(hvl_distance) > 30
        vwap_significant = abs(vwap_distance) > 25
        delta_bullish = cum_delta > 800
        delta_bearish = cum_delta < -800

        if above_hvl and above_vwap:
            if hvl_significant and vwap_significant and delta_bullish:
                return TrendBias.STRONG_BULLISH, f"Prix >> HVL ({hvl_distance:+.0f}t) et >> VWAP ({vwap_distance:+.0f}t)"
            elif hvl_significant or vwap_significant:
                return TrendBias.BULLISH, f"Prix > HVL ({hvl_distance:+.0f}t) et > VWAP ({vwap_distance:+.0f}t)"
            else:
                return TrendBias.WEAK_BULLISH, f"Prix légèrement > HVL/VWAP"

        elif not above_hvl and not above_vwap:
            if hvl_significant and vwap_significant and delta_bearish:
                return TrendBias.STRONG_BEARISH, f"Prix << HVL ({hvl_distance:+.0f}t) et << VWAP ({vwap_distance:+.0f}t)"
            elif hvl_significant or vwap_significant:
                return TrendBias.BEARISH, f"Prix < HVL ({hvl_distance:+.0f}t) et < VWAP ({vwap_distance:+.0f}t)"
            else:
                return TrendBias.WEAK_BEARISH, f"Prix légèrement < HVL/VWAP"
        else:
            # Prix entre HVL et VWAP → NEUTRAL (LE PROBLÈME!)
            return TrendBias.NEUTRAL, f"Prix entre HVL et VWAP → RANGE"

    def should_allow(self, direction: str, snapshot: Dict) -> Tuple[bool, str]:
        bias, reason = self.analyze(snapshot)

        if bias == TrendBias.NEUTRAL or bias == TrendBias.UNKNOWN:
            return True, f"[OK] {bias}: Direction autorisee"

        is_bullish = bias in [TrendBias.STRONG_BULLISH, TrendBias.BULLISH, TrendBias.WEAK_BULLISH]
        is_bearish = bias in [TrendBias.STRONG_BEARISH, TrendBias.BEARISH, TrendBias.WEAK_BEARISH]

        if (is_bullish and direction == "LONG") or (is_bearish and direction == "SHORT"):
            return True, f"[OK] {direction} aligne avec {bias}"

        if bias in [TrendBias.STRONG_BULLISH, TrendBias.STRONG_BEARISH]:
            return False, f"[BLOCK] {direction} BLOQUE - Contre {bias}"

        # Tendance faible → autoriser
        return True, f"⚠️ {direction} contre tendance faible - Autorisé"


class NewTrendFilter:
    """
    NOUVELLE LOGIQUE PROPOSÉE (multi-facteur avec momentum)
    """

    def __init__(self):
        self.price_history = deque(maxlen=30)  # 30 derniers prix

    def _analyze_momentum(self, snapshot: Dict) -> Tuple[str, float]:
        """Analyse le momentum basé sur tick_momentum et mia_bullish_score"""
        tick_momentum = snapshot.get('tick_momentum', 0)
        mia_score = snapshot.get('mia_bullish_score', 0)

        # Calculer score momentum
        momentum_score = (tick_momentum * 0.5) + (mia_score * 0.5)

        if momentum_score > 0.15:
            return "BULLISH", momentum_score
        elif momentum_score < -0.15:
            return "BEARISH", momentum_score
        return "NEUTRAL", momentum_score

    def _analyze_delta_trend(self, snapshot: Dict) -> str:
        """Analyse la direction du delta"""
        cum_delta = snapshot.get('cum_delta_session', 0)
        delta_pct = snapshot.get('deltaPct', 0)

        # Combiner delta cumulatif et delta récent
        if cum_delta > 500 and delta_pct > 0.1:
            return "BULLISH"
        elif cum_delta < -500 and delta_pct < -0.1:
            return "BEARISH"
        return "NEUTRAL"

    def _analyze_structure(self, snapshot: Dict) -> str:
        """Analyse la structure de marché"""
        # Utiliser les données de structure disponibles
        structure = snapshot.get('structure', {})
        mid = snapshot.get('mid', 0)

        ibh = structure.get('ibh', 0)  # Initial Balance High
        ibl = structure.get('ibl', 0)  # Initial Balance Low

        if ibh and ibl and mid:
            if mid > ibh:
                return "BULLISH"  # Au-dessus de l'IB
            elif mid < ibl:
                return "BEARISH"  # En-dessous de l'IB
        return "NEUTRAL"

    def _analyze_position(self, snapshot: Dict) -> Tuple[str, str]:
        """Ancienne logique de position (pour comparaison)"""
        mid = snapshot.get('mid', 0)
        hvl = snapshot.get('hvl', 0)
        vwap = snapshot.get('vwap', 0)

        if not mid or not hvl or not vwap:
            return "UNKNOWN", "Données manquantes"

        above_hvl = mid > hvl
        above_vwap = mid > vwap

        hvl_dist = (mid - hvl) / 0.25
        vwap_dist = (mid - vwap) / 0.25

        if above_hvl and above_vwap:
            return "BULLISH", f"Au-dessus HVL ({hvl_dist:+.0f}t) et VWAP ({vwap_dist:+.0f}t)"
        elif not above_hvl and not above_vwap:
            return "BEARISH", f"En-dessous HVL ({hvl_dist:+.0f}t) et VWAP ({vwap_dist:+.0f}t)"
        else:
            return "NEUTRAL", f"Entre HVL ({hvl_dist:+.0f}t) et VWAP ({vwap_dist:+.0f}t)"

    def analyze(self, snapshot: Dict) -> Tuple[str, str, Dict]:
        """
        Analyse multi-facteur avec votes pondérés
        """
        # 1. Position vs HVL/VWAP (25%)
        position_bias, position_reason = self._analyze_position(snapshot)

        # 2. Momentum (30%) - CRITIQUE!
        momentum_bias, momentum_score = self._analyze_momentum(snapshot)

        # 3. Delta trend (20%)
        delta_bias = self._analyze_delta_trend(snapshot)

        # 4. Structure (25%)
        structure_bias = self._analyze_structure(snapshot)

        # Votes pondérés
        votes = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
        weights = {"position": 0.25, "momentum": 0.30, "delta": 0.20, "structure": 0.25}

        for bias_name, bias_value, weight_key in [
            ("position", position_bias, "position"),
            ("momentum", momentum_bias, "momentum"),
            ("delta", delta_bias, "delta"),
            ("structure", structure_bias, "structure")
        ]:
            if "BULLISH" in str(bias_value).upper():
                votes["BULLISH"] += weights[weight_key]
            elif "BEARISH" in str(bias_value).upper():
                votes["BEARISH"] += weights[weight_key]
            else:
                votes["NEUTRAL"] += weights[weight_key]

        # Déterminer biais final
        max_vote = max(votes.values())
        if votes["BULLISH"] == max_vote and max_vote > 0.40:
            final_bias = TrendBias.BULLISH
        elif votes["BEARISH"] == max_vote and max_vote > 0.40:
            final_bias = TrendBias.BEARISH
        else:
            final_bias = TrendBias.NEUTRAL

        details = {
            "position": position_bias,
            "momentum": momentum_bias,
            "momentum_score": momentum_score,
            "delta": delta_bias,
            "structure": structure_bias,
            "votes": votes
        }

        reason = f"Position={position_bias}, Momentum={momentum_bias}({momentum_score:.2f}), Delta={delta_bias}, Structure={structure_bias}"

        return final_bias, reason, details

    def should_allow(self, direction: str, snapshot: Dict) -> Tuple[bool, str, Dict]:
        bias, reason, details = self.analyze(snapshot)

        if bias == TrendBias.NEUTRAL:
            return True, f"[OK] NEUTRAL: Direction autorisee", details

        is_bullish = bias in [TrendBias.STRONG_BULLISH, TrendBias.BULLISH]
        is_bearish = bias in [TrendBias.STRONG_BEARISH, TrendBias.BEARISH]

        if (is_bullish and direction == "LONG") or (is_bearish and direction == "SHORT"):
            return True, f"[OK] {direction} aligne avec {bias}", details

        # Contre-tendance -> BLOQUER
        return False, f"[BLOCK] {direction} BLOQUE - Contre {bias} ({reason})", details


def load_snapshots_around_time(target_hour: int, target_minute: int, window_minutes: int = 2) -> List[Dict]:
    """
    Charge les snapshots autour d'une heure spécifique
    """
    snapshots = []

    print(f"\n[LOAD] Chargement des donnees depuis: {DATA_PATH}")

    if not DATA_PATH.exists():
        print(f"[ERROR] Fichier non trouve: {DATA_PATH}")
        return []

    # Calculer timestamp cible (approximatif)
    # Le 05/12/2025 en timestamp: environ 1764892800 secondes (00:00 UTC)
    # 20:00 Paris = 19:00 UTC
    target_hour_utc = target_hour - 1  # Paris = UTC+1
    target_ts_start = 1764892800 + (target_hour_utc * 3600) + (target_minute * 60) - (window_minutes * 60)
    target_ts_end = 1764892800 + (target_hour_utc * 3600) + (target_minute * 60) + (window_minutes * 60)

    target_ts_start_ms = target_ts_start * 1000
    target_ts_end_ms = target_ts_end * 1000

    count = 0
    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                snap = json.loads(line)
                t_ms = snap.get('t_ms', 0)

                if target_ts_start_ms <= t_ms <= target_ts_end_ms:
                    snapshots.append(snap)
                    count += 1

                # Early exit si on a assez
                if count > 1000:
                    break

            except json.JSONDecodeError:
                continue

    print(f"[OK] {len(snapshots)} snapshots charges pour {target_hour}:{target_minute:02d} +/-{window_minutes}min")
    return snapshots


def find_snapshot_closest_to_price(snapshots: List[Dict], target_price: float) -> Dict:
    """Trouve le snapshot le plus proche du prix cible"""
    if not snapshots:
        return {}

    closest = min(snapshots, key=lambda s: abs(s.get('mid', 0) - target_price))
    return closest


def run_test():
    """
    Execute le test de comparaison
    """
    print("="*80)
    print("[TEST] TREND FILTER - DONNEES REELLES 05/12/2025")
    print("="*80)

    old_filter = OldTrendFilter()
    new_filter = NewTrendFilter()

    results = []

    for trade in TRADES_05DEC:
        hour, minute = map(int, trade["time"].split(":"))

        print(f"\n{'='*80}")
        print(f"[TRADE] {trade['time']} - {trade['direction']} @ {trade['price']}")
        print(f"   Resultat reel: {trade['result']} ({trade['pnl']:+}$)")
        print("="*80)

        # Charger les snapshots autour de cette heure
        snapshots = load_snapshots_around_time(hour, minute, window_minutes=3)

        if not snapshots:
            print("[ERROR] Pas de donnees disponibles pour ce moment")
            continue

        # Trouver le snapshot le plus proche du prix d'entree
        snapshot = find_snapshot_closest_to_price(snapshots, trade["price"])

        if not snapshot:
            print("[ERROR] Snapshot non trouve")
            continue

        mid = snapshot.get('mid', 0)
        hvl = snapshot.get('hvl', 0)
        vwap = snapshot.get('vwap', 0)
        cum_delta = snapshot.get('cum_delta_session', 0)
        tick_mom = snapshot.get('tick_momentum', 0)
        mia_score = snapshot.get('mia_bullish_score', 0)

        print(f"\n[DATA] Donnees marche:")
        print(f"   Mid: {mid:.2f}")
        print(f"   HVL: {hvl:.2f} (distance: {(mid-hvl)/0.25:+.0f}t)")
        print(f"   VWAP: {vwap:.2f} (distance: {(mid-vwap)/0.25:+.0f}t)")
        print(f"   Delta cumulatif: {cum_delta:+.0f}")
        print(f"   Tick momentum: {tick_mom:.3f}")
        print(f"   MIA bullish score: {mia_score:.3f}")

        # Test ANCIENNE logique
        print(f"\n[OLD] ANCIENNE LOGIQUE:")
        old_allowed, old_reason = old_filter.should_allow(trade["direction"], snapshot)
        print(f"   {old_reason}")
        print(f"   Autorise: {'OUI' if old_allowed else 'NON'}")

        # Test NOUVELLE logique
        print(f"\n[NEW] NOUVELLE LOGIQUE:")
        new_allowed, new_reason, details = new_filter.should_allow(trade["direction"], snapshot)
        print(f"   {new_reason}")
        print(f"   Votes: BULL={details['votes']['BULLISH']:.2f}, BEAR={details['votes']['BEARISH']:.2f}, NEUT={details['votes']['NEUTRAL']:.2f}")
        print(f"   Autorise: {'OUI' if new_allowed else 'NON'}")

        # Comparaison
        trade_was_good = trade["result"] == "WIN"
        old_correct = old_allowed == trade_was_good
        new_correct = new_allowed == trade_was_good

        # Pour un trade perdant:
        # - Si ancienne logique l'autorise mais c'est LOSS -> ancienne est MAUVAISE
        # - Si nouvelle logique le bloque et c'est LOSS -> nouvelle est BONNE

        if trade["result"] == "LOSS":
            old_correct = not old_allowed  # Aurait du bloquer
            new_correct = not new_allowed  # Aurait du bloquer

        print(f"\n[VERDICT]:")
        print(f"   Ancienne logique: {'CORRECT' if old_correct else 'ERREUR'}")
        print(f"   Nouvelle logique: {'CORRECT' if new_correct else 'ERREUR'}")

        results.append({
            "trade": trade,
            "old_allowed": old_allowed,
            "new_allowed": new_allowed,
            "old_correct": old_correct,
            "new_correct": new_correct
        })

    # Resume final
    print("\n" + "="*80)
    print("[RESUME FINAL]")
    print("="*80)

    if results:
        old_correct_count = sum(1 for r in results if r["old_correct"])
        new_correct_count = sum(1 for r in results if r["new_correct"])

        print(f"\n   Ancienne logique: {old_correct_count}/{len(results)} decisions correctes ({100*old_correct_count/len(results):.0f}%)")
        print(f"   Nouvelle logique: {new_correct_count}/{len(results)} decisions correctes ({100*new_correct_count/len(results):.0f}%)")

        improvement = new_correct_count - old_correct_count
        print(f"\n   [AMELIORATION]: {improvement:+d} decisions correctes")

        # Calculer P&L evite
        losses_blocked_new = sum(
            abs(r["trade"]["pnl"])
            for r in results
            if r["trade"]["result"] == "LOSS" and not r["new_allowed"]
        )
        losses_blocked_old = sum(
            abs(r["trade"]["pnl"])
            for r in results
            if r["trade"]["result"] == "LOSS" and not r["old_allowed"]
        )

        print(f"\n   [$$] Pertes evitees (ancienne): ${losses_blocked_old}")
        print(f"   [$$] Pertes evitees (nouvelle): ${losses_blocked_new}")
        print(f"   [$$] Gain differentiel: ${losses_blocked_new - losses_blocked_old}")


if __name__ == "__main__":
    run_test()
