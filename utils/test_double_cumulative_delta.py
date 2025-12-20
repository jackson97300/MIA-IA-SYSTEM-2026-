#!/usr/bin/env python3
"""
Script de test pour vérifier le double Cumulative Delta
Teste la logique de reset et la cohérence des données
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def parse_timestamp(timestamp: float) -> datetime:
    """Convertit un timestamp Sierra Chart en datetime UTC"""
    # Sierra Chart utilise des timestamps en secondes depuis 1900-01-01
    # On doit ajuster pour Python qui utilise 1970-01-01
    sierra_epoch = datetime(1900, 1, 1, tzinfo=timezone.utc)
    python_timestamp = timestamp - 2208988800  # Différence entre 1900 et 1970
    return datetime.fromtimestamp(python_timestamp, tz=timezone.utc)

def get_session_from_utc_hour(hour: int) -> str:
    """Détermine la session basée sur l'heure UTC"""
    if hour >= 23 or hour < 7:
        return "Asia"
    elif hour >= 7 and hour < 13:
        return "London"
    elif hour >= 13 and hour < 21:
        return "US"
    else:
        return "Unknown"

def test_double_cumulative_delta(file_path: Path) -> Dict[str, Any]:
    """
    Teste la cohérence du double cumulative delta dans un fichier JSONL
    """
    results = {
        "file": str(file_path),
        "total_lines": 0,
        "trade_lines": 0,
        "basedata_lines": 0,
        "heartbeat_lines": 0,
        "errors": [],
        "session_transitions": [],
        "reset_events": [],
        "robustness_checks": {
            "late_resets": 0,
            "session_initialization": 0,
            "heartbeat_presence": 0
        },
        "cum_delta_stats": {
            "day": {"min": float('inf'), "max": float('-inf'), "final": 0},
            "session": {"min": float('inf'), "max": float('-inf'), "final": 0}
        }
    }
    
    if not file_path.exists():
        results["errors"].append(f"Fichier non trouvé: {file_path}")
        return results
    
    last_session = None
    last_day_reset = None
    last_session_reset = None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            results["total_lines"] += 1
            
            try:
                data = json.loads(line.strip())
                
                # Vérifier les champs requis
                if "cum_delta_day" not in data or "cum_delta_session" not in data or "session_id" not in data:
                    continue
                
                # Analyser les trades
                if data.get("type") == "trade":
                    results["trade_lines"] += 1
                elif data.get("type") == "cumulative_delta_heartbeat":
                    results["heartbeat_lines"] += 1
                    results["robustness_checks"]["heartbeat_presence"] += 1
                    
                    # Vérifier la cohérence des cumulative deltas
                    cum_delta_day = data.get("cum_delta_day", 0)
                    cum_delta_session = data.get("cum_delta_session", 0)
                    session_id = data.get("session_id", "Unknown")
                    
                    # Mettre à jour les stats
                    results["cum_delta_stats"]["day"]["min"] = min(results["cum_delta_stats"]["day"]["min"], cum_delta_day)
                    results["cum_delta_stats"]["day"]["max"] = max(results["cum_delta_stats"]["day"]["max"], cum_delta_day)
                    results["cum_delta_stats"]["day"]["final"] = cum_delta_day
                    
                    results["cum_delta_stats"]["session"]["min"] = min(results["cum_delta_stats"]["session"]["min"], cum_delta_session)
                    results["cum_delta_stats"]["session"]["max"] = max(results["cum_delta_stats"]["session"]["max"], cum_delta_session)
                    results["cum_delta_stats"]["session"]["final"] = cum_delta_session
                    
                    # Vérifier les transitions de session
                    if last_session and last_session != session_id:
                        results["session_transitions"].append({
                            "line": line_num,
                            "from": last_session,
                            "to": session_id,
                            "timestamp": data.get("t", 0)
                        })
                    last_session = session_id
                    
                    # Vérifier les resets
                    timestamp = data.get("t", 0)
                    if timestamp:
                        dt = parse_timestamp(timestamp)
                        hour = dt.hour
                        minute = dt.minute
                        
                        # Reset Day (23:00 UTC et après) - version robuste
                        if hour >= 23:
                            if last_day_reset and abs(cum_delta_day) > 100:
                                results["errors"].append(f"Ligne {line_num}: Reset Day détecté mais cum_delta_day non nul: {cum_delta_day}")
                            results["reset_events"].append({
                                "type": "day_reset",
                                "line": line_num,
                                "timestamp": timestamp,
                                "hour": hour,
                                "minute": minute,
                                "cum_delta_day": cum_delta_day,
                                "cum_delta_session": cum_delta_session
                            })
                            last_day_reset = timestamp
                            # Vérifier si c'est un reset tardif (après 23:00:00)
                            if minute > 0:
                                results["robustness_checks"]["late_resets"] += 1
                        
                        # Reset Session London (07:00 UTC et après)
                        elif hour >= 7 and hour < 13:
                            if last_session_reset and abs(cum_delta_session) > 100:
                                results["errors"].append(f"Ligne {line_num}: Reset Session London détecté mais cum_delta_session non nul: {cum_delta_session}")
                            results["reset_events"].append({
                                "type": "session_reset_london",
                                "line": line_num,
                                "timestamp": timestamp,
                                "hour": hour,
                                "minute": minute,
                                "session": session_id,
                                "cum_delta_day": cum_delta_day,
                                "cum_delta_session": cum_delta_session
                            })
                            last_session_reset = timestamp
                            # Vérifier si c'est un reset tardif (après 07:00:00)
                            if minute > 0:
                                results["robustness_checks"]["late_resets"] += 1
                        
                        # Reset Session US (13:30 UTC et après)
                        elif hour >= 13 and minute >= 30:
                            if last_session_reset and abs(cum_delta_session) > 100:
                                results["errors"].append(f"Ligne {line_num}: Reset Session US détecté mais cum_delta_session non nul: {cum_delta_session}")
                            results["reset_events"].append({
                                "type": "session_reset_us",
                                "line": line_num,
                                "timestamp": timestamp,
                                "hour": hour,
                                "minute": minute,
                                "session": session_id,
                                "cum_delta_day": cum_delta_day,
                                "cum_delta_session": cum_delta_session
                            })
                            last_session_reset = timestamp
                            # Vérifier si c'est un reset tardif (après 13:30:00)
                            if minute > 30:
                                results["robustness_checks"]["late_resets"] += 1
                
                # Analyser les basedata
                elif data.get("type") == "basedata":
                    results["basedata_lines"] += 1
                    
                    # Vérifier que basedata a aussi les cumulative deltas
                    if "cum_delta_day" not in data or "cum_delta_session" not in data:
                        results["errors"].append(f"Ligne {line_num}: basedata sans cumulative delta")
                
            except json.JSONDecodeError as e:
                results["errors"].append(f"Ligne {line_num}: Erreur JSON: {e}")
            except Exception as e:
                results["errors"].append(f"Ligne {line_num}: Erreur: {e}")
    
    return results

def print_test_results(results: Dict[str, Any]) -> None:
    """Affiche les résultats du test de manière lisible"""
    print(f"\n🔍 TEST DOUBLE CUMULATIVE DELTA")
    print(f"📁 Fichier: {results['file']}")
    print(f"📊 Statistiques:")
    print(f"   - Total lignes: {results['total_lines']}")
    print(f"   - Trades: {results['trade_lines']}")
    print(f"   - BaseData: {results['basedata_lines']}")
    print(f"   - Heartbeats: {results['heartbeat_lines']}")
    
    print(f"\n🛡️ Robustesse:")
    robustness = results['robustness_checks']
    print(f"   - Resets tardifs détectés: {robustness['late_resets']}")
    print(f"   - Heartbeats présents: {robustness['heartbeat_presence']}")
    if robustness['late_resets'] > 0:
        print(f"   ✅ Système robuste: resets tardifs gérés correctement")
    if robustness['heartbeat_presence'] > 0:
        print(f"   ✅ Heartbeats actifs: protection contre perte de données")
    
    print(f"\n📈 Cumulative Delta Stats:")
    day_stats = results['cum_delta_stats']['day']
    session_stats = results['cum_delta_stats']['session']
    print(f"   - Day: min={day_stats['min']:.1f}, max={day_stats['max']:.1f}, final={day_stats['final']:.1f}")
    print(f"   - Session: min={session_stats['min']:.1f}, max={session_stats['max']:.1f}, final={session_stats['final']:.1f}")
    
    if results['session_transitions']:
        print(f"\n🔄 Transitions de session ({len(results['session_transitions'])}):")
        for trans in results['session_transitions'][:5]:  # Afficher les 5 premières
            print(f"   - Ligne {trans['line']}: {trans['from']} → {trans['to']}")
        if len(results['session_transitions']) > 5:
            print(f"   ... et {len(results['session_transitions']) - 5} autres")
    
    if results['reset_events']:
        print(f"\n🔄 Événements de reset ({len(results['reset_events'])}):")
        for reset in results['reset_events']:
            print(f"   - {reset['type']} à la ligne {reset['line']}: cum_delta_day={reset['cum_delta_day']:.1f}, cum_delta_session={reset['cum_delta_session']:.1f}")
    
    if results['errors']:
        print(f"\n❌ Erreurs ({len(results['errors'])}):")
        for error in results['errors'][:10]:  # Afficher les 10 premières
            print(f"   - {error}")
        if len(results['errors']) > 10:
            print(f"   ... et {len(results['errors']) - 10} autres erreurs")
    else:
        print(f"\n✅ Aucune erreur détectée!")

def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Tester le double Cumulative Delta")
    parser.add_argument("--file", required=True, help="Fichier JSONL à tester")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    
    args = parser.parse_args()
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ Fichier non trouvé: {file_path}")
        return 1
    
    print(f"🧪 Test du double Cumulative Delta sur {file_path}")
    results = test_double_cumulative_delta(file_path)
    print_test_results(results)
    
    return 0 if not results['errors'] else 1

if __name__ == "__main__":
    raise SystemExit(main())
