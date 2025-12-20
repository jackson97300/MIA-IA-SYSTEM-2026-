#!/usr/bin/env python3
"""
TEST OPTION A SUR HISTORIQUE COMPLET
====================================

Analyse tous les trades des derniers jours avec leurs données VWAP
pour tester l'efficacité de l'Option A (VWAP Distance Filter).

Date: 08/12/2025
"""

import os
import json
import glob
from dataclasses import dataclass
from typing import List, Dict, Tuple
from datetime import datetime
import re

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

SNAPSHOTS_DIR = r"D:\MIA_IA_system\snapshots_trades\daily"
LOGS_DIR = r"D:\MIA_IA_system\logs"

# Seuils à tester
VWAP_THRESHOLDS = [40, 50, 60, 75, 100]

# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeData:
    trade_id: str
    timestamp: str
    symbol: str
    direction: str
    entry_price: float
    vwap_price: float
    vwap_distance_ticks: float
    pnl: float
    result: str  # WIN or LOSS
    mfe: float
    mae: float

# ═══════════════════════════════════════════════════════════════════════════════
# FONCTIONS D'EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

def extract_trades_from_snapshots() -> List[TradeData]:
    """Extrait les trades depuis les snapshots"""

    trades = []

    # Trouver tous les fichiers pre_analysis
    pattern = os.path.join(SNAPSHOTS_DIR, "*_pre_analysis.json")
    pre_files = glob.glob(pattern)

    print(f"[INFO] Trouvé {len(pre_files)} fichiers pre_analysis")

    for pre_file in pre_files:
        try:
            # Lire pre_analysis
            with open(pre_file, 'r') as f:
                pre_data = json.load(f)

            # Trouver le fichier final_result correspondant
            final_file = pre_file.replace("_pre_analysis.json", "_final_result.json")
            if not os.path.exists(final_file):
                continue

            with open(final_file, 'r') as f:
                final_data = json.load(f)

            # Extraire les données
            trade_id = pre_data.get('trade_id', '')
            timestamp = pre_data.get('timestamp', '')

            # Symbol
            symbol_full = pre_data.get('market', {}).get('symbol', '')
            if 'ES' in symbol_full:
                symbol = 'ES'
                tick_size = 0.25
            elif 'NQ' in symbol_full:
                symbol = 'NQ'
                tick_size = 0.25
            else:
                continue

            # Prix et VWAP
            entry_price = pre_data.get('market', {}).get('mid', 0)
            vwap_price = pre_data.get('vwap', {}).get('price', 0)

            if entry_price == 0 or vwap_price == 0:
                continue

            vwap_distance_ticks = (entry_price - vwap_price) / tick_size

            # Direction - chercher dans decision.json
            decision_file = pre_file.replace("_pre_analysis.json", "_decision.json")
            direction = "UNKNOWN"
            if os.path.exists(decision_file):
                with open(decision_file, 'r') as f:
                    decision_data = json.load(f)
                # Le champ est 'action', pas 'direction'
                direction = decision_data.get('signal', {}).get('action', 'UNKNOWN')

            # P&L et résultat - format correct
            result_data = final_data.get('result', {})
            pnl = result_data.get('pnl', 0)
            mfe = 0  # Non disponible dans ce format
            mae = 0  # Non disponible dans ce format
            result = "WIN" if pnl > 0 else "LOSS"

            trade = TradeData(
                trade_id=trade_id,
                timestamp=timestamp,
                symbol=symbol,
                direction=direction,
                entry_price=entry_price,
                vwap_price=vwap_price,
                vwap_distance_ticks=vwap_distance_ticks,
                pnl=pnl,
                result=result,
                mfe=mfe,
                mae=mae
            )
            trades.append(trade)

        except Exception as e:
            print(f"[WARN] Erreur lecture {pre_file}: {e}")
            continue

    return trades

def extract_trades_from_logs() -> List[Dict]:
    """Extrait les trades depuis les logs (backup si snapshots incomplets)"""

    trades = []

    # Parcourir les logs des derniers jours
    log_files = glob.glob(os.path.join(LOGS_DIR, "__main___202512*.log"))

    for log_file in log_files[-5:]:  # 5 derniers jours
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Pattern pour extraire les trades fermés
            pattern = r"Trade fermé.*\((\w+) (SL|TP).*\$([+-]?\d+\.?\d*)\).*MFE: \+?(\d+\.?\d*).*MAE: ([+-]?\d+\.?\d*)"
            matches = re.findall(pattern, content)

            for match in matches:
                symbol, exit_type, pnl, mfe, mae = match
                trades.append({
                    'symbol': symbol,
                    'exit_type': exit_type,
                    'pnl': float(pnl),
                    'mfe': float(mfe),
                    'mae': float(mae)
                })

        except Exception as e:
            print(f"[WARN] Erreur lecture {log_file}: {e}")

    return trades

# ═══════════════════════════════════════════════════════════════════════════════
# OPTION A: VWAP DISTANCE FILTER
# ═══════════════════════════════════════════════════════════════════════════════

def test_option_a(trades: List[TradeData], max_distance: int) -> Dict:
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
        'details': []
    }

    for trade in trades:
        # Règle Option A
        should_block = False
        reason = ""

        if trade.direction == "LONG" and trade.vwap_distance_ticks < -max_distance:
            should_block = True
            reason = f"LONG bloqué - VWAP dist {trade.vwap_distance_ticks:.0f}t < -{max_distance}t"
        elif trade.direction == "SHORT" and trade.vwap_distance_ticks > max_distance:
            should_block = True
            reason = f"SHORT bloqué - VWAP dist {trade.vwap_distance_ticks:.0f}t > +{max_distance}t"
        else:
            reason = "Autorisé"

        detail = {
            'trade_id': trade.trade_id[:20] if trade.trade_id else 'N/A',
            'symbol': trade.symbol,
            'direction': trade.direction,
            'vwap_dist': trade.vwap_distance_ticks,
            'pnl': trade.pnl,
            'result': trade.result,
            'blocked': should_block,
            'reason': reason
        }
        results['details'].append(detail)

        if should_block:
            results['blocked'] += 1
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
    print("TEST OPTION A: VWAP DISTANCE FILTER - HISTORIQUE COMPLET")
    print("="*80)

    # Extraire les trades
    print("\n[1/3] Extraction des trades depuis les snapshots...")
    trades = extract_trades_from_snapshots()
    print(f"      -> {len(trades)} trades extraits")

    if len(trades) == 0:
        print("\n[WARN] Aucun trade trouvé dans les snapshots!")
        print("       Vérifiez le dossier:", SNAPSHOTS_DIR)
        exit(1)

    # Afficher les trades trouvés
    print("\n[2/3] Trades extraits:")
    print("-"*100)
    print(f"{'Trade ID':<25} {'Symbol':<6} {'Dir':<6} {'VWAP Dist':<12} {'P&L':<12} {'Result':<8}")
    print("-"*100)

    for t in trades:
        print(f"{t.trade_id[:25]:<25} {t.symbol:<6} {t.direction:<6} {t.vwap_distance_ticks:>+10.1f}t {t.pnl:>+10.2f}$ {t.result:<8}")

    # Tester différents seuils
    print("\n\n[3/3] Test Option A avec différents seuils:")
    print("="*80)

    all_results = []

    for threshold in VWAP_THRESHOLDS:
        results = test_option_a(trades, threshold)
        all_results.append(results)

        print(f"\n--- Seuil: {threshold} ticks ---")
        print(f"    Bloqués: {results['blocked']} ({results['blocked_losses']} LOSS, {results['blocked_wins']} WIN)")
        print(f"    Pertes évitées: ${results['pnl_saved']:.2f}")
        print(f"    Gains perdus: ${results['pnl_lost']:.2f}")
        print(f"    IMPACT NET: ${results['net_impact']:+.2f}")

    # Tableau comparatif
    print("\n\n" + "="*80)
    print("COMPARAISON FINALE")
    print("="*80)
    print(f"\n{'Seuil':<10} | {'Bloqués':<10} | {'LOSS évitées':<15} | {'WIN perdus':<15} | {'IMPACT NET':<15}")
    print("-"*80)

    for r in all_results:
        print(f"{r['threshold']:<10} | {r['blocked']:<10} | ${r['pnl_saved']:<14.2f} | ${r['pnl_lost']:<14.2f} | ${r['net_impact']:>+14.2f}")

    # Meilleur seuil
    best = max(all_results, key=lambda x: x['net_impact'])

    print("\n" + "="*80)
    print(f"MEILLEUR SEUIL: {best['threshold']} ticks")
    print(f"Impact net: ${best['net_impact']:+.2f}")
    print("="*80)

    # Détails des trades bloqués pour le meilleur seuil
    print(f"\n\nDETAILS DES TRADES BLOQUES (seuil={best['threshold']}t):")
    print("-"*100)

    for d in best['details']:
        if d['blocked']:
            status = "LOSS evitee" if d['result'] == "LOSS" else "WIN perdu"
            print(f"  {d['symbol']} {d['direction']:<5} VWAP:{d['vwap_dist']:>+7.0f}t P&L:{d['pnl']:>+10.2f}$ -> {status}")

    print("\n")
