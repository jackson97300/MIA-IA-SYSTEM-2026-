#!/usr/bin/env python3
"""
🧪 TEST ORDRE SIMPLE - MIA Trading Bot
========================================
Script pour tester le passage d'ordres avec SL/TP

Usage:
    python LAUNCH/test_ordre_simple.py

Actions:
    1. Place un ordre MARKET proche du prix
    2. Affiche les ordres créés (Entry + SL + TP)
    3. Option pour annuler tout (flatten_all)
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Ajouter le path racine
sys.path.insert(0, str(Path(__file__).parent.parent))

from execution.sierra_dtc_connector import SierraDTCConnector, DTCConfig, OrderRequest

# Config - MODIFIABLE PAR ARGUMENTS
# Usage: python test_ordre_simple.py ES SHORT 6836.50
SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "ES"
DIRECTION = sys.argv[2] if len(sys.argv) > 2 else "SHORT"
PRICE = float(sys.argv[3]) if len(sys.argv) > 3 else None
QUANTITY = 1


async def get_current_price(symbol: str) -> float:
    """Récupère le prix actuel depuis argument ou ML Ready"""
    # Si prix fourni en argument, l'utiliser
    if PRICE:
        print(f"   📊 Prix depuis argument: {PRICE:.2f}")
        return PRICE

    try:
        # Essayer de lire depuis les fichiers ML_READY
        from features.ml_ready_reader import MLReadyReader

        config = {
            "live_mode": {
                "realtime": {
                    "watch_dirs": [
                        "D:/MIA_IA_system/DATA_SIERRA_CHART/CHART_3",  # ES
                        "D:/MIA_IA_system/DATA_SIERRA_CHART/CHART_9",  # NQ
                    ]
                },
                "chart_mapping": {"ES": 3, "NQ": 9}
            }
        }

        reader = MLReadyReader(config)
        snapshot = reader.get_live_snapshot(symbol)

        if snapshot:
            mid = snapshot.get('mid', 0)
            bid = snapshot.get('best_bid', snapshot.get('dom_bid1', 0))
            ask = snapshot.get('best_ask', snapshot.get('dom_ask1', 0))
            print(f"   📊 Mid: {mid:.2f} | Bid: {bid:.2f} | Ask: {ask:.2f}")
            return mid

    except Exception as e:
        print(f"   ⚠️ Lecture auto échouée: {e}")

    print(f"   ❌ Prix non fourni! Usage: python test_ordre_simple.py ES SHORT 6836.50")
    return 0


async def test_ordre():
    """Test principal"""
    print("=" * 60)
    print("🧪 TEST ORDRE SIMPLE - MIA Trading Bot")
    print("=" * 60)
    print(f"   Symbol: {SYMBOL}")
    print(f"   Direction: {DIRECTION}")
    print(f"   Quantity: {QUANTITY}")
    print("=" * 60)

    # 1. Récupérer prix actuel
    print("\n📊 1. Récupération du prix actuel...")
    mid_price = await get_current_price(SYMBOL)

    if mid_price == 0:
        print("❌ Impossible de récupérer le prix!")
        return

    # 2. Calculer SL/TP
    tick_size = 0.25 if SYMBOL in ['ES', 'NQ'] else 0.10
    sl_ticks = 12  # 3 pts
    tp_ticks = 16  # 4 pts

    if DIRECTION == "LONG":
        entry_price = mid_price  # Market order
        stop_loss = mid_price - (sl_ticks * tick_size)
        take_profit = mid_price + (tp_ticks * tick_size)
    else:  # SHORT
        entry_price = mid_price
        stop_loss = mid_price + (sl_ticks * tick_size)
        take_profit = mid_price - (tp_ticks * tick_size)

    print(f"\n📐 2. Calcul SL/TP:")
    print(f"   Entry: {entry_price:.2f} (MARKET)")
    print(f"   SL: {stop_loss:.2f} ({sl_ticks} ticks)")
    print(f"   TP: {take_profit:.2f} ({tp_ticks} ticks)")

    # 3. Connexion DTC
    print(f"\n🔌 3. Connexion DTC...")
    config = DTCConfig(
        es_port=11099,
        nq_port=11099,
        host="127.0.0.1"
    )
    connector = SierraDTCConnector(config)

    connected = await connector.ensure_connected(SYMBOL)
    if not connected:
        print("❌ Échec connexion DTC!")
        return

    print(f"   ✅ Connecté (paper_mode: {connector.paper_mode})")

    # 4. Confirmation auto (pas d'input en mode non-interactif)
    print("\n" + "=" * 60)
    print("🚀 EXÉCUTION AUTOMATIQUE")
    print("=" * 60)
    print(f"   Ordre {DIRECTION} {SYMBOL} @ MARKET")
    print(f"   SL: {stop_loss:.2f} | TP: {take_profit:.2f}")
    print("")

    # 5. Placer l'ordre avec PRIX ABSOLUS (pas offsets!)
    print(f"\n📤 4. Envoi ordre avec place_parent_then_children (PRIX ABSOLUS)...")

    side = "BUY" if DIRECTION == "LONG" else "SELL"

    # Utiliser PRIX ABSOLUS au lieu d'offsets
    result = await connector.place_parent_then_children(
        symbol=SYMBOL,
        side=side,
        qty=QUANTITY,
        entry_kind="MKT",  # Market order
        tp_price=take_profit,   # Prix absolu!
        sl_price=stop_loss,     # Prix absolu!
        use_offsets=False,      # PAS d'offsets!
        client_tag="TEST"
    )

    print(f"\n📋 5. Résultat:")
    print(f"   {result}")

    if result.get("ok"):
        print("\n✅ ORDRE ENVOYÉ!")
        print(f"   Parent: {result.get('parent')}")
        print(f"   TP: {result.get('tp_cid')} @ {take_profit}")
        print(f"   SL: {result.get('sl_cid')} @ {stop_loss}")
        print(f"   Account: {result.get('trade_account')}")
    else:
        print(f"\n❌ ERREUR: {result.get('error')}")

    # 6. Attendre 30 secondes pour voir les ordres
    print("\n" + "=" * 60)
    print("⏳ Attente 30 secondes... VÉRIFIE LES ORDRES SUR SIERRA CHART!")
    print("=" * 60)

    for i in range(30, 0, -5):
        print(f"   ⏳ {i} secondes restantes...")
        await asyncio.sleep(5)

    # Proposer flatten
    print("\n🧹 FLATTEN_ALL dans 5 secondes...")
    await asyncio.sleep(5)

    print("🧹 Exécution FLATTEN_ALL...")
    success = await connector.flatten_all(SYMBOL)
    print(f"   Résultat: {'✅ OK' if success else '❌ ÉCHEC'}")

    # Déconnexion
    await connector.disconnect()
    print("\n👋 Test terminé!")


if __name__ == "__main__":
    asyncio.run(test_ordre())
