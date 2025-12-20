#!/usr/bin/env python3
"""
AUDIT CONFIDENCE NQ - Semaine 01 (02-04 Décembre 2025)
Analyse l'impact RÉEL de confidence >= 45% sur les trades NQ
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

def parse_log_file(log_path: str) -> List[Dict]:
    """Parse un fichier de log et extrait les trades NQ avec confidence et résultat"""

    trades = []
    current_trade = {}

    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            # Détecter signal NQ avec confidence
            signal_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[NQ\] Signal (LONG|SHORT): ([\d.]+) \(conf: ([\d.]+)%\)', line)
            if signal_match:
                timestamp = signal_match.group(1)
                direction = signal_match.group(2)
                entry_price = float(signal_match.group(3))
                confidence = float(signal_match.group(4))

                current_trade = {
                    'timestamp': timestamp,
                    'direction': direction,
                    'entry': entry_price,
                    'confidence': confidence,
                    'exit': None,
                    'pnl': None,
                    'result': None
                }

            # Détecter fermeture position NQ
            close_match = re.search(r'Entry: ([\d.]+).*Exit: ([\d.]+)', line)
            pnl_match = re.search(r'P&L: ([+-]?[\d.]+) ticks \(\$([+-]?[\d.]+)\)', line)

            if close_match and '[NQ]' in line and current_trade:
                current_trade['exit'] = float(close_match.group(2))

            if pnl_match and '[NQ]' in line and current_trade:
                current_trade['pnl'] = float(pnl_match.group(2))

                # Déterminer WIN/LOSS
                if current_trade['pnl'] > 5:  # > $5 = WIN
                    current_trade['result'] = 'WIN'
                elif current_trade['pnl'] < -5:  # < -$5 = LOSS
                    current_trade['result'] = 'LOSS'
                else:
                    current_trade['result'] = 'SCRATCH'

                # Ajouter le trade complet
                if current_trade['confidence'] and current_trade['result']:
                    trades.append(current_trade.copy())

                current_trade = {}

    return trades

def analyze_by_confidence_threshold(trades: List[Dict], threshold: float) -> Dict:
    """Analyse les trades selon un seuil de confidence"""

    above = [t for t in trades if t['confidence'] >= threshold]
    below = [t for t in trades if t['confidence'] < threshold]

    def stats(trade_list):
        if not trade_list:
            return {'count': 0, 'wins': 0, 'losses': 0, 'wr': 0, 'pnl': 0, 'avg_conf': 0}

        wins = [t for t in trade_list if t['result'] == 'WIN']
        losses = [t for t in trade_list if t['result'] == 'LOSS']
        total_pnl = sum(t['pnl'] for t in trade_list)
        avg_conf = sum(t['confidence'] for t in trade_list) / len(trade_list)

        return {
            'count': len(trade_list),
            'wins': len(wins),
            'losses': len(losses),
            'wr': len(wins) / len(trade_list) * 100 if trade_list else 0,
            'pnl': total_pnl,
            'avg_conf': avg_conf
        }

    return {
        'above': stats(above),
        'below': stats(below),
        'threshold': threshold
    }

def main():
    print("=" * 80)
    print("AUDIT CONFIDENCE NQ - SEMAINE 01 (02-04 DECEMBRE 2025)")
    print("=" * 80)
    print()

    log_dir = Path("D:/MIA_IA_system/logs")
    log_files = [
        log_dir / "__main___20251202.log",
        log_dir / "__main___20251203.log",
        log_dir / "__main___20251204.log"
    ]

    all_trades = []

    for log_file in log_files:
        if log_file.exists():
            day = log_file.stem.split('_')[-1]
            print(f"Analyse {log_file.name}...")
            trades = parse_log_file(str(log_file))
            all_trades.extend(trades)
            print(f"   OK {len(trades)} trades NQ trouves")
        else:
            print(f"   WARN Fichier non trouve: {log_file.name}")

    print()
    print(f"TOTAL TRADES NQ SEMAINE: {len(all_trades)}")
    print("=" * 80)
    print()

    if not all_trades:
        print("Aucun trade trouve!")
        return

    # Analyse globale
    wins = [t for t in all_trades if t['result'] == 'WIN']
    losses = [t for t in all_trades if t['result'] == 'LOSS']
    total_pnl = sum(t['pnl'] for t in all_trades)
    avg_conf = sum(t['confidence'] for t in all_trades) / len(all_trades)

    print("STATISTIQUES GLOBALES NQ")
    print("-" * 80)
    print(f"Trades: {len(all_trades)}")
    print(f"Wins: {len(wins)} ({len(wins)/len(all_trades)*100:.1f}%)")
    print(f"Losses: {len(losses)} ({len(losses)/len(all_trades)*100:.1f}%)")
    print(f"P&L Total: ${total_pnl:+,.2f}")
    print(f"Confidence Moyenne: {avg_conf:.1f}%")
    print()

    # Test différents seuils
    thresholds = [35, 40, 45, 50, 55, 60]

    print("ANALYSE PAR SEUIL DE CONFIDENCE")
    print("=" * 80)
    print()

    results = []

    for threshold in thresholds:
        analysis = analyze_by_confidence_threshold(all_trades, threshold)
        results.append(analysis)

        above = analysis['above']
        below = analysis['below']

        marker = '*** ' if threshold == 45 else ''
        print(f"{marker}SEUIL >= {threshold}%")
        print("-" * 80)

        if above['count'] > 0:
            print(f"   GARDES (>= {threshold}%):")
            print(f"      Trades: {above['count']}")
            print(f"      Wins: {above['wins']} | Losses: {above['losses']}")
            print(f"      Win Rate: {above['wr']:.1f}%")
            print(f"      P&L: ${above['pnl']:+,.2f}")
            print(f"      Confidence Moy: {above['avg_conf']:.1f}%")

        print()

        if below['count'] > 0:
            print(f"   REJETES (< {threshold}%):")
            print(f"      Trades: {below['count']}")
            print(f"      Wins: {below['wins']} | Losses: {below['losses']}")
            print(f"      Win Rate: {below['wr']:.1f}%")
            print(f"      P&L: ${below['pnl']:+,.2f}")
            print(f"      Confidence Moy: {below['avg_conf']:.1f}%")

        print()

        # Impact net
        impact = above['pnl'] - total_pnl if below['count'] > 0 else 0
        trades_evites = below['count']

        print(f"   IMPACT NET:")
        print(f"      P&L GARDES: ${above['pnl']:+,.2f}")
        print(f"      P&L PERDUS: ${below['pnl']:+,.2f}")
        print(f"      DIFFERENCE: ${impact:+,.2f}")
        print(f"      TRADES EVITES: {trades_evites}")
        print()
        print("=" * 80)
        print()

    # Recommandation
    print("RECOMMANDATION FINALE")
    print("=" * 80)
    print()

    # Trouver le meilleur seuil
    best_threshold = 35
    best_pnl = total_pnl
    best_wr = len(wins) / len(all_trades) * 100

    for analysis in results:
        if analysis['above']['count'] >= 10:  # Au moins 10 trades
            if analysis['above']['pnl'] > best_pnl and analysis['above']['wr'] > best_wr:
                best_threshold = analysis['threshold']
                best_pnl = analysis['above']['pnl']
                best_wr = analysis['above']['wr']

    if best_threshold == 35:
        print("GARDER Confidence 35% (actuel)")
        print("   Raison: Augmenter le seuil REDUIT la performance")
    else:
        print(f"RECOMMANDER Confidence {best_threshold}%")
        print(f"   Win Rate: {best_wr:.1f}%")
        print(f"   P&L: ${best_pnl:+,.2f}")
        print(f"   Amelioration: ${best_pnl - total_pnl:+,.2f}")

    print()
    print("=" * 80)

    # Sauvegarder résultats
    output_path = Path("D:/MIA_IA_system/REVUE_DE_SESSION/2025/DECEMBRE/AUDIT_CONFIDENCE_NQ.json")
    output_data = {
        'date_analyse': datetime.now().isoformat(),
        'total_trades': len(all_trades),
        'win_rate_global': len(wins) / len(all_trades) * 100,
        'pnl_global': total_pnl,
        'analyses': results,
        'recommandation': {
            'seuil_optimal': best_threshold,
            'win_rate': best_wr,
            'pnl': best_pnl
        }
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2)

    print(f"Resultats sauvegardes: {output_path}")
    print()

if __name__ == "__main__":
    main()
