# 🚀 MIA UNIFIER V2 - Documentation Complète

## 📋 **Vue d'ensemble**

L'unifier v2 intègre le **MenthorQDecisionEngine** pour fournir des **décisions de trading prêtes à l'emploi** directement dans les fichiers `unified_*.jsonl`.

---

## 🏗️ **Architecture**

### **Unifier v1 (Legacy)**
- ✅ Collecte des données (basedata, trade, quote, menthorq_levels, correlation)
- ✅ Calcul des alertes basiques (confluence + clusters)
- ❌ Pas de scoring MenthorQ
- ❌ Pas de décisions de trading

### **Unifier v2 (Nouveau)**
- ✅ Collecte des données (basedata, trade, quote, menthorq_levels, correlation)
- ✅ Calcul des alertes avancées (confluence + clusters + summary)
- ✅ **Scoring MenthorQ complet** (proximité pondérée)
- ✅ **Décisions de trading prêtes** (action, confiance, label, E/U/L)
- ✅ **Gates de sécurité** (MIA Bullish, OrderFlow, Leadership)
- ✅ **Adaptation VIX** (tolérance mèches, buffers structurels)

---

## 🎯 **Utilisation**

### **1. Mode MenthorQ Decisions (Recommandé)**
```bash
python mia_unifier.py --indir "D:\MIA_IA_system" --date today \
  --menthorq-decisions \
  --tick-size 0.25 \
  --confluence-thr 3 \
  --cluster-min-levels 2 \
  --cluster-thr 3 \
  --mia-long-thr 0.20 \
  --mia-short-thr -0.20 \
  --of-min-conf 3 \
  --verbose
```

### **2. Mode Legacy (Ancien)**
```bash
python mia_unifier.py --indir "D:\MIA_IA_system" --date today \
  --menthorq-alerts \
  --tick-size 0.25 \
  --confluence-thr 3 \
  --cluster-min-levels 2 \
  --cluster-thr 3 \
  --verbose
```

### **3. Mode Basique (Sans alertes)**
```bash
python mia_unifier.py --indir "D:\MIA_IA_system" --date today \
  --tick-size 0.25 \
  --verbose
```

---

## 📊 **Structure des Données de Sortie**

### **Mode MenthorQ Decisions (v2)**
```json
{
  "t": 45917.123456,
  "sym": "ESZ25_FUT_CME",
  "basedata": {"c": 6675.25, "v": 1500, "o": 6675.00, "h": 6675.50, "l": 6674.75},
  "trade": {"px": 6675.25, "sz": 100},
  "quote": {"bid": 6675.00, "ask": 6675.50},
  "menthorq_levels": [
    {"level_type": "gamma_wall_0dte", "price": 6675.50, "subgraph": 8},
    {"level_type": "blind_spot_3", "price": 6675.00, "subgraph": 3}
  ],
  "correlation": {"cc": 0.85},
  "vix": {"value": 20.0},
  
  "menthorq_decision": {
    "action": "long",
    "confidence": 0.78,
    "label": "Strong",
    "price": 6675.25,
    "vix_band": "MID",
    "entry": 6676.25,
    "stop": 6668.50,
    "tp1": 6684.00,
    "rationale": "fade_cluster_eul"
  },
  
  "alerts": {
    "summary": {
      "nearest_cluster": {
        "zone_min": 6675.00,
        "zone_max": 6675.75,
        "center": 6675.375,
        "width_ticks": 3.0,
        "groups": ["gamma", "blind"],
        "score": 2.8,
        "distance_ticks": 0.0,
        "status": "inside"
      },
      "signals": {
        "cluster_confluence": true,
        "cluster_strong": true,
        "cluster_touch": true
      }
    },
    "confidence": 0.78,
    "label": "Strong",
    "action": "long",
    "rationale": "fade_cluster_eul"
  }
}
```

### **Mode Legacy (v1)**
```json
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

## ⚙️ **Paramètres de Configuration**

### **Paramètres de Base**
- `--tick-size`: Taille du tick (0.25 pour ES)
- `--confluence-thr`: Seuil de confluence en ticks (3.0)
- `--cluster-min-levels`: Minimum de niveaux pour un cluster (2)
- `--cluster-thr`: Seuil de distance pour grouper les niveaux (3.0)

### **Paramètres MenthorQ Decision Engine**
- `--mia-long-thr`: Seuil MIA pour les signaux LONG (0.20)
- `--mia-short-thr`: Seuil MIA pour les signaux SHORT (-0.20)
- `--of-min-conf`: Confirmations OrderFlow minimales (3)

### **Paramètres de Sortie**
- `--gzip`: Compression gzip des fichiers de sortie
- `--out`: Chemin de sortie explicite
- `--verbose`: Mode verbeux avec logs détaillés

---

## 🎯 **Types de Décisions**

### **Actions Possibles**
- `"long"`: Signal d'achat
- `"short"`: Signal de vente
- `"flat"`: Pas de signal

### **Labels de Confiance**
- `"Extreme"`: ≥ 0.90 (très rare)
- `"Strong"`: ≥ 0.75 (signaux forts)
- `"Moderate"`: ≥ 0.60 (signaux modérés)
- `"Weak"`: ≥ 0.45 (signaux faibles)
- `"None"`: < 0.45 (pas de signal)

### **Rationales de Trading**
- `"fade_cluster_eul"`: Fade dans un cluster avec E/U/L
- `"breakout_retest_eul"`: Breakout avec retest et E/U/L
- `"no_cluster"`: Pas de cluster détecté
- `"no_pattern"`: Aucun pattern reconnu
- `"gate_mia:..."`: Bloqué par le gate MIA Bullish
- `"gate_orderflow:..."`: Bloqué par le gate OrderFlow

---

## 🔧 **Gates de Sécurité**

### **1. Gate MIA Bullish (BLOQUANT)**
```python
# LONG si MIA ≥ +0.20
# SHORT si MIA ≤ -0.20
# Sinon → action = "flat"
```

### **2. Gate OrderFlow (BLOQUANT)**
```python
# Minimum 3 confirmations OrderFlow requises
# Sinon → action = "flat"
```

### **3. Gate Leadership (NON-BLOQUANT)**
```python
# Pas de veto - juste une vérification
# MenthorQ peut anticiper les retournements
```

---

## 📈 **Scores et Calculs**

### **Scoring MenthorQ (55% du score final)**
```python
# Poids par type de niveau
Gamma Wall 0DTE: 0.25
0DTE Call/Put: 0.18-0.20
HVL: 0.12
Blind Spots: 0.12
GEX: 0.08

# Buckets de distance
2 ticks → 1.0
4 ticks → 0.7
8 ticks → 0.4
16 ticks → 0.1
32 ticks → 0.05
```

### **Scoring OrderFlow (30% du score final)**
```python
# Confirmations disponibles
- Delta burst: +1
- Delta flip: +1
- Stacked imbalance: +1
- Absorption: +1

# Score normalisé sur 4 confirmations max
```

### **Scoring Contexte (15% du score final)**
```python
# Pénalités structurelles
- Trop proche VWAP: -0.15
- Trop proche VPOC/VAL/VAH: -0.15
```

### **Bonuses**
```python
# Confluence forte (≥0.7): +0.1
# Cluster confluence: +0.05
# Cluster strong: +0.1
```

---

## 🚀 **Avantages du Mode v2**

### **✅ Performance**
- **Calculs centralisés** : Tout dans l'unifier
- **Pas de recalcul** : Le bot lit directement les décisions
- **Cache intelligent** : Résultats réutilisables

### **✅ Données Enrichies**
- **Scores pré-calculés** : MenthorQ, OrderFlow, Contexte
- **Décisions prêtes** : Action, confiance, label, E/U/L
- **Alertes complètes** : Summary + décision finale

### **✅ Architecture Simplifiée**
- **Un seul point de calcul** : L'unifier
- **Bot allégé** : Juste lecture des décisions
- **Maintenance centralisée** : Logique dans l'unifier

---

## 🔄 **Migration depuis v1**

### **1. Mise à jour des scripts**
```bash
# Ancien
python mia_unifier.py --menthorq-alerts

# Nouveau
python mia_unifier.py --menthorq-decisions
```

### **2. Mise à jour du bot**
```python
# Ancien - Lecture des alertes basiques
alerts = unified_row.get("alerts", {})
summary = alerts.get("summary", {})

# Nouveau - Lecture des décisions prêtes
decision = unified_row.get("menthorq_decision", {})
action = decision.get("action", "flat")
confidence = decision.get("confidence", 0.0)
entry = decision.get("entry")
stop = decision.get("stop")
tp1 = decision.get("tp1")
```

### **3. Compatibilité**
- **Mode legacy** : Toujours disponible avec `--menthorq-alerts`
- **Mode basique** : Toujours disponible sans options
- **Migration progressive** : Possible de migrer étape par étape

---

## 🎉 **Résultat**

Avec l'unifier v2, vous obtenez :
- **Décisions de trading prêtes** dans `menthorq_decision`
- **Alertes enrichies** dans `alerts`
- **Scores complets** (MenthorQ + OrderFlow + Contexte)
- **Gates de sécurité** intégrés
- **Adaptation VIX** automatique

**Le bot n'a plus qu'à lire les décisions et exécuter !** 🚀




























