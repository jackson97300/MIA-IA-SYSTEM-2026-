#!/usr/bin/env python3
"""Analyse rapide des résultats du backtest"""

import json
from pathlib import Path

json_path = Path('backtesting/results/backtest_data.json')
with open(json_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

summary = data.get('summary', {})

print("="*80)
print("ANALYSE RAPIDE DES RESULTATS")
print("="*80)
print(f"\nTotal Trades: {data.get('total_trades', 0):,}")
print(f"\nPERFORMANCE GLOBALE:")
win_rate_val = summary.get('win_rate', 0)
if isinstance(win_rate_val, (int, float)):
    win_rate = win_rate_val if win_rate_val <= 1 else win_rate_val / 100
    print(f"  Win Rate: {win_rate*100:.2f}%")
else:
    print(f"  Win Rate: N/A")

pnl_ticks = summary.get('total_pnl_ticks', 0)
pnl_dollars = summary.get('total_pnl_dollars', 0)
wins = summary.get('wins', 0)
losses = summary.get('losses', 0)

print(f"  Total PnL (ticks): {int(pnl_ticks):,}" if isinstance(pnl_ticks, (int, float)) else f"  Total PnL (ticks): N/A")
print(f"  Total PnL ($): ${float(pnl_dollars):,.2f}" if isinstance(pnl_dollars, (int, float)) else f"  Total PnL ($): N/A")
print(f"  Profit Factor: {float(summary.get('profit_factor', 0)):.2f}" if isinstance(summary.get('profit_factor', 0), (int, float)) else "  Profit Factor: N/A")
print(f"  Wins: {int(wins):,}" if isinstance(wins, (int, float)) else "  Wins: N/A")
print(f"  Losses: {int(losses):,}" if isinstance(losses, (int, float)) else "  Losses: N/A")
avg_win = summary.get('avg_win', 0)
avg_loss = summary.get('avg_loss', 0)
print(f"  Average Win: {float(avg_win):.2f} ticks" if isinstance(avg_win, (int, float)) else "  Average Win: N/A")
print(f"  Average Loss: {float(avg_loss):.2f} ticks" if isinstance(avg_loss, (int, float)) else "  Average Loss: N/A")

# Top 5 configurations SL/TP
by_sl_tp = data.get('by_sl_tp', {})
if by_sl_tp:
    print(f"\nTOP 5 CONFIGURATIONS SL/TP:")
    configs = []
    for key, perf in by_sl_tp.items():
        if isinstance(perf, dict):
            trades_val = perf.get('trades', 0)
            trades = int(trades_val) if isinstance(trades_val, (int, float)) else 0
            win_rate_val = perf.get('win_rate', 0)
            win_rate = float(win_rate_val) if isinstance(win_rate_val, (int, float)) else 0.0
            pnl_val = perf.get('pnl_ticks', 0)
            pnl = float(pnl_val) if isinstance(pnl_val, (int, float)) else 0.0

            configs.append({
                'key': str(key)[:80],
                'win_rate': win_rate,
                'pnl': pnl,
                'trades': trades
            })
    configs.sort(key=lambda x: x['pnl'], reverse=True)
    for i, cfg in enumerate(configs[:5], 1):
        print(f"  {i}. {cfg['key']}")
        print(f"     WR: {cfg['win_rate']:.1f}%, PnL: {cfg['pnl']:.0f} ticks, Trades: {cfg['trades']:,}")

# Top 5 niveaux
by_level = data.get('by_level', {})
if by_level:
    print(f"\nTOP 5 NIVEAUX:")
    levels = []
    for key, perf in by_level.items():
        if isinstance(perf, dict):
            trades_val = perf.get('trades', 0)
            trades = int(trades_val) if isinstance(trades_val, (int, float)) else 0
            win_rate_val = perf.get('win_rate', 0)
            win_rate = float(win_rate_val) if isinstance(win_rate_val, (int, float)) else 0.0
            pnl_val = perf.get('pnl_ticks', 0)
            pnl = float(pnl_val) if isinstance(pnl_val, (int, float)) else 0.0

            levels.append({
                'key': str(key)[:60],
                'win_rate': win_rate,
                'pnl': pnl,
                'trades': trades
            })
    levels.sort(key=lambda x: x['pnl'], reverse=True)
    for i, level in enumerate(levels[:5], 1):
        print(f"  {i}. {level['key']}")
        print(f"     WR: {level['win_rate']:.1f}%, PnL: {level['pnl']:.0f} ticks, Trades: {level['trades']:,}")

print("\n" + "="*80)
print("Rapports complets disponibles dans: backtesting/results/")
print("="*80)
