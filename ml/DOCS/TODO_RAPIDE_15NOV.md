# ⚡ TODO LISTE - VUE RAPIDE 15 NOV

**Objectif:** Corriger ML système (1h30 total) → F1 55-60%, P&L +80-120% RÉEL

---

## 🎯 PHASES (5)

### **PHASE 1: VÉRIFICATION (10 min)**
```
✅ TODO #1: Ajouter vérification cohérence matrice (5 min)
✅ TODO #2: Backup résultats actuels (5 min)
```

### **PHASE 2: SPLIT TEMPOREL (30 min)**
```
✅ TODO #3: Créer _prepare_data_temporal_split() (20 min)
✅ TODO #4: Modifier train_pipeline() ligne 667 (5 min)
✅ TODO #5: Sauvegarder split_info metadata (5 min)
```

### **PHASE 3: RE-TRAINING (20 min)**
```
✅ TODO #6: Re-training split temporel (15 min)
✅ TODO #7: Analyser métriques réelles (5 min)
```

### **PHASE 4: BACKTEST OUT-OF-SAMPLE (25 min)**
```
✅ TODO #8: Créer _load_data_out_of_sample() (15 min)
✅ TODO #9: Modifier run_backtest() (5 min)
✅ TODO #10: Modifier script principal (5 min)
```

### **PHASE 5: VALIDATION (20 min)**
```
✅ TODO #11: Lancer backtest out-of-sample (5 min)
✅ TODO #12: Analyser P&L réel (5 min)
✅ TODO #13: Validation finale (checklist) (5 min)
✅ TODO #14: Mettre à jour documentation (10 min)
```

---

## 📊 RÉSULTATS ATTENDUS

| Métrique | AVANT | APRÈS | Status |
|----------|-------|-------|--------|
| **F1-Score** | 65% | **55-60%** | ✅ Normal |
| **P&L Gain** | +185% | **+80-120%** | ✅ RÉEL |
| **Split** | Random | **Temporel** | ✅ Corrigé |
| **Backtest** | In-sample | **Out-of-sample** | ✅ Corrigé |

---

## 🚨 COMMANDES CLÉS

```bash
# 1. Backup
cp ml/models/lightgbm_quality_v1.pkl ml/backup_random_split_15nov/

# 2. Re-training (après modifications #3-5)
python ml/4_TRAINING/train_lightgbm_classifier.py

# 3. Backtest (après modifications #8-10)
python ml/5_PREDICTION/backtest_classifier.py
```

---

## ✅ VALIDATION FINALE

**Système READY si:**
- ✅ F1 > 50% (out-of-sample)
- ✅ P&L > +80% (out-of-sample)
- ✅ Split temporel documenté
- ✅ Métriques cohérentes

**→ PRÊT POUR SHADOW MODE !** 🚀

---

**📄 Doc complète:** `ml/DOCS/TODO_CORRECTION_ML_15NOV.md` (avec CODE COMPLET)







