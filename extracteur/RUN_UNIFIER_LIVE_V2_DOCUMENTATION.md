# 🚀 RUN_UNIFIER_LIVE V2 - Documentation Complète

## 📋 **Vue d'ensemble**

`run_unifier_live.py` a été mis à jour pour utiliser le **MenthorQDecisionEngine** et générer des **décisions de trading prêtes à l'emploi** toutes les minutes.

---

## 🔄 **CHANGEMENTS MAJEURS**

### **Ancienne Version (v1)**
```python
# Ancienne commande
cmd = [
    PY, "mia_unifier.py",
    "--menthorq-alerts",  # ❌ Mode legacy
    "--tick-size", "0.25",
    "--confluence-thr", "3",
    "--cluster-min-levels", "2",
    "--cluster-thr", "3"
]
```

### **Nouvelle Version (v2)**
```python
# Nouvelle commande
cmd = [
    PY, "mia_unifier.py",
    "--menthorq-decisions",  # ✅ Mode v2 avec décisions
    "--tick-size", "0.25",
    "--confluence-thr", "3",
    "--cluster-min-levels", "2",
    "--cluster-thr", "3",
    "--mia-long-thr", "0.20",    # ✅ NOUVEAU
    "--mia-short-thr", "-0.20",  # ✅ NOUVEAU
    "--of-min-conf", "3",        # ✅ NOUVEAU
    "--verbose"                  # ✅ NOUVEAU
]
```

---

## ⚙️ **NOUVELLES FONCTIONNALITÉS**

### **1. Mode v2 avec MenthorQDecisionEngine** ✅
- **Décisions complètes** : Action, confiance, label, E/U/L
- **Gates de sécurité** : MIA Bullish, OrderFlow, Leadership
- **Scoring avancé** : Proximité pondérée, confluence, clusters
- **Adaptation VIX** : Tolérances et buffers automatiques

### **2. Mode Legacy (Fallback)** ✅
- **Compatibilité** : Ancienne logique préservée
- **Fallback automatique** : Si v2 échoue, bascule vers legacy
- **Sécurité** : Pas de perte de fonctionnalité

### **3. Gestion d'Erreurs Améliorée** ✅
- **Logs détaillés** : Capture stdout/stderr
- **Fallback intelligent** : Bascule automatique vers legacy
- **Arrêt propre** : Ctrl+C géré correctement

### **4. Configuration Flexible** ✅
```python
USE_V2 = True  # Utiliser le mode v2 par défaut
FALLBACK_TO_LEGACY = True  # Fallback vers legacy si v2 échoue
```

---

## 🎯 **UTILISATION**

### **Lancement Standard**
```bash
python run_unifier_live.py
```

### **Sortie Console**
```
🎯 MIA Unifier Live - Mode v2 avec MenthorQDecisionEngine
📁 Base directory: D:\MIA_IA_system
🐍 Python: C:\Python\python.exe
⚙️ Mode: v2 (MenthorQDecisionEngine)
============================================================
🚀 Lancement unifier v2 - 14:30:15
✅ Unifier v2 terminé avec succès
📊 Unification v2 terminée: 1440 lignes, 23 décisions → unified_20241215.jsonl
⏰ Attente 60 secondes... (14:30:16)
```

### **En Cas d'Erreur v2**
```
❌ Erreur unifier v2: MenthorQDecisionEngine non disponible
🔄 Tentative de fallback vers mode legacy...
⚠️ Lancement unifier legacy - 14:30:17
✅ Unifier legacy terminé
```

---

## 📊 **DONNÉES GÉNÉRÉES**

### **Mode v2 - Fichier unifié enrichi**
```jsonl
# unified_YYYYMMDD.jsonl
{
  "t": 45917.123456,
  "sym": "ESZ25_FUT_CME",
  "basedata": {"c": 6675.25, "v": 1500},
  "menthorq_levels": [...],
  "correlation": {"cc": 0.85},
  "vix": {"value": 20.5},
  
  "menthorq_decision": {
    "action": "long",
    "confidence": 0.78,
    "label": "Strong",
    "entry": 6676.25,
    "stop": 6668.50,
    "tp1": 6684.00,
    "rationale": "fade_cluster_eul"
  },
  
  "alerts": {
    "summary": {...},
    "confidence": 0.78,
    "label": "Strong",
    "action": "long"
  }
}
```

### **Mode Legacy - Fichier unifié basique**
```jsonl
# unified_YYYYMMDD.jsonl
{
  "t": 45917.123456,
  "basedata": {"c": 6675.25, "v": 1500},
  "menthorq_levels": [...],
  "correlation": {"cc": 0.85},
  "alerts": {
    "confluence": {...},
    "clusters": [...],
    "summary": {...}
  }
}
```

---

## 🔧 **CONFIGURATION AVANCÉE**

### **Paramètres MenthorQDecisionEngine**
```python
# Dans run_unifier_v2()
"--mia-long-thr", "0.20",    # Seuil MIA pour LONG
"--mia-short-thr", "-0.20",  # Seuil MIA pour SHORT
"--of-min-conf", "3",        # Confirmations OrderFlow minimales
```

### **Paramètres de Base**
```python
"--tick-size", "0.25",       # Taille du tick ES
"--confluence-thr", "3",     # Seuil de confluence (ticks)
"--cluster-min-levels", "2", # Minimum niveaux pour cluster
"--cluster-thr", "3"         # Seuil de distance pour cluster
```

### **Fréquence d'Exécution**
```python
time.sleep(60)  # Exécution toutes les 60 secondes
```

---

## 🚨 **GESTION D'ERREURS**

### **Types d'Erreurs Gérées**
1. **Erreur MenthorQDecisionEngine** : Fallback vers legacy
2. **Erreur de lancement** : Logs détaillés
3. **Erreur critique** : Arrêt propre ou fallback
4. **Interruption utilisateur** : Ctrl+C géré

### **Logs d'Erreur**
```
❌ Erreur unifier v2: MenthorQDecisionEngine non disponible
❌ Erreur lancement unifier v2: [Errno 2] No such file or directory
❌ Erreur critique: Division by zero
💥 Arrêt du système
```

---

## 🔄 **MIGRATION DEPUIS V1**

### **Changements Automatiques**
- ✅ **Mode v2 par défaut** : Utilise `--menthorq-decisions`
- ✅ **Fallback automatique** : Bascule vers legacy si problème
- ✅ **Logs améliorés** : Capture stdout/stderr
- ✅ **Gestion d'erreurs** : Plus robuste

### **Compatibilité**
- ✅ **Ancienne logique préservée** : Mode legacy disponible
- ✅ **Même fréquence** : 60 secondes
- ✅ **Même répertoire** : `D:\MIA_IA_system`
- ✅ **Même format** : Fichiers `unified_*.jsonl`

---

## 🎯 **AVANTAGES DU MODE V2**

### **✅ Performance**
- **Décisions prêtes** : Le bot n'a plus qu'à lire
- **Calculs centralisés** : Tout dans l'unifier
- **Cache intelligent** : Résultats réutilisables

### **✅ Données Enrichies**
- **Scoring complet** : MenthorQ + OrderFlow + Contexte
- **Gates intégrés** : Sécurité automatique
- **E/U/L précis** : Entry, Stop, TP calculés

### **✅ Robustesse**
- **Fallback automatique** : Pas de perte de service
- **Gestion d'erreurs** : Logs détaillés
- **Arrêt propre** : Ctrl+C géré

---

## 🚀 **DÉPLOIEMENT**

### **1. Vérification des Prérequis**
```bash
# Vérifier que MenthorQDecisionEngine est disponible
python -c "from extracteur.MenthorQDecisionEngine import MenthorQDecisionEngine; print('✅ OK')"
```

### **2. Test Manuel**
```bash
# Test une fois
python mia_unifier.py --indir "D:\MIA_IA_system" --date today --menthorq-decisions --verbose
```

### **3. Lancement Live**
```bash
# Lancement en continu
python run_unifier_live.py
```

### **4. Monitoring**
- **Logs console** : Vérifier les messages de succès/erreur
- **Fichiers générés** : Vérifier `unified_*.jsonl`
- **Décisions** : Compter les décisions générées

---

## 🎉 **RÉSULTAT**

Avec `run_unifier_live.py` v2, vous obtenez :
- **Décisions de trading automatiques** toutes les minutes
- **Fallback intelligent** vers l'ancienne logique
- **Logs détaillés** pour le monitoring
- **Gestion d'erreurs robuste**
- **Compatibilité totale** avec l'existant

**Le système génère maintenant des décisions prêtes à l'emploi pour le bot !** 🚀




























