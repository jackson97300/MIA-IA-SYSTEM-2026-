# -*- coding: utf-8 -*-
"""
BACKTEST SESSIONS US V2 - Recherche de seuils optimaux
"""

import os
import sys
import re
from typing import List, Dict
from collections import defaultdict
from datetime import datetime, time
import itertools

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

LOGS_DIR = r"D:\MIA_IA_system\logs_advanced\trades"
DATES = ["20251204", "20251205", "20251208", "20251209", "20251210",
         "20251211", "20251212", "20251216", "20251217"]

SESSIONS = {
    'LONDON': {'start': time(8, 0), 'end': time(11, 0)},
    'US_MORNING': {'start': time(15, 50), 'end': time(17, 0)},
    'LUNCH': {'start': time(17, 0), 'end': time(19, 30)},
    'US_POWER': {'start': time(20, 0), 'end': time(21, 30)},
}

def get_session(trade_time: time) -> str:
    for session_name, hours in SESSIONS.items():
        if hours['start'] <= trade_time <= hours['end']:
            return session_name
    if trade_time < time(8, 0):
        return 'ASIA'
    elif trade_time > time(21, 30):
        return 'OFF_HOURS'
    return 'OTHER'

def parse_log_file_with_time(filepath: str) -> List[Dict]:
    trades = []
    entries = {}
    entry_times = {}

    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            time_match = re.match(r'^(\d{2}:\d{2}:\d{2})', line)
            if not time_match:
                continue

            trade_time = datetime.strptime(time_match.group(1), '%H:%M:%S').time()

            match = re.search(r'\[(\w+)\]\s+(ENTRY|EXIT)\s+\|\s+({.*})', line)
            if not match:
                continue

            symbol = match.group(1)
            action = match.group(2)

            try:
                data = eval(match.group(3))
            except:
                continue

            if action == 'ENTRY':
                if data.get('strategy') == 'ML_3Layer':
                    entries[symbol] = data
                    entry_times[symbol] = trade_time
            elif action == 'EXIT':
                if symbol in entries:
                    entry_data = entries[symbol]
                    pnl_usd = data.get('pnl_usd', 0) or 0

                    trade = {
                        'symbol': symbol,
                        'direction': entry_data.get('direction', 'UNKNOWN'),
                        'pnl_usd': pnl_usd,
                        'is_win': pnl_usd > 0,
                        'confluence': entry_data.get('confluence', 0),
                        'menthorq_score': entry_data.get('menthorq_score', 0),
                        'orderflow_score': entry_data.get('orderflow_score', 0),
                        'context_score': entry_data.get('context_score', 0),
                        'entry_time': entry_times.get(symbol, trade_time),
                        'session': get_session(entry_times.get(symbol, trade_time)),
                    }

                    if abs(pnl_usd) < 10000 and trade['menthorq_score'] > 0:
                        trades.append(trade)

                    del entries[symbol]
                    if symbol in entry_times:
                        del entry_times[symbol]

    return trades

def apply_filter(trades: List[Dict], seuils: Dict) -> List[Dict]:
    filtered = []
    for t in trades:
        if (t['menthorq_score'] >= seuils['menthorq_min'] and
            t['orderflow_score'] >= seuils['orderflow_min'] and
            t['context_score'] >= seuils['context_min'] and
            t['confluence'] >= seuils['confluence_min']):
            filtered.append(t)
    return filtered

def calculate_metrics(trades: List[Dict]) -> Dict:
    if not trades:
        return {'count': 0, 'wins': 0, 'wr': 0, 'pnl': 0, 'pf': 0}

    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]

    win_pnl = sum(t['pnl_usd'] for t in wins) if wins else 0
    loss_pnl = abs(sum(t['pnl_usd'] for t in losses)) if losses else 0

    return {
        'count': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'wr': 100 * len(wins) / len(trades),
        'pnl': sum(t['pnl_usd'] for t in trades),
        'pf': win_pnl / loss_pnl if loss_pnl > 0 else 0
    }

def main():
    print("=" * 100)
    print("[BACKTEST V2] RECHERCHE DE SEUILS OPTIMAUX POUR SESSIONS US")
    print("=" * 100)

    # Charger tous les trades
    all_trades = []
    for date in DATES:
        filepath = os.path.join(LOGS_DIR, f"trades_{date}.log")
        trades = parse_log_file_with_time(filepath)
        all_trades.extend(trades)

    # Filtrer sessions US
    us_trades = [t for t in all_trades if t['session'] in ['US_MORNING', 'US_POWER']]

    print(f"\n[DATA] {len(us_trades)} trades sur sessions US")

    base = calculate_metrics(us_trades)
    print(f"[BASE] WR: {base['wr']:.1f}% | P&L: ${base['pnl']:.2f}")

    # ============================================
    # GRID SEARCH - Trouver les meilleurs seuils
    # ============================================
    print(f"\n{'='*100}")
    print("[GRID SEARCH] Test de multiples configurations")
    print("=" * 100)

    # Valeurs à tester
    mq_values = [0.0, 0.50, 0.55, 0.60, 0.65, 0.70]
    of_values = [0.0, 0.20, 0.24, 0.28]
    ctx_values = [0.0, 0.16, 0.18, 0.20]
    conf_values = [0.35, 0.90, 1.00, 1.10]

    results = []

    for mq, of, ctx, conf in itertools.product(mq_values, of_values, ctx_values, conf_values):
        seuils = {
            'menthorq_min': mq,
            'orderflow_min': of,
            'context_min': ctx,
            'confluence_min': conf,
        }

        filtered = apply_filter(us_trades, seuils)
        metrics = calculate_metrics(filtered)

        if metrics['count'] >= 10:  # Minimum 10 trades pour être significatif
            results.append({
                'seuils': seuils,
                'metrics': metrics,
                'score': metrics['wr'] * (metrics['count'] / len(us_trades)) ** 0.5  # Score composite
            })

    # Trier par score
    results.sort(key=lambda x: x['score'], reverse=True)

    print(f"\n[TOP 10] Meilleures configurations pour sessions US:")
    print(f"\n{'MQ':>5} | {'OF':>5} | {'CTX':>5} | {'CONF':>5} | {'TRADES':>7} | {'WR':>6} | {'P&L':>10} | {'PF':>5}")
    print("-" * 75)

    for r in results[:10]:
        s = r['seuils']
        m = r['metrics']
        print(f"{s['menthorq_min']:>5.2f} | {s['orderflow_min']:>5.2f} | {s['context_min']:>5.2f} | {s['confluence_min']:>5.2f} | {m['count']:>7} | {m['wr']:>5.1f}% | ${m['pnl']:>8.2f} | {m['pf']:>5.2f}")

    # ============================================
    # ANALYSE DES PATTERNS GAGNANTS
    # ============================================
    print(f"\n{'='*100}")
    print("[PATTERNS] ANALYSE DES TRADES GAGNANTS vs PERDANTS")
    print("=" * 100)

    wins = [t for t in us_trades if t['is_win']]
    losses = [t for t in us_trades if not t['is_win']]

    print(f"\n[SCORES MOYENS]")
    print(f"{'METRIQUE':<15} | {'WINS':>10} | {'LOSSES':>10} | {'DIFF':>10}")
    print("-" * 55)

    for metric in ['menthorq_score', 'orderflow_score', 'context_score', 'confluence']:
        win_avg = sum(t[metric] for t in wins) / len(wins) if wins else 0
        loss_avg = sum(t[metric] for t in losses) / len(losses) if losses else 0
        diff = win_avg - loss_avg
        print(f"{metric:<15} | {win_avg:>10.3f} | {loss_avg:>10.3f} | {diff:>+10.3f}")

    # Analyse par direction
    print(f"\n[PAR DIRECTION SUR SESSIONS US]")
    for direction in ['LONG', 'SHORT']:
        dir_trades = [t for t in us_trades if t['direction'] == direction]
        if dir_trades:
            m = calculate_metrics(dir_trades)
            print(f"   {direction}: {m['count']} trades | WR: {m['wr']:.1f}% | P&L: ${m['pnl']:.2f}")

    # ============================================
    # RECOMMANDATION OPTIMALE POUR US
    # ============================================
    print(f"\n{'='*100}")
    print("[RECOMMANDATION] SEUILS OPTIMAUX POUR SESSIONS US")
    print("=" * 100)

    if results:
        best = results[0]
        s = best['seuils']
        m = best['metrics']

        # Trouver config avec meilleur P&L parmi ceux avec WR > 50%
        high_wr = [r for r in results if r['metrics']['wr'] >= 50 and r['metrics']['count'] >= 10]
        if high_wr:
            best_pnl = max(high_wr, key=lambda x: x['metrics']['pnl'])
            s = best_pnl['seuils']
            m = best_pnl['metrics']

        print(f"""
[MEILLEURE CONFIG POUR SESSIONS US]

Seuils:
   - MenthorQ  >= {s['menthorq_min']:.2f}
   - OrderFlow >= {s['orderflow_min']:.2f}
   - Context   >= {s['context_min']:.2f}
   - Confluence >= {s['confluence_min']:.2f}

Performance attendue:
   - Win Rate: {m['wr']:.1f}%
   - Trades:   {m['count']} ({100*m['count']/len(us_trades):.0f}% rétention)
   - P&L:      ${m['pnl']:.2f}
   - PF:       {m['pf']:.2f}

Amélioration vs actuel:
   - WR:  {base['wr']:.1f}% -> {m['wr']:.1f}% ({m['wr']-base['wr']:+.1f}%)
   - P&L: ${base['pnl']:.2f} -> ${m['pnl']:.2f} ({m['pnl']-base['pnl']:+.2f})
""")

    # Test avec focus SHORT (souvent problématique)
    print(f"\n{'='*100}")
    print("[ANALYSE] PROBLEME POTENTIEL AVEC LES SHORTS")
    print("=" * 100)

    short_trades = [t for t in us_trades if t['direction'] == 'SHORT']
    long_trades = [t for t in us_trades if t['direction'] == 'LONG']

    print(f"\n[SANS FILTRE]")
    sm = calculate_metrics(short_trades)
    lm = calculate_metrics(long_trades)
    print(f"   SHORT: {sm['count']} trades | WR: {sm['wr']:.1f}% | P&L: ${sm['pnl']:.2f}")
    print(f"   LONG:  {lm['count']} trades | WR: {lm['wr']:.1f}% | P&L: ${lm['pnl']:.2f}")

    # Test: bloquer les shorts avec OF < 0.26
    print(f"\n[TEST] Bloquer SHORT si OrderFlow < 0.26:")
    short_filtered = [t for t in short_trades if t['orderflow_score'] >= 0.26]
    sm2 = calculate_metrics(short_filtered)
    if sm2['count'] > 0:
        print(f"   SHORT filtré: {sm2['count']} trades | WR: {sm2['wr']:.1f}% | P&L: ${sm2['pnl']:.2f}")

    # Combiner LONG normal + SHORT filtré
    combined = long_trades + short_filtered
    cm = calculate_metrics(combined)
    print(f"\n[COMBINÉ] LONG (tous) + SHORT (OF>=0.26):")
    print(f"   Total: {cm['count']} trades | WR: {cm['wr']:.1f}% | P&L: ${cm['pnl']:.2f}")

    print(f"\n{'='*100}")
    print("[FIN] Backtest sessions US terminé")
    print("=" * 100)

if __name__ == "__main__":
    main()

