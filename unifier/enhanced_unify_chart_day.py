#!/usr/bin/env python3
"""
Unifier amélioré qui exploite le double Cumulative Delta
Version étendue de unify_chart_day.py avec support des nouveaux champs
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
import argparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from unifier.load_cumdelta import load_cumdelta_from_trades, analyze_cumdelta_sessions, detect_reset_events
from utils.clean_jsonl import clean_symbol_file

def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Lit un fichier JSONL et retourne une liste de dictionnaires"""
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

def enhanced_unify_chart_day(root: Path, ymd: str, chart_id: int, symbol: str = None) -> int:
    """
    Unifie les données d'un chart avec support du double Cumulative Delta
    
    Args:
        root: Dossier racine de la journée (…/YYYYMMDD)
        ymd: Date au format YYYYMMDD
        chart_id: Numéro du chart (1, 2, 3, etc.)
        symbol: Symbole à filtrer (optionnel)
    
    Returns:
        0 si succès, 1 si erreur
    """
    print(f"🔍 UNIFICATION CHART {chart_id} - {ymd}")
    if symbol:
        print(f"📊 Symbole: {symbol}")
    print("=" * 50)
    
    # Déterminer le symbole si non fourni
    if not symbol:
        if chart_id == 1:
            symbol = "ESZ25-CME"
        elif chart_id == 2:
            symbol = "NQZ25-CME"
        else:
            print(f"❌ Chart {chart_id} non reconnu, symbole requis")
            return 1
    
    # Nettoyage des fichiers si nécessaire
    clean_dir = root / f"CHART_{chart_id}" / "CLEAN"
    if symbol and not clean_dir.exists():
        clean_dir.mkdir(parents=True, exist_ok=True)
        print(f"🧹 Nettoyage des fichiers pour le symbole {symbol}...")
        
        # Nettoyer les fichiers principaux
        file_types = ["basedata", "trade", "quote", "vwap", "nbcv", "cumulative_delta"]
        for file_type in file_types:
            src_filename = f"chart_{chart_id}_{file_type}_{ymd}.jsonl"
            input_path = root / f"CHART_{chart_id}" / src_filename
            output_path = clean_dir / f"chart_{chart_id}_{file_type}_{ymd}_{symbol}.jsonl"
            
            if input_path.exists():
                try:
                    rows = clean_symbol_file(input_path, output_path, symbol)
                    print(f"   ✅ {file_type}: {rows} lignes nettoyées")
                except Exception as e:
                    print(f"   ❌ Erreur {file_type}: {e}")
    
    # Utiliser le dossier CLEAN si disponible
    data_dir = clean_dir if clean_dir.exists() else root / f"CHART_{chart_id}"
    
    # Charger les cumulative deltas depuis les trades
    trade_file = data_dir / f"chart_{chart_id}_trade_{ymd}_{symbol}.jsonl" if clean_dir.exists() else data_dir / f"chart_{chart_id}_trade_{ymd}.jsonl"
    
    if not trade_file.exists():
        print(f"❌ Fichier de trades non trouvé: {trade_file}")
        return 1
    
    try:
        # Charger les cumulative deltas
        print(f"📊 Chargement des cumulative deltas depuis {trade_file.name}...")
        cumdelta_df = load_cumdelta_from_trades(str(trade_file), symbol)
        
        if cumdelta_df.empty:
            print("⚠️ Aucune donnée cumulative delta trouvée")
            return 1
        
        print(f"✅ {len(cumdelta_df)} enregistrements cumulative delta chargés")
        print(f"📅 Période: {cumdelta_df['datetime_utc'].min()} → {cumdelta_df['datetime_utc'].max()}")
        print(f"🔄 Sessions: {', '.join(cumdelta_df['session_id'].unique())}")
        
        # Analyse par session
        session_analysis = analyze_cumdelta_sessions(cumdelta_df)
        print(f"\n📊 Analyse par session:")
        for session, stats in session_analysis.items():
            print(f"  {session}:")
            print(f"    - Records: {stats['count']}")
            print(f"    - Cum Delta Day: {stats['day_stats']['final']:.1f}")
            print(f"    - Cum Delta Session: {stats['session_stats']['final']:.1f}")
            print(f"    - Range Session: {stats['session_stats']['range']:.1f}")
        
        # Détection des resets
        reset_events = detect_reset_events(cumdelta_df)
        if reset_events:
            print(f"\n🔄 Événements de reset détectés: {len(reset_events)}")
            for event in reset_events[:5]:
                print(f"  - {event['type']} à {event['datetime']}")
                print(f"    Day: {event['cum_delta_day']:.1f}, Session: {event['cum_delta_session']:.1f}")
        
        # Charger les autres données
        print(f"\n📊 Chargement des autres données...")
        
        # BaseData
        basedata_file = data_dir / f"chart_{chart_id}_basedata_{ymd}_{symbol}.jsonl" if clean_dir.exists() else data_dir / f"chart_{chart_id}_basedata_{ymd}.jsonl"
        basedata_rows = _read_jsonl(basedata_file) if basedata_file.exists() else []
        print(f"   📈 BaseData: {len(basedata_rows)} enregistrements")
        
        # Quotes
        quote_file = data_dir / f"chart_{chart_id}_quote_{ymd}_{symbol}.jsonl" if clean_dir.exists() else data_dir / f"chart_{chart_id}_quote_{ymd}.jsonl"
        quote_rows = _read_jsonl(quote_file) if quote_file.exists() else []
        print(f"   💬 Quotes: {len(quote_rows)} enregistrements")
        
        # VWAP
        vwap_file = data_dir / f"chart_{chart_id}_vwap_{ymd}_{symbol}.jsonl" if clean_dir.exists() else data_dir / f"chart_{chart_id}_vwap_{ymd}.jsonl"
        vwap_rows = _read_jsonl(vwap_file) if vwap_file.exists() else []
        print(f"   📊 VWAP: {len(vwap_rows)} enregistrements")
        
        # NBCV
        nbcv_file = data_dir / f"chart_{chart_id}_nbcv_{ymd}_{symbol}.jsonl" if clean_dir.exists() else data_dir / f"chart_{chart_id}_nbcv_{ymd}.jsonl"
        nbcv_rows = _read_jsonl(nbcv_file) if nbcv_file.exists() else []
        print(f"   🔄 NBCV: {len(nbcv_rows)} enregistrements")
        
        # Créer le rapport de qualité enrichi
        quality_report = {
            "date": ymd,
            "chart_id": chart_id,
            "symbol": symbol,
            "data_sources": {
                "trades": len(cumdelta_df),
                "basedata": len(basedata_rows),
                "quotes": len(quote_rows),
                "vwap": len(vwap_rows),
                "nbcv": len(nbcv_rows)
            },
            "cumulative_delta_analysis": {
                "sessions": session_analysis,
                "reset_events": reset_events,
                "day_range": {
                    "min": cumdelta_df["cum_delta_day"].min(),
                    "max": cumdelta_df["cum_delta_day"].max(),
                    "final": cumdelta_df["cum_delta_day"].iloc[-1]
                },
                "session_range": {
                    "min": cumdelta_df["cum_delta_session"].min(),
                    "max": cumdelta_df["cum_delta_session"].max(),
                    "final": cumdelta_df["cum_delta_session"].iloc[-1]
                }
            },
            "quality_checks": {
                "cum_delta_day_consistency": "OK" if abs(cumdelta_df["cum_delta_day"].iloc[-1]) < 100000 else "WARN",
                "cum_delta_session_consistency": "OK" if abs(cumdelta_df["cum_delta_session"].iloc[-1]) < 50000 else "WARN",
                "session_transitions": len(reset_events),
                "data_completeness": "OK" if len(cumdelta_df) > 100 else "WARN"
            }
        }
        
        # Sauvegarder le rapport
        output_file = root / f"CHART_{chart_id}" / f"enhanced_quality_report_{symbol}_{ymd}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(quality_report, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n✅ Rapport de qualité enrichi sauvegardé: {output_file.name}")
        
        # Afficher le résumé final
        print(f"\n📊 RÉSUMÉ FINAL:")
        print(f"   📅 Date: {ymd}")
        print(f"   📈 Chart: {chart_id}")
        print(f"   🎯 Symbole: {symbol}")
        print(f"   📊 Trades: {len(cumdelta_df)}")
        print(f"   🔄 Sessions: {len(session_analysis)}")
        print(f"   🎯 Cum Delta Day final: {cumdelta_df['cum_delta_day'].iloc[-1]:.1f}")
        print(f"   🎯 Cum Delta Session final: {cumdelta_df['cum_delta_session'].iloc[-1]:.1f}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Erreur lors de l'unification: {e}")
        import traceback
        traceback.print_exc()
        return 1

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Unifier amélioré avec support du double Cumulative Delta")
    parser.add_argument("--root", required=True, help="Dossier racine de la journée (…/YYYYMMDD)")
    parser.add_argument("--date", required=True, help="YYYYMMDD")
    parser.add_argument("--chart", type=int, required=True, help="Numéro du chart (1, 2, 3, etc.)")
    parser.add_argument("--symbol", help="Symbole à filtrer (ex: ESZ25-CME)")
    
    args = parser.parse_args()
    
    root_path = Path(args.root)
    if not root_path.exists():
        print(f"❌ Dossier non trouvé: {root_path}")
        return 1
    
    return enhanced_unify_chart_day(root_path, args.date, args.chart, args.symbol)

if __name__ == "__main__":
    raise SystemExit(main())


