# 🚀 MIA IA SYSTEM - DATASET ML

Ce dossier contient le pipeline complet pour construire et entraîner des modèles ML sur les données de marché MIA IA System.

## 📁 Structure

```
DATASET/
├── build_dataset.py          # Construction du dataset depuis JSONL
├── analyze_dataset.py        # Analyse et validation du dataset
├── train_baseline.py         # Entraînement des modèles XGBoost
├── run_ml_pipeline.py        # Pipeline complet automatisé
├── README.md                 # Ce fichier
├── dataset_20251002_20251003.parquet  # Dataset final (généré)
├── analysis/                 # Rapports d'analyse (généré)
├── models/                   # Modèles entraînés (généré)
└── results/                  # Résultats et visualisations (généré)
```

## 🎯 Objectifs

1. **Assembler** les données JSONL des 2 et 3 octobre 2025
2. **Nettoyer** avec forward-fill limité et masques de disponibilité
3. **Générer** des labels pour horizon H=5 (direction, touch VWAP, breakouts)
4. **Entraîner** des modèles baseline XGBoost
5. **Valider** la qualité et détecter les fuites temporelles

## 🚀 Utilisation Rapide

### Installation des Dépendances
```bash
cd DATASET
python install_rl_deps.py  # Installe stable-baselines3, torch, etc.
```

### Pipeline Complet (Recommandé)
```bash
cd DATASET
python run_ml_pipeline.py
```

### Étapes Individuelles
```bash
# 1. Construction du dataset
python build_dataset.py

# 2. Analyse du dataset
python analyze_dataset.py

# 3. Entraînement des modèles ML (XGBoost + LightGBM + CatBoost)
python train_baseline.py --target y_dir_h
python train_baseline.py --target y_touch_vwap

# 4. Entraînement des modèles RL
python train_ppo.py      # Actions discrètes (FLAT/LONG/SHORT)
python train_sac.py      # Actions continues (sizing -1 à +1)

# 5. Comparaison de tous les modèles
python compare_models.py

# 6. Prédiction en temps réel
python predict_live.py
```

### Options Avancées
```bash
# Ignorer certaines étapes
python run_ml_pipeline.py --skip-analysis --skip-training

# Forcer l'exécution malgré les erreurs
python run_ml_pipeline.py --force

# Entraîner seulement certains modèles
python train_baseline.py --models xgb,lgb  # Seulement XGBoost et LightGBM
```

## 📊 Features Disponibles

### Features Brutes (91 features)
- **OHLC**: o, h, l, c
- **VWAP**: v, up1, dn1, up2, dn2, up3, dn3
- **Volume & Delta**: v, bidvol, askvol, cum_delta_day, cum_delta_session
- **NBCV**: ask_volume, bid_volume, delta, trades, pressure, pressure_smooth
- **MenthorQ Gamma**: gex_1 à gex_10, hvl, call_resistance, put_support
- **Blind Spots**: blind_spot_0 à blind_spot_8
- **VVA**: vah, val, vpoc, pvah, pval, ppoc
- **PVWAP**: pvwap, pv_up1, pv_dn1, pv_up2, pv_dn2
- **Volatilité**: vix, atr
- **Corrélation**: cc
- **DOM**: quote_bid, quote_ask, has_l1, match_L1, depth_imbalance

### Features Engineered (25 features)
- Distance VWAP normalisée par ATR
- Volume Pressure et Delta Pressure
- VIX/ATR Ratio
- Correlation Strength
- Distance PVWAP
- VVA Position
- DOM Imbalance
- Trade/Volume Imbalance
- Price Momentum
- ATR Normalized Range
- VVA Width
- PVWAP Deviation
- Time Context (cyclical encoding)
- Session Context
- Gamma Wall Proximity
- Blind Spot Density
- Pressure Smooth (EMA)
- Cumulative Delta Trend
- Data Completeness

### Labels Générés (6 targets)
- **y_dir_h**: Direction future H=5 (3 classes: 1, 0, -1)
- **y_touch_vwap**: Touch VWAP dans H=5 (binaire)
- **y_touch_up1**: Touch VWAP+1σ dans H=5 (binaire)
- **y_touch_dn1**: Touch VWAP-1σ dans H=5 (binaire)
- **y_breakout_up_h**: Breakout Up avec pression > 0.4 (binaire)
- **y_breakout_dn_h**: Breakout Down avec pression < -0.4 (binaire)

## 🔧 Configuration

### Paramètres Modifiables dans `build_dataset.py`
```python
BASE_DIR = r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\OCTOBRE"
YMD_LIST = ["20251002", "20251003"]
H = 5                      # horizon en barres/minutes
RET_NEUTRAL_THR_ATR = 0.10 # zone neutre direction
PRESS_UP_THR = 0.40        # seuil pression breakout up
PRESS_DN_THR = -0.40       # seuil pression breakout down
```

### Paramètres des Modèles ML
```python
# XGBoost
XGB_PARAMS = {
    'n_estimators': 400,
    'max_depth': 5,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 1e-3,
    'reg_lambda': 1e-2,
    'random_state': 42,
    'n_jobs': -1
}

# LightGBM
LGB_PARAMS = {
    'objective': 'binary',
    'n_estimators': 600,
    'learning_rate': 0.05,
    'num_leaves': 31,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'class_weight': 'balanced'
}

# CatBoost
CATBOOST_PARAMS = {
    'iterations': 1000,
    'learning_rate': 0.03,
    'depth': 6,
    'l2_leaf_reg': 3,
    'bootstrap_type': 'Bayesian'
}
```

### Paramètres des Modèles RL
```python
# PPO (Actions Discrètes)
PPO_PARAMS = {
    'n_steps': 2048,
    'batch_size': 256,
    'learning_rate': 3e-4,
    'gamma': 0.99,
    'gae_lambda': 0.95,
    'clip_range': 0.2,
    'ent_coef': 0.0,
    'vf_coef': 0.5
}

# SAC (Actions Continues)
SAC_PARAMS = {
    'learning_rate': 3e-4,
    'buffer_size': 100_000,
    'batch_size': 256,
    'tau': 0.005,
    'gamma': 0.99,
    'train_freq': 64,
    'gradient_steps': 64,
    'learning_starts': 1000,
    'ent_coef': 'auto'
}
```

## 📈 Résultats Attendus

### Métriques de Performance
- **AUC**: Area Under Curve (objectif > 0.6)
- **AP**: Average Precision (objectif > 0.3)
- **Classification Report**: Precision, Recall, F1-score

### Visualisations Générées
- Matrices de confusion
- Courbes ROC et Precision-Recall
- Importance des features
- Distribution des labels
- Matrice de corrélation
- Disponibilité des données

## 🛡️ Qualité et Validation

### Détection de Fuites Temporelles
- Vérification de l'ordre temporel par symbole
- Détection de colonnes futures accidentelles
- Corrélations suspectes avec les labels

### Masques de Disponibilité
- `avail_nbcv`: Disponibilité des données NBCV
- `avail_dom`: Disponibilité des données DOM
- `avail_vwap`: Disponibilité des données VWAP
- `avail_pvwap`: Disponibilité des données PVWAP
- `avail_vva`: Disponibilité des données VVA
- `avail_gamma`: Disponibilité des données Gamma
- `avail_blind`: Disponibilité des données Blind Spots

### Forward-Fill Limité
- **Colonnes lentes** (Gamma, Blind Spots, VVA, PVWAP): forward-fill limit=10
- **Colonnes rapides** (DOM, NBCV, Trades): pas de forward-fill

## 🔍 Dépannage

### Erreurs Communes

1. **"Dataset non trouvé"**
   - Vérifiez que `build_dataset.py` a été exécuté avec succès
   - Vérifiez le chemin dans `DATASET_PATH`

2. **"Aucun fichier JSONL trouvé"**
   - Vérifiez que les données sont dans `DATA_SIERRA_CHART/DATA_2025/OCTOBRE`
   - Vérifiez les dates dans `YMD_LIST`

3. **"Packages manquants"**
   ```bash
   pip install pandas numpy scikit-learn xgboost matplotlib seaborn pyarrow
   ```

4. **"Pas assez d'échantillons"**
   - Vérifiez que les données contiennent suffisamment de lignes
   - Ajustez `H` (horizon) si nécessaire

### Logs et Debug
- Les logs détaillés sont affichés dans la console
- Les rapports sont sauvegardés dans `analysis/` et `results/`
- Utilisez `--force` pour continuer malgré les erreurs

## 📚 Prochaines Étapes

1. **Optimisation des hyperparamètres** avec Optuna ou GridSearch
2. **Features engineering avancées** (lag features, rolling statistics)
3. **Modèles plus sophistiqués** (LightGBM, CatBoost, Neural Networks)
4. **Validation croisée temporelle** plus robuste
5. **Backtesting** des stratégies basées sur les prédictions

## 🤝 Support

Pour toute question ou problème :
1. Vérifiez les logs d'erreur
2. Consultez les rapports générés dans `analysis/`
3. Vérifiez la configuration des paramètres
4. Utilisez `--force` pour diagnostiquer les problèmes

---

**MIA IA System** - Pipeline ML pour données de marché haute fréquence
