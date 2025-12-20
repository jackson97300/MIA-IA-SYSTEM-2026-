# -*- coding: utf-8 -*-
"""
BACKTEST CORRELATION FILTER ES/NQ
=================================
Teste le filtre de correlation sur les donnees de la semaine derniere.

Usage:
    python tests/backtest_correlation_filter.py

Cree: 08/12/2025
"""

import json
import sys
import io
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import deque
import numpy as np

# Fix encodage Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Barre de progression
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("[!] tqdm non installe - pas de barre de progression")


# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DATA_PATH = Path("D:/MIA_IA_system/DATA_SIERRA_CHART/DATA_2025")

CHART_MAPPING = {'ES': 3, 'NQ': 9, 'RTY': 1}

MOIS_FR = {
    1: 'JANVIER', 2: 'FEVRIER', 3: 'MARS', 4: 'AVRIL',
    5: 'MAI', 6: 'JUIN', 7: 'JUILLET', 8: 'AOUT',
    9: 'SEPTEMBRE', 10: 'OCTOBRE', 11: 'NOVEMBRE', 12: 'DECEMBRE'
}


# ============================================================================
# CORRELATION FILTER (INLINE - Evite les imports lourds)
# ============================================================================

class CorrelationFilterSimple:
    """Version simplifiee pour backtest rapide"""

    def __init__(self, window: int = 30, min_correlation: float = 0.50):
        self.window = window
        self.min_correlation = min_correlation
        self.es_prices = deque(maxlen=window)
        self.nq_prices = deque(maxlen=window)

    def update(self, symbol: str, price: float):
        if symbol == 'ES':
            self.es_prices.append(price)
        elif symbol == 'NQ':
            self.nq_prices.append(price)

    def calculate_correlation(self) -> float:
        if len(self.es_prices) < 15 or len(self.nq_prices) < 15:
            return 1.0

        es = np.array(list(self.es_prices))
        nq = np.array(list(self.nq_prices))

        min_len = min(len(es), len(nq))
        es, nq = es[-min_len:], nq[-min_len:]

        es_ret = np.diff(es)
        nq_ret = np.diff(nq)

        if np.std(es_ret) == 0 or np.std(nq_ret) == 0:
            return 1.0

        try:
            corr = np.corrcoef(es_ret, nq_ret)[0, 1]
            return corr if not np.isnan(corr) else 1.0
        except:
            return 1.0

    def should_trade(self) -> tuple:
        corr = self.calculate_correlation()
        if corr < self.min_correlation:
            return (False, f"r={corr:.3f}", corr)
        return (True, f"r={corr:.3f}", corr)


# ============================================================================
# CHARGEMENT DONNEES (Optimise)
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


def load_data_fast(filepath: Path, max_lines: int = 50000) -> List[Dict]:
    """Chargement rapide avec limite"""
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
                        data.append({
                            't_ms': snap.get('t_ms', 0),
                            'mid': snap.get('mid', 0)
                        })
                    except:
                        continue
    except Exception as e:
        print(f"[X] Erreur: {e}")

    return data


def load_week_data(start_date: datetime, days: int = 5) -> Dict[str, List[Dict]]:
    """Charge ES et NQ pour plusieurs jours"""
    all_data = {'ES': [], 'NQ': []}

    dates_to_load = []
    for i in range(days + 2):
        date = start_date + timedelta(days=i)
        if date.weekday() < 5:
            dates_to_load.append(date)
        if len(dates_to_load) >= days:
            break

    iterator = tqdm(dates_to_load, desc="Chargement jours") if HAS_TQDM else dates_to_load

    for date in iterator:
        for symbol in ['ES', 'NQ']:
            filepath = get_data_path(date, symbol)
            if filepath:
                day_data = load_data_fast(filepath, max_lines=30000)
                if day_data:
                    all_data[symbol].extend(day_data)
                    if not HAS_TQDM:
                        print(f"  [OK] {date.strftime('%Y-%m-%d')} {symbol}: {len(day_data):,}")

    return all_data


# ============================================================================
# BACKTEST
# ============================================================================

def run_backtest(es_data: List[Dict], nq_data: List[Dict],
                 min_correlation: float = 0.50, window: int = 30) -> Dict:
    """Backtest le filtre de correlation"""

    filter_obj = CorrelationFilterSimple(window=window, min_correlation=min_correlation)

    # Fusionner et trier par timestamp
    all_points = []
    for snap in es_data:
        all_points.append(('ES', snap['t_ms'], snap['mid']))
    for snap in nq_data:
        all_points.append(('NQ', snap['t_ms'], snap['mid']))

    all_points.sort(key=lambda x: x[1])

    # Stats
    correlations = []
    divergence_periods = 0
    total_checks = 0

    # Parcourir avec barre de progression
    sample_rate = max(1, len(all_points) // 5000)

    iterator = range(0, len(all_points), sample_rate)
    if HAS_TQDM:
        iterator = tqdm(iterator, desc="Calcul correlations", total=len(all_points)//sample_rate)

    for i in iterator:
        symbol, t_ms, mid = all_points[i]
        filter_obj.update(symbol, mid)

        # Alimenter aussi l'autre symbole si proche
        for j in range(max(0, i-10), min(len(all_points), i+10)):
            s2, t2, m2 = all_points[j]
            if s2 != symbol:
                filter_obj.update(s2, m2)

        can_trade, reason, corr = filter_obj.should_trade()

        if corr != 1.0:
            correlations.append(corr)
            total_checks += 1
            if not can_trade:
                divergence_periods += 1

    if not correlations:
        return {'error': 'Pas assez de donnees'}

    return {
        'total_checks': total_checks,
        'divergence_periods': divergence_periods,
        'divergence_rate': divergence_periods / total_checks if total_checks > 0 else 0,
        'mean_correlation': np.mean(correlations),
        'std_correlation': np.std(correlations),
        'min_correlation': np.min(correlations),
        'max_correlation': np.max(correlations),
        'median_correlation': np.median(correlations),
        'below_threshold': sum(1 for c in correlations if c < min_correlation) / len(correlations),
        'percentile_5': np.percentile(correlations, 5),
        'percentile_25': np.percentile(correlations, 25),
        'percentile_75': np.percentile(correlations, 75),
        'percentile_95': np.percentile(correlations, 95),
    }


def print_results(results: Dict, threshold: float):
    """Affiche les resultats"""
    print("\n" + "=" * 60)
    print(f"RESULTATS BACKTEST (seuil={threshold})")
    print("=" * 60)

    print(f"\nSTATISTIQUES CORRELATION ES/NQ:")
    print(f"   Echantillons: {results['total_checks']:,}")
    print(f"   Moyenne:      {results['mean_correlation']:.3f}")
    print(f"   Ecart-type:   {results['std_correlation']:.3f}")
    print(f"   Min:          {results['min_correlation']:.3f}")
    print(f"   Max:          {results['max_correlation']:.3f}")

    print(f"\nDISTRIBUTION:")
    print(f"    5%:  {results['percentile_5']:.3f}")
    print(f"   25%:  {results['percentile_25']:.3f}")
    print(f"   50%:  {results['median_correlation']:.3f}")
    print(f"   75%:  {results['percentile_75']:.3f}")
    print(f"   95%:  {results['percentile_95']:.3f}")

    print(f"\nIMPACT DU FILTRE:")
    print(f"   Periodes divergentes: {results['divergence_periods']} / {results['total_checks']}")
    print(f"   Taux de blocage:      {results['divergence_rate']*100:.1f}%")
    print(f"   % sous seuil {threshold}: {results['below_threshold']*100:.1f}%")

    print("\n" + "=" * 60)


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("BACKTEST CORRELATION FILTER ES/NQ")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    # Dates: semaine derniere + aujourd'hui
    today = datetime.now()
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday + 7)

    print(f"Periode: {last_monday.strftime('%d/%m')} -> {today.strftime('%d/%m/%Y')}")
    print("-" * 60)

    # Charger donnees
    data = load_week_data(last_monday, days=7)

    print("-" * 60)
    print(f"ES: {len(data['ES']):,} points")
    print(f"NQ: {len(data['NQ']):,} points")

    if len(data['ES']) < 1000 or len(data['NQ']) < 1000:
        print("\n[!] Peu de donnees, essai avec aujourd'hui...")
        today_data = load_week_data(today, days=1)
        if len(today_data['ES']) > 1000:
            data = today_data
            print(f"[OK] Aujourd'hui: ES={len(data['ES']):,}, NQ={len(data['NQ']):,}")

    if len(data['ES']) < 500 or len(data['NQ']) < 500:
        print("\n[X] Pas assez de donnees!")
        return

    # Test differents seuils
    print("\n" + "=" * 60)
    print("TEST DIFFERENTS SEUILS")
    print("=" * 60)

    thresholds = [0.30, 0.40, 0.50, 0.60, 0.70]

    for threshold in thresholds:
        print(f"\n>>> Test seuil = {threshold}...")
        results = run_backtest(data['ES'], data['NQ'], min_correlation=threshold, window=30)

        if 'error' in results:
            print(f"   [X] {results['error']}")
            continue

        print(f"   Correlation moyenne: {results['mean_correlation']:.3f}")
        print(f"   Taux blocage:        {results['divergence_rate']*100:.1f}%")
        print(f"   % sous seuil:        {results['below_threshold']*100:.1f}%")

    # Resultats detailles pour seuil 0.50
    print("\n")
    results_050 = run_backtest(data['ES'], data['NQ'], min_correlation=0.50, window=30)
    print_results(results_050, 0.50)

    # Conclusion
    print("\nCONCLUSION:")
    if results_050['below_threshold'] > 0.15:
        print(f"   [!] {results_050['below_threshold']*100:.1f}% du temps ES/NQ decorreles")
        print("   -> FILTRE UTILE - A implementer")
    elif results_050['below_threshold'] > 0.05:
        print(f"   [~] {results_050['below_threshold']*100:.1f}% du temps decorreles")
        print("   -> FILTRE OPTIONNEL - Impact modere")
    else:
        print(f"   [OK] Seulement {results_050['below_threshold']*100:.1f}% decorreles")
        print("   -> FILTRE PEU UTILE - ES/NQ tres alignes")

    print()


if __name__ == "__main__":
    main()
