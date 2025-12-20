"""
MIA_IA_SYSTEM - MenthorQ ES Bridge

Bridge ES avec MenthorQ (remplacement de Polygon.io)
- Interface compatible avec es_bias_bridge.py
- Utilise MenthorQ au lieu de Polygon.io
- Maintien de la compatibilité API

Version: ES Bridge Replacement
Performance: Compatible avec l'existant
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Assurer l'import du package racine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from features.menthorq_polygon_replacement import MenthorQPolygonReplacement
from features.menthorq_processor import MenthorQProcessor

def jprint(obj):
    """Print JSON sur stdout"""
    print(json.dumps(obj, ensure_ascii=False))
    sys.stdout.flush()

def dprint(msg):
    """Print debug sur stderr"""
    print(f"DEBUG: {msg}", file=sys.stderr)
    sys.stderr.flush()

async def run():
    """Fonction principale du bridge ES MenthorQ"""
    dprint("Démarrage du bridge ES MenthorQ...")
    
    try:
        # Créer le processeur MenthorQ
        menthorq_processor = MenthorQProcessor()
        dprint("Processeur MenthorQ créé")
        
        # Créer l'adaptateur de remplacement
        replacement = MenthorQPolygonReplacement(menthorq_processor)
        dprint("Adaptateur MenthorQ créé")
        
        # Simuler des données MenthorQ pour le test
        # En production, ces données viendront du fichier JSONL
        test_menthorq_data = {
            "gamma": {
                "Call Resistance": 5300.0,
                "Put Support": 5285.0,
                "HVL": 5292.0,
                "GEX 1": 5295.0,
                "GEX 2": 5305.0,
                "GEX 3": 5290.0
            },
            "blind_spots": {
                "BL 1": 5295.0,
                "BL 2": 5300.0,
                "BL 3": 5288.0
            },
            "swing": {
                "SG1": 5288.0,
                "SG2": 5302.0,
                "SG3": 5295.0
            },
            "stale": False,
            "last_update": datetime.now()
        }
        
        # Mettre à jour le cache MenthorQ
        menthorq_processor.levels_cache["ESZ5"] = test_menthorq_data
        dprint("Données MenthorQ simulées chargées")
        
        # Générer le snapshot avec timeout
        try:
            snap = await asyncio.wait_for(replacement.get_spx_snapshot_for_es(), timeout=20)
            dprint(f"Snapshot MenthorQ récupéré: {bool(snap)}")
        except asyncio.TimeoutError:
            dprint("Timeout génération snapshot MenthorQ")
            jprint({
                "ok": False,
                "status": "timeout",
                "error": "Timeout génération snapshot MenthorQ",
                "ts": datetime.utcnow().isoformat()
            })
            return 2
        except Exception as e:
            dprint(f"Exception pendant get_spx_snapshot_for_es(): {e}")
            jprint({
                "ok": False,
                "status": "error",
                "error": str(e),
                "ts": datetime.utcnow().isoformat()
            })
            return 2
        
        # Vérifier le snapshot
        if not snap or snap.get("status") == "empty":
            dprint("Snapshot vide ou status=empty")
            jprint({
                "ok": False,
                "status": snap.get("status") if snap else "error",
                "error": "Snapshot MenthorQ vide",
                "ts": datetime.utcnow().isoformat()
            })
            return 1
        
        # Vérifier la qualité des données
        quality = snap.get("quality", {})
        if quality.get("score", 0) < 0.5:
            dprint(f"Qualité des données faible: {quality.get('score', 0)}")
            jprint({
                "ok": False,
                "status": "low_quality",
                "error": f"Qualité des données MenthorQ faible: {quality.get('score', 0)}",
                "ts": datetime.utcnow().isoformat()
            })
            return 1
        
        # Snapshot valide - l'envoyer
        dprint(f"Envoi snapshot MenthorQ: {snap['status']}")
        jprint(snap)
        return 0
        
    except Exception as e:
        dprint(f"Erreur critique bridge ES MenthorQ: {e}")
        jprint({
            "ok": False,
            "status": "critical_error",
            "error": str(e),
            "ts": datetime.utcnow().isoformat()
        })
        return 3

def main():
    """Point d'entrée principal"""
    try:
        exit_code = asyncio.run(run())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        dprint("Interruption utilisateur")
        sys.exit(130)
    except Exception as e:
        dprint(f"Erreur fatale: {e}")
        jprint({
            "ok": False,
            "status": "fatal_error",
            "error": str(e),
            "ts": datetime.utcnow().isoformat()
        })
        sys.exit(1)

if __name__ == "__main__":
    main()
