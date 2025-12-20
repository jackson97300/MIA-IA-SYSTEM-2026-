# AUDIT: COMPLÉTER MarketRegimeDetector
## Date: 08/12/2025

---

## 🎯 OBJECTIF

Compléter le module `features/market_regime.py` pour:
1. Détecter les BRACKETS (5-30 min) avec 3 touches + buffer
2. Ajouter logique FADE basée sur POSITION dans le range
3. Détecter les breakouts imminents
4. Intégrer au bot live

---

## 📊 ÉTAT ACTUEL DU MODULE

### ✅ CE QUI EXISTE:

| Fonctionnalité | Status | Ligne | Valeur |
|----------------|--------|-------|--------|
| Détection range | ✅ | 696-858 | Oui |
| 3 touches minimum | ✅ | 329 | `min_level_tests = 3` |
| Buffer touches | ✅ | 760 | `tolerance = 1.5 ticks` |
| Taille range | ✅ | 326-327 | `12-50 ticks` |
| Durée minimum | ✅ | 328 | `20 minutes` |
| Respect niveaux | ✅ | 330 | `75%` |
| Classification | ✅ | 805-812 | TIGHT/NORMAL/WIDE |
| Bias tendance | ✅ | 816-826 | Basé sur HH/HL |

### ❌ CE QUI MANQUE:

| Fonctionnalité | Impact | Priorité |
|----------------|--------|----------|
| **Position dans range** | Impossible de savoir si HAUT/BAS/MILIEU | 🔴 CRITIQUE |
| **Logique FADE** | Pas de filtrage LONG bas / SHORT haut | 🔴 CRITIQUE |
| **Détection breakout** | Pas d'alerte si prix proche bord + momentum | 🟠 HAUTE |
| **Durée 10 min** | Brackets courts non détectés | 🟡 MOYENNE |
| **Config par symbole** | ES/NQ ont les mêmes paramètres | 🟡 MOYENNE |

---

## 🔧 MODIFICATIONS PROPOSÉES

### 1️⃣ AJOUTER `RangeAnalysis.position_in_range`

**Fichier:** `features/market_regime.py`
**Ligne:** ~125 (dans @dataclass RangeAnalysis)

```python
@dataclass
class RangeAnalysis:
    """Analyse range complète"""
    timestamp: pd.Timestamp

    # ... champs existants ...

    # 🔥 NOUVEAU: Position dans le range
    current_price: float = 0.0
    position_in_range_pct: float = 50.0  # 0-100%
    range_zone: str = "MIDDLE"  # "BOTTOM", "MIDDLE", "TOP"
    distance_to_support_ticks: float = 0.0
    distance_to_resistance_ticks: float = 0.0

    # 🔥 NOUVEAU: Détection breakout
    breakout_risk: str = "NONE"  # "NONE", "BEARISH", "BULLISH"
    breakout_proximity_ticks: float = 5.0
```

---

### 2️⃣ CALCULER LA POSITION DANS LE RANGE

**Fichier:** `features/market_regime.py`
**Ligne:** ~855 (après `range_detected=True`)

```python
# === POSITION DANS LE RANGE (NOUVEAU) ===

current_price = market_data.close
position_in_range_pct = 0.0
range_zone = "MIDDLE"
distance_to_support = 0.0
distance_to_resistance = 0.0

if resistance_level > support_level:
    position_in_range_pct = ((current_price - support_level) /
                             (resistance_level - support_level)) * 100
    position_in_range_pct = max(0, min(100, position_in_range_pct))

    distance_to_support = TickConverter.price_range_to_ticks(
        current_price, support_level, 'ES'
    )
    distance_to_resistance = TickConverter.price_range_to_ticks(
        resistance_level, current_price, 'ES'
    )

    # Zones avec buffer (25% / 75%)
    BOTTOM_ZONE = 25
    TOP_ZONE = 75

    if position_in_range_pct < BOTTOM_ZONE:
        range_zone = "BOTTOM"
    elif position_in_range_pct > TOP_ZONE:
        range_zone = "TOP"
    else:
        range_zone = "MIDDLE"
```

---

### 3️⃣ DÉTECTER LE BREAKOUT IMMINENT

**Fichier:** `features/market_regime.py`
**Ligne:** ~860 (après calcul position)

```python
# === DÉTECTION BREAKOUT (NOUVEAU) ===

breakout_risk = "NONE"
BREAKOUT_PROXIMITY_TICKS = 5  # Alerte si < 5 ticks du bord

# Calculer le momentum (utiliser volume_trend ou autre indicateur)
momentum_bearish = volume_trend < -0.1 or underlying_bias == "bearish"
momentum_bullish = volume_trend > 0.1 or underlying_bias == "bullish"

# Proche du support + momentum baissier = breakout down
if distance_to_support < BREAKOUT_PROXIMITY_TICKS and momentum_bearish:
    breakout_risk = "BEARISH"

# Proche de la résistance + momentum haussier = breakout up
elif distance_to_resistance < BREAKOUT_PROXIMITY_TICKS and momentum_bullish:
    breakout_risk = "BULLISH"
```

---

### 4️⃣ MODIFIER LA LOGIQUE FADE

**Fichier:** `features/market_regime.py`
**Ligne:** ~1099-1109 (dans _generate_regime_implications)

**AVANT:**
```python
elif regime == MarketRegime.RANGE_BULLISH_BIAS:
    allowed_directions = ["LONG"]  # Seulement longs en bas range

elif regime == MarketRegime.RANGE_BEARISH_BIAS:
    allowed_directions = ["SHORT"]  # Seulement shorts en haut range

elif regime == MarketRegime.RANGE_NEUTRAL:
    allowed_directions = ["LONG", "SHORT"]  # Both sides
```

**APRÈS:**
```python
elif regime in [MarketRegime.RANGE_BULLISH_BIAS,
                MarketRegime.RANGE_BEARISH_BIAS,
                MarketRegime.RANGE_NEUTRAL]:

    # 🔥 LOGIQUE FADE BASÉE SUR POSITION
    range_zone = range_analysis.range_zone
    breakout_risk = range_analysis.breakout_risk

    # Breakout imminent = PAS DE TRADE
    if breakout_risk != "NONE":
        allowed_directions = []
        preferred_strategy = "wait"
        logger.warning(f"⚠️ BREAKOUT RISK {breakout_risk} - Pas de trade")

    # Bas du range = LONG seulement (FADE)
    elif range_zone == "BOTTOM":
        allowed_directions = ["LONG"]
        logger.info(f"📈 RANGE BOTTOM ({range_analysis.position_in_range_pct:.0f}%) - LONG autorisé")

    # Haut du range = SHORT seulement (FADE)
    elif range_zone == "TOP":
        allowed_directions = ["SHORT"]
        logger.info(f"📉 RANGE TOP ({range_analysis.position_in_range_pct:.0f}%) - SHORT autorisé")

    # Milieu = PAS DE TRADE
    else:
        allowed_directions = []
        preferred_strategy = "wait"
        logger.info(f"⏸️ RANGE MIDDLE ({range_analysis.position_in_range_pct:.0f}%) - Attendre")
```

---

### 5️⃣ RÉDUIRE DURÉE MINIMUM (OPTIONNEL)

**Fichier:** `features/market_regime.py`
**Ligne:** 328

**AVANT:**
```python
self.min_range_duration = self.config.get('min_range_duration', 20)
```

**APRÈS:**
```python
self.min_range_duration = self.config.get('min_range_duration', 10)  # Réduit pour brackets courts
```

---

### 6️⃣ CONFIG PAR SYMBOLE

**Fichier:** `features/market_regime.py`
**Ajouter après ligne 330:**

```python
# 🔥 NOUVEAU: Configuration par symbole
self.symbol_config = self.config.get('symbol_config', {
    'ES': {
        'min_range_size_ticks': 15,
        'max_range_size_ticks': 60,
        'breakout_proximity_ticks': 5,
    },
    'NQ': {
        'min_range_size_ticks': 20,
        'max_range_size_ticks': 80,
        'breakout_proximity_ticks': 8,
    }
})
```

---

## 📁 FICHIERS À MODIFIER

| Fichier | Modifications | Lignes |
|---------|---------------|--------|
| `features/market_regime.py` | Ajouter position_in_range | ~125 |
| `features/market_regime.py` | Calculer position | ~855 |
| `features/market_regime.py` | Détecter breakout | ~860 |
| `features/market_regime.py` | Logique FADE | ~1099 |
| `features/market_regime.py` | Durée 10 min | 328 |
| `LAUNCH/launch_production_CLEAN_v2.py` | Intégrer module | À ajouter |

---

## 🧪 TESTS À FAIRE

### Test 1: Power Hour 08/12
```
Contexte:
- Range 6840-6850 (40 ticks)
- Prix @ 6841 (position 10% = BOTTOM)
- Momentum bearish (-0.15)
- Distance au support: 4 ticks

Attendu:
- range_zone = "BOTTOM"
- breakout_risk = "BEARISH" (< 5t + bearish)
- allowed_directions = [] (breakout imminent)
- Trade LONG BLOQUÉ ✅
```

### Test 2: Range normal (pas de breakout)
```
Contexte:
- Range 6840-6850 (40 ticks)
- Prix @ 6842 (position 20% = BOTTOM)
- Momentum neutre (0.05)
- Distance au support: 8 ticks

Attendu:
- range_zone = "BOTTOM"
- breakout_risk = "NONE"
- allowed_directions = ["LONG"]
- Trade LONG autorisé ✅
```

---

## ✅ CHECKLIST IMPLÉMENTATION

- [ ] Ajouter champs à `RangeAnalysis`
- [ ] Calculer `position_in_range_pct`
- [ ] Calculer `range_zone`
- [ ] Détecter `breakout_risk`
- [ ] Modifier logique FADE dans `_generate_regime_implications`
- [ ] Réduire `min_range_duration` à 10
- [ ] Ajouter config par symbole
- [ ] Intégrer au bot (`launch_production_CLEAN_v2.py`)
- [ ] Tester sur Power Hour
- [ ] Valider en paper trading

---

## 📊 IMPACT ESTIMÉ

| Métrique | Avant | Après |
|----------|-------|-------|
| Trades en range middle | ✅ Autorisés | ❌ Bloqués |
| Trades breakout imminent | ✅ Autorisés | ❌ Bloqués |
| Économie estimée (Power Hour) | $0 | +$513 |
| Conformité pro | 50% | 95% |

---

**Prêt pour implémentation!**

