# ⚡ DÉCISIONS RAPIDES - À VALIDER MAINTENANT

**Time to decide**: 10 minutes  
**Ensuite**: On code

---

## 🎯 5 DÉCISIONS CRITIQUES

### 1️⃣ PRIORITÉ MODÈLES

**Ordre proposé:**
```
1. Stop Hunt Predictor (Semaine 1)
2. Regime Detector (Semaine 2)  
3. Magnitude Predictor (Semaine 3)
```

**Alternative:** Autre ordre?

**VOTRE CHOIX:** _______________

---

### 2️⃣ FEATURES VERSION 1

**Option A: Minimaliste (RECOMMANDÉ)**
- Garder 69 features actuelles
- Ajouter 15 pour stop hunts
- **Total: 84 features**

**Option B: Refaire sélection complète**
- Feature importance sur 194 features
- Garder top 100
- **Risque: Plus long, potentiel overfitting**

**VOTRE CHOIX:** A ou B? _______________

---

### 3️⃣ LABELS STOP HUNT

**Proposition:**
```python
STOP_HUNT = 
  SL touché 
  ET duration < 120s
  ET prix reversé après dans direction opposée
  ET trade aurait été gagnant si tenu
```

**Alternative:** Autre définition?

**VOTRE CHOIX:** OK ou modifier? _______________

---

### 4️⃣ VALIDATION STRATEGY

**Option A: K-Fold temporel (RECOMMANDÉ)**
- 5-fold TimeSeriesSplit
- Utilise tous les 10 jours
- Évite overfitting temporel

**Option B: Split fixe**
- Train: 7 jours
- Val: 2 jours
- Test: 1 jour

**VOTRE CHOIX:** A ou B? _______________

---

### 5️⃣ MAGNITUDE - CLASSIFIER OU REGRESSOR?

**Option A: Classifier 4 classes**
```
0: CHOP (<10 ticks)
1: SMALL (10-20)
2: MEDIUM (20-50)
3: BIG (>50)
```
**Pro:** Plus simple, plus robuste
**Con:** Moins précis

**Option B: Regressor (prédire nombre de ticks)**
**Pro:** Plus précis
**Con:** Peut être moins robuste

**VOTRE CHOIX:** A ou B? _______________

---

## 📋 CHECKLIST AVANT DE COMMENCER

Cocher quand prêt:

- [ ] Ai accès aux 10 jours de data en CSV/JSON
- [ ] Connais format exact des données
- [ ] Ai LightGBM installé (`pip install lightgbm`)
- [ ] Ai pandas, numpy, sklearn installés
- [ ] Ai un IDE prêt pour coder
- [ ] Ai temps pour 3-4h de code aujourd'hui

---

## 🚀 NEXT STEPS (si tout validé)

### Immédiatement après validation:

1. **Data extraction** (30min)
   - Exporter 10 jours de trades + snapshots
   - Format: 1 row par trade avec toutes les features

2. **Labeling** (1h)
   - Créer labels stop_hunt pour chaque trade
   - Vérifier distribution (combien de 1 vs 0?)

3. **Feature engineering** (1h)
   - Coder les 15 nouvelles features
   - Tester sur 1 snapshot

4. **Training V0.1** (1h)
   - Model de base sans tuning
   - Juste pour voir si ça marche

**Total: ~3-4h pour avoir un premier modèle fonctionnel**

---

## ❓ QUESTIONS?

**Avant de commencer, besoin de clarifier:**

1. Format des données? (CSV, JSON, autre?)
2. Où sont les 10 jours de data?
3. Structure exacte d'un trade record?
4. Déjà un script d'extraction ou à créer?

**Répondre maintenant pour éviter blocages.**

---

## 📊 RAPPEL GAINS ATTENDUS

**Avec juste Stop Hunt Predictor (Semaine 1):**

```
Trades actuels:  45/jour, 33% WR, -$403
Stop hunts:      17/jour = -$2,118

Après modèle:
Stop hunts:      5/jour (réduction 70%)
Économies:       +$1,482/jour
WR:              33% → 45-48%
P&L:             -$403 → +$800 à +$1,200

SWING: +$1,200 à +$1,600 PAR JOUR
```

**ROI investissement:**
- 1 semaine de dev
- Gain: $6,000 à $8,000/semaine
- **Retour immédiat**

---

## ✅ VALIDATION FINALE

**Je valide les 5 décisions:**

1. Priorité: Stop Hunt → Regime → Magnitude ✓
2. Features: Garder 69 + ajouter 15 ✓
3. Labels: SL<120s + reverse ✓
4. Validation: TimeSeriesSplit 5-fold ✓
5. Magnitude: Classifier 4 classes ✓

**Signature:** _______________
**Date:** 18 Nov 2025

**⚡ UNE FOIS SIGNÉ → ON CODE**
