# -*- coding: utf-8 -*-
"""
BACKTEST PAR SESSION DE TRADING
===============================
Analyse des seuils sur les sessions US uniquement:
- US Morning: 15:50 - 17:00 (Paris)
- US Power Hour: 20:00 - 21:30 (Paris)
"""

import os
import sys
import re
from typing import List, Dict
from collections import defaultdict
from datetime import datetime, time

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

LOGS_DIR = r"D:\MIA_IA_system\logs_advanced\trades"
DATES = [
    "20251204", "20251205", "20251208", "20251209", "20251210",
    "20251211", "20251212", "20251216", "20251217"
]

# Sessions de trading (heure Paris)
SESSIONS = {
    'LONDON': {'start': time(8, 0), 'end': time(11, 0)},
    'US_MORNING': {'start': time(15, 50), 'end': time(17, 0)},
    'LUNCH': {'start': time(17, 0), 'end': time(19, 30)},  # Pas de trading
    'US_POWER': {'start': time(20, 0), 'end': time(21, 30)},
}

# Seuils à tester
SEUILS_MODERE = {
    'menthorq_min': 0.58,
    'orderflow_min': 0.22,
    'context_min': 0.16,
    'confluence_min': 0.96,
}

SEUILS_ACTUEL = {
    'menthorq_min': 0.0,
    'orderflow_min': 0.0,
    'context_min': 0.0,
    'confluence_min': 0.35,
}

def get_session(trade_time: time) -> str:
    """Détermine la session pour une heure donnée"""
    for session_name, hours in SESSIONS.items():
        if hours['start'] <= trade_time <= hours['end']:
            return session_name

    # Hors sessions principales
    if trade_time < time(8, 0):
        return 'ASIA'
    elif trade_time > time(21, 30):
        return 'OFF_HOURS'
    else:
        return 'OTHER'

def parse_log_file_with_time(filepath: str) -> List[Dict]:
    """Parse un fichier de log avec extraction de l'heure"""
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

            # Pattern: HH:MM:SS - INFO - [SYMBOL] ENTRY/EXIT | {...}
            time_match = re.match(r'^(\d{2}:\d{2}:\d{2})', line)
            if not time_match:
                continue

            trade_time_str = time_match.group(1)
            trade_time = datetime.strptime(trade_time_str, '%H:%M:%S').time()

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

                    entry_time = entry_times.get(symbol, trade_time)
                    session = get_session(entry_time)

                    trade = {
                        'symbol': symbol,
                        'direction': entry_data.get('direction', 'UNKNOWN'),
                        'pnl_usd': pnl_usd,
                        'is_win': pnl_usd > 0,
                        'confluence': entry_data.get('confluence', 0),
                        'menthorq_score': entry_data.get('menthorq_score', 0),
                        'orderflow_score': entry_data.get('orderflow_score', 0),
                        'context_score': entry_data.get('context_score', 0),
                        'entry_time': entry_time,
                        'session': session,
                    }

                    # Filtrer trades corrompus
                    if abs(pnl_usd) < 10000 and trade['menthorq_score'] > 0:
                        trades.append(trade)

                    del entries[symbol]
                    if symbol in entry_times:
                        del entry_times[symbol]

    return trades

def apply_filter(trades: List[Dict], seuils: Dict) -> List[Dict]:
    """Applique les seuils"""
    filtered = []
    for t in trades:
        if (t['menthorq_score'] >= seuils['menthorq_min'] and
            t['orderflow_score'] >= seuils['orderflow_min'] and
            t['context_score'] >= seuils['context_min'] and
            t['confluence'] >= seuils['confluence_min']):
            filtered.append(t)
    return filtered

def calculate_metrics(trades: List[Dict]) -> Dict:
    """Calcule les métriques"""
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
    print("[BACKTEST] ANALYSE PAR SESSION DE TRADING")
    print("=" * 100)

    # Charger tous les trades
    all_trades = []
    for date in DATES:
        filepath = os.path.join(LOGS_DIR, f"trades_{date}.log")
        trades = parse_log_file_with_time(filepath)
        all_trades.extend(trades)

    print(f"\n[DATA] {len(all_trades)} trades ML_3Layer chargés")

    # Répartition par session
    print(f"\n{'='*100}")
    print("[REPARTITION] TRADES PAR SESSION")
    print("=" * 100)

    session_trades = defaultdict(list)
    for t in all_trades:
        session_trades[t['session']].append(t)

    print(f"\n{'SESSION':<15} | {'TRADES':>7} | {'WR ACTUEL':>10} | {'P&L ACTUEL':>12}")
    print("-" * 60)

    for session in ['LONDON', 'US_MORNING', 'US_POWER', 'OTHER', 'ASIA', 'OFF_HOURS', 'LUNCH']:
        trades = session_trades.get(session, [])
        if trades:
            metrics = calculate_metrics(trades)
            print(f"{session:<15} | {metrics['count']:>7} | {metrics['wr']:>9.1f}% | ${metrics['pnl']:>10.2f}")

    # ============================================
    # FOCUS SUR LES SESSIONS US
    # ============================================
    print(f"\n{'='*100}")
    print("[FOCUS] SESSIONS US (US_MORNING + US_POWER)")
    print("=" * 100)

    us_trades = session_trades['US_MORNING'] + session_trades['US_POWER']

    if not us_trades:
        print("\n[WARN] Aucun trade sur les sessions US!")
        return

    print(f"\n[TOTAL] {len(us_trades)} trades sur sessions US")
    print(f"   - US_MORNING (15:50-17:00): {len(session_trades['US_MORNING'])} trades")
    print(f"   - US_POWER (20:00-21:30):   {len(session_trades['US_POWER'])} trades")

    # ============================================
    # COMPARAISON SEUILS ACTUEL vs MODERE
    # ============================================
    print(f"\n{'='*100}")
    print("[COMPARAISON] SEUILS ACTUEL vs MODERE SUR SESSIONS US")
    print("=" * 100)

    # Seuils actuels
    filtered_actuel = apply_filter(us_trades, SEUILS_ACTUEL)
    metrics_actuel = calculate_metrics(filtered_actuel)

    # Seuils modérés
    filtered_modere = apply_filter(us_trades, SEUILS_MODERE)
    metrics_modere = calculate_metrics(filtered_modere)

    print(f"\n{'CONFIG':<15} | {'TRADES':>7} | {'WINS':>5} | {'WR':>7} | {'P&L':>12} | {'PF':>6}")
    print("-" * 70)
    print(f"{'ACTUEL':<15} | {metrics_actuel['count']:>7} | {metrics_actuel['wins']:>5} | {metrics_actuel['wr']:>6.1f}% | ${metrics_actuel['pnl']:>10.2f} | {metrics_actuel['pf']:>5.2f}")
    print(f"{'MODERE':<15} | {metrics_modere['count']:>7} | {metrics_modere['wins']:>5} | {metrics_modere['wr']:>6.1f}% | ${metrics_modere['pnl']:>10.2f} | {metrics_modere['pf']:>5.2f}")

    # Amélioration
    if metrics_actuel['count'] > 0 and metrics_modere['count'] > 0:
        wr_gain = metrics_modere['wr'] - metrics_actuel['wr']
        pnl_gain = metrics_modere['pnl'] - metrics_actuel['pnl']
        print(f"\n[GAIN] WR: {wr_gain:+.1f}% | P&L: ${pnl_gain:+.2f}")

    # ============================================
    # ANALYSE DETAILLEE PAR SESSION US
    # ============================================
    print(f"\n{'='*100}")
    print("[DETAIL] PAR SESSION US")
    print("=" * 100)

    for session_name in ['US_MORNING', 'US_POWER']:
        session_data = session_trades.get(session_name, [])
        if not session_data:
            continue

        print(f"\n[{session_name}]")

        # Actuel
        filtered = apply_filter(session_data, SEUILS_ACTUEL)
        m = calculate_metrics(filtered)
        print(f"   ACTUEL: {m['count']} trades | WR: {m['wr']:.1f}% | P&L: ${m['pnl']:.2f}")

        # Modéré
        filtered = apply_filter(session_data, SEUILS_MODERE)
        m = calculate_metrics(filtered)
        print(f"   MODERE: {m['count']} trades | WR: {m['wr']:.1f}% | P&L: ${m['pnl']:.2f}")

    # ============================================
    # COMPARAISON US vs AUTRES SESSIONS
    # ============================================
    print(f"\n{'='*100}")
    print("[COMPARAISON] SESSIONS US vs LONDON vs AUTRES")
    print("=" * 100)

    session_groups = {
        'US (Morning+Power)': us_trades,
        'LONDON': session_trades.get('LONDON', []),
        'OFF_HOURS/ASIA': session_trades.get('OFF_HOURS', []) + session_trades.get('ASIA', []) + session_trades.get('OTHER', []),
    }

    print(f"\n{'SESSION':<20} | {'ACTUEL WR':>10} | {'MODERE WR':>10} | {'ACTUEL P&L':>12} | {'MODERE P&L':>12}")
    print("-" * 80)

    for session_name, trades in session_groups.items():
        if not trades:
            continue

        # Actuel
        f_actuel = apply_filter(trades, SEUILS_ACTUEL)
        m_actuel = calculate_metrics(f_actuel)

        # Modéré
        f_modere = apply_filter(trades, SEUILS_MODERE)
        m_modere = calculate_metrics(f_modere)

        print(f"{session_name:<20} | {m_actuel['wr']:>9.1f}% | {m_modere['wr']:>9.1f}% | ${m_actuel['pnl']:>10.2f} | ${m_modere['pnl']:>10.2f}")

    # ============================================
    # TRADES MODERE DETAILLES (Sessions US)
    # ============================================
    print(f"\n{'='*100}")
    print("[DETAIL] TRADES QUI PASSENT LES SEUILS MODERE (Sessions US)")
    print("=" * 100)

    if filtered_modere:
        wins_modere = [t for t in filtered_modere if t['is_win']]
        losses_modere = [t for t in filtered_modere if not t['is_win']]

        print(f"\n[WINS] {len(wins_modere)} trades gagnants:")
        for t in wins_modere[:10]:  # Max 10
            print(f"   {t['symbol']} {t['direction']:<5} | MQ:{t['menthorq_score']:.2f} OF:{t['orderflow_score']:.2f} CTX:{t['context_score']:.2f} | CONF:{t['confluence']:.2f} | P&L: ${t['pnl_usd']:.0f}")

        print(f"\n[LOSSES] {len(losses_modere)} trades perdants:")
        for t in losses_modere[:10]:
            print(f"   {t['symbol']} {t['direction']:<5} | MQ:{t['menthorq_score']:.2f} OF:{t['orderflow_score']:.2f} CTX:{t['context_score']:.2f} | CONF:{t['confluence']:.2f} | P&L: ${t['pnl_usd']:.0f}")

    # ============================================
    # RECOMMANDATION
    # ============================================
    print(f"\n{'='*100}")
    print("[RECOMMANDATION] POUR SESSIONS US")
    print("=" * 100)

    if metrics_modere['count'] > 0 and metrics_modere['wr'] > metrics_actuel['wr']:
        print(f"""
[RESULTAT] Les seuils MODERE FONCTIONNENT sur les sessions US!

Seuils recommandés pour US_MORNING et US_POWER:
   - MenthorQ  >= 0.58
   - OrderFlow >= 0.22
   - Context   >= 0.16
   - Confluence >= 0.96

Impact sur sessions US:
   - Win Rate: {metrics_actuel['wr']:.1f}% -> {metrics_modere['wr']:.1f}% ({metrics_modere['wr']-metrics_actuel['wr']:+.1f}%)
   - Trades:   {metrics_actuel['count']} -> {metrics_modere['count']} ({100*metrics_modere['count']/metrics_actuel['count']:.0f}% rétention)
   - P&L:      ${metrics_actuel['pnl']:.2f} -> ${metrics_modere['pnl']:.2f}
""")
    else:
        print(f"\n[INFO] Les seuils modérés réduisent trop le volume sur les sessions US.")
        print(f"       Considérer des seuils moins stricts pour ces sessions.")

    print("=" * 100)

if __name__ == "__main__":
    main()

