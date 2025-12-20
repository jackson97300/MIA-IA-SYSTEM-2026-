#!/usr/bin/env python3
"""
Script d'analyse rapide des résultats du backtest
Affiche les statistiques clés et identifie les meilleures configurations
"""

import sys
from pathlib import Path
import json
import pandas as pd

# Ajouter racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def analyze_backtest_results():
    """Analyse les résultats du backtest"""

    results_dir = Path('backtesting/results')

    # Chercher le fichier JSON le plus récent
    json_files = list(results_dir.glob('backtest_data.json'))
    if not json_files:
        print("ERREUR: Aucun fichier backtest_data.json trouve")
        return

    json_path = json_files[0]
    print(f"Chargement: {json_path}")

    with open(json_path, 'r', encoding='utf-8') as f:
        results = json.load(f)

    print("\n" + "="*80)
    print("ANALYSE DES RESULTATS DU BACKTEST")
    print("="*80)

    # Résumé général
    print(f"\nRESUME GENERAL:")
    print(f"  Total trades: {results.get('total_trades', 0):,}")

    summary = results.get('summary', {})
    if summary:
        print(f"\nPERFORMANCE GLOBALE:")
        print(f"  Win Rate: {summary.get('win_rate', 0)*100:.2f}%")
        print(f"  Total PnL (ticks): {summary.get('total_pnl_ticks', 0):,.0f}")
        print(f"  Total PnL ($): ${summary.get('total_pnl_dollars', 0):,.2f}")
        print(f"  Profit Factor: {summary.get('profit_factor', 0):.2f}")
        print(f"  Average Win: {summary.get('avg_win', 0):.2f} ticks")
        print(f"  Average Loss: {summary.get('avg_loss', 0):.2f} ticks")
        print(f"  Max Drawdown: {summary.get('max_drawdown', 0):.2f} ticks")

    # Meilleures configurations SL/TP
    by_sl_tp = results.get('by_sl_tp', {})
    if by_sl_tp:
        print(f"\nMEILLEURES CONFIGURATIONS SL/TP:")
        configs = []
        for config_key, perf in by_sl_tp.items():
            if isinstance(perf, dict) and perf.get('total_trades', 0) > 0:
                win_rate = perf.get('wins', 0) / perf.get('total_trades', 1)
                configs.append({
                    'config': config_key,
                    'win_rate': win_rate,
                    'pnl': perf.get('pnl', 0),
                    'trades': perf.get('total_trades', 0)
                })

        configs.sort(key=lambda x: x['pnl'], reverse=True)
        for i, config in enumerate(configs[:10], 1):
            print(f"  {i}. {config['config']}: WR={config['win_rate']*100:.1f}%, PnL={config['pnl']:.0f} ticks, Trades={config['trades']:,}")

    # Meilleurs niveaux
    by_level = results.get('by_level', {})
    if by_level:
        print(f"\nMEILLEURS NIVEAUX:")
        levels = []
        for level_key, perf in by_level.items():
            if isinstance(perf, dict) and perf.get('total_trades', 0) > 0:
                win_rate = perf.get('wins', 0) / perf.get('total_trades', 1)
                levels.append({
                    'level': level_key,
                    'win_rate': win_rate,
                    'pnl': perf.get('pnl', 0),
                    'trades': perf.get('total_trades', 0)
                })

        levels.sort(key=lambda x: x['pnl'], reverse=True)
        for i, level in enumerate(levels[:10], 1):
            print(f"  {i}. {level['level']}: WR={level['win_rate']*100:.1f}%, PnL={level['pnl']:.0f} ticks, Trades={level['trades']:,}")

    # Performance par heure
    by_time = results.get('by_time', {})
    if by_time:
        print(f"\nMEILLEURES HEURES DE TRADING:")
        hours = []
        for hour_key, perf in by_time.items():
            if isinstance(perf, dict) and perf.get('total_trades', 0) > 0:
                win_rate = perf.get('wins', 0) / perf.get('total_trades', 1)
                hours.append({
                    'hour': hour_key,
                    'win_rate': win_rate,
                    'pnl': perf.get('pnl', 0),
                    'trades': perf.get('total_trades', 0)
                })

        hours.sort(key=lambda x: x['pnl'], reverse=True)
        for i, hour in enumerate(hours[:10], 1):
            print(f"  {i}. {hour['hour']}: WR={hour['win_rate']*100:.1f}%, PnL={hour['pnl']:.0f} ticks, Trades={hour['trades']:,}")

    print("\n" + "="*80)
    print("ANALYSE TERMINEE")
    print("="*80)

if __name__ == '__main__':
    analyze_backtest_results()
