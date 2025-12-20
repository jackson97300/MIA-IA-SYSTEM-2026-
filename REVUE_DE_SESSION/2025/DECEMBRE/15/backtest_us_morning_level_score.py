"""
═══════════════════════════════════════════════════════════════════════════════
    BACKTEST COMPARATIF: US_MORNING_ES - min_level_score 3 vs 2

    OBJECTIF: Tester si accepter les niveaux MOYENS (score=2) améliore les résultats

    COMPARAISON:
    - CONFIG A (actuel): min_level_score=3, max_distance=5t → Niveaux FORTS uniquement
    - CONFIG B (test):   min_level_score=2, max_distance=12t → Niveaux FORTS + MOYENS

    Date: 15 Décembre 2025
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

# ═══════════════════════════════════════════════════════════════════════════════
#                           CONFIGURATION DES TESTS
# ═══════════════════════════════════════════════════════════════════════════════

# Config A: Actuelle (STRICT - FORT uniquement)
CONFIG_A = {
    'name': 'STRICT (actuel)',
    'max_distance': 5,
    'min_level_score': 3,  # FORT uniquement
    'min_confidence': 0.60,
    'tp_ticks': 12,
    'sl_ticks': 12,
}

# Config B: Proposée (ASSOUPLIE - MOYEN+)
CONFIG_B = {
    'name': 'ASSOUPLIE (test)',
    'max_distance': 12,
    'min_level_score': 2,  # MOYEN + FORT
    'min_confidence': 0.60,
    'tp_ticks': 12,
    'sl_ticks': 12,
}

# Classification des niveaux
LEVEL_SCORES = {
    # FORT (score 3)
    'gex_1': 3, 'gex_2': 3, 'hvl': 3, 'gamma_wall_level': 3, 'vwap': 3,
    # MOYEN (score 2)
    'gex_3': 2, 'gex_4': 2, 'gex_5': 2, 'hvl_0dte': 2,
    'call_resistance': 2, 'put_support': 2,
    'blind_spot_0': 2, 'blind_spot_1': 2,
    # FAIBLE (score 1)
    'vwap_upper': 1, 'vwap_lower': 1,
    'blind_spot_2': 1, 'blind_spot_3': 1, 'blind_spot_4': 1,
}

TICK_SIZE = 0.25
TICK_VALUE = 12.50  # ES

# Sessions US_MORNING: 15h50 - 17h00 Paris
US_MORNING_START = (15, 50)
US_MORNING_END = (17, 0)

# ═══════════════════════════════════════════════════════════════════════════════
#                           FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════════════════════════════

def get_level_score(level_name: str) -> int:
    """Retourne le score d'un niveau."""
    base = level_name.lower()
    if base in LEVEL_SCORES:
        return LEVEL_SCORES[base]

    # GEX > 5 = score 1
    if base.startswith('gex_'):
        try:
            num = int(base.split('_')[1])
            return 3 if num <= 2 else (2 if num <= 5 else 1)
        except:
            return 1

    # Blind spots > 1 = score 1
    if base.startswith('blind_spot_'):
        try:
            num = int(base.split('_')[2])
            return 2 if num <= 1 else 1
        except:
            return 1

    return 0

def is_us_morning(timestamp_ms: int) -> bool:
    """Vérifie si le timestamp est dans la session US_MORNING (15h50-17h00 Paris)."""
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        time_val = dt.hour * 60 + dt.minute
        start = US_MORNING_START[0] * 60 + US_MORNING_START[1]
        end = US_MORNING_END[0] * 60 + US_MORNING_END[1]
        return start <= time_val < end
    except:
        return False

def extract_levels_from_snapshot(snapshot: dict) -> list:
    """Extrait tous les niveaux MenthorQ du snapshot."""
    levels = []

    # Niveaux directs
    level_keys = [
        'hvl', 'vwap', 'gamma_wall_level',
        'gex_1', 'gex_2', 'gex_3', 'gex_4', 'gex_5',
        'call_resistance', 'put_support',
        'hvl_0dte', 'vwap_upper', 'vwap_lower',
    ]

    for key in level_keys:
        if key in snapshot and snapshot[key]:
            try:
                price = float(snapshot[key])
                if price > 0:
                    levels.append((key, price, get_level_score(key)))
            except:
                pass

    # Blind spots (liste)
    blind_spots = snapshot.get('blind_spots', [])
    if isinstance(blind_spots, list):
        for i, bs in enumerate(blind_spots[:5]):  # Max 5
            if isinstance(bs, dict) and 'price' in bs:
                price = float(bs['price'])
                if price > 0:
                    levels.append((f'blind_spot_{i}', price, get_level_score(f'blind_spot_{i}')))
            elif isinstance(bs, (int, float)) and bs > 0:
                levels.append((f'blind_spot_{i}', float(bs), get_level_score(f'blind_spot_{i}')))

    return levels

def find_nearest_valid_level(mid_price: float, levels: list, config: dict) -> tuple:
    """
    Trouve le niveau valide le plus proche selon la config.

    Returns:
        (level_name, level_price, distance_ticks, level_score) ou None
    """
    min_score = config['min_level_score']
    max_dist = config['max_distance']

    nearest = None
    nearest_dist = 9999

    for level_name, level_price, level_score in levels:
        if level_score < min_score:
            continue

        dist_ticks = abs(mid_price - level_price) / TICK_SIZE

        if dist_ticks <= max_dist and dist_ticks < nearest_dist:
            nearest_dist = dist_ticks
            nearest = (level_name, level_price, dist_ticks, level_score)

    return nearest

def simulate_trade(entry_price: float, direction: str, tp_ticks: int, sl_ticks: int,
                   high_after: float, low_after: float) -> dict:
    """
    Simule un trade et retourne le résultat.

    Args:
        entry_price: Prix d'entrée
        direction: 'LONG' ou 'SHORT'
        tp_ticks: Take Profit en ticks
        sl_ticks: Stop Loss en ticks
        high_after: Plus haut après l'entrée
        low_after: Plus bas après l'entrée

    Returns:
        {'win': bool, 'pnl_ticks': float, 'exit_reason': str}
    """
    tp_price = entry_price + (tp_ticks * TICK_SIZE) if direction == 'LONG' else entry_price - (tp_ticks * TICK_SIZE)
    sl_price = entry_price - (sl_ticks * TICK_SIZE) if direction == 'LONG' else entry_price + (sl_ticks * TICK_SIZE)

    if direction == 'LONG':
        # Check TP hit
        if high_after >= tp_price:
            return {'win': True, 'pnl_ticks': tp_ticks, 'exit_reason': 'TP'}
        # Check SL hit
        if low_after <= sl_price:
            return {'win': False, 'pnl_ticks': -sl_ticks, 'exit_reason': 'SL'}
        # Timeout - fermeture au prix actuel
        pnl = (high_after - entry_price) / TICK_SIZE  # Approximation
        return {'win': pnl > 0, 'pnl_ticks': pnl, 'exit_reason': 'TIMEOUT'}
    else:  # SHORT
        # Check TP hit
        if low_after <= tp_price:
            return {'win': True, 'pnl_ticks': tp_ticks, 'exit_reason': 'TP'}
        # Check SL hit
        if high_after >= sl_price:
            return {'win': False, 'pnl_ticks': -sl_ticks, 'exit_reason': 'SL'}
        # Timeout
        pnl = (entry_price - low_after) / TICK_SIZE
        return {'win': pnl > 0, 'pnl_ticks': pnl, 'exit_reason': 'TIMEOUT'}

# ═══════════════════════════════════════════════════════════════════════════════
#                           BACKTEST PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

def run_backtest(config: dict, snapshots_dir: str = "snapshots") -> dict:
    """
    Exécute le backtest avec une config donnée.

    Returns:
        dict avec résultats: trades, wins, losses, pnl, etc.
    """
    results = {
        'config_name': config['name'],
        'trades': [],
        'n_trades': 0,
        'n_wins': 0,
        'n_losses': 0,
        'pnl_ticks': 0,
        'pnl_usd': 0,
        'signals_rejected': 0,
        'rejection_reasons': defaultdict(int),
        'levels_used': defaultdict(int),
    }

    # Parcourir les snapshots des derniers jours
    base_path = Path(snapshots_dir)

    # Chercher les 27 derniers jours (comme V9)
    dates_to_check = []
    for i in range(30):
        date = datetime.now() - timedelta(days=i)
        date_str = date.strftime("%Y%m%d")
        date_path = base_path / date_str
        if date_path.exists():
            dates_to_check.append(date_str)
        if len(dates_to_check) >= 27:
            break

    print(f"\n📅 Dates analysées: {len(dates_to_check)} jours")

    # Cooldown tracking
    last_trade_time = 0
    cooldown_ms = 15 * 60 * 1000  # 15 min

    for date_str in sorted(dates_to_check):
        date_path = base_path / date_str
        es_files = sorted(date_path.glob("ES_*.json"))

        # Grouper par fenêtre de temps pour simuler MFE/MAE
        snapshots_buffer = []

        for f in es_files:
            try:
                with open(f, 'r') as fp:
                    snapshot = json.load(fp)

                t_ms = snapshot.get('t_ms', 0)

                # Filtrer: US_MORNING seulement
                if not is_us_morning(t_ms):
                    continue

                mid = snapshot.get('mid', 0)
                if mid <= 0:
                    continue

                snapshots_buffer.append(snapshot)

                # Garder une fenêtre de 5 min pour calculer MFE/MAE
                if len(snapshots_buffer) > 300:  # ~5 min à 1 snapshot/sec
                    snapshots_buffer.pop(0)

                # Vérifier cooldown
                if t_ms - last_trade_time < cooldown_ms:
                    continue

                # Extraire les niveaux
                levels = extract_levels_from_snapshot(snapshot)

                if not levels:
                    results['signals_rejected'] += 1
                    results['rejection_reasons']['no_levels'] += 1
                    continue

                # Trouver le niveau valide le plus proche
                nearest = find_nearest_valid_level(mid, levels, config)

                if nearest is None:
                    results['signals_rejected'] += 1
                    results['rejection_reasons']['no_valid_level'] += 1
                    continue

                level_name, level_price, dist_ticks, level_score = nearest

                # Déterminer direction (simplifié: basé sur position vs niveau)
                # En réalité, c'est le ML 3-Layer qui décide
                # Ici on simule: si prix < niveau → LONG (rebond), si prix > niveau → SHORT
                direction = 'LONG' if mid < level_price else 'SHORT'

                # Simuler le trade avec MFE/MAE des prochains snapshots
                future_highs = [s.get('high', mid) for s in snapshots_buffer[-60:]]  # 1 min après
                future_lows = [s.get('low', mid) for s in snapshots_buffer[-60:]]

                high_after = max(future_highs) if future_highs else mid + 5 * TICK_SIZE
                low_after = min(future_lows) if future_lows else mid - 5 * TICK_SIZE

                # Simuler le trade
                trade_result = simulate_trade(
                    entry_price=mid,
                    direction=direction,
                    tp_ticks=config['tp_ticks'],
                    sl_ticks=config['sl_ticks'],
                    high_after=high_after,
                    low_after=low_after
                )

                # Enregistrer le trade
                results['n_trades'] += 1
                results['pnl_ticks'] += trade_result['pnl_ticks']
                results['levels_used'][level_name] += 1

                if trade_result['win']:
                    results['n_wins'] += 1
                else:
                    results['n_losses'] += 1

                results['trades'].append({
                    'date': date_str,
                    'time': datetime.fromtimestamp(t_ms/1000).strftime('%H:%M:%S'),
                    'mid': mid,
                    'level': level_name,
                    'level_price': level_price,
                    'level_score': level_score,
                    'dist_ticks': dist_ticks,
                    'direction': direction,
                    'pnl_ticks': trade_result['pnl_ticks'],
                    'exit_reason': trade_result['exit_reason'],
                    'win': trade_result['win'],
                })

                # Update cooldown
                last_trade_time = t_ms

            except Exception as e:
                continue

    # Calculer stats finales
    results['pnl_usd'] = results['pnl_ticks'] * TICK_VALUE
    results['winrate'] = (results['n_wins'] / results['n_trades'] * 100) if results['n_trades'] > 0 else 0

    return results

# ═══════════════════════════════════════════════════════════════════════════════
#                           MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("="*80)
    print("   BACKTEST COMPARATIF: US_MORNING_ES - min_level_score 3 vs 2")
    print("="*80)

    # Test Config A (actuelle)
    print(f"\n🔬 Test CONFIG A: {CONFIG_A['name']}")
    print(f"   max_distance={CONFIG_A['max_distance']}t, min_level_score={CONFIG_A['min_level_score']}")
    results_a = run_backtest(CONFIG_A)

    # Test Config B (proposée)
    print(f"\n🔬 Test CONFIG B: {CONFIG_B['name']}")
    print(f"   max_distance={CONFIG_B['max_distance']}t, min_level_score={CONFIG_B['min_level_score']}")
    results_b = run_backtest(CONFIG_B)

    # Afficher comparaison
    print("\n" + "="*80)
    print("   📊 RÉSULTATS COMPARATIFS")
    print("="*80)

    print(f"\n{'MÉTRIQUE':<30} {'CONFIG A (STRICT)':<20} {'CONFIG B (ASSOUPLIE)':<20} {'DIFF':<15}")
    print("-"*85)

    print(f"{'Trades':<30} {results_a['n_trades']:<20} {results_b['n_trades']:<20} {results_b['n_trades'] - results_a['n_trades']:+<15}")
    print(f"{'Wins':<30} {results_a['n_wins']:<20} {results_b['n_wins']:<20} {results_b['n_wins'] - results_a['n_wins']:+<15}")
    print(f"{'Losses':<30} {results_a['n_losses']:<20} {results_b['n_losses']:<20} {results_b['n_losses'] - results_a['n_losses']:+<15}")
    print(f"{'Win Rate':<30} {results_a['winrate']:.1f}%{'':<17} {results_b['winrate']:.1f}%{'':<17} {results_b['winrate'] - results_a['winrate']:+.1f}%")
    print(f"{'P&L (ticks)':<30} {results_a['pnl_ticks']:.1f}{'':<18} {results_b['pnl_ticks']:.1f}{'':<18} {results_b['pnl_ticks'] - results_a['pnl_ticks']:+.1f}")
    print(f"{'P&L (USD)':<30} ${results_a['pnl_usd']:,.0f}{'':<17} ${results_b['pnl_usd']:,.0f}{'':<17} ${results_b['pnl_usd'] - results_a['pnl_usd']:+,.0f}")
    print(f"{'Signaux rejetés':<30} {results_a['signals_rejected']:<20} {results_b['signals_rejected']:<20} {results_b['signals_rejected'] - results_a['signals_rejected']:+<15}")

    # Niveaux utilisés
    print("\n" + "-"*85)
    print("📍 NIVEAUX UTILISÉS:")
    print("-"*85)

    all_levels = set(results_a['levels_used'].keys()) | set(results_b['levels_used'].keys())
    for level in sorted(all_levels, key=lambda x: get_level_score(x), reverse=True):
        count_a = results_a['levels_used'].get(level, 0)
        count_b = results_b['levels_used'].get(level, 0)
        score = get_level_score(level)
        score_label = {3: 'FORT', 2: 'MOYEN', 1: 'FAIBLE'}.get(score, '?')
        print(f"  {level:<25} (score={score}/{score_label}): {count_a:<10} → {count_b:<10} ({count_b - count_a:+})")

    # Conclusion
    print("\n" + "="*80)
    print("   🎯 CONCLUSION")
    print("="*80)

    pnl_diff = results_b['pnl_usd'] - results_a['pnl_usd']
    trades_diff = results_b['n_trades'] - results_a['n_trades']

    if pnl_diff > 0 and results_b['winrate'] >= results_a['winrate'] - 5:
        print(f"\n✅ CONFIG B RECOMMANDÉE!")
        print(f"   +{trades_diff} trades, +${pnl_diff:,.0f}")
        print(f"   → Modifier US_MORNING_ES: max_distance=12, min_level_score=2")
    elif pnl_diff > 0:
        print(f"\n⚠️ CONFIG B: Plus de trades (+{trades_diff}) mais WinRate inférieur")
        print(f"   À évaluer selon risk appetite")
    else:
        print(f"\n✅ CONFIG A (actuelle) reste meilleure")
        print(f"   Garder: max_distance=5, min_level_score=3")

    print("\n" + "="*80)

    # Sauvegarder les résultats
    output = {
        'test_date': datetime.now().isoformat(),
        'config_a': CONFIG_A,
        'config_b': CONFIG_B,
        'results_a': {k: v for k, v in results_a.items() if k != 'trades'},
        'results_b': {k: v for k, v in results_b.items() if k != 'trades'},
        'conclusion': 'CONFIG_B' if pnl_diff > 0 else 'CONFIG_A',
    }

    output_path = Path(__file__).parent / "backtest_us_morning_results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n💾 Résultats sauvegardés: {output_path}")

if __name__ == "__main__":
    main()
