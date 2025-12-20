#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 BACKTEST COMPLET AVEC ML QUALITY SCORE
Version: 1.0 - Features Complètes 100%
Date: 16 Novembre 2025

Backtest ROBUSTE utilisant les snapshots COMPLETS avec toutes les features:
- ✅ MenthorQ (17 features)
- ✅ Battle Navale (7 features)
- ✅ Volume Profile (4 features)
- ✅ OrderFlow (15 features)
- ✅ Context (20 features)
- ✅ Features Engineered (auto)

→ ML Quality Score ACTIVÉ (score 0-100)
→ WIN/LOSS Classifier ACTIVÉ (proba win)
→ TOUS les filtres 3-Layer actifs
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

from ml.snapshot_loader_complet import SnapshotLoaderComplet
from strategies.menthorq_3layer_strategy import MenthorQ3LayerStrategy
from ml.ml_3layer_integrated_system import ML3LayerIntegratedSystem


def backtest_avec_ml_quality(
    symbol: str,
    date: str = "20251114",
    chart: int = 9,
    session_filter: str = None
):
    """
    Backtest complet avec ML Quality Score activé

    Args:
        symbol: Symbole (ES, NQ, RTY)
        date: Date YYYYMMDD
        chart: Numéro de chart
        session_filter: Filtrer par session (London, US, Asia) ou None

    Returns:
        DataFrame des trades
    """
    print("\n" + "=" * 80)
    print(f"🚀 BACKTEST COMPLET ML QUALITY - {symbol}")
    print("=" * 80)
    print(f"   Date: {date}")
    print(f"   Chart: {chart}")
    print(f"   Session: {session_filter or 'TOUTES'}")
    print("=" * 80 + "\n")

    # ═══════════════════════════════════════════════════════════════════
    # 1. CHARGER SNAPSHOTS COMPLETS (100% features)
    # ═══════════════════════════════════════════════════════════════════

    loader = SnapshotLoaderComplet()
    df = loader.load_day_data(
        symbol=symbol,
        date=date,
        chart=chart,
        validate_features=True
    )

    if df.empty:
        print("❌ Aucun snapshot chargé")
        return pd.DataFrame()

    # Filtrer par session si demandé
    if session_filter:
        df = loader.filter_trading_session(df, session_filter)

    print(f"✅ {len(df)} snapshots prêts pour backtest\n")

    # ═══════════════════════════════════════════════════════════════════
    # 2. INITIALISER SYSTÈME ML (RÉACTIVÉ!)
    # ═══════════════════════════════════════════════════════════════════

    print("🧠 Initialisation ML 3-Layer System...")
    ml_system = ML3LayerIntegratedSystem(
        symbols=[symbol],
        use_ml_models=True  # ✅ RÉACTIVÉ! Snapshots complets permettent ML
    )
    print("✅ ML 3-Layer System prêt\n")

    # ═══════════════════════════════════════════════════════════════════
    # 3. INITIALISER STRATÉGIE
    # ═══════════════════════════════════════════════════════════════════

    strategy = MenthorQ3LayerStrategy(ml_3layer_system=ml_system)
    print("✅ Stratégie MenthorQ 3-Layer initialisée\n")

    # ═══════════════════════════════════════════════════════════════════
    # 4. SIMULER TRADES
    # ═══════════════════════════════════════════════════════════════════

    print("=" * 80)
    print("🎯 GÉNÉRATION SIGNAUX")
    print("=" * 80 + "\n")

    trades = []
    positions_open = {}
    signal_count = 0
    rejected_count = 0

    for idx, row in df.iterrows():
        snapshot = row.to_dict()

        # Générer signal (avec TOUS les filtres ML actifs)
        signal = strategy.generate_signal(snapshot, symbol)

        if signal:
            signal_count += 1
            
            if signal.get('action') in ['LONG', 'SHORT']:
                # Gérer différents formats de signal
                stop_price = signal.get('stop') or signal.get('sl')
                target_price = signal.get('target') or signal.get('tp') or signal.get('tp1')
                
                if not stop_price or not target_price:
                    continue  # Skip si pas de SL/TP
                
                # Signal ACCEPTÉ
                trade = {
                    'time': snapshot.get('t_ms', idx),
                    'action': signal['action'],
                    'entry': snapshot['mid'],
                    'stop': stop_price,
                    'target': target_price,
                    'ml_quality': signal.get('ml_quality_score', 0),
                    'ml_win_prob': signal.get('ml_win_probability', 0),
                    'layer1_conf': signal.get('layer1_confidence', 0),
                    'layer2_conf': signal.get('layer2_confidence', 0),
                    'layer3_conf': signal.get('layer3_confidence', 0),
                    'confidence': signal.get('confidence', 0)
                }
                positions_open[idx] = trade

                print(f"{'='*70}")
                print(f"🔵 {trade['action']} @ {trade['entry']:.2f}")
                print(f"   ML Quality:  {trade['ml_quality']:.1f}/100")
                print(f"   ML WIN Prob: {trade['ml_win_prob']:.1%}")
                print(f"   Confidence:  {trade['confidence']:.1%}")
                print(f"   L1/L2/L3:    {trade['layer1_conf']:.1%} / {trade['layer2_conf']:.1%} / {trade['layer3_conf']:.1%}")
                print(f"   SL: {trade['stop']:.2f} | TP: {trade['target']:.2f}")
            else:
                # Signal REJETÉ
                rejected_count += 1

        # Vérifier TP/SL des positions ouvertes
        for pos_id in list(positions_open.keys()):
            pos = positions_open[pos_id]

            # Simuler high/low (approximation avec ATR)
            atr = snapshot.get('atr', 5)
            high = snapshot['mid'] + atr * 0.5
            low = snapshot['mid'] - atr * 0.5

            hit_tp = False
            hit_sl = False

            if pos['action'] == 'LONG':
                if high >= pos['target']:
                    hit_tp = True
                elif low <= pos['stop']:
                    hit_sl = True
            else:  # SHORT
                if low <= pos['target']:
                    hit_tp = True
                elif high >= pos['stop']:
                    hit_sl = True

            if hit_tp or hit_sl:
                exit_price = pos['target'] if hit_tp else pos['stop']

                # Calculer P&L
                if symbol == "ES":
                    tick_size = 0.25
                    tick_value = 12.50
                elif symbol == "NQ":
                    tick_size = 0.25
                    tick_value = 5.00
                else:  # RTY
                    tick_size = 0.10
                    tick_value = 5.00

                pnl_points = (exit_price - pos['entry']) if pos['action'] == 'LONG' else (pos['entry'] - exit_price)
                pnl_ticks = pnl_points / tick_size
                pnl_dollars = pnl_ticks * tick_value

                result = {
                    **pos,
                    'exit': exit_price,
                    'exit_reason': 'TP' if hit_tp else 'SL',
                    'pnl_points': pnl_points,
                    'pnl_ticks': pnl_ticks,
                    'pnl_dollars': pnl_dollars,
                    'win': hit_tp
                }
                trades.append(result)

                status = "✅ WIN" if hit_tp else "❌ LOSS"
                print(f"  {status} | Exit: {exit_price:.2f} | P&L: {pnl_ticks:.1f}t (${pnl_dollars:.2f})")

                del positions_open[pos_id]

    # ═══════════════════════════════════════════════════════════════════
    # 5. RÉSULTATS
    # ═══════════════════════════════════════════════════════════════════

    print("\n" + "=" * 80)
    print("📊 RÉSULTATS BACKTEST")
    print("=" * 80)

    print(f"\n📋 SIGNAUX:")
    print(f"   Total signaux générés: {signal_count}")
    print(f"   Signaux acceptés:      {len(trades)}")
    print(f"   Signaux rejetés:       {rejected_count}")
    print(f"   Taux acceptation:      {len(trades)/signal_count*100 if signal_count > 0 else 0:.1f}%")

    if not trades:
        print("\n❌ Aucun trade exécuté")
        print("=" * 80 + "\n")
        return pd.DataFrame()

    trades_df = pd.DataFrame(trades)

    # Statistiques
    wins = trades_df['win'].sum()
    losses = len(trades_df) - wins
    total = len(trades_df)
    wr = wins / total * 100

    pnl_total = trades_df['pnl_dollars'].sum()
    pnl_avg = trades_df['pnl_dollars'].mean()

    win_trades = trades_df[trades_df['win'] == True]
    loss_trades = trades_df[trades_df['win'] == False]

    avg_win = win_trades['pnl_dollars'].mean() if len(win_trades) > 0 else 0
    avg_loss = loss_trades['pnl_dollars'].mean() if len(loss_trades) > 0 else 0

    profit_factor = abs(win_trades['pnl_dollars'].sum() / loss_trades['pnl_dollars'].sum()) if len(loss_trades) > 0 and loss_trades['pnl_dollars'].sum() != 0 else 0

    print(f"\n💰 PERFORMANCE:")
    print(f"   Trades:         {total}")
    print(f"   Wins:           {wins}")
    print(f"   Losses:         {losses}")
    print(f"   Win Rate:       {wr:.1f}%")
    print(f"   P&L Total:      ${pnl_total:,.2f}")
    print(f"   P&L Moyen:      ${pnl_avg:,.2f}")
    print(f"   Avg Win:        ${avg_win:,.2f}")
    print(f"   Avg Loss:       ${avg_loss:,.2f}")
    print(f"   Profit Factor:  {profit_factor:.2f}")

    print(f"\n🎯 ML QUALITY SCORES:")
    print(f"   ML Quality (moy):   {trades_df['ml_quality'].mean():.1f}/100")
    print(f"   ML Quality (min):   {trades_df['ml_quality'].min():.1f}")
    print(f"   ML Quality (max):   {trades_df['ml_quality'].max():.1f}")
    print(f"   ML WIN Prob (moy):  {trades_df['ml_win_prob'].mean():.1%}")
    print(f"   Confidence (moy):   {trades_df['confidence'].mean():.1%}")

    # Stats système ML
    ml_stats = ml_system.get_stats()
    print(f"\n📊 FILTRES ML 3-LAYER:")
    print(f"   Total évalués:        {ml_stats['total_evaluations']}")
    print(f"   Layer 1 rejets:       {ml_stats['layer1_rejections']}")
    print(f"   Layer 2 rejets:       {ml_stats['layer2_rejections']}")
    print(f"   Layer 3 rejets:       {ml_stats['layer3_rejections']}")
    print(f"   ML Quality rejets:    {ml_stats['ml_quality_rejections']}")
    print(f"   ML WIN/LOSS rejets:   {ml_stats['ml_winloss_rejections']}")
    print(f"   Hard Rules rejets:    {ml_stats['hard_rules_rejections']}")
    print(f"   Trades exécutés:      {ml_stats['trades_executed']}")

    print("=" * 80 + "\n")

    return trades_df


def main():
    """Exécute backtest avec paramètres"""

    # Paramètres backtest
    SYMBOL = "NQ"
    DATE = "20251114"  # Vendredi 14 novembre
    CHART = 9
    SESSION = "London"  # ou None pour toutes les sessions

    # Lancer backtest
    results = backtest_avec_ml_quality(
        symbol=SYMBOL,
        date=DATE,
        chart=CHART,
        session_filter=SESSION
    )

    # Sauvegarder résultats
    if not results.empty:
        output_file = f"backtest_results_{SYMBOL}_{DATE}_{SESSION or 'ALL'}.csv"
        results.to_csv(output_file, index=False)
        print(f"💾 Résultats sauvegardés: {output_file}\n")

    return results


if __name__ == "__main__":
    main()
