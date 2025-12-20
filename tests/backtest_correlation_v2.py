# -*- coding: utf-8 -*-
"""
BACKTEST CORRELATION FILTER ES/NQ - V2 CORRIGE
==============================================
Version corrigee avec synchronisation temporelle des donnees.

Usage:
    python tests/backtest_correlation_v2.py
"""

import json
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DATA_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")
CHART_MAPPING = {'ES': 3, 'NQ': 9}
MOIS_FR = {
    1: 'JANVIER', 2: 'FEVRIER', 3: 'MARS', 4: 'AVRIL',
    5: 'MAI', 6: 'JUIN', 7: 'JUILLET', 8: 'AOUT',
    9: 'SEPTEMBRE', 10: 'OCTOBRE', 11: 'NOVEMBRE', 12: 'DECEMBRE'
}


# ============================================================================
# CHARGEMENT DONNEES
# ============================================================================

def get_data_path(date: datetime, symbol: str) -> Optional[Path]:
    chart_id = CHART_MAPPING.get(symbol)
    if not chart_id:
        return None

    mois = MOIS_FR.get(date.month)
    date_str = date.strftime('%Y%m%d')
    path = BASE_DATA_PATH / mois / date_str / f"CHART_{chart_id}" / "ML_READY"

    if path.exists():
        files = list(path.glob(f"ml_{symbol}*.jsonl"))
        if files:
            return files[0]
    return None


def load_data_fast(filepath: Path, max_lines: int = 50000) -> List[Tuple[int, float]]:
    """Retourne liste de (timestamp_ms, mid_price)"""
    data = []
    if not filepath or not filepath.exists():
        return data

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= max_lines:
                    break
                if line.strip():
                    try:
                        snap = json.loads(line)
                        t_ms = snap.get('t_ms', 0)
                        mid = snap.get('mid', 0)
                        if t_ms > 0 and mid > 0:
                            data.append((t_ms, mid))
                    except:
                        continue
    except Exception as e:
        print(f"[X] Erreur: {e}")

    return data


def load_week_data(start_date: datetime, days: int = 5) -> Dict[str, List[Tuple[int, float]]]:
    """Charge ES et NQ pour plusieurs jours"""
    all_data = {'ES': [], 'NQ': []}

    dates_to_load = []
    for i in range(days + 2):
        date = start_date + timedelta(days=i)
        if date.weekday() < 5:
            dates_to_load.append(date)
        if len(dates_to_load) >= days:
            break

    iterator = tqdm(dates_to_load, desc="Chargement") if HAS_TQDM else dates_to_load

    for date in iterator:
        for symbol in ['ES', 'NQ']:
            filepath = get_data_path(date, symbol)
            if filepath:
                day_data = load_data_fast(filepath, max_lines=30000)
                if day_data:
                    all_data[symbol].extend(day_data)

    return all_data


# ============================================================================
# SYNCHRONISATION TEMPORELLE (CLE!)
# ============================================================================

def synchronize_data(es_data: List[Tuple[int, float]],
                     nq_data: List[Tuple[int, float]],
                     bucket_size_ms: int = 1000) -> Tuple[List[float], List[float]]:
    """
    Synchronise ES et NQ par buckets de temps.
    Retourne deux listes alignees de prix moyens par bucket.

    Args:
        es_data: Liste de (timestamp_ms, price) pour ES
        nq_data: Liste de (timestamp_ms, price) pour NQ
        bucket_size_ms: Taille du bucket en ms (1000 = 1 seconde)

    Returns:
        (es_prices, nq_prices) - Listes alignees
    """
    # Creer des buckets par seconde
    es_buckets = defaultdict(list)
    nq_buckets = defaultdict(list)

    for t_ms, price in es_data:
        bucket = t_ms // bucket_size_ms
        es_buckets[bucket].append(price)

    for t_ms, price in nq_data:
        bucket = t_ms // bucket_size_ms
        nq_buckets[bucket].append(price)

    # Trouver les buckets communs
    common_buckets = sorted(set(es_buckets.keys()) & set(nq_buckets.keys()))

    if not common_buckets:
        return [], []

    # Calculer prix moyen par bucket
    es_synced = []
    nq_synced = []

    for bucket in common_buckets:
        es_synced.append(np.mean(es_buckets[bucket]))
        nq_synced.append(np.mean(nq_buckets[bucket]))

    return es_synced, nq_synced


# ============================================================================
# CALCUL CORRELATION (CORRECT)
# ============================================================================

def calculate_rolling_correlations(es_prices: List[float],
                                    nq_prices: List[float],
                                    window: int = 30) -> List[float]:
    """
    Calcule la correlation Pearson sur une fenetre glissante.

    Args:
        es_prices: Prix ES synchronises
        nq_prices: Prix NQ synchronises
        window: Taille de la fenetre

    Returns:
        Liste des correlations
    """
    correlations = []

    if len(es_prices) < window or len(nq_prices) < window:
        return correlations

    es = np.array(es_prices)
    nq = np.array(nq_prices)

    # Calculer les returns
    es_ret = np.diff(es) / es[:-1]
    nq_ret = np.diff(nq) / nq[:-1]

    # Rolling correlation
    iterator = range(window, len(es_ret))
    if HAS_TQDM:
        iterator = tqdm(iterator, desc="Correlation")

    for i in iterator:
        es_window = es_ret[i-window:i]
        nq_window = nq_ret[i-window:i]

        # Eviter les cas degeneres
        if np.std(es_window) == 0 or np.std(nq_window) == 0:
            correlations.append(1.0)
            continue

        try:
            corr = np.corrcoef(es_window, nq_window)[0, 1]
            if not np.isnan(corr):
                correlations.append(corr)
        except:
            pass

    return correlations


# ============================================================================
# BACKTEST
# ============================================================================

def run_backtest(correlations: List[float], threshold: float = 0.50) -> Dict:
    """Analyse les correlations et calcule l'impact du filtre"""

    if not correlations:
        return {'error': 'Pas de donnees'}

    arr = np.array(correlations)

    below_threshold = np.sum(arr < threshold)

    return {
        'total_samples': len(correlations),
        'mean': np.mean(arr),
        'std': np.std(arr),
        'min': np.min(arr),
        'max': np.max(arr),
        'median': np.median(arr),
        'percentile_5': np.percentile(arr, 5),
        'percentile_25': np.percentile(arr, 25),
        'percentile_75': np.percentile(arr, 75),
        'percentile_95': np.percentile(arr, 95),
        'below_threshold': below_threshold,
        'below_rate': below_threshold / len(correlations),
    }


def print_results(results: Dict, threshold: float):
    print("\n" + "=" * 60)
    print(f"RESULTATS BACKTEST (seuil={threshold})")
    print("=" * 60)

    print(f"\nSTATISTIQUES CORRELATION ES/NQ (SYNCHRONISEE):")
    print(f"   Echantillons: {results['total_samples']:,}")
    print(f"   Moyenne:      {results['mean']:.3f}")
    print(f"   Ecart-type:   {results['std']:.3f}")
    print(f"   Min:          {results['min']:.3f}")
    print(f"   Max:          {results['max']:.3f}")

    print(f"\nDISTRIBUTION:")
    print(f"    5%:  {results['percentile_5']:.3f}")
    print(f"   25%:  {results['percentile_25']:.3f}")
    print(f"   50%:  {results['median']:.3f}")
    print(f"   75%:  {results['percentile_75']:.3f}")
    print(f"   95%:  {results['percentile_95']:.3f}")

    print(f"\nIMPACT DU FILTRE:")
    print(f"   Periodes sous {threshold}: {results['below_threshold']} / {results['total_samples']}")
    print(f"   Taux de blocage:      {results['below_rate']*100:.1f}%")

    print("\n" + "=" * 60)


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("BACKTEST CORRELATION FILTER ES/NQ - V2 CORRIGE")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    print("[!] Cette version SYNCHRONISE les donnees ES/NQ par seconde")
    print("    avant de calculer la correlation (plus precis)")
    print()

    # Dates
    today = datetime.now()
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday + 7)

    print(f"Periode: {last_monday.strftime('%d/%m')} -> {today.strftime('%d/%m/%Y')}")
    print("-" * 60)

    # Charger donnees
    data = load_week_data(last_monday, days=7)

    print("-" * 60)
    print(f"ES brut: {len(data['ES']):,} points")
    print(f"NQ brut: {len(data['NQ']):,} points")

    if len(data['ES']) < 1000 or len(data['NQ']) < 1000:
        print("\n[!] Peu de donnees, essai avec aujourd'hui...")
        today_data = load_week_data(today, days=1)
        if len(today_data['ES']) > 500:
            data = today_data

    if len(data['ES']) < 500 or len(data['NQ']) < 500:
        print("\n[X] Pas assez de donnees!")
        return

    # Synchroniser les donnees
    print("\n[*] Synchronisation temporelle (buckets 1s)...")
    es_synced, nq_synced = synchronize_data(data['ES'], data['NQ'], bucket_size_ms=1000)
    print(f"    Points synchronises: {len(es_synced):,}")

    if len(es_synced) < 100:
        print("[X] Pas assez de points synchronises!")
        return

    # Calculer correlations rolling
    print("\n[*] Calcul correlations rolling (window=30s)...")
    correlations = calculate_rolling_correlations(es_synced, nq_synced, window=30)
    print(f"    Correlations calculees: {len(correlations):,}")

    if not correlations:
        print("[X] Pas de correlations!")
        return

    # Test differents seuils
    print("\n" + "=" * 60)
    print("TEST DIFFERENTS SEUILS")
    print("=" * 60)

    thresholds = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80]

    for threshold in thresholds:
        results = run_backtest(correlations, threshold)
        print(f"\n>>> Seuil {threshold}:")
        print(f"    Correlation moyenne: {results['mean']:.3f}")
        print(f"    % sous seuil: {results['below_rate']*100:.1f}%")
        print(f"    -> {results['below_threshold']} periodes bloqueraient sur {results['total_samples']}")

    # Resultats detailles pour 0.50
    print("\n")
    results = run_backtest(correlations, 0.50)
    print_results(results, 0.50)

    # Conclusion
    print("\nCONCLUSION:")
    mean_corr = results['mean']

    if mean_corr > 0.7:
        print(f"   [OK] Correlation moyenne = {mean_corr:.3f} (ELEVE)")
        print("   -> ES/NQ tres correles comme attendu!")
        if results['below_rate'] < 0.10:
            print(f"   -> Seulement {results['below_rate']*100:.1f}% sous 0.50")
            print("   -> FILTRE PEU UTILE (rarement active)")
        else:
            print(f"   -> {results['below_rate']*100:.1f}% sous 0.50")
            print("   -> FILTRE UTILE pour ces periodes")
    elif mean_corr > 0.5:
        print(f"   [~] Correlation moyenne = {mean_corr:.3f} (MODERE)")
        print("   -> FILTRE POTENTIELLEMENT UTILE")
    else:
        print(f"   [!] Correlation moyenne = {mean_corr:.3f} (FAIBLE)")
        print("   -> Verifier les donnees!")

    print()


if __name__ == "__main__":
    main()



















