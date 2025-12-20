#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 TEST SIMPLE - 1 ordre ES seulement

But: Vérifier que les ordres sont créés correctement dans Sierra Chart
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from execution.sierra_dtc_connector import create_sierra_dtc_connector
from core.logger import get_logger

logger = get_logger(__name__)


async def test_ordre_simple():
    """Test ultra-simple: 1 ordre MARKET ES avec TP/SL"""

    print("="*80)
    print("🧪 TEST SIMPLE - Ordre ES uniquement")
    print("="*80)
    print("\n📋 Ce test va:")
    print("   1. Créer 1 ordre MARKET BUY sur ES")
    print("   2. Créer TP @ +5 points")
    print("   3. Créer SL @ -5 points")
    print("   4. Attendre que VOUS vérifiez dans Sierra Chart")
    print("\n" + "="*80)

    # Créer connecteur
    connector = create_sierra_dtc_connector(
        trade_account_map={"ES": "Sim1"}
    )

    try:
        print("\n📤 Envoi ordre MARKET ES...")

        # 🔍 DÉTECTION AUTOMATIQUE DU PRIX (comme test_es_nq_rty_auto_prices)
        import json
        from pathlib import Path
        from datetime import datetime

        # Chemin fichier ML_READY ES (même logique que test_es_nq_rty_auto_prices)
        today = datetime.now().strftime('%Y%m%d')
        base_path = Path('DATA_SIERRA_CHART/DATA_2025/NOVEMBRE')
        file_path = base_path / today / 'CHART_3' / 'ML_READY' / 'ml_ESZ25_FUT_CME_3.jsonl'

        current_price = 6000.0  # Fallback
        try:
            if file_path.exists():
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        last_line = lines[-1].strip()
                        data = json.loads(last_line)
                        current_price = data.get('mid', 6000.0)
                print(f"✅ Prix détecté depuis: {file_path.name}")
            else:
                print(f"⚠️ Fichier non trouvé: {file_path}")
                print(f"   Utilisation prix par défaut: {current_price}")
        except Exception as e:
            print(f"⚠️ Erreur lecture prix: {e}")
            print(f"   Utilisation prix par défaut: {current_price}")

        # Calculer TP/SL (5 points comme test_es_nq_rty_auto_prices)
        tick_size = 0.25
        tp_distance = 5.0  # 5 points = 20 ticks
        sl_distance = 5.0  # 5 points = 20 ticks

        tp_price = round((current_price + tp_distance) / tick_size) * tick_size
        sl_price = round((current_price - sl_distance) / tick_size) * tick_size

        print(f"\n📊 LONG ES @ {current_price:.2f}")
        print(f"   TP: {tp_price:.2f} (+{tp_distance:.1f} pts)")
        print(f"   SL: {sl_price:.2f} (-{sl_distance:.1f} pts)")
        print()

        result = await connector.place_parent_then_children(
            symbol="ESZ25-CME",
            side="BUY",
            qty=1.0,
            entry_kind="MKT",
            entry_price=None,
            tp_price=tp_price,  # ✅ Calculé dynamiquement
            sl_price=sl_price,  # ✅ Calculé dynamiquement
            client_tag="TEST_SIMPLE",
            children_mode="separate"
        )

        if result.get("error"):
            print(f"\n❌ ERREUR: {result}")
            return False

        print(f"\n📥 RÉSULTAT:")
        print(f"   Parent: {result.get('parent', 'N/A')}")
        print(f"   TP:     {result.get('tp_cid', 'N/A')}")
        print(f"   SL:     {result.get('sl_cid', 'N/A')}")
        print(f"   Compte: {result.get('trade_account', 'N/A')}")

        print("\n" + "="*80)
        print("⏳ ATTENTE 30 SECONDES - Listener DTC actif")
        print("="*80)
        print("\n📋 MAINTENANT dans Sierra Chart:")
        print("   1. Drag & drop TP ou SL près du prix")
        print("   2. Attendez qu'il se remplisse")
        print("   3. OBSERVEZ les logs ci-dessous :")
        print("\n      🔍 Cherchez :")
        print("      🚨 TEST_SIMPLE_TP_xxx FILLED → Annulation automatique")
        print("      🔥 [DTC->] CANCEL TEST_SIMPLE_SL_xxx")
        print("      🔥 [DTC->] FLATTEN_POSITION")
        print("\n" + "-"*80)

        # Attendre 30s pour laisser le _reader_loop actif
        for i in range(30):
            await asyncio.sleep(1)
            print(f"⏱️  {30-i}s restantes...", end='\r')

        print("\n\n" + "="*80)
        print("⏰ Fin de l'attente")
        print("="*80)
        print("\n✅ Si vous avez vu les messages OCO → Système fonctionne !")
        print("❌ Si aucun message OCO → Le _reader_loop n'a pas détecté le FILL")
        print("\n💡 Vérifiez dans Sierra Chart Trade DOM si le SL a disparu")

        return True  # Succès - bracket créé et listener actif 30s

    except Exception as e:
        print(f"\n❌ EXCEPTION: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print("\n🔌 Déconnexion...")
        try:
            await connector.disconnect()
            print("✅ Déconnexion OK")
        except:
            pass


async def main():
    """Main"""
    print("\n🎯 TEST DIAGNOSTIQUE SIMPLIFIÉ")
    print("="*80)
    print("Ce test aide à identifier LE problème exact:")
    print("  • Ordre parent pas rempli? → Config Sierra Chart")
    print("  • Ordres enfants pas créés? → Code place_parent_then_children")
    print("  • Tout OK mais TP/SL fonctionnent pas? → Listener DTC")
    print("="*80 + "\n")

    success = await test_ordre_simple()

    print("\n" + "="*80)
    if success:
        print("✅ TEST RÉUSSI")
        print("\n📝 Prochaine étape:")
        print("   Tester avec le bot complet et vérifier FLATTEN automatique")
    else:
        print("❌ TEST ÉCHOUÉ")
        print("\n📝 Suivre les instructions ci-dessus pour corriger")
    print("="*80)

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
