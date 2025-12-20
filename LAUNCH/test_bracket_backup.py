#!/usr/bin/env python3
"""
Test de la nouvelle méthode place_parent_then_children
"""

import asyncio
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from execution.sierra_dtc_connector import create_sierra_dtc_connector

def normalize_symbol(sym: str) -> str:
    """DTC ne veut pas des suffixes d'affichage de chart (ex: [M])"""
    i = sym.find('[')
    return sym if i == -1 else sym[:i]

async def test_parent_then_children():
    """Test de la nouvelle méthode place_parent_then_children"""

    print("🎯 Test Parent Then Children - Ordres séparés")
    print("=" * 60)

    username = os.getenv("SC_USER", "")
    password = os.getenv("SC_PASS", "")

    connector = create_sierra_dtc_connector(
        username=username,
        password=password,
        trade_account_map={"ES": "Sim1", "NQ": "Sim2"}  # ES sur Sim1, NQ sur Sim2
    )

    try:
        # --- ES (Sim1) ---
        print("📈 ES bracket (Sim1) - 150 ticks TP/SL")
        print("-" * 40)
        es_symbol = normalize_symbol("ESZ25-CME[M]")

        # TP/SL en OFFSETS (ticks) - le connecteur calcule les prix absolus!
        es_tick_size = 0.25
        sl_ticks = 20  # 5 pts
        tp_ticks = 20  # 5 pts

        print(f"   Direction: SHORT (SELL)")
        print(f"   TP offset: {tp_ticks} ticks en dessous du fill")
        print(f"   SL offset: {sl_ticks} ticks au dessus du fill")

        # Utiliser use_offsets=True pour que le connecteur calcule automatiquement!
        res_es = await connector.place_parent_then_children(
            symbol=es_symbol,
            side="SELL",  # SHORT!
            qty=1.0,
            entry_kind="MKT",  # MARKET!
            entry_price=None,
            tp_offset_ticks=tp_ticks,  # ✅ OFFSET, pas prix absolu
            sl_offset_ticks=sl_ticks,  # ✅ OFFSET, pas prix absolu
            use_offsets=True,          # ✅ Mode offsets!
            client_tag="ES",
            children_mode="separate"
        )
        print("ES:", res_es)

        # Attendre 180 secondes (3 min) pour voir l'OCO en action
        print("\n⏳ Attente 3 MINUTES - VÉRIFIE SIERRA CHART!")
        print("   Quand TP ou SL est touché, l'autre doit s'annuler!")
        print("   Le bot reste connecté pour gérer l'OCO manuellement.")
        print("   CTRL+C pour arrêter plus tôt.\n")
        for i in range(180, 0, -10):
            try:
                orders = await connector.get_open_orders(es_symbol)
                print(f"   {i} secondes... (ordres actifs: {len(orders)})")
            except:
                print(f"   {i} secondes...")
            await asyncio.sleep(10)

        # === VÉRIFICATION ===
        print("\n📋 Vérification...")
        es_orders = await connector.get_open_orders(es_symbol)

        print(f"   ES ordres: {len(es_orders)}")

        if (isinstance(res_es, dict) and 'error' not in res_es):
            print("   ✅ ES envoyé!")
        else:
            print(f"   ❌ ES erreur: {res_es}")

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    else:
        print("\n🟢 Ordres envoyés. Vérifie dans Sierra ► Trade Activity Log / Trade Orders.")
        # En environnement non interactif, pas d'input()
    finally:
        await connector.disconnect()

if __name__ == "__main__":
    asyncio.run(test_parent_then_children())
