"""
🎯 STOP HUNT PREDICTOR - Exemple de Code Complet
Version: 1.0
Date: 18 Nov 2025

Code prêt à l'emploi pour prédire les stop hunts.
"""

import pandas as pd
import numpy as np
from lightgbm import LGBMClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
import pickle
from pathlib import Path
from typing import Dict, Tuple


# ═══════════════════════════════════════════════════════════════
# 1. FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════

class StopHuntFeatureEngineer:
    """
    Calcule les 15-20 features spécifiques aux stop hunts.
    """
    
    def engineer_features(self, snapshot: dict, signal: dict) -> dict:
        """
        Calcule toutes les features pour prédiction stop hunt.
        
        Args:
            snapshot: ML_READY snapshot avec toutes les features de base
            signal: Trading signal avec direction, entry, SL, TP
        
        Returns:
            Dict avec features engineered
        """
        features = {}
        
        # ─────────────────────────────────────────────────────────
        # GROUP 1: Distance aux zones dangereuses
        # ─────────────────────────────────────────────────────────
        
        mid = snapshot['mid']
        hvl = snapshot['hvl']
        atr = snapshot['atr']
        tick_size = 0.25  # NQ/ES
        
        # Distance à HVL
        features['dist_hvl_ticks'] = abs(mid - hvl) / tick_size
        features['dist_hvl_atr'] = abs(mid - hvl) / (atr if atr > 0 else 5.0)
        
        # Distance aux GEX walls
        gex_levels = [snapshot.get(f'gex_{i}', 0) for i in range(1, 11)]
        gex_distances = [abs(mid - g) / tick_size for g in gex_levels if g > 0]
        features['dist_nearest_gamma_wall_ticks'] = min(gex_distances) if gex_distances else 9999.0
        
        features['dist_call_wall_ticks'] = abs(mid - snapshot.get('call_resistance', 0)) / tick_size
        features['dist_put_wall_ticks'] = abs(mid - snapshot.get('put_support', 0)) / tick_size
        
        # Distance aux blind spots
        blind_spots = [snapshot.get(f'blind_spot_{i}', 0) for i in range(9)]
        blind_distances = [abs(mid - bs) / tick_size for bs in blind_spots if bs > 0]
        features['dist_nearest_blind_spot'] = min(blind_distances) if blind_distances else 9999.0
        
        # Zones dangereuses (booléens)
        features['in_gamma_zone'] = 1 if features['dist_nearest_gamma_wall_ticks'] < 5 else 0
        features['in_hvl_zone'] = 1 if features['dist_hvl_ticks'] < 10 else 0
        features['in_blind_spot_zone'] = 1 if features['dist_nearest_blind_spot'] < 20 else 0
        
        # ─────────────────────────────────────────────────────────
        # GROUP 2: DOM Indicators
        # ─────────────────────────────────────────────────────────
        
        dom_features = snapshot.get('dom_features', {})
        depth_bid = dom_features.get('depth_bid', 0)
        depth_ask = dom_features.get('depth_ask', 0)
        
        # Imbalance côté opposé au trade
        if signal['direction'] == 'LONG':
            features['opposite_side_imbalance'] = depth_ask / (depth_bid + 1)
        else:
            features['opposite_side_imbalance'] = depth_bid / (depth_ask + 1)
        
        # DOM imbalances
        features['dom_imbalance_1_3'] = dom_features.get('imbalance_1_3', 0)
        features['dom_imbalance_6_10'] = dom_features.get('imbalance_6_10', 0)
        
        # Slopes DOM
        features['dom_slope_bid'] = dom_features.get('slope_bid_1_3_n', 0)
        features['dom_slope_ask'] = dom_features.get('slope_ask_1_3_n', 0)
        
        # ─────────────────────────────────────────────────────────
        # GROUP 3: Volume & Flow
        # ─────────────────────────────────────────────────────────
        
        features['delta_intensity'] = abs(snapshot.get('delta', 0)) / (snapshot.get('volume', 1))
        features['cum_delta_normalized'] = snapshot.get('cum_delta_session', 0) / 1000
        
        # Pressure
        features['pressure_strength'] = snapshot.get('pressure_strength', 0)
        features['pressure_strength_atr'] = snapshot.get('pressure_strength_atr', 0)
        
        # Flow direction vs signal
        bidPct = snapshot.get('bidPct', 0.5)
        askPct = snapshot.get('askPct', 0.5)
        flow_direction = bidPct - askPct  # Positif = bullish flow
        
        if signal['direction'] == 'LONG':
            features['flow_aligned'] = 1 if flow_direction > 0 else 0
        else:
            features['flow_aligned'] = 1 if flow_direction < 0 else 0
        
        # ─────────────────────────────────────────────────────────
        # GROUP 4: Timing & Context
        # ─────────────────────────────────────────────────────────
        
        features['session_progress'] = snapshot.get('session_progress', 0)
        features['in_opening_range'] = 1 if snapshot.get('session_elapsed_s', 1000) < 900 else 0  # <15min
        
        # Volatility
        features['atr_ratio'] = snapshot.get('atr_ratio', 1.0)
        features['volatility_regime_cont'] = snapshot.get('volatility_regime_cont', 0)
        
        # Position in day range
        features['position_in_range'] = snapshot.get('position_in_range', 50)
        features['distance_to_high_pct'] = snapshot.get('distance_to_high_pct', 5)
        features['distance_to_low_pct'] = snapshot.get('distance_to_low_pct', 5)
        
        # ─────────────────────────────────────────────────────────
        # GROUP 5: Signal characteristics
        # ─────────────────────────────────────────────────────────
        
        # SL distance
        entry = signal.get('entry_price', mid)
        sl = signal.get('sl_price', entry - 15*tick_size if signal['direction']=='LONG' else entry + 15*tick_size)
        sl_distance_ticks = abs(entry - sl) / tick_size
        
        features['sl_distance_ticks'] = sl_distance_ticks
        features['sl_distance_atr'] = sl_distance_ticks * tick_size / (atr if atr > 0 else 5.0)
        
        # Risk/Reward
        tp = signal.get('tp_price', entry + 15*tick_size if signal['direction']=='LONG' else entry - 15*tick_size)
        tp_distance_ticks = abs(entry - tp) / tick_size
        features['risk_reward_ratio'] = tp_distance_ticks / (sl_distance_ticks + 0.1)
        
        return features


# ═══════════════════════════════════════════════════════════════
# 2. LABELING
# ═══════════════════════════════════════════════════════════════

def label_stop_hunt(trade_record: dict) -> int:
    """
    Labellise un trade comme stop hunt (1) ou safe (0).
    
    Critères stop hunt:
    1. SL touché
    2. Duration < 120 secondes
    3. Prix a reversé dans direction opposée après SL
    4. Le trade aurait été gagnant si tenu
    
    Args:
        trade_record: Dict avec:
            - sl_hit: bool
            - tp_hit: bool
            - duration_seconds: float
            - direction: 'LONG' | 'SHORT'
            - entry_price: float
            - tp_price: float
            - sl_price: float
            - max_price_after_sl: float (dans 30s après SL)
            - min_price_after_sl: float
    
    Returns:
        1 si stop hunt, 0 si safe
    """
    
    # Pas de SL hit = safe
    if not trade_record.get('sl_hit', False):
        return 0
    
    # Duration >= 2min = pas un hunt (juste un loss)
    if trade_record.get('duration_seconds', 999) >= 120:
        return 0
    
    # Vérifier reverse après SL
    direction = trade_record['direction']
    entry = trade_record['entry_price']
    tp = trade_record['tp_price']
    
    max_after_sl = trade_record.get('max_price_after_sl', 0)
    min_after_sl = trade_record.get('min_price_after_sl', 999999)
    
    if direction == 'LONG':
        # Long stopped out
        # Stop hunt si prix remonte au-dessus du TP
        if max_after_sl > tp:
            return 1  # STOP HUNT
    else:
        # Short stopped out
        # Stop hunt si prix descend en-dessous du TP
        if min_after_sl < tp:
            return 1  # STOP HUNT
    
    return 0  # Juste un loss normal


# ═══════════════════════════════════════════════════════════════
# 3. TRAINING
# ═══════════════════════════════════════════════════════════════

class StopHuntTrainer:
    """
    Entraîne le modèle de prédiction stop hunt.
    """
    
    def __init__(self):
        self.feature_engineer = StopHuntFeatureEngineer()
        self.model = None
        self.feature_names = None
        
    def prepare_dataset(self, trades_df: pd.DataFrame, snapshots: Dict) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prépare dataset complet avec features + labels.
        
        Args:
            trades_df: DataFrame avec historique trades
            snapshots: Dict {trade_id: snapshot}
        
        Returns:
            X (features), y (labels)
        """
        
        all_features = []
        all_labels = []
        
        for idx, trade in trades_df.iterrows():
            # Label
            label = label_stop_hunt(trade.to_dict())
            
            # Features
            snapshot = snapshots.get(trade['trade_id'], {})
            signal = {
                'direction': trade['direction'],
                'entry_price': trade['entry_price'],
                'sl_price': trade['sl_price'],
                'tp_price': trade['tp_price']
            }
            
            features = self.feature_engineer.engineer_features(snapshot, signal)
            
            all_features.append(features)
            all_labels.append(label)
        
        X = pd.DataFrame(all_features)
        y = pd.Series(all_labels)
        
        # Garder noms features
        self.feature_names = X.columns.tolist()
        
        print(f"✅ Dataset préparé:")
        print(f"   Samples: {len(X)}")
        print(f"   Features: {len(X.columns)}")
        print(f"   Stop hunts: {y.sum()} ({y.mean():.1%})")
        print(f"   Safe: {(1-y).sum()} ({(1-y).mean():.1%})")
        
        return X, y
    
    def train(self, X: pd.DataFrame, y: pd.Series):
        """
        Entraîne le modèle avec validation croisée temporelle.
        """
        
        # Params LightGBM
        params = {
            'objective': 'binary',
            'metric': 'auc',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'max_depth': 6,
            'min_data_in_leaf': 20,
            'lambda_l1': 0.1,
            'lambda_l2': 0.1,
            'verbose': -1
        }
        
        # TimeSeriesSplit pour validation temporelle
        tscv = TimeSeriesSplit(n_splits=5)
        
        cv_scores = []
        cv_precisions = []
        
        print("\n🔄 Cross-validation temporelle...")
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            # Train
            model = LGBMClassifier(**params)
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                eval_metric='auc',
                callbacks=[lgb.early_stopping(stopping_rounds=20)]
            )
            
            # Évaluer
            y_pred = model.predict(X_val)
            y_proba = model.predict_proba(X_val)[:, 1]
            
            # Métriques
            from sklearn.metrics import precision_score, roc_auc_score
            auc = roc_auc_score(y_val, y_proba)
            precision = precision_score(y_val, y_pred, zero_division=0)
            
            cv_scores.append(auc)
            cv_precisions.append(precision)
            
            print(f"   Fold {fold+1}: AUC={auc:.3f}, Precision={precision:.3f}")
        
        # Stats CV
        print(f"\n✅ CV Results:")
        print(f"   Mean AUC: {np.mean(cv_scores):.3f} ± {np.std(cv_scores):.3f}")
        print(f"   Mean Precision: {np.mean(cv_precisions):.3f} ± {np.std(cv_precisions):.3f}")
        
        # Train final sur toutes les données
        print("\n🚀 Training final model...")
        self.model = LGBMClassifier(**params)
        self.model.fit(X, y)
        
        # Feature importance
        self._print_feature_importance()
        
        return self.model
    
    def _print_feature_importance(self):
        """
        Affiche les features les plus importantes.
        """
        if self.model is None:
            return
        
        importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        print("\n📊 Top 15 features:")
        print(importance.head(15).to_string(index=False))
    
    def save_model(self, path: str):
        """
        Sauvegarde le modèle entraîné.
        """
        model_data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'feature_engineer': self.feature_engineer
        }
        
        with open(path, 'wb') as f:
            pickle.dump(model_data, f)
        
        print(f"✅ Modèle sauvegardé: {path}")


# ═══════════════════════════════════════════════════════════════
# 4. PRÉDICTION EN PRODUCTION
# ═══════════════════════════════════════════════════════════════

class StopHuntPredictor:
    """
    Prédit le risque de stop hunt en temps réel.
    """
    
    def __init__(self, model_path: str):
        """
        Charge le modèle entraîné.
        """
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.feature_names = model_data['feature_names']
        self.feature_engineer = model_data['feature_engineer']
        
        # Seuils de décision
        self.threshold_block = 0.75  # Au-dessus: BLOCK
        self.threshold_wait = 0.55   # Au-dessus: WAIT
        
        print(f"✅ StopHuntPredictor loaded from {model_path}")
    
    def predict_risk(self, snapshot: dict, signal: dict) -> dict:
        """
        Prédit le risque de stop hunt pour un signal donné.
        
        Args:
            snapshot: Snapshot ML_READY actuel
            signal: Signal de trading avec direction, entry, SL, TP
        
        Returns:
            {
                'risk_score': float (0-1),
                'action': 'BLOCK' | 'WAIT' | 'SAFE',
                'reason': str,
                'should_trade': bool
            }
        """
        
        # Feature engineering
        features = self.feature_engineer.engineer_features(snapshot, signal)
        
        # Convertir en DataFrame avec bon ordre
        features_df = pd.DataFrame([features])[self.feature_names]
        
        # Prédiction
        risk_score = self.model.predict_proba(features_df)[0][1]
        
        # Décision
        if risk_score > self.threshold_block:
            return {
                'risk_score': risk_score,
                'action': 'BLOCK',
                'reason': f'⛔ High stop hunt risk: {risk_score:.1%}',
                'should_trade': False
            }
        elif risk_score > self.threshold_wait:
            return {
                'risk_score': risk_score,
                'action': 'WAIT',
                'reason': f'⏸️ Moderate risk, wait 30s: {risk_score:.1%}',
                'should_trade': False
            }
        else:
            return {
                'risk_score': risk_score,
                'action': 'SAFE',
                'reason': f'✅ Low stop hunt risk: {risk_score:.1%}',
                'should_trade': True
            }


# ═══════════════════════════════════════════════════════════════
# 5. EXEMPLE D'UTILISATION
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    
    # ─────────────────────────────────────────────────────────
    # TRAINING
    # ─────────────────────────────────────────────────────────
    
    # 1. Charger les données
    print("📂 Chargement des données...")
    trades_df = pd.read_csv("data/trades_10days.csv")
    
    with open("data/snapshots_10days.pkl", "rb") as f:
        snapshots = pickle.load(f)
    
    # 2. Préparer dataset
    trainer = StopHuntTrainer()
    X, y = trainer.prepare_dataset(trades_df, snapshots)
    
    # 3. Entraîner
    model = trainer.train(X, y)
    
    # 4. Sauvegarder
    trainer.save_model("models/stop_hunt_predictor_v1.pkl")
    
    # ─────────────────────────────────────────────────────────
    # PRODUCTION
    # ─────────────────────────────────────────────────────────
    
    # 1. Charger predictor
    predictor = StopHuntPredictor("models/stop_hunt_predictor_v1.pkl")
    
    # 2. Utiliser sur nouveau signal
    snapshot = {
        'mid': 24913.63,
        'hvl': 25140.00,
        'atr': 5.57,
        'call_resistance': 26000.00,
        'put_support': 24000.00,
        # ... toutes les autres features
    }
    
    signal = {
        'direction': 'LONG',
        'entry_price': 24913.63,
        'sl_price': 24898.63,  # -15 ticks
        'tp_price': 24928.63   # +15 ticks
    }
    
    # 3. Prédire
    result = predictor.predict_risk(snapshot, signal)
    
    print(f"\n{result['reason']}")
    print(f"Should trade: {result['should_trade']}")
    
    # 4. Intégrer dans système de trading
    if result['should_trade']:
        # Exécuter le trade
        execute_trade(signal)
    else:
        # Bloquer ou attendre
        log_rejected_trade(signal, result['reason'])
