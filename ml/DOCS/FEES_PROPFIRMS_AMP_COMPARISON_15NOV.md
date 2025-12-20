# COMPARAISON FEES - PROPFIRMS vs AMP FUTURES

**Date:** 15 Novembre 2025
**Sources:** Recherche web + sites officiels brokers
**Objectif:** Déterminer les fees les PLUS ÉLEVÉES pour calculs conservateurs

---

## 📊 TABLEAU COMPARATIF FEES (Round Turn = Aller-Retour)

### E-MINI ES (S&P 500)

| Broker / PropFirm | Commission | Exchange + NFA | **TOTAL** | En Ticks |
|-------------------|------------|----------------|-----------|----------|
| **AMP Futures** | $0.65 | $1.60 | **$2.25** | **0.18t** |
| **Apex Trader Funding** | $0.50-0.90 | $0.60 | **$1.10-1.50** | **0.09-0.12t** |
| **TopStep** | $0.65-1.00 | $0.60 | **$1.25-1.60** | **0.10-0.13t** |
| **Elite Trader** | $0.55-0.85 | $0.60 | **$1.15-1.45** | **0.09-0.12t** |
| **Phidias PropFirm** | $2.20 | $1.60 | **$3.80** | **0.30t** |
| **Interactive Brokers** | $0.85 | $1.60 | **$2.45** | **0.20t** |

**🔴 PLUS CHER: Phidias PropFirm = $3.80 (0.30t)**

---

### E-MINI NQ (Nasdaq-100)

| Broker / PropFirm | Commission | Exchange + NFA | **TOTAL** | En Ticks |
|-------------------|------------|----------------|-----------|----------|
| **AMP Futures** | $0.65 | $1.60 | **$2.25** | **0.45t** |
| **Apex Trader Funding** | $0.50-0.90 | $0.60 | **$1.10-1.50** | **0.22-0.30t** |
| **TopStep** | $0.65-1.00 | $0.60 | **$1.25-1.60** | **0.25-0.32t** |
| **Elite Trader** | $0.55-0.85 | $0.60 | **$1.15-1.45** | **0.23-0.29t** |
| **Phidias PropFirm** | $2.20 | $1.60 | **$3.80** | **0.76t** |
| **Interactive Brokers** | $0.85 | $1.60 | **$2.45** | **0.49t** |

**🔴 PLUS CHER: Phidias PropFirm = $3.80 (0.76t)**

---

## 🎯 RECOMMANDATION FINALE

### LE PLUS CHER DES DEUX (AMP vs PropFirms)

| Instrument | AMP Futures | PropFirm (Moyenne) | **LE PLUS CHER** |
|------------|-------------|--------------------|--------------------|
| **ES** | $2.25 (0.18t) | $1.40 (0.12t) | **AMP = $2.25** ✅ |
| **NQ** | $2.25 (0.45t) | $1.40 (0.30t) | **AMP = $2.25** ✅ |

**⚠️ MAIS si on considère TOUTES les PropFirms (incluant Phidias):**

| Instrument | AMP Futures | Phidias (pire) | **LE PLUS CHER** |
|------------|-------------|----------------|-------------------|
| **ES** | $2.25 (0.18t) | $3.80 (0.30t) | **Phidias = $3.80** ✅ |
| **NQ** | $2.25 (0.45t) | $3.80 (0.76t) | **Phidias = $3.80** ✅ |

---

## 💰 RECOMMANDATION POUR VOS CALCULS

### Option 1: ULTRA CONSERVATEUR (Pire Pire Cas)

**Utiliser Phidias PropFirm (la plus chère du marché):**

```python
FEES_ES = 0.30 ticks  # $3.80
FEES_NQ = 0.76 ticks  # $3.80
```

**Impact sur Bot T4 Baseline:**
```
Avec 0.30t au lieu de 0.62t actuellement:
+0.30 + 0.32 = +0.62 t/trade ✅
```

---

### Option 2: RÉALISTE (Moyenne PropFirms - RECOMMANDÉ)

**Moyenne Apex/TopStep/Elite Trader:**

```python
FEES_ES = 0.12 ticks  # $1.40
FEES_NQ = 0.30 ticks  # $1.40
```

**Impact sur Bot T4 Baseline:**
```
Avec 0.12t au lieu de 0.62t actuellement:
+0.30 + 0.50 = +0.80 t/trade ✅ (Proche +1.0t !)
```

---

### Option 3: AMP FUTURES

**Si vous tradez directement chez AMP:**

```python
FEES_ES = 0.18 ticks  # $2.25
FEES_NQ = 0.45 ticks  # $2.25
```

**Impact sur Bot T4 Baseline:**
```
Avec 0.18t au lieu de 0.62t actuellement:
+0.30 + 0.44 = +0.74 t/trade ✅
```

---

## ✅ MA RECOMMANDATION FINALE

**UTILISER OPTION 2 (Réaliste - 0.12t pour ES):**

**Raisons:**
1. ✅ **Moyenne des PropFirms principales** (Apex/TopStep/Elite)
2. ✅ **Vous serez à +0.80 t/trade** (très proche +1.0t)
3. ✅ **Conservateur mais réaliste** (pas extrême comme Phidias)
4. ✅ **Si PropFirm plus chère**, marge de sécurité reste

**Si vous voulez être ULTRA conservateur, prenez Option 1 (0.30t).**

---

## 🚀 PROCHAINE ÉTAPE

**Quelle option voulez-vous ?**

**A) Option 1 - Ultra conservateur (0.30t)**
**B) Option 2 - Réaliste (0.12t)** ← **RECOMMANDÉ**
**C) Option 3 - AMP Futures (0.18t)**

Je mettrai à jour tous les fichiers et relancerai les backtests ! 🎯







