#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de nettoyage FLATTEN_ALL pour tous les comptes Sierra Chart

Date: 14 Nov 2025
But: Supprimer tous les ordres et positions avant de lancer les tests
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from execution.sierra_dtc_connector import create_sierra_dtc_connector


async def cleanup_all():
    """Nettoie TOUS les comptes configurés"""
    print("\n" + "="*80)
    print("🧹 NETTOYAGE COMPLET - FLATTEN_ALL pour tous les comptes")
    print("="*80)

    # Créer connecteur
    connector = create_sierra_dtc_connector(
        trade_account_map={"ES": "Sim1", "NQ": "Sim2", "RTY": "Sim3"}
    )

    accounts_to_clean = [
        ("ESZ25-CME", "Sim1"),
        ("NQZ25-CME", "Sim2"),
        # ("RTYZ25-CME", "Sim3"),  # RTY pas configuré pour l'instant
    ]

    print("\n🎯 Comptes à nettoyer:")
    for symbol, account in accounts_to_clean:
        print(f"   • {account} ({symbol})")

    print("\n🔥 Envoi des commandes FLATTEN_ALL...\n")

    for symbol, account in accounts_to_clean:
        try:
            await connector.ensure_connected(symbol)
            await connector._cancel_order_only(symbol, "CLEANUP", f"Nettoyage manuel {account}")
            print(f"✅ {account} nettoyé")
        except Exception as e:
            print(f"❌ {account}: {e}")

    print("\n⏳ Attente 2s pour laisser Sierra Chart traiter...")
    await asyncio.sleep(2)

    # Déconnexion propre
    await connector.disconnect()

    print("\n" + "="*80)
    print("✅ NETTOYAGE TERMINÉ")
    print("="*80)
    print("\n💡 Vous pouvez maintenant lancer vos tests:")
    print("   python EXECUTION\\test_es_nq_rty_auto_prices.py")
    print()


if __name__ == "__main__":
    asyncio.run(cleanup_all())
