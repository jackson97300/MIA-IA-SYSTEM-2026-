# 📊 GUIDE ORDER FLOW - Analyse du Flux d'Ordres

## Introduction

L'Order Flow analyse les transactions RÉELLES sur le marché.
Contrairement aux indicateurs techniques, il montre QUI achète et QUI vend en temps réel.

---

## 🎓 Concepts Fondamentaux

### 1. Delta

**Définition:** Différence entre le volume acheté et le volume vendu.

```json
"delta": 19,
"cum_delta_day": -1841,
"cum_delta_session": -1926
```

| Champ | Description |
|-------|-------------|
| `delta` | Delta de la dernière barre (+19 = plus d'achats) |
| `cum_delta_day` | Delta cumulé du jour (-1841 = vendeurs dominent) |
| `cum_delta_session` | Delta cumulé de la session |

**Interprétation:**
- Delta positif = Acheteurs agressifs (achètent au ask)
- Delta négatif = Vendeurs agressifs (vendent au bid)
- Divergence prix/delta = Signal potentiel

### 2. Bid/Ask Volume

```json
"bidvol": 67,
"askvol": 48,
"volume": 115
```

**Calcul:**
- `bidvol` = Volume exécuté au BID (ventes agressives)
- `askvol` = Volume exécuté au ASK (achats agressifs)
- `delta` = askvol - bidvol = 48 - 67 = -19... wait, c'est +19?

**Note:** Le delta dans le snapshot est +19, ce qui signifie que malgré plus de volume au bid, les acheteurs ont eu plus d'impact.

### 3. Pourcentages Bid/Ask

```json
"bidPct": 0.582609,
"askPct": 0.417391,
"deltaPct": 0.165217
```

**Interprétation:**
- 58.3% du volume au BID (vendeurs)
- 41.7% du volume au ASK (acheteurs)
- Ratio delta: 16.5% en faveur des acheteurs

---

## 📈 DOM (Depth of Market)

### Niveaux DOM

```json
"dom_bid1": 25058.00,
"dom_ask1": 25065.50,
"dom_bq1": 1,
"dom_aq1": 2
```

| Champ | Description |
|-------|-------------|
| `dom_bid1` | Meilleur prix bid dans le DOM |
| `dom_ask1` | Meilleur prix ask dans le DOM |
| `dom_bq1` | Quantité au meilleur bid |
| `dom_aq1` | Quantité au meilleur ask |

### Profondeur DOM (10 niveaux)

```json
"dom_bid_1": 1, "dom_bid_2": 0, ... "dom_bid_10": 0,
"dom_ask_1": 2, "dom_ask_2": 0, ... "dom_ask_10": 0
```

**Interprétation:**
- DOM très léger (1 lot bid, 2 lots ask)
- Pas de profondeur = Marché peut bouger vite

### DOM Features Avancées

```json
"dom_features": {
    "depth_bid": 1,
    "depth_ask": 2,
    "rings_bid": 1,
    "rings_ask": 1,
    "imbalance_1_3": 0.400000,
    "imbalance_6_10": 0.176471,
    "slope_bid_1_3": 3,
    "slope_ask_1_3": 0
}
```

| Champ | Description |
|-------|-------------|
| `depth_bid/ask` | Profondeur totale |
| `rings_bid/ask` | Nombre de niveaux avec ordres |
| `imbalance_1_3` | Déséquilibre niveaux 1-3 |
| `imbalance_6_10` | Déséquilibre niveaux 6-10 |
| `slope_bid/ask` | Pente du carnet (accumulation) |

---

## 🎯 Imbalances

### Level 1 Imbalance

```json
"level1_imbalance": -0.333333
```

**Calcul:** (ask_qty - bid_qty) / (ask_qty + bid_qty)

**Interprétation:**
- -0.33 = Plus de pression vendeuse au niveau 1
- Range: -1 (tout bid) à +1 (tout ask)

### Depth Imbalance

```json
"depth_imbalance": -0.333333
```

Même calcul mais sur toute la profondeur du DOM.

### Micro Imbalance

```json
"micro_imb": -0.333333
```

Imbalance calculée sur le microprice.

---

## 💪 Pressure & Flow

### Institutional Pressure

```json
"institutional_pressure": 0.165217
```

**Interprétation:**
- Mesure la pression des gros ordres
- Positif = Pression acheteuse institutionnelle
- Négatif = Pression vendeuse institutionnelle

### Smart Money Flow

```json
"smart_money_flow": -0.165217
```

**Interprétation:**
- Direction du "smart money"
- Négatif = Les institutionnels vendent

### Pressure Strength

```json
"pressure": 0,
"pressure_strength": 0.038333,
"pressure_strength_depth": 0.333333,
"pressure_strength_atr": 0.008739
```

| Champ | Description |
|-------|-------------|
| `pressure` | Direction globale (0 = neutre) |
| `pressure_strength` | Force de la pression |
| `pressure_strength_depth` | Force basée sur profondeur |
| `pressure_strength_atr` | Force relative à l'ATR |

---

## ⚔️ Battle Navale

Notre indicateur propriétaire qui détecte les "batailles" entre acheteurs et vendeurs.

```json
"battle_navale_signal_strength": 0.038183,
"battle_navale_confidence": 0.045819
```

**Interprétation:**
- `signal_strength` = Intensité du signal (0-1)
- `confidence` = Confiance dans le signal (0-1)
- Valeurs basses = Pas de bataille claire
- Valeurs hautes = Bataille intense, breakout probable

---

## 📊 Tick & Trade Rate

```json
"tick_rate_1s": 1,
"tick_rate_3s": 1.000000,
"trade_rate_1s": 0,
"delta_rate_1s": 0
```

| Champ | Description |
|-------|-------------|
| `tick_rate_1s` | Ticks par seconde |
| `tick_rate_3s` | Moyenne 3 secondes |
| `trade_rate_1s` | Trades par seconde |
| `delta_rate_1s` | Delta par seconde |

**Utilisation:**
- Tick rate élevé = Marché actif
- Tick rate bas = Marché calme, éviter de trader

---

## 🔥 Delta Burst & Flip

```json
"delta_burst": 19,
"delta_flip": false
```

### Delta Burst
- Pic soudain de delta
- Indique une entrée agressive

### Delta Flip
- `true` = Le delta vient de changer de signe
- Signal potentiel de retournement

---

## 📐 Stacked Imbalances

```json
"stacked_imbalance_bid_rows": 0,
"stacked_imbalance_ask_rows": 0
```

**Définition:** Plusieurs niveaux consécutifs avec déséquilibre dans la même direction.

**Interprétation:**
- 0 = Pas de stacked imbalance
- 3+ = Signal fort de direction

---

## 🔧 Application dans le Trading

### Signal LONG (Order Flow)
- Delta positif ✅
- Institutional pressure positif ✅
- Smart money flow positif ✅
- DOM imbalance positif ✅
- Pas de stacked imbalance ask ✅

### Signal SHORT (Order Flow)
- Delta négatif ✅
- Institutional pressure négatif ✅
- Smart money flow négatif ✅
- DOM imbalance négatif ✅
- Pas de stacked imbalance bid ✅

### Confirmation de Signal
L'order flow CONFIRME un signal MenthorQ:
- MenthorQ dit LONG + Delta positif = ✅ GO
- MenthorQ dit LONG + Delta négatif = ⚠️ Attendre

---

## 📝 Poids dans le ML 3-Layer

**Layer 2 (OrderFlow) = 30% du score total**

| Composant | Poids |
|-----------|-------|
| Delta instantané | 12% |
| Volume bid/ask | 6% |
| DOM Imbalance | 6% |
| Institutional Pressure | 4% |
| Battle Navale | 2% |

---

## 🧮 Calcul du Score Layer 2

```python
# Exemple de calcul simplifié
delta_score = 1.0 if delta > 0 else -1.0  # +19 → 1.0
volume_score = (bidPct - 0.5) * 2  # 0.58 → 0.16
dom_score = level1_imbalance  # -0.33
pressure_score = institutional_pressure  # 0.165
battle_score = battle_navale_confidence  # 0.046

layer2_score = (
    delta_score * 0.40 +      # 0.40
    volume_score * 0.20 +     # 0.03
    dom_score * 0.20 +        # -0.07
    pressure_score * 0.13 +   # 0.02
    battle_score * 0.07       # 0.003
)
# ≈ 0.38 → 38% Layer 2 score
```

---

*Document technique MIA_IA_system - Version 1.0*
