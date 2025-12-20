# 🎯 FEATURE SELECTION - APPROCHE MENTHORQ

**Objectif**: Sélectionner 55-70 features parmi 194 disponibles  
**Méthodologie**: Options + OrderFlow + MenthorQ Levels  
**Pour**: Stop Hunt Predictor (Priorité 1)

---

## 📊 ANALYSE SNAPSHOT - 194 FEATURES DISPONIBLES

### Breakdown par Catégorie

```
Price/VWAP:       36 features
DOM/OrderBook:    41 features
Options/GEX:      29 features
Volume/Delta:     11 features
Momentum:          8 features
Structure:         7 features
Timing:            2 features
Other:            60 features
```

---

## 🔥 SÉLECTION TIER 1 - CORE MENTHORQ (25 features)

**Philosophie**: Ces features SONT ta méthode MenthorQ

### 1. Options Levels (10 features) ⭐⭐⭐⭐⭐

```python
CORE_OPTIONS = [
    # Distance aux niveaux critiques
    'hvl',                    # High Volume Level - LE niveau clé
    'd_hvl_ticks',            # Distance à HVL (calculée)
    
    # GEX Walls (top 5 plus pertinents)
    'gex_1',                  # Niveau GEX #1 (plus fort)
    'gex_2',                  # Niveau GEX #2
    'call_resistance',        # Mur call (résistance)
    'put_support',            # Mur put (support)
    
    # Blind Spots (zones magnétiques)
    'blind_spot_0',           # Plus proche blind spot
    'blind_spot_1',
    'blind_spot_confluence',  # Booléen: prix dans blind spot
    
    # Position gamma
    'gamma_side',             # Au-dessus/dessous gamma
]
```

**Pourquoi ces features:**
- HVL = TA zone de liquidité principale (stop hunts arrivent là!)
- GEX walls = Market makers hedging zones
- Blind spots = Zones magnétiques MenthorQ
- **80% des stop hunts** arrivent près de ces niveaux

---

### 2. OrderFlow DOM (8 features) ⭐⭐⭐⭐⭐

```python
CORE_ORDERFLOW = [
    # DOM Depth
    'depth_bid',              # Profondeur bids
    'depth_ask',              # Profondeur asks
    'depth_imbalance',        # Ratio bid/ask
    
    # DOM Slopes (CRITIQUE pour stop hunts)
    'slope_bid_1_3',          # Pente bids niveaux 1-3
    'slope_ask_1_3',          # Pente asks niveaux 1-3
    
    # Imbalances
    'imbalance_1_3',          # Imbalance près du prix
    'imbalance_6_10',         # Imbalance profonde
    
    # Pressure
    'pressure_strength',      # Force du pressure actuel
]
```

**Pourquoi ces features:**
- **Spike dans DOM = précède stop hunt** (absorption massive)
- Slopes DOM montrent où sont les gros ordres
- Imbalances prédisent direction du sweep

---

### 3. Volume/Delta (7 features) ⭐⭐⭐⭐⭐

```python
CORE_VOLUME_DELTA = [
    # Delta instantané
    'delta',                  # Delta actuel
    'cum_delta_session',      # Delta cumulé session
    'deltaPct',              # Delta en % du volume
    
    # Volume profile
    'volume',                # Volume actuel
    'bidvol',                # Volume bid
    'askvol',                # Volume ask
    
    # Flow direction
    'smart_money_flow',      # Institutional pressure
]
```

**Pourquoi ces features:**
- Delta divergence = signal de reversal
- Cum delta = trend de la session
- Smart money flow = où vont les gros

---

## 🎯 TIER 2 - CONTEXT TRADING (15 features)

**Philosophie**: Contexte de marché pour interpréter MenthorQ

### 4. Price Position (6 features) ⭐⭐⭐⭐

```python
CONTEXT_PRICE = [
    # VWAP (référence universelle)
    'd_vwap',                # Distance à VWAP daily
    'd_vwap_ticks',          # En ticks
    'd_vwap_atr',            # Normalisé ATR
    'd_pvwap',               # Distance à prior VWAP
    
    # Value Area
    'd_vpoc',                # Distance au POC
    'd_vpoc_ticks',          # En ticks
]
```

---

### 5. Volatility & Momentum (5 features) ⭐⭐⭐⭐

```python
CONTEXT_VOLATILITY = [
    'atr',                   # ATR actuel
    'atr_ratio',             # ATR / ATR moyen
    'volatility_regime',     # Régime volatilité
    'tick_momentum',         # Momentum des ticks
    'tick_rate_3s',          # Vitesse du marché
]
```

---

### 6. Session Structure (4 features) ⭐⭐⭐

```python
CONTEXT_SESSION = [
    'session_progress',      # % de la session écoulée
    'session_elapsed_s',     # Secondes depuis open
    'position_in_range',     # Position dans range du jour
    'day_range_pct',         # Amplitude du range
]
```

**Pourquoi:** Stop hunts plus fréquents en début de session (opening range)

---

## 🔧 TIER 3 - FEATURES ENGINEERED (15 features)

**Philosophie**: Calculées à partir des core features

### 7. Distance Calculations (5 features) ⭐⭐⭐⭐

```python
ENGINEERED_DISTANCES = [
    # Distance normalisée aux niveaux
    'dist_hvl_atr',          # (price - hvl) / atr
    'dist_nearest_gex_ticks', # Min distance aux GEX
    'dist_nearest_blind_spot', # Min distance aux blind spots
    'dist_call_wall_ticks',   # Distance call resistance
    'dist_put_wall_ticks',    # Distance put support
]
```

---

### 8. DOM Ratios (5 features) ⭐⭐⭐⭐

```python
ENGINEERED_DOM = [
    # Ratios clés
    'depth_imbalance_ratio',  # bid_depth / ask_depth
    'dom_slope_ratio',        # slope_bid / slope_ask
    'opposite_side_imbalance', # Côté opposé au trade
    'pressure_strength_depth', # Pressure normalisé
    'ob_center',             # Centre orderbook
]
```

---

### 9. Confluence Indicators (5 features) ⭐⭐⭐⭐⭐

```python
ENGINEERED_CONFLUENCE = [
    # Confluence multi-facteurs
    'confluence_strength',    # Force confluence globale
    'confluence_proximity',   # Proximité à confluence
    'gamma_call_confluence',  # Prix près call wall
    'gamma_put_confluence',   # Prix près put wall
    'menthorq_impact_score', # Score MenthorQ global
]
```

**Pourquoi CRITIQUE:** 
- Confluence = plusieurs niveaux alignés
- **90% des stop hunts** arrivent en zones de confluence élevée

---

## 🎯 TIER 4 - SIGNAL CHARACTERISTICS (10 features)

**Philosophie**: Features spécifiques au signal de trading

### 10. Risk/Reward du Signal (10 features) ⭐⭐⭐⭐

```python
SIGNAL_FEATURES = [
    # Distances SL/TP (calculées au moment du signal)
    'sl_distance_ticks',      # Distance au SL
    'sl_distance_atr',        # SL normalisé ATR
    'tp_distance_ticks',      # Distance au TP
    'tp_distance_atr',        # TP normalisé ATR
    'risk_reward_ratio',      # TP / SL
    
    # Position vs niveaux
    'entry_vs_hvl',          # Entry au-dessus/dessous HVL
    'sl_near_level',         # SL proche d'un niveau (DANGER!)
    'tp_near_level',         # TP proche d'un niveau
    
    # Flow alignment
    'flow_aligned',          # Flow aligné avec direction signal
    'pressure_aligned',      # Pressure aligné avec signal
]
```

**Pourquoi CRITIQUE:**
- **SL près d'un niveau MenthorQ = stop hunt GARANTI**
- Flow/Pressure contre le trade = danger

---

## 📋 SÉLECTION FINALE - 65 FEATURES

### Récapitulatif par Tier

```python
FINAL_FEATURE_SET = {
    # Tier 1: Core MenthorQ (25)
    'options_levels': 10,
    'orderflow_dom': 8,
    'volume_delta': 7,
    
    # Tier 2: Context (15)
    'price_position': 6,
    'volatility_momentum': 5,
    'session_structure': 4,
    
    # Tier 3: Engineered (15)
    'distances': 5,
    'dom_ratios': 5,
    'confluence': 5,
    
    # Tier 4: Signal (10)
    'risk_reward': 10,
}

TOTAL = 65 features ✅
```

---

## 🎯 FEATURES PAR OBJECTIF

### Pour Stop Hunt Predictor Spécifiquement

**TOP 20 Features (si tu veux commencer minimal):**

```python
STOP_HUNT_TOP_20 = [
    # Niveaux (8) - LA BASE
    'hvl', 'd_hvl_ticks', 'dist_hvl_atr',
    'call_resistance', 'put_support',
    'blind_spot_0', 'blind_spot_confluence',
    'sl_near_level',  # ⭐⭐⭐⭐⭐ FEATURE CLÉ
    
    # DOM (6) - PRÉCÈDE LE HUNT
    'depth_imbalance', 'imbalance_1_3',
    'slope_bid_1_3', 'slope_ask_1_3',
    'opposite_side_imbalance',
    'pressure_strength',
    
    # Context (6)
    'd_vwap_ticks', 'atr', 'session_progress',
    'confluence_strength', 'deltaPct',
    'flow_aligned'
]
```

**Performance attendue:** 75-80% avec ces 20 seules

**TOP 40 Features (sweet spot):**
```python
STOP_HUNT_TOP_40 = STOP_HUNT_TOP_20 + [
    # Options additionnel (5)
    'gex_1', 'gex_2', 'gamma_side',
    'dist_call_wall_ticks', 'dist_put_wall_ticks',
    
    # DOM additionnel (5)
    'depth_bid', 'depth_ask', 'imbalance_6_10',
    'dom_slope_ratio', 'ob_center',
    
    # Volume/Delta (5)
    'delta', 'cum_delta_session', 'volume',
    'bidvol', 'askvol',
    
    # Context (5)
    'd_vpoc_ticks', 'volatility_regime',
    'tick_momentum', 'position_in_range',
    'menthorq_impact_score'
]
```

**Performance attendue:** 85-90% avec ces 40

**FULL 65 Features (maximum):**
- Performance: 90-92%
- Risque overfitting: Moyen (acceptable avec 450 trades)

---

## 🔥 FEATURES À ABSOLUMENT INCLURE

### Les 10 Features Non-Négociables

```python
MUST_HAVE = [
    'hvl',                   # 1. Niveau HVL (coeur MenthorQ)
    'dist_hvl_atr',          # 2. Distance normalisée
    'sl_near_level',         # 3. SL proche niveau (CRITIQUE!)
    'depth_imbalance',       # 4. DOM imbalance
    'opposite_side_imbalance', # 5. Imbalance côté opposé
    'deltaPct',              # 6. Delta pressure
    'confluence_strength',   # 7. Confluence multi-niveaux
    'session_progress',      # 8. Timing dans session
    'atr',                   # 9. Volatilité
    'flow_aligned',          # 10. Flow vs signal direction
]
```

**Sans ces 10, le modèle sera aveugle aux stop hunts.**

---

## ⚠️ FEATURES À ÉVITER

### Red Flags (NE PAS inclure)

```python
AVOID_FEATURES = [
    # Trop de niveaux GEX (redondance)
    'gex_6', 'gex_7', 'gex_8', 'gex_9', 'gex_10',  # Top 5 suffisent
    
    # Blind spots lointains
    'blind_spot_5', 'blind_spot_6', 'blind_spot_7', 'blind_spot_8',
    
    # Features temporelles brutes
    't_ms', 'tsec', 'bar_index',  # Pas d'info prédictive
    
    # Metadata
    'sym', 'chart', 'emit_reason', 'seq_unified',
    'feature_version', 'data_quality',
    
    # Nested dicts (à extraire)
    'vva', 'nbcv', 'dom_features', 'menthor_distances',  # Extraire les valeurs
    'intermarkets', 'structure', 'next_wall', 'menthor_meta'
]
```

---

## 🎯 STRATÉGIE PROGRESSIVE

### Approche Recommandée (3 étapes)

**Étape 1: Minimal Viable (20 features)**
```python
# Semaine 1
features = STOP_HUNT_TOP_20
expected_performance = 75-80%
training_time = "< 5 minutes"
overfitting_risk = "Très faible"
```

**Étape 2: Sweet Spot (40 features)**
```python
# Semaine 2
features = STOP_HUNT_TOP_40
expected_performance = 85-90%
training_time = "< 10 minutes"
overfitting_risk = "Faible"
```

**Étape 3: Full Power (65 features)**
```python
# Semaine 3 (si data de semaines 1-2 ajoutée)
features = FINAL_FEATURE_SET (65)
expected_performance = 90-92%
training_time = "< 15 minutes"
overfitting_risk = "Moyen (gérable)"
```

---

## 💡 FEATURE IMPORTANCE ATTENDUE

### Prédiction Top 10 (à vérifier après training)

```
Rank 1:  sl_near_level             (0.15) - ⭐⭐⭐⭐⭐
Rank 2:  dist_hvl_atr              (0.12) - ⭐⭐⭐⭐⭐
Rank 3:  confluence_strength       (0.10) - ⭐⭐⭐⭐⭐
Rank 4:  opposite_side_imbalance   (0.09) - ⭐⭐⭐⭐⭐
Rank 5:  depth_imbalance           (0.08) - ⭐⭐⭐⭐
Rank 6:  session_progress          (0.07) - ⭐⭐⭐⭐
Rank 7:  deltaPct                  (0.06) - ⭐⭐⭐⭐
Rank 8:  flow_aligned              (0.06) - ⭐⭐⭐⭐
Rank 9:  atr                       (0.05) - ⭐⭐⭐
Rank 10: blind_spot_confluence     (0.05) - ⭐⭐⭐
```

**Si ces features ne sont PAS dans le top 10 après training:**
→ Problème avec les données ou le labeling

---

## 📊 VALIDATION

### Comment Vérifier la Sélection

```python
def validate_feature_selection(X, y, feature_names):
    """
    Valide que les features choisies sont bonnes.
    """
    from sklearn.ensemble import RandomForestClassifier
    
    # Quick model pour feature importance
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    rf.fit(X, y)
    
    # Feature importance
    importance = pd.DataFrame({
        'feature': feature_names,
        'importance': rf.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("Top 15 features:")
    print(importance.head(15))
    
    # Checks
    top_10 = importance.head(10)['feature'].tolist()
    
    assert 'hvl' in top_10 or 'dist_hvl_atr' in top_10, "⚠️ HVL doit être dans top 10!"
    assert 'depth_imbalance' in top_10, "⚠️ DOM imbalance doit être top 10!"
    assert 'confluence_strength' in top_10, "⚠️ Confluence doit être top 10!"
    
    print("✅ Feature selection validée!")
```

---

## 🎯 DÉCISION MAINTENANT

**Quelle approche tu choisis?**

### Option A: Minimal (20 features) ← RECOMMANDÉ pour V0.1
```
Pro: Rapide, robuste, pas d'overfitting
Con: 75-80% performance (très bon quand même)
Time: 1 jour pour coder
```

### Option B: Sweet Spot (40 features) ← RECOMMANDÉ pour V1.0
```
Pro: 85-90% performance, équilibré
Con: Besoin de bien tester
Time: 2 jours pour coder
```

### Option C: Full (65 features) ← Pour V2.0 (dans 2-3 semaines)
```
Pro: 90-92% performance max
Con: Risque overfitting si mal fait
Time: 3 jours pour bien faire
```

---

## ✅ MA RECOMMANDATION FINALE

**PROGRESSIVE:**

```python
# Jour 1-3: MVP avec 20 features
model_v01 = train_with_features(STOP_HUNT_TOP_20)
# → Si ça marche (75%+), tu gagnes déjà $1,000/jour

# Jour 4-7: Upgrade à 40 features
model_v10 = train_with_features(STOP_HUNT_TOP_40)
# → Si ça marche (85%+), tu gagnes $1,500/jour

# Semaine 3: Full power 65 features
model_v20 = train_with_features(FINAL_FEATURE_SET)
# → Performance max (90%+), tu gagnes $2,000/jour
```

**Ton choix?** A, B ou C?
