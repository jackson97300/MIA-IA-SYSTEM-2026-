#!/usr/bin/env python3
"""
Lanceur MIA HYBRIDE en mode LIVE avec création d'un nouveau unifier
Utilise le lanceur hybride qui crée un unifier en temps réel
INTÉGRATION DES MÉTHODES ELITE
"""

import sys
import os
import subprocess
import time
import signal
import argparse
from datetime import datetime

# Ajouter le répertoire racine au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# === CONFIGURATION MÉTHODES ELITE ===
ELITE_CONFIG = {
    "elite_methods_enabled": True,
    "menthorq_elite_enabled": True,
    "battle_navale_elite_enabled": True,
    "kernel_smooth_enabled": True,
    "orderflow_advanced_enabled": True,
    "dom_health_enabled": True,
    "elite_unifier_enabled": True
}

def signal_handler(signum, frame):
    """Gestionnaire de signal pour arrêt propre"""
    print(f"\n🛑 Signal {signum} reçu - Arrêt du système...")
    sys.exit(0)

def launch_hybrid_live_system():
    """Lance le système hybride en mode live avec nouveau unifier"""
    
    print("🚀 DÉMARRAGE MIA HYBRIDE EN MODE LIVE")
    print("=" * 60)
    print("📊 Mode: Création d'un nouveau unifier en temps réel")
    print("🎯 Trading: Mode LIVE (Demo Account)")
    print("📈 Dow Theory: ✅ Activée")
    print("🔥 MÉTHODES ELITE: ✅ Activées")
    print("   - MenthorQ Elite: ✅")
    print("   - Battle Navale Elite: ✅")
    print("   - Kernel Smooth: ✅")
    print("   - OrderFlow Advanced: ✅")
    print("   - DOM Health: ✅")
    print("=" * 60)
    
    # Configuration des gestionnaires de signal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Lancer le système hybride en mode live
        cmd = [
            "python", "launch_hybrid_system.py",
            "--live",  # Mode live (pas paper trading)
            "--date", "today",  # Date d'aujourd'hui
            "--background"  # En arrière-plan
        ]
        
        print(f"📋 Commande: {' '.join(cmd)}")
        print()
        
        # Lancer le processus
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print(f"✅ Système hybride lancé (PID: {process.pid})")
        print("🔄 Le système va:")
        print("   1. Créer un nouveau unifier en temps réel")
        print("   2. Lire les dumpers C++ (Charts 3, 8, 10)")
        print("   3. Générer des données fraîches")
        print("   4. Lancer le trading en mode LIVE")
        print()
        print("📊 Monitoring du système...")
        
        # Monitoring en temps réel
        while True:
            # Vérifier si le processus est toujours actif
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print("⚠️ Processus terminé")
                if stdout:
                    print("📤 Sortie standard:")
                    print(stdout)
                if stderr:
                    print("❌ Erreurs:")
                    print(stderr)
                break
            
            # Attendre un peu
            time.sleep(5)
            
            # Afficher un heartbeat
            print(f"💓 Système actif - {datetime.now().strftime('%H:%M:%S')}")
    
    except KeyboardInterrupt:
        print("\n⏹️ Arrêt demandé par l'utilisateur")
        if 'process' in locals():
            process.terminate()
            process.wait()
    except Exception as e:
        print(f"\n❌ Erreur système: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Lanceur MIA Hybride en mode LIVE")
    parser.add_argument("--validate-only", action="store_true", help="Valider seulement les données")
    
    args = parser.parse_args()
    
    if args.validate_only:
        print("🔍 Validation des données...")
        # Lancer la validation
        subprocess.run(["python", "launch_hybrid_system.py", "--validate-only", "--date", "today"])
    else:
        launch_hybrid_live_system()

















