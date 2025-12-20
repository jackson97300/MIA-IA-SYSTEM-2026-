# 🎯 TARGET OPTIMIZATION SYSTEM

**Auteur:** MIA Trading System
**Date:** 15 novembre 2025
**Version:** 1.0.0

---

## 📋 OBJECTIF

Tester empiriquement **8 définitions de target ML différentes** et sélectionner celle qui maximise le **P&L net out-of-sample**.

**Problème actuel:** Modèle actuel T1 (binary simple) donne **+0.25t/trade** → insuffisant.

**Objectif:** Trouver une target qui donne **+1.20t/trade** (+380% amélioration).

---

## 🏗️ ARCHITECTURE

```
ml/6_TARGET_OPTIMIZATION/
├── __init__.py                    # Exports principaux
├── target_optimizer.py            # Framework complet (1500+ lignes)
├── run_optimization.py            # Script principal
├── tests/
│   ├── test_target_generators.py  # Tests unitaires targets
│   └── test_backtest_logic.py     # Tests logiques de décision
└── README.md                      # Ce fichier
```

---

## 🎯 LES 8 TARGETS

| ID | Nom | Type | Description | Seuil décision |
|----|-----|------|-------------|----------------|
| **T1** | Binary Simple | Classification | y = (pnl > 0) | P(WIN) > 0.45 |
| **T2** | Binary Strong | Classification | y = (pnl_ratio >= 0.5) | P(WIN) > 0.50 |
| **T3** | P&L Ratio | Régression | Prédit R-multiple | pred > 0.3R |
| **T4** | P&L Ticks | Régression | Prédit P&L direct | pred > 2.0t |
| **T5** | Multiclass | Multiclass | BAD/NEUTRAL/GOOD | P(GOOD) > 0.60 |
| **T6** | Quality Score | Régression | Score 0-100 | pred > 60 |
| **T7** | Expected Value | Régression | EV contextuel | pred > 1.0t |
| **T8** | Sharpe Simplified | Régression | Sharpe per-trade | pred > 0.5 |

---

## 🔄 PIPELINE

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CHARGEMENT DONNÉES                                       │
│    - labeled_trades.parquet (7,949 trades)                  │
│    - 98 features MenthorQ + OrderFlow                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. SPLIT TEMPOREL STRICT (par jours)                        │
│    - Train: 60% jours (4,769 trades)                        │
│    - Val:   20% jours (1,590 trades)                        │
│    - Test:  20% jours (1,590 trades)                        │
│    ⚠️  AUCUN CHEVAUCHEMENT (évite leakage)                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. BOUCLE SUR 8 TARGETS                                     │
│    Pour chaque target T1-T8:                                │
│    ┌──────────────────────────────────────────────────────┐ │
│    │ 3a. GÉNÉRER TARGET                                   │ │
│    │     - Appliquer formule (pnl > 0, pnl_ratio, etc.)  │ │
│    │     - Retourner (y_train, y_val, y_test)            │ │
│    └──────────────────────────────────────────────────────┘ │
│                          ↓                                   │
│    ┌──────────────────────────────────────────────────────┐ │
│    │ 3b. TRAINING ADAPTATIF                               │ │
│    │     - Si classification → LGBMClassifier             │ │
│    │     - Si regression → LGBMRegressor                  │ │
│    │     - Si multiclass → LGBMClassifier(num_class=3)    │ │
│    │     - Hyperparams optimaux (Optuna)                  │ │
│    └──────────────────────────────────────────────────────┘ │
│                          ↓                                   │
│    ┌──────────────────────────────────────────────────────┐ │
│    │ 3c. BACKTEST OUT-OF-SAMPLE                           │ │
│    │     - Prédictions sur test set                       │ │
│    │     - Décision TRADE/SKIP (logique par target)       │ │
│    │     - Calcul P&L brut/net, WR, Sharpe, MaxDD         │ │
│    └──────────────────────────────────────────────────────┘ │
│                          ↓                                   │
│    ┌──────────────────────────────────────────────────────┐ │
│    │ 3d. STOCKAGE RÉSULTATS                               │ │
│    │     - TargetResult(pnl_net, pnl/trade, n_trades...)  │ │
│    └──────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. SÉLECTION MEILLEURE TARGET                                │
│    - Score multi-objectif:                                   │
│      * 50% P&L net                                           │
│      * 20% Sharpe ratio                                      │
│      * 15% Nombre de trades                                  │
│      * 15% (100 - Max DD)                                    │
│    - Retourner best_target                                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. VALIDATION ROBUSTESSE                                     │
│    - 3 splits temporels différents                           │
│    - Retourner mean/std/min P&L                              │
│    - Confirmer stabilité                                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. REPORTING                                                 │
│    - Tableau comparatif (P&L, WR, Sharpe...)                │
│    - Graphiques (P&L cumulé, heatmap métriques)             │
│    - Rapport Markdown complet                                │
│    - Sauvegarde meilleur modèle                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 UTILISATION

### Installation

```bash
cd D:\MIA_IA_system
python -m pip install lightgbm pandas numpy scikit-learn matplotlib seaborn
```

### Lancement rapide

```bash
# Optimisation complète (15-20 min)
python ml/6_TARGET_OPTIMIZATION/run_optimization.py

# Avec arguments
python ml/6_TARGET_OPTIMIZATION/run_optimization.py \
    --data ml/2_LABELING/labeled_trades.parquet \
    --output ml/6_TARGET_OPTIMIZATION/results \
    --fees 0.62
```

### Output attendu

```
ml/6_TARGET_OPTIMIZATION/results/
├── comparison_table.csv           # Tableau résultats
├── best_target.json               # Meilleure target + métriques
├── all_results.json               # Tous les résultats
├── validation_results.json        # Robustesse
├── plots/
│   ├── pnl_comparison.png         # P&L cumulé par target
│   ├── metrics_heatmap.png        # Heatmap métriques
│   └── score_breakdown.png        # Radar chart best target
└── TARGET_OPTIMIZATION_REPORT.md  # Rapport complet
```

---

## 📊 CRITÈRES DE SUCCÈS

Une target est considérée **valide** si:

1. ✅ **P&L net out-of-sample > baseline** (+524t actuellement)
2. ✅ **P&L net par trade > +1.0 tick** (actuellement +0.25t)
3. ✅ **Nombre de trades raisonnable** (> 500 trades)
4. ✅ **Validation robustesse OK** (std < 20% de mean)

---

## 🧪 TESTS

```bash
# Tests unitaires
pytest ml/6_TARGET_OPTIMIZATION/tests/ -v

# Test rapide (1000 trades, 2 min)
python ml/6_TARGET_OPTIMIZATION/run_optimization.py --fast --n_trades 1000
```

---

## 📚 RÉFÉRENCES

- **train_lightgbm_classifier.py**: Source des hyperparams Optuna
- **backtest_classifier.py**: Logique de décision TRADE/SKIP
- **MenthorQ v2.0**: Features options uniques

---

## 🎯 RÉSULTATS ATTENDUS

**Hypothèses:**

- **T1** (Binary Simple): +524t | +0.25t/trade ← Baseline
- **T3** (P&L Ratio Reg): +1,200t | +0.80t/trade (prédiction conservative)
- **T7** (Expected Value): +1,800t | +1.20t/trade (prédiction optimiste)

**Meilleure target attendue:** T7 ou T3

---

## 📝 NOTES IMPORTANTES

1. **Split temporel strict:** Évite le leakage, résultats représentatifs production
2. **Fees incluses:** 0.62t/trade (réaliste)
3. **Features identiques:** 98 features MenthorQ+OrderFlow, seule la target change
4. **Hyperparams optimaux:** Réutilise résultats Optuna (100 trials)

---

## 🔄 WORKFLOW DÉVELOPPEMENT

1. **Phase 1:** Implémenter infrastructure + 8 targets
2. **Phase 2:** Training adaptatif + backtest
3. **Phase 3:** Sélection + validation
4. **Phase 4:** Reporting + visualisation
5. **Phase 5:** Tests + production

**Status actuel:** Phase 1 terminée ✅ (Infrastructure + 8 targets)

---

## 💡 AMÉLIORATIONS FUTURES

- [ ] Ajouter T9: Target combinée (moyenne pondérée T3 + T7)
- [ ] Implémenter cross-validation temporelle K-fold
- [ ] Tester ensembles de modèles (voting, stacking)
- [ ] Optimiser hyperparams par target (actuellement shared)
- [ ] Ajouter métriques avancées (Sortino, Calmar, Omega)

---

## 📧 SUPPORT

Pour questions ou bugs, contactez l'équipe MIA Trading System.

**Dernière mise à jour:** 15 novembre 2025 12:15 UTC







