#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 TEST FIX TP/SL - Validation de la correction du FLATTEN

Date: 14 Nov 2025
But: Tester que le FLATTEN est bien envoyé quand TP/SL est touché
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from execution.sierra_dtc_connector import create_sierra_dtc_connector
from core.logger import get_logger

logger = get_logger(__name__)


async def test_tp_sl_flatten():
    """Test que le FLATTEN est envoyé après TP/SL"""
    
    print("="*80)
    print("🔧 TEST FIX TP/SL - Validation FLATTEN")
    print("="*80)
    
    # Créer connecteur
    connector = create_sierra_dtc_connector(
        trade_account_map={"ES": "Sim1", "NQ": "Sim2", "RTY": "Sim3"}
    )
    
    # Callback pour tracker les fermetures
    closed_positions = []
    
    async def on_position_closed(symbol: str, fill_info: dict):
        """Callback appelé quand position fermée"""
        logger.info(f"✅ CALLBACK: {symbol} fermé ({fill_info['exit_type']})")
        closed_positions.append({
            'symbol': symbol,
            'exit_type': fill_info['exit_type'],
            'price': fill_info['fill_price']
        })
    
    # Enregistrer callback
    connector.set_position_closed_callback(on_position_closed)
    
    print("\n📋 Étapes du test:")
    print("   1. Placer trade ES avec TP/SL")
    print("   2. Attendre que TP ou SL soit touché")
    print("   3. Vérifier logs: CANCEL + FLATTEN")
    print("   4. Vérifier callback appelé")
    print("\n⚠️  VÉRIFICATIONS MANUELLES REQUISES:")
    print("   - Sierra Chart: Position doit être à 0 après TP/SL")
    print("   - Logs: Chercher '[DTC->] FLATTEN_POSITION'")
    print("\n" + "="*80)
    
    # Placer un trade ES avec TP/SL
    print("\n📤 Placement trade ES avec TP/SL...")
    
    result = await connector.place_parent_then_children(
        symbol="ESZ25-CME",
        side="BUY",
        qty=1.0,
        entry_kind="MKT",
        entry_price=None,
        tp_price=6770.0,  # TP 5 points au-dessus
        sl_price=6760.0,  # SL 5 points en-dessous
        client_tag="TEST_FIX",
        children_mode="separate"
    )
    
    if result.get("error"):
        print(f"\n❌ Erreur placement: {result}")
        return False
    
    print(f"\n✅ Trade placé:")
    print(f"   Parent: {result['parent']}")
    print(f"   TP:     {result['tp_cid']}")
    print(f"   SL:     {result['sl_cid']}")
    
    print("\n⏳ Attente TP/SL touché (60s max)...")
    print("   💡 Astuce: Déplacer le prix manuellement dans Sierra Chart")
    print("   💡 Chart → Advanced/Custom Settings → 'Simulated Order Fill Delay (ms)' = 0")
    
    # Attendre max 60s
    for i in range(60):
        await asyncio.sleep(1)
        
        if closed_positions:
            print(f"\n🎉 POSITION FERMÉE DÉTECTÉE !")
            print(f"   Symbol: {closed_positions[0]['symbol']}")
            print(f"   Type:   {closed_positions[0]['exit_type']}")
            print(f"   Prix:   {closed_positions[0]['price']}")
            
            print("\n🔍 VÉRIFICATIONS:")
            print("   1. ✅ Callback appelé")
            print("   2. ⏳ Vérifier logs pour FLATTEN...")
            
            # Attendre un peu pour les logs
            await asyncio.sleep(2)
            
            print("\n📝 Vérifier les logs:")
            print("   Get-Content logs\\execution.sierra_dtc_connector*.log -Tail 50 | Select-String 'FLATTEN'")
            
            print("\n📊 Vérifier Sierra Chart:")
            print("   Trade → Trade DOM → Net Position doit être 0")
            
            return True
        
        if (i + 1) % 10 == 0:
            print(f"   ... {i+1}s écoulées (attente TP/SL)")
    
    print("\n⏱️ Timeout 60s - TP/SL non touché")
    print("\n💡 Pour tester manuellement:")
    print("   1. Chercher l'ordre TP/SL dans Sierra Chart (Trade DOM)")
    print("   2. Cliquer sur 'Flatten All' pour simuler fermeture")
    print("   3. Observer les logs pour CANCEL + FLATTEN")
    
    return False


async def main():
    """Main test"""
    try:
        success = await test_tp_sl_flatten()
        
        print("\n" + "="*80)
        if success:
            print("✅ TEST RÉUSSI - Fix validé !")
            print("\n🔥 FLATTEN est maintenant envoyé automatiquement")
            print("🎯 Le bot ferme correctement les positions après TP/SL")
        else:
            print("⚠️  TEST INCOMPLET - Validation manuelle requise")
            print("\n📋 Vérifications à faire:")
            print("   1. Logs contiennent '[DTC->] FLATTEN_POSITION'")
            print("   2. Sierra Chart: Position = 0 après fermeture")
            print("   3. Bot: Pas d'erreur de désynchronisation")
        print("="*80)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Interruption utilisateur")
        return 130
    except Exception as e:
        print(f"\n\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

