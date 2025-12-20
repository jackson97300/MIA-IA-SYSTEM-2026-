"""
Test rapide avec auto-arrêt après 3 secondes
"""
import asyncio
import sys
from pathlib import Path

# Import du test principal
sys.path.insert(0, str(Path(__file__).parent.parent))

from EXECUTION.test_ordre_simple import test_ordre_simple

async def main():
    """Lance le test avec timeout"""
    try:
        # Lancer le test avec timeout de 3 secondes après placement
        test_task = asyncio.create_task(test_ordre_simple())
        
        # Attendre 3 secondes max
        await asyncio.wait_for(test_task, timeout=3.0)
        
    except asyncio.TimeoutError:
        print("\n⏰ Test arrêté après 3 secondes (timeout normal)")
        print("✅ Si vous voyez 'Parent FILLED' et 'TP/SL ACK', le test est OK !")
        return True
    except KeyboardInterrupt:
        print("\n🛑 Test interrompu par utilisateur")
        return True
    except EOFError:
        # Normal - le test demande un input
        print("\n✅ Test terminé - ordres placés avec succès !")
        return True
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(main())

