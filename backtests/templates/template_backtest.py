"""
📊 TEMPLATE BACKTEST - MIA IA Trading System
=============================================

🎯 INSTRUCTIONS:
1. Copier ce fichier dans un nouveau dossier YYYY-MM-DD_nom_test/
2. Renommer en backtest.py
3. Modifier les paramètres TEST_* ci-dessous
4. Exécuter:
   - TEST:  python backtest.py              (échantillon rapide)
   - FULL:  python backtest.py --full       (toutes les données)

Date création: YYYY-MM-DD
Auteur: [Votre nom]
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# Ajouter les paths du projet
PROJECT_ROOT = Path(__file__).parent.parent.parent  # D:\MIA_IA_system
BACKTESTS_ROOT = Path(__file__).parent.parent       # D:\MIA_IA_system\BACKTESTS
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(BACKTESTS_ROOT))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Vérifier tqdm
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("⚠️ tqdm non installé. pip install tqdm pour une meilleure barre de progression")

# Import config partagée
from config.backtest_config import (
    SYMBOLS, TRADING_SESSIONS,
    MIN_TOTAL_CONFIDENCE, MIN_LAYER_CONFIDENCE,
    MAX_DISTANCE_TO_LEVEL, TP_SL_CONFIG, TICK_VALUES, TICK_SIZES,
    COOLDOWN_MS, MAX_TRADE_DURATION_MS, MAX_SNAPSHOTS_LOOKAHEAD,
    MLScores, Signal, TradeResult, BacktestStats,
    get_session, get_distance_to_level, load_snapshots
)

# ============================================================================
# 🎯 CONFIGURATION DU TEST (À MODIFIER)
# ============================================================================

TEST_NAME = "Nom du test"
TEST_DESCRIPTION = """
Description détaillée de ce que ce backtest teste.
Quelle hypothèse on veut valider ?
"""

# Période à tester (format YYYYMMDD)
DATE_RANGE = [
    "20251202",
    "20251203",
    "20251204",
    "20251205",
]

# Mois des données
DATA_MONTH = "DECEMBRE"
DATA_YEAR = 2025

# Symboles à tester (utiliser SYMBOLS pour tous)
TEST_SYMBOLS = SYMBOLS  # ou ['ES'] pour un seul

# ============================================================================
# 🧪 CONFIGURATION MODE TEST (échantillon)
# ============================================================================

# Nombre de snapshots max en mode test (pour validation rapide)
TEST_SAMPLE_SIZE = 5000  # ~2-3 minutes de données
TEST_DATES = 1  # Nombre de jours en mode test

# ============================================================================
# 🔧 PARAMÈTRES CUSTOM À TESTER (À MODIFIER)
# ============================================================================

# Exemple: tester différentes valeurs d'un paramètre
CUSTOM_PARAMS = {
    'param_a': 0.10,  # Valeur à tester
    'param_b': 0.20,  # Autre valeur
}

# Définir les variantes à comparer
VARIANTS = [
    {"name": "BASELINE", "use_custom_filter": False},
    {"name": "AVEC_FILTRE", "use_custom_filter": True},
]

# ============================================================================
# 📊 BARRE DE PROGRESSION
# ============================================================================

class ProgressBar:
    """Barre de progression compatible avec/sans tqdm"""

    def __init__(self, total: int, desc: str = "", use_tqdm: bool = True):
        self.total = max(total, 1)
        self.current = 0
        self.desc = desc
        self.start = time.time()
        self.use_tqdm = use_tqdm and HAS_TQDM

        if self.use_tqdm:
            self.pbar = tqdm(
                total=self.total,
                desc=desc,
                unit="snap",
                bar_format="{l_bar}{bar:40}{r_bar}{bar:-10b}",
                colour="green"
            )
        else:
            self._print_bar()

    def update(self, n: int = 1):
        self.current += n
        if self.use_tqdm:
            self.pbar.update(n)
        else:
            self._print_bar()

    def _print_bar(self):
        pct = self.current / self.total
        bar = "█" * int(40 * pct) + "░" * (40 - int(40 * pct))
        elapsed = time.time() - self.start
        if self.current > 0:
            eta = elapsed / self.current * (self.total - self.current)
        else:
            eta = 0
        sys.stdout.write(f"\r{self.desc} |{bar}| {self.current:,}/{self.total:,} [{elapsed:.0f}s<{eta:.0f}s]")
        sys.stdout.flush()

    def close(self):
        if self.use_tqdm:
            self.pbar.close()
        else:
            elapsed = time.time() - self.start
            print(f" ✅ {elapsed:.1f}s")

    def set_postfix(self, **kwargs):
        """Affiche des infos supplémentaires (trades, wins, etc.)"""
        if self.use_tqdm:
            self.pbar.set_postfix(**kwargs)


# ============================================================================
# 📊 LOGIQUE DU BACKTEST
# ============================================================================

def calculate_ml_scores(snap: Dict, symbol: str) -> MLScores:
    """Calcule les scores ML (adapter si besoin)"""
    l1 = snap.get('layer1_score') or snap.get('menthorq_score', 0)
    l2 = snap.get('layer2_score') or snap.get('orderflow_score', 0)
    l3 = snap.get('layer3_score') or snap.get('context_score', 0)

    # Si pas de scores pré-calculés, approximer
    if l1 == 0 and l2 == 0 and l3 == 0:
        mid = snap.get('mid', 0)
        dist, _ = get_distance_to_level(snap, mid, symbol)
        l1 = max(0, min(1, 1 - dist / 100)) if dist < 9999 else 0.2

        delta = abs(snap.get('delta', 0))
        pressure = snap.get('pressure_strength', 0)
        l2 = max(0, min(1, delta / 500 + pressure * 0.5))

        vwap = snap.get('vwap')
        if vwap and mid:
            vwap_dist = abs(mid - vwap) / TICK_SIZES.get(symbol, 0.25)
            l3 = max(0, min(1, 1 - vwap_dist / 50))
        else:
            l3 = 0.3

    total = l1 * 0.5 + l2 * 0.3 + l3 * 0.2
    return MLScores(layer1=l1, layer2=l2, layer3=l3, total=total)


def validate_signal(snap: Dict, symbol: str, use_custom_filter: bool) -> Tuple[Optional[Signal], str]:
    """
    Valide un signal avec tous les filtres production.

    ⚠️ MODIFIER CETTE FONCTION pour ajouter votre filtre custom
    """
    ts = snap.get('t_ms', 0)
    mid = snap.get('mid', 0)
    delta = snap.get('delta', 0)

    if not ts or not mid:
        return None, "no_price"

    # 1. FILTRE SESSION
    in_session, session = get_session(ts)
    if not in_session:
        return None, "out_of_session"

    # 2. FILTRE DIRECTION
    if delta == 0:
        return None, "delta_zero"
    direction = "LONG" if delta > 0 else "SHORT"

    # 3. FILTRE ML SCORES
    ml_scores = calculate_ml_scores(snap, symbol)
    ml_ok, ml_reason = ml_scores.meets_thresholds(symbol)
    if not ml_ok:
        return None, f"ml_{ml_reason}"

    # 4. FILTRE DISTANCE
    distance, nearest = get_distance_to_level(snap, mid, symbol)
    max_dist = MAX_DISTANCE_TO_LEVEL.get(symbol, 20)
    if distance > max_dist:
        return None, f"distance_{distance:.0f}t"

    # 5. 🆕 FILTRE CUSTOM (À MODIFIER)
    if use_custom_filter:
        # Exemple: filtrer sur pressure_strength
        pressure = snap.get('pressure_strength', 0)
        min_pressure = CUSTOM_PARAMS.get('param_a', 0.10)
        if pressure < min_pressure:
            return None, f"custom_filter"

    return Signal(
        timestamp=ts,
        symbol=symbol,
        direction=direction,
        price=mid,
        session=session,
        ml_scores=ml_scores,
        pressure_strength=snap.get('pressure_strength', 0),
        distance_to_level=distance,
        nearest_level=nearest,
        delta=delta
    ), "OK"


def simulate_trade(signal: Signal, subsequent: List[Dict]) -> TradeResult:
    """Simule un trade avec TP/SL"""
    cfg = TP_SL_CONFIG.get(signal.symbol, TP_SL_CONFIG['ES'])
    tv = TICK_VALUES.get(signal.symbol, 12.50)
    ts = TICK_SIZES.get(signal.symbol, 0.25)

    if signal.direction == "LONG":
        tp = signal.price + cfg['tp_ticks'] * ts
        sl = signal.price - cfg['sl_ticks'] * ts
    else:
        tp = signal.price - cfg['tp_ticks'] * ts
        sl = signal.price + cfg['sl_ticks'] * ts

    for snap in subsequent[:MAX_SNAPSHOTS_LOOKAHEAD]:
        if snap.get('t_ms', 0) - signal.timestamp > MAX_TRADE_DURATION_MS:
            break

        high = snap.get('high', snap.get('mid', 0))
        low = snap.get('low', snap.get('mid', 0))

        if signal.direction == "LONG":
            if high >= tp:
                return TradeResult(signal, "WIN", cfg['tp_ticks'], cfg['tp_ticks'] * tv, "TP_HIT")
            if low <= sl:
                return TradeResult(signal, "LOSS", -cfg['sl_ticks'], -cfg['sl_ticks'] * tv, "SL_HIT")
        else:
            if low <= tp:
                return TradeResult(signal, "WIN", cfg['tp_ticks'], cfg['tp_ticks'] * tv, "TP_HIT")
            if high >= sl:
                return TradeResult(signal, "LOSS", -cfg['sl_ticks'], -cfg['sl_ticks'] * tv, "SL_HIT")

    return TradeResult(signal, "BE", 0, 0, "TIMEOUT")


def run_backtest(all_data: Dict, use_custom_filter: bool, variant_name: str, show_progress: bool = True) -> BacktestStats:
    """Exécute le backtest complet avec barre de progression"""
    stats = BacktestStats()

    # Compter total snapshots
    total_snaps = sum(len(snaps) for sym_data in all_data.values() for _, snaps in sym_data)

    # Barre de progression
    pbar = ProgressBar(total_snaps, f"🔄 {variant_name}", use_tqdm=show_progress) if show_progress else None

    for symbol in TEST_SYMBOLS:
        last_trade_time = 0

        for date_str, snaps in all_data.get(symbol, []):
            for i, snap in enumerate(snaps):
                stats.signals_total += 1

                signal, reason = validate_signal(snap, symbol, use_custom_filter)

                if signal is None:
                    if "session" not in reason:
                        stats.signals_in_session += 1
                    if "ml_" in reason:
                        stats.rejected_ml += 1
                    elif "distance" in reason:
                        stats.rejected_distance += 1
                    elif "custom" in reason:
                        stats.rejected_pressure += 1

                    if pbar:
                        pbar.update(1)
                    continue

                stats.signals_in_session += 1

                # Cooldown
                if signal.timestamp - last_trade_time < COOLDOWN_MS:
                    stats.rejected_cooldown += 1
                    if pbar:
                        pbar.update(1)
                    continue

                last_trade_time = signal.timestamp

                # Simuler trade
                subsequent = snaps[i+1:i+1+MAX_SNAPSHOTS_LOOKAHEAD]
                trade = simulate_trade(signal, subsequent)

                # Stats
                stats.trades_executed += 1
                stats.pnl_total += trade.pnl_usd

                if trade.result == "WIN":
                    stats.wins += 1
                elif trade.result == "LOSS":
                    stats.losses += 1
                else:
                    stats.be += 1

                # Par session
                stats.by_session[signal.session]["trades"] += 1
                stats.by_session[signal.session]["pnl"] += trade.pnl_usd
                if trade.result == "WIN":
                    stats.by_session[signal.session]["wins"] += 1

                # Par symbole
                stats.by_symbol[symbol]["trades"] += 1
                stats.by_symbol[symbol]["pnl"] += trade.pnl_usd
                if trade.result == "WIN":
                    stats.by_symbol[symbol]["wins"] += 1

                # Par date
                stats.by_date[date_str]["trades"] += 1
                stats.by_date[date_str]["pnl"] += trade.pnl_usd
                if trade.result == "WIN":
                    stats.by_date[date_str]["wins"] += 1

                # Mettre à jour la barre avec stats
                if pbar:
                    pbar.set_postfix(trades=stats.trades_executed, wins=stats.wins, pnl=f"${stats.pnl_total:,.0f}")
                    pbar.update(1)

    if pbar:
        pbar.close()

    return stats


def print_results(results: Dict[str, BacktestStats], is_test_mode: bool = False):
    """Affiche les résultats comparatifs"""
    mode_label = "🧪 TEST" if is_test_mode else "📊 COMPLET"

    print("\n" + "="*100)
    print(f"{mode_label} RÉSULTATS: {TEST_NAME}")
    print("="*100)

    print(f"\n{'Variante':<20} {'Trades':<10} {'Wins':<10} {'Losses':<10} {'WR %':<10} {'P&L':<15}")
    print("-"*75)

    for name, stats in results.items():
        wr = stats.wins / max(stats.trades_executed, 1) * 100
        print(f"{name:<20} {stats.trades_executed:<10} {stats.wins:<10} {stats.losses:<10} {wr:<10.1f} ${stats.pnl_total:>12,.2f}")

    # Comparaison
    if len(results) >= 2:
        names = list(results.keys())
        baseline = results[names[0]]
        test = results[names[1]]

        diff_pnl = test.pnl_total - baseline.pnl_total
        diff_wr = test.win_rate - baseline.win_rate

        print("\n" + "-"*75)
        print(f"{'DIFFÉRENCE':<20} {test.trades_executed - baseline.trades_executed:+d}{'':<9} {test.wins - baseline.wins:+d}{'':<9} {test.losses - baseline.losses:+d}{'':<9} {diff_wr:+.1f}%{'':<5} ${diff_pnl:+>12,.2f}")

        print("\n" + "="*100)
        print("🏆 VERDICT")
        print("="*100)

        if diff_pnl > 0:
            print(f"\n✅ {names[1]} est MEILLEUR:")
            print(f"   • P&L: +${diff_pnl:,.2f}")
            print(f"   • Win Rate: +{diff_wr:.1f}%")
        elif diff_pnl < 0:
            print(f"\n❌ {names[1]} est MOINS BON:")
            print(f"   • P&L: ${diff_pnl:,.2f}")
            print(f"   • Win Rate: {diff_wr:.1f}%")
        else:
            print(f"\n➖ Résultats IDENTIQUES")

    if is_test_mode:
        print("\n" + "="*100)
        print("⚠️  MODE TEST - Échantillon limité")
        print("    Pour le backtest complet: python backtest.py --full")
        print("="*100)


def save_results(results: Dict[str, BacktestStats], is_test_mode: bool = False):
    """Sauvegarde les résultats en JSON"""
    output = {
        "test_name": TEST_NAME,
        "test_date": datetime.now().isoformat(),
        "mode": "TEST" if is_test_mode else "FULL",
        "date_range": DATE_RANGE,
        "custom_params": CUSTOM_PARAMS,
        "results": {}
    }

    for name, stats in results.items():
        output["results"][name] = {
            "trades": stats.trades_executed,
            "wins": stats.wins,
            "losses": stats.losses,
            "be": stats.be,
            "win_rate": stats.win_rate,
            "pnl_total": stats.pnl_total,
            "by_session": dict(stats.by_session),
            "by_date": dict(stats.by_date)
        }

    suffix = "_test" if is_test_mode else ""
    output_path = Path(__file__).parent / f"results{suffix}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n💾 Résultats sauvegardés: {output_path}")


# ============================================================================
# 🚀 MAIN
# ============================================================================

def main():
    # Parser arguments
    parser = argparse.ArgumentParser(description=f"Backtest: {TEST_NAME}")
    parser.add_argument('--full', action='store_true', help='Lancer le backtest complet (toutes les données)')
    parser.add_argument('--no-progress', action='store_true', help='Désactiver la barre de progression')
    args = parser.parse_args()

    is_test_mode = not args.full
    show_progress = not args.no_progress

    # Header
    mode_emoji = "🧪" if is_test_mode else "📊"
    mode_label = "MODE TEST (échantillon)" if is_test_mode else "MODE COMPLET"

    print("="*100)
    print(f"{mode_emoji} BACKTEST: {TEST_NAME}")
    print(f"   {mode_label}")
    print("="*100)
    print(f"\n{TEST_DESCRIPTION}")

    # Déterminer les dates à utiliser
    dates_to_use = DATE_RANGE[:TEST_DATES] if is_test_mode else DATE_RANGE

    print(f"\n📅 Période: {dates_to_use[0]} → {dates_to_use[-1]} ({len(dates_to_use)} jour{'s' if len(dates_to_use) > 1 else ''})")
    print(f"📊 Symboles: {TEST_SYMBOLS}")
    print(f"⚙️  Params custom: {CUSTOM_PARAMS}")

    if is_test_mode:
        print(f"\n⚠️  MODE TEST: {TEST_SAMPLE_SIZE:,} snapshots max par symbole")
        print(f"    Pour le backtest complet: python {Path(__file__).name} --full")

    # Charger données
    print(f"\n📥 Chargement des données...")
    all_data = {s: [] for s in TEST_SYMBOLS}
    total_snaps = 0

    pbar = ProgressBar(len(dates_to_use) * len(TEST_SYMBOLS), "📂 Load", use_tqdm=show_progress)

    for date in dates_to_use:
        for symbol in TEST_SYMBOLS:
            snaps = load_snapshots(date, symbol, DATA_MONTH, DATA_YEAR)

            # Limiter en mode test
            if is_test_mode and len(snaps) > TEST_SAMPLE_SIZE:
                snaps = snaps[:TEST_SAMPLE_SIZE]

            if snaps:
                all_data[symbol].append((date, snaps))
                total_snaps += len(snaps)

            pbar.update(1)

    pbar.close()

    print(f"   Total: {total_snaps:,} snapshots")

    if total_snaps == 0:
        print("❌ Aucune donnée trouvée!")
        return

    # =========================================
    # 🧪 VALIDATION RAPIDE (mode test)
    # =========================================
    if is_test_mode:
        print("\n" + "="*100)
        print("🧪 VALIDATION SUR ÉCHANTILLON")
        print("="*100)

    # Exécuter les variantes
    results = {}
    for variant in VARIANTS:
        stats = run_backtest(all_data, variant['use_custom_filter'], variant['name'], show_progress)
        results[variant['name']] = stats

    # Afficher et sauvegarder
    print_results(results, is_test_mode)
    save_results(results, is_test_mode)

    # =========================================
    # 🚀 PROCHAINES ÉTAPES
    # =========================================
    if is_test_mode:
        print("\n" + "="*100)
        print("✅ Test terminé avec succès!")
        print("="*100)
        print("\n🚀 Prochaine étape - Backtest COMPLET:")
        print(f"   python {Path(__file__).name} --full")
    else:
        print("\n" + "="*100)
        print("📋 PROCHAINES ÉTAPES")
        print("="*100)
        print("\n1. 📄 Créer le README.md avec les résultats")
        print("2. 👤 VALIDER les résultats (c'est TOI qui décide!)")
        print("3. ✅ Si approuvé → Implémenter manuellement en production")
        print("4. ❌ Si rejeté  → Archiver et passer au prochain test")
        print("\n⚠️  AUCUNE implémentation automatique - Ta validation est requise!")

    print("\n" + "="*100)


if __name__ == "__main__":
    main()
