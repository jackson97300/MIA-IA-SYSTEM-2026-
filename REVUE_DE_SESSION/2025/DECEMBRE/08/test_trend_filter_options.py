#!/usr/bin/env python3
"""
TEST DES OPTIONS DE RENFORCEMENT DU FILTRE TENDANCE
====================================================

Teste 3 options sur les trades réels du 08/12/2025:
- Option A: VWAP Distance Filter
- Option B: Cooldown Tendance (Mémoire)
- Option A+B: Combinaison

Date: 08/12/2025
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════════════════════
# DONNÉES RÉELLES DES TRADES DU 08/12/2025
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Trade:
    time: str
    symbol: str
    direction: str
    pnl: float
    vwap_distance_ticks: float  # Négatif = sous VWAP
    hvl_distance_ticks: float   # Négatif = sous HVL
    previous_trend: str  # Tendance 10-15 min avant
    result: str  # WIN ou LOSS

# Trades problématiques du soir (20:38, 21:16)
PROBLEM_TRADES = [
    Trade(
        time="20:38",
        symbol="ES",
        direction="LONG",
        pnl=-256.50,
        vwap_distance_ticks=-140,  # 140 ticks SOUS le VWAP!
        hvl_distance_ticks=-10,    # 10 ticks sous HVL
        previous_trend="BEARISH",  # Était BEARISH à 20:28
        result="LOSS"
    ),
    Trade(
        time="21:16",
        symbol="ES",
        direction="LONG",
        pnl=-256.50,
        vwap_distance_ticks=-150,  # Encore plus loin sous VWAP
        hvl_distance_ticks=-5,     # Proche du HVL
        previous_trend="BEARISH",  # Toujours BEARISH
        result="LOSS"
    ),
]

# Trades gagnants de l'après-midi (pour vérifier qu'on ne les bloque pas)
GOOD_TRADES = [
    Trade(
        time="15:50",
        symbol="ES",
        direction="LONG",
        pnl=+6.00,
        vwap_distance_ticks=-30,   # 30 ticks sous VWAP (acceptable)
        hvl_distance_ticks=+5,     # Au-dessus HVL
        previous_trend="NEUTRAL",
        result="WIN"
    ),
    Trade(
        time="16:05",
        symbol="ES",
        direction="LONG",
        pnl=+6.00,
        vwap_distance_ticks=-25,
        hvl_distance_ticks=+8,
        previous_trend="NEUTRAL",
        result="WIN"
    ),
    Trade(
        time="16:29",
        symbol="ES",
        direction="LONG",
        pnl=+31.50,
        vwap_distance_ticks=-35,
        hvl_distance_ticks=+10,
        previous_trend="NEUTRAL",
        result="WIN"
    ),
    Trade(
        time="16:39",
        symbol="ES",
        direction="SHORT",  # Ce SHORT a gagné!
        pnl=+50.00,
        vwap_distance_ticks=-40,
        hvl_distance_ticks=+5,
        previous_trend="NEUTRAL",
        result="WIN"
    ),
]

ALL_TRADES = PROBLEM_TRADES + GOOD_TRADES

# ═══════════════════════════════════════════════════════════════════════════════
# OPTION A: VWAP DISTANCE FILTER
# ═══════════════════════════════════════════════════════════════════════════════

class OptionA_VWAPDistanceFilter:
    """
    Bloque les trades si le prix est trop loin du VWAP dans la direction opposée.

    Règle:
    - LONG bloqué si VWAP distance < -50 ticks (prix trop bas)
    - SHORT bloqué si VWAP distance > +50 ticks (prix trop haut)
    """

    def __init__(self, max_distance_ticks: int = 50):
        self.max_distance = max_distance_ticks
        self.name = f"Option A: VWAP Distance (max={max_distance_ticks}t)"

    def should_allow(self, trade: Trade) -> Tuple[bool, str]:
        if trade.direction == "LONG" and trade.vwap_distance_ticks < -self.max_distance:
            return False, f"❌ LONG bloqué - Prix {abs(trade.vwap_distance_ticks):.0f}t sous VWAP (max={self.max_distance}t)"

        if trade.direction == "SHORT" and trade.vwap_distance_ticks > self.max_distance:
            return False, f"❌ SHORT bloqué - Prix {trade.vwap_distance_ticks:.0f}t au-dessus VWAP (max={self.max_distance}t)"

        return True, "✅ Autorisé"

# ═══════════════════════════════════════════════════════════════════════════════
# OPTION B: COOLDOWN TENDANCE (MÉMOIRE)
# ═══════════════════════════════════════════════════════════════════════════════

class OptionB_TrendCooldown:
    """
    Bloque les trades contre-tendance si la tendance a changé récemment.

    Règle:
    - Si tendance était BEARISH il y a < 15min → Pas de LONG
    - Si tendance était BULLISH il y a < 15min → Pas de SHORT
    """

    def __init__(self, cooldown_minutes: int = 15):
        self.cooldown_minutes = cooldown_minutes
        self.name = f"Option B: Trend Cooldown ({cooldown_minutes}min)"

    def should_allow(self, trade: Trade) -> Tuple[bool, str]:
        # Si la tendance précédente était BEARISH et on veut LONG
        if trade.previous_trend == "BEARISH" and trade.direction == "LONG":
            return False, f"❌ LONG bloqué - Tendance était BEARISH il y a < {self.cooldown_minutes}min"

        # Si la tendance précédente était BULLISH et on veut SHORT
        if trade.previous_trend == "BULLISH" and trade.direction == "SHORT":
            return False, f"❌ SHORT bloqué - Tendance était BULLISH il y a < {self.cooldown_minutes}min"

        return True, "✅ Autorisé"

# ═══════════════════════════════════════════════════════════════════════════════
# OPTION A+B: COMBINAISON
# ═══════════════════════════════════════════════════════════════════════════════

class OptionAB_Combined:
    """
    Combine les deux filtres: VWAP Distance + Trend Cooldown

    Le trade est bloqué si l'une OU l'autre condition est remplie.
    """

    def __init__(self, max_vwap_distance: int = 50, cooldown_minutes: int = 15):
        self.filter_a = OptionA_VWAPDistanceFilter(max_vwap_distance)
        self.filter_b = OptionB_TrendCooldown(cooldown_minutes)
        self.name = f"Option A+B: VWAP({max_vwap_distance}t) + Cooldown({cooldown_minutes}min)"

    def should_allow(self, trade: Trade) -> Tuple[bool, str]:
        # Vérifier Option A
        allowed_a, reason_a = self.filter_a.should_allow(trade)
        if not allowed_a:
            return False, reason_a

        # Vérifier Option B
        allowed_b, reason_b = self.filter_b.should_allow(trade)
        if not allowed_b:
            return False, reason_b

        return True, "✅ Autorisé (passe A et B)"

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTION DE TEST
# ═══════════════════════════════════════════════════════════════════════════════

def test_filter(filter_instance, trades: List[Trade]) -> Dict:
    """Teste un filtre sur une liste de trades"""

    results = {
        'name': filter_instance.name,
        'total_trades': len(trades),
        'blocked': 0,
        'allowed': 0,
        'blocked_losses': 0,  # Pertes évitées
        'blocked_wins': 0,    # Gains perdus
        'pnl_saved': 0.0,
        'pnl_lost': 0.0,
        'net_impact': 0.0,
        'details': []
    }

    for trade in trades:
        allowed, reason = filter_instance.should_allow(trade)

        detail = {
            'time': trade.time,
            'direction': trade.direction,
            'pnl': trade.pnl,
            'allowed': allowed,
            'reason': reason,
            'result': trade.result
        }
        results['details'].append(detail)

        if allowed:
            results['allowed'] += 1
        else:
            results['blocked'] += 1
            if trade.result == "LOSS":
                results['blocked_losses'] += 1
                results['pnl_saved'] += abs(trade.pnl)  # Perte évitée = positif
            else:
                results['blocked_wins'] += 1
                results['pnl_lost'] += trade.pnl  # Gain perdu = négatif

    results['net_impact'] = results['pnl_saved'] - results['pnl_lost']

    return results

def print_results(results: Dict):
    """Affiche les résultats d'un test"""

    print(f"\n{'='*70}")
    print(f"📊 {results['name']}")
    print(f"{'='*70}")

    print(f"\n📈 STATISTIQUES:")
    print(f"   Total trades testés: {results['total_trades']}")
    print(f"   ✅ Autorisés: {results['allowed']}")
    print(f"   ❌ Bloqués: {results['blocked']}")

    print(f"\n💰 IMPACT FINANCIER:")
    print(f"   🛡️ Pertes évitées: {results['blocked_losses']} trades = +${results['pnl_saved']:.2f}")
    print(f"   ⚠️ Gains perdus: {results['blocked_wins']} trades = -${results['pnl_lost']:.2f}")
    print(f"   📊 IMPACT NET: ${results['net_impact']:+.2f}")

    print(f"\n📋 DÉTAILS PAR TRADE:")
    for d in results['details']:
        status = "✅" if d['allowed'] else "❌"
        print(f"   {d['time']} {d['direction']:5} ${d['pnl']:+8.2f} ({d['result']}) → {status} {d['reason']}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN - EXÉCUTION DES TESTS
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 TEST DES OPTIONS DE RENFORCEMENT DU FILTRE TENDANCE")
    print("="*70)
    print(f"\n📅 Données: Trades du 08/12/2025")
    print(f"   Trades problématiques (soir): {len(PROBLEM_TRADES)}")
    print(f"   Trades gagnants (après-midi): {len(GOOD_TRADES)}")
    print(f"   Total: {len(ALL_TRADES)}")

    # ═══════════════════════════════════════════════════════════════════════════
    # TEST OPTION A
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n\n" + "🔷"*35)
    print("🔷 TEST OPTION A: VWAP DISTANCE FILTER")
    print("🔷"*35)

    # Test avec différents seuils
    for max_dist in [50, 75, 100]:
        filter_a = OptionA_VWAPDistanceFilter(max_distance_ticks=max_dist)
        results_a = test_filter(filter_a, ALL_TRADES)
        print_results(results_a)

    # ═══════════════════════════════════════════════════════════════════════════
    # TEST OPTION B
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n\n" + "🔶"*35)
    print("🔶 TEST OPTION B: TREND COOLDOWN")
    print("🔶"*35)

    # Test avec différents cooldowns
    for cooldown in [10, 15, 20]:
        filter_b = OptionB_TrendCooldown(cooldown_minutes=cooldown)
        results_b = test_filter(filter_b, ALL_TRADES)
        print_results(results_b)

    # ═══════════════════════════════════════════════════════════════════════════
    # TEST OPTION A+B
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n\n" + "🔴"*35)
    print("🔴 TEST OPTION A+B: COMBINAISON")
    print("🔴"*35)

    # Meilleure combinaison
    filter_ab = OptionAB_Combined(max_vwap_distance=50, cooldown_minutes=15)
    results_ab = test_filter(filter_ab, ALL_TRADES)
    print_results(results_ab)

    # Variante plus stricte
    filter_ab_strict = OptionAB_Combined(max_vwap_distance=40, cooldown_minutes=10)
    results_ab_strict = test_filter(filter_ab_strict, ALL_TRADES)
    print_results(results_ab_strict)

    # ═══════════════════════════════════════════════════════════════════════════
    # COMPARAISON FINALE
    # ═══════════════════════════════════════════════════════════════════════════

    print("\n\n" + "="*70)
    print("📊 COMPARAISON FINALE")
    print("="*70)

    # Recalculer avec les meilleurs paramètres
    best_a = test_filter(OptionA_VWAPDistanceFilter(50), ALL_TRADES)
    best_b = test_filter(OptionB_TrendCooldown(15), ALL_TRADES)
    best_ab = test_filter(OptionAB_Combined(50, 15), ALL_TRADES)

    print(f"\n{'Option':<40} | {'Bloqués':<10} | {'Pertes évitées':<15} | {'Gains perdus':<15} | {'IMPACT NET':<12}")
    print("-"*100)
    print(f"{'Option A: VWAP Distance (50t)':<40} | {best_a['blocked']:<10} | ${best_a['pnl_saved']:<14.2f} | ${best_a['pnl_lost']:<14.2f} | ${best_a['net_impact']:+.2f}")
    print(f"{'Option B: Trend Cooldown (15min)':<40} | {best_b['blocked']:<10} | ${best_b['pnl_saved']:<14.2f} | ${best_b['pnl_lost']:<14.2f} | ${best_b['net_impact']:+.2f}")
    print(f"{'Option A+B: Combinaison':<40} | {best_ab['blocked']:<10} | ${best_ab['pnl_saved']:<14.2f} | ${best_ab['pnl_lost']:<14.2f} | ${best_ab['net_impact']:+.2f}")

    print("\n" + "="*70)
    print("✅ RECOMMANDATION")
    print("="*70)

    # Trouver la meilleure option
    options = [
        ("Option A", best_a['net_impact']),
        ("Option B", best_b['net_impact']),
        ("Option A+B", best_ab['net_impact']),
    ]
    best_option = max(options, key=lambda x: x[1])

    print(f"\n🏆 MEILLEURE OPTION: {best_option[0]}")
    print(f"   Impact net: ${best_option[1]:+.2f}")

    if best_option[0] == "Option A":
        print(f"\n   → Implémenter VWAP Distance Filter (max 50 ticks)")
    elif best_option[0] == "Option B":
        print(f"\n   → Implémenter Trend Cooldown (15 minutes)")
    else:
        print(f"\n   → Implémenter la combinaison A+B")

    print("\n" + "="*70)

