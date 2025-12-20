# 🎯 GUIDE MENTHORQ - Analyse Options/Gamma

## Introduction

MenthorQ fournit des données en temps réel sur le positionnement des options institutionnelles.
Ces données nous permettent d'identifier les niveaux de support/résistance "invisibles" créés par le hedging des dealers.

---

## 📊 Concepts Clés

### 1. Gamma Walls (Murs Gamma)

**Définition:** Niveaux de prix où les dealers ont accumulé beaucoup de gamma (exposition aux options).

**Comment ça marche:**
- Quand le prix approche un Gamma Wall, les dealers doivent hedger
- Cela crée une "force magnétique" qui peut repousser ou attirer le prix
- Plus le gamma est élevé, plus le niveau est significatif

**Dans le snapshot:**
```json
"gamma_wall_level": 25400.00,
"gamma_side": "below"
```
→ Le mur gamma principal est à 25400, et le prix est EN-DESSOUS

### 2. GEX Levels (Gamma Exposure)

**Définition:** Les 10 niveaux avec le plus de gamma exposure.

**Dans le snapshot:**
```json
"gex_1": 24900.00,   // Plus fort niveau GEX
"gex_2": 25000.00,
"gex_3": 24700.00,
"gex_4": 25125.00,
"gex_5": 25200.00,
"gex_6": 24500.00,
"gex_7": 25500.00,
"gex_8": 25600.00,
"gex_9": 24600.00,
"gex_10": 24400.00
```

**Interprétation:**
- GEX_1 (24900) = Niveau avec le plus de gamma → Support/Résistance fort
- Les niveaux proches du prix actuel sont plus importants

### 3. Call Resistance & Put Support

**Définition:** Niveaux où les calls/puts créent des barrières.

**Dans le snapshot:**
```json
"call_resistance": 25400.00,  // Résistance créée par les calls
"put_support": 24800.00       // Support créé par les puts
```

**Interprétation:**
- Prix actuel: 25065
- Call Resistance à 25400 → Le prix aura du mal à monter au-dessus
- Put Support à 24800 → Le prix aura du mal à descendre en-dessous

### 4. HVL (Highest Volume Level)

**Définition:** Niveau de prix avec le plus grand volume d'options.

**Dans le snapshot:**
```json
"hvl": 24825.00
```

**Interprétation:**
- C'est le "centre de gravité" du marché options
- Le prix a tendance à revenir vers ce niveau

### 5. Blind Spots (Zones Aveugles)

**Définition:** Zones avec PEU de protection options → Le prix peut bouger vite!

**Dans le snapshot:**
```json
"blind_spot_0": 24483.29,
"blind_spot_1": 24606.50,
"blind_spot_2": 24274.70,
"blind_spot_3": 24820.59,
"blind_spot_4": 25280.48,
"blind_spot_5": 25150.05,
"blind_spot_6": 23975.84,
"blind_spot_7": 24185.13,
"blind_spot_8": 25084.07
```

**Interprétation:**
- blind_spot_8 (25084) est TRÈS proche du prix actuel (25065)!
- → Zone de danger potentiel, mouvement rapide possible

### 6. 1D Expected Move (Mouvement Attendu)

**Définition:** Range probable pour la journée basé sur les options.

**Dans le snapshot:**
```json
"1d_max": 25294.04,
"1d_min": 24602.46
```

**Interprétation:**
- Le marché "attend" que le prix reste entre 24602 et 25294
- Mouvement au-delà = Surprise, possible accélération

---

## 📐 Distances MenthorQ

Le snapshot contient les distances en TICKS vers chaque niveau:

```json
"menthor_distances": {
    "gamma0": 1339,      // Distance au gamma wall (en ticks)
    "call0": 1339,       // Distance à call resistance
    "put0": -1061,       // Distance à put support (négatif = en-dessous)
    "hvl0": -961,        // Distance au HVL
    "call": 339,         // Distance call (autre calcul)
    "put": -1061,        // Distance put
    "hvl": -961,         // Distance HVL
    "dist_1d_max": 915,  // Distance au max attendu
    "dist_1d_min": -1851,// Distance au min attendu
    "near_gex_up": 239,  // Prochain GEX au-dessus
    "near_gex_dn": 261,  // Prochain GEX en-dessous
    "near_blind": 75     // Blind spot le plus proche (75 ticks!)
}
```

**⚠️ ALERTE:** `near_blind: 75` = Un blind spot est à seulement 75 ticks!

---

## 🎯 Next Wall (Prochain Mur)

**Définition:** Le prochain niveau significatif que le prix va rencontrer.

**Dans le snapshot:**
```json
"next_wall": {
    "price": 25125.00,   // Prix du mur
    "side": "call",      // Type (call = résistance)
    "dist_pts": 59.75,   // Distance en points
    "dist_ticks": 239,   // Distance en ticks
    "strength": 0.304167,// Force du mur (0-1)
    "age_min": 0         // Âge en minutes
}
```

**Interprétation:**
- Prochain obstacle: 25125 (résistance call)
- Distance: ~60 points
- Force: 30% → Mur modéré

---

## 📊 Scores Calculés

### MenthorQ Impact Score
```json
"menthorq_impact_score": 0.075281
```
Score global de l'impact des niveaux MenthorQ sur le prix actuel.

### Confluence Strength
```json
"confluence_strength": 0.038183,
"confluence_proximity": 75.28
```
- Plusieurs niveaux se chevauchent-ils?
- Plus c'est élevé, plus le niveau est fort

### Gamma Flip Detection
```json
"gamma_flip_up": false,
"gamma_flip_down": false
```
Le prix a-t-il traversé un niveau gamma important?

---

## 🔧 Utilisation dans le Trading

### Signal LONG favorable:
- Prix au-dessus du HVL ✅
- Put support proche en-dessous ✅
- Pas de call resistance immédiate ✅
- Pas dans un blind spot ✅

### Signal SHORT favorable:
- Prix en-dessous du HVL ✅
- Call resistance proche au-dessus ✅
- Pas de put support immédiat ✅
- Pas dans un blind spot ✅

### Éviter de trader si:
- Prix dans un blind spot ⚠️
- Prix entre call_resistance et put_support serrés ⚠️
- Gamma flip récent (volatilité) ⚠️

---

## 📝 Poids dans le ML 3-Layer

**Layer 1 (MenthorQ) = 50% du score total**

| Composant | Poids |
|-----------|-------|
| Gamma Walls | 10% |
| GEX Levels | 10% |
| Blind Spots | 8% |
| Next Wall | 8% |
| Distances | 8% |
| Confluence | 6% |

---

*Document technique MIA_IA_system - Version 1.0*
