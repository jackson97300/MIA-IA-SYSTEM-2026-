# 🎯 CLUSTER ALERTS - Documentation Complète

## 📋 **Vue d'ensemble**

La logique de **niveau option proche / cluster** a été intégrée directement dans l'unifier pour simplifier l'utilisation côté bot. Le bot n'a plus qu'à lire le champ `alerts.summary` pour obtenir des signaux prêts à l'emploi.

---

## 🏗️ **Architecture**

### **Collecteur G10 (MenthorQ)**
- ✅ **Collecte simple** : Niveaux MenthorQ + Corrélation
- ✅ **Pas de logique complexe** : Juste la collecte des données
- ✅ **Performance optimisée** : 15min pour niveaux, 1min pour corrélation

### **Unifier (mia_unifier.py)**
- ✅ **Logique centralisée** : Confluence + Clusters + Summary
- ✅ **Calculs avancés** : Distance, scoring, groupement
- ✅ **Signaux prêts** : Drapeaux simples pour le bot

### **Bot (launch_24_7_menthorq_final.py)**
- ✅ **Consommation simple** : Lecture du champ `alerts.summary`
- ✅ **Logique de trading** : Basée sur les signaux prêts

---

## 📊 **Structure des Alertes**

### **Bloc `alerts` complet**
```json
{
  "confluence": {
    "type": "confluence",
    "price": 6675.25,
    "gamma": {
      "level_type": "gamma_wall_0dte",
      "price": 6675.50,
      "ticks": 1.0,
      "sg": 8
    },
    "blind": {
      "level_type": "blind_spot_3", 
      "price": 6675.00,
      "ticks": 1.0,
      "sg": 3
    },
    "threshold_ticks": 3.0,
    "tick_size": 0.25
  },
  "confluence_strength": 0.8,
  "clusters": [
    {
      "type": "cluster",
      "price": 6675.25,
      "zone_min": 6675.00,
      "zone_max": 6675.75,
      "center": 6675.375,
      "width_ticks": 3.0,
      "count": 3,
      "groups": ["gamma", "blind", "gex"],
      "score": 3.2,
      "levels": [...],
      "threshold_ticks": 3.0,
      "tick_size": 0.25
    }
  ],
  "summary": {
    "nearest_cluster": {
      "zone_min": 6675.00,
      "zone_max": 6675.75,
      "center": 6675.375,
      "width_ticks": 3.0,
      "groups": ["gamma", "blind", "gex"],
      "score": 3.2,
      "distance_ticks": 0.0,
      "status": "inside"
    },
    "signals": {
      "cluster_confluence": true,
      "cluster_strong": true,
      "cluster_touch": true
    }
  }
}
```

---

## 🎯 **Signaux Disponibles**

### **1. `cluster_confluence`**
- **Condition** : ≥2 groupes dans le cluster
- **Signification** : Zone multi-niveaux (gamma + blind + gex)
- **Priorité** : HAUTE

### **2. `cluster_strong`**
- **Condition** : Score ≥ 2.5 OU largeur ≤ 3.0 ticks
- **Signification** : Cluster dense et puissant
- **Priorité** : HAUTE

### **3. `cluster_touch`**
- **Condition** : Prix au bord du cluster ≤ 1 tick
- **Signification** : Prix touche le cluster
- **Priorité** : MOYENNE

### **4. `confluence_strength`**
- **Valeur** : 0.0 à 1.0
- **Signification** : Force de la confluence gamma + blind
- **Usage** : Bonus de confiance

---

## 🚀 **Utilisation Côté Bot**

### **Lecture des signaux**
```python
alerts = unified_row.get("alerts") or {}
summary = alerts.get("summary") or {}
nearest = summary.get("nearest_cluster") or {}
signals = summary.get("signals") or {}

# Vérification des signaux
if signals.get("cluster_confluence") and signals.get("cluster_strong"):
    # Zone prioritaire : cluster multi-groupes et fort
    pass
```

### **Logique de trading**
```python
if nearest.get("status") == "inside":
    # Prix dans le cluster → Fade strategy
    strategy = "fade"
    stop_loss = 1-2  # ticks au-delà du bord opposé
elif nearest.get("status") == "below":
    # Prix sous le cluster → Breakout strategy
    strategy = "breakout"
    entry_trigger = nearest.get("zone_max") + 0.5
else:  # above
    # Prix au-dessus du cluster → Breakdown strategy
    strategy = "breakdown"
    entry_trigger = nearest.get("zone_min") - 0.5
```

### **Calcul de confiance**
```python
base_confidence = 0.75
bonus = 0.0

if alerts.get("confluence_strength", 0) >= 0.7:
    bonus += 0.1
if signals.get("cluster_strong"):
    bonus += 0.1
if signals.get("cluster_confluence"):
    bonus += 0.05

adjusted_confidence = min(1.0, base_confidence + bonus)
```

---

## ⚙️ **Configuration**

### **Paramètres par défaut**
```bash
--tick-size 0.25          # ES tick size
--confluence-thr 3        # 3 ticks pour confluence
--cluster-min-levels 2    # Minimum 2 niveaux pour cluster
--cluster-thr 3           # 3 ticks pour grouper les niveaux
```

### **Seuils de signaux**
- **Cluster Strong** : Score ≥ 2.5 OU largeur ≤ 3.0 ticks
- **Cluster Touch** : Distance ≤ 1.0 tick
- **Confluence Strong** : Force ≥ 0.7

---

## 📈 **Exemples de Signaux**

### **Signal 1: Cluster Confluence**
```json
{
  "type": "cluster_confluence",
  "priority": "HIGH",
  "strategy": "fade",
  "zone_min": 6675.00,
  "zone_max": 6675.75,
  "center": 6675.375,
  "width_ticks": 3.0,
  "groups": ["gamma", "blind", "gex"],
  "score": 3.2,
  "status": "inside",
  "stop_loss": 1.5,
  "target": 6675.375
}
```

### **Signal 2: Cluster Touch**
```json
{
  "type": "cluster_touch",
  "priority": "MEDIUM",
  "strategy": "touch",
  "zone_min": 6675.00,
  "zone_max": 6675.75,
  "distance_ticks": 0.5,
  "stop_loss": 2.0,
  "target": 6675.375
}
```

### **Signal 3: Confluence Strong**
```json
{
  "type": "confluence_strong",
  "priority": "HIGH",
  "strategy": "confluence",
  "gamma_level": "gamma_wall_0dte",
  "blind_level": "blind_spot_3",
  "strength": 0.8,
  "stop_loss": 2.0,
  "target": 6675.50
}
```

---

## 🎯 **Avantages**

### **✅ Simplicité**
- **Bot allégé** : Plus de calculs complexes côté bot
- **Signaux prêts** : Drapeaux simples à consommer
- **Maintenance centralisée** : Logique dans l'unifier

### **✅ Performance**
- **Calculs optimisés** : Une seule fois dans l'unifier
- **Cache intelligent** : Résultats réutilisables
- **Fréquence adaptée** : 15min pour niveaux, 1min pour corrélation

### **✅ Flexibilité**
- **Configuration** : Paramètres ajustables
- **Extensibilité** : Facile d'ajouter de nouveaux signaux
- **Debugging** : Logs détaillés dans l'unifier

---

## 🔧 **Déploiement**

### **1. Mise à jour de l'unifier**
```bash
# L'unifier est déjà mis à jour avec la nouvelle logique
python mia_unifier.py --indir "D:\MIA_IA_system" --date today \
  --menthorq-alerts --tick-size 0.25 --confluence-thr 3 \
  --cluster-min-levels 2 --cluster-thr 3
```

### **2. Intégration côté bot**
```python
# Dans launch_24_7_menthorq_final.py
alerts = market_data.get("menthorq", {}).get("alerts", {})
summary = alerts.get("summary", {})
signals = summary.get("signals", {})

if signals.get("cluster_confluence") and signals.get("cluster_strong"):
    # Logique de trading basée sur les signaux
    pass
```

### **3. Test et validation**
- Vérifier que les fichiers `unified_*.jsonl` contiennent le bloc `alerts`
- Tester les signaux avec des données réelles
- Ajuster les paramètres si nécessaire

---

## 🎉 **Résultat**

Avec cette implémentation, vous obtenez :
- **Signaux prêts à l'emploi** dans `alerts.summary`
- **Logique centralisée** dans l'unifier
- **Bot simplifié** et performant
- **Maintenance facilitée** et évolutive

**Le système est maintenant prêt pour la production avec des signaux de cluster avancés !** 🚀




























