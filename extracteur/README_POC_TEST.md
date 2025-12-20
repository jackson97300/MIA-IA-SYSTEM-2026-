# 🧪 POC : Test Day Change % - Mode d'emploi

**Fichier** : `Test_DayChangePct_POC.cpp`
**Objectif** : Valider l'approche "Previous Close" avant intégration dans MIA_Dumper
**Durée estimée** : 10-15 minutes

---

## 🎯 **CE QUE CE POC FAIT**

Ce custom study Sierra Chart **compare deux méthodes** de calcul de `day_change_pct` :

1. **MÉTHODE 1** (Nouvelle) : Depuis **Previous Close / Settlement** (via Daily Chart)
2. **MÉTHODE 2** (Ancienne) : Depuis **Session Open** (18h00 EST)

Il affiche :
- ✅ Les deux résultats en temps réel
- ✅ La différence entre les deux méthodes
- ✅ Des logs détaillés dans le Message Log

---

## 📋 **ÉTAPES D'INSTALLATION**

### **ÉTAPE 1 : Compiler le POC**

#### **Option A : Build avec Sierra Chart** (Recommandé)

1. Copier `Test_DayChangePct_POC.cpp` dans :
   ```
   C:\SierraChart\ACS_Source\
   ```

2. Dans Sierra Chart :
   - Menu **Analysis > Build Custom Studies DLL**
   - Sélectionner **Test_DayChangePct_POC.cpp**
   - Cliquer **Build**
   - Attendre le message "Build Successful"

#### **Option B : Build manuel avec MSVC**

```powershell
# Ouvrir Developer Command Prompt for VS
cd D:\MIA_IA_system\extracteur

# Compiler
cl.exe /LD /EHsc /O2 /MD ^
  /I"C:\SierraChart" ^
  Test_DayChangePct_POC.cpp ^
  /link /OUT:Test_DayChangePct_POC.dll

# Copier dans Sierra Chart
copy Test_DayChangePct_POC.dll "C:\SierraChart\Data\Test_DayChangePct_POC.dll"
```

---

### **ÉTAPE 2 : Créer un Daily Chart pour NQ**

1. Dans Sierra Chart, ouvrir un **nouveau chart**
2. Configurer :
   - **Symbol** : `NQZ25_FUT_CME` (ou votre symbole NQ)
   - **Timeframe** : `Daily`
   - **Chart Number** : Noter le numéro (ex: Chart #10)
3. Vérifier que le chart charge les données historiques
4. **IMPORTANT** : Laisser ce chart ouvert

---

### **ÉTAPE 3 : Ajouter le POC sur votre chart intraday NQ**

1. Ouvrir votre chart **intraday NQ** (1 seconde, 1 minute, etc.)
2. Menu **Analysis > Studies**
3. Cliquer **Add Custom Study**
4. Sélectionner **Test Day Change % POC**
5. Cliquer **Add**

---

### **ÉTAPE 4 : Configurer les Inputs**

Dans la fenêtre d'inputs de l'étude :

| Input | Valeur | Description |
|-------|--------|-------------|
| **Daily Chart Number** | `10` | Le numéro du Daily Chart créé à l'étape 2 |
| **Enable Debug Logs** | `Yes` | Activer les logs détaillés |

Cliquer **OK**

---

## 📊 **INTERPRÉTATION DES RÉSULTATS**

### **1. Graphique**

Vous verrez **3 lignes** :

- **Ligne VERTE (Settlement)** : Day Change % calculé depuis le previous close ✅
- **Ligne ROUGE pointillée (Session Open)** : Day Change % depuis session start ❌
- **Ligne JAUNE (Delta)** : Différence entre les deux méthodes

### **2. Message Log**

Menu **Global Settings > Message Log** :

```
========== TEST DAY CHANGE PCT ==========
Prix Actuel           : 25880.00
------------------------------------------
MÉTHODE 1 (Settlement - NOUVELLE):
  Previous Close      : 26000.00
  Day Change %        : -0.4615%
------------------------------------------
MÉTHODE 2 (Session Open - ANCIENNE):
  Session Open        : 25500.00
  Day Change %        : +1.4902%
------------------------------------------
DIFFÉRENCE            : -1.9517% (Settlement - SessionOpen)
STATUT : ❌ ÉCART IMPORTANT (>= 1%) - Gap overnight détecté
==========================================
VALIDATION : Comparez 'Day Change % (Settlement)' avec :
  - CME Group : https://www.cmegroup.com/...
  - TradingView : https://www.tradingview.com/...
```

---

## ✅ **VALIDATION**

### **Test 1 : Vérifier que le Daily Chart fonctionne**

- ✅ Previous Close doit être **> 0** (ex: 26000.00)
- ✅ Previous Close doit être **cohérent** avec le close d'hier
- ❌ Si Previous Close = 0 → **Problème** : Daily Chart mal configuré

### **Test 2 : Comparer avec sources officielles**

Ouvrir dans votre navigateur :

1. **CME Group** : https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.html
   - Noter le "Change" affiché (ex: -0.46%)

2. **TradingView** : https://www.tradingview.com/symbols/CME_MINI-NQ1!/
   - Noter le "%" de variation (ex: -0.46%)

3. **Comparer** :
   ```
   CME / TradingView : -0.46%
   Notre Settlement  : -0.46%  ✅ MATCH !
   Notre SessionOpen : +1.49%  ❌ INCORRECT
   ```

### **Critère de succès** :

✅ **Écart Settlement vs CME < 0.05%** → Méthode validée !
❌ **Écart Settlement vs CME > 0.05%** → Problème à investiguer

---

## 🔍 **TROUBLESHOOTING**

### **Problème 1 : Previous Close = 0**

**Cause** : Daily Chart non configuré ou mal référencé

**Solution** :
1. Vérifier que le Daily Chart existe et affiche des données
2. Vérifier le numéro du chart (Input "Daily Chart Number")
3. Redémarrer l'étude (Remove puis Add à nouveau)

---

### **Problème 2 : Session Open = 0**

**Cause** : Pas assez d'historique intraday chargé

**Solution** :
1. Menu **Edit > Intraday Data Settings**
2. Augmenter "Days To Load" à au moins 2
3. Recharger le chart (F5)

---

### **Problème 3 : Les deux méthodes donnent le même résultat**

**Cause** : Vous testez pendant RTH (09h30-16h00) sans gap overnight

**Solution** :
- Tester pendant ETH (18h00-09h30) quand il y a un gap
- Ou vérifier les logs historiques (scroller dans le passé)

---

### **Problème 4 : Compilation échoue**

**Erreur** : `scsf.h not found`

**Solution** :
```cpp
// Dans le fichier, remplacer la première ligne par :
#include "C:\SierraChart\scsf.h"
```

**Erreur** : `unresolved external symbols`

**Solution** : Utiliser la méthode **Option A** (Build via Sierra Chart)

---

## 📈 **EXEMPLES DE RÉSULTATS ATTENDUS**

### **CAS 1 : Gap Overnight Important (NQ/ES)**

```
Prix Actuel         : 25880.00
Previous Close      : 26000.00  (Settlement 16h J-1)
Session Open        : 25500.00  (Réouverture 18h J)

Settlement Method   : -0.46%  ✅ Match CME
SessionOpen Method  : +1.49%  ❌ Incorrect
Delta               : -1.95%  (Gap overnight)
```

### **CAS 2 : Pas de Gap (GC/CL ou mid-session)**

```
Prix Actuel         : 3950.00
Previous Close      : 3948.00
Session Open        : 3948.00  (Pas de gap)

Settlement Method   : +0.05%  ✅
SessionOpen Method  : +0.05%  ✅
Delta               : 0.00%   (Pas d'écart)
```

---

## 🎯 **CRITÈRES DE VALIDATION FINALE**

Avant d'intégrer dans MIA_Dumper, **TOUS ces critères doivent être vérifiés** :

- [ ] **Previous Close > 0** et cohérent avec la veille
- [ ] **Écart Settlement vs CME < 0.05%** sur NQ
- [ ] **Écart Settlement vs CME < 0.05%** sur ES (si disponible)
- [ ] **Les logs s'affichent correctement** dans Message Log
- [ ] **Le graphique affiche les 3 lignes** correctement
- [ ] **Delta significatif** (1-3%) détecté pendant gaps overnight

**Si TOUS ✅ → Approche validée ! Prêt pour intégration dans MIA_Dumper**

---

## 🚀 **PROCHAINES ÉTAPES APRÈS VALIDATION**

1. ✅ Documenter les résultats de validation (screenshot + logs)
2. ✅ Intégrer le code dans `MIA_Dumper_G3_Unifier.cpp`
3. ✅ Tester sur les 5 marchés (NQ, ES, RTY, GC, CL)
4. ✅ Déployer en production

---

## 📞 **SUPPORT**

Si problème :
1. Vérifier les logs Sierra Chart : **Global Settings > Message Log**
2. Vérifier que le Daily Chart #10 existe et affiche des données
3. Consulter `SIERRA_CHART_NATIVE_SOLUTIONS.md` pour détails techniques

---

**Temps estimé total** : 10-15 minutes
**Prérequis** : Sierra Chart installé, accès à un data feed NQ
**Niveau** : Intermédiaire

**Bon test ! 🧪**
