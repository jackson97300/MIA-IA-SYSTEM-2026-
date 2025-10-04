#!/usr/bin/env python3
"""
Module d'ingestion pour le double Cumulative Delta
Charge et traite les fichiers JSONL exportés par MIA_Dumper_G3_Unifier.cpp
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
from datetime import datetime, timezone

def load_cumdelta(path: str, symbol: str) -> pd.DataFrame:
    """
    Charge un fichier JSONL cum_delta exporté par MIA_Dumper_G3_Unifier.cpp
    et retourne un DataFrame filtré pour le symbole demandé.
    
    Args:
        path: Chemin vers le fichier JSONL
        symbol: Symbole à filtrer (ex: "ESZ25-CME", "NQZ25-CME")
    
    Returns:
        DataFrame avec colonnes: datetime_utc, sym, cum_delta_day, cum_delta_session, session_id
        
    Raises:
        ValueError: Si des champs requis sont manquants
        FileNotFoundError: Si le fichier n'existe pas
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Fichier non trouvé: {path}")
    
    # Charger JSONL
    df = pd.read_json(path, lines=True)
    
    if df.empty:
        return pd.DataFrame(columns=["datetime_utc", "sym", "cum_delta_day", "cum_delta_session", "session_id"])
    
    # Filtrer par symbole
    df = df[df["sym"] == symbol].copy()
    
    if df.empty:
        print(f"⚠️ Aucune donnée trouvée pour le symbole {symbol} dans {path}")
        return pd.DataFrame(columns=["datetime_utc", "sym", "cum_delta_day", "cum_delta_session", "session_id"])
    
    # Vérification des champs attendus
    expected = {"cum_delta_day", "cum_delta_session", "session_id"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Champs manquants dans {path}: {missing}")
    
    # Conversion horodatage en datetime UTC
    # Sierra Chart utilise des timestamps en jours depuis 1900-01-01
    df["datetime_utc"] = pd.to_datetime(df["t"], unit="D", origin="1899-12-30", utc=True)
    
    # Tri par timestamp
    df = df.sort_values("datetime_utc")
    
    # Sélection des colonnes d'intérêt
    result_columns = ["datetime_utc", "sym", "cum_delta_day", "cum_delta_session", "session_id"]
    return df[result_columns].copy()

def load_cumdelta_from_trades(path: str, symbol: str) -> pd.DataFrame:
    """
    Charge les cumulative deltas depuis un fichier de trades
    (alternative si pas de fichier dédié cumulative_delta)
    
    Args:
        path: Chemin vers le fichier de trades JSONL
        symbol: Symbole à filtrer
    
    Returns:
        DataFrame avec les cumulative deltas extraits des trades
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Fichier non trouvé: {path}")
    
    # Charger JSONL
    df = pd.read_json(path, lines=True)
    
    if df.empty:
        return pd.DataFrame(columns=["datetime_utc", "sym", "cum_delta_day", "cum_delta_session", "session_id"])
    
    # Filtrer par symbole et type trade
    df = df[(df["sym"] == symbol) & (df["type"] == "trade")].copy()
    
    if df.empty:
        print(f"⚠️ Aucun trade trouvé pour le symbole {symbol} dans {path}")
        return pd.DataFrame(columns=["datetime_utc", "sym", "cum_delta_day", "cum_delta_session", "session_id"])
    
    # Vérification des champs attendus
    expected = {"cum_delta_day", "cum_delta_session", "session_id"}
    missing = expected - set(df.columns)
    if missing:
        raise ValueError(f"Champs manquants dans {path}: {missing}")
    
    # Conversion horodatage
    df["datetime_utc"] = pd.to_datetime(df["t"], unit="D", origin="1899-12-30", utc=True)
    
    # Tri par timestamp
    df = df.sort_values("datetime_utc")
    
    # Sélection des colonnes d'intérêt
    result_columns = ["datetime_utc", "sym", "cum_delta_day", "cum_delta_session", "session_id"]
    return df[result_columns].copy()

def analyze_cumdelta_sessions(df: pd.DataFrame) -> Dict[str, Dict]:
    """
    Analyse les cumulative deltas par session
    
    Args:
        df: DataFrame avec les colonnes cum_delta_day, cum_delta_session, session_id
    
    Returns:
        Dictionnaire avec statistiques par session
    """
    if df.empty:
        return {}
    
    results = {}
    
    for session in df["session_id"].unique():
        session_data = df[df["session_id"] == session]
        
        if session_data.empty:
            continue
        
        # Statistiques pour cette session
        day_stats = {
            "min": session_data["cum_delta_day"].min(),
            "max": session_data["cum_delta_day"].max(),
            "final": session_data["cum_delta_day"].iloc[-1],
            "range": session_data["cum_delta_day"].max() - session_data["cum_delta_day"].min()
        }
        
        session_stats = {
            "min": session_data["cum_delta_session"].min(),
            "max": session_data["cum_delta_session"].max(),
            "final": session_data["cum_delta_session"].iloc[-1],
            "range": session_data["cum_delta_session"].max() - session_data["cum_delta_session"].min()
        }
        
        results[session] = {
            "count": len(session_data),
            "start_time": session_data["datetime_utc"].min(),
            "end_time": session_data["datetime_utc"].max(),
            "day_stats": day_stats,
            "session_stats": session_stats
        }
    
    return results

def detect_reset_events(df: pd.DataFrame) -> List[Dict]:
    """
    Détecte les événements de reset dans les cumulative deltas
    
    Args:
        df: DataFrame avec les colonnes cum_delta_day, cum_delta_session, session_id
    
    Returns:
        Liste des événements de reset détectés
    """
    if df.empty:
        return []
    
    reset_events = []
    
    # Détection des resets de session (cum_delta_session proche de 0)
    session_resets = df[df["cum_delta_session"].abs() < 100].copy()
    
    for idx, row in session_resets.iterrows():
        reset_events.append({
            "type": "session_reset",
            "datetime": row["datetime_utc"],
            "session_id": row["session_id"],
            "cum_delta_day": row["cum_delta_day"],
            "cum_delta_session": row["cum_delta_session"]
        })
    
    # Détection des resets de jour (cum_delta_day proche de 0)
    day_resets = df[df["cum_delta_day"].abs() < 100].copy()
    
    for idx, row in day_resets.iterrows():
        reset_events.append({
            "type": "day_reset",
            "datetime": row["datetime_utc"],
            "session_id": row["session_id"],
            "cum_delta_day": row["cum_delta_day"],
            "cum_delta_session": row["cum_delta_session"]
        })
    
    # Trier par datetime
    reset_events.sort(key=lambda x: x["datetime"])
    
    return reset_events

def export_cumdelta_summary(df: pd.DataFrame, output_path: str) -> None:
    """
    Exporte un résumé des cumulative deltas en JSON
    
    Args:
        df: DataFrame avec les cumulative deltas
        output_path: Chemin de sortie pour le fichier JSON
    """
    if df.empty:
        print("⚠️ DataFrame vide, aucun résumé à exporter")
        return
    
    # Analyse par session
    session_analysis = analyze_cumdelta_sessions(df)
    
    # Détection des resets
    reset_events = detect_reset_events(df)
    
    # Statistiques globales
    global_stats = {
        "total_records": len(df),
        "symbol": df["sym"].iloc[0] if not df.empty else None,
        "start_time": df["datetime_utc"].min().isoformat(),
        "end_time": df["datetime_utc"].max().isoformat(),
        "cum_delta_day_range": {
            "min": df["cum_delta_day"].min(),
            "max": df["cum_delta_day"].max(),
            "final": df["cum_delta_day"].iloc[-1]
        },
        "cum_delta_session_range": {
            "min": df["cum_delta_session"].min(),
            "max": df["cum_delta_session"].max(),
            "final": df["cum_delta_session"].iloc[-1]
        },
        "sessions": list(df["session_id"].unique()),
        "session_analysis": session_analysis,
        "reset_events": reset_events
    }
    
    # Export JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(global_stats, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"✅ Résumé exporté vers {output_path}")

def main():
    """Fonction principale pour tests et exemples"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Charger et analyser les cumulative deltas")
    parser.add_argument("--file", required=True, help="Fichier JSONL à analyser")
    parser.add_argument("--symbol", required=True, help="Symbole à filtrer (ex: ESZ25-CME)")
    parser.add_argument("--output", help="Fichier de sortie pour le résumé JSON")
    parser.add_argument("--from-trades", action="store_true", help="Charger depuis un fichier de trades")
    
    args = parser.parse_args()
    
    try:
        # Charger les données
        if args.from_trades:
            df = load_cumdelta_from_trades(args.file, args.symbol)
        else:
            df = load_cumdelta(args.file, args.symbol)
        
        if df.empty:
            print("❌ Aucune donnée trouvée")
            return 1
        
        print(f"📊 Données chargées: {len(df)} enregistrements")
        print(f"📅 Période: {df['datetime_utc'].min()} → {df['datetime_utc'].max()}")
        print(f"🔄 Sessions: {', '.join(df['session_id'].unique())}")
        
        # Afficher les dernières valeurs
        print(f"\n📈 Dernières valeurs:")
        print(df.tail(10).to_string(index=False))
        
        # Analyse par session
        session_analysis = analyze_cumdelta_sessions(df)
        print(f"\n📊 Analyse par session:")
        for session, stats in session_analysis.items():
            print(f"  {session}:")
            print(f"    - Records: {stats['count']}")
            print(f"    - Cum Delta Day: {stats['day_stats']['final']:.1f}")
            print(f"    - Cum Delta Session: {stats['session_stats']['final']:.1f}")
        
        # Détection des resets
        reset_events = detect_reset_events(df)
        if reset_events:
            print(f"\n🔄 Événements de reset détectés: {len(reset_events)}")
            for event in reset_events[:5]:  # Afficher les 5 premiers
                print(f"  - {event['type']} à {event['datetime']}: day={event['cum_delta_day']:.1f}, session={event['cum_delta_session']:.1f}")
        
        # Export du résumé si demandé
        if args.output:
            export_cumdelta_summary(df, args.output)
        
        return 0
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())


