# 📋 RÈGLES DE TRADING - MIA IA System

## Introduction

Ce document définit les règles strictes que le bot suit pour entrer et sortir des trades.
Ces règles sont le résultat de backtests extensifs et d'optimisations ML.

---

## 🕐 Sessions de Trading

### Horaires Autorisés (Heure Paris)

| Session | Début | Fin | Caractéristiques |
|---------|-------|-----|------------------|
| London | 08:00 | 11:00 | Volatilité modérée, bon pour ES |
| US Morning | 15:50 | 17:00 | Ouverture US, haute volatilité |
| US Power Hour | 20:00 | 21:30 | Dernière heure, mouvements forts |

### Horaires Bloqués

| Période | Raison |
|---------|--------|
| 00:00 - 08:00 | Nuit, pas de liquidité |
| 11:00 - 15:50 | Transition London/US |
| 17:00 - 20:00 | Lunch US, chop |
| 21:30 - 00:00 | Après clôture, risque overnight |

### Détection de Session
```json
"session_id": "US",
"session_elapsed_s": 31888,
"session_progress": 0.984198
```

- `session_id`: Session actuelle (London, US, Asia)
- `session_progress`: 0.98 = 98% de la session écoulée

---

## 🎯 Conditions d'Entrée

### Score Minimum ML 3-Layer

| Symbole | Seuil Minimum |
|---------|---------------|
| ES | 35% |
| NQ | 35% |
| RTY | 40% |

### Décomposition du Score

```
Score Total = Layer1 (50%) + Layer2 (30%) + Layer3 (20%)

Layer 1 (MenthorQ):
- Gamma Walls: 10%
- GEX Levels: 10%
- Blind Spots: 8%
- Next Wall: 8%
- Distances: 8%
- Confluence: 6%

Layer 2 (OrderFlow):
- Delta: 12%
- Volume: 6%
- DOM: 6%
- Pressure: 4%
- Battle Navale: 2%

Layer 3 (Context):
- VWAP: 6%
- Value Area: 5%
- Structure: 5%
- Volatility: 4%
```

### Validations Obligatoires

1. **Session OK** - Dans les horaires autorisés
2. **VIX OK** - VIX < 25 (< 35 pour skip, ≥ 35 = STOP)
3. **Pas d'annonce économique** - Pas dans fenêtre FOMC/NFP/CPI
4. **Risk Manager OK** - Pas de position ouverte sur le symbole
5. **Drawdown OK** - Pas en drawdown excessif

---

## 🛡️ Protections Obligatoires

### 1. VIX Regime Filter

```python
VIX_THRESHOLDS = {
    'low': 15,      # Trading normal
    'medium': 20,   # Trading normal
    'high': 25,     # Prudence, skip certains trades
    'extreme': 35   # STOP TOTAL
}
```

**Dans le snapshot:**
```json
"vix": 16.93
```
→ VIX à 16.93 = Trading normal ✅

### 2. Economic Calendar

Bloque le trading:
- **15 minutes AVANT** une annonce ⭐⭐⭐
- **30 minutes APRÈS** une annonce ⭐⭐⭐

Annonces bloquantes:
- FOMC (Federal Reserve)
- NFP (Non-Farm Payrolls)
- CPI (Consumer Price Index)
- GDP, Retail Sales, etc.

### 3. Drawdown Monitor

```python
MAX_DAILY_DRAWDOWN = 2.0%  # Du capital
MAX_POSITION_DRAWDOWN = 1.0%  # Par trade
```

Si atteint → STOP trading pour la journée

### 4. Safety Kill Switch

Arrêt d'urgence si:
- Perte > seuil critique
- Erreur système détectée
- Déconnexion broker

---

## 📊 Gestion des Positions

### Taille de Position

```python
POSITION_SIZES = {
    'ES': 1,   # 1 contrat
    'NQ': 1,   # 1 contrat
    'RTY': 1   # 1 contrat
}
```

### Maximum Positions

- **1 position par symbole** maximum
- **3 positions totales** maximum

### Stop Loss & Take Profit

Calculés dynamiquement basés sur:
- ATR (Average True Range)
- Distance aux niveaux MenthorQ
- Volatilité actuelle

```json
"atr": 3.18
```

Exemple pour NQ:
- Stop Loss: ~2x ATR = ~6.36 points
- Take Profit: ~3x ATR = ~9.54 points
- Ratio R/R: 1:1.5

---

## 🔄 Trailing Stop

Activé quand le trade est en profit:

```python
TRAILING_ACTIVATION = 1.0  # ATR de profit
TRAILING_DISTANCE = 0.5    # ATR de distance
```

---

## 📈 Contexte de Marché

### VWAP Position

```json
"d_vwap": -4.23,
"d_vwap_ticks": -16.929688
```

| Position | Interprétation |
|----------|----------------|
| Au-dessus VWAP | Biais haussier |
| En-dessous VWAP | Biais baissier |
| Sur VWAP | Neutre |

### Value Area

```json
"in_value_area": true,
"vva": {
    "vah": 25523.50,
    "val": 24101.00,
    "vpoc": 24800.00
}
```

| Position | Action |
|----------|--------|
| Dans VA | Trading normal |
| Au-dessus VAH | Extension, prudence |
| En-dessous VAL | Extension, prudence |

### Position dans le Range

```json
"position_in_range": 90.629139
```

- 90.6% = Prix proche du haut du range journalier
- Prudence pour les LONG à ce niveau

---

## ⚠️ Signaux de Danger

### Éviter de trader si:

1. **Blind Spot proche** (< 100 ticks)
```json
"menthor_distances": {
    "near_blind": 75  // ⚠️ DANGER
}
```

2. **Gamma Flip imminent**
```json
"gamma_flip_up": true  // ⚠️ Volatilité
```

3. **VIX élevé**
```json
"vix": 28.5  // ⚠️ Skip trades
```

4. **Fin de session**
```json
"session_progress": 0.98  // ⚠️ 98% = Presque fini
```

5. **Spread large**
```json
"spread_ticks": 4  // ⚠️ > 2 ticks = Attention
```

---

## 📝 Logging des Trades

### Trade Exécuté
```python
self.advanced_log.log_trade(symbol, "OPEN", {
    "entry": price,
    "direction": "LONG",
    "confidence": 0.45,
    "layers": {"L1": 0.52, "L2": 0.38, "L3": 0.42}
})
```

### Signal Rejeté
```python
self.trade_snapshotter.capture_rejected_signal_snapshot(
    symbol=symbol,
    signal=signal,
    ml_data=snapshot,
    rejection_reason="VIX trop haut",
    rejection_category="VIX_FILTER"
)
```

---

## 🎯 Objectifs de Performance

| Métrique | Cible |
|----------|-------|
| Win Rate | > 50% |
| Ratio R/R | 1:1.5 minimum |
| Max Trades/Jour | 10-15 |
| Max Drawdown | < 2% |
| Sessions Actives | ~5h40/jour |

---

## 📋 Checklist Avant Trade

```
□ Session autorisée?
□ VIX < 25?
□ Pas d'annonce économique?
□ Pas de position ouverte sur ce symbole?
□ Drawdown OK?
□ Score ML ≥ seuil?
□ Pas dans un blind spot?
□ Spread acceptable?
```

Si TOUT est ✅ → TRADE
Si UN seul est ❌ → SKIP

---

*Document technique MIA_IA_system - Version 1.0*
