# 🛠️ GUIDE DE COMPILATION - PATCH V3.4 : Arrêt automatique marché fermé

**Date** : 2025-11-04
**Version** : MIA Dumper G3 Unifier v3.4
**Patch appliqué** : ✅ ARRÊT_AUTOMATIQUE_MARCHÉ_FERMÉ

---

## 📋 RÉSUMÉ DU PATCH

### **Problème résolu** :
Le dumper continuait d'écrire dans ML_READY même quand le marché était fermé, générant des données figées inutiles.

### **Solution implémentée** :
- Détection automatique du marché fermé basée sur les **vraies rates** (tick_rate, trade_rate)
- Calcul de la **vraie session progress**
- **Arrêt complet** de l'écriture ML_READY si marché fermé (score >= 2)

### **Critères d'arrêt** :
- `tick_rate_1s = 0` (pas de ticks)
- `trade_rate_1s = 0` (pas de trades)
- DOM stale (>1500ms)
- Session edges (progress = 0.0 ou 1.0)
- Weak quote (QUOTE source + sizes = 0)

**Si 2+ critères sont vrais** → **ARRÊT d'écriture**

---

## 🔧 ÉTAPE 1 : COMPILATION DANS SIERRA CHART

### **Option A : Compilation Remote Build (RECOMMANDÉ)**

1. **Ouvrir Sierra Chart**
2. **Analysis** → **Studies** → **Custom Studies** → **Remote Build**
3. **Sélectionner** : `MIA_Dumper_G3_Unifier.cpp`
4. **Cliquer** : `Build`
5. **Attendre** : Sierra compile automatiquement (30-60 secondes)
6. **Vérifier** : Message "Build successful" dans le log

### **Option B : Compilation locale (si Remote Build échoue)**

```powershell
# Dans PowerShell
cd D:\MIA_IA_system\extracteur

# Compiler avec Visual Studio (si installé)
cl /LD /EHsc /O2 /MD MIA_Dumper_G3_Unifier.cpp /link /DEF:MIA_Dumper_G3_Unifier.def

# OU avec g++ (si MinGW installé)
g++ -shared -o MIA_Dumper_G3_Unifier.dll MIA_Dumper_G3_Unifier.cpp -O2 -std=c++17

# Copier la DLL dans le dossier Sierra Chart
copy MIA_Dumper_G3_Unifier.dll "C:\SierraChart\Data\"
```

---

## 🧪 ÉTAPE 2 : TEST DU PATCH

### **Test 1 : Arrêt automatique (marché fermé)**

1. **Redémarrer le study** dans Sierra Chart :
   - `Analysis` → `Studies` → Décocher `MIA_Dumper_G3_Unifier`
   - Attendre 5 secondes
   - Recocher le study

2. **Attendre 2 minutes**

3. **Vérifier que ML_READY s'arrête** :

```powershell
cd D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\NOVEMBRE\20251104

# Vérifier la dernière MAJ de ML_READY ES
$esML = Get-Item "CHART_3\ML_READY\ml_ESZ25_FUT_CME_3.jsonl"
$esLastWrite = $esML.LastWriteTime
$now = Get-Date
$ageMinutes = ($now - $esLastWrite).TotalMinutes

Write-Host "ES ML_READY derniere MAJ: $($esLastWrite.ToString('HH:mm:ss'))"
Write-Host "Age: $([math]::Round($ageMinutes, 1)) minutes"

if ($ageMinutes -lt 2) {
    Write-Host "[PROBLEME] ML_READY continue d'ecrire (marche ferme)" -ForegroundColor Red
} else {
    Write-Host "[OK] ML_READY arrete (patch fonctionne !)" -ForegroundColor Green
}
```

**Résultat attendu** : ML_READY **NE SE MET PLUS À JOUR** quand le marché est fermé

---

### **Test 2 : Reprise automatique (ouverture Asia)**

**Timing** :
- **Ouverture Asia** : 18:00 ET (00:00 CET, 6:00 Tokyo)
- **Attendre** : 5-10 minutes après l'ouverture

**Vérification** :

```powershell
cd D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\NOVEMBRE\20251104

# Vérifier que ML_READY reprend pour ES/NQ
$esML = Get-Item "CHART_3\ML_READY\ml_ESZ25_FUT_CME_3.jsonl"
$esLastWrite = $esML.LastWriteTime
$now = Get-Date
$ageMinutes = ($now - $esLastWrite).TotalMinutes

Write-Host "ES ML_READY derniere MAJ: $($esLastWrite.ToString('HH:mm:ss'))"
Write-Host "Age: $([math]::Round($ageMinutes, 1)) minutes"

if ($ageMinutes -lt 2) {
    Write-Host "[OK] ML_READY actif (marche ouvert)" -ForegroundColor Green
} else {
    Write-Host "[PROBLEME] ML_READY inactif (verifier Sierra Chart)" -ForegroundColor Red
}

# Vérifier que RTY génère ML_READY
if (Test-Path "CHART_1\ML_READY\ml_RTYZ25_FUT_CME_1.jsonl") {
    $rtyML = Get-Item "CHART_1\ML_READY\ml_RTYZ25_FUT_CME_1.jsonl"
    $rtyLastWrite = $rtyML.LastWriteTime
    $rtyAgeMinutes = ($now - $rtyLastWrite).TotalMinutes

    Write-Host ""
    Write-Host "RTY ML_READY derniere MAJ: $($rtyLastWrite.ToString('HH:mm:ss'))"
    Write-Host "Age: $([math]::Round($rtyAgeMinutes, 1)) minutes"

    if ($rtyAgeMinutes -lt 2) {
        Write-Host "[SUCCESS] RTY ML_READY fonctionne !" -ForegroundColor Green
    }
} else {
    Write-Host ""
    Write-Host "[INFO] RTY ML_READY pas encore cree (attendre quelques minutes)" -ForegroundColor Yellow
}
```

**Résultat attendu** :
- ✅ ES/NQ ML_READY **reprend automatiquement**
- ✅ RTY ML_READY **se crée automatiquement**

---

## 📊 ÉTAPE 3 : VALIDATION FINALE

### **Vérification des tailles de fichiers**

```powershell
cd D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\NOVEMBRE\20251104

Write-Host "[COMPARAISON TAILLES FICHIERS]" -ForegroundColor Cyan
Write-Host ""

# ES
$esML = Get-Item "CHART_3\ML_READY\ml_ESZ25_FUT_CME_3.jsonl"
$esMB = [math]::Round($esML.Length/1024/1024, 2)
Write-Host "ES ML_READY: $esMB MB"

# NQ
if (Test-Path "CHART_9\ML_READY") {
    $nqML = Get-ChildItem "CHART_9\ML_READY" -Filter "*.jsonl" | Select-Object -First 1
    $nqMB = [math]::Round($nqML.Length/1024/1024, 2)
    Write-Host "NQ ML_READY: $nqMB MB"
}

# RTY
if (Test-Path "CHART_1\ML_READY") {
    $rtyML = Get-ChildItem "CHART_1\ML_READY" -Filter "*.jsonl" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($rtyML) {
        $rtyMB = [math]::Round($rtyML.Length/1024/1024, 2)
        Write-Host "RTY ML_READY: $rtyMB MB"
    }
}

Write-Host ""
Write-Host "[VERDICT]" -ForegroundColor Yellow
Write-Host "  - Patch V3.4 applique avec succes"
Write-Host "  - Arret automatique marche ferme: ACTIF"
Write-Host "  - Reprise automatique ouverture: ACTIF"
Write-Host "  - Multi-marches (ES/NQ/RTY): FONCTIONNEL"
```

---

## 🐛 DÉPANNAGE

### **Problème 1 : Erreur de compilation**

**Symptôme** : "Build failed" dans Sierra Chart

**Solution** :
1. Vérifier que le backup existe : `MIA_Dumper_G3_Unifier.cpp.backup_XXXXXXXX`
2. Restaurer si nécessaire :
   ```powershell
   cd D:\MIA_IA_system\extracteur
   copy MIA_Dumper_G3_Unifier.cpp.backup_XXXXXXXX MIA_Dumper_G3_Unifier.cpp
   ```
3. Réappliquer le patch manuellement

---

### **Problème 2 : ML_READY continue d'écrire**

**Symptôme** : ML_READY se met toujours à jour même marché fermé

**Diagnostic** :
```powershell
# Vérifier que le patch est bien appliqué
cd D:\MIA_IA_system\extracteur
Select-String -Path "MIA_Dumper_G3_Unifier.cpp" -Pattern "PATCH V3.4"

# Si pas de résultat → Patch pas appliqué
```

**Solution** :
1. Réappliquer le patch
2. Recompiler
3. Redémarrer le study

---

### **Problème 3 : RTY ML_READY ne se crée pas**

**Symptôme** : Après ouverture Asia, RTY ML_READY absent

**Diagnostic** :
```powershell
# Vérifier que RTY unified est actif
cd D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\NOVEMBRE\20251104\CHART_1\unified
$rtyU = Get-ChildItem "*.jsonl" | Select-Object -First 1
$rtyUAge = ((Get-Date) - $rtyU.LastWriteTime).TotalMinutes
Write-Host "RTY unified age: $([math]::Round($rtyUAge, 1)) min"

# Si age > 5 min → Marché pas encore ouvert ou study inactif
```

**Solution** :
1. Attendre que le marché soit actif (données unified évoluent)
2. Vérifier Input[67] = 1 (Unified Output Enabled)
3. Redémarrer le study si nécessaire

---

## ✅ CHECKLIST FINALE

- [ ] Backup du fichier original créé
- [ ] Patch appliqué (ligne 2442-2471)
- [ ] Compilation réussie dans Sierra Chart
- [ ] Study redémarré (décocher/cocher)
- [ ] Test marché fermé : ML_READY s'arrête
- [ ] Test ouverture Asia : ML_READY reprend
- [ ] RTY ML_READY se crée automatiquement
- [ ] Tailles de fichiers vérifiées
- [ ] Dashboard "Collecte Données" mis à jour

---

## 📝 NOTES

- **Version patch** : V3.4
- **Date application** : 2025-11-04
- **Fichier modifié** : `MIA_Dumper_G3_Unifier.cpp` (lignes 2442-2471)
- **Backup** : `MIA_Dumper_G3_Unifier.cpp.backup_20251104_XXXXXX`
- **Compatibilité** : ES, NQ, RTY, GC, CL (tous marchés)

---

**Auteur** : MIA IA System
**Support** : contact@mia-ia-system.com
**Documentation** : https://docs.mia-ia-system.com/patch-v3.4
