# 🎯 PLAN DE TEST: ES vs NQ - 1 SEMAINE
# Date: 15 Novembre 2025

## ✅ DÉCISION VALIDÉE

**TRADER ES + NQ EN PARALLÈLE PENDANT 1 SEMAINE**

Comparer les performances réelles pour décider de la suite.

---

## 📊 CONFIGURATIONS VALIDÉES

### ES (S&P 500)
```python
tp_ticks_es = 16  # TP Optimal
sl_ticks_es = 12  # SL Élargi
rr_es = 1.33      # R:R 1.33:1
```

**Performance Attendue:**
- P&L/trade: +0.397 ticks
- WinRate: 45.8%
- Profit Factor: 1.09
- TP Hit Rate: 17.9%
- SL Hit Rate: 46.7%

### NQ (Nasdaq-100)
```python
tp_ticks_nq = 23  # TP Optimal
sl_ticks_nq = 12  # SL Élargi
rr_nq = 1.92      # R:R 1.92:1
```

**Performance Attendue:**
- P&L/trade: +1.528 ticks
- WinRate: 43.5%
- Profit Factor: 1.27
- TP Hit Rate: 15.1%
- SL Hit Rate: 56.2%

---

## 📈 OBJECTIFS DU TEST (1 SEMAINE)

### Métriques à Comparer:

**Performance:**
- [ ] P&L Net par symbole
- [ ] P&L/trade par symbole
- [ ] WinRate par symbole
- [ ] Profit Factor par symbole
- [ ] Nombre de trades par symbole

**Qualité d'exécution:**
- [ ] TP Hit Rate réel vs attendu
- [ ] SL Hit Rate réel vs attendu
- [ ] Temps moyen en position
- [ ] Slippage moyen

**Psychologie:**
- [ ] Stress ressenti (1 vs 2 symboles)
- [ ] Qualité de surveillance
- [ ] Erreurs d'exécution
- [ ] Fatigue mentale

---

## 🎯 CRITÈRES DE DÉCISION APRÈS 1 SEMAINE

### Scénario A: NQ clairement supérieur
**Critères:**
- P&L/trade NQ > 3x ES
- NQ atteint performance attendue (+1.5t)
- ES sous-performe (<0.3t)

**Décision:** Focus 100% NQ

### Scénario B: Les deux rentables
**Critères:**
- ES: +0.3-0.5 t/trade
- NQ: +1.3-1.7 t/trade
- Stress gérable

**Décision:** Continuer ES + NQ

### Scénario C: ES surprend positivement
**Critères:**
- ES: >+0.5 t/trade
- ES proche de NQ en ROI
- Diversification bénéfique

**Décision:** Continuer ES + NQ, optimiser davantage

---

## 📊 RAPPORT QUOTIDIEN (Template)

### Jour 1: [DATE]

**ES:**
- Trades: X
- P&L Net: XXX ticks
- P&L/trade: X.XX ticks
- WinRate: XX.X%
- TP Hits: X (XX%)
- SL Hits: X (XX%)

**NQ:**
- Trades: X
- P&L Net: XXX ticks
- P&L/trade: X.XX ticks
- WinRate: XX.X%
- TP Hits: X (XX%)
- SL Hits: X (XX%)

**Observations:**
- [Notes sur qualité d'exécution]
- [Stress/Focus]
- [Problèmes rencontrés]

---

## ✅ CHECKLIST IMPLÉMENTATION

- [x] Optimiseur TP/SL créé et testé
- [x] Configurations optimales validées (ES: 16t/12t, NQ: 23t/12t)
- [ ] Code de production modifié
- [ ] Backtests relancés (optionnel)
- [ ] Bot redémarré avec nouvelles configs
- [ ] Monitoring actif pendant 1 semaine
- [ ] Rapport final après 1 semaine

---

## 🚀 PROCHAINES ÉTAPES IMMÉDIATES

1. **Implémenter les configs dans le code**
2. **Redémarrer le bot**
3. **Monitorer activement pendant 1 semaine**
4. **Générer rapport comparatif ES vs NQ**
5. **Décider de la suite**

---

## 📁 FICHIERS GÉNÉRÉS AUJOURD'HUI

### Optimiseurs:
- `ml/tp_optimizer.py` (TP seul)
- `ml/tp_sl_optimizer.py` (TP + SL combinés)
- `ml/tp_sl_extended_analyzer.py` (SL élargi 12-18t)

### Résultats:
- `ml/output/tp_optimization_ES_*.csv`
- `ml/output/tp_optimization_NQ_*.csv`
- `ml/output/tp_sl_optimization_ES_*.csv`
- `ml/output/tp_sl_optimization_NQ_*.csv`
- `ml/output/tp_sl_extended_ES_*.csv`
- `ml/output/tp_sl_extended_NQ_*.csv`

### Rapports:
- `ml/output/tp_optimization_COMPARISON_*.txt`
- `ml/output/tp_sl_optimization_COMPARISON_*.txt`
- `ml/output/tp_sl_extended_COMPARISON_*.txt`

### Graphiques:
- Heatmaps TP/SL pour ES et NQ
- Surfaces 3D P&L en fonction TP/SL

### Documentation:
- `ml/DOCS/RECOMMANDATION_ES_15NOV.md`
- `ml/DOCS/PLAN_TEST_ES_NQ_15NOV.md` (ce fichier)

---

## 🎯 RÉSUMÉ EXÉCUTIF

**Configuration Test (1 semaine):**
```
ES: TP 16t / SL 12t → Attendu: +0.397 t/trade
NQ: TP 23t / SL 12t → Attendu: +1.528 t/trade
```

**Objectif:**
Valider en production réelle les performances
et décider si on continue ES ou focus 100% NQ.

**Décision finale:** Dans 1 semaine basée sur données réelles.

---

**STATUS:** ⏳ EN ATTENTE D'IMPLÉMENTATION







