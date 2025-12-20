#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest Vendredi 14 Novembre 2025 - ES & NQ
Avec nouvelles optimisations ML + TP/SL
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import json

# Ajouter racine au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from strategies.menthorq_3layer_strategy import MenthorQ3LayerStrategy
from ml.ml_3layer_integrated_system import ML3LayerIntegratedSystem

# Chemins données (absolu)
DATA_DIR = Path(__file__).resolve().parent.parent / "DATA_SIERRA_CHART" / "DATA_2025" / "NOVEMBRE" / "20251114"

def load_friday_data(symbol: str, chart: int = 9):
    """Charge données vendredi 14 novembre (JSONL)"""
    file_path = DATA_DIR / f"CHART_{chart}" / "ML_READY" / f"ml_{symbol}Z25_FUT_CME_{chart}.jsonl"

    if not file_path.exists():
        print(f"❌ Fichier non trouvé: {file_path}")
        return None

    # Charger JSON (1 ligne = 1 snapshot)
    snapshots = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                snapshots.append(json.loads(line))

    df = pd.DataFrame(snapshots)
    print(f"✅ {symbol}: {len(df)} snapshots chargés")
    return df

def backtest_friday(symbol: str, chart: int = 9):
    """Backtest vendredi 14 novembre avec optimisations"""

    print(f"\n{'='*70}")
    print(f"📊 BACKTEST {symbol} - Vendredi 14 novembre 2025")
    print(f"{'='*70}\n")

    # 1. Charger données
    df = load_friday_data(symbol, chart)
    if df is None:
        return

    # 2. Initialiser système ML (désactivé pour backtest)
    ml_system = ML3LayerIntegratedSystem(
        symbols=[symbol],
        use_ml_models=False  # Désactiver ML (features manquantes)
    )

    # 3. Initialiser stratégie
    strategy = MenthorQ3LayerStrategy(ml_3layer_system=ml_system)

    # 4. Simuler trades
    trades = []
    positions_open = {}

    for idx, row in df.iterrows():
        snapshot = row.to_dict()

        # Générer signal
        signal = strategy.generate_signal(snapshot, symbol)

        if signal and signal.get('action') in ['LONG', 'SHORT']:
            trade = {
                'time': snapshot.get('t_ms', idx),
                'action': signal['action'],
                'entry': snapshot['mid'],
                'stop': signal['stop'],
                'target': signal['target'],
                'ml_quality': signal.get('ml_quality_score', 0),
                'ml_win_prob': signal.get('ml_win_probability', 0)
            }
            positions_open[idx] = trade
            print(f"🔵 {trade['action']} @ {trade['entry']:.2f} | Q: {trade['ml_quality']:.1f} | WIN: {trade['ml_win_prob']:.1%}")

        # Vérifier TP/SL
        for pos_id in list(positions_open.keys()):
            pos = positions_open[pos_id]

            # Simuler high/low
            high = snapshot['mid'] + snapshot.get('atr', 5) * 0.5
            low = snapshot['mid'] - snapshot.get('atr', 5) * 0.5

            hit_tp = False
            hit_sl = False

            if pos['action'] == 'LONG':
                if high >= pos['target']:
                    hit_tp = True
                elif low <= pos['stop']:
                    hit_sl = True
            else:
                if low <= pos['target']:
                    hit_tp = True
                elif high >= pos['stop']:
                    hit_sl = True

            if hit_tp or hit_sl:
                exit_price = pos['target'] if hit_tp else pos['stop']
                pnl_points = (exit_price - pos['entry']) if pos['action'] == 'LONG' else (pos['entry'] - exit_price)
                pnl_ticks = pnl_points / 0.25

                result = {
                    **pos,
                    'exit': exit_price,
                    'exit_reason': 'TP' if hit_tp else 'SL',
                    'pnl_points': pnl_points,
                    'pnl_ticks': pnl_ticks,
                    'win': hit_tp
                }
                trades.append(result)

                status = "✅" if hit_tp else "❌"
                print(f"  {status} | Exit: {exit_price:.2f} | P&L: {pnl_ticks:.1f}t")

                del positions_open[pos_id]

    # 5. Résultats
    if not trades:
        print("\n❌ Aucun trade")
        return

    trades_df = pd.DataFrame(trades)
    wins = trades_df['win'].sum()
    total = len(trades_df)
    wr = wins / total * 100
    pnl = trades_df['pnl_ticks'].sum()

    print(f"\n{'='*70}")
    print(f"📊 RÉSULTATS {symbol}")
    print(f"{'='*70}")
    print(f"Trades: {total} | Wins: {wins} | WR: {wr:.1f}%")
    print(f"P&L: {pnl:.1f}t")
    print(f"ML Quality: {trades_df['ml_quality'].mean():.1f}")
    print(f"ML WIN Prob: {trades_df['ml_win_prob'].mean():.1%}")
    print(f"{'='*70}\n")

    return trades_df

if __name__ == "__main__":
    print("\n🧪 BACKTEST VENDREDI 14 NOVEMBRE 2025\n")

    trades_es = backtest_friday("ES", chart=3)
    trades_nq = backtest_friday("NQ", chart=9)

    print("\n✅ Backtest terminé")


