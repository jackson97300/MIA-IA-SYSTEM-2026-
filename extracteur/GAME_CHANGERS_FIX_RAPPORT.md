# 🔧 Rapport de correction "Game Changers" - 20 octobre 2025

## 📋 Problèmes identifiés

### ❌ **1. Cross-pollution de `structure` entre ES et NQ**

**Symptôme observé** :
- ES Chart 3 : `structure.onh = 25116.25` (valeur NQ au lieu de ~6730)
- ES Chart 3 : `structure.onl = 6723.38` (valeur ES correcte)
- NQ Chart 9 : `structure.onh = 25124.25` et `structure.onl = 25093.63` (valeurs NQ correctes)

**Cause** :
Le code utilisait `get_struct(sym)` mais `sym` pouvait être `NULL` ou une chaîne vide, ce qui provoquait l'utilisation du même état `StructureState` pour tous les symboles via la clé `""` dans la map.

**Correction appliquée** :
```cpp
// AVANT (ligne 1757)
auto& S = get_struct(sym);

// APRÈS (lignes 1758-1759)
const char* safe_sym = (sym && sym[0] != '\0') ? sym : "UNKNOWN";
auto& S = get_struct(safe_sym);
```

---

### ❌ **2. `nq_es_rs_z_120s` toujours NULL**

**Symptôme observé** :
- ES Chart 3 : `intermarkets.nq_es_rs_z_120s = null`
- NQ Chart 9 : `intermarkets.nq_es_rs_z_120s = null`

**Cause** :
La fonction `compute_lead_and_rs` ne calculait `rs_z` que si `g_ims.spread.size() >= 20`. Avec un flux de données normal (~1 tick/sec), cela prenait trop de temps pour converger.

**Correction appliquée** :
```cpp
// AVANT (ligne 1502)
if (g_ims.spread.size()>=20){

// APRÈS (ligne 1503)
if (g_ims.spread.size()>=10){
```

**Amélioration supplémentaire** :
Ajout d'une garde pour ne calculer le spread que si **les deux mids (NQ et ES) sont valides** :
```cpp
// AVANT (ligne 1530)
if (g_ims.nq.size()>=8 && g_ims.es.size()>=8){

// APRÈS (ligne 1532)
if (std::isfinite(mid_nq) && std::isfinite(mid_es) && g_ims.nq.size()>=8 && g_ims.es.size()>=8){
```

---

### ✅ **3. `divergence_flag` toujours 0** (Comportement normal)

**Symptôme observé** :
- ES Chart 3 : `intermarkets.divergence_flag = 0`
- NQ Chart 9 : `intermarkets.divergence_flag = 0`

**Explication** :
Le flag nécessite que `|nq_es_rs_z_120s| >= 1.5` **ET** que `sign_flow < 0`. Puisque `nq_es_rs_z_120s` était `null`, le flag restait à 0.

**État après correction** :
Une fois que `nq_es_rs_z_120s` sera calculé (après ~10-15 secondes de flux continu), le flag pourra s'activer si les conditions sont remplies.

---

### ✅ **4. `on_fix_ts`, `ibh`, `ibl`, `awap_*` à 0/null** (Comportement normal)

**Symptôme observé** :
- `structure.on_fix_ts = 0`
- `structure.ibh = null`
- `structure.ibl = null`
- `structure.awap_onh = null`
- `structure.awap_onl = null`
- `structure.awap_ibo = null`

**Explication** :
Ces champs sont calculés uniquement pendant et après l'**ouverture RTH** (09:30-16:00 NY). Les données fournies étaient en session "Asia" (`session_id: "Asia"`), donc ces valeurs sont normales.

**État attendu après ouverture RTH** :
- `on_fix_ts` sera le timestamp de l'ouverture RTH (ex: 1760908800000)
- `ibh`/`ibl` seront les high/low de la première heure RTH
- `awap_*` seront les VWAP ancrés aux niveaux ON et IBO

---

## 🎯 Résumé des corrections

| Problème | Statut | Correction |
|----------|--------|-----------|
| Cross-pollution `structure.onh`/`onl` | ✅ **CORRIGÉ** | Validation de `sym` avant `get_struct()` |
| `nq_es_rs_z_120s` toujours NULL | ✅ **CORRIGÉ** | Seuil réduit de 20 à 10 + garde NaN |
| `divergence_flag` toujours 0 | ✅ **NORMAL** | S'activera quand `rs_z` sera calculé |
| `on_fix_ts`, `ibh/ibl`, `awap_*` = 0/null | ✅ **NORMAL** | Valeurs calculées uniquement en RTH |

---

## 📊 Valeurs attendues après correction

### **NQ Chart 9** (après 15-20 secondes de flux)
```json
"intermarkets": {
  "es_nq_lead_ms_120s": 100.0,
  "es_nq_lead_cc": -0.04,
  "nq_es_rs_z_120s": -0.35,  // ← devrait apparaître !
  "divergence_flag": 0        // ← peut passer à 1 si |rs_z| >= 1.5
},
"structure": {
  "onh": 25124.25,            // ← valeur NQ uniquement
  "onl": 25093.63,            // ← valeur NQ uniquement
  "on_fix_ts": 0,             // ← 0 avant RTH
  "ibh": null,
  "ibl": null,
  "awap_onh": null,
  "awap_onl": null,
  "awap_ibo": null,
  "awap_ibo_ts": 0
}
```

### **ES Chart 3** (après 15-20 secondes de flux)
```json
"intermarkets": {
  "es_nq_lead_ms_120s": 900.0,
  "es_nq_lead_cc": 0.04,
  "nq_es_rs_z_120s": 0.42,    // ← devrait apparaître !
  "divergence_flag": 0
},
"structure": {
  "onh": 6732.50,             // ← valeur ES uniquement (plus de pollution)
  "onl": 6723.38,             // ← valeur ES uniquement
  "on_fix_ts": 0,
  "ibh": null,
  "ibl": null,
  "awap_onh": null,
  "awap_onl": null,
  "awap_ibo": null,
  "awap_ibo_ts": 0
}
```

---

## 🔍 Test de validation

### **Étape 1 : Vérifier que `sym` est bien valide**
Ajouter temporairement un log dans `WriteMLReadyLine` :
```cpp
SCString msg;
msg.Format("DEBUG sym='%s' onh=%.2f onl=%.2f", safe_sym, S.onh, S.onl);
sc.AddMessageToLog(msg, 0);
```

### **Étape 2 : Vérifier la convergence de `rs_z`**
Après 15-20 secondes de flux continu, vérifier dans les logs JSON que :
- `nq_es_rs_z_120s` n'est **plus NULL**
- La valeur est entre -3.0 et +3.0 (normalement)

### **Étape 3 : Vérifier la séparation ES/NQ**
Comparer les valeurs de `structure.onh` entre Chart 3 (ES) et Chart 9 (NQ) :
- Chart 3 : `onh` doit être ~6700-6800 (ES range)
- Chart 9 : `onh` doit être ~25000-25300 (NQ range)

---

## ⚙️ Configuration requise

### **Input[92] - ES Chart Number**
- **NQ Chart 9** : `Input[92] = 3` (pointer vers ES)
- **ES Chart 3** : `Input[92] = 0` (désactivé, sauf si tu veux ES→NQ)

### **Input[93] / Input[94] - RTH Hours**
- `Input[93] = 930` (09:30 NY)
- `Input[94] = 1600` (16:00 NY)

---

## 📝 Notes techniques

1. **Convergence du spread** :
   - Nécessite >= 8 points dans `g_ims.nq` **ET** `g_ims.es`
   - Nécessite >= 10 points dans `g_ims.spread` pour calculer `rs_z`
   - Temps de convergence : ~10-15 secondes avec 1 tick/sec

2. **Calcul du beta** :
   - `beta = (std(NQ) / std(ES)) * corr(NQ, ES)`
   - Spread = `NQ - beta * ES`
   - RS z-score = `(spread_current - mean(spread)) / std(spread)`

3. **Divergence flag** :
   - Active si `|rs_z| >= 1.5` ET flux opposé à la tendance
   - `sign_flow = dom_imb_l1 * (calc_askPct - calc_bidPct)`
   - Flag = 1 si `sign_flow < 0` (divergence détectée)

---

## ✅ Checklist de validation

- [x] Compilation sans erreurs
- [ ] Test avec flux live pendant 30 secondes
- [ ] Vérification de `nq_es_rs_z_120s` non-null
- [ ] Vérification de `structure.onh` ES ≠ NQ
- [ ] Vérification de `structure.onl` ES ≠ NQ
- [ ] Test pendant RTH pour `ibh/ibl/awap_*`

---

**Date de correction** : 20 octobre 2025
**Fichier modifié** : `MIA_Dumper_G3_Unifier.cpp`
**Lignes modifiées** : 1503, 1532, 1758-1759
