#!/usr/bin/env python3
"""
BACKTEST TRAILING STOP OPTIMIZATION
=====================================

Teste différentes configurations de TRAILING après BE
pour capturer plus de profit tout en protégeant.

BE fixé à 8 ticks - on optimise les paliers APRÈS.

Date: 08/12/2025
"""

import os
import json
import glob
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# TICK VALUES
# ═══════════════════════════════════════════════════════════════════════════════

TICK_VALUES = {'ES': 12.50, 'NQ': 5.00, 'RTY': 5.00}
LOGS_DIR = r"D:\MIA_IA_system\logs"

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIONS DE TRAILING À TESTER
# ═══════════════════════════════════════════════════════════════════════════════

TRAILING_CONFIGS = {
    # Config actuelle (lente)
    "ACTUEL": [
        (8, 2),    # +8t  → SL à +2t
        (15, 5),   # +15t → SL à +5t
        (20, 8),   # +20t → SL à +8t
        (25, 12),  # +25t → SL à +12t
    ],

    # Config agressive (trailing rapide)
    "AGRESSIF": [
        (8, 2),    # +8t  → SL à +2t
        (10, 4),   # +10t → SL à +4t (serré!)
        (12, 6),   # +12t → SL à +6t
        (15, 8),   # +15t → SL à +8t
        (20, 12),  # +20t → SL à +12t
    ],

    # Config modérée (équilibrée)
    "MODERE": [
        (8, 2),    # +8t  → SL à +2t
        (12, 4),   # +12t → SL à +4t
        (16, 7),   # +16t → SL à +7t
        (20, 10),  # +20t → SL à +10t
        (25, 14),  # +25t → SL à +14t
    ],

    # Config semi-agressive
    "SEMI_AGRESSIF": [
        (8, 2),    # +8t  → SL à +2t
        (11, 4),   # +11t → SL à +4t
        (14, 6),   # +14t → SL à +6t
        (17, 9),   # +17t → SL à +9t
        (20, 12),  # +20t → SL à +12t
    ],

    # Config "lock profits" (verrouille 50% du profit)
    "LOCK_50PCT": [
        (8, 2),    # +8t  → SL à +2t (25%)
        (12, 6),   # +12t → SL à +6t (50%)
        (16, 8),   # +16t → SL à +8t (50%)
        (20, 10),  # +20t → SL à +10t (50%)
        (24, 12),  # +24t → SL à +12t (50%)
    ],

    # Config PRO (utilisée par les traders institutionnels)
    "PRO": [
        (8, 2),    # BE + buffer
        (12, 5),   # 40% lock
        (15, 7),   # 47% lock
        (18, 9),   # 50% lock
        (22, 11),  # 50% lock
        (26, 14),  # 54% lock
    ],
}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeData:
    symbol: str
    mfe_ticks: float
    mae_ticks: float
    actual_pnl: float

# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTION DES TRADES
# ═══════════════════════════════════════════════════════════════════════════════

def extract_trades() -> List[TradeData]:
    """Extrait les trades avec MFE/MAE depuis les logs"""

    trades = []
    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, "__main___202512*.log")))[-5:]

    pattern = re.compile(
        r'MFE:\s*\+?([\d.]+).*MAE:\s*([+-]?\d+\.?\d*)',
        re.IGNORECASE
    )

    symbol_pattern = re.compile(r'\[(ES|NQ|RTY)\]', re.IGNORECASE)
    pnl_pattern = re.compile(r'P&L[:\s]+\$?([+-]?\d+\.?\d*)', re.IGNORECASE)

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                if 'MFE:' in line and 'MAE:' in line:
                    match = pattern.search(line)
                    if match:
                        mfe = float(match.group(1))
                        mae = abs(float(match.group(2)))

                        # Chercher le symbole dans les lignes autour
                        context = ''.join(lines[max(0,i-3):i+3])
                        sym_match = symbol_pattern.search(context)
                        symbol = sym_match.group(1).upper() if sym_match else 'ES'

                        # Chercher le P&L
                        pnl_match = pnl_pattern.search(context)
                        pnl = float(pnl_match.group(1)) if pnl_match else 0

                        tick_value = TICK_VALUES.get(symbol, 12.50)

                        trades.append(TradeData(
                            symbol=symbol,
                            mfe_ticks=mfe / tick_value,
                            mae_ticks=mae / tick_value,
                            actual_pnl=pnl
                        ))

        except Exception as e:
            pass

    return trades

# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION DU TRAILING
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trailing(trade: TradeData, levels: List[Tuple[int, int]],
                      sl_ticks: int = 20, tp_ticks: int = 30) -> Tuple[float, str, int]:
    """
    Simule un trade avec trailing progressif.

    Returns: (pnl, exit_reason, ticks_captured)
    """

    tick_value = TICK_VALUES.get(trade.symbol, 12.50)
    mfe = trade.mfe_ticks
    mae = trade.mae_ticks

    # Cas 1: SL initial touché avant tout profit significatif
    if mae >= sl_ticks and mfe < levels[0][0]:
        return -sl_ticks * tick_value, "SL_INITIAL", -sl_ticks

    # Cas 2: TP touché
    if mfe >= tp_ticks:
        return tp_ticks * tick_value, "TP_HIT", tp_ticks

    # Cas 3: Trailing - trouver le meilleur niveau atteint
    best_sl = -sl_ticks  # SL initial (négatif)
    best_level_name = "INITIAL"

    for trigger, new_sl in levels:
        if mfe >= trigger:
            best_sl = new_sl
            best_level_name = f"TRAIL_{trigger}"

    # Si on a atteint au moins le BE (premier niveau)
    if best_sl > 0:
        # Le trade a atteint un niveau de protection
        # Simulation: le prix revient et touche le trailing SL

        # Si le trade était perdant dans la réalité, on est sorti au trailing
        if trade.actual_pnl < 0:
            return best_sl * tick_value, f"TRAIL_SAVE_{best_level_name}", best_sl
        else:
            # Trade gagnant - on capture entre le SL trailing et le MFE
            # En moyenne, on capture ~70% de la distance MFE - trailing_SL
            captured = best_sl + (mfe - best_sl) * 0.5
            captured = min(captured, mfe)  # Pas plus que le MFE
            return captured * tick_value, f"TRAIL_WIN_{best_level_name}", int(captured)

    # Cas 4: Pas de trailing atteint, utiliser résultat réel
    if trade.actual_pnl > 0:
        return trade.actual_pnl, "WIN_NO_TRAIL", int(trade.actual_pnl / tick_value)
    else:
        return -sl_ticks * tick_value, "SL_NO_TRAIL", -sl_ticks

def run_trailing_backtest(trades: List[TradeData], config_name: str,
                          levels: List[Tuple[int, int]]) -> Dict:
    """Exécute le backtest pour une config de trailing"""

    results = {
        'config': config_name,
        'levels': levels,
        'total_trades': len(trades),
        'wins': 0,
        'losses': 0,
        'total_pnl': 0,
        'total_gains': 0,
        'total_losses': 0,
        'ticks_captured': [],
        'exits': {}
    }

    for trade in trades:
        pnl, exit_reason, ticks = simulate_trailing(trade, levels)

        results['total_pnl'] += pnl
        results['ticks_captured'].append(ticks)

        exit_type = exit_reason.split('_')[0]
        results['exits'][exit_type] = results['exits'].get(exit_type, 0) + 1

        if pnl > 0:
            results['wins'] += 1
            results['total_gains'] += pnl
        else:
            results['losses'] += 1
            results['total_losses'] += abs(pnl)

    # Métriques
    results['win_rate'] = results['wins'] / results['total_trades'] * 100
    results['avg_win'] = results['total_gains'] / results['wins'] if results['wins'] else 0
    results['avg_loss'] = results['total_losses'] / results['losses'] if results['losses'] else 0
    results['profit_factor'] = results['total_gains'] / results['total_losses'] if results['total_losses'] else 0
    results['avg_ticks'] = sum(results['ticks_captured']) / len(results['ticks_captured'])

    # MFE Capture Rate
    total_mfe = sum(t.mfe_ticks for t in trades)
    results['mfe_capture_rate'] = sum(max(0, t) for t in results['ticks_captured']) / total_mfe * 100 if total_mfe else 0

    return results

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*90)
    print("BACKTEST TRAILING STOP OPTIMIZATION")
    print("="*90)

    # Extraire trades
    print("\n[1/2] Extraction des trades...")
    trades = extract_trades()
    print(f"      {len(trades)} trades avec MFE/MAE extraits")

    if len(trades) < 10:
        print("\n[WARN] Pas assez de données!")
        exit()

    # Stats MFE/MAE
    avg_mfe = sum(t.mfe_ticks for t in trades) / len(trades)
    avg_mae = sum(t.mae_ticks for t in trades) / len(trades)
    print(f"      MFE moyen: {avg_mfe:.1f} ticks | MAE moyen: {avg_mae:.1f} ticks")

    # Tester chaque config
    print("\n[2/2] Test des configurations de trailing...")
    print("="*90)

    all_results = []

    for name, levels in TRAILING_CONFIGS.items():
        result = run_trailing_backtest(trades, name, levels)
        all_results.append(result)

    # Trier par P&L
    all_results.sort(key=lambda x: x['total_pnl'], reverse=True)

    # Afficher résultats
    print("\nRÉSULTATS PAR CONFIGURATION:")
    print("-"*90)
    print(f"{'Config':<15} | {'P&L':>10} | {'WR':>6} | {'Avg Win':>9} | {'Avg Loss':>9} | {'PF':>5} | {'MFE%':>6}")
    print("-"*90)

    for r in all_results:
        print(f"{r['config']:<15} | ${r['total_pnl']:>+9.2f} | {r['win_rate']:>5.1f}% | "
              f"${r['avg_win']:>8.2f} | ${r['avg_loss']:>8.2f} | "
              f"{r['profit_factor']:>4.2f} | {r['mfe_capture_rate']:>5.1f}%")

    # Détails de chaque config
    print("\n" + "="*90)
    print("DÉTAIL DES CONFIGURATIONS:")
    print("="*90)

    for r in all_results:
        print(f"\n📊 {r['config']}:")
        print(f"   Paliers: {r['levels']}")
        print(f"   P&L: ${r['total_pnl']:+.2f} | Wins: {r['wins']} | Losses: {r['losses']}")
        print(f"   Exits: {r['exits']}")

    # Meilleure config
    best = all_results[0]
    actuel = next(r for r in all_results if r['config'] == 'ACTUEL')

    print("\n" + "="*90)
    print("COMPARAISON ACTUEL vs MEILLEUR:")
    print("="*90)

    improvement = best['total_pnl'] - actuel['total_pnl']
    mfe_improvement = best['mfe_capture_rate'] - actuel['mfe_capture_rate']

    print(f"""
    CONFIGURATION ACTUELLE:
    ├─ Paliers: {actuel['levels']}
    ├─ P&L: ${actuel['total_pnl']:+.2f}
    ├─ Win Rate: {actuel['win_rate']:.1f}%
    ├─ Avg Win: ${actuel['avg_win']:.2f}
    ├─ MFE Capture: {actuel['mfe_capture_rate']:.1f}%
    └─ Profit Factor: {actuel['profit_factor']:.2f}

    MEILLEURE CONFIGURATION ({best['config']}):
    ├─ Paliers: {best['levels']}
    ├─ P&L: ${best['total_pnl']:+.2f}
    ├─ Win Rate: {best['win_rate']:.1f}%
    ├─ Avg Win: ${best['avg_win']:.2f}
    ├─ MFE Capture: {best['mfe_capture_rate']:.1f}%
    └─ Profit Factor: {best['profit_factor']:.2f}

    ════════════════════════════════════════════════════════
    AMÉLIORATION P&L: ${improvement:+.2f}
    AMÉLIORATION MFE CAPTURE: {mfe_improvement:+.1f}%
    ════════════════════════════════════════════════════════
    """)

    # Recommandation
    print("\n🎯 RECOMMANDATION:")
    print("-"*60)
    if improvement > 0:
        print(f"   Passer à la config '{best['config']}'")
        print(f"   Paliers: {best['levels']}")
    else:
        print("   Garder la config actuelle")

