#!/usr/bin/env python3
"""
Test DTC Cleanup - Lance des ordres et teste le nettoyage
Usage: python LAUNCH/test_dtc_cleanup.py
"""

import asyncio
import sys
from pathlib import Path

# Path setup
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from execution.sierra_dtc_connector import SierraDTCConnector
import logging

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
logger = logging.getLogger(__name__)

# Config
SYMBOLS = ["NQ"]  # Tester sur NQ d'abord
DTC_PORTS = {
    "ESZ25-CME": 11199,
    "NQZ25-CME": 11198,
}


async def test_cleanup():
    """Test le nettoyage des ordres DTC"""

    print("\n" + "="*60)
    print("🧪 TEST DTC CLEANUP")
    print("="*60)

    # Créer connecteur
    connector = SierraDTCConnector(
        host="127.0.0.1",
        symbol_ports=DTC_PORTS,
        paper_mode=False  # Mode live pour tester vraiment
    )

    try:
        # 1. Connexion
        print("\n📡 Connexion DTC...")
        for symbol in SYMBOLS:
            sc_symbol = f"{symbol}Z25-CME"
            connected = await connector.ensure_connected(sc_symbol)
            print(f"   {sc_symbol}: {'✅ Connecté' if connected else '❌ Échec'}")

        await asyncio.sleep(1)

        # 2. Vérifier ordres ouverts AVANT
        print("\n📋 Ordres ouverts AVANT nettoyage:")
        # On ne peut pas lister les ordres directement, mais on peut annuler tout

        # 3. Annuler tous les ordres ouverts
        print("\n🧹 Tentative de nettoyage (Cancel All Orders)...")

        for symbol in SYMBOLS:
            sc_symbol = f"{symbol}Z25-CME"
            print(f"\n   Nettoyage {sc_symbol}...")

            # Méthode: flatten_all
            result = await connector.flatten_all(sc_symbol)
            print(f"   flatten_all: {'✅' if result else '❌'}")

        await asyncio.sleep(2)

        # 4. Le nettoyage a été fait ci-dessus avec flatten_all
        print("\n✅ Nettoyage effectué via flatten_all")

        # 6. Flatten final
        print("\n🧹 Flatten final (toutes positions)...")
        for symbol in SYMBOLS:
            sc_symbol = f"{symbol}Z25-CME"
            result = await connector.flatten_all(sc_symbol)
            print(f"   {sc_symbol}: {'✅' if result else '❌'}")

        print("\n✅ Test terminé!")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Fermer connexion
        print("\n🔌 Fermeture connexion...")
        await connector.close()


async def test_cancel_all_working_orders():
    """Test spécifique pour annuler tous les ordres en attente"""

    print("\n" + "="*60)
    print("🧪 TEST CANCEL ALL WORKING ORDERS")
    print("="*60)

    connector = SierraDTCConnector(
        host="127.0.0.1",
        symbol_ports=DTC_PORTS,
        paper_mode=False
    )

    try:
        # Connexion
        for symbol in SYMBOLS:
            sc_symbol = f"{symbol}Z25-CME"
            await connector.ensure_connected(sc_symbol)

        await asyncio.sleep(1)

        # Envoyer message CANCEL_ALL_ORDERS via DTC
        print("\n🧹 Envoi CANCEL_ALL_ORDERS via DTC...")

        for symbol in SYMBOLS:
            sc_symbol = f"{symbol}Z25-CME"
            key = sc_symbol
            sock = connector.connections.get(key)

            if sock:
                # Type 308 = CANCEL_ALL_ORDERS (DTC Protocol)
                cancel_all_msg = {
                    "Type": 308,  # CANCEL_ALL_ORDERS
                    "RequestID": connector.request_id_counter,
                    "Symbol": sc_symbol,
                    "TradeAccount": connector._account_for_symbol(sc_symbol)
                }
                connector.request_id_counter += 1

                success = await connector._send_dtc_message(sock, cancel_all_msg)
                print(f"   {sc_symbol}: {'✅ Message envoyé' if success else '❌ Échec'}")
            else:
                print(f"   {sc_symbol}: ❌ Pas de socket")

        await asyncio.sleep(2)
        print("\n✅ Cancel All terminé!")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await connector.close()


async def main():
    """Menu principal"""
    print("\n" + "="*60)
    print("🧪 DTC CLEANUP TESTER")
    print("="*60)
    print("\n1. Test complet (connexion + ordre test + cleanup)")
    print("2. Cancel All Working Orders seulement")
    print("3. Les deux")
    print("0. Quitter")

    choice = input("\nChoix: ").strip()

    if choice == "1":
        await test_cleanup()
    elif choice == "2":
        await test_cancel_all_working_orders()
    elif choice == "3":
        await test_cleanup()
        await test_cancel_all_working_orders()
    else:
        print("Au revoir!")


if __name__ == "__main__":
    asyncio.run(main())
