"""
Test TP/SL avec attente active (pas d'input qui bloque)
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from EXECUTION.sierra_dtc_connector import SierraDTCConnector


def get_latest_es_price():
    """Récupère prix ES"""
    today = datetime.now().strftime('%Y%m%d')
    file_path = Path('DATA_SIERRA_CHART/DATA_2025/NOVEMBRE') / today / 'CHART_3' / 'ML_READY' / 'ml_ESZ25_FUT_CME_3.jsonl'
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            if lines:
                data = json.loads(lines[-1].strip())
                return data.get('mid', 6000.0)
    except:
        pass
    return 6000.0


async def test_avec_attente():
    """Test avec attente active pour voir les messages OCO"""
    
    print("\n" + "="*80)
    print("🧪 TEST TP/SL - Attente active 30 secondes")
    print("="*80)
    
    connector = SierraDTCConnector(
        host="127.0.0.1",
        port=11099,
        symbols=["ES"],
        trade_account_map={"ES": "Sim1"}
    )
    
    try:
        await connector.connect("ES")
        
        current_price = get_latest_es_price()
        tp_price = round((current_price + 5.0) / 0.25) * 0.25
        sl_price = round((current_price - 5.0) / 0.25) * 0.25
        
        print(f"\n📊 LONG ES @ ~{current_price:.2f}")
        print(f"   TP: {tp_price:.2f} (+5 pts)")
        print(f"   SL: {sl_price:.2f} (-5 pts)")
        print("\n📤 Envoi bracket order...\n")
        
        result = await connector.place_parent_then_children(
            symbol="ESZ25-CME",
            side="BUY",
            qty=1.0,
            entry_kind="MKT",
            entry_price=None,
            tp_price=tp_price,
            sl_price=sl_price,
            client_tag="TEST_WAIT",
            children_mode="separate"
        )
        
        if result.get("error"):
            print(f"\n❌ Erreur: {result}")
            return
        
        print(f"\n✅ Ordres créés:")
        print(f"   TP CID: {result.get('tp_cid')}")
        print(f"   SL CID: {result.get('sl_cid')}")
        
        print("\n" + "="*80)
        print("⏳ ATTENTE 30 SECONDES")
        print("="*80)
        print("\n📋 Instructions:")
        print("   1. Ouvrez Trade DOM (compte Sim1)")
        print("   2. Drag & drop TP ou SL près du prix actuel")
        print("   3. Attendez que l'ordre se remplisse")
        print("   4. OBSERVEZ les logs ci-dessous :\n")
        print("      🔍 Cherchez le message :")
        print("      🚨 XXX FILLED → Annulation automatique YYY")
        print("      🔥 [DTC->] CANCEL YYY")
        print("      🔥 [DTC->] FLATTEN_TRADE_ACCOUNT Sim1")
        print("\n" + "-"*80)
        
        # Attendre 30 secondes en laissant le listener actif
        for i in range(30):
            await asyncio.sleep(1)
            # Le _reader_loop continue de tourner en arrière-plan
            print(f"⏱️  {30-i}s restantes...", end='\r')
        
        print("\n\n" + "="*80)
        print("⏰ Temps écoulé - Fin du test")
        print("="*80)
        print("\n📊 RÉSULTAT:")
        print("   Si vous avez vu les messages 🚨 et 🔥 ci-dessus:")
        print("   → Le système OCO fonctionne ✅")
        print("\n   Si vous n'avez PAS vu ces messages:")
        print("   → Le _reader_loop ne détecte pas le FILL ❌")
        
    finally:
        print("\n🔌 Déconnexion...")
        await connector.disconnect()
        print("✅ Terminé\n")


if __name__ == "__main__":
    asyncio.run(test_avec_attente())

