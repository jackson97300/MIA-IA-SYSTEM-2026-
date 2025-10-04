"""
utils/diagnose_cumulative_delta.py
Diagnostic des écarts entre NBCV et cum_delta dérivé des trades.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import numpy as np

# Assurer import des modules locaux
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Lit un fichier JSONL et retourne les lignes valides."""
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with open(path, 'r', encoding='utf-8') as f:
        for ln in f:
            try:
                rows.append(json.loads(ln))
            except Exception:
                continue
    return rows


def _extract_trade_fields(r: Dict[str, Any]) -> Tuple[float, float, float] | None:
    """Extrait (t, p, q) d'un trade."""
    t_keys = ["t", "time", "ts", "timestamp"]
    p_keys = ["px", "p", "price", "Price"]
    q_keys = ["vol", "q", "qty", "volume", "Volume", "size", "Size"]
    
    t = p = q = None
    for k in t_keys:
        if k in r:
            try:
                t = float(r[k])
                break
            except Exception:
                pass
    for k in p_keys:
        if k in r:
            try:
                p = float(r[k])
                break
            except Exception:
                pass
    for k in q_keys:
        if k in r:
            try:
                q = float(r[k])
                break
            except Exception:
                pass
    
    if t is None or p is None or q is None:
        return None
    return (t, p, q)


def diagnose_cumulative_delta(root: Path, ymd: str, symbol: str) -> None:
    """
    Diagnostique les écarts entre NBCV et cum_delta dérivé des trades.
    """
    print(f"🔍 DIAGNOSTIC CUMULATIVE DELTA - {symbol} - {ymd}")
    print("=" * 60)
    
    # Chemins des fichiers
    nbcv_fp = root / f"CHART_1/CLEAN/chart_1_nbcv_{ymd}_{symbol}.jsonl"
    trade_fp = root / f"CHART_1/CLEAN/chart_1_trade_{ymd}_{symbol}.jsonl"
    
    if not nbcv_fp.exists():
        print(f"❌ Fichier NBCV manquant: {nbcv_fp}")
        return
    
    if not trade_fp.exists():
        print(f"❌ Fichier trade manquant: {trade_fp}")
        return
    
    # 1. Analyser NBCV
    print("\n📊 ANALYSE NBCV:")
    nbcv_rows = _read_jsonl(nbcv_fp)
    print(f"   Lignes NBCV: {len(nbcv_rows)}")
    
    nbcv_series = []
    for r in nbcv_rows:
        if r.get('type') != 'nbcv':
            continue
        try:
            t = float(r.get('t'))
            cum_delta = float(r.get('cumulative_delta', 0))
            nbcv_series.append({'t': t, 'cum_delta': cum_delta})
        except Exception:
            continue
    
    print(f"   Points NBCV valides: {len(nbcv_series)}")
    if nbcv_series:
        nbcv_series.sort(key=lambda x: x['t'])
        print(f"   Plage temporelle: {nbcv_series[0]['t']:.6f} → {nbcv_series[-1]['t']:.6f}")
        print(f"   Cum_delta range: {min(r['cum_delta'] for r in nbcv_series):.1f} → {max(r['cum_delta'] for r in nbcv_series):.1f}")
    
    # 2. Analyser trades et calculer cum_delta dérivé
    print("\n📊 ANALYSE TRADES:")
    trade_rows = _read_jsonl(trade_fp)
    print(f"   Lignes trades: {len(trade_rows)}")
    
    # Extraire et dédupliquer les trades
    seen = set()
    ticks = []
    cum = 0.0
    trade_cum_series = []
    
    for tr in trade_rows:
        extracted = _extract_trade_fields(tr)
        if extracted is None:
            continue
        t, p, q = extracted
        
        try:
            if not (np.isnan(t) or np.isnan(p) or np.isnan(q)) and q > 0:
                k = (t, p, q)
                if k not in seen:
                    seen.add(k)
                    ticks.append({"t": t, "p": p, "q": q})
                    
                    # Calculer cum_delta depuis side
                    side = str(tr.get('side') or '').upper()
                    if side == 'BUY':
                        cum += float(q)
                    elif side == 'SELL':
                        cum -= float(q)
                    
                    trade_cum_series.append({'t': float(t), 'cum_delta': float(cum)})
        except Exception:
            continue
    
    print(f"   Trades uniques: {len(ticks)}")
    print(f"   Points cum_delta dérivé: {len(trade_cum_series)}")
    if trade_cum_series:
        trade_cum_series.sort(key=lambda x: x['t'])
        print(f"   Plage temporelle: {trade_cum_series[0]['t']:.6f} → {trade_cum_series[-1]['t']:.6f}")
        print(f"   Cum_delta range: {min(r['cum_delta'] for r in trade_cum_series):.1f} → {max(r['cum_delta'] for r in trade_cum_series):.1f}")
    
    # 3. Comparaison détaillée
    print("\n📊 COMPARAISON DÉTAILLÉE:")
    if not nbcv_series or not trade_cum_series:
        print("   ❌ Données insuffisantes pour comparaison")
        return
    
    # Aligner par temps et calculer les écarts
    trade_idx = 0
    pairs = []
    errors = []
    
    for nbcv_pt in nbcv_series:
        nbcv_t = nbcv_pt['t']
        nbcv_val = nbcv_pt['cum_delta']
        
        # Trouver le point trade le plus proche
        while (trade_idx + 1 < len(trade_cum_series) and 
               trade_cum_series[trade_idx + 1]['t'] <= nbcv_t):
            trade_idx += 1
        
        if trade_idx < len(trade_cum_series):
            trade_val = trade_cum_series[trade_idx]['cum_delta']
            pairs.append((nbcv_val, trade_val))
            errors.append(abs(nbcv_val - trade_val))
    
    if pairs:
        print(f"   Points comparés: {len(pairs)}")
        print(f"   Écart moyen: {np.mean(errors):.1f}")
        print(f"   Écart médian: {np.median(errors):.1f}")
        print(f"   Écart p95: {np.percentile(errors, 95):.1f}")
        print(f"   Écart p99: {np.percentile(errors, 99):.1f}")
        print(f"   Écart max: {np.max(errors):.1f}")
        
        # Analyser les plus gros écarts
        print("\n🔍 TOP 5 PLUS GROS ÉCARTS:")
        sorted_pairs = sorted(zip(pairs, errors), key=lambda x: x[1], reverse=True)
        for i, ((nbcv_val, trade_val), error) in enumerate(sorted_pairs[:5]):
            print(f"   #{i+1}: NBCV={nbcv_val:.1f}, Trade={trade_val:.1f}, Écart={error:.1f}")
    
    # 4. Analyse des patterns
    print("\n📊 ANALYSE DES PATTERNS:")
    if len(errors) > 10:
        # Vérifier si les écarts sont systématiques
        nbcv_vals = [p[0] for p in pairs]
        trade_vals = [p[1] for p in pairs]
        
        correlation = np.corrcoef(nbcv_vals, trade_vals)[0, 1]
        print(f"   Corrélation NBCV vs Trade: {correlation:.4f}")
        
        # Vérifier si l'écart est constant (offset)
        diff_vals = [nbcv - trade for nbcv, trade in pairs]
        diff_std = np.std(diff_vals)
        print(f"   Écart-type des différences: {diff_std:.1f}")
        
        if diff_std < 100:  # Écart relativement constant
            offset = np.mean(diff_vals)
            print(f"   ⚠️  ÉCART SYSTÉMATIQUE DÉTECTÉ: offset ≈ {offset:.1f}")
            print(f"   💡 Solution: Ajuster NBCV ou cum_delta dérivé de {offset:.1f}")
        else:
            print(f"   ⚠️  ÉCARTS VARIABLES: pas d'offset constant")
            print(f"   💡 Solution: Vérifier la logique de calcul des deux méthodes")


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Diagnostique les écarts Cumulative Delta")
    ap.add_argument("--root", required=True, help="Dossier racine de la journée")
    ap.add_argument("--date", required=True, help="YYYYMMDD")
    ap.add_argument("--symbol", required=True, help="Symbole (ex: ESZ25-CME)")
    args = ap.parse_args()
    
    diagnose_cumulative_delta(Path(args.root), args.date, args.symbol)


if __name__ == "__main__":
    main()


