"""
Test avec logs détaillés pour voir EXACTEMENT ce que Sierra Chart répond
quand on CANCEL + FLATTEN
"""
import asyncio
import sys
from pathlib import Path

# Setup path
sys.path.insert(0, str(Path(__file__).parent.parent))

from EXECUTION.sierra_dtc_connector import SierraDTCConnector
from datetime import datetime
import json


def get_latest_es_price():
    """Récupère le dernier prix ES depuis ML_READY"""
    today = datetime.now().strftime('%Y%m%d')
    base_path = Path('DATA_SIERRA_CHART/DATA_2025/NOVEMBRE')
    file_path = base_path / today / 'CHART_3' / 'ML_READY' / 'ml_ESZ25_FUT_CME_3.jsonl'

    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            if lines:
                data = json.loads(lines[-1].strip())
                return data.get('mid', 6000.0)
    except:
        pass
    return 6000.0


async def test_avec_logs_detailles():
    """Test avec surveillance des réponses Sierra Chart"""

    print("\n" + "="*80)
    print("🔍 TEST DÉTAILLÉ - Surveillance messages Sierra Chart")
    print("="*80)
    print("\nCe test va :")
    print("  1. Créer position LONG ES")
    print("  2. Créer TP et SL proches")
    print("  3. AFFICHER TOUS les messages Sierra Chart")
    print("  4. Vérifier si CANCEL et FLATTEN sont bien ACK")
    print("="*80)

    # Connexion
    connector = SierraDTCConnector(
        host="127.0.0.1",
        port=11099,
        symbols=["ES"],
        trade_account_map={"ES": "Sim1"}
    )

    try:
        # Connecter
        await connector.connect("ES")

        # Prix actuel
        current_price = get_latest_es_price()
        tp_price = round((current_price + 2.0) / 0.25) * 0.25  # +2 pts
        sl_price = round((current_price - 2.0) / 0.25) * 0.25  # -2 pts

        print(f"\n📊 LONG ES @ ~{current_price:.2f}")
        print(f"   TP: {tp_price:.2f} (+2 pts)")
        print(f"   SL: {sl_price:.2f} (-2 pts)")
        print("\n📤 Envoi bracket order...")

        # Placer ordre
        result = await connector.place_parent_then_children(
            symbol="ESZ25-CME",
            side="BUY",
            qty=1.0,
            entry_kind="MKT",
            entry_price=None,
            tp_price=tp_price,
            sl_price=sl_price,
            client_tag="TEST_LOGS",
            children_mode="separate"
        )

        if result.get("error"):
            print(f"\n❌ Erreur: {result}")
            return

        print(f"\n✅ Ordres créés:")
        print(f"   Parent: {result.get('parent')}")
        print(f"   TP CID: {result.get('tp_cid')}")
        print(f"   SL CID: {result.get('sl_cid')}")

        print("\n" + "="*80)
        print("⏳ ATTENTE 30 secondes pour que TP ou SL soit touché...")
        print("="*80)
        print("\n📺 SURVEILLANCE DES MESSAGES (les ORDER_UPDATE vont s'afficher ci-dessous):")
        print("-" * 80)

        # Attendre 30s pour observer
        await asyncio.sleep(30)

        print("\n" + "="*80)
        print("🔍 ANALYSE")
        print("="*80)
        print("\nDans les logs ci-dessus, cherchez:")
        print("  1. 🚨 TP (ou SL) FILLED → Annulation automatique")
        print("  2. 🔥 [DTC->] CANCEL xxx")
        print("  3. 🔥 [DTC->] FLATTEN_POSITION")
        print("  4. Réponses Sierra Chart (ORDER_UPDATE avec OrderStatus)")
        print("\nSi vous voyez CANCEL + FLATTEN envoyés MAIS SL reste:")
        print("  → C'est un problème d'affichage Sierra Chart")
        print("  → Essayez de fermer/rouvrir Trade DOM")
        print("  → Ou cliquez 'Refresh' dans Trade Activity Log")

    finally:
        print("\n🔌 Déconnexion...")
        await connector.disconnect()
        print("✅ Terminé")


if __name__ == "__main__":
    asyncio.run(test_avec_logs_detailles())
