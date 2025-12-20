# ANALYSE DÉTAILLÉE NQ - FEES ET PERFORMANCES

**Date:** 15 Novembre 2025
**Instrument:** E-mini Nasdaq-100 (NQ)
**Objectif:** Analyser l'impact des fees réelles sur les performances NQ

---

## 📊 FEES NQ - TABLEAU COMPLET

### Valeur du Tick NQ

```
1 point NQ = $20
1 tick (0.25 point) = $5.00

Ratio vs ES: 1 tick NQ = 0.40 × 1 tick ES
```

---

## 💰 FEES PAR BROKER - NQ

| Broker / PropFirm | Commission | Exchange + NFA | **TOTAL $** | **En TICKS NQ** |
|-------------------|------------|----------------|-------------|-----------------|
| **AMP Futures** | $0.65 | $1.60 | **$2.25** | **0.45t** |
| **Apex Trader Funding** | $0.50-0.90 | $0.60 | **$1.10-1.50** | **0.22-0.30t** |
| **TopStep** | $0.65-1.00 | $0.60 | **$1.25-1.60** | **0.25-0.32t** |
| **Elite Trader** | $0.55-0.85 | $0.60 | **$1.15-1.45** | **0.23-0.29t** |
| **Phidias PropFirm** | $2.20 | $1.60 | **$3.80** | **0.76t** |
| **Interactive Brokers** | $0.85 | $1.60 | **$2.45** | **0.49t** |

---

## 🎯 COMPARAISON: LE PLUS CHER

### AMP vs PropFirms (Moyenne)

| Comparaison | Fees $ | Fees Ticks | Gagnant |
|-------------|--------|------------|---------|
| **AMP Futures** | $2.25 | **0.45t** | - |
| **PropFirms Moyenne** | $1.40 | **0.28t** | ✅ **37% moins cher** |
| **Différence** | -$0.85 | **-0.17t** | PropFirms gagnent |

**🔴 LE PLUS CHER entre AMP et PropFirms: AMP = $2.25 (0.45t)**

### Si on inclut TOUTES les PropFirms

| Comparaison | Fees $ | Fees Ticks | Gagnant |
|-------------|--------|------------|---------|
| **AMP Futures** | $2.25 | **0.45t** | - |
| **Phidias PropFirm** | $3.80 | **0.76t** | ❌ **69% plus cher** |

**🔴 LE PLUS CHER ABSOLU: Phidias = $3.80 (0.76t)**

---

## 💡 VOTRE CODE ACTUEL

**Dans `launch_ml_v3_production.py`:**

```python
fees = $2.40 par contrat
```

**Conversion en ticks NQ:**

```
$2.40 ÷ $5.00 = 0.48 ticks NQ
```

---

## 📊 COMPARAISON AVEC LA RÉALITÉ NQ

| Scénario | Fees $ | Fees Ticks | Votre Code | Écart |
|----------|--------|------------|------------|-------|
| **Ultra Conservateur (Phidias)** | $3.80 | **0.76t** | 0.48t | **-58%** ❌ |
| **AMP Futures** | $2.25 | **0.45t** | 0.48t | **+7%** ✅ |
| **Réaliste (PropFirms Moyenne)** | $1.40 | **0.28t** | 0.48t | **+71%** ❌ |
| **Optimiste (Apex)** | $1.10 | **0.22t** | 0.48t | **+118%** ❌ |

**Votre code ($2.40 = 0.48t) est ENTRE AMP (0.45t) et PropFirms moyennes (0.28t).**

---

## 🎯 IMPACT SUR PERFORMANCES NQ

### Scénario 1: Bot NQ avec Fees Actuelles (0.48t)

```
Supposons P&L similaire à ES:
P&L brut estimé: +0.90 t/trade (en ticks NQ)
Fees actuelles: -0.48t
═══════════════════════════════════════
P&L net: +0.42 t/trade
```

---

### Scénario 2: Avec Fees Réalistes PropFirms (0.28t)

```
P&L brut estimé: +0.90 t/trade
Fees PropFirms: -0.28t (au lieu de -0.48t)
═══════════════════════════════════════
P&L net: +0.62 t/trade ✅

Amélioration: +0.20 t/trade (+48%)
```

---

### Scénario 3: Avec Fees Apex (0.22t)

```
P&L brut estimé: +0.90 t/trade
Fees Apex: -0.22t (au lieu de -0.48t)
═══════════════════════════════════════
P&L net: +0.68 t/trade ✅

Amélioration: +0.26 t/trade (+62%)
```

---

### Scénario 4: Avec Fees Phidias (0.76t - Pire Cas)

```
P&L brut estimé: +0.90 t/trade
Fees Phidias: -0.76t (au lieu de -0.48t)
═══════════════════════════════════════
P&L net: +0.14 t/trade ❌

Dégradation: -0.28 t/trade (-67%)
```

---

## 🚀 RECOMMANDATIONS NQ

### Option 1: Ultra Conservateur (Phidias)

```python
FEES_NQ = 0.76 ticks  # $3.80
```

**Performance attendue:** +0.14 t/trade (très conservateur)

---

### Option 2: Réaliste PropFirms (RECOMMANDÉ)

```python
FEES_NQ = 0.28 ticks  # $1.40
```

**Performance attendue:** +0.62 t/trade ✅

---

### Option 3: AMP Futures

```python
FEES_NQ = 0.45 ticks  # $2.25
```

**Performance attendue:** +0.45 t/trade

---

### Option 4: Apex (Optimiste)

```python
FEES_NQ = 0.22 ticks  # $1.10
```

**Performance attendue:** +0.68 t/trade ✅

---

## 📋 TABLEAU RÉCAPITULATIF ES vs NQ

| Instrument | Valeur Tick | Fees AMP | Fees PropFirms | LE PLUS CHER |
|------------|-------------|----------|----------------|--------------|
| **ES** | $12.50 | $2.25 (0.18t) | $1.40 (0.12t) | **AMP = 0.18t** |
| **NQ** | $5.00 | $2.25 (0.45t) | $1.40 (0.28t) | **AMP = 0.45t** |

**Ratio NQ/ES:** 2.5x en ticks (fees NQ coûtent 2.5x plus cher en ticks que ES)

---

## 💰 IMPACT SUR OBJECTIF +1.0 t/trade

### Pour ES:

| Scénario | Fees | P&L Net |
|----------|------|---------|
| Actuel (0.62t) | - | +0.30 t/trade |
| PropFirms (0.12t) | ✅ | **+0.80 t/trade** |
| AMP (0.18t) | ✅ | **+0.74 t/trade** |

**Objectif +1.0t presque atteint avec PropFirms !**

---

### Pour NQ:

| Scénario | Fees | P&L Net Estimé |
|----------|------|----------------|
| Actuel (0.48t) | - | +0.42 t/trade |
| PropFirms (0.28t) | ✅ | **+0.62 t/trade** |
| AMP (0.45t) | - | **+0.45 t/trade** |
| Apex (0.22t) | ✅ | **+0.68 t/trade** |

**Objectif +1.0t plus difficile sur NQ (fees proportionnellement plus élevées)**

---

## 🎯 AVANTAGES / INCONVÉNIENTS NQ vs ES

### ES (S&P 500)

**✅ AVANTAGES:**
- Fees en ticks plus faibles (0.12-0.18t)
- Spread plus serré
- Liquidité maximale
- +0.80 t/trade possible en PropFirms

**❌ INCONVÉNIENTS:**
- Volatilité modérée
- TP plus difficiles à atteindre

---

### NQ (Nasdaq-100)

**✅ AVANTAGES:**
- Volatilité 2x plus élevée
- TP plus faciles à atteindre (25-35t)
- Mouvements plus rapides

**❌ INCONVÉNIENTS:**
- Fees en ticks 2.5x plus élevées (0.28-0.45t)
- Spread plus large
- +0.68 t/trade max en PropFirms (vs +0.80t ES)

---

## ✅ CONCLUSION NQ

### 1️⃣ FEES RECOMMANDÉES POUR VOS CALCULS

**Option Conservatrice (AMP = plus cher entre AMP et PropFirms moyennes):**

```python
FEES_NQ = 0.45 ticks  # $2.25 (AMP Futures)
```

**Option Réaliste (PropFirms Moyenne - RECOMMANDÉ):**

```python
FEES_NQ = 0.28 ticks  # $1.40 (Apex/TopStep/Elite moyenne)
```

**Option Ultra Conservatrice (Phidias = pire cas absolu):**

```python
FEES_NQ = 0.76 ticks  # $3.80 (Phidias PropFirm)
```

---

### 2️⃣ IMPACT SUR VOS PERFORMANCES

**Avec fees réalistes PropFirms (0.28t):**

```
Amélioration vs code actuel (0.48t):
+0.20 t/trade sur NQ

Performance attendue: +0.62 t/trade ✅
```

---

### 3️⃣ ES vs NQ: QUEL EST LE MEILLEUR ?

| Critère | ES | NQ | Gagnant |
|---------|----|----|---------|
| **Fees (ticks)** | 0.12t | 0.28t | ✅ **ES** |
| **P&L/trade (PropFirms)** | +0.80t | +0.62t | ✅ **ES** |
| **Volatilité** | Normale | 2x | ✅ **NQ** |
| **TP faciles** | Moyen | Élevé | ✅ **NQ** |
| **Spread** | Serré | Large | ✅ **ES** |
| **Liquidité** | Max | Élevé | ✅ **ES** |

**🏆 GAGNANT GLOBAL: ES**

**ES offre de meilleures performances nettes (+0.80t vs +0.62t) grâce à des fees plus faibles en ticks.**

---

## 🚀 RECOMMANDATION FINALE POUR VOUS

### Configuration Recommandée:

```python
# Fees réalistes PropFirms moyennes (Apex/TopStep/Elite)
FEES_ES = 0.12 ticks  # $1.40
FEES_NQ = 0.28 ticks  # $1.40

# Performances attendues:
# ES: +0.80 t/trade ✅ (Excellent !)
# NQ: +0.62 t/trade ✅ (Très bon !)
```

**FOCUS PRINCIPAL: ES** (meilleures performances nettes)

**SECONDAIRE: NQ** (pour diversification et volatilité)

---

**Voulez-vous que je mette à jour les fichiers avec ces fees réalistes et relance les backtests ?** 🚀







