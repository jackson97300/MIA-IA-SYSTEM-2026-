# AUDIT COMPLET - DIAGNOSTIC PERFORMANCE DECEVANTE LIGHTGBM

**Date:** 2025-11-15 03:20:14

---

## RESUME EXECUTIF

**Issues critiques:** 3
**Issues high:** 1
**Issues medium:** 1
**Warnings:** 3

---

## ISSUES CRITIQUES

### 1. Features Mismatch

**Severite:** CRITICAL

**Description:** 2 features utilisees pour training sont ABSENTES lors prediction

**Features concernees (2):**
- `pnl_ticks`
- `duration_minutes`

---

### 2. Feature Engineering Not Applied

**Severite:** CRITICAL

**Description:** 20 features engineered n'ont PAS ete calculees

**Features concernees (20):**
- `delta_intensity`
- `depth_imbalance_ratio`
- `vwap_atr_ratio`
- `gamma_position`
- `flow_direction`
- `gex_proximity_min`
- `range_bias`
- `efficiency_ratio`
- `dom_slope_ratio`
- `confluence_delta`
- `layer1_layer2_interaction`
- `next_wall_weighted`
- `blind_gex_confluence`
- `vwap_hvl_regime`
- `delta_session_ratio`
- `volume_atr_intensity`
- `approaching_1d_max`
- `approaching_1d_min`
- `range_expansion`
- `vix_atr_volatility`

---

### 3. Prediction Error

**Severite:** CRITICAL

**Description:** Impossible de faire prediction: 'dict' object has no attribute 'predict'

---

## AUTRES ISSUES

### 1. Missing Values (HIGH)

2 colonnes avec NaNs

**Top colonnes:**
- `confluence`: 3
- `ml_confidence`: 3

---

### 2. Constant Features (MEDIUM)

1 features n'ont aucune variance

**Colonnes (1):** `vix`

---

## WARNINGS

1. **Features Extra** (LOW): 7 features disponibles mais non utilisees

2. **Extreme Values** (MEDIUM): 1 colonnes avec valeurs potentiellement aberrantes

3. **No Scaling** (MEDIUM): Pas de StandardScaler ou normalisation appliquee
   - Impact: Features avec echelles differentes peuvent biaiser le modele

---

## RECOMMENDATIONS

### 1. Appliquer feature engineering lors du labeling (Priorite: HIGH)

Les features engineered doivent etre calculees AVANT de sauvegarder labeled_trades.parquet

---

### 2. Ajouter StandardScaler au pipeline (Priorite: MEDIUM)

Normaliser les features avant training pour ameliorer convergence

---


---

*Fin du rapport d'audit*
