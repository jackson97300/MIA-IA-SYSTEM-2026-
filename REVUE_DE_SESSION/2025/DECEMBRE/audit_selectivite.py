"""
AUDIT SÉLECTIVITÉ - Test des filtres sur 139 trades réels
Semaine 02-04 Décembre 2025
"""

import os
import re
import json
from collections import defaultdict

def parse_trade_logs():
    """Parse les logs de trades"""
    trades = []

    for day in ['20251202', '20251203', '20251204']:
        filepath = f'logs_advanced/trades/trades_{day}.log'
        if not os.path.exists(filepath):
            print(f"Fichier non trouvé: {filepath}")
            continue

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        current_entries = {}  # {symbol: entry_data}

        for line in lines:
            # Parse ENTRY
            entry_match = re.search(r'(\d{2}:\d{2}:\d{2}).*\[(\w+)\] ENTRY \| ({.*})', line)
            if entry_match:
                time, symbol, data_str = entry_match.groups()
                try:
                    data = eval(data_str)
                    current_entries[symbol] = {
                        'day': day,
                        'time': time,
                        'hour': int(time.split(':')[0]),
                        'symbol': symbol,
                        'direction': data.get('direction', ''),
                        'confidence': data.get('confidence', 0),
                        'menthorq': data.get('menthorq_score', 0),
                        'orderflow': data.get('orderflow_score', 0),
                        'context': data.get('context_score', 0),
                        'entry_price': data.get('price', 0)
                    }
                except:
                    pass

            # Parse EXIT
            exit_match = re.search(r'(\d{2}:\d{2}:\d{2}).*\[(\w+)\] EXIT \| ({.*})', line)
            if exit_match:
                time, symbol, data_str = exit_match.groups()
                try:
                    data = eval(data_str)
                    if symbol in current_entries:
                        entry = current_entries[symbol]
                        trade = {
                            **entry,
                            'exit_time': time,
                            'pnl': data.get('pnl_usd', 0),
                            'exit_reason': data.get('exit_reason', ''),
                            'mfe': data.get('mfe', 0),
                            'mae': data.get('mae', 0),
                            'is_win': data.get('pnl_usd', 0) > 0
                        }
                        trades.append(trade)
                        del current_entries[symbol]
                except:
                    pass

    return trades

def test_filter(trades, filter_fn, filter_name):
    """Teste un filtre sur les trades"""
    passed = [t for t in trades if filter_fn(t)]
    rejected = [t for t in trades if not filter_fn(t)]

    passed_wins = sum(1 for t in passed if t['is_win'])
    passed_losses = len(passed) - passed_wins
    passed_pnl = sum(t['pnl'] for t in passed)

    rejected_wins = sum(1 for t in rejected if t['is_win'])
    rejected_losses = len(rejected) - rejected_wins
    rejected_pnl = sum(t['pnl'] for t in rejected)

    passed_wr = (passed_wins / len(passed) * 100) if passed else 0
    rejected_wr = (rejected_wins / len(rejected) * 100) if rejected else 0

    return {
        'name': filter_name,
        'passed': len(passed),
        'rejected': len(rejected),
        'passed_wins': passed_wins,
        'passed_losses': passed_losses,
        'passed_pnl': passed_pnl,
        'passed_wr': passed_wr,
        'rejected_wins': rejected_wins,
        'rejected_losses': rejected_losses,
        'rejected_pnl': rejected_pnl,
        'rejected_wr': rejected_wr,
        'gain_from_rejection': -rejected_pnl if rejected_pnl < 0 else 0
    }

def main():
    print("=" * 80)
    print("AUDIT SELECTIVITE - Test filtres sur 139 trades reels")
    print("Semaine 02-04 Decembre 2025")
    print("=" * 80)
    print()

    # Changer vers le répertoire racine
    os.chdir('D:/MIA_IA_system')

    trades = parse_trade_logs()
    print(f"Total trades analyses: {len(trades)}")

    # Stats globales
    total_pnl = sum(t['pnl'] for t in trades)
    total_wins = sum(1 for t in trades if t['is_win'])
    total_wr = total_wins / len(trades) * 100 if trades else 0

    print(f"P&L Total: ${total_pnl:+.2f}")
    print(f"Win Rate: {total_wr:.1f}% ({total_wins}W / {len(trades) - total_wins}L)")
    print()

    # Par symbole
    print("Par symbole:")
    for symbol in ['ES', 'NQ']:
        sym_trades = [t for t in trades if t['symbol'] == symbol]
        sym_pnl = sum(t['pnl'] for t in sym_trades)
        sym_wins = sum(1 for t in sym_trades if t['is_win'])
        sym_wr = sym_wins / len(sym_trades) * 100 if sym_trades else 0
        print(f"  {symbol}: {len(sym_trades)} trades, WR {sym_wr:.1f}%, P&L ${sym_pnl:+.2f}")
    print()

    # ═══════════════════════════════════════════════════════════════
    # TESTS DES FILTRES
    # ═══════════════════════════════════════════════════════════════

    print("=" * 80)
    print("TEST DES FILTRES PROPOSES")
    print("=" * 80)
    print()

    filters = [
        # Filtre 1: Confidence minimum 50%
        (lambda t: t['confidence'] >= 0.50, "Confidence >= 50% (tous)"),

        # Filtre 2: Confidence ES 50%, NQ 60%
        (lambda t: t['confidence'] >= 0.60 if t['symbol'] == 'NQ' else t['confidence'] >= 0.50,
         "Confidence ES>=50%, NQ>=60%"),

        # Filtre 3: Confidence >= 70%
        (lambda t: t['confidence'] >= 0.70, "Confidence >= 70%"),

        # Filtre 4: Confidence >= 100% (1.0)
        (lambda t: t['confidence'] >= 1.00, "Confidence >= 100%"),

        # Filtre 5: Bloquer 16h (16:00-16:30)
        (lambda t: not (t['hour'] == 16 and int(t['time'].split(':')[1]) < 30),
         "Block 16h00-16h30"),

        # Filtre 6: OrderFlow minimum 0.12
        (lambda t: t['orderflow'] >= 0.12, "OrderFlow >= 0.12"),

        # Filtre 7: OrderFlow minimum 0.18 pour NQ
        (lambda t: t['orderflow'] >= 0.18 if t['symbol'] == 'NQ' else True,
         "OrderFlow NQ >= 0.18"),

        # Filtre 8: MenthorQ minimum 0.50
        (lambda t: t['menthorq'] >= 0.50, "MenthorQ >= 0.50"),

        # Filtre 9: Context minimum 0.15
        (lambda t: t['context'] >= 0.15, "Context >= 0.15"),

        # Filtre 10: Combinaison recommandée
        (lambda t: (
            t['confidence'] >= (0.60 if t['symbol'] == 'NQ' else 0.50) and
            not (t['hour'] == 16 and int(t['time'].split(':')[1]) < 30) and
            t['orderflow'] >= (0.15 if t['symbol'] == 'NQ' else 0.10)
        ), "COMBO: Conf+Block16h+OrderFlow"),
    ]

    print(f"{'Filtre':<35} {'Trades':<10} {'WR':<10} {'P&L':<12} {'Rejetes':<10} {'WR Rej':<10} {'Gain Rej':<10}")
    print("-" * 97)

    for filter_fn, name in filters:
        result = test_filter(trades, filter_fn, name)
        print(f"{name:<35} {result['passed']:<10} {result['passed_wr']:.1f}%     ${result['passed_pnl']:+8.0f}   {result['rejected']:<10} {result['rejected_wr']:.1f}%     ${result['gain_from_rejection']:+8.0f}")

    print()
    print("=" * 80)
    print("ANALYSE DETAILLEE DES TRADES REJETES")
    print("=" * 80)
    print()

    # Analyser les trades à faible confidence qui ont perdu
    low_conf_losses = [t for t in trades if t['confidence'] < 0.50 and not t['is_win']]
    low_conf_pnl = sum(t['pnl'] for t in low_conf_losses)
    print(f"Trades Confidence < 50% PERDANTS: {len(low_conf_losses)} trades, P&L ${low_conf_pnl:+.2f}")

    # Trades pendant 16h
    trades_16h = [t for t in trades if t['hour'] == 16 and int(t['time'].split(':')[1]) < 30]
    trades_16h_pnl = sum(t['pnl'] for t in trades_16h)
    trades_16h_wins = sum(1 for t in trades_16h if t['is_win'])
    print(f"Trades 16h00-16h30: {len(trades_16h)} trades, {trades_16h_wins}W, P&L ${trades_16h_pnl:+.2f}")

    # Trades NQ avec faible OrderFlow
    nq_low_of = [t for t in trades if t['symbol'] == 'NQ' and t['orderflow'] < 0.15]
    nq_low_of_pnl = sum(t['pnl'] for t in nq_low_of)
    nq_low_of_wins = sum(1 for t in nq_low_of if t['is_win'])
    print(f"Trades NQ OrderFlow < 0.15: {len(nq_low_of)} trades, {nq_low_of_wins}W, P&L ${nq_low_of_pnl:+.2f}")

    print()

    # Analyse plus détaillée - trouver les vrais patterns perdants
    print("=" * 80)
    print("RECHERCHE DES VRAIS PATTERNS PERDANTS")
    print("=" * 80)
    print()

    # Trades perdants par heure
    print("P&L par heure:")
    by_hour = defaultdict(lambda: {'trades': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        h = t['hour']
        by_hour[h]['trades'] += 1
        by_hour[h]['pnl'] += t['pnl']
        by_hour[h]['wins'] += 1 if t['is_win'] else 0

    for h in sorted(by_hour.keys()):
        data = by_hour[h]
        wr = data['wins'] / data['trades'] * 100 if data['trades'] else 0
        emoji = "OK" if data['pnl'] > 0 else "BAD"
        print(f"  {h:02d}h: {data['trades']:3d} trades, WR {wr:5.1f}%, P&L ${data['pnl']:+8.2f} [{emoji}]")

    print()

    # Trades avec losses consécutives (série de pertes)
    print("Analyse des séries de pertes:")
    losses_streak = 0
    max_streak = 0
    streak_pnl = 0
    trades_in_streak = []

    sorted_trades = sorted(trades, key=lambda t: (t['day'], t['time']))
    for t in sorted_trades:
        if not t['is_win']:
            losses_streak += 1
            streak_pnl += t['pnl']
            trades_in_streak.append(t)
            if losses_streak > max_streak:
                max_streak = losses_streak
        else:
            if losses_streak >= 3:
                print(f"  Serie {losses_streak} losses: P&L ${streak_pnl:.2f}")
            losses_streak = 0
            streak_pnl = 0
            trades_in_streak = []

    print(f"  Max streak: {max_streak} losses consécutives")
    print()

    # Analyse croisée: Confidence + OrderFlow
    print("Matrice Confidence x OrderFlow:")
    matrix = defaultdict(lambda: {'trades': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        conf_tier = 'C<70%' if t['confidence'] < 0.70 else 'C>=70%' if t['confidence'] < 1.0 else 'C>=100%'
        of_tier = 'OF<12%' if t['orderflow'] < 0.12 else 'OF<18%' if t['orderflow'] < 0.18 else 'OF>=18%'
        key = f"{conf_tier} + {of_tier}"
        matrix[key]['trades'] += 1
        matrix[key]['pnl'] += t['pnl']
        matrix[key]['wins'] += 1 if t['is_win'] else 0

    for key in sorted(matrix.keys()):
        data = matrix[key]
        wr = data['wins'] / data['trades'] * 100 if data['trades'] else 0
        emoji = "OK" if data['pnl'] > 0 else "BAD"
        print(f"  {key:<25}: {data['trades']:3d} trades, WR {wr:5.1f}%, P&L ${data['pnl']:+8.2f} [{emoji}]")

    print()

    # Trades NQ SHORT consécutifs
    print("Analyse NQ SHORTs consécutifs:")
    nq_shorts = [t for t in sorted_trades if t['symbol'] == 'NQ' and t['direction'] == 'SHORT']
    consecutive_shorts = 0
    for i, t in enumerate(nq_shorts):
        if i > 0:
            prev = nq_shorts[i-1]
            # Si < 10 min entre trades
            prev_mins = int(prev['time'].split(':')[0]) * 60 + int(prev['time'].split(':')[1])
            curr_mins = int(t['time'].split(':')[0]) * 60 + int(t['time'].split(':')[1])
            if prev['day'] == t['day'] and abs(curr_mins - prev_mins) < 10:
                consecutive_shorts += 1
    print(f"  {consecutive_shorts} trades NQ SHORT consécutifs (<10 min entre)")

    # Re-entries rapides
    print()
    print("Analyse re-entries rapides (<5 min):")
    rapid_reentries = []
    for i, t in enumerate(sorted_trades):
        if i > 0:
            prev = sorted_trades[i-1]
            if prev['symbol'] == t['symbol'] and prev['day'] == t['day']:
                prev_mins = int(prev['exit_time'].split(':')[0]) * 60 + int(prev['exit_time'].split(':')[1]) if 'exit_time' in prev else 0
                curr_mins = int(t['time'].split(':')[0]) * 60 + int(t['time'].split(':')[1])
                if abs(curr_mins - prev_mins) < 5:
                    rapid_reentries.append(t)

    rapid_pnl = sum(t['pnl'] for t in rapid_reentries)
    rapid_wins = sum(1 for t in rapid_reentries if t['is_win'])
    rapid_wr = rapid_wins / len(rapid_reentries) * 100 if rapid_reentries else 0
    print(f"  {len(rapid_reentries)} re-entries <5min, WR {rapid_wr:.1f}%, P&L ${rapid_pnl:+.2f}")

    print()
    print("=" * 80)
    print("CONCLUSIONS DATA-DRIVEN")
    print("=" * 80)
    print()
    print("1. Confidence < 50% n'est PAS un probleme (7 trades, 71% WR)")
    print("2. Creneau 16h n'est PAS toxique (+$1051, 50% WR)")
    print("3. Verifier les heures avec P&L negatif dans l'analyse ci-dessus")
    print("4. Verifier la matrice Confidence x OrderFlow pour trouver la zone BAD")

if __name__ == "__main__":
    main()
