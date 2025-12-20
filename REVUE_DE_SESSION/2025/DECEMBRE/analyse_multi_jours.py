# -*- coding: utf-8 -*-
"""
ANALYSE MULTI-JOURS DES TRADES MIA
==================================
Analyse approfondie sur plusieurs jours avec:
- Separation WINS vs LOSSES
- Analyse TENDANCE vs CONTRE-TENDANCE
- Split 80/20 pour backtest/validation
- Recommandations de seuils optimaux
"""

import os
import sys
import re
import json
import random
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Chemins des fichiers de logs
LOGS_DIR = r"D:\MIA_IA_system\logs_advanced\trades"

# Jours a analyser
DATES = [
    "20251204", "20251205", "20251208", "20251209", "20251210",
    "20251211", "20251212", "20251216", "20251217"
]

def parse_log_file(filepath: str) -> List[Dict]:
    """Parse un fichier de log et extrait les trades complets"""
    trades = []
    entries = {}  # symbol -> entry data

    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Pattern: TIME - INFO - [SYMBOL] ENTRY/EXIT | {...}
            match = re.search(r'\[(\w+)\]\s+(ENTRY|EXIT)\s+\|\s+({.*})', line)
            if not match:
                continue

            symbol = match.group(1)
            action = match.group(2)
            data_str = match.group(3)

            try:
                data = eval(data_str)  # Parse le dict Python
            except:
                continue

            if action == 'ENTRY':
                # Ne garder que ML_3Layer (exclure RANGE_FADE)
                if data.get('strategy') == 'ML_3Layer':
                    entries[symbol] = data
            elif action == 'EXIT':
                if symbol in entries:
                    entry_data = entries[symbol]

                    # Determiner WIN/LOSS
                    pnl_usd = data.get('pnl_usd', 0)
                    if pnl_usd is None:
                        pnl_usd = 0

                    is_win = pnl_usd > 0

                    # Creer le trade complet
                    trade = {
                        'symbol': symbol,
                        'direction': entry_data.get('direction', 'UNKNOWN'),
                        'entry_price': entry_data.get('price', 0),
                        'exit_price': data.get('exit_price', 0),
                        'pnl_usd': pnl_usd,
                        'pnl_ticks': data.get('pnl_ticks', 0),
                        'is_win': is_win,
                        'exit_reason': data.get('exit_reason', 'UNKNOWN'),
                        'duration_ms': data.get('duration_ms', 0),
                        'mae': data.get('mae', 0),
                        'mfe': data.get('mfe', 0),
                        # Scores
                        'confluence': entry_data.get('confluence', 0),
                        'menthorq_score': entry_data.get('menthorq_score', 0),
                        'orderflow_score': entry_data.get('orderflow_score', 0),
                        'context_score': entry_data.get('context_score', 0),
                        'strategy': entry_data.get('strategy', 'UNKNOWN'),
                    }

                    # Filtrer les trades corrompus (prix absurdes)
                    if abs(pnl_usd) < 10000 and trade['menthorq_score'] > 0:
                        trades.append(trade)

                    del entries[symbol]

    return trades

def analyze_trend_alignment(trade: Dict) -> str:
    """
    Determine si le trade est en TENDANCE ou CONTRE-TENDANCE
    Basé sur la direction et les niveaux MenthorQ

    Heuristique:
    - Si LONG avec OrderFlow positif (>0.25) = TENDANCE
    - Si SHORT avec OrderFlow positif (>0.25) = CONTRE-TENDANCE
    - Si OrderFlow moyen (0.20-0.25) = NEUTRE
    """
    direction = trade['direction']
    orderflow = trade['orderflow_score']

    # OrderFlow indique la pression acheteuse/vendeuse
    # >0.25 = forte pression dans un sens
    if orderflow >= 0.28:
        if direction == 'LONG':
            return 'AVEC_TENDANCE'  # Achat avec forte pression acheteuse
        else:
            return 'CONTRE_TENDANCE'  # Vente avec forte pression acheteuse
    elif orderflow <= 0.18:
        if direction == 'SHORT':
            return 'AVEC_TENDANCE'  # Vente avec faible pression acheteuse
        else:
            return 'CONTRE_TENDANCE'  # Achat avec faible pression acheteuse
    else:
        return 'NEUTRE'

def main():
    print("=" * 80)
    print("[ANALYSE MULTI-JOURS] TRADES MIA - DECEMBRE 2025")
    print("=" * 80)

    # Collecter tous les trades
    all_trades = []
    trades_by_date = {}

    for date in DATES:
        filepath = os.path.join(LOGS_DIR, f"trades_{date}.log")
        trades = parse_log_file(filepath)
        if trades:
            trades_by_date[date] = trades
            all_trades.extend(trades)
            print(f"[OK] {date}: {len(trades)} trades ML_3Layer")
        else:
            print(f"[--] {date}: Aucun trade")

    if not all_trades:
        print("\n[ERREUR] Aucun trade trouve!")
        return

    print(f"\n[TOTAL] {len(all_trades)} trades analyses sur {len(trades_by_date)} jours")

    # Separer WINS et LOSSES
    wins = [t for t in all_trades if t['is_win']]
    losses = [t for t in all_trades if not t['is_win']]

    print(f"\n[STATS GLOBALES]")
    print(f"   [WIN]  Gagnants:  {len(wins)} ({100*len(wins)/len(all_trades):.1f}%)")
    print(f"   [LOSS] Perdants:  {len(losses)} ({100*len(losses)/len(all_trades):.1f}%)")

    # Analyse par symbole
    print(f"\n[STATS PAR SYMBOLE]")
    for symbol in ['ES', 'NQ']:
        sym_trades = [t for t in all_trades if t['symbol'] == symbol]
        sym_wins = [t for t in sym_trades if t['is_win']]
        if sym_trades:
            wr = 100 * len(sym_wins) / len(sym_trades)
            print(f"   {symbol}: {len(sym_trades)} trades | WR: {wr:.1f}% | Wins: {len(sym_wins)}")

    # Analyse par direction
    print(f"\n[STATS PAR DIRECTION]")
    for direction in ['LONG', 'SHORT']:
        dir_trades = [t for t in all_trades if t['direction'] == direction]
        dir_wins = [t for t in dir_trades if t['is_win']]
        if dir_trades:
            wr = 100 * len(dir_wins) / len(dir_trades)
            print(f"   {direction}: {len(dir_trades)} trades | WR: {wr:.1f}% | Wins: {len(dir_wins)}")

    # ============================================================
    # ANALYSE TENDANCE vs CONTRE-TENDANCE
    # ============================================================
    print(f"\n{'='*80}")
    print("[ANALYSE] TENDANCE vs CONTRE-TENDANCE")
    print("=" * 80)

    for trade in all_trades:
        trade['trend_alignment'] = analyze_trend_alignment(trade)

    trend_stats = defaultdict(lambda: {'wins': 0, 'losses': 0})
    for trade in all_trades:
        alignment = trade['trend_alignment']
        if trade['is_win']:
            trend_stats[alignment]['wins'] += 1
        else:
            trend_stats[alignment]['losses'] += 1

    for alignment, stats in sorted(trend_stats.items()):
        total = stats['wins'] + stats['losses']
        wr = 100 * stats['wins'] / total if total > 0 else 0
        print(f"   {alignment:18} | {total:3} trades | WR: {wr:5.1f}% | W:{stats['wins']:2} L:{stats['losses']:2}")

    # ============================================================
    # SPLIT 80/20 POUR BACKTEST/VALIDATION
    # ============================================================
    print(f"\n{'='*80}")
    print("[SPLIT] 80% BACKTEST / 20% VALIDATION")
    print("=" * 80)

    # Shuffle pour randomiser
    random.seed(42)  # Pour reproductibilite
    shuffled = all_trades.copy()
    random.shuffle(shuffled)

    split_idx = int(len(shuffled) * 0.8)
    train_set = shuffled[:split_idx]
    valid_set = shuffled[split_idx:]

    train_wins = [t for t in train_set if t['is_win']]
    valid_wins = [t for t in valid_set if t['is_win']]

    print(f"   TRAIN (80%): {len(train_set)} trades | WR: {100*len(train_wins)/len(train_set):.1f}%")
    print(f"   VALID (20%): {len(valid_set)} trades | WR: {100*len(valid_wins)/len(valid_set):.1f}%")

    # ============================================================
    # ANALYSE DES SCORES: TRAIN SET
    # ============================================================
    print(f"\n{'='*80}")
    print("[ANALYSE SCORES] SET D'ENTRAINEMENT (80%)")
    print("=" * 80)

    train_wins_list = [t for t in train_set if t['is_win']]
    train_losses_list = [t for t in train_set if not t['is_win']]

    metrics = ['menthorq_score', 'orderflow_score', 'context_score', 'confluence']
    metric_labels = {
        'menthorq_score': 'MenthorQ (L1)',
        'orderflow_score': 'OrderFlow (L2)',
        'context_score': 'Context (L3)',
        'confluence': 'Confluence'
    }

    print(f"\n{'METRIQUE':<18} | {'WINS':>10} | {'LOSSES':>10} | {'DIFF':>10} | {'%DIFF':>8}")
    print("-" * 70)

    thresholds_proposed = {}

    for metric in metrics:
        win_vals = [t[metric] for t in train_wins_list if t[metric] > 0]
        loss_vals = [t[metric] for t in train_losses_list if t[metric] > 0]

        if win_vals and loss_vals:
            win_avg = sum(win_vals) / len(win_vals)
            loss_avg = sum(loss_vals) / len(loss_vals)
            diff = win_avg - loss_avg
            pct_diff = 100 * diff / loss_avg if loss_avg > 0 else 0

            print(f"{metric_labels[metric]:<18} | {win_avg:>10.3f} | {loss_avg:>10.3f} | {diff:>+10.3f} | {pct_diff:>+7.1f}%")

            # Proposer seuil = min des wins (conservateur)
            thresholds_proposed[metric] = min(win_vals)

    # ============================================================
    # SEUILS RECOMMANDES
    # ============================================================
    print(f"\n{'='*80}")
    print("[SEUILS] RECOMMANDES (basé sur SET D'ENTRAINEMENT)")
    print("=" * 80)

    print(f"\n[L1] MenthorQ Score:")
    win_mq = [t['menthorq_score'] for t in train_wins_list if t['menthorq_score'] > 0]
    loss_mq = [t['menthorq_score'] for t in train_losses_list if t['menthorq_score'] > 0]
    if win_mq:
        print(f"     Wins:   min={min(win_mq):.3f} | max={max(win_mq):.3f} | avg={sum(win_mq)/len(win_mq):.3f}")
    if loss_mq:
        print(f"     Losses: min={min(loss_mq):.3f} | max={max(loss_mq):.3f} | avg={sum(loss_mq)/len(loss_mq):.3f}")
    proposed_mq = min(win_mq) if win_mq else 0.55
    print(f"     -> SEUIL PROPOSE: {proposed_mq:.2f}")

    print(f"\n[L2] OrderFlow Score:")
    win_of = [t['orderflow_score'] for t in train_wins_list if t['orderflow_score'] > 0]
    loss_of = [t['orderflow_score'] for t in train_losses_list if t['orderflow_score'] > 0]
    if win_of:
        print(f"     Wins:   min={min(win_of):.3f} | max={max(win_of):.3f} | avg={sum(win_of)/len(win_of):.3f}")
    if loss_of:
        print(f"     Losses: min={min(loss_of):.3f} | max={max(loss_of):.3f} | avg={sum(loss_of)/len(loss_of):.3f}")
    proposed_of = min(win_of) if win_of else 0.20
    print(f"     -> SEUIL PROPOSE: {proposed_of:.2f}")

    print(f"\n[L3] Context Score:")
    win_ctx = [t['context_score'] for t in train_wins_list if t['context_score'] > 0]
    loss_ctx = [t['context_score'] for t in train_losses_list if t['context_score'] > 0]
    if win_ctx:
        print(f"     Wins:   min={min(win_ctx):.3f} | max={max(win_ctx):.3f} | avg={sum(win_ctx)/len(win_ctx):.3f}")
    if loss_ctx:
        print(f"     Losses: min={min(loss_ctx):.3f} | max={max(loss_ctx):.3f} | avg={sum(loss_ctx)/len(loss_ctx):.3f}")
    proposed_ctx = min(win_ctx) if win_ctx else 0.16
    print(f"     -> SEUIL PROPOSE: {proposed_ctx:.2f}")

    print(f"\n[CONF] Confluence Totale:")
    win_conf = [t['confluence'] for t in train_wins_list if t['confluence'] > 0]
    loss_conf = [t['confluence'] for t in train_losses_list if t['confluence'] > 0]
    if win_conf:
        print(f"     Wins:   min={min(win_conf):.3f} | max={max(win_conf):.3f} | avg={sum(win_conf)/len(win_conf):.3f}")
    if loss_conf:
        print(f"     Losses: min={min(loss_conf):.3f} | max={max(loss_conf):.3f} | avg={sum(loss_conf)/len(loss_conf):.3f}")
    proposed_conf = min(win_conf) if win_conf else 0.95
    print(f"     -> SEUIL PROPOSE: {proposed_conf:.2f}")

    # ============================================================
    # VALIDATION SUR SET 20%
    # ============================================================
    print(f"\n{'='*80}")
    print("[VALIDATION] TEST DES SEUILS SUR SET 20%")
    print("=" * 80)

    # Seuils conservateurs (basés sur minimum des wins)
    seuils_conservateurs = {
        'menthorq_score': proposed_mq,
        'orderflow_score': proposed_of,
        'context_score': proposed_ctx,
        'confluence': proposed_conf
    }

    # Seuils agressifs (basés sur moyenne des wins - 1 std)
    win_mq_avg = sum(win_mq) / len(win_mq) if win_mq else 0.60
    win_of_avg = sum(win_of) / len(win_of) if win_of else 0.24
    win_ctx_avg = sum(win_ctx) / len(win_ctx) if win_ctx else 0.18
    win_conf_avg = sum(win_conf) / len(win_conf) if win_conf else 1.05

    seuils_agressifs = {
        'menthorq_score': win_mq_avg * 0.9,  # 90% de la moyenne
        'orderflow_score': win_of_avg * 0.9,
        'context_score': win_ctx_avg * 0.9,
        'confluence': win_conf_avg * 0.9
    }

    print(f"\n[TEST 1] Seuils CONSERVATEURS (min des wins)")
    print(f"         MenthorQ >= {proposed_mq:.2f}, OrderFlow >= {proposed_of:.2f}")
    print(f"         Context >= {proposed_ctx:.2f}, Confluence >= {proposed_conf:.2f}")

    passed_conservative = []
    for t in valid_set:
        if (t['menthorq_score'] >= proposed_mq and
            t['orderflow_score'] >= proposed_of and
            t['context_score'] >= proposed_ctx and
            t['confluence'] >= proposed_conf):
            passed_conservative.append(t)

    if passed_conservative:
        wins_pass = [t for t in passed_conservative if t['is_win']]
        wr = 100 * len(wins_pass) / len(passed_conservative)
        print(f"         Trades passés: {len(passed_conservative)}/{len(valid_set)} ({100*len(passed_conservative)/len(valid_set):.1f}%)")
        print(f"         Win Rate: {wr:.1f}% ({len(wins_pass)}W / {len(passed_conservative)-len(wins_pass)}L)")
    else:
        print(f"         [WARN] Aucun trade ne passe ces seuils!")

    print(f"\n[TEST 2] Seuils MODERÉS (90% de la moyenne des wins)")
    print(f"         MenthorQ >= {seuils_agressifs['menthorq_score']:.2f}, OrderFlow >= {seuils_agressifs['orderflow_score']:.2f}")
    print(f"         Context >= {seuils_agressifs['context_score']:.2f}, Confluence >= {seuils_agressifs['confluence']:.2f}")

    passed_moderate = []
    for t in valid_set:
        if (t['menthorq_score'] >= seuils_agressifs['menthorq_score'] and
            t['orderflow_score'] >= seuils_agressifs['orderflow_score'] and
            t['context_score'] >= seuils_agressifs['context_score'] and
            t['confluence'] >= seuils_agressifs['confluence']):
            passed_moderate.append(t)

    if passed_moderate:
        wins_pass = [t for t in passed_moderate if t['is_win']]
        wr = 100 * len(wins_pass) / len(passed_moderate)
        print(f"         Trades passés: {len(passed_moderate)}/{len(valid_set)} ({100*len(passed_moderate)/len(valid_set):.1f}%)")
        print(f"         Win Rate: {wr:.1f}% ({len(wins_pass)}W / {len(passed_moderate)-len(wins_pass)}L)")
    else:
        print(f"         [WARN] Aucun trade ne passe ces seuils!")

    # Test avec seuils actuels du bot
    print(f"\n[TEST 3] Seuils ACTUELS du bot")
    print(f"         Confluence >= 0.35 (seul critere actuel)")

    passed_current = [t for t in valid_set if t['confluence'] >= 0.35]
    if passed_current:
        wins_pass = [t for t in passed_current if t['is_win']]
        wr = 100 * len(wins_pass) / len(passed_current)
        print(f"         Trades passés: {len(passed_current)}/{len(valid_set)} ({100*len(passed_current)/len(valid_set):.1f}%)")
        print(f"         Win Rate: {wr:.1f}% ({len(wins_pass)}W / {len(passed_current)-len(wins_pass)}L)")

    # ============================================================
    # ANALYSE DES PROBLEMES IDENTIFIES
    # ============================================================
    print(f"\n{'='*80}")
    print("[PROBLEMES] PATTERNS DES TRADES PERDANTS")
    print("=" * 80)

    # OrderFlow faible
    low_of_losses = [t for t in losses if t['orderflow_score'] < 0.20]
    print(f"\n[1] OrderFlow < 0.20: {len(low_of_losses)}/{len(losses)} losses ({100*len(low_of_losses)/len(losses):.1f}%)")

    # Context faible
    low_ctx_losses = [t for t in losses if t['context_score'] < 0.16]
    print(f"[2] Context < 0.16:   {len(low_ctx_losses)}/{len(losses)} losses ({100*len(low_ctx_losses)/len(losses):.1f}%)")

    # SHORT en contre-tendance
    short_losses = [t for t in losses if t['direction'] == 'SHORT']
    ct_shorts = [t for t in short_losses if t.get('trend_alignment') == 'CONTRE_TENDANCE']
    if short_losses:
        print(f"[3] SHORT contre-tendance: {len(ct_shorts)}/{len(short_losses)} ({100*len(ct_shorts)/len(short_losses):.1f}%)")

    # Confluence faible mais trade pris
    low_conf_losses = [t for t in losses if t['confluence'] < 1.00]
    print(f"[4] Confluence < 1.00: {len(low_conf_losses)}/{len(losses)} losses ({100*len(low_conf_losses)/len(losses):.1f}%)")

    # ============================================================
    # RECOMMANDATIONS FINALES
    # ============================================================
    print(f"\n{'='*80}")
    print("[RECOMMANDATIONS] POUR AMELIORER LE WIN RATE")
    print("=" * 80)

    print(f"""
[1] AUGMENTER LE SEUIL ORDERFLOW:
    Actuel: ~0.17 -> Proposé: 0.20+
    Impact: Filtre {100*len([t for t in all_trades if t['orderflow_score'] < 0.20])/len(all_trades):.1f}% des trades

[2] AUGMENTER LE SEUIL CONTEXT:
    Actuel: ~0.12 -> Proposé: 0.16+
    Impact: Filtre {100*len([t for t in all_trades if t['context_score'] < 0.16])/len(all_trades):.1f}% des trades

[3] AUGMENTER LE SEUIL CONFLUENCE:
    Actuel: 0.35 -> Proposé: 0.95+
    Impact: Filtre {100*len([t for t in all_trades if t['confluence'] < 0.95])/len(all_trades):.1f}% des trades

[4] FILTRER LES SHORTS EN CONTRE-TENDANCE:
    Exiger OrderFlow >= 0.26 pour les SHORTs
    Ou désactiver SHORT si OrderFlow > 0.25

[5] SEUILS PROPOSES POUR BACKTEST:
""")

    print(f"""
# ============================================
# SEUILS PROPOSES POUR unified_thresholds.py
# ============================================

MIN_LAYER_CONFIDENCE = {{
    'ES': {{
        'layer1': {proposed_mq:.2f},   # MenthorQ (min des wins)
        'layer2': {proposed_of:.2f},   # OrderFlow (min des wins)
        'layer3': {proposed_ctx:.2f},   # Context (min des wins)
    }},
    'NQ': {{
        'layer1': {proposed_mq:.2f},
        'layer2': {proposed_of:.2f},
        'layer3': {proposed_ctx:.2f},
    }}
}}

MIN_TOTAL_CONFIDENCE = {{
    'ES': {proposed_conf:.2f},
    'NQ': {proposed_conf:.2f},
}}

# OU version plus aggressive (90% moyenne):
MIN_LAYER_CONFIDENCE_AGGRESSIVE = {{
    'ES': {{
        'layer1': {win_mq_avg*0.9:.2f},
        'layer2': {win_of_avg*0.9:.2f},
        'layer3': {win_ctx_avg*0.9:.2f},
    }},
}}
""")

    print("=" * 80)
    print("[FIN] Analyse terminee - Prochaine etape: Backtest avec ces seuils")
    print("=" * 80)

if __name__ == "__main__":
    main()

