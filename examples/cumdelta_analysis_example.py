#!/usr/bin/env python3
"""
Exemple d'utilisation du module load_cumdelta.py
Montre comment analyser les cumulative deltas avec les nouveaux champs
"""

import sys
from pathlib import Path

# Ajouter le dossier parent au path pour importer les modules
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from unifier.load_cumdelta import (
    load_cumdelta, 
    load_cumdelta_from_trades, 
    analyze_cumdelta_sessions, 
    detect_reset_events,
    export_cumdelta_summary
)

def example_analysis():
    """Exemple d'analyse des cumulative deltas"""
    
    print("🔍 EXEMPLE D'ANALYSE CUMULATIVE DELTA")
    print("=" * 50)
    
    # Exemple 1: Charger depuis un fichier de trades
    print("\n📊 Exemple 1: Chargement depuis fichier de trades")
    try:
        # Remplace par le chemin réel de ton fichier
        trades_file = "DATA_SIERRA_CHART/DATA_2025/SEPTEMBRE/20250924/CHART_1/chart_1_trade_ESZ25_CME_20250924.jsonl"
        
        if Path(trades_file).exists():
            df = load_cumdelta_from_trades(trades_file, "ESZ25-CME")
            
            if not df.empty:
                print(f"✅ {len(df)} enregistrements chargés")
                print(f"📅 Période: {df['datetime_utc'].min()} → {df['datetime_utc'].max()}")
                print(f"🔄 Sessions: {', '.join(df['session_id'].unique())}")
                
                # Afficher les dernières valeurs
                print(f"\n📈 Dernières valeurs:")
                print(df.tail(5).to_string(index=False))
                
                # Analyse par session
                session_analysis = analyze_cumdelta_sessions(df)
                print(f"\n📊 Analyse par session:")
                for session, stats in session_analysis.items():
                    print(f"  {session}:")
                    print(f"    - Records: {stats['count']}")
                    print(f"    - Cum Delta Day: {stats['day_stats']['final']:.1f}")
                    print(f"    - Cum Delta Session: {stats['session_stats']['final']:.1f}")
                    print(f"    - Range Session: {stats['session_stats']['range']:.1f}")
                
                # Détection des resets
                reset_events = detect_reset_events(df)
                if reset_events:
                    print(f"\n🔄 Événements de reset détectés: {len(reset_events)}")
                    for event in reset_events[:3]:
                        print(f"  - {event['type']} à {event['datetime']}")
                        print(f"    Day: {event['cum_delta_day']:.1f}, Session: {event['cum_delta_session']:.1f}")
                
                # Export du résumé
                output_file = "cumdelta_summary_ESZ25_20250924.json"
                export_cumdelta_summary(df, output_file)
                print(f"\n💾 Résumé exporté vers {output_file}")
                
            else:
                print("⚠️ Aucune donnée trouvée")
        else:
            print(f"⚠️ Fichier non trouvé: {trades_file}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Exemple 2: Charger depuis un fichier basedata
    print("\n📊 Exemple 2: Chargement depuis fichier basedata")
    try:
        basedata_file = "DATA_SIERRA_CHART/DATA_2025/SEPTEMBRE/20250924/CHART_1/chart_1_basedata_ESZ25_CME_20250924.jsonl"
        
        if Path(basedata_file).exists():
            df = load_cumdelta_from_trades(basedata_file, "ESZ25-CME")  # Même fonction car basedata a aussi les champs
            
            if not df.empty:
                print(f"✅ {len(df)} enregistrements basedata chargés")
                
                # Comparaison des cumulative deltas entre trades et basedata
                print(f"\n📈 Dernières valeurs basedata:")
                print(df.tail(3).to_string(index=False))
                
            else:
                print("⚠️ Aucune donnée basedata trouvée")
        else:
            print(f"⚠️ Fichier non trouvé: {basedata_file}")
            
    except Exception as e:
        print(f"❌ Erreur: {e}")

def example_session_analysis():
    """Exemple d'analyse par session"""
    
    print("\n🔄 ANALYSE PAR SESSION")
    print("=" * 30)
    
    # Simulation de données pour l'exemple
    import pandas as pd
    from datetime import datetime, timezone
    
    # Créer des données d'exemple
    sample_data = [
        {"datetime_utc": datetime(2025, 9, 24, 23, 0, 0, tzinfo=timezone.utc), "sym": "ESZ25-CME", "cum_delta_day": 0, "cum_delta_session": 0, "session_id": "Asia"},
        {"datetime_utc": datetime(2025, 9, 24, 23, 30, 0, tzinfo=timezone.utc), "sym": "ESZ25-CME", "cum_delta_day": 150, "cum_delta_session": 150, "session_id": "Asia"},
        {"datetime_utc": datetime(2025, 9, 25, 7, 0, 0, tzinfo=timezone.utc), "sym": "ESZ25-CME", "cum_delta_day": 200, "cum_delta_session": 0, "session_id": "London"},
        {"datetime_utc": datetime(2025, 9, 25, 7, 30, 0, tzinfo=timezone.utc), "sym": "ESZ25-CME", "cum_delta_day": 350, "cum_delta_session": 150, "session_id": "London"},
        {"datetime_utc": datetime(2025, 9, 25, 13, 30, 0, tzinfo=timezone.utc), "sym": "ESZ25-CME", "cum_delta_day": 400, "cum_delta_session": 0, "session_id": "US"},
        {"datetime_utc": datetime(2025, 9, 25, 14, 0, 0, tzinfo=timezone.utc), "sym": "ESZ25-CME", "cum_delta_day": 500, "cum_delta_session": 100, "session_id": "US"},
    ]
    
    df = pd.DataFrame(sample_data)
    
    print("📊 Données d'exemple:")
    print(df.to_string(index=False))
    
    # Analyse par session
    session_analysis = analyze_cumdelta_sessions(df)
    print(f"\n📈 Analyse par session:")
    for session, stats in session_analysis.items():
        print(f"  {session}:")
        print(f"    - Records: {stats['count']}")
        print(f"    - Cum Delta Day final: {stats['day_stats']['final']:.1f}")
        print(f"    - Cum Delta Session final: {stats['session_stats']['final']:.1f}")
        print(f"    - Range Session: {stats['session_stats']['range']:.1f}")
    
    # Détection des resets
    reset_events = detect_reset_events(df)
    print(f"\n🔄 Événements de reset détectés: {len(reset_events)}")
    for event in reset_events:
        print(f"  - {event['type']} à {event['datetime']}")
        print(f"    Session: {event['session_id']}")
        print(f"    Day: {event['cum_delta_day']:.1f}, Session: {event['cum_delta_session']:.1f}")

def main():
    """Fonction principale"""
    print("🚀 EXEMPLES D'UTILISATION LOAD_CUMDELTA")
    print("=" * 50)
    
    # Exemple avec données réelles (si disponibles)
    example_analysis()
    
    # Exemple avec données simulées
    example_session_analysis()
    
    print(f"\n✅ Exemples terminés!")
    print(f"\n💡 Pour utiliser avec tes propres données:")
    print(f"   python unifier/load_cumdelta.py --file ton_fichier.jsonl --symbol ESZ25-CME")

if __name__ == "__main__":
    main()


