# 🔧 SPECS TECHNIQUES - IMPLÉMENTATION ML

**Date**: 18 Nov 2025  
**Focus**: 3 Modèles Prioritaires avec specs détaillées

---

## 🎯 MODÈLE #1: STOP HUNT PREDICTOR

### Objectif Business
Éviter les 17 stop hunts/jour qui coûtent -$2,118 (51% des pertes totales)

### Objectif ML
**Classifier binaire**: Prédire si un trade risque un stop hunt dans les 2 prochaines minutes

### Features Spécifiques (15-20)

**Groupe 1: Distance aux zones dangereuses**
```python
# Features à calculer
features = {
    # Distance à HVL (zone de liquidité haute)
    'dist_hvl_ticks': abs(price - hvl) / tick_size,
    'dist_hvl_atr': abs(price - hvl) / atr,
    
    # Distance aux GEX walls
    'dist_nearest_gamma_wall_ticks': min([abs(price - gex) for gex in gamma_walls]),
    'dist_call_wall_ticks': abs(price - call_resistance),
    'dist_put_wall_ticks': abs(price - put_support),
    
    # Distance aux blind spots
    'dist_nearest_blind_spot': min([abs(price - bs) for bs in blind_spots]),
    
    # Dans zone dangereuse?
    'in_gamma_zone': 1 if within_5_ticks_of_gamma else 0,
    'in_hvl_zone': 1 if within_10_ticks_of_hvl else 0,
}
```

**Groupe 2: DOM Indicators**
```python
features.update({
    # Imbalance côté opposé au trade
    'opposite_side_imbalance': ask_depth / bid_depth if signal.direction == 'LONG' else bid_depth / ask_depth,
    
    # Spike récent dans orderbook
    'dom_bid_spike_30s': (current_bid_depth - avg_bid_depth_30s) / std_bid_depth_30s,
    'dom_ask_spike_30s': (current_ask_depth - avg_ask_depth_30s) / std_ask_depth_30s,
    
    # Absorption récente
    'absorption_indicator': detect_large_orders_absorbed_last_30s(),
})
```

**Groupe 3: Volume Profile & Flow**
```python
features.update({
    # Volume profile imbalance près du niveau
    'volume_imbalance_at_level': get_volume_imbalance_at_price(entry_price),
    
    # Delta burst opposé
    'recent_opposite_delta_burst': max_opposite_delta_last_60s,
    
    # Time since last sweep de cette zone
    'seconds_since_last_sweep': time_since_last_liquidity_sweep(entry_price, range=20_ticks),
})
```

**Groupe 4: Timing & Context**
```python
features.update({
    # Session timing (opening range = plus de sweeps)
    'session_progress': elapsed_seconds / total_session_seconds,
    'in_opening_range': 1 if elapsed_seconds < 15*60 else 0,  # Premiers 15min
    
    # Volatility spike récent
    'atr_spike_ratio': current_atr / avg_atr_5min,
    
    # Price action récent
    'candles_since_reversal': bars_since_last_direction_change,
})
```

### Labels

```python
def label_stop_hunt(trade_record):
    """
    Label un trade comme stop hunt ou safe.
    
    Critères stop hunt:
    1. SL touché
    2. Duration < 120 secondes
    3. Prix a reversé dans direction opposée dans 30s après SL
    4. Trade aurait été gagnant si tenu 2min de plus
    """
    if not trade_record['sl_hit']:
        return 0  # SAFE
    
    if trade_record['duration_seconds'] >= 120:
        return 0  # SAFE (pas un hunt si > 2min)
    
    # Vérifier reverse après SL
    sl_time = trade_record['sl_timestamp']
    post_sl_prices = get_prices_after(sl_time, window=30)
    
    if trade_record['direction'] == 'LONG':
        # Long stopped out, vérifier si prix a remonté
        max_after_sl = max(post_sl_prices)
        if max_after_sl > trade_record['entry_price'] + trade_record['tp_distance']:
            return 1  # STOP HUNT
    else:
        # Short stopped out, vérifier si prix a baissé
        min_after_sl = min(post_sl_prices)
        if min_after_sl < trade_record['entry_price'] - trade_record['tp_distance']:
            return 1  # STOP HUNT
    
    return 0  # SAFE (juste un loss normal)
```

### Modèle

```python
from lightgbm import LGBMClassifier

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
    'min_data_in_leaf': 20,  # Important: éviter overfitting sur 450 trades
    'lambda_l1': 0.1,
    'lambda_l2': 0.1,
    'verbose': -1
}

model = LGBMClassifier(**params)
```

### Validation

**Métrique principale**: **Precision sur classe RISK**
- On préfère 80% precision (bloquer les vrais stop hunts) vs 100% recall
- Mieux vaut laisser passer quelques trades OK que prendre des stop hunts

**Stratégie validation:**
```python
from sklearn.model_selection import TimeSeriesSplit

# 5-fold temporel sur 10 jours
tscv = TimeSeriesSplit(n_splits=5)

for train_idx, val_idx in tscv.split(X):
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
    
    model.fit(X_train, y_train)
    
    # Évaluer
    y_pred = model.predict_proba(X_val)[:, 1]
    
    # Seuil optimal = maximize (precision * (1 - stop_hunts_missed))
    best_threshold = find_optimal_threshold(y_val, y_pred)
```

### Intégration

```python
class StopHuntPredictor:
    def __init__(self, model_path):
        self.model = load_lightgbm_model(model_path)
        self.threshold = 0.75  # Conservative
    
    def predict_risk(self, snapshot: dict, signal: TradingSignal) -> dict:
        """
        Retourne risque de stop hunt.
        
        Returns:
            {
                'risk_score': 0.0-1.0,
                'action': 'BLOCK' | 'WAIT' | 'SAFE',
                'reason': str
            }
        """
        # Feature engineering
        features = self._engineer_stop_hunt_features(snapshot, signal)
        
        # Prédiction
        risk_score = self.model.predict_proba([features])[0][1]
        
        # Décision
        if risk_score > self.threshold:
            return {
                'risk_score': risk_score,
                'action': 'BLOCK',
                'reason': f'High stop hunt risk: {risk_score:.2%}'
            }
        elif risk_score > 0.55:
            return {
                'risk_score': risk_score,
                'action': 'WAIT',
                'reason': f'Moderate risk, wait 30s: {risk_score:.2%}'
            }
        else:
            return {
                'risk_score': risk_score,
                'action': 'SAFE',
                'reason': f'Low risk: {risk_score:.2%}'
            }
```

---

## 🌐 MODÈLE #2: REGIME DETECTOR

### Objectif Business
Éviter ES quand il est en régime pourri (27% WR vs 37% pour NQ)

### Objectif ML
**Multi-class classifier**: Identifier 8-10 régimes de marché distincts

### Approach: Clustering puis Classification

**Phase 1: Découverte des régimes (Unsupervised)**
```python
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Features pour clustering
regime_features = [
    # Volatility
    'atr', 'atr_ratio', 'volatility_regime_cont',
    
    # Trend
    'd_vwap_ticks', 'd_pvwap_ticks',
    'distance_to_high_pct', 'distance_to_low_pct',
    
    # Volume/Delta
    'cum_delta_session', 'volume', 'delta_intensity',
    
    # Structure
    'day_range_pct', 'position_in_range',
    
    # Options flow
    'gamma_side', 'dist_nearest_gamma_wall',
]

# Normaliser
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X[regime_features])

# Cluster
kmeans = KMeans(n_clusters=8, random_state=42)
regime_labels = kmeans.fit_predict(X_scaled)

# Analyser chaque régime
for regime_id in range(8):
    regime_data = trades[regime_labels == regime_id]
    print(f"Regime {regime_id}:")
    print(f"  N trades: {len(regime_data)}")
    print(f"  WR: {regime_data['win'].mean():.1%}")
    print(f"  Avg P&L: ${regime_data['pnl'].mean():.2f}")
    print(f"  Characteristics: {get_regime_stats(regime_data)}")
```

**Phase 2: Nommer les régimes**
```python
# Après analyse, on pourrait avoir:
regime_names = {
    0: 'TRENDING_BULL_HIGH_VOL',     # Meilleur pour LONG momentum
    1: 'TRENDING_BEAR_HIGH_VOL',     # Meilleur pour SHORT momentum
    2: 'RANGE_TIGHT',                # Éviter (chop)
    3: 'RANGE_WIDE',                 # Bon pour reversals
    4: 'BREAKOUT_PENDING',           # Attendre confirmation
    5: 'CHOP_AVOID',                 # NE PAS TRADER
    6: 'VOLATILITY_EXPANSION',       # Bon pour trends
    7: 'GAMMA_PIN',                  # Range trading seulement
}
```

**Phase 3: Classifier (Supervised)**
```python
# Maintenant qu'on a les labels, entraîner classifier
from lightgbm import LGBMClassifier

regime_model = LGBMClassifier(
    objective='multiclass',
    num_class=8,
    learning_rate=0.05,
    num_leaves=31,
    max_depth=6
)

regime_model.fit(X[regime_features], regime_labels)
```

### Utilisation

```python
class RegimeDetector:
    def __init__(self, model_path):
        self.model = load_model(model_path)
        self.regime_strategies = {
            'TRENDING_BULL_HIGH_VOL': ['gamma_wall_break', 'momentum_long'],
            'TRENDING_BEAR_HIGH_VOL': ['gamma_wall_break', 'momentum_short'],
            'RANGE_TIGHT': [],  # Skip trading
            'RANGE_WIDE': ['liquidity_sweep_reversal', 'vwap_bounce'],
            'CHOP_AVOID': [],  # Skip trading
            # ...
        }
    
    def detect_regime(self, snapshot: dict) -> dict:
        features = extract_regime_features(snapshot)
        regime_id = self.model.predict([features])[0]
        regime_probs = self.model.predict_proba([features])[0]
        
        regime_name = self.regime_names[regime_id]
        confidence = regime_probs[regime_id]
        
        return {
            'regime': regime_name,
            'confidence': confidence,
            'optimal_strategies': self.regime_strategies[regime_name],
            'should_trade': len(self.regime_strategies[regime_name]) > 0
        }
    
    def should_trade_symbol(self, symbol: str, snapshot: dict) -> bool:
        """
        Décision spéciale pour ES: bloquer en mauvais régimes.
        """
        if symbol != 'ES':
            return True  # NQ/RTY OK toujours
        
        regime_info = self.detect_regime(snapshot)
        
        # ES seulement en régimes favorables
        favorable_regimes = [
            'TRENDING_BULL_HIGH_VOL',
            'TRENDING_BEAR_HIGH_VOL',
            'VOLATILITY_EXPANSION'
        ]
        
        return regime_info['regime'] in favorable_regimes
```

---

## 📏 MODÈLE #3: MAGNITUDE PREDICTOR

### Objectif Business
Adapter position size selon magnitude attendue du mouvement

### Objectif ML
**Multi-class classifier OU Régression**: Prédire amplitude du mouvement

### Option A: Classification en 4 classes

```python
def label_magnitude(trade_record):
    """
    Labellise l'amplitude réelle du mouvement.
    """
    max_favorable_excursion_ticks = trade_record['mfe_ticks']
    
    if max_favorable_excursion_ticks < 10:
        return 0  # CHOP
    elif max_favorable_excursion_ticks < 20:
        return 1  # SMALL
    elif max_favorable_excursion_ticks < 50:
        return 2  # MEDIUM
    else:
        return 3  # BIG

# Classes
magnitude_classes = {
    0: 'CHOP',     # < 10 ticks (éviter)
    1: 'SMALL',    # 10-20 ticks (position normale)
    2: 'MEDIUM',   # 20-50 ticks (1.5x position)
    3: 'BIG',      # 50+ ticks (2x position)
}
```

### Option B: Régression

```python
from lightgbm import LGBMRegressor

# Target: MFE en ticks
y = trades['mfe_ticks']

model = LGBMRegressor(
    objective='regression',
    metric='mae',  # Mean Absolute Error
    learning_rate=0.05
)

model.fit(X, y)
```

### Features Spécifiques

```python
magnitude_features = [
    # Momentum indicators
    'tick_momentum', 'tick_rate_3s', 'atr_ratio',
    
    # Volume
    'volume', 'delta_intensity', 'cum_delta_session',
    
    # Structure
    'distance_to_high_pct', 'distance_to_low_pct',
    'd_vwap_ticks', 'd_vpoc_ticks',
    
    # Options flow (direction force)
    'gamma_side', 'dist_call_wall', 'dist_put_wall',
    
    # DOM
    'depth_imbalance', 'pressure_strength',
    
    # Recent price action
    'upper_wick_ticks', 'lower_wick_ticks',
    'total_range_ticks'
]
```

### Utilisation

```python
class MagnitudePredictor:
    def __init__(self, model_path, use_classification=True):
        self.model = load_model(model_path)
        self.use_classification = use_classification
    
    def predict(self, snapshot: dict) -> dict:
        features = extract_magnitude_features(snapshot)
        
        if self.use_classification:
            magnitude_class = self.model.predict([features])[0]
            confidence = self.model.predict_proba([features])[0].max()
            
            return {
                'magnitude': ['CHOP', 'SMALL', 'MEDIUM', 'BIG'][magnitude_class],
                'confidence': confidence,
                'position_multiplier': [0, 1.0, 1.5, 2.0][magnitude_class],
                'skip_trade': magnitude_class == 0  # CHOP
            }
        else:
            predicted_ticks = self.model.predict([features])[0]
            
            return {
                'predicted_ticks': predicted_ticks,
                'tp_suggestion': int(predicted_ticks * 0.7),  # TP à 70% du mouvement prédit
                'skip_trade': predicted_ticks < 10
            }
```

---

## 🔄 PIPELINE D'INTÉGRATION

### Architecture Globale

```python
class MLTradingPipeline:
    def __init__(self):
        self.stop_hunt_predictor = StopHuntPredictor("models/stop_hunt.pkl")
        self.regime_detector = RegimeDetector("models/regime.pkl")
        self.magnitude_predictor = MagnitudePredictor("models/magnitude.pkl")
    
    def process_signal(self, signal: TradingSignal, snapshot: dict) -> dict:
        """
        Pipeline complet ML:
        1. Regime check (skip bad regimes)
        2. Stop hunt check (VETO)
        3. Magnitude prediction (position sizing)
        
        Returns:
            {
                'should_trade': bool,
                'position_size': int,
                'tp_distance': int,
                'reason': str
            }
        """
        
        # 1. REGIME CHECK (ES only)
        if signal.symbol == 'ES':
            if not self.regime_detector.should_trade_symbol('ES', snapshot):
                return {
                    'should_trade': False,
                    'reason': 'ES in unfavorable regime'
                }
        
        # 2. STOP HUNT CHECK (VETO absolu)
        stop_hunt_result = self.stop_hunt_predictor.predict_risk(snapshot, signal)
        
        if stop_hunt_result['action'] == 'BLOCK':
            return {
                'should_trade': False,
                'reason': stop_hunt_result['reason']
            }
        
        if stop_hunt_result['action'] == 'WAIT':
            return {
                'should_trade': False,
                'reason': 'Wait 30s for stop hunt risk to clear'
            }
        
        # 3. MAGNITUDE PREDICTION (position sizing)
        magnitude_result = self.magnitude_predictor.predict(snapshot)
        
        if magnitude_result['skip_trade']:
            return {
                'should_trade': False,
                'reason': 'CHOP detected - low magnitude expected'
            }
        
        # ALL CLEAR - EXECUTE
        return {
            'should_trade': True,
            'position_size': magnitude_result['position_multiplier'],
            'tp_distance': magnitude_result.get('tp_suggestion', 15),
            'confidence': stop_hunt_result['risk_score'],  # Inverser: low risk = high confidence
            'reason': f"All checks passed - {magnitude_result['magnitude']} move expected"
        }
```

---

## 📊 METRICS & MONITORING

### Features Importance à tracker

```python
# Après training, sauvegarder
feature_importance = pd.DataFrame({
    'feature': model.feature_name_,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

print("Top 10 features:")
print(feature_importance.head(10))
```

### Performance Metrics

```python
class MLMonitor:
    def track_model_performance(self, model_name: str, predictions: list, actuals: list):
        """
        Track performance en production.
        """
        metrics = {
            'accuracy': accuracy_score(actuals, predictions),
            'precision': precision_score(actuals, predictions, average='weighted'),
            'recall': recall_score(actuals, predictions, average='weighted'),
            'f1': f1_score(actuals, predictions, average='weighted'),
            
            # Business metrics
            'stop_hunts_blocked': count_stop_hunts_blocked(predictions),
            'false_blocks': count_false_blocks(predictions, actuals),
            'pnl_improvement': calculate_pnl_delta(predictions, actuals)
        }
        
        log_to_discord(f"📊 {model_name} Performance:\n{metrics}")
```

---

## 🎯 ORDRE D'IMPLÉMENTATION

### Semaine 1: Stop Hunt Predictor
1. **Jour 1-2**: Feature engineering + labeling
2. **Jour 3-4**: Training + validation
3. **Jour 5**: Intégration + backtest
4. **Jour 6-7**: Paper trading

### Semaine 2: Regime Detector
1. **Jour 1-2**: Clustering analysis
2. **Jour 3**: Training classifier
3. **Jour 4-5**: Intégration + backtest
4. **Jour 6-7**: Production

### Semaine 3: Magnitude Predictor
1. **Jour 1-2**: Feature engineering + labeling
2. **Jour 3-4**: Training (classifier ou regressor)
3. **Jour 5-7**: Intégration + production

---

## ✅ CHECKLIST AVANT TRAINING

- [ ] Data des 10 jours extraite en CSV
- [ ] Labels créés (stop hunt / magnitude / regime)
- [ ] Features engineered calculées
- [ ] Train/val/test split défini
- [ ] Hyperparams de base définis
- [ ] Validation strategy choisie (TimeSeriesSplit?)
- [ ] Metrics à optimiser définies
- [ ] Seuils de décision définis
- [ ] Pipeline d'intégration designé
- [ ] Monitoring plan établi

**Prêt à coder?**
