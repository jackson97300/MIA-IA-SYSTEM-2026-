"""
🔗 BACKTEST CORRÉLATION ES/NQ - Impact sur les trades
======================================================

Teste le module de corrélation sur les données de la semaine.
Mesure combien de trades auraient été confirmés ou bloqués.

Date: 07/12/2025
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from tqdm import tqdm
except ImportError:
    print("[INSTALL] Installation de tqdm...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "tqdm", "-q"])
    from tqdm import tqdm

# Désactiver les logs pour un affichage propre
import logging
logging.disable(logging.INFO)

# Import du module de corrélation
from features.correlation.es_nq_correlation import ESNQCorrelationModule, CorrelationResult

# Configuration
DATE_RANGE = ["20251202", "20251203", "20251204", "20251205"]
DATA_MONTH = "DECEMBRE"
DATA_YEAR = 2025
BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\DECEMBRE")
CHART_ES = 3
CHART_NQ = 9

# Seuils pour les trades
DELTA_THRESHOLD = 100  # Delta minimum pour considérer un signal
SYNC_TOLERANCE_MS = 5000  # 5 secondes de tolérance

# ============================================================================
# FONCTIONS
# ============================================================================

def load_snapshots(date_str: str, symbol: str) -> List[Dict]:
    """Charge les snapshots pour une date et symbole"""
    chart_id = CHART_ES if symbol == "ES" else CHART_NQ
    path = BASE_PATH / date_str / f"CHART_{chart_id}" / "ML_READY"

    if not path.exists():
        return []

    files = list(path.glob(f"ml_*{symbol}*.jsonl"))
    if not files:
        return []

    snaps = []
    with open(files[0], 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    snaps.append(json.loads(line))
                except:
                    pass
    return snaps


def get_direction(delta: float) -> str:
    """Retourne la direction basée sur le delta"""
    if delta > DELTA_THRESHOLD:
        return "LONG"
    elif delta < -DELTA_THRESHOLD:
        return "SHORT"
    return "NEUTRAL"


def find_closest_snapshot(target_time: int, snapshots: List[Dict], tolerance_ms: int = SYNC_TOLERANCE_MS) -> Optional[Dict]:
    """Trouve le snapshot le plus proche dans le temps"""
    closest = None
    min_diff = float('inf')

    for snap in snapshots:
        snap_time = snap.get('t_ms', 0)
        diff = abs(target_time - snap_time)
        if diff < min_diff and diff <= tolerance_ms:
            min_diff = diff
            closest = snap

    return closest


def main():
    print("="*100)
    print("[CORRELATION] BACKTEST CORRELATION ES/NQ - Impact sur les trades")
    print("="*100)
    print(f"\nPeriode: {DATE_RANGE[0]} -> {DATE_RANGE[-1]} (4 jours)")

    # Charger toutes les données
    print("\n[LOAD] Chargement des donnees...")
    all_es = []
    all_nq = []

    for date in tqdm(DATE_RANGE, desc="[LOAD] Jours", unit="jour"):
        es_snaps = load_snapshots(date, "ES")
        nq_snaps = load_snapshots(date, "NQ")

        if es_snaps:
            for s in es_snaps:
                s['date'] = date
            all_es.extend(es_snaps)
        if nq_snaps:
            for s in nq_snaps:
                s['date'] = date
            all_nq.extend(nq_snaps)

        print(f"   {date}: ES={len(es_snaps):,} | NQ={len(nq_snaps):,}")

    print(f"\n   TOTAL: ES={len(all_es):,} | NQ={len(all_nq):,}")

    # Indexer NQ par timestamp
    print("\n[INDEX] Indexation NQ par timestamp...")
    nq_by_time = {}
    for snap in tqdm(all_nq, desc="[INDEX] NQ snapshots", unit="snap"):
        t = snap.get('t_ms', 0)
        if t > 0:
            nq_by_time[t] = snap

    # Initialiser le module de corrélation
    correlation_module = ESNQCorrelationModule(window_size=60)

    # Analyser tous les signaux potentiels
    print("\n[ANALYZE] Analyse des signaux...")

    # Stats
    stats = {
        'total_signals_es': 0,
        'total_signals_nq': 0,
        'confirmed': 0,
        'blocked_divergence': 0,
        'blocked_neutral': 0,
        'no_correlation_data': 0,
        'by_direction': defaultdict(lambda: {'total': 0, 'confirmed': 0, 'blocked': 0}),
        'by_recommendation': defaultdict(int),
        'correlation_scores': [],
        'examples_confirmed': [],
        'examples_blocked': [],
    }

    # Parcourir ES et synchroniser avec NQ
    last_signal_time = 0
    COOLDOWN = 300000  # 5 minutes

    for i, es_snap in enumerate(tqdm(all_es, desc="[ANALYZE] Analyse correlation", unit="snap")):
        es_time = es_snap.get('t_ms', 0)
        es_delta = es_snap.get('delta', 0)
        es_mid = es_snap.get('mid', 0)

        # Trouver NQ correspondant
        nq_snap = find_closest_snapshot(es_time, list(nq_by_time.values()))
        if not nq_snap:
            continue

        # Mettre à jour la corrélation
        result = correlation_module.update(es_snap, nq_snap)

        # Vérifier si c'est un signal potentiel (delta fort)
        direction = get_direction(es_delta)
        if direction == "NEUTRAL":
            continue

        # Cooldown
        if es_time - last_signal_time < COOLDOWN:
            continue

        last_signal_time = es_time
        stats['total_signals_es'] += 1
        stats['by_direction'][direction]['total'] += 1

        # Analyser avec le module de corrélation
        if not result:
            stats['no_correlation_data'] += 1
            continue

        stats['correlation_scores'].append(result.correlation_score)

        # Vérifier la confirmation
        confirmation = correlation_module.get_confirmation_for_signal("ES", direction)

        stats['by_recommendation'][confirmation['recommendation']] += 1

        if confirmation['confirmed']:
            stats['confirmed'] += 1
            stats['by_direction'][direction]['confirmed'] += 1

            if len(stats['examples_confirmed']) < 5:
                stats['examples_confirmed'].append({
                    'time': datetime.fromtimestamp(es_time/1000).strftime('%Y-%m-%d %H:%M'),
                    'direction': direction,
                    'es_delta': es_delta,
                    'nq_delta': nq_snap.get('delta', 0),
                    'score': result.correlation_score,
                    'reason': confirmation['reason']
                })
        else:
            if confirmation['recommendation'] == 'DIVERGENCE':
                stats['blocked_divergence'] += 1
            else:
                stats['blocked_neutral'] += 1

            stats['by_direction'][direction]['blocked'] += 1

            if len(stats['examples_blocked']) < 5:
                stats['examples_blocked'].append({
                    'time': datetime.fromtimestamp(es_time/1000).strftime('%Y-%m-%d %H:%M'),
                    'direction': direction,
                    'es_delta': es_delta,
                    'nq_delta': nq_snap.get('delta', 0),
                    'nq_direction': result.direction_nq,
                    'score': result.correlation_score,
                    'reason': confirmation['reason']
                })

    # Afficher les résultats
    print("\n" + "="*100)
    print("[RESULTS] RESULTATS DE L'ANALYSE")
    print("="*100)

    total = stats['total_signals_es']
    confirmed = stats['confirmed']
    blocked = stats['blocked_divergence'] + stats['blocked_neutral']

    print(f"\n[SIGNALS] Signaux ES analyses: {total}")
    print(f"   - Confirmes par NQ:  {confirmed} ({confirmed/max(total,1)*100:.1f}%)")
    print(f"   - Bloques:           {blocked} ({blocked/max(total,1)*100:.1f}%)")
    print(f"      > Divergence:     {stats['blocked_divergence']}")
    print(f"      > Neutre:         {stats['blocked_neutral']}")
    print(f"   - Sans donnees:      {stats['no_correlation_data']}")

    print(f"\n[DIRECTION] Par direction:")
    for direction in ['LONG', 'SHORT']:
        d = stats['by_direction'][direction]
        print(f"   {direction}: {d['total']} signaux -> {d['confirmed']} confirmes, {d['blocked']} bloques")

    print(f"\n[RECOMMENDATION] Par recommandation:")
    for rec, count in sorted(stats['by_recommendation'].items()):
        print(f"   {rec}: {count}")

    if stats['correlation_scores']:
        avg_score = sum(stats['correlation_scores']) / len(stats['correlation_scores'])
        min_score = min(stats['correlation_scores'])
        max_score = max(stats['correlation_scores'])
        print(f"\n[SCORE] Score de correlation:")
        print(f"   Moyenne: {avg_score:.1f}")
        print(f"   Min: {min_score:.1f} | Max: {max_score:.1f}")

    # Exemples
    print("\n" + "="*100)
    print("[EXAMPLES] EXEMPLES DE SIGNAUX CONFIRMES")
    print("="*100)
    for ex in stats['examples_confirmed']:
        print(f"\n   {ex['time']} | {ex['direction']}")
        print(f"      ES delta: {ex['es_delta']:.0f} | NQ delta: {ex['nq_delta']:.0f}")
        print(f"      Score: {ex['score']:.0f} | {ex['reason']}")

    print("\n" + "="*100)
    print("[EXAMPLES] EXEMPLES DE SIGNAUX BLOQUES")
    print("="*100)
    for ex in stats['examples_blocked']:
        print(f"\n   {ex['time']} | ES={ex['direction']} vs NQ={ex['nq_direction']}")
        print(f"      ES delta: {ex['es_delta']:.0f} | NQ delta: {ex['nq_delta']:.0f}")
        print(f"      Score: {ex['score']:.0f} | {ex['reason']}")

    # Statistiques du module
    print("\n" + "="*100)
    print("[STATS] STATISTIQUES DU MODULE")
    print("="*100)
    print(correlation_module.get_stats_summary())

    # Recommandation finale
    print("\n" + "="*100)
    print("[VERDICT] RECOMMANDATION")
    print("="*100)

    block_rate = blocked / max(total, 1) * 100

    if block_rate > 50:
        print(f"\n[WARN] Le module bloquerait {block_rate:.0f}% des trades!")
        print("   -> A utiliser en MODE INFORMATION seulement")
        print("   -> Afficher l'info mais ne PAS bloquer")
    elif block_rate > 30:
        print(f"\n[CAUTION] Le module bloquerait {block_rate:.0f}% des trades")
        print("   -> Utiliser comme FILTRE SOUPLE")
        print("   -> Reduire la taille si divergence, ne pas bloquer")
    else:
        print(f"\n[OK] Le module bloquerait seulement {block_rate:.0f}% des trades")
        print("   -> Peut etre utilise comme FILTRE STRICT")
        print("   -> Bloquer les trades en divergence")

    # Sauvegarder
    output = {
        'date': datetime.now().isoformat(),
        'total_signals': total,
        'confirmed': confirmed,
        'blocked': blocked,
        'block_rate': block_rate,
        'stats': dict(stats['by_recommendation'])
    }

    output_path = Path(__file__).parent / "results.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n[SAVE] Resultats: {output_path}")


if __name__ == "__main__":
    main()
