# predict_live.py
# -*- coding: utf-8 -*-
"""
Script de prédiction live pour paper trading
- Charge un modèle entraîné (XGBoost)
- Score des snapshots en temps réel
- Applique le policy overlay pour les décisions
- Journalise les trades simulés
"""

import os, sys, json, time
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd
import xgboost as xgb

# Import du policy overlay
try:
    from policy_overlay import PolicyOverlay
except ImportError:
    print("[WARN] PolicyOverlay non disponible - prédictions sans gating")
    PolicyOverlay = None

class LivePredictor:
    def __init__(self, model_path: str, scaler_path: str = None, policy_config: str = None):
        """Initialise le prédicteur live"""
        self.model_path = model_path
        self.scaler_path = scaler_path
        self.model = None
        self.scaler = None
        self.policy = None
        self.feature_cols = None
        
        # Charger le modèle
        self._load_model()
        
        # Charger le scaler si disponible
        if scaler_path and os.path.exists(scaler_path):
            self._load_scaler()
        
        # Charger le policy overlay
        if PolicyOverlay and policy_config:
            self._load_policy(policy_config)
        
        # Journal des trades
        self.trades_log = []
        self.position = 0.0  # Position actuelle
        self.last_price = None
        
    def _load_model(self):
        """Charge le modèle XGBoost"""
        try:
            if self.model_path.endswith('.json'):
                self.model = xgb.XGBClassifier()
                self.model.load_model(self.model_path)
            else:
                import joblib
                self.model = joblib.load(self.model_path)
            print(f"✅ Modèle chargé: {self.model_path}")
        except Exception as e:
            print(f"❌ Erreur chargement modèle: {e}")
            sys.exit(1)
    
    def _load_scaler(self):
        """Charge le scaler"""
        try:
            import joblib
            self.scaler = joblib.load(self.scaler_path)
            print(f"✅ Scaler chargé: {self.scaler_path}")
        except Exception as e:
            print(f"⚠️ Erreur chargement scaler: {e}")
    
    def _load_policy(self, config_path: str):
        """Charge le policy overlay"""
        try:
            self.policy = PolicyOverlay(config_path)
            print(f"✅ Policy overlay chargé: {config_path}")
        except Exception as e:
            print(f"⚠️ Erreur chargement policy: {e}")
    
    def prepare_features(self, snapshot: dict) -> np.ndarray:
        """Prépare les features pour le modèle"""
        # Colonnes attendues par le modèle (à adapter selon votre dataset)
        feature_cols = [
            'o', 'h', 'l', 'c', 'volume', 'bidvol', 'askvol',
            'up1', 'dn1', 'up2', 'dn2', 'up3', 'dn3',
            'ask_volume', 'bid_volume', 'delta', 'pressure', 'pressure_smooth',
            'vix', 'atr', 'cc'
        ]
        
        # Extraire les features du snapshot
        features = []
        for col in feature_cols:
            value = snapshot.get(col, 0.0)
            if pd.isna(value):
                value = 0.0
            features.append(float(value))
        
        return np.array(features).reshape(1, -1)
    
    def predict(self, snapshot: dict) -> dict:
        """Prédit sur un snapshot"""
        try:
            # Préparer les features
            X = self.prepare_features(snapshot)
            
            # Appliquer le scaler si disponible
            if self.scaler is not None:
                X = self.scaler.transform(X)
            
            # Prédiction du modèle
            proba = self.model.predict_proba(X)[0]
            pred_class = self.model.predict(X)[0]
            
            # Mapping des classes (si nécessaire)
            class_mapping = {0: -1, 1: 0, 2: 1}  # Ajuster selon votre mapping
            pred_direction = class_mapping.get(pred_class, 0)
            
            # Appliquer le policy overlay
            decision = {
                'action': 'hold',
                'confidence': float(max(proba)),
                'direction': pred_direction,
                'probabilities': proba.tolist()
            }
            
            if self.policy:
                # Utiliser le policy overlay pour gater la décision
                vix = snapshot.get('vix', 20.0)
                atr = snapshot.get('atr', 1.0)
                pressure = snapshot.get('pressure_smooth', 0.0)
                
                policy_decision = self.policy.get_decision(
                    vix=vix, atr=atr, pressure=pressure,
                    model_direction=pred_direction,
                    model_confidence=max(proba)
                )
                
                decision.update(policy_decision)
            
            return decision
            
        except Exception as e:
            print(f"❌ Erreur prédiction: {e}")
            return {
                'action': 'hold',
                'confidence': 0.0,
                'direction': 0,
                'error': str(e)
            }
    
    def simulate_trade(self, snapshot: dict, decision: dict):
        """Simule un trade basé sur la décision"""
        current_price = snapshot.get('c', 0.0)
        if current_price == 0:
            return
        
        action = decision.get('action', 'hold')
        confidence = decision.get('confidence', 0.0)
        
        # Logique de trading simple
        if action == 'buy' and self.position <= 0:
            # Ouvrir position longue
            self.position = 1.0
            self.last_price = current_price
            trade = {
                'timestamp': datetime.now().isoformat(),
                'action': 'BUY',
                'price': current_price,
                'confidence': confidence,
                'position': self.position
            }
            self.trades_log.append(trade)
            print(f"📈 BUY @ {current_price:.2f} (conf: {confidence:.3f})")
            
        elif action == 'sell' and self.position >= 0:
            # Ouvrir position courte
            self.position = -1.0
            self.last_price = current_price
            trade = {
                'timestamp': datetime.now().isoformat(),
                'action': 'SELL',
                'price': current_price,
                'confidence': confidence,
                'position': self.position
            }
            self.trades_log.append(trade)
            print(f"📉 SELL @ {current_price:.2f} (conf: {confidence:.3f})")
            
        elif action == 'close' and self.position != 0:
            # Fermer position
            pnl = (current_price - self.last_price) * self.position if self.last_price else 0
            trade = {
                'timestamp': datetime.now().isoformat(),
                'action': 'CLOSE',
                'price': current_price,
                'pnl': pnl,
                'position': 0.0
            }
            self.trades_log.append(trade)
            print(f"🔒 CLOSE @ {current_price:.2f} (PnL: {pnl:.2f})")
            self.position = 0.0
            self.last_price = None
    
    def save_trades_log(self, output_path: str):
        """Sauvegarde le journal des trades"""
        if self.trades_log:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.trades_log, f, indent=2, ensure_ascii=False)
            print(f"📝 Journal sauvegardé: {output_path}")

def main():
    """Fonction principale pour test"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Prédiction live pour paper trading")
    parser.add_argument("--model", required=True, help="Chemin vers le modèle XGBoost")
    parser.add_argument("--scaler", help="Chemin vers le scaler (optionnel)")
    parser.add_argument("--policy", help="Chemin vers la config policy overlay (optionnel)")
    parser.add_argument("--snapshot", help="Fichier JSON avec snapshot de test")
    parser.add_argument("--output", default="trades_log.json", help="Fichier de sortie pour les trades")
    
    args = parser.parse_args()
    
    # Initialiser le prédicteur
    predictor = LivePredictor(
        model_path=args.model,
        scaler_path=args.scaler,
        policy_config=args.policy
    )
    
    # Test avec un snapshot
    if args.snapshot and os.path.exists(args.snapshot):
        with open(args.snapshot, 'r') as f:
            snapshot = json.load(f)
        
        print("🔮 Prédiction sur snapshot de test...")
        decision = predictor.predict(snapshot)
        print(f"   Décision: {decision}")
        
        # Simuler le trade
        predictor.simulate_trade(snapshot, decision)
        
        # Sauvegarder le journal
        predictor.save_trades_log(args.output)
    
    else:
        print("💡 Usage: python predict_live.py --model model.json --snapshot test_snapshot.json")
        print("   Ou utilisez l'API: predictor.predict(snapshot_dict)")

if __name__ == "__main__":
    main()