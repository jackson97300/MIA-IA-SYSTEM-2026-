#!/usr/bin/env python3
"""
EXTRACTION DE TOUS LES TRADES AVEC VWAP DISTANCE
=================================================

Combine les données de:
1. snapshots_trades/daily/ (VWAP distance)
2. trades_historique.txt (P&L et résultat)

Date: 08/12/2025
"""

import os
import json
import glob
import re
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = r"D:\MIA_IA_system"
SNAPSHOTS_DIR = os.path.join(BASE_DIR, "snapshots_trades", "daily")
HISTORIQUE_FILE = os.path.join(BASE_DIR, "REVUE_DE_SESSION", "trades_historique.txt")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeComplete:
    date: str
    time: str
    symbol: str
    direction: str
    entry_price: float
    vwap_price: float
    vwap_distance_ticks: float
    pnl: float
    result: str
    source: str  # "snapshot" ou "historique"

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def load_historique() -> Dict[str, Dict]:
    """Charge trades_historique.txt"""

    trades = {}

    try:
        with open(HISTORIQUE_FILE, 'r') as f:
            lines = f.readlines()

        for line in lines[1:]:  # Skip header
            parts = line.strip().split(',')
            if len(parts) >= 7:
                date, time, symbol, direction, entry, pnl, result = parts[:7]

                # Clé unique
                key = f"{date}_{time}_{symbol}"

                trades[key] = {
                    'date': date,
                    'time': time,
                    'symbol': symbol,
                    'direction': direction,
                    'entry_price': float(entry),
                    'pnl': float(pnl),
                    'result': result
                }

    except Exception as e:
        print(f"[WARN] Erreur lecture historique: {e}")

    return trades

def extract_from_snapshots() -> List[TradeComplete]:
    """Extrait les trades des snapshots avec VWAP"""

    trades = []

    # Trouver tous les pre_analysis
    pattern = os.path.join(SNAPSHOTS_DIR, "*_pre_analysis.json")
    pre_files = glob.glob(pattern)

    # Filtrer pour garder seulement ceux avec final_result
    valid_files = []
    for f in pre_files:
        final = f.replace("_pre_analysis.json", "_final_result.json")
        decision = f.replace("_pre_analysis.json", "_decision.json")
        if os.path.exists(final) and os.path.exists(decision):
            valid_files.append(f)

    print(f"[INFO] Snapshots avec final_result: {len(valid_files)}")

    for pre_file in valid_files:
        try:
            # Lire pre_analysis (VWAP)
            with open(pre_file, 'r') as f:
                pre = json.load(f)

            # Lire decision (direction)
            decision_file = pre_file.replace("_pre_analysis.json", "_decision.json")
            with open(decision_file, 'r') as f:
                decision = json.load(f)

            # Lire final_result (P&L)
            final_file = pre_file.replace("_pre_analysis.json", "_final_result.json")
            with open(final_file, 'r') as f:
                final = json.load(f)

            # Extraire données
            timestamp = pre.get('timestamp', '')
            dt = datetime.fromisoformat(timestamp.replace('+00:00', ''))

            symbol_full = pre.get('market', {}).get('symbol', '')
            if 'ES' in symbol_full:
                symbol = 'ES'
                tick_size = 0.25
            elif 'NQ' in symbol_full:
                symbol = 'NQ'
                tick_size = 0.25
            else:
                continue

            entry_price = pre.get('market', {}).get('mid', 0)
            vwap_price = pre.get('vwap', {}).get('price', 0)

            if entry_price == 0 or vwap_price == 0:
                continue

            vwap_distance_ticks = (entry_price - vwap_price) / tick_size

            direction = decision.get('signal', {}).get('action', 'UNKNOWN')
            pnl = final.get('result', {}).get('pnl', 0)
            result = 'WIN' if pnl > 0 else 'LOSS'

            trade = TradeComplete(
                date=dt.strftime('%Y%m%d'),
                time=dt.strftime('%H:%M:%S'),
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                vwap_price=vwap_price,
                vwap_distance_ticks=vwap_distance_ticks,
                pnl=pnl,
                result=result,
                source='snapshot'
            )
            trades.append(trade)

        except Exception as e:
            continue

    return trades

def test_option_a(trades: List[TradeComplete], max_distance: int) -> Dict:
    """Teste l'Option A"""

    results = {
        'threshold': max_distance,
        'total': len(trades),
        'blocked': 0,
        'allowed': 0,
        'blocked_losses': 0,
        'blocked_wins': 0,
        'pnl_saved': 0.0,
        'pnl_lost': 0.0,
        'blocked_trades': []
    }

    for trade in trades:
        should_block = False

        # LONG trop loin EN-DESSOUS du VWAP = contre-tendance
        if trade.direction == "LONG" and trade.vwap_distance_ticks < -max_distance:
            should_block = True
        # SHORT trop loin AU-DESSUS du VWAP = contre-tendance
        elif trade.direction == "SHORT" and trade.vwap_distance_ticks > max_distance:
            should_block = True

        if should_block:
            results['blocked'] += 1
            results['blocked_trades'].append(trade)
            if trade.result == "LOSS":
                results['blocked_losses'] += 1
                results['pnl_saved'] += abs(trade.pnl)
            else:
                results['blocked_wins'] += 1
                results['pnl_lost'] += trade.pnl
        else:
            results['allowed'] += 1

    results['net_impact'] = results['pnl_saved'] - results['pnl_lost']

    return results

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "="*80)
    print("EXTRACTION COMPLÈTE DES TRADES AVEC VWAP DISTANCE")
    print("="*80)

    # 1. Extraire depuis snapshots
    print("\n[1/4] Extraction depuis snapshots...")
    trades = extract_from_snapshots()
    print(f"      Trades avec VWAP: {len(trades)}")

    if len(trades) == 0:
        print("\n[WARN] Aucun trade trouvé!")
        exit(1)

    # 2. Afficher les trades
    print("\n[2/4] Trades extraits:")
    print("-"*120)
    print(f"{'Date':<10} {'Heure':<10} {'Sym':<4} {'Dir':<6} {'Entry':<12} {'VWAP':<12} {'VWAP Dist':<12} {'P&L':<12} {'Result'}")
    print("-"*120)

    for t in sorted(trades, key=lambda x: (x.date, x.time)):
        print(f"{t.date:<10} {t.time:<10} {t.symbol:<4} {t.direction:<6} {t.entry_price:<12.2f} {t.vwap_price:<12.2f} {t.vwap_distance_ticks:>+10.0f}t {t.pnl:>+10.2f}$ {t.result}")

    # Stats de base
    total_pnl = sum(t.pnl for t in trades)
    wins = sum(1 for t in trades if t.result == 'WIN')
    losses = len(trades) - wins

    print("-"*120)
    print(f"TOTAL: {len(trades)} trades | {wins}W / {losses}L ({wins/len(trades)*100:.1f}% WR) | P&L: ${total_pnl:+.2f}")

    # 3. Tester Option A
    print("\n\n[3/4] Test Option A (VWAP Distance Filter):")
    print("="*80)

    thresholds = [40, 50, 60, 75, 100, 125, 150]
    all_results = []

    for thresh in thresholds:
        r = test_option_a(trades, thresh)
        all_results.append(r)

        if r['blocked'] > 0:
            print(f"\nSeuil {thresh}t: {r['blocked']} bloqués ({r['blocked_losses']}L/{r['blocked_wins']}W)")
            print(f"  Pertes évitées: ${r['pnl_saved']:.2f} | Gains perdus: ${r['pnl_lost']:.2f}")
            print(f"  IMPACT NET: ${r['net_impact']:+.2f}")

    # 4. Tableau final
    print("\n\n[4/4] TABLEAU COMPARATIF:")
    print("="*90)
    print(f"{'Seuil':<8} | {'Bloqués':<10} | {'LOSS évitées':<15} | {'WIN perdus':<15} | {'IMPACT NET':<15}")
    print("-"*90)

    for r in all_results:
        print(f"{r['threshold']:<8} | {r['blocked']:<10} | ${r['pnl_saved']:<14.2f} | ${r['pnl_lost']:<14.2f} | ${r['net_impact']:>+14.2f}")

    # Meilleur seuil
    valid = [r for r in all_results if r['blocked'] > 0]
    if valid:
        best = max(valid, key=lambda x: x['net_impact'])

        print("\n" + "="*90)
        print(f"MEILLEUR SEUIL: {best['threshold']} ticks")
        print(f"Impact net: ${best['net_impact']:+.2f}")
        print(f"Nouveau P&L: ${total_pnl + best['net_impact']:+.2f} (au lieu de ${total_pnl:+.2f})")

        if best['blocked_trades']:
            print(f"\nDétails trades bloqués:")
            for t in best['blocked_trades']:
                status = "LOSS évitée" if t.result == "LOSS" else "WIN perdu"
                print(f"  {t.date} {t.time} {t.symbol} {t.direction:<5} VWAP:{t.vwap_distance_ticks:>+6.0f}t P&L:{t.pnl:>+10.2f}$ -> {status}")

    print("\n")

