#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test réel OCO avec skip_flatten - Validation correction 27/11/2025

BUT: Valider que quand un ordre OCO est FILLED, l'ordre opposé est annulé
     avec skip_flatten=True (pas de FLATTEN inutile)

CORRECTION TESTÉE:
- Quand SL est FILLED → TP annulé avec skip_flatten=True
- Quand TP est FILLED → SL annulé avec skip_flatten=True
- Seul CANCEL est envoyé (pas de FLATTEN car position déjà fermée)
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
from execution.sierra_dtc_connector import create_sierra_dtc_connector
from core.logger import get_logger

logger = get_logger(__name__)


def get_latest_price(symbol: str) -> float:
    """
    Détecte automatiquement le dernier prix d'un symbole depuis les données ML_READY
    """
    chart_mapping = {
        'ES': 'CHART_3',
        'NQ': 'CHART_9',
        'RTY': 'CHART_1'
    }

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
        # Essayer OCTOBRE si NOVEMBRE n'existe pas
        base_path = Path('DATA_SIERRA_CHART/DATA_2025/OCTOBRE')
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

        mid_price = data.get('mid')
        if mid_price is None:
            raise ValueError(f"Prix 'mid' non trouvé dans: {file_path}")

        return float(mid_price)


async def test_oco_skip_flatten():
    """
    Test réel OCO avec validation skip_flatten
    """
    print("=" * 80)
    print("🔥 TEST RÉEL OCO - Validation skip_flatten (27/11/2025)")
    print("=" * 80)
    print(f"\n📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📋 OBJECTIF:")
    print("   Vérifier que quand un ordre OCO est FILLED:")
    print("   ✅ L'ordre opposé est annulé avec skip_flatten=True")
    print("   ✅ Seul CANCEL est envoyé (pas de FLATTEN)")
    print("   ✅ L'ordre opposé disparaît du Trade DOM")
    print("\n" + "=" * 80)

    # Créer connecteur
    connector = create_sierra_dtc_connector(
        trade_account_map={"ES": "Sim1", "NQ": "Sim1", "RTY": "Sim1"}
    )

    try:
        # Détecter prix ES
        print("\n🔍 Détection prix ES...")
        try:
            es_price = get_latest_price("ES")
            print(f"   ✅ Prix ES détecté: {es_price:.2f}")
        except Exception as e:
            print(f"   ⚠️  Impossible de détecter prix: {e}")
            print(f"   → Utilisation prix par défaut: 4500.00")
            es_price = 4500.00

        # TP et SL très proches pour test rapide
        # TP à +1 point (4 ticks) - sera touché rapidement si marché monte
        # SL à -1 point (4 ticks) - sera touché rapidement si marché baisse
        es_tp = es_price + 1.0  # +1 point (4 ticks)
        es_sl = es_price - 1.0  # -1 point (4 ticks)

        print(f"\n🔧 Configuration:")
        print(f"   Symbol: ESZ25-CME")
        print(f"   Entry: MARKET @ ~{es_price:.2f}")
        print(f"   TP: {es_tp:.2f} (+1.0 point = 4 ticks)")
        print(f"   SL: {es_sl:.2f} (-1.0 point = 4 ticks)")
        print(f"   Qty: 1")
        print(f"\n{'='*80}")

        print(f"\n📤 ENVOI BRACKET ES...")
        print(f"   → Ordre MARKET BUY + TP/SL OCO")

        result = await connector.place_parent_then_children(
            symbol="ESZ25-CME",
            side="BUY",
            qty=1.0,
            entry_kind="MKT",
            entry_price=None,
            tp_price=es_tp,
            sl_price=es_sl,
            client_tag="TEST_SKIP_FLATTEN",
            children_mode="separate"
        )

        if result.get("error"):
            print(f"\n❌ Erreur: {result}")
            return 1

        print(f"\n✅ BRACKET PLACÉ AVEC SUCCÈS !")
        print(f"   Entry:   {result.get('parent')}")
        print(f"   TP:      {result.get('tp_cid')}")
        print(f"   SL:      {result.get('sl_cid')}")
        print(f"   Account: {result.get('trade_account')}")

        tp_cid = result.get('tp_cid')
        sl_cid = result.get('sl_cid')

        print(f"\n{'='*80}")
        print(f"⏳ ATTENTE 60 SECONDES...")
        print(f"{'='*80}")
        print(f"\n📋 INSTRUCTIONS:")
        print(f"   1. Ouvrez Trade DOM dans Sierra Chart")
        print(f"   2. Observez les ordres TP et SL")
        print(f"   3. Attendez que l'un des ordres soit touché")
        print(f"   4. VÉRIFIEZ les logs pour:")
        print(f"      ✅ '🚨 {tp_cid} FILLED → Annulation IMMÉDIATE {sl_cid}'")
        print(f"      ✅ '🔥 [DTC->] CANCEL {sl_cid}'")
        print(f"      ✅ '✅ CANCEL terminée pour {sl_cid} (FLATTEN ignoré - position déjà fermée)'")
        print(f"   5. VÉRIFIEZ dans Trade DOM: L'ordre opposé a disparu !")
        print(f"\n{'='*80}\n")

        # Attendre avec countdown
        for i in range(60):
            remaining = 60 - i
            print(f"⏱️  {remaining}s restantes... (Listener DTC actif)", end='\r')
            await asyncio.sleep(1)

        print("\n\n" + "=" * 80)
        print("📊 FIN D'OBSERVATION")
        print("=" * 80)

        print("\n🔍 RÉSULTAT ATTENDU:")
        print("\n   Si TP touché:")
        print("   ✅ Logs montrent: '🚨 TEST_SKIP_FLATTEN_TP_xxx FILLED → Annulation IMMÉDIATE TEST_SKIP_FLATTEN_SL_xxx'")
        print("   ✅ Logs montrent: '🔥 [DTC->] CANCEL TEST_SKIP_FLATTEN_SL_xxx'")
        print("   ✅ Logs montrent: '✅ CANCEL terminée pour TEST_SKIP_FLATTEN_SL_xxx (FLATTEN ignoré - position déjà fermée)'")
        print("   ✅ Logs NE montrent PAS: '🔥 [DTC->] FLATTEN_POSITION'")
        print("   ✅ Dans Trade DOM: SL a disparu !")

        print("\n   Si SL touché:")
        print("   ✅ Logs montrent: '🚨 TEST_SKIP_FLATTEN_SL_xxx FILLED → Annulation IMMÉDIATE TEST_SKIP_FLATTEN_TP_xxx'")
        print("   ✅ Logs montrent: '🔥 [DTC->] CANCEL TEST_SKIP_FLATTEN_TP_xxx'")
        print("   ✅ Logs montrent: '✅ CANCEL terminée pour TEST_SKIP_FLATTEN_TP_xxx (FLATTEN ignoré - position déjà fermée)'")
        print("   ✅ Logs NE montrent PAS: '🔥 [DTC->] FLATTEN_POSITION'")
        print("   ✅ Dans Trade DOM: TP a disparu !")

        print("\n   Si aucun ordre touché:")
        print("   → Marché trop calme, réessayer avec TP/SL plus proches")
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
    print("🎯 TEST RÉEL OCO - Validation skip_flatten (27/11/2025)")
    print("=" * 80)
    print("\n📝 Objectif:")
    print("   Vérifier que quand un ordre OCO est FILLED, l'ordre opposé")
    print("   est annulé avec skip_flatten=True (pas de FLATTEN inutile)")
    print("\n🔧 Correction testée:")
    print("   - skip_flatten=True utilisé dans _cancel_order_by_client_id")
    print("   - Seul CANCEL envoyé (pas de FLATTEN car position déjà fermée)")
    print("\n⚙️ Configuration requise:")
    print("   • Sierra Chart ouvert")
    print("   • DTC Server actif (port 11099)")
    print("   • Trade DOM ouvert avec compte Sim1")
    print("   • 'Use Attached Orders' COCHÉ dans Trade DOM")
    print("\n" + "=" * 80 + "\n")

    exit_code = asyncio.run(test_oco_skip_flatten())

    if exit_code == 0:
        print("\n🎉 TEST TERMINÉ !")
        print("\n💡 Vérifiez les logs ci-dessus pour confirmer:")
        print("   → ✅ skip_flatten=True est utilisé")
        print("   → ✅ Seul CANCEL est envoyé (pas de FLATTEN)")
        print("   → ✅ L'ordre opposé disparaît du Trade DOM")
    else:
        print("\n❌ TEST ÉCHOUÉ")
        print("\n🔧 Vérifications suggérées:")
        print("   1. Sierra Chart est ouvert avec Chart 3 (ES)")
        print("   2. DTC Server actif (Global Settings → DTC)")
        print("   3. Compte Sim1 existe")
        print("   4. 'Use Attached Orders' coché dans Trade DOM")

    sys.exit(exit_code)
