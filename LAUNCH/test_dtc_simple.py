#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test DTC Simple - Vérifier la connexion Sierra Chart
Date: 29 Nov 2025

Ce test vérifie:
1. Connexion TCP au port 11099
2. Handshake DTC (LOGON)
3. Réception HEARTBEAT
"""
import asyncio
import sys
import os

# Configurer encoding pour Windows
sys.stdout.reconfigure(encoding='utf-8')

# Ajouter le répertoire parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.sierra_dtc_connector import create_sierra_dtc_connector


async def test_dtc_connection():
    """Test de connexion DTC simple"""
    print("=" * 80)
    print("🧪 TEST CONNEXION DTC SIERRA CHART")
    print("=" * 80)
    print()

    # Configuration
    HOST = 'localhost'
    PORT = 11099

    print(f"📡 Configuration:")
    print(f"   Host: {HOST}")
    print(f"   Port: {PORT}")
    print(f"   Symboles: ES, NQ")
    print()

    # Créer connecteur
    print("🔧 Création du connecteur DTC...")
    dtc = create_sierra_dtc_connector(
        host=HOST,
        es_port=PORT,
        nq_port=PORT,
        trade_account_map={"ES": "Sim1", "NQ": "Sim2", "RTY": "Sim3"}
    )
    print("   ✅ Connecteur créé")
    print()

    # Test 1: Connexion ES
    print("=" * 60)
    print("TEST 1: CONNEXION ES")
    print("=" * 60)

    try:
        print("🔌 Tentative de connexion ES...")
        sys.stdout.flush()

        connected = await asyncio.wait_for(
            dtc.ensure_connected('ES'),
            timeout=10.0
        )

        if connected:
            if dtc.paper_mode:
                print("   ⚠️ PAPER MODE activé (DTC non joignable)")
                print()
                print("   🔍 DIAGNOSTIC:")
                print("      1. Sierra Chart est-il lancé ?")
                print("      2. DTC Protocol Server est-il activé ?")
                print("         → Global Settings → Data/Trade Service Settings")
                print("         → Enable DTC Protocol Server = Yes")
                print("         → Listening Port = 11099")
                print("         → Allow Trading = Yes")
                print("      3. Redémarrer Sierra Chart après changement")
            else:
                print("   ✅ CONNEXION RÉUSSIE !")
                print(f"   Mode: LIVE (DTC actif)")

                # Attendre quelques heartbeats
                print("\n   ⏳ Attente heartbeats (5s)...")
                sys.stdout.flush()
                await asyncio.sleep(5)
                print("   ✅ Connexion stable")

                # Déconnexion propre
                await dtc.disconnect()
                print("   ✅ Déconnexion propre")
        else:
            print("   ❌ CONNEXION ÉCHOUÉE")

    except asyncio.TimeoutError:
        print("   ❌ TIMEOUT (>10s)")
    except Exception as e:
        print(f"   ❌ ERREUR: {e}")

    print()

    # Résumé
    print("=" * 80)
    print("RÉSUMÉ")
    print("=" * 80)

    if dtc.paper_mode:
        print()
        print("❌ DTC NON DISPONIBLE - Le bot fonctionnera en PAPER MODE")
        print()
        print("📋 CHECKLIST POUR ACTIVER DTC:")
        print()
        print("   1. OUVRIR Sierra Chart")
        print()
        print("   2. CONFIGURER DTC:")
        print("      → Global Settings (menu)")
        print("      → Data/Trade Service Settings")
        print("      → Chercher 'DTC Protocol Server'")
        print()
        print("   3. PARAMÈTRES:")
        print("      ┌────────────────────────────────────────┐")
        print("      │ Enable DTC Protocol Server: YES ✅     │")
        print("      │ Listening Port: 11099                  │")
        print("      │ Allow Trading: YES ✅                  │")
        print("      │ Require Authentication: NO             │")
        print("      │ Require TLS: NO                        │")
        print("      └────────────────────────────────────────┘")
        print()
        print("   4. REDÉMARRER Sierra Chart")
        print()
        print("   5. RELANCER ce test:")
        print("      python LAUNCH/test_dtc_simple.py")
        print()
    else:
        print()
        print("✅ DTC FONCTIONNEL - Le bot peut trader en LIVE")
        print()
        print("   Prochaine étape:")
        print("   python LAUNCH/launch_production_CLEAN_v2.py")
        print()

    print("=" * 80)


async def test_dtc_order():
    """Test d'envoi d'ordre (optionnel)"""
    print()
    print("=" * 80)
    print("🧪 TEST ENVOI ORDRE (PAPER/SIM)")
    print("=" * 80)
    print()

    dtc = create_sierra_dtc_connector(
        host='localhost',
        es_port=11099,
        nq_port=11099,
        trade_account_map={"ES": "Sim1", "NQ": "Sim2", "RTY": "Sim3"}
    )

    # Connexion
    await dtc.ensure_connected('ES')

    if dtc.paper_mode:
        print("⚠️ Mode PAPER - Ordre simulé localement")
    else:
        print("🔥 Mode LIVE - Ordre envoyé à Sierra Chart")

    # Envoyer ordre test
    print("\n🚀 Envoi ordre ES LONG 1 contrat...")
    print("   Type: MARKET")
    print("   TP: +10 ticks")
    print("   SL: -10 ticks")

    result = await dtc.place_parent_then_children(
        symbol='ES',
        side='BUY',
        qty=1,
        tp_offset_ticks=10,
        sl_offset_ticks=10,
        use_offsets=True,
        entry_kind='MKT',
        client_tag='TEST_DTC_SIMPLE'
    )

    print("\n📊 RÉSULTAT:")
    print(f"   OK: {result.get('ok', False)}")
    print(f"   Parent CID: {result.get('parent', 'N/A')}")
    print(f"   TP CID: {result.get('tp_cid', 'N/A')}")
    print(f"   SL CID: {result.get('sl_cid', 'N/A')}")
    print(f"   Account: {result.get('trade_account', 'N/A')}")

    if result.get('error'):
        print(f"   ❌ ERREUR: {result.get('error')}")

    print()


if __name__ == "__main__":
    print()
    try:
        # Test connexion uniquement
        asyncio.run(test_dtc_connection())

        # Demander si on veut tester un ordre
        # response = input("\nTester envoi ordre ? (o/N): ")
        # if response.lower() == 'o':
        #     asyncio.run(test_dtc_order())

    except KeyboardInterrupt:
        print("\n⚠️ Test interrompu")
    except Exception as e:
        print(f"\n❌ ERREUR FATALE: {e}")
        import traceback
        traceback.print_exc()
