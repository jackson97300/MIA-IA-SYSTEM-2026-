#!/usr/bin/env python3
"""
TEST OPTION A SUR SEMAINE DERNIÈRE (LOGS)
==========================================

Extrait les trades des logs et teste l'Option A.

Date: 08/12/2025
"""

import os
import re
import glob
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

LOGS_DIR = r"D:\MIA_IA_system\logs"
# Semaine dernière: 01-07 décembre 2025
LOG_FILES = [
    "__main___20251201.log",
    "__main___20251202.log",
    "__main___20251203.log",
    "__main___20251204.log",
    "__main___20251205.log",
    "__main___20251206.log",
    "__main___20251207.log",
    "__main___20251208.log",  # Aujourd'hui aussi
]

# Seuils à tester
VWAP_THRESHOLDS = [40, 50, 60, 75, 100, 125, 150]

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeFromLogs:
    date: str
    time: str
    symbol: str
    direction: str
    entry_price: float
    vwap_distance: int  # en ticks
    pnl: float
    mfe: float
    mae: float
    result: str

# ═══════════════════════════════════════════════════════════════════════════════
# EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_trades_from_log(log_file: str) -> List[TradeFromLogs]:
    """Extrait les trades depuis un fichier log"""

    trades = []

    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[WARN] Erreur lecture {log_file}: {e}")
        return []

    # Pattern pour détecter l'ouverture de position
    open_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}).*POSITION OUVERTE: (LONG|SHORT) @ ([\d.]+)')

    # Pattern pour VWAP distance (avant l'ouverture)
    vwap_pattern = re.compile(r'VWAP distance: (-?\d+)t')

    # Pattern pour fermeture de trade
    close_pattern = re.compile(r'Trade ferm.*\((\w+) (SL|TP|BE).*\$([+-]?\d+\.?\d*)\).*MFE: \+?([\d.]+).*MAE: ([+-]?\d+\.?\d*)')

    # Stocker temporairement les infos d'ouverture
    pending_trades: Dict[str, dict] = {}  # symbol -> trade info
    last_vwap_distance: Dict[str, int] = {}  # symbol -> vwap distance

    for i, line in enumerate(lines):
        # Chercher VWAP distance
        vwap_match = vwap_pattern.search(line)
        if vwap_match:
            # Identifier le symbole (généralement mentionné avant)
            if '[ES]' in line or 'ES' in line:
                last_vwap_distance['ES'] = int(vwap_match.group(1))
            elif '[NQ]' in line or 'NQ' in line:
                last_vwap_distance['NQ'] = int(vwap_match.group(1))

        # Chercher ouverture de position
        open_match = open_pattern.search(line)
        if open_match:
            date, time, direction, price = open_match.groups()

            # Identifier le symbole
            symbol = 'ES' if '[ES]' in line else 'NQ' if '[NQ]' in line else 'UNKNOWN'

            # Récupérer la dernière VWAP distance connue
            vwap_dist = last_vwap_distance.get(symbol, 0)

            pending_trades[symbol] = {
                'date': date,
                'time': time,
                'symbol': symbol,
                'direction': direction,
                'entry_price': float(price),
                'vwap_distance': vwap_dist
            }

        # Chercher fermeture de trade
        close_match = close_pattern.search(line)
        if close_match:
            symbol_raw, exit_type, pnl, mfe, mae = close_match.groups()

            # Normaliser le symbole
            symbol = 'ES' if 'ES' in symbol_raw else 'NQ' if 'NQ' in symbol_raw else symbol_raw

            if symbol in pending_trades:
                trade_info = pending_trades[symbol]
                pnl_val = float(pnl)

                trade = TradeFromLogs(
                    date=trade_info['date'],
                    time=trade_info['time'],
                    symbol=symbol,
                    direction=trade_info['direction'],
                    entry_price=trade_info['entry_price'],
                    vwap_distance=trade_info['vwap_distance'],
                    pnl=pnl_val,
                    mfe=float(mfe),
                    mae=float(mae),
                    result='WIN' if pnl_val > 0 else 'LOSS'
                )
                trades.append(trade)
                del pending_trades[symbol]

    return trades

# ═══════════════════════════════════════════════════════════════════════════════
# OPTION A: VWAP DISTANCE FILTER
# ═══════════════════════════════════════════════════════════════════════════════

def test_option_a(trades: List[TradeFromLogs], max_distance: int) -> Dict:
    """Teste l'Option A sur les trades"""

    results = {
        'threshold': max_distance,
        'total': len(trades),
        'blocked': 0,
        'allowed': 0,
        'blocked_losses': 0,
        'blocked_wins': 0,
        'pnl_saved': 0.0,
        'pnl_lost': 0.0,
        'net_impact': 0.0,
        'blocked_trades': []
    }

    for trade in trades:
        # Règle Option A: Bloquer si trop loin du VWAP dans la mauvaise direction
        should_block = False

        # LONG: devrait être AU-DESSUS du VWAP (distance positive) ou proche
        # SHORT: devrait être EN-DESSOUS du VWAP (distance négative) ou proche

        if trade.direction == "LONG" and trade.vwap_distance < -max_distance:
            # LONG trop loin EN-DESSOUS du VWAP = contre-tendance
            should_block = True
        elif trade.direction == "SHORT" and trade.vwap_distance > max_distance:
            # SHORT trop loin AU-DESSUS du VWAP = contre-tendance
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
    print("TEST OPTION A: VWAP DISTANCE FILTER - SEMAINE DERNIÈRE (LOGS)")
    print("="*80)

    # Collecter tous les trades
    all_trades = []

    print("\n[1/3] Extraction des trades depuis les logs...")

    for log_name in LOG_FILES:
        log_path = os.path.join(LOGS_DIR, log_name)
        if os.path.exists(log_path):
            trades = extract_trades_from_log(log_path)
            print(f"      {log_name}: {len(trades)} trades")
            all_trades.extend(trades)
        else:
            print(f"      {log_name}: (fichier non trouvé)")

    print(f"\n      TOTAL: {len(all_trades)} trades extraits")

    if len(all_trades) == 0:
        print("\n[WARN] Aucun trade trouvé!")
        exit(1)

    # Afficher les trades
    print("\n[2/3] Trades extraits:")
    print("-"*110)
    print(f"{'Date':<12} {'Heure':<8} {'Sym':<4} {'Dir':<6} {'VWAP Dist':<12} {'P&L':<12} {'MFE':<10} {'MAE':<10} {'Result':<8}")
    print("-"*110)

    for t in all_trades:
        print(f"{t.date:<12} {t.time:<8} {t.symbol:<4} {t.direction:<6} {t.vwap_distance:>+10}t {t.pnl:>+10.2f}$ {t.mfe:>+8.2f} {t.mae:>+8.2f} {t.result:<8}")

    # Stats de base
    total_pnl = sum(t.pnl for t in all_trades)
    wins = sum(1 for t in all_trades if t.result == 'WIN')
    losses = len(all_trades) - wins

    print("-"*110)
    print(f"STATS: {wins}W / {losses}L | Win Rate: {wins/len(all_trades)*100:.1f}% | P&L Total: ${total_pnl:+.2f}")

    # Tester différents seuils
    print("\n\n[3/3] Test Option A avec différents seuils:")
    print("="*80)

    all_results = []

    for threshold in VWAP_THRESHOLDS:
        results = test_option_a(all_trades, threshold)
        all_results.append(results)

        if results['blocked'] > 0:
            print(f"\n--- Seuil: {threshold} ticks ---")
            print(f"    Bloqués: {results['blocked']} ({results['blocked_losses']} LOSS, {results['blocked_wins']} WIN)")
            print(f"    Pertes évitées: ${results['pnl_saved']:.2f}")
            print(f"    Gains perdus: ${results['pnl_lost']:.2f}")
            print(f"    IMPACT NET: ${results['net_impact']:+.2f}")

    # Tableau comparatif
    print("\n\n" + "="*90)
    print("COMPARAISON FINALE")
    print("="*90)
    print(f"\n{'Seuil':<10} | {'Bloqués':<10} | {'LOSS évitées':<15} | {'WIN perdus':<15} | {'IMPACT NET':<15} | {'Nouveau P&L':<15}")
    print("-"*90)

    for r in all_results:
        new_pnl = total_pnl + r['net_impact']
        print(f"{r['threshold']:<10} | {r['blocked']:<10} | ${r['pnl_saved']:<14.2f} | ${r['pnl_lost']:<14.2f} | ${r['net_impact']:>+14.2f} | ${new_pnl:>+14.2f}")

    # Meilleur seuil
    valid_results = [r for r in all_results if r['blocked'] > 0]
    if valid_results:
        best = max(valid_results, key=lambda x: x['net_impact'])

        print("\n" + "="*90)
        print(f"MEILLEUR SEUIL: {best['threshold']} ticks")
        print(f"Impact net: ${best['net_impact']:+.2f}")
        print(f"Nouveau P&L: ${total_pnl + best['net_impact']:+.2f} (au lieu de ${total_pnl:+.2f})")
        print("="*90)

        # Détails
        if best['blocked_trades']:
            print(f"\nTRADES BLOQUES (seuil={best['threshold']}t):")
            print("-"*90)
            for t in best['blocked_trades']:
                status = "LOSS evitee" if t.result == "LOSS" else "WIN perdu"
                print(f"  {t.date} {t.time} {t.symbol} {t.direction:<5} VWAP:{t.vwap_distance:>+5}t P&L:{t.pnl:>+10.2f}$ -> {status}")
    else:
        print("\n[INFO] Aucun trade bloqué avec les seuils testés.")

    print("\n")

