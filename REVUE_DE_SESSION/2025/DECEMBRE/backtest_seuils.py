# -*- coding: utf-8 -*-
"""
BACKTEST DES NOUVEAUX SEUILS
============================
Test 80/20 des seuils proposés pour améliorer le Win Rate
"""

import os
import sys
import re
import random
from typing import List, Dict
from collections import defaultdict

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

LOGS_DIR = r"D:\MIA_IA_system\logs_advanced\trades"
DATES = [
    "20251204", "20251205", "20251208", "20251209", "20251210",
    "20251211", "20251212", "20251216", "20251217"
]

# ============================================
# CONFIGURATIONS DE SEUILS A TESTER
# ============================================

CONFIGS = {
    'ACTUEL': {
        'description': 'Seuils actuels du bot (Confluence >= 0.35)',
        'menthorq_min': 0.0,
        'orderflow_min': 0.0,
        'context_min': 0.0,
        'confluence_min': 0.35,
    },
    'MODERE': {
        'description': 'Seuils modérés (90% moyenne wins)',
        'menthorq_min': 0.58,
        'orderflow_min': 0.22,
        'context_min': 0.16,
        'confluence_min': 0.96,
    },
    'ORDERFLOW_ONLY': {
        'description': 'Focus OrderFlow (>=0.22)',
        'menthorq_min': 0.0,
        'orderflow_min': 0.22,
        'context_min': 0.0,
        'confluence_min': 0.35,
    },
    'CONFLUENCE_STRICT': {
        'description': 'Confluence stricte (>=1.00)',
        'menthorq_min': 0.0,
        'orderflow_min': 0.0,
        'context_min': 0.0,
        'confluence_min': 1.00,
    },
    'BALANCED': {
        'description': 'Seuils équilibrés (compromis volume/WR)',
        'menthorq_min': 0.55,
        'orderflow_min': 0.20,
        'context_min': 0.16,
        'confluence_min': 0.95,
    },
    'AGRESSIF': {
        'description': 'Seuils agressifs (haute sélectivité)',
        'menthorq_min': 0.62,
        'orderflow_min': 0.24,
        'context_min': 0.18,
        'confluence_min': 1.05,
    },
}

def parse_log_file(filepath: str) -> List[Dict]:
    """Parse un fichier de log et extrait les trades ML_3Layer"""
    trades = []
    entries = {}

    if not os.path.exists(filepath):
        return []

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

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
                    }

                    # Filtrer les trades corrompus
                    if abs(pnl_usd) < 10000 and trade['menthorq_score'] > 0:
                        trades.append(trade)

                    del entries[symbol]

    return trades

def apply_filter(trades: List[Dict], config: Dict) -> List[Dict]:
    """Applique les filtres de seuils à une liste de trades"""
    filtered = []
    for t in trades:
        if (t['menthorq_score'] >= config['menthorq_min'] and
            t['orderflow_score'] >= config['orderflow_min'] and
            t['context_score'] >= config['context_min'] and
            t['confluence'] >= config['confluence_min']):
            filtered.append(t)
    return filtered

def calculate_metrics(trades: List[Dict]) -> Dict:
    """Calcule les métriques de performance"""
    if not trades:
        return {'count': 0, 'wins': 0, 'wr': 0, 'pnl': 0, 'avg_win': 0, 'avg_loss': 0}

    wins = [t for t in trades if t['is_win']]
    losses = [t for t in trades if not t['is_win']]

    avg_win = sum(t['pnl_usd'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['pnl_usd'] for t in losses) / len(losses) if losses else 0

    return {
        'count': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'wr': 100 * len(wins) / len(trades),
        'pnl': sum(t['pnl_usd'] for t in trades),
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': abs(avg_win * len(wins)) / abs(avg_loss * len(losses)) if losses and avg_loss else 0
    }

def run_kfold_validation(trades: List[Dict], config: Dict, k: int = 5) -> Dict:
    """Validation croisée k-fold"""
    random.seed(42)
    shuffled = trades.copy()
    random.shuffle(shuffled)

    fold_size = len(shuffled) // k
    fold_results = []

    for i in range(k):
        # Split train/test
        test_start = i * fold_size
        test_end = test_start + fold_size
        test_set = shuffled[test_start:test_end]
        train_set = shuffled[:test_start] + shuffled[test_end:]

        # Appliquer filtre sur train et test
        filtered_test = apply_filter(test_set, config)
        metrics = calculate_metrics(filtered_test)
        fold_results.append(metrics)

    # Moyenne des folds
    avg_wr = sum(r['wr'] for r in fold_results) / k
    avg_count = sum(r['count'] for r in fold_results) / k
    avg_pnl = sum(r['pnl'] for r in fold_results) / k

    return {
        'avg_wr': avg_wr,
        'avg_count_per_fold': avg_count,
        'total_pnl': sum(r['pnl'] for r in fold_results),
        'fold_details': fold_results
    }

def main():
    print("=" * 100)
    print("[BACKTEST] VALIDATION DES SEUILS PROPOSES")
    print("=" * 100)

    # Charger tous les trades
    all_trades = []
    for date in DATES:
        filepath = os.path.join(LOGS_DIR, f"trades_{date}.log")
        trades = parse_log_file(filepath)
        all_trades.extend(trades)

    print(f"\n[DATA] {len(all_trades)} trades ML_3Layer chargés sur {len(DATES)} jours")

    base_metrics = calculate_metrics(all_trades)
    print(f"[BASE] WR sans filtre: {base_metrics['wr']:.1f}% | P&L: ${base_metrics['pnl']:.2f}")

    # ============================================
    # TEST DE CHAQUE CONFIGURATION
    # ============================================
    print(f"\n{'='*100}")
    print("[COMPARAISON] CONFIGURATIONS DE SEUILS")
    print("=" * 100)

    header = f"{'CONFIG':<18} | {'DESCRIPTION':<40} | {'TRADES':>7} | {'WR':>6} | {'P&L':>12} | {'PF':>6}"
    print(header)
    print("-" * 100)

    results = {}
    for name, config in CONFIGS.items():
        filtered = apply_filter(all_trades, config)
        metrics = calculate_metrics(filtered)
        results[name] = {'config': config, 'metrics': metrics, 'filtered': filtered}

        retention = 100 * metrics['count'] / len(all_trades) if all_trades else 0
        pf_str = f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] > 0 else "N/A"

        print(f"{name:<18} | {config['description']:<40} | {metrics['count']:>4} ({retention:>3.0f}%) | {metrics['wr']:>5.1f}% | ${metrics['pnl']:>10.2f} | {pf_str:>6}")

    # ============================================
    # VALIDATION CROISEE K-FOLD
    # ============================================
    print(f"\n{'='*100}")
    print("[K-FOLD] VALIDATION CROISEE (5 folds)")
    print("=" * 100)

    print(f"{'CONFIG':<18} | {'AVG WR':>8} | {'AVG TRADES/FOLD':>15} | {'TOTAL P&L':>12}")
    print("-" * 70)

    for name, config in CONFIGS.items():
        kfold = run_kfold_validation(all_trades, config, k=5)
        print(f"{name:<18} | {kfold['avg_wr']:>7.1f}% | {kfold['avg_count_per_fold']:>15.1f} | ${kfold['total_pnl']:>10.2f}")

    # ============================================
    # ANALYSE PAR SYMBOLE
    # ============================================
    print(f"\n{'='*100}")
    print("[SYMBOLE] PERFORMANCE PAR SYMBOLE AVEC SEUILS BALANCED")
    print("=" * 100)

    balanced_config = CONFIGS['BALANCED']
    balanced_filtered = apply_filter(all_trades, balanced_config)

    for symbol in ['ES', 'NQ']:
        sym_trades = [t for t in balanced_filtered if t['symbol'] == symbol]
        if sym_trades:
            metrics = calculate_metrics(sym_trades)
            print(f"   {symbol}: {metrics['count']:>3} trades | WR: {metrics['wr']:>5.1f}% | P&L: ${metrics['pnl']:>8.2f}")

    # ============================================
    # ANALYSE PAR DIRECTION
    # ============================================
    print(f"\n{'='*100}")
    print("[DIRECTION] PERFORMANCE PAR DIRECTION AVEC SEUILS BALANCED")
    print("=" * 100)

    for direction in ['LONG', 'SHORT']:
        dir_trades = [t for t in balanced_filtered if t['direction'] == direction]
        if dir_trades:
            metrics = calculate_metrics(dir_trades)
            print(f"   {direction}: {metrics['count']:>3} trades | WR: {metrics['wr']:>5.1f}% | P&L: ${metrics['pnl']:>8.2f}")

    # ============================================
    # RECOMMANDATION FINALE
    # ============================================
    print(f"\n{'='*100}")
    print("[RECOMMANDATION] MEILLEURE CONFIGURATION")
    print("=" * 100)

    # Trouver le meilleur compromis WR/Volume
    best_config = None
    best_score = 0

    for name, data in results.items():
        metrics = data['metrics']
        if metrics['count'] < 20:  # Minimum de trades pour être statistiquement significatif
            continue

        # Score = WR * sqrt(count) pour favoriser à la fois WR et volume
        retention = metrics['count'] / len(all_trades)
        score = metrics['wr'] * (retention ** 0.3)  # Pondération légère pour le volume

        if score > best_score:
            best_score = score
            best_config = name

    if best_config:
        cfg = results[best_config]
        print(f"\n   [GAGNANT] {best_config}")
        print(f"   {cfg['config']['description']}")
        print(f"\n   Seuils:")
        print(f"      - MenthorQ  >= {cfg['config']['menthorq_min']:.2f}")
        print(f"      - OrderFlow >= {cfg['config']['orderflow_min']:.2f}")
        print(f"      - Context   >= {cfg['config']['context_min']:.2f}")
        print(f"      - Confluence >= {cfg['config']['confluence_min']:.2f}")
        print(f"\n   Résultats:")
        print(f"      - Win Rate: {cfg['metrics']['wr']:.1f}%")
        print(f"      - Trades: {cfg['metrics']['count']} ({100*cfg['metrics']['count']/len(all_trades):.0f}% rétention)")
        print(f"      - P&L Total: ${cfg['metrics']['pnl']:.2f}")
        print(f"      - Profit Factor: {cfg['metrics']['profit_factor']:.2f}")

    # ============================================
    # CODE PRET A APPLIQUER
    # ============================================
    print(f"\n{'='*100}")
    print("[CODE] A AJOUTER DANS unified_thresholds.py")
    print("=" * 100)

    if best_config and best_config != 'ACTUEL':
        cfg = results[best_config]['config']
        print(f"""
# ============================================
# NOUVEAUX SEUILS VALIDES PAR BACKTEST
# Configuration: {best_config}
# Win Rate attendu: {results[best_config]['metrics']['wr']:.1f}%
# ============================================

MIN_LAYER_THRESHOLDS = {{
    'ES': {{
        'menthorq_min': {cfg['menthorq_min']:.2f},
        'orderflow_min': {cfg['orderflow_min']:.2f},
        'context_min': {cfg['context_min']:.2f},
    }},
    'NQ': {{
        'menthorq_min': {cfg['menthorq_min']:.2f},
        'orderflow_min': {cfg['orderflow_min']:.2f},
        'context_min': {cfg['context_min']:.2f},
    }},
}}

MIN_CONFLUENCE_TOTAL = {cfg['confluence_min']:.2f}

# ============================================
# IMPACT ATTENDU
# ============================================
# - Trades par jour: ~{results[best_config]['metrics']['count'] / len(DATES):.0f} (vs ~{len(all_trades) / len(DATES):.0f} actuellement)
# - Win Rate: {results[best_config]['metrics']['wr']:.1f}% (vs {base_metrics['wr']:.1f}% actuellement)
# - Amélioration P&L: +{results[best_config]['metrics']['pnl'] - base_metrics['pnl']:.2f}$
""")
    else:
        print("\n   [INFO] Les seuils actuels sont déjà optimaux selon le backtest.")

    print("=" * 100)
    print("[FIN] Backtest terminé")
    print("=" * 100)

if __name__ == "__main__":
    main()

