# 📊 RÉFÉRENCE SNAPSHOT - Structure des Données

## Introduction

Ce document décrit la structure complète d'un snapshot généré par le dumper C++ (MIA_Dumper_G3_Unifier).
Chaque snapshot contient toutes les données nécessaires pour prendre une décision de trading.

---

## 📄 Exemple de Snapshot Complet

```json
{
  "t_ms": 1764111088400,
  "sym": "NQZ25_FUT_CME",
  "chart": 9,
  "mid": 25065.25,
  "spread": 0.50,
  "spread_ticks": 2,
  "microprice": 25065.17,
  "microgap": 0.08,
  "microgap_n": -0.026217,
  "microgap_signed": -0.08,
  "best_bid": 25065.00,
  "best_ask": 25065.50,
  "q_bq1": 1,
  "q_aq1": 2,
  "dom_bbo_mid_diff": -3.50,
  "dom_bbo_spread_diff_ticks": 28,
  "d_vwap": -4.23,
  "d_vwap_ticks": -16.929688,
  "d_vwap_weekly": 159.29,
  "d_vwap_weekly_ticks": 637.171875,
  "d_vwap_monthly": -301.38,
  "d_vwap_monthly_ticks": -1205.539063,
  "d_w_up1": 75.84,
  "d_w_up1_ticks": 303.367188,
  "d_w_dn1": 326.20,
  "d_w_dn1_ticks": 1304.781250,
  "d_pvwap": 183.24,
  "d_pvwap_ticks": 732.952467,
  "d_vpoc": 265.25,
  "d_vpoc_ticks": 1061.000000,
  "d_vah": -458.25,
  "d_vah_ticks": -1833.000000,
  "d_val": 964.25,
  "d_val_ticks": 3857.000000,
  "level1_imbalance": -0.333333,
  "point_value": 20.00,
  "price_scale": 2,
  "tsec": 1764111088.40,
  "emit_reason": "base",
  "seq_unified": 79990,
  "vwap": 25069.48,
  "vwap_weekly": 24905.96,
  "vwap_monthly": 25366.63,
  "atr": 3.18,
  "pvwap": 24882.01,
  "vva": {
    "vah": 25523.50,
    "val": 24101.00,
    "vpoc": 24800.00
  },
  "d_vwap_atr": -1.331548,
  "d_vpoc_atr": 83.449437,
  "micro_imb": -0.333333,
  "bar_index": 43710,
  "open": 25064.75,
  "high": 25066.25,
  "low": 25063.75,
  "close": 25064.50,
  "volume": 115,
  "bidvol": 67,
  "askvol": 48,
  "dom_bid1": 25058.00,
  "dom_ask1": 25065.50,
  "dom_bq1": 1,
  "dom_aq1": 2,
  "vwap_up1": 25072.44,
  "vwap_dn1": 25063.58,
  "vwap_up2": 25075.39,
  "vwap_dn2": 25060.62,
  "vwap_up3": 25078.34,
  "vwap_dn3": 25057.67,
  "vwap_weekly_up1": 24989.41,
  "vwap_weekly_dn1": 24739.05,
  "pvwap_up1": 24946.97,
  "pvwap_dn1": 24817.05,
  "pvwap_up2": 25011.93,
  "pvwap_dn2": 24752.09,
  "cum_delta_day": -1841,
  "cum_delta_session": -1926,
  "nbcv": {
    "ask_volume": 48,
    "bid_volume": 67,
    "delta": 19,
    "total_volume": 115
  },
  "askPct": 0.417391,
  "bidPct": 0.582609,
  "deltaPct": 0.165217,
  "pressure": 0,
  "corr": 0.977424,
  "vix": 16.93,
  "elapsed_s": 31888,
  "progress01": 0.984198,
  "last_mq_update_ms": 1764111088400,
  "is_1tick_spread": false,
  "in_value_area": true,
  "ob_center": -0.333333,
  "top_heavy": 1.000000,
  "tick_rate_3s": 1.000000,
  "delta_cum_10s": 0,
  "confluence_density": 0,
  "confluence_strength": 0.038183,
  "confluence_proximity": 75.28,
  "gamma_call_confluence": false,
  "gamma_put_confluence": false,
  "blind_spot_confluence": false,
  "delta": 19,
  "tick_rate_1s": 1,
  "trade_rate_1s": 0,
  "delta_rate_1s": 0,
  "gex_1": 24900.00,
  "gex_2": 25000.00,
  "gex_3": 24700.00,
  "gex_4": 25125.00,
  "gex_5": 25200.00,
  "gex_6": 24500.00,
  "gex_7": 25500.00,
  "gex_8": 25600.00,
  "gex_9": 24600.00,
  "gex_10": 24400.00,
  "call_resistance": 25400.00,
  "put_support": 24800.00,
  "hvl": 24825.00,
  "1d_max": 25294.04,
  "1d_min": 24602.46,
  "blind_spot_0": 24483.29,
  "blind_spot_1": 24606.50,
  "blind_spot_2": 24274.70,
  "blind_spot_3": 24820.59,
  "blind_spot_4": 25280.48,
  "blind_spot_5": 25150.05,
  "blind_spot_6": 23975.84,
  "blind_spot_7": 24185.13,
  "blind_spot_8": 25084.07,
  "dom_bid_1": 1,
  "dom_bid_2": 0,
  "dom_bid_3": 0,
  "dom_bid_4": 0,
  "dom_bid_5": 0,
  "dom_bid_6": 0,
  "dom_bid_7": 0,
  "dom_bid_8": 0,
  "dom_bid_9": 0,
  "dom_bid_10": 0,
  "dom_ask_1": 2,
  "dom_ask_2": 0,
  "dom_ask_3": 0,
  "dom_ask_4": 0,
  "dom_ask_5": 0,
  "dom_ask_6": 0,
  "dom_ask_7": 0,
  "dom_ask_8": 0,
  "dom_ask_9": 0,
  "dom_ask_10": 0,
  "dom_features": {
    "depth_bid": 1,
    "depth_ask": 2,
    "rings_bid": 1,
    "rings_ask": 1,
    "imbalance_1_3": 0.400000,
    "imbalance_6_10": 0.176471,
    "slope_bid_1_3": 3,
    "slope_ask_1_3": 0,
    "slope_bid_1_3_n": 30.000000,
    "slope_ask_1_3_n": 0.000000
  },
  "menthor_distances": {
    "gamma0": 1339,
    "call0": 1339,
    "put0": -1061,
    "hvl0": -961,
    "call": 339,
    "put": -1061,
    "hvl": -961,
    "dist_1d_max": 915,
    "dist_1d_min": -1851,
    "near_gex_up": 239,
    "near_gex_dn": 261,
    "near_blind": 75
  },
  "session_id": "US",
  "session_elapsed_s": 31888,
  "session_progress": 0.984198,
  "menthor_meta": {
    "month": "2025-11",
    "quarter": "2025Q4"
  },
  "is_dom_fresh": true,
  "dom_age_ms": 0,
  "sizes_source": "L2",
  "data_quality": "OK",
  "ob_center_b": -0.333333,
  "ob_center_tanh": -0.244919,
  "battle_navale_signal_strength": 0.038183,
  "battle_navale_confidence": 0.045819,
  "menthorq_impact_score": 0.075281,
  "menthorq_proximity_strength": 0.150563,
  "smart_money_flow": -0.165217,
  "institutional_pressure": 0.165217,
  "tick_momentum": -0.333333,
  "depth_imbalance": -0.333333,
  "pressure_strength": 0.038333,
  "pressure_strength_depth": 0.333333,
  "pressure_strength_atr": 0.008739,
  "volatility_regime": 1.000000,
  "volatility_regime5": 2.000000,
  "volatility_regime_cont": 0.136944,
  "atr_ratio": 12.714286,
  "intermarkets": {
    "es_nq_lead_ms_120s": null,
    "es_nq_lead_cc": null,
    "nq_es_rs_z_120s": -0.351891,
    "divergence_flag": 0
  },
  "structure": {
    "onh": 24516.63,
    "onl": 24513.88,
    "on_fix_ts": 1764081000284,
    "ibh": 24874.75,
    "ibl": 24603.63,
    "awap_onh": 24827.03,
    "awap_onl": 24827.03,
    "awap_ibo": 24889.86,
    "awap_ibo_ts": 1764081000284
  },
  "next_wall": {
    "price": 25125.00,
    "side": "call",
    "dist_pts": 59.75,
    "dist_ticks": 239,
    "strength": 0.304167,
    "age_min": 0
  },
  "mia_bullish_score": -0.439567,
  "sell_pct": 0.417391,
  "buy_pct": 0.582609,
  "delta_burst": 19,
  "delta_flip": false,
  "upper_wick_ticks": 6.000000,
  "lower_wick_ticks": 3.000000,
  "total_range_ticks": 10.000000,
  "stacked_imbalance_bid_rows": 0,
  "stacked_imbalance_ask_rows": 0,
  "gamma_flip_up": false,
  "gamma_flip_down": false,
  "gamma_side": "below",
  "gamma_wall_level": 25400.00,
  "distance_to_high_pct": 0.281477,
  "distance_to_low_pct": 2.806575,
  "day_range_pct": 3.024476,
  "position_in_range": 90.629139,
  "feature_version": "v3.5.23_awap_corruption_fixed"
}
```

---

## 📑 Catégories de Champs

### 1. Métadonnées

| Champ | Type | Description |
|-------|------|-------------|
| `t_ms` | int | Timestamp en millisecondes |
| `sym` | string | Symbole (ex: NQZ25_FUT_CME) |
| `chart` | int | ID du chart Sierra Chart |
| `emit_reason` | string | Raison de l'émission |
| `seq_unified` | int | Numéro de séquence |
| `feature_version` | string | Version du dumper |

### 2. Prix et Spread

| Champ | Type | Description |
|-------|------|-------------|
| `mid` | float | Prix milieu |
| `best_bid` | float | Meilleur bid |
| `best_ask` | float | Meilleur ask |
| `spread` | float | Spread en points |
| `spread_ticks` | int | Spread en ticks |
| `microprice` | float | Prix micro-ajusté |

### 3. OHLCV (Barre actuelle)

| Champ | Type | Description |
|-------|------|-------------|
| `open` | float | Prix ouverture |
| `high` | float | Prix haut |
| `low` | float | Prix bas |
| `close` | float | Prix clôture |
| `volume` | int | Volume total |
| `bidvol` | int | Volume au bid |
| `askvol` | int | Volume au ask |

### 4. VWAP et Bandes

| Champ | Type | Description |
|-------|------|-------------|
| `vwap` | float | VWAP du jour |
| `vwap_weekly` | float | VWAP hebdomadaire |
| `vwap_monthly` | float | VWAP mensuel |
| `d_vwap` | float | Distance au VWAP |
| `vwap_up1/2/3` | float | Bandes supérieures |
| `vwap_dn1/2/3` | float | Bandes inférieures |

### 5. Value Area

| Champ | Type | Description |
|-------|------|-------------|
| `vva.vah` | float | Value Area High |
| `vva.val` | float | Value Area Low |
| `vva.vpoc` | float | Volume POC |
| `in_value_area` | bool | Prix dans VA? |

### 6. Delta et Order Flow

| Champ | Type | Description |
|-------|------|-------------|
| `delta` | int | Delta de la barre |
| `cum_delta_day` | int | Delta cumulé jour |
| `cum_delta_session` | int | Delta cumulé session |
| `bidPct` | float | % volume au bid |
| `askPct` | float | % volume au ask |
| `deltaPct` | float | % delta |

### 7. DOM (Depth of Market)

| Champ | Type | Description |
|-------|------|-------------|
| `dom_bid_1..10` | int | Quantités bid |
| `dom_ask_1..10` | int | Quantités ask |
| `level1_imbalance` | float | Imbalance niveau 1 |
| `depth_imbalance` | float | Imbalance profondeur |

### 8. MenthorQ (Options/Gamma)

| Champ | Type | Description |
|-------|------|-------------|
| `gex_1..10` | float | Niveaux GEX |
| `call_resistance` | float | Résistance calls |
| `put_support` | float | Support puts |
| `hvl` | float | Highest Volume Level |
| `gamma_wall_level` | float | Niveau gamma wall |
| `blind_spot_0..8` | float | Zones aveugles |

### 9. Distances MenthorQ

| Champ | Type | Description |
|-------|------|-------------|
| `menthor_distances.gamma0` | int | Distance gamma (ticks) |
| `menthor_distances.call` | int | Distance call |
| `menthor_distances.put` | int | Distance put |
| `menthor_distances.near_blind` | int | Distance blind spot |

### 10. Scores Calculés

| Champ | Type | Description |
|-------|------|-------------|
| `mia_bullish_score` | float | Score bullish global |
| `institutional_pressure` | float | Pression institutionnelle |
| `smart_money_flow` | float | Flux smart money |
| `battle_navale_confidence` | float | Confiance Battle Navale |
| `menthorq_impact_score` | float | Impact MenthorQ |

### 11. Session et Volatilité

| Champ | Type | Description |
|-------|------|-------------|
| `session_id` | string | Session actuelle |
| `session_progress` | float | Progression (0-1) |
| `vix` | float | Valeur VIX |
| `volatility_regime` | int | Régime (1-5) |
| `atr` | float | Average True Range |

### 12. Structure de Marché

| Champ | Type | Description |
|-------|------|-------------|
| `structure.onh` | float | Overnight High |
| `structure.onl` | float | Overnight Low |
| `structure.ibh` | float | Initial Balance High |
| `structure.ibl` | float | Initial Balance Low |

### 13. Next Wall

| Champ | Type | Description |
|-------|------|-------------|
| `next_wall.price` | float | Prix du mur |
| `next_wall.side` | string | Type (call/put) |
| `next_wall.dist_ticks` | int | Distance en ticks |
| `next_wall.strength` | float | Force (0-1) |

---

## 🔧 Utilisation dans le Code

### Lecture d'un Snapshot

```python
from features.ml_ready_reader import MLReadyReader

reader = MLReadyReader()
snapshot = reader.get_latest_snapshot("NQ")

# Accès aux champs
price = snapshot.get('mid')
delta = snapshot.get('delta')
vix = snapshot.get('vix')
```

### Champs Critiques pour le ML

```python
# Layer 1 (MenthorQ)
gex_levels = [snapshot.get(f'gex_{i}') for i in range(1, 11)]
call_res = snapshot.get('call_resistance')
put_sup = snapshot.get('put_support')
blind_spots = [snapshot.get(f'blind_spot_{i}') for i in range(9)]

# Layer 2 (OrderFlow)
delta = snapshot.get('delta')
bid_pct = snapshot.get('bidPct')
dom_imb = snapshot.get('level1_imbalance')
pressure = snapshot.get('institutional_pressure')

# Layer 3 (Context)
d_vwap = snapshot.get('d_vwap')
in_va = snapshot.get('in_value_area')
vix = snapshot.get('vix')
```

---

## 📝 Notes Importantes

1. **Timestamps:** En millisecondes UTC
2. **Distances:** En TICKS (pas en points)
3. **Scores:** Normalisés entre -1 et +1
4. **Pourcentages:** Entre 0 et 1
5. **Qualité:** Vérifier `data_quality == "OK"`

---

*Document technique MIA_IA_system - Version 1.0*
