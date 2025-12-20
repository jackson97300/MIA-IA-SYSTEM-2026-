# 🔧 PATCH DUMPER C++ - ADVANCED METRICS V1
**Date**: 04 Novembre 2025
**Version**: V1 (Quick Wins - 7 Features)
**Fichier cible**: `extracteur/MIA_Dumper_G3_Unifier.cpp`
**Mode**: ADDITIF (on ajoute, on ne casse RIEN)

---

## ✅ FEATURES AJOUTÉES (7)

1. **mia_bullish_score** - Score bullish/bearish unifié
2. **sell_pct** / **buy_pct** - Renommage clarification sémantique
3. **delta_burst** - Magnitude changement delta
4. **delta_flip** - Retournement signe delta
5. **upper_wick_ticks** - Mèche haute (rejection haut)
6. **lower_wick_ticks** - Mèche basse (rejection bas)
7. **total_range_ticks** - Range total de la barre

---

## 📍 LOCALISATION DES MODIFICATIONS

### **SECTION 1 : Après ligne ~514 (Calcul des ratios)**

**AVANT** :
```cpp
// ratios
const double tv = (double) (std::max<long long>(1, (long long)total_vol));
const double calc_askPct   = (double)askVolume / tv;
const double calc_bidPct   = (double)bidVolume / tv;
const double calc_deltaPct = calc_askPct - calc_bidPct;
```

**APRÈS** (AJOUTER ces lignes) :
```cpp
// ratios
const double tv = (double) (std::max<long long>(1, (long long)total_vol));
const double calc_askPct   = (double)askVolume / tv;
const double calc_bidPct   = (double)bidVolume / tv;
const double calc_deltaPct = calc_askPct - calc_bidPct;

// === PATCH V1.1: Renommage sémantique (GARDER les anciens noms pour compatibilité) ===
const double calc_sell_pct = calc_askPct;  // askVolume = ventes (hitting ask)
const double calc_buy_pct  = calc_bidPct;  // bidVolume = achats (hitting bid)
// NOTE: On garde calc_askPct/bidPct pour rétro-compatibilité, mais privilégier sell_pct/buy_pct

// === PATCH V1.2: Delta Burst & Flip ===
// Récupérer le delta précédent depuis UnifiedState (ou cache global si dispo)
double prev_delta_val = 0.0;  // TODO: Implémenter cache par symbole si nécessaire
if (U.cum_delta_session != 0) {
    // Approximation: utiliser cum_delta_session pour détecter changements
    prev_delta_val = U.cum_delta_session;  // Ou implémenter cache propre
}

const double delta_burst = std::abs(delta_top - prev_delta_val);
const bool   delta_flip  = (sgn(delta_top) != sgn(prev_delta_val)) && (prev_delta_val != 0);

// === PATCH V1.3: Wicks (depuis OHLC) ===
// OHLC disponibles dans: open, high, low, close (déjà dans le code)
const double upper_wick_ticks = std::max(0.0, (high - std::max(open, close)) / tick);
const double lower_wick_ticks = std::max(0.0, (std::min(open, close) - low) / tick);
const double total_range_ticks = (high > low) ? ((high - low) / tick) : 0.0;

// === PATCH V1.4: MIA Bullish Score ===
// Formule: 40% VWAP + 30% Delta Session + 20% DeltaPct + 10% VA
double mia_bullish_score = 0.0;

// 1. Composante VWAP (40%)
double d_vwap_atr_val = (atr_price > 0) ? ((mid - vwap_v) / atr_price) : 0.0;
double vwap_normalized = std::max(-1.0, std::min(1.0, d_vwap_atr_val / 5.0));
double vwap_contrib = vwap_normalized * 0.4;

// 2. Composante Delta Session (30%)
double delta_session_normalized = std::max(-1.0, std::min(1.0, cum_delta_session / 500.0));
double delta_contrib = delta_session_normalized * 0.3;

// 3. Composante DeltaPct (20%)
double deltapct_contrib = calc_deltaPct * 0.2;

// 4. Composante Value Area (10%)
double va_contrib = 0.0;
if (mid < vva_val) {
    va_contrib = -0.1;  // Sous VAL = bearish
} else if (mid > vva_vah) {
    va_contrib = 0.1;   // Au-dessus VAH = bullish
}

// Score final
mia_bullish_score = vwap_contrib + delta_contrib + deltapct_contrib + va_contrib;
mia_bullish_score = std::max(-1.0, std::min(1.0, mia_bullish_score));  // Clamp [-1, 1]
```

---

### **SECTION 2 : Dans BuildMLReadyJSON15() - Ligne ~886 (après "vix")**

**AVANT** :
```cpp
// === MÉTRIQUES DE MARCHÉ ===
<< "\"corr\":" << format_ratio(corr) << ","
<< "\"vix\":" << format_price(vix) << ","
```

**APRÈS** (AJOUTER ces lignes) :
```cpp
// === MÉTRIQUES DE MARCHÉ ===
<< "\"corr\":" << format_ratio(corr) << ","
<< "\"vix\":" << format_price(vix) << ","

// === PATCH V1: NOUVELLES FEATURES AVANCÉES ===
<< "\"mia_bullish_score\":" << format_ratio(mia_bullish_score) << ","
<< "\"sell_pct\":" << format_ratio(calc_sell_pct) << ","
<< "\"buy_pct\":" << format_ratio(calc_buy_pct) << ","
<< "\"delta_burst\":" << format_size(delta_burst) << ","
<< "\"delta_flip\":" << json_bool(delta_flip) << ","
<< "\"upper_wick_ticks\":" << format_ratio(upper_wick_ticks) << ","
<< "\"lower_wick_ticks\":" << format_ratio(lower_wick_ticks) << ","
<< "\"total_range_ticks\":" << format_ratio(total_range_ticks) << ","
```

---

### **SECTION 3 : Validation (optionnel mais recommandé)**

Après la ligne ~2652 (ValidatePreWrite), ajouter une validation pour les nouvelles features :

```cpp
// === PATCH V1: Validation nouvelles features ===
if (!std::isfinite(mia_bullish_score) || mia_bullish_score < -1.0 || mia_bullish_score > 1.0) {
    // Optionnel: logger ou rejeter
    // return false;  // Si on veut être strict
}
if (!std::isfinite(upper_wick_ticks) || upper_wick_ticks < 0.0) {
    // upper_wick_ticks = 0.0;  // Correction automatique
}
if (!std::isfinite(lower_wick_ticks) || lower_wick_ticks < 0.0) {
    // lower_wick_ticks = 0.0;
}
```

---

## ⚠️ POINTS D'ATTENTION

### **1. Cache Delta Précédent**

Pour `delta_burst` et `delta_flip`, il faut tracker le delta précédent. **DEUX OPTIONS** :

**OPTION A** (Simple, approximation) :
```cpp
// Utiliser cum_delta_session comme proxy
double prev_delta_val = 0.0;  // Acceptable pour V1
```

**OPTION B** (Précis, nécessite cache) :
```cpp
// Créer un cache global par symbole
static std::unordered_map<std::string, double> g_last_delta_by_sym;
double prev_delta_val = g_last_delta_by_sym[std::string(sym)];
g_last_delta_by_sym[std::string(sym)] = delta_top;  // Update après calcul
```

**RECOMMANDATION** : Commencer avec **OPTION A** pour V1, implémenter OPTION B en V2 si nécessaire.

### **2. Variables déjà disponibles**

Ces variables sont **déjà calculées** dans le dumper (ne pas les recalculer) :
- `mid` : Prix médian
- `tick` : Taille de tick
- `open`, `high`, `low`, `close` : OHLC
- `vwap_v` : VWAP
- `atr_price` : ATR
- `vva_val`, `vva_vah` : Value Area Low/High
- `cum_delta_session` : Delta cumulé session
- `askVolume`, `bidVolume`, `delta_top` : Volumes NBCV

### **3. Fonctions helper disponibles**

- `format_ratio(x)` : Formater ratio (6 décimales)
- `format_price(x)` : Formater prix
- `format_size(x)` : Formater taille
- `json_bool(b)` : Convertir bool en JSON "true"/"false"
- `sgn(x)` : Retourne signe (-1, 0, 1)

---

## 🧪 TESTS POST-PATCH

### **Test 1 : Compilation**
```bash
# Recompiler le dumper
# Vérifier 0 erreur, 0 warning
```

### **Test 2 : Vérifier sortie ML_READY**
```bash
# Lire la dernière ligne d'un fichier ML_READY
tail -n 1 DATA_SIERRA_CHART/.../ML_READY/ml_ready_*.jsonl | python -m json.tool

# Vérifier présence des nouveaux champs:
# - mia_bullish_score (float entre -1 et 1)
# - sell_pct, buy_pct (floats entre 0 et 1)
# - delta_burst (float >= 0)
# - delta_flip (true/false)
# - upper_wick_ticks, lower_wick_ticks, total_range_ticks (floats >= 0)
```

### **Test 3 : Cohérence des valeurs**
```python
import json

# Charger une ligne ML_READY
with open('ml_ready_xxx.jsonl') as f:
    data = json.loads(f.readlines()[-1])

# Tests
assert -1.0 <= data['mia_bullish_score'] <= 1.0
assert abs(data['sell_pct'] + data['buy_pct'] - 1.0) < 0.01  # Doivent sommer à 1
assert data['upper_wick_ticks'] >= 0
assert data['lower_wick_ticks'] >= 0
assert data['total_range_ticks'] >= 0
assert isinstance(data['delta_flip'], bool)
print("✅ Tous les tests passés !")
```

---

## 📝 CHECKLIST AVANT COMMIT

- [ ] Code compilé sans erreur
- [ ] Aucune régression (anciennes features toujours présentes)
- [ ] Nouvelles features visibles dans ML_READY
- [ ] Valeurs cohérentes (ranges respectés)
- [ ] Testé sur ES et NQ
- [ ] Documentation mise à jour (ce fichier)

---

## 🎯 PROCHAINES ÉTAPES (PATCH #2)

Après validation du PATCH #1, implémenter :
- `stacked_imbalance_bid_rows` / `_ask_rows`
- `gamma_flip_up` / `_down`
- `quotes_speed_up` (post-processing depuis fichiers quote)

---

**FIN DU PATCH V1**

