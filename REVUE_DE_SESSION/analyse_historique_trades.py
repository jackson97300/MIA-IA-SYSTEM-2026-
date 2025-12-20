"""
ANALYSE HISTORIQUE DES TRADES
=============================

Objectif:
1. Compter les vrais trades (ENTRY + EXIT complets)
2. Verifier si les snapshots existent pour chaque date
3. Evaluer la qualite des donnees pour le ML
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Chemins
TRADES_DIR = Path(r"D:\MIA_IA_system\logs_advanced\trades")
DATA_DIR = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025")

# Mapping symbole -> chart
CHART_MAP = {'ES': 3, 'NQ': 9, 'RTY': 1}


def parse_trade_logs():
    """Parse tous les fichiers de trades"""

    all_trades = []

    for log_file in sorted(TRADES_DIR.glob("trades_*.log")):
        date_match = re.search(r'trades_(\d{8})\.log', log_file.name)
        if not date_match:
            continue

        date_str = date_match.group(1)

        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        entries = {}  # symbol -> entry info

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse ENTRY
            entry_match = re.search(r'\[(\w+)\] ENTRY.*direction.*?[\'"](\w+)[\'"].*price.*?(\d+\.?\d*)', line)
            if entry_match:
                symbol = entry_match.group(1)
                direction = entry_match.group(2)
                price = float(entry_match.group(3))
                time_match = re.search(r'^(\d{2}:\d{2}:\d{2})', line)
                time_str = time_match.group(1) if time_match else "00:00:00"

                entries[symbol] = {
                    'date': date_str,
                    'time': time_str,
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': price
                }

            # Parse EXIT
            exit_match = re.search(r'\[(\w+)\] EXIT.*pnl_usd.*?([-\d.]+)', line)
            if exit_match:
                symbol = exit_match.group(1)
                pnl = float(exit_match.group(2))

                if symbol in entries:
                    trade = entries[symbol].copy()
                    trade['pnl'] = pnl
                    trade['result'] = 'WIN' if pnl > 0 else 'LOSS'
                    all_trades.append(trade)
                    del entries[symbol]

    return all_trades


def check_snapshots_availability():
    """Verifie quels snapshots sont disponibles"""

    available = {}

    # Parcourir NOVEMBRE et DECEMBRE
    for month in ['NOVEMBRE', 'DECEMBRE']:
        month_dir = DATA_DIR / month
        if not month_dir.exists():
            continue

        for date_dir in month_dir.iterdir():
            if not date_dir.is_dir():
                continue

            date_str = date_dir.name
            available[date_str] = {}

            for symbol, chart_id in CHART_MAP.items():
                ml_ready_path = date_dir / f"CHART_{chart_id}" / "ML_READY"
                if ml_ready_path.exists():
                    files = list(ml_ready_path.glob("*.jsonl"))
                    if files:
                        size_mb = sum(f.stat().st_size for f in files) / (1024*1024)
                        available[date_str][symbol] = {
                            'path': str(ml_ready_path),
                            'files': len(files),
                            'size_mb': size_mb
                        }

    return available


def main():
    print("="*100)
    print("ANALYSE HISTORIQUE DES TRADES")
    print("="*100)

    # 1. Parse les trades
    print("\n[1] PARSING DES LOGS DE TRADES...")
    trades = parse_trade_logs()

    # 2. Statistiques par date
    print("\n[2] STATISTIQUES PAR DATE")
    print("-"*80)

    by_date = defaultdict(list)
    for t in trades:
        by_date[t['date']].append(t)

    total_trades = 0
    total_wins = 0
    total_losses = 0
    total_pnl = 0

    print(f"{'Date':<12} {'Trades':<8} {'Wins':<8} {'Losses':<8} {'WR':<8} {'P&L':<12}")
    print("-"*80)

    for date in sorted(by_date.keys()):
        date_trades = by_date[date]
        wins = sum(1 for t in date_trades if t['result'] == 'WIN')
        losses = sum(1 for t in date_trades if t['result'] == 'LOSS')
        pnl = sum(t['pnl'] for t in date_trades)
        wr = wins / len(date_trades) * 100 if date_trades else 0

        total_trades += len(date_trades)
        total_wins += wins
        total_losses += losses
        total_pnl += pnl

        print(f"{date:<12} {len(date_trades):<8} {wins:<8} {losses:<8} {wr:<7.0f}% ${pnl:>+10.2f}")

    print("-"*80)
    total_wr = total_wins / total_trades * 100 if total_trades else 0
    print(f"{'TOTAL':<12} {total_trades:<8} {total_wins:<8} {total_losses:<8} {total_wr:<7.0f}% ${total_pnl:>+10.2f}")

    # 3. Statistiques par symbole
    print("\n[3] STATISTIQUES PAR SYMBOLE")
    print("-"*80)

    by_symbol = defaultdict(list)
    for t in trades:
        by_symbol[t['symbol']].append(t)

    print(f"{'Symbole':<8} {'Trades':<8} {'Wins':<8} {'Losses':<8} {'WR':<8} {'P&L':<12}")
    print("-"*80)

    for symbol in sorted(by_symbol.keys()):
        sym_trades = by_symbol[symbol]
        wins = sum(1 for t in sym_trades if t['result'] == 'WIN')
        losses = sum(1 for t in sym_trades if t['result'] == 'LOSS')
        pnl = sum(t['pnl'] for t in sym_trades)
        wr = wins / len(sym_trades) * 100 if sym_trades else 0

        print(f"{symbol:<8} {len(sym_trades):<8} {wins:<8} {losses:<8} {wr:<7.0f}% ${pnl:>+10.2f}")

    # 4. Verifier disponibilite snapshots
    print("\n[4] DISPONIBILITE DES SNAPSHOTS ML_READY")
    print("-"*80)

    snapshots = check_snapshots_availability()

    dates_with_trades = set(by_date.keys())
    dates_with_snapshots = set(snapshots.keys())

    print(f"{'Date':<12} {'Trades':<8} {'ES':<15} {'NQ':<15} {'RTY':<15}")
    print("-"*80)

    matched_trades = 0

    for date in sorted(dates_with_trades | dates_with_snapshots):
        n_trades = len(by_date.get(date, []))

        es_status = "N/A"
        nq_status = "N/A"
        rty_status = "N/A"

        if date in snapshots:
            if 'ES' in snapshots[date]:
                es_status = f"{snapshots[date]['ES']['size_mb']:.0f}MB"
            if 'NQ' in snapshots[date]:
                nq_status = f"{snapshots[date]['NQ']['size_mb']:.0f}MB"
            if 'RTY' in snapshots[date]:
                rty_status = f"{snapshots[date]['RTY']['size_mb']:.0f}MB"

            if n_trades > 0:
                matched_trades += n_trades

        trade_marker = f"{n_trades}" if n_trades > 0 else "-"
        print(f"{date:<12} {trade_marker:<8} {es_status:<15} {nq_status:<15} {rty_status:<15}")

    # 5. Resume final
    print("\n" + "="*100)
    print("RESUME FINAL")
    print("="*100)

    print(f"\n   TRADES TOTAUX:           {total_trades}")
    print(f"   TRADES AVEC SNAPSHOTS:   {matched_trades}")
    print(f"   COUVERTURE:              {matched_trades/total_trades*100:.0f}%" if total_trades else "N/A")

    print(f"\n   WINS:                    {total_wins} ({total_wr:.0f}%)")
    print(f"   LOSSES:                  {total_losses}")
    print(f"   P&L TOTAL:               ${total_pnl:+.2f}")

    # 6. Recommendation ML
    print("\n" + "="*100)
    print("RECOMMENDATION POUR LE ML")
    print("="*100)

    if matched_trades >= 300:
        print(f"\n   [OK] {matched_trades} trades avec snapshots = SUFFISANT pour ML!")
        print("   >>> Pret pour creer le dataset ML <<<")
    elif matched_trades >= 100:
        print(f"\n   [ATTENTION] {matched_trades} trades = MINIMUM pour ML basique")
        print("   >>> Collecter encore 1-2 semaines recommande <<<")
    else:
        print(f"\n   [INSUFFISANT] {matched_trades} trades = PAS ASSEZ pour ML")
        print("   >>> Collecter 2-4 semaines supplementaires <<<")

    # 7. Exporter liste des trades
    print("\n[EXPORT] Liste des trades sauvegardee...")

    export_path = Path("REVUE_DE_SESSION/trades_historique.txt")
    with open(export_path, 'w', encoding='utf-8') as f:
        f.write("DATE,TIME,SYMBOL,DIRECTION,ENTRY_PRICE,PNL,RESULT\n")
        for t in trades:
            f.write(f"{t['date']},{t['time']},{t['symbol']},{t['direction']},{t['entry_price']},{t['pnl']},{t['result']}\n")

    print(f"   Fichier: {export_path}")


if __name__ == "__main__":
    main()

