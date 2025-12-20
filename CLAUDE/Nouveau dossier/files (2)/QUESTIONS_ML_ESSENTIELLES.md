# 🎯 QUESTIONS ESSENTIELLES - REBUILD ML SYSTEM

**Date**: 18 Nov 2025  
**Objectif**: Construire un système ML RENTABLE (vs actuel: -$403/jour, 33% WR)

---

## 📊 SITUATION ACTUELLE

### Système Existant
- **Modèles**: LightGBM binaires (WIN/LOSS) par symbole (ES, NQ, RTY)
- **Features**: 69 (49 brutes + 20 engineered)
- **Objectif**: Prédire si trade sera gagnant/perdant
- **Seuil**: ML confidence > 48% pour entrer

### Performances RÉELLES (18 Nov)
```
45 trades | WR: 33% | P&L: -$403 | PF: 0.90
- 17 stop hunts = -$2,118 (51% des pertes!)
- ES catastrophique: 27% WR, -$303
- 26 trades "UNKNOWN" = -$421
```

### Problème Principal
**Le ML prédit WIN/LOSS mais ne prédit PAS:**
1. ❌ Risque de stop hunt imminent
2. ❌ Magnitude du mouvement (10 ticks vs 50 ticks?)
3. ❌ Timing optimal d'entrée
4. ❌ Durée de holding optimale
5. ❌ Meilleure stratégie selon contexte

---

## ❓ 10 QUESTIONS CRITIQUES À RÉPONDRE

### Q1: QUEL EST LE VRAI OBJECTIF ML?

**Options:**
- A) Prédire WIN/LOSS (actuel - ne marche pas)
- B) Prédire magnitude du mouvement 
- C) Prédire risque de stop hunt
- D) Prédire timing optimal d'entrée
- E) Combiner plusieurs modèles spécialisés ✅

**Question:** On part sur E avec 3-5 modèles spécialisés?

---

### Q2: QUELS MODÈLES PRIORISER?

**Proposition ordre de priorité:**

**1. Stop Hunt Predictor (URGENT)** 
   - Objectif: Bloquer les 17 stop hunts/jour = -$2,118
   - Target: Classifier binaire (SAFE / RISK)
   - Gain estimé: +$1,500/jour

**2. Regime Detector**
   - Objectif: Éviter ES en régime pourri (27% WR)
   - Target: Multi-class (8-10 régimes)
   - Gain estimé: +$600/jour

**3. Magnitude Predictor**
   - Objectif: Position sizing dynamique
   - Target: Régression (ticks prédits) ou Multi-class (BIG/MED/SMALL/CHOP)
   - Gain estimé: +$800/jour

**Question:** Ces 3 d'abord? Ou autre ordre?

---

### Q3: FEATURES - LESQUELLES GARDER?

**Données disponibles**: 194 features par tick

**Catégories:**
- Price/VWAP: 36 features
- DOM/OrderBook: 41 features  
- Options/GEX: 29 features
- Volume/Delta: 11 features
- Momentum: 8 features
- Structure: 7 features

**Actuel**: 69 features utilisées

**Questions:**
1. Garder les 69 actuelles ou refaire selection?
2. Ajouter features temporelles (rolling windows)?
3. Créer features de "contexte" (séquences)?

**Proposition:** Feature importance analysis sur 10 jours de data

---

### Q4: LABELS - COMMENT DÉFINIR "SUCCÈS"?

**Pour Stop Hunt Predictor:**
- Label 1 (RISK): Trade touché SL dans <2min ET prix reverse
- Label 0 (SAFE): Trade survit >2min OU hit TP

**Pour Magnitude Predictor:**
- Option A: Régression continue (nombre de ticks)
- Option B: Classes (CHOP<10, SMALL 10-20, MED 20-50, BIG>50)

**Pour Regime Detector:**
- Clustering non-supervisé sur historique
- Puis labeling manuel des clusters
- Ou features → performance par stratégie

**Question:** Option A ou B pour Magnitude? Clustering ou supervisé pour Regime?

---

### Q5: COMBIEN DE DATA POUR ENTRAÎNER?

**Disponible**: 10 jours de trading (~450 trades)

**Breakdown possible:**
- Train: 7 jours (315 trades)
- Validation: 2 jours (90 trades)  
- Test: 1 jour (45 trades)

**Problème:** 315 trades pour entraîner c'est PEU

**Options:**
1. Utiliser tous les 10 jours + validation croisée
2. Demander plus de data historique
3. Data augmentation (shuffling time windows?)

**Question:** Comment maximiser l'utilisation de 10 jours?

---

### Q6: ARCHITECTURE - ENSEMBLE OU SÉQUENTIEL?

**Option A: Séquentiel (Pipeline)**
```
Signal Stratégie 
  → Stop Hunt Filter (bloque si RISK)
    → Magnitude Predictor (size position)
      → Timing Optimizer (attend si mauvais)
        → EXECUTE
```

**Option B: Ensemble (Voting)**
```
- Stop Hunt Score: 0.8
- Magnitude Score: 0.7  
- Timing Score: 0.6
→ Combined Score: 0.7 → EXECUTE
```

**Option C: Hybride**
- Stop Hunt = VETO absolu (si RISK → block)
- Reste = weighted voting

**Question:** C semble le plus sûr? Ou autre approche?

---

### Q7: SYMBOLES - MODÈLES SÉPARÉS OU UNIFIÉS?

**Actuel**: 1 modèle par symbole (ES, NQ, RTY)

**Problème:** ES a patterns très différents de NQ
- ES: 27% WR (catastrophe)
- NQ: 37% WR (moins pire)

**Options:**
1. Garder modèles séparés par symbole
2. Modèle unifié + "symbol" comme feature
3. Stratégies spécifiques par symbole

**Question:** Modèles séparés mieux? Ou feature "symbol"?

---

### Q8: VALIDATION - COMMENT ÉVITER OVERFITTING?

**Avec seulement 10 jours de data:**

**Stratégies:**
1. Walk-forward validation (rolling window)
2. K-fold avec attention aux gaps temporels
3. Ensemble de modèles avec différents seeds
4. Early stopping aggressive
5. Régularisation forte (L1/L2)

**Question:** Quelle combinaison pour 450 trades seulement?

---

### Q9: FEATURES TEMPORELLES - COMBIEN DE LOOKBACK?

**Actuellement:** Features instantanées (snapshot à T)

**À ajouter?**
- Rolling mean/std delta sur [10s, 30s, 1min, 5min]?
- Momentum (diff price T vs T-30s)?
- Volume acceleration?
- DOM imbalance trend?

**Problème:** Créer features temporelles = compliquer training

**Question:** Worth it? Ou garder features instantanées pour V1?

---

### Q10: DÉPLOIEMENT - COMMENT INTÉGRER DANS PIPELINE?

**Architecture actuelle:**
```python
stratégie.generate_signal()
  → ml_filter.should_trade(signal)  # Confidence > 48%
    → execute
```

**Nouvelle architecture:**
```python
stratégie.generate_signal()
  → stop_hunt_predictor.check(signal)  # VETO si RISK
    → magnitude_predictor.predict(signal)  # Position size
      → timing_optimizer.should_enter_now(signal)
        → execute with optimized params
```

**Question:** Remplacer ml_filter ou ajouter en layers?

---

## 🎯 DÉCISIONS À PRENDRE MAINTENANT

### Décision 1: Stratégie Générale

**Proposition:**
1. **Semaine 1-2**: Stop Hunt Predictor (PRIORITÉ MAX)
   - Gain immédiat: +$1,500/jour
   - Bloque 70% des stop hunts
   
2. **Semaine 3**: Regime Detector  
   - Désactive ES en mauvais régimes
   - Gain: +$600/jour

3. **Semaine 4**: Magnitude Predictor
   - Position sizing dynamique
   - Gain: +$800/jour

**Total gain projeté: +$2,900/jour vs -$403 actuel**

**Validation?** Ou autre priorité?

---

### Décision 2: Features pour V1

**Proposition MINIMALISTE** (V1 = MVP):
- Garder 69 features actuelles
- Ajouter 10-15 features clés pour stop hunts:
  - Distance à HVL/GEX walls
  - DOM imbalance spike detection
  - Recent sweep indicator
  - Time since last volatility spike

**Total: ~80-85 features**

**Validation?** Ou refaire feature selection complète?

---

### Décision 3: Labels Stop Hunt

**Proposition:**
```python
def label_stop_hunt(trade):
    if trade.sl_hit and trade.duration < 120s:
        # Vérifier si prix a reversé après SL
        if opposite_direction_within_30s:
            return 1  # STOP HUNT
    return 0  # SAFE
```

**Validation?** Ou autre définition?

---

### Décision 4: Dataset

**Proposition:**
- Utiliser les 10 jours complets
- 7-fold cross-validation temporelle
- Garder dernier jour comme final holdout test

**Validation?** Ou split fixe 7-2-1?

---

## 🚀 PLAN D'ACTION PROPOSÉ

### IMMÉDIAT (Aujourd'hui)
1. ✅ Définir priorités modèles
2. ✅ Définir features V1  
3. ✅ Définir labels stop hunt
4. ⏳ Extraire/préparer 10 jours de data

### SEMAINE 1 (Jours 1-3)
1. Feature engineering pour stop hunts
2. Labelling des 450 trades (stop hunt ou non)
3. Feature importance analysis
4. Train Stop Hunt Predictor V1

### SEMAINE 1 (Jours 4-7)
1. Validation croisée Stop Hunt model
2. Intégration dans pipeline (as VETO filter)
3. Backtesting sur 10 jours
4. Paper trading 2-3 jours

### SEMAINE 2
1. Production Stop Hunt Predictor
2. Monitoring gains réels
3. Commencer Regime Detector

---

## 🎤 QUESTIONS POUR VOUS

**Répondre à:**

1. **Priorités modèles:** OK avec Stop Hunt → Regime → Magnitude?
2. **Features:** Garder 69 + ajouter 15 pour stop hunts, ou refaire selection?
3. **Labels stop hunt:** Définition ci-dessus OK?
4. **Dataset:** 7-fold CV ou split fixe?
5. **Autre décision critique** que j'ai oubliée?

**Une fois ces 5 points validés, on peut coder.**

---

## 📈 GAINS ATTENDUS

**Avec Stop Hunt Predictor seul:**
- Réduction stop hunts: 17 → 5 par jour
- Économies: $1,482 par jour
- WR: 33% → 45-48%
- P&L: -$403 → +$800 à +$1,200

**ROI Développement:**
- Temps: 1-2 semaines
- Gain: +$1,200/jour = +$24,000/mois
- **ROI: IMMÉDIAT**
