# -*- coding: utf-8 -*-
"""
Bridge ES robuste:
- Timeout dur sur l'appel snapshot
- Imprime toujours une sortie JSON (stdout)
- Logs DEBUG sur stderr
"""
import asyncio
import json
import sys
import os
from datetime import datetime

# Assurer l'import du package racine
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data.polygon_spx_adapter import PolygonSPXAdapter

def jprint(obj):
    print(json.dumps(obj, ensure_ascii=False))
    sys.stdout.flush()

def dprint(msg):
    print(f"DEBUG: {msg}", file=sys.stderr)
    sys.stderr.flush()

async def run():
    dprint("Démarrage du bridge ES...")
    adapter = PolygonSPXAdapter()
    dprint("Adaptateur créé")

    try:
        # Timeout dur (ajuste 10→20s si besoin)
        snap = await asyncio.wait_for(adapter.get_spx_snapshot_for_es(), timeout=20)
        dprint(f"Snapshot récupéré: {bool(snap)}")
    except Exception as e:
        dprint(f"Exception pendant get_spx_snapshot_for_es(): {e}")
        jprint({
            "ok": False,
            "status": "error",
            "error": str(e),
            "ts": datetime.utcnow().isoformat()
        })
        return 2

    if not snap or snap.get("status") == "empty":
        dprint("Snapshot vide ou status=empty")
        jprint({
            "ok": False,
            "status": snap.get("status") if snap else "error",
            "error": "empty_or_error",
            "ts": datetime.utcnow().isoformat()
        })
        return 2

    bias = snap.get("dealers_bias", {})
    out = {
        "ok": True,
        "status": snap.get("status", "ok"),
        "direction": bias.get("direction"),
        "strength": bias.get("strength"),
        "score": bias.get("score"),
        "underlying_price": snap.get("underlying_price"),
        "meta": snap.get("meta", {}),
        "data_delay": "15min",  # Marquer comme DELAYED
        "live_trigger": False,  # Non-déclencheur en live
        "ts": datetime.utcnow().isoformat(),
    }
    dprint("Sortie JSON préparée")
    jprint(out)
    return 0

if __name__ == "__main__":
    try:
        dprint("Main start")
        code = asyncio.run(run())
        dprint(f"Exit code: {code}")
        sys.exit(code)
    except Exception as e:
        dprint(f"Exception main: {e}")
        jprint({"ok": False, "status": "error", "error": str(e)})
        sys.exit(2)
