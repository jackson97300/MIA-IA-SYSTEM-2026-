#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EMERGENCY FLATTEN - Ferme toutes les positions ouvertes
Date: 13 Nov 2025
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from execution.sierra_dtc_connector import create_sierra_dtc_connector


async def emergency_flatten_all():
    """Ferme toutes les positions sur ES, NQ, RTY"""
    print("🚨 EMERGENCY FLATTEN - Fermeture de toutes les positions")
    print("=" * 70)

    connector = create_sierra_dtc_connector(
        trade_account_map={
            "ES": "Sim1",
            "NQ": "Sim2",
            "RTY": "Sim3"
        }
    )

    markets = ["ESZ25-CME", "NQZ25-CME", "RTYZ25-CME"]

    for symbol in markets:
        try:
            print(f"\n🔍 Vérification {symbol}...")
            # Tenter de flatten (même si pas de position)
            await connector.flatten_position(symbol)
            print(f"✅ {symbol} flatten envoyé")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"⚠️ {symbol}: {e}")

    print("\n" + "=" * 70)
    print("✅ Commandes flatten envoyées sur tous les marchés")
    print("🔍 Vérifiez dans Sierra Chart que les positions sont fermées")

    await asyncio.sleep(2)
    await connector.disconnect()


if __name__ == "__main__":
    asyncio.run(emergency_flatten_all())
