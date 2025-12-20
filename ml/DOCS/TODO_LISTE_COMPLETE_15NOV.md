# 📋 TODO LISTE COMPLÈTE - CORRECTIONS AUDIT DISCORD + PIPELINE

**Date:** 15 Novembre 2025
**Objectif:** Corriger TOUS les manquements identifiés dans les audits
**Total TODOs:** 48 tâches

---

## 🔥 **PRIORITÉ 1: RENAMING (HONNÊTETÉ) - 4 TODOs**

### **Objectif:** Clarifier que le système est "MenthorQ 3-Layer" pas "ML 3-Layer"

```
✅ TODO #1: Renommer ml_3layer_strategy.py → menthorq_3layer_strategy.py
✅ TODO #2: Update display_name dans le fichier (ML → MenthorQ)
✅ TODO #3: Update imports dans strategy_manager_optimized_v3.py
✅ TODO #4: Update imports dans launch_ml_v3_production.py
```

**Impact:** Honnêteté, clarté système
**Temps:** 30 minutes
**Blockers:** Aucun

---

## 🎨 **PRIORITÉ 2: DISCORD ENRICHISSEMENT - 8 TODOs**

### **Objectif:** Enrichir embeds Discord avec contexte complet

#### **A. Trade Opened Embed (3 nouveaux fields):**

```
✅ TODO #5: Ajouter field "🌐 Market Context"
   - Bias (BULLISH/BEARISH)
   - Bullish Score (%)
   - Régime (Momentum/Mean Reversion)
   - Session

✅ TODO #6: Ajouter field "📍 Entry Context"
   - MenthorQ Level Type (GEX/CALL/PUT/HVL)
   - MenthorQ Level Price
   - Strength (%)
   - Distance to Level (ticks)

✅ TODO #7: Ajouter field "🎯 Risk Management"
   - R:R Ratio
   - 1D Proximity (distance + level type)
   - Swing Distance (ticks)
```

#### **B. Trade Closed Embed (2 nouveaux fields + footer):**

```
✅ TODO #8: Modifier field "💰 P&L" pour inclure:
   - P&L Trade (ticks + USD)
   - P&L Jour Cumulé (USD)
   - WinRate Jour (%)

✅ TODO #9: Ajouter field "📊 Exit Analysis"
   - Type détaillé (TP_HIT, TP_TIMEOUT, REVERSAL_XX)
   - MFE / MAE (ticks)
   - Efficiency (P&L / MFE * 100)

✅ TODO #10: Ajouter footer avec stats jour
   - Total trades jour
   - Wins/Losses
   - P&L jour
```

#### **C. Nouveaux Embeds:**

```
✅ TODO #11: Créer build_signal_rejected_embed()
   - Symbol, Direction, Confluence
   - Rejection Reason
   - Rejection Category
   - Filters Passed / Failed

✅ TODO #12: Créer build_daily_summary_embed()
   - P&L Total
   - Stats par symbole (ES/NQ)
   - Exit Breakdown
   - Best/Worst Trade
```

**Impact:** Visibilité complète, monitoring amélioré
**Temps:** 2 heures
**Blockers:** Besoin données enrichies (Priorité 4)

---

## 📝 **PRIORITÉ 3: EXIT LOGGING DÉTAILLÉ - 4 TODOs**

### **Objectif:** Exit reasons précis pour analyse

```
✅ TODO #13: Modifier _close_position() pour distinguer:
   - "TP_HIT" → TP réellement atteint (MFE >= expected_tp)
   - "TP_TIMEOUT" → Exit avant TP (timeout/reversal)

✅ TODO #14: Ajouter distinction SL:
   - "SL_HIT" → SL réellement atteint (MAE >= expected_sl)
   - "SL_REVERSAL" → Exit avant SL (reversal détecté)

✅ TODO #15: Ajouter score reversal dans exit_reason:
   - "REVERSAL_75" → Exit sur reversal score 75
   - "REVERSAL_80" → Exit sur reversal score 80

✅ TODO #16: Ajouter durée dans timeout:
   - "TIMEOUT_8MIN" → Exit après 8 minutes
   - "TIMEOUT_15MIN" → Exit après 15 minutes
```

**Impact:** Analyse précise exits anticipées vs TP/SL
**Temps:** 1 heure
**Blockers:** Aucun

---

## 💾 **PRIORITÉ 4: DATA ENRICHMENT - 13 TODOs**

### **Objectif:** Logger toutes données utiles pour ML futur

#### **A. Dans self.open_positions (entrée trade):**

```
✅ TODO #17: Ajouter expected_tp_ticks (TP configuré)
✅ TODO #18: Ajouter expected_sl_ticks (SL configuré)
✅ TODO #21: Ajouter menthorq_level_entry (prix du niveau)
✅ TODO #22: Ajouter menthorq_level_type (GEX/CALL/PUT/HVL/BLIND)
✅ TODO #23: Ajouter menthorq_strength (force du niveau 0-100)
✅ TODO #24: Ajouter d1_proximity (distance 1D Min/Max en ticks)
✅ TODO #25: Ajouter swing_distance (distance dernier swing en ticks)
✅ TODO #27: Ajouter market_bias ("BULLISH"/"BEARISH"/"NEUTRAL")
✅ TODO #28: Ajouter bullish_score (0-100)
✅ TODO #29: Ajouter regime ("momentum"/"mean_reversion")
```

#### **B. Dans self.daily_trades (sortie trade):**

```
✅ TODO #19: Ajouter actual_exit_ticks (distance exit réelle)
✅ TODO #20: Ajouter slippage_ticks (expected - actual)
✅ TODO #26: Ajouter reversal_score_max (max reversal atteint)
```

**Impact:** Dataset qualité pour ML semaine 2+
**Temps:** 1.5 heures
**Blockers:** Aucun

---

## 🔧 **PRIORITÉ 5: EMBED FIXES - 3 TODOs**

### **Objectif:** Corriger embeds pour refléter vraies données

```
✅ TODO #30: Remplacer ml_confidence par menthorq_score
   - Utiliser layer1_score (MenthorQ 50%)

✅ TODO #31: Ajouter orderflow_score
   - Utiliser layer2_score (OrderFlow 30%)

✅ TODO #32: Ajouter context_score
   - Utiliser layer3_score (Context 20%)
```

**Impact:** Cohérence embeds vs réalité
**Temps:** 30 minutes
**Blockers:** Priorité 1 (Renaming)

---

## 🚀 **PRIORITÉ 6: LAUNCHER INTEGRATION - 3 TODOs**

### **Objectif:** Intégrer nouveaux embeds dans launcher

```
✅ TODO #33: Intégrer build_signal_rejected_embed
   - Dans _reject_signal_with_snapshot()
   - Webhook: #signal

✅ TODO #34: Créer tracker daily_data
   - Accumuler stats jour (trades, P&L, exits)
   - Reset à minuit

✅ TODO #35: Scheduler daily_summary 16h30 EST
   - Envoi automatique
   - Webhook: #performance
```

**Impact:** Monitoring automatique complet
**Temps:** 1 heure
**Blockers:** Priorité 2 (Discord enrichi)

---

## 🔍 **PRIORITÉ 7: AUDIT STRATÉGIES - 5 TODOs**

### **Objectif:** Vérifier cohérence toutes stratégies

```
✅ TODO #36: Audit VWAPSDOptionsConfluenceStrategy
   - Vérifier 6 scenarios
   - TP/SL cohérents
   - Signal dict conforme

✅ TODO #37: Audit GammaWallRejectionStrategy
   - Vérifier TP/SL
   - Signal dict conforme

✅ TODO #38: Audit TP/SL toutes stratégies
   - Vérifier cohérence avec config optimale
   - ES: 16t/12t, NQ: 23t/12t

✅ TODO #39: Audit format signal dict
   - Toutes stratégies retournent même format
   - Champs requis présents

✅ TODO #40: Audit priorités stratégies
   - Vérifier STRATEGY_PRIORITY dans config
   - Ordre logique
```

**Impact:** Cohérence système complet
**Temps:** 2 heures
**Blockers:** Aucun

---

## ✅ **PRIORITÉ 8: TESTS - 4 TODOs**

### **Objectif:** Valider toutes modifications

```
✅ TODO #41: Tester embeds enrichis
   - Envoyer test sur webhooks Discord
   - Vérifier affichage

✅ TODO #42: Tester rejection embed
   - Générer signal rejeté
   - Vérifier notification

✅ TODO #43: Tester exit_reason détaillé
   - Vérifier logs
   - Vérifier classification correcte

✅ TODO #44: Tester données enrichies
   - Vérifier daily_trades.json
   - Tous champs présents
```

**Impact:** Validation avant production
**Temps:** 1 heure
**Blockers:** Toutes priorités précédentes

---

## 📚 **PRIORITÉ 9: DOCUMENTATION - 2 TODOs**

### **Objectif:** Documenter changements

```
✅ TODO #45: Créer CHANGELOG_15NOV_CORRECTIONS.md
   - Lister tous changements
   - Rationale
   - Impact

✅ TODO #46: Update README
   - Nouveau naming (MenthorQ 3-Layer)
   - Architecture clarifiée
   - Discord embeds enrichis
```

**Impact:** Traçabilité
**Temps:** 30 minutes
**Blockers:** Toutes priorités précédentes

---

## ✔️ **PRIORITÉ 10: VALIDATION FINALE - 2 TODOs**

### **Objectif:** S'assurer code production-ready

```
✅ TODO #47: Compiler tous fichiers modifiés
   - python -m py_compile <file>
   - Vérifier aucune erreur syntaxe

✅ TODO #48: Vérifier lints
   - read_lints sur fichiers modifiés
   - Corriger erreurs
```

**Impact:** Code propre
**Temps:** 30 minutes
**Blockers:** Toutes priorités précédentes

---

## 📊 **RÉSUMÉ PAR PRIORITÉ**

| Priorité | Tâches | Temps | Blockers | Criticité |
|----------|--------|-------|----------|-----------|
| **P1: Renaming** | 4 | 30min | Aucun | 🔴 CRITIQUE |
| **P2: Discord** | 8 | 2h | P4 | 🔴 CRITIQUE |
| **P3: Exit Logging** | 4 | 1h | Aucun | 🟠 HAUTE |
| **P4: Data Enrichment** | 13 | 1.5h | Aucun | 🟠 HAUTE |
| **P5: Embed Fixes** | 3 | 30min | P1 | 🟠 HAUTE |
| **P6: Launcher** | 3 | 1h | P2 | 🟡 MOYENNE |
| **P7: Audit Strats** | 5 | 2h | Aucun | 🟡 MOYENNE |
| **P8: Tests** | 4 | 1h | P1-P7 | 🟢 BASSE |
| **P9: Docs** | 2 | 30min | P1-P7 | 🟢 BASSE |
| **P10: Validation** | 2 | 30min | P1-P9 | 🟢 BASSE |
| **TOTAL** | **48** | **~10h** | - | - |

---

## ⏰ **PLANNING RECOMMANDÉ**

### **Dimanche Soir (4h):**
```
18h-18h30: P1 - Renaming (4 TODOs)
18h30-19h00: P5 - Embed Fixes (3 TODOs)
19h00-20h30: P4 - Data Enrichment (13 TODOs)
20h30-21h30: P3 - Exit Logging (4 TODOs)
```

### **Lundi Matin (3h):**
```
7h-9h: P2 - Discord Enrichissement (8 TODOs)
9h-10h: P6 - Launcher Integration (3 TODOs)
```

### **Lundi Après-midi (3h):**
```
14h-16h: P7 - Audit Stratégies (5 TODOs)
16h-17h: P8 - Tests (4 TODOs)
17h-17h30: P9 - Documentation (2 TODOs)
17h30-18h: P10 - Validation (2 TODOs)
```

---

## 🎯 **CHECKLIST SIMPLIFIÉE**

### **Phase 1 (Dimanche - CRITIQUE):**
- [ ] Renaming complet (ml → menthorq)
- [ ] Data enrichment (13 champs)
- [ ] Exit logging détaillé
- [ ] Embed fixes

### **Phase 2 (Lundi Matin - IMPORTANT):**
- [ ] Discord embeds enrichis
- [ ] Launcher integration

### **Phase 3 (Lundi Après-midi - VALIDATION):**
- [ ] Audit stratégies
- [ ] Tests complets
- [ ] Documentation
- [ ] Validation finale

---

## ✅ **VALIDATION AVANT PRODUCTION**

```
[ ] 48/48 TODOs complétés
[ ] Tous tests passés
[ ] Aucune erreur lint
[ ] Documentation à jour
[ ] Code compilé sans erreur
[ ] Discord embeds testés
[ ] Exit reasons validés
[ ] Données enrichies présentes
```

---

**Status:** ⚠️ 0/48 TODOs complétés
**ETA:** 10 heures (Dimanche soir + Lundi)
**Prêt Production:** Lundi 18h00







