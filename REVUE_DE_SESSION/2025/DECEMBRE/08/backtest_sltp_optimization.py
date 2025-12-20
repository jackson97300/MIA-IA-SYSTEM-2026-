#!/usr/bin/env python3
"""
BACKTEST SL/TP OPTIMIZATION
============================

Teste différentes configurations SL/TP sur données historiques
pour trouver le meilleur ratio gain/perte.

Date: 08/12/2025
"""

import os
import json
import glob
from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# Charger les trades avec MFE/MAE depuis les logs
LOGS_DIR = r"D:\MIA_IA_system\logs"

# Configurations à tester
SL_OPTIONS = [12, 15, 18, 20, 22, 25]  # en ticks
TP_OPTIONS = [25, 30, 35, 40, 45, 50]  # en ticks
BE_TRIGGER_OPTIONS = [6, 8, 10, 12, 15]  # Déclencher BE à X ticks de profit

# Tick values
TICK_VALUES = {'ES': 12.50, 'NQ': 5.00, 'RTY': 5.00}
TICK_SIZES = {'ES': 0.25, 'NQ': 0.25, 'RTY': 0.10}

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeData:
    symbol: str
    direction: str
    entry_price: float
    mfe_ticks: float  # Maximum Favorable Excursion (max profit atteint)
    mae_ticks: float  # Maximum Adverse Excursion (max perte atteinte)
    actual_pnl: float
    actual_result: str

# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTION DES TRADES
# ═══════════════════════════════════════════════════════════════════════════════

def extract_trades_from_logs() -> List[TradeData]:
    """Extrait les trades avec MFE/MAE depuis les logs"""

    trades = []

    # Logs des derniers jours
    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, "__main___202512*.log")))[-5:]

    import re

    # Pattern pour extraire MFE/MAE
    pattern = re.compile(
        r'Trade ferm.*\((\w+) (SL|TP|BE).*\$([+-]?\d+\.?\d*)\).*'
        r'MFE: \+?([\d.]+).*MAE: ([+-]?\d+\.?\d*)'
    )

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            matches = pattern.findall(content)

            for match in matches:
                symbol_raw, exit_type, pnl, mfe, mae = match

                # Normaliser symbole
                symbol = 'ES' if 'ES' in symbol_raw else 'NQ' if 'NQ' in symbol_raw else 'RTY'
                tick_value = TICK_VALUES.get(symbol, 12.50)

                pnl_val = float(pnl)
                mfe_val = float(mfe)
                mae_val = float(mae)

                # Convertir en ticks
                mfe_ticks = mfe_val / tick_value
                mae_ticks = abs(mae_val) / tick_value

                trade = TradeData(
                    symbol=symbol,
                    direction='LONG' if pnl_val > 0 else 'UNKNOWN',  # Simplifié
                    entry_price=0,  # Pas nécessaire pour simulation
                    mfe_ticks=mfe_ticks,
                    mae_ticks=mae_ticks,
                    actual_pnl=pnl_val,
                    actual_result='WIN' if pnl_val > 0 else 'LOSS'
                )
                trades.append(trade)

        except Exception as e:
            print(f"[WARN] Erreur lecture {log_file}: {e}")

    return trades

# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

def simulate_trade(trade: TradeData, sl_ticks: int, tp_ticks: int,
                   be_trigger: int, be_offset: int = 2) -> Tuple[float, str]:
    """
    Simule un trade avec une configuration SL/TP donnée.

    Retourne (pnl_simulé, exit_reason)
    """

    tick_value = TICK_VALUES.get(trade.symbol, 12.50)

    # Logique de simulation:
    # 1. Si MAE >= SL → LOSS (SL touché avant tout)
    # 2. Si MFE >= TP → WIN (TP touché)
    # 3. Si MFE >= BE_TRIGGER mais MFE < TP →
    #    - Si MAE après BE >= nouveau SL → petit gain (BE+offset)
    #    - Sinon sortie à MFE partiel
    # 4. Sinon → dépend du trade réel

    # Cas 1: SL touché (MAE atteint le SL)
    if trade.mae_ticks >= sl_ticks:
        # Le prix a touché le SL avant tout
        pnl = -sl_ticks * tick_value
        return pnl, "SL_HIT"

    # Cas 2: TP touché (MFE atteint le TP)
    if trade.mfe_ticks >= tp_ticks:
        pnl = tp_ticks * tick_value
        return pnl, "TP_HIT"

    # Cas 3: BE déclenché mais pas TP
    if trade.mfe_ticks >= be_trigger:
        # BE activé - nouveau SL à entry + be_offset
        # Si le trade a finalement perdu après BE, sortie à BE+offset
        if trade.actual_result == 'LOSS':
            # Le prix est revenu après BE → sortie à BE offset
            pnl = be_offset * tick_value
            return pnl, "BE_HIT"
        else:
            # Trade gagnant - on garde le MFE partiel (ou le résultat réel)
            # Simulation: sortie à MFE/2 en moyenne (trailing imparfait)
            captured = min(trade.mfe_ticks * 0.5, trade.mfe_ticks - be_offset)
            pnl = max(be_offset, captured) * tick_value
            return pnl, "TRAIL_EXIT"

    # Cas 4: Ni SL, ni TP, ni BE → utiliser le résultat réel
    return trade.actual_pnl, "ACTUAL"

def run_backtest(trades: List[TradeData], sl_ticks: int, tp_ticks: int,
                 be_trigger: int, be_offset: int = 2) -> Dict:
    """
    Exécute un backtest complet avec une configuration donnée.
    """

    results = {
        'sl_ticks': sl_ticks,
        'tp_ticks': tp_ticks,
        'be_trigger': be_trigger,
        'be_offset': be_offset,
        'total_trades': len(trades),
        'wins': 0,
        'losses': 0,
        'total_pnl': 0,
        'total_gains': 0,
        'total_losses': 0,
        'exit_types': {'SL_HIT': 0, 'TP_HIT': 0, 'BE_HIT': 0, 'TRAIL_EXIT': 0, 'ACTUAL': 0}
    }

    for trade in trades:
        pnl, exit_reason = simulate_trade(trade, sl_ticks, tp_ticks, be_trigger, be_offset)

        results['total_pnl'] += pnl
        results['exit_types'][exit_reason] += 1

        if pnl > 0:
            results['wins'] += 1
            results['total_gains'] += pnl
        else:
            results['losses'] += 1
            results['total_losses'] += abs(pnl)

    # Calculer métriques
    results['win_rate'] = results['wins'] / results['total_trades'] * 100 if results['total_trades'] else 0
    results['avg_win'] = results['total_gains'] / results['wins'] if results['wins'] else 0
    results['avg_loss'] = results['total_losses'] / results['losses'] if results['losses'] else 0
    results['profit_factor'] = results['total_gains'] / results['total_losses'] if results['total_losses'] else 0
    results['rr_ratio'] = results['avg_win'] / results['avg_loss'] if results['avg_loss'] else 0

    return results

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*80)
    print("BACKTEST SL/TP OPTIMIZATION")
    print("="*80)

    # Extraire trades
    print("\n[1/3] Extraction des trades...")
    trades = extract_trades_from_logs()
    print(f"      {len(trades)} trades extraits")

    if len(trades) < 10:
        print("\n[WARN] Pas assez de trades pour un backtest fiable!")

    # Afficher stats actuelles
    print("\n[2/3] Stats actuelles:")
    print("-"*60)

    actual_pnl = sum(t.actual_pnl for t in trades)
    actual_wins = sum(1 for t in trades if t.actual_result == 'WIN')
    actual_losses = len(trades) - actual_wins

    print(f"Trades: {len(trades)} | Wins: {actual_wins} | Losses: {actual_losses}")
    print(f"Win Rate: {actual_wins/len(trades)*100:.1f}%")
    print(f"P&L actuel: ${actual_pnl:+.2f}")

    # Analyser MFE/MAE
    print("\nDistribution MFE/MAE:")
    mfe_values = [t.mfe_ticks for t in trades]
    mae_values = [t.mae_ticks for t in trades]
    print(f"MFE moyen: {sum(mfe_values)/len(mfe_values):.1f} ticks")
    print(f"MAE moyen: {sum(mae_values)/len(mae_values):.1f} ticks")
    print(f"MFE max: {max(mfe_values):.1f} ticks")
    print(f"MAE max: {max(mae_values):.1f} ticks")

    # Tester configurations
    print("\n[3/3] Test des configurations...")
    print("="*80)

    all_results = []

    # Test grid
    for sl in SL_OPTIONS:
        for tp in TP_OPTIONS:
            for be in BE_TRIGGER_OPTIONS:
                if tp > sl and be < tp:  # Configurations valides seulement
                    result = run_backtest(trades, sl, tp, be, be_offset=2)
                    all_results.append(result)

    # Trier par P&L
    all_results.sort(key=lambda x: x['total_pnl'], reverse=True)

    # Afficher top 10
    print("\nTOP 10 CONFIGURATIONS:")
    print("-"*100)
    print(f"{'SL':>4} {'TP':>4} {'BE':>4} | {'P&L':>10} | {'WR':>6} | {'Avg Win':>10} | {'Avg Loss':>10} | {'R:R':>6} | {'PF':>6}")
    print("-"*100)

    for r in all_results[:10]:
        print(f"{r['sl_ticks']:>4} {r['tp_ticks']:>4} {r['be_trigger']:>4} | "
              f"${r['total_pnl']:>+9.2f} | {r['win_rate']:>5.1f}% | "
              f"${r['avg_win']:>9.2f} | ${r['avg_loss']:>9.2f} | "
              f"{r['rr_ratio']:>5.2f} | {r['profit_factor']:>5.2f}")

    # Meilleure config
    best = all_results[0]

    print("\n" + "="*80)
    print("MEILLEURE CONFIGURATION:")
    print("="*80)
    print(f"""
    SL: {best['sl_ticks']} ticks
    TP: {best['tp_ticks']} ticks
    BE Trigger: {best['be_trigger']} ticks (SL passe à +2t)

    P&L Total: ${best['total_pnl']:+.2f}
    Win Rate: {best['win_rate']:.1f}%
    Ratio R:R: {best['rr_ratio']:.2f}:1
    Profit Factor: {best['profit_factor']:.2f}

    Exits: TP={best['exit_types']['TP_HIT']} | SL={best['exit_types']['SL_HIT']} | BE={best['exit_types']['BE_HIT']}
    """)

    # Comparer avec config actuelle
    print("\n" + "-"*80)
    print("COMPARAISON AVEC CONFIG ACTUELLE (ES: SL=22t, TP=30t, BE=8t):")
    print("-"*80)

    current = run_backtest(trades, sl_ticks=22, tp_ticks=30, be_trigger=8, be_offset=2)

    improvement = best['total_pnl'] - current['total_pnl']

    print(f"Config actuelle: P&L=${current['total_pnl']:+.2f} | WR={current['win_rate']:.1f}% | R:R={current['rr_ratio']:.2f}")
    print(f"Meilleure config: P&L=${best['total_pnl']:+.2f} | WR={best['win_rate']:.1f}% | R:R={best['rr_ratio']:.2f}")
    print(f"\nAMÉLIORATION: ${improvement:+.2f}")

    print("\n" + "="*80)

