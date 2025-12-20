#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de validation OCO - Vérification correction 14 Nov 2025

BUT: Valider que le SL disparaît bien du DOM quand TP est touché
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from execution.sierra_dtc_connector import create_sierra_dtc_connector


async def test_oco_validation():
    """Test OCO avec prix proches pour validation rapide"""
    print("=" * 80)
    print("🔥 TEST VALIDATION OCO - Correction 14 Nov 2025")
    print("=" * 80)
    print(f"\n📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Créer connecteur ES uniquement
    connector = create_sierra_dtc_connector(
        trade_account_map={"ES": "Sim1"}
    )

    print("\n📋 Test ES avec TP/SL proches (+/- 2.5 points)")
    print("   → TP proche sera touché rapidement")
    print("   → Vérifier que SL disparaît du Trade DOM")
    print("\n" + "=" * 80)

    try:
        # Prix ES approximatif
        # AJUSTER SI NÉCESSAIRE selon le prix actuel
        es_price = 6734.0  # Prix approximatif ES

        # TP et SL très proches pour test rapide
        es_tp = es_price + 2.5  # +2.5 points (10 ticks)
        es_sl = es_price - 2.5  # -2.5 points (10 ticks)

        print(f"\n🔧 Configuration:")
        print(f"   Prix estimé ES: {es_price:.2f}")
        print(f"   TP: {es_tp:.2f} (+2.5 pts)")
        print(f"   SL: {es_sl:.2f} (-2.5 pts)")
        print(f"\n{'='*80}")

        print(f"\n📤 ENVOI BRACKET ES...")

        result = await connector.place_parent_then_children(
            symbol="ESZ25-CME",
            side="BUY",
            qty=1.0,
            entry_kind="MKT",
            entry_price=None,
            tp_price=es_tp,
            sl_price=es_sl,
            client_tag="OCO_TEST",
            children_mode="separate"
        )

        if result.get("error"):
            print(f"\n❌ Erreur: {result}")
            return 1

        print(f"\n📥 RÉSULTAT:")
        print(f"   Entry:   {result.get('parent')}")
        print(f"   TP:      {result.get('tp_cid')}")
        print(f"   SL:      {result.get('sl_cid')}")
        print(f"   Account: {result.get('trade_account')}")

        print(f"\n✅ Bracket placé avec succès !")

        # Attente avec countdown pour laisser le _reader_loop actif
        print(f"\n⏳ ATTENTE 30 SECONDES...")
        print("\n📋 INSTRUCTIONS:")
        print("   1. Ouvrez Trade DOM dans Sierra Chart")
        print("   2. Observez les ordres TP et SL")
        print("   3. Si le marché monte, le TP sera touché")
        print("   4. VÉRIFIEZ que le SL DISPARAÎT du DOM !")
        print(f"\n{'='*80}\n")

        for i in range(30):
            remaining = 30 - i
            print(f"⏱️  {remaining}s restantes... (Listener DTC actif)", end='\r')
            await asyncio.sleep(1)

        print("\n\n" + "=" * 80)
        print("📊 FIN D'OBSERVATION")
        print("=" * 80)

        print("\n🔍 RÉSULTAT ATTENDU:")
        print("   Si TP touché pendant les 30 secondes:")
        print("   ✅ Logs montrent: '🚨 OCO_TEST_TP_xxx FILLED → Annulation automatique'")
        print("   ✅ Logs montrent: '🔥 [DTC->] CANCEL OCO_TEST_SL_xxx'")
        print("   ✅ Logs montrent: '🔥 [DTC->] FLATTEN_POSITION ESZ25-CME'")
        print("   ✅ Dans Trade DOM: SL a disparu !")

        print("\n   Si aucun ordre touché:")
        print("   → Marché trop calme, réessayer avec TP plus proche")
        print("   → Ou attendre que le marché bouge")

        print("\n" + "=" * 80)
        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️ Interruption utilisateur (Ctrl+C)")
        return 130

    except Exception as e:
        print(f"\n\n❌ Erreur globale: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        print("\n🔌 Déconnexion...")
        try:
            await connector.disconnect()
            print("✅ Déconnexion effectuée")
        except:
            pass


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🎯 TEST VALIDATION OCO - Correction 14 Nov 2025")
    print("=" * 80)
    print("\n📝 Objectif:")
    print("   Vérifier que le SL disparaît du Trade DOM quand TP est touché")
    print("\n🔧 Correction appliquée:")
    print("   _cancel_order_only() utilise maintenant CANCEL (203) + FLATTEN (209)")
    print("   Au lieu de FLATTEN_ALL (210)")
    print("\n⚙️ Configuration requise:")
    print("   • Sierra Chart ouvert")
    print("   • DTC Server actif (port 11099)")
    print("   • Trade DOM ouvert avec compte Sim1")
    print("   • 'Use Attached Orders' COCHÉ dans Trade DOM")
    print("\n" + "=" * 80 + "\n")

    exit_code = asyncio.run(test_oco_validation())

    if exit_code == 0:
        print("\n🎉 TEST TERMINÉ !")
        print("\n💡 Si le TP a été touché ET le SL a disparu:")
        print("   → ✅ CORRECTION VALIDÉE")
        print("\n   Si le TP a été touché MAIS le SL reste visible:")
        print("   → ❌ PROBLÈME PERSISTE - Vérifier logs")
    else:
        print("\n❌ TEST ÉCHOUÉ")
        print("\n🔧 Vérifications suggérées:")
        print("   1. Sierra Chart est ouvert avec Chart 3 (ES)")
        print("   2. DTC Server actif (Global Settings → DTC)")
        print("   3. Compte Sim1 existe")
        print("   4. 'Use Attached Orders' coché dans Trade DOM")

    sys.exit(exit_code)

