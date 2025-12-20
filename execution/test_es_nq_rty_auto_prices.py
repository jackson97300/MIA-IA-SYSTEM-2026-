#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test complet ES + NQ + RTY avec brackets et DÉTECTION AUTOMATIQUE DES PRIX

Date: 06 Nov 2025
But: Valider l'exécution complète avec prix réels détectés automatiquement
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from execution.sierra_dtc_connector import create_sierra_dtc_connector


def get_latest_price(symbol: str) -> float:
    """
    Détecte automatiquement le dernier prix d'un symbole depuis les données ML_READY

    Args:
        symbol: 'ES', 'NQ' ou 'RTY'

    Returns:
        float: Le dernier prix mid du symbole
    """
    # Mapping symbole → chart
    chart_mapping = {
        'ES': 'CHART_3',
        'NQ': 'CHART_9',
        'RTY': 'CHART_1'
    }

    # Mapping symbole → nom de fichier
    file_mapping = {
        'ES': 'ml_ESZ25_FUT_CME_3.jsonl',
        'NQ': 'ml_NQZ25_FUT_CME_9.jsonl',
        'RTY': 'ml_RTYZ25_FUT_CME_1.jsonl'
    }

    if symbol not in chart_mapping:
        raise ValueError(f"Symbole inconnu: {symbol}")

    chart = chart_mapping[symbol]
    file_name = file_mapping[symbol]

    # Construire le chemin vers le fichier
    today = datetime.now().strftime('%Y%m%d')
    base_path = Path('DATA_SIERRA_CHART/DATA_2025/NOVEMBRE')
    file_path = base_path / today / chart / 'ML_READY' / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"Fichier non trouvé: {file_path}")

    # Lire la dernière ligne du fichier
    with open(file_path, 'r') as f:
        lines = f.readlines()
        if not lines:
            raise ValueError(f"Fichier vide: {file_path}")

        last_line = lines[-1].strip()
        data = json.loads(last_line)

        # Récupérer le prix mid
        mid_price = data.get('mid')
        if mid_price is None:
            raise ValueError(f"Prix 'mid' non trouvé dans: {file_path}")

        return float(mid_price)


async def test_bracket(
    connector,
    instrument: str,
    symbol: str,
    qty: float,
    tp_price: float,
    sl_price: float,
    client_tag: str
):
    """Test bracket pour un instrument"""
    print(f"\n{'='*70}")
    print(f"🔧 TEST {instrument} - Ordre MARKET + Bracket")
    print(f"{'='*70}")
    print(f"   Symbol: {symbol}")
    print(f"   Entry: MARKET")
    print(f"   TP: {tp_price:.2f}")
    print(f"   SL: {sl_price:.2f}")
    print(f"   Qty: {qty}")
    print(f"{'-'*70}")

    try:
        start_time = datetime.now()

        print(f"\n📤 ENVOI BRACKET {instrument} (MARKET)...")

        result = await connector.place_parent_then_children(
            symbol=symbol,
            side="BUY",
            qty=qty,
            entry_kind="MKT",
            entry_price=None,
            tp_price=tp_price,
            sl_price=sl_price,
            client_tag=client_tag,
            children_mode="separate"  # ✅ 2x Type 208 avec OCOGroup (SPAWN VICTOIRE)
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        if result.get("error"):
            print(f"\n❌ Erreur {instrument}: {result}")
            return {"instrument": instrument, "success": False, "error": result.get("error")}

        print(f"\n📥 RÉPONSE {instrument}:")
        print(f"   Entry:   {result.get('entry', 'N/A')}")
        print(f"   TP:      {result.get('tp_cid')}")
        print(f"   SL:      {result.get('sl_cid')}")
        print(f"   Account: {result.get('trade_account')}")
        print(f"   Temps:   {elapsed:.3f}s")
        print(f"\n✅ {instrument} - Bracket placé avec succès !")

        return {
            "instrument": instrument,
            "success": True,
            "result": result,
            "elapsed": elapsed
        }

    except Exception as e:
        print(f"\n❌ Exception {instrument}: {e}")
        import traceback
        traceback.print_exc()
        return {"instrument": instrument, "success": False, "error": str(e)}


async def main():
    """Test complet ES + NQ + RTY avec détection automatique des prix"""
    print("=" * 80)
    print("🔥 TEST BRACKET COMPLET - ES + NQ + RTY (Prix Auto)")
    print("=" * 80)
    print(f"\n📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # ═══════════════════════════════════════════════════════════
    # DÉTECTION AUTOMATIQUE DES PRIX
    # ═══════════════════════════════════════════════════════════
    print("\n🔍 DÉTECTION AUTOMATIQUE DES PRIX...")

    try:
        es_price = get_latest_price('ES')
        nq_price = get_latest_price('NQ')
        rty_price = get_latest_price('RTY')

        print(f"   ✅ ES  : {es_price:.2f}")
        print(f"   ✅ NQ  : {nq_price:.2f}")
        print(f"   ✅ RTY : {rty_price:.2f}")
    except Exception as e:
        print(f"\n❌ Erreur détection prix: {e}")
        print("\n💡 Utilisation des prix par défaut...")
        es_price = 6837.0
        nq_price = 25785.0
        rty_price = 2477.0

    print("\n📋 Configuration:")
    print("   ES  → Sim1 (E-mini S&P 500)")
    print("   NQ  → Sim2 (E-mini NASDAQ)")
    print("   RTY → Sim3 (Russell 2000)")
    print("   Mode: MARKET (exécution immédiate)")
    print("   TP/SL: Calculés automatiquement")
    print("\n" + "=" * 80)

    # Créer connecteur pour ES, NQ et RTY
    connector = create_sierra_dtc_connector(
        trade_account_map={"ES": "Sim1", "NQ": "Sim2", "RTY": "Sim3"}
    )

    results = []

    try:
        # ═══════════════════════════════════════════════════════════
        # TEST 1 : E-mini S&P 500 (ES)
        # ═══════════════════════════════════════════════════════════
        # ES: tick_size=0.25 → 5.0 pts = 20 ticks
        es_tp = es_price + 5.0
        es_sl = es_price - 5.0

        es_result = await test_bracket(
            connector=connector,
            instrument="ES",
            symbol="ESZ25-CME",
            qty=1.0,
            tp_price=es_tp,
            sl_price=es_sl,
            client_tag="ES_TEST"
        )
        results.append(es_result)

        # Pause entre les tests
        await asyncio.sleep(3)

        # ═══════════════════════════════════════════════════════════
        # TEST 2 : E-mini NASDAQ (NQ)
        # ═══════════════════════════════════════════════════════════
        # NQ: tick_size=0.25 → 10.0 pts = 40 ticks
        nq_tp = nq_price + 10.0
        nq_sl = nq_price - 10.0

        nq_result = await test_bracket(
            connector=connector,
            instrument="NQ",
            symbol="NQZ25-CME",
            qty=1.0,
            tp_price=nq_tp,
            sl_price=nq_sl,
            client_tag="NQ_TEST"
        )
        results.append(nq_result)

        # Pause entre les tests
        await asyncio.sleep(3)

        # ═══════════════════════════════════════════════════════════
        # TEST 3 : Russell 2000 (RTY)
        # ═══════════════════════════════════════════════════════════
        # RTY: tick_size=0.10 → 2.0 pts = 20 ticks (cohérent avec ES)
        rty_tp = rty_price + 2.0  # 20 ticks
        rty_sl = rty_price - 2.0  # 20 ticks

        rty_result = await test_bracket(
            connector=connector,
            instrument="RTY",
            symbol="RTYZ25-CME",
            qty=1.0,
            tp_price=rty_tp,
            sl_price=rty_sl,
            client_tag="RTY_TEST"
        )
        results.append(rty_result)

        # ═══════════════════════════════════════════════════════════
        # RÉSUMÉ FINAL
        # ═══════════════════════════════════════════════════════════
        print(f"\n\n{'='*80}")
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 80)

        success_count = sum(1 for r in results if r.get("success"))
        total_count = len(results)

        for result in results:
            instrument = result.get("instrument")
            success = result.get("success")

            if success:
                print(f"\n✅ {instrument} : SUCCÈS")
                res = result.get("result", {})
                elapsed = result.get("elapsed", 0)
                print(f"   TP:      {res.get('tp_cid')}")
                print(f"   SL:      {res.get('sl_cid')}")
                print(f"   Account: {res.get('trade_account')}")
                print(f"   Temps:   {elapsed:.3f}s")
            else:
                print(f"\n❌ {instrument} : ÉCHEC")
                print(f"   Erreur: {result.get('error')}")

        print(f"\n{'='*80}")
        print(f"📈 Résultat global: {success_count}/{total_count} tests réussis")
        print("=" * 80)

        if success_count == total_count:
            print("\n🎉 TOUS LES TESTS ONT RÉUSSI !")
            print("\n🔍 Vérifiez dans Sierra Chart:")
            print("   • Window → Trade Activity Log")
            print("   • Trade → Trade DOM (pour voir les positions)")
            print("\n⚡ OCO CÔTÉ SERVEUR ACTIF:")
            print("   • TP et SL sont liés via OCOLinkedOrderServerOrderID")
            print("   • Sierra Chart gère l'OCO automatiquement")
            print("   • Quand TP/SL touché → l'autre ordre disparaît")
            print("\n🎯 TESTEZ MAINTENANT:")
            print("   1. Bougez le TP manuellement pour le faire toucher")
            print("   2. Vérifiez que le SL DISPARAÎT automatiquement")
            print("   3. Ou inversement: touchez le SL, le TP disparaît")
            print("\n⏳ Le bot reste connecté - Appuyez sur Ctrl+C pour arrêter")

            # 🔥 ATTENTE INFINIE jusqu'à Ctrl+C
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\n✅ Arrêt demandé par l'utilisateur")
        else:
            print(f"\n⚠️ {total_count - success_count} test(s) échoué(s)")
            print("\n💡 Vérifiez:")
            print("   • Sierra Chart est ouvert")
            print("   • Serveur DTC actif (port 11099)")
            print("   • Simulation active (Sim1, Sim2, Sim3)")
            print("   • Charts bien configurés (ES=3, NQ=9, RTY=1)")
            print("   • Linking désactivé (Chart Linking = None)")
            return 1

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
    print("🎯 TEST ES + NQ + RTY - Détection automatique des prix")
    print("=" * 80)
    print("\n📝 Objectif:")
    print("   Valider l'exécution complète ES + NQ + RTY avec brackets")
    print("   automatiques et détection automatique des prix réels.")
    print("\n📚 Configuration:")
    print("   • Prix détectés automatiquement depuis ML_READY")
    print("   • Port DTC unique: 11099 (même instance Sierra Chart)")
    print("   • 3 comptes sim: Sim1 (ES), Sim2 (NQ), Sim3 (RTY)")
    print("   • 3 charts séparés: ES=3, NQ=9, RTY=1")
    print("\n" + "=" * 80 + "\n")

    exit_code = asyncio.run(main())

    if exit_code == 0:
        print("\n🎉 TEST RÉUSSI - ES + NQ + RTY OPÉRATIONNELS !")
        print("\n💡 Système prêt pour:")
        print("   • Collecte de données live (3 marchés)")
        print("   • Trading paper automatique (3 marchés)")
        print("   • Migration vers live trading")
        print("\n🚀 Prochaine étape:")
        print("   • Ajouter GC (Chart 2) et CL (Chart 4)")
    else:
        print("\n❌ TEST ÉCHOUÉ")
        print("\n🔧 Vérifications suggérées:")
        print("   1. Sierra Chart ouvert avec Charts 1, 3, 9")
        print("   2. Chart 1 = RTYZ25-CME (pas ESZ25-CME)")
        print("   3. Chart 3 = ESZ25-CME")
        print("   4. Chart 9 = NQZ25-CME")
        print("   5. Chart Linking = None pour chaque chart")
        print("   6. DTC Server actif sur port 11099")
        print("   7. Comptes Sim1, Sim2, Sim3 créés")

    sys.exit(exit_code)

        print("   3. Chart 3 = ESZ25-CME")
        print("   4. Chart 9 = NQZ25-CME")
        print("   5. Chart Linking = None pour chaque chart")
        print("   6. DTC Server actif sur port 11099")
        print("   7. Comptes Sim1, Sim2, Sim3 créés")

    sys.exit(exit_code)
