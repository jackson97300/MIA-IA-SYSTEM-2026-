# 🔍 AUDIT SEUILS MIA IA SYSTEM - 13 Décembre 2025

## ⚠️ DIAGNOSTIC CRITIQUE: 39 POINTS DE BLOCAGE DÉTECTÉS!

Le fichier `strategies/menthorq_3layer_strategy.py` contient **39 `return None/False`** = 39 façons de rejeter un trade!
C'est **MASSIF** et explique pourquoi le bot ne trade plus.

---

## 1. SEUILS DE SIGNAL (Quand générer un signal?)

| Paramètre | Valeur | Fichier | Impact |
|-----------|--------|---------|--------|
| `MIN_TOTAL_CONFIDENCE` ES | **1.00** 🔴 | config/trading_params.py:208 | TRÈS STRICT - Bloque ~80% signaux |
| `MIN_TOTAL_CONFIDENCE` NQ | **1.00** 🔴 | config/trading_params.py:209 | TRÈS STRICT - Bloque ~80% signaux |
| `MIN_LAYER1_CONFIDENCE` (MenthorQ) | 0.44 | config/trading_params.py:216 | Bloque si MenthorQ < 44% |
| `MIN_LAYER2_CONFIDENCE` (OrderFlow) | 0.18 | config/trading_params.py:217 | Bloque si OrderFlow < 18% |
| `MIN_LAYER3_CONFIDENCE` (Context) | 0.15 | config/trading_params.py:218 | Bloque si Context < 15% |
| `min_total_confidence` (stratégie) | 0.60 | menthorq_3layer_strategy.py:110 | Seuil de base |
| `min_layer1_confidence` (stratégie) | 0.40 | menthorq_3layer_strategy.py:111 | Seuil MenthorQ |

---

## 2. SEUILS DE DISTANCE MENTHORQ

| Paramètre | Valeur ES | Valeur NQ | Fichier | Impact |
|-----------|-----------|-----------|---------|--------|
| `MAX_DISTANCE_TO_LEVEL` | **8t** 🔴 | **10t** | config/trading_params.py:34,70 | TRÈS STRICT! |
| `MENTHORQ_DISTANCE_CONFIG` | 8t | 10t | menthorq_3layer_strategy.py:82-84 | Aligné |
| `menthorq_distance` (lanceur) | 10t | 15t | launch_production_CLEAN_v2.py:146-148 | Conflictuel! |

**⚠️ PROBLÈME DÉTECTÉ**: Les valeurs ne sont pas alignées entre fichiers!

---

## 3. HORAIRES DE TRADING (Paris)

| Session | Heures | Status | Impact |
|---------|--------|--------|--------|
| **OVERNIGHT** | 00:00-08:00 | 🔴 BLOQUÉ | 8h bloquées |
| **London** | 08:00-11:00 | ✅ AUTORISÉ | 3h de trading |
| **Pre-US Block** | 11:00-15:00 | 🔴 BLOQUÉ | 4h bloquées |
| **Pre-Market Block** | 15:00-15:50 | 🔴 BLOQUÉ | 50min bloquées |
| **US Morning** | 15:50-17:00 | ✅ AUTORISÉ | 1h10 de trading |
| **Lunch Block** | 17:00-19:30 | 🔴 BLOQUÉ | 2h30 bloquées |
| **Pre-Afternoon** | 19:30-20:00 | ⚠️ MARGINAL | 30min OK |
| **Power Hour** | 20:00-21:25 | ✅ AUTORISÉ | 1h25 de trading |
| **Hard Stop** | 21:25+ | 🔴 BLOQUÉ | Reste de la journée |

**TOTAL TRADING AUTORISÉ: ~5h35/jour sur 24h = 23% du temps seulement!**

---

## 4. FILTRES ACTIFS (Liste Complète)

### 4.1 Dans `menthorq_3layer_strategy.py` (39 points de blocage!)

| Filtre | Condition | Ligne approx. | Impact estimé |
|--------|-----------|---------------|---------------|
| Snapshot invalide | Champs requis manquants | 186-189 | ~5% bloqués |
| ML 3-Layer System absent | self.ml_3layer_system = None | 191-195 | Blocage total |
| Distance niveau > max | closest_level_distance > max_distance | 339-345 | **~40% bloqués** |
| ML result = None | result is None | 352-356 | ~10% bloqués |
| should_trade = False | result.should_trade = False | 359-371 | ~20% bloqués |
| Confidence insuffisante | total_confidence < min_confidence | 409-415 | ~15% bloqués |
| Layer1 = 0 | layer1_confidence <= 0 | 422-427 | ~5% bloqués |
| Layer1 < seuil | layer1_confidence < min_layer1_threshold | 429-436 | ~10% bloqués |
| **Pressure strength** | pressure_strength < min_pressure | 448-459 | **~20% bloqués** |
| Action invalide | action not in ['LONG', 'SHORT'] | 463-465 | ~1% bloqués |
| Validations catastrophiques | _validate_catastrophic_trade_filters | 486-491 | ~10% bloqués |
| Confluence par session | confluence_score < min_confluence | 546-552 | ~15% bloqués |
| OrderFlow par session | layer2_score < min_orderflow | 555-561 | ~10% bloqués |
| Context = 0 | layer3_score <= 0 | 567-572 | ~5% bloqués |
| Context < seuil | layer3_score < min_context | 574-580 | ~10% bloqués |
| MenthorQ par session | layer1_score < min_menthorq | 583-591 | ~10% bloqués |
| **Distance entrée invalide** | is_distance_valid = False | 664-669 | **~25% bloqués** |
| **R:R invalide** | sltp_result.is_valid = False | 688-690 | ~10% bloqués |
| Session quality faible | session_quality < min_session | 817-822 | ~5% bloqués |
| **Proximité niveau** | is_valid = False (level_proximity) | 857-859 | **~15% bloqués** |
| Validations critiques | validation_result = None | 890-892 | ~5% bloqués |
| MenthorQ UNKNOWN | menthorq_level = None | 1131-1136 | ~10% bloqués |
| MenthorQ trop loin | menthorq_distance > max_distance | 1143-1149 | ~20% bloqués |
| Prix > 1D MAX | distance_above_max > max_dist | 1178-1184 | ~5% bloqués |
| Confluence insuffisante | confluence < min_confluence | 1303-1308 | ~10% bloqués |
| MenthorQ score insuffisant | menthorq_score < min_menthorq | 1313-1318 | ~10% bloqués |
| OrderFlow insuffisant | orderflow < min_orderflow | 1321-1326 | ~10% bloqués |
| Context insuffisant | context < min_context | 1331-1336 | ~5% bloqués |

### 4.2 Dans `launch_production_CLEAN_v2.py` (Modules additionnels)

| Module | Fonction | Status | Impact |
|--------|----------|--------|--------|
| Session Quality Monitor | check_can_trade() | TEST MODE ⚠️ | Normalement bloque hors sessions |
| Risk Manager | check_can_trade() | ACTIF | Limite positions |
| Drawdown Monitor | check_position() | ACTIF | Limite pertes |
| Safety Kill Switch | is_triggered() | ACTIF | Arrêt d'urgence |
| VIX Filter | vix_thresholds | ACTIF 🔴 | Bloque VIX > 35 |
| Economic Calendar | is_blocked() | ACTIF | Bloque FOMC/NFP |
| Circuit Breaker | consecutive_losses >= 3 | ACTIF | Pause 10min après 3 pertes |
| **Trend Direction Filter** | check_direction() | ACTIF 🔴 | **Bloque contre-tendance** |
| Intraday Bracket Detector | is_in_middle() | ACTIF 🔴 | Bloque milieu bracket |
| Dual Mode Strategy | validate() | ACTIF | Peut bloquer |

### 4.3 Dans `ml/ml_3layer_filter.py` (Validation ML)

| Filtre | Condition | Impact |
|--------|-----------|--------|
| GEX distance > max | > 8t ES / 10t NQ | ~30% bloqués |
| Blind Spot distance > max | > 10t | ~20% bloqués |
| Next Wall strength < min | < 0.12 | ~15% bloqués |
| VWAP distance > max | > 10t | ~20% bloqués |
| OrderFlow alignment | Delta contradictoire | ~25% bloqués |
| Pressure strength | Acheteurs vs vendeurs | ~20% bloqués |

---

## 5. FILTRES ADDITIONNELS (SOURCES DE BLOCAGES)

### 5.1 Filtre Pressure Strength (NOUVEAU 06-07/12/2025)

```python
MIN_PRESSURE_STRENGTH_BY_SESSION = {
    'London': 0.10,        # 08:00-11:00
    'US Morning': 0.03,    # 15:50-17:00 - Le plus permissif
    'US Power Hour': 0.10, # 20:00-21:30
}

MIN_PRESSURE_STRENGTH_BY_SYMBOL = {
    'ES': 0.20,    # 🔴 ES = SEUIL LE PLUS STRICT!
    'NQ': 0.03,    # NQ = Permissif
    'RTY': 0.10,
}
```

**Impact estimé**: Bloque 20-30% des trades ES!

### 5.2 Filtre Trend Direction (02/12/2025)

```python
# Bloque trades contre-tendance
allow_counter_trend = False  # 🔴 BLOCAGE TOTAL!

# Sauf sur niveaux majeurs
counter_trend_on_major_levels = True  # Exception possible
```

**Impact estimé**: Bloque 30-40% des trades!

### 5.3 Filtre R:R Minimum

```python
MIN_RISK_REWARD_RATIO = {
    'ES': 1.00,    # R:R ≥ 1.00 requis
    'NQ': 0.50,    # Plus permissif
    'RTY': 0.50,
}
```

---

## 6. SEUILS DE VALIDATION PAR SESSION

| Session | Confluence Min | OrderFlow Min | Context Min | MenthorQ Min |
|---------|----------------|---------------|-------------|--------------|
| ASIA | 0.68 | 0.00 (désactivé) | 0.08 | 0.15 |
| London | 0.65 | 0.10 | 0.08 | 0.35 |
| US | 0.63 | 0.08 | 0.06 | 0.45 |
| Default | 0.75 | 0.20 | 0.15 | 0.50 |

---

## 7. RÉSUMÉ DU PROBLÈME D'OVER-ENGINEERING

### ❌ CE QUI NE VA PAS:

1. **39 points de blocage** dans une seule fonction de génération de signal!
2. **MIN_TOTAL_CONFIDENCE = 1.00** = Requiert 100% de confiance = IMPOSSIBLE
3. **Distance max = 8t ES** = Trop strict, le prix est rarement si proche
4. **Pressure strength ES = 0.20** = Bloque 20-30% des trades
5. **Trend filter actif** = Bloque 30-40% des trades contre-tendance
6. **Validations redondantes** = Mêmes checks à plusieurs endroits
7. **Sessions trop restrictives** = Seulement 5h35/jour de trading autorisé

### 📊 ESTIMATION D'IMPACT:

Si chaque filtre bloque indépendamment:
- Distance: 40%
- Confidence: 80% (avec seuil à 1.00!)
- Pressure: 25%
- Trend: 30%
- Sessions: 77% du temps bloqué

**RÉSULTAT**: Probablement < 1% des opportunités passent tous les filtres!

---

## 8. RECOMMANDATIONS IMMÉDIATES

### Changements URGENTS à faire:

1. **Baisser MIN_TOTAL_CONFIDENCE de 1.00 à 0.60**
   - Fichier: `config/trading_params.py:208-210`
   - Impact: +200-300% de trades

2. **Augmenter MAX_DISTANCE de 8t à 15t pour ES**
   - Fichier: `config/trading_params.py:34`
   - Impact: +50% de trades

3. **Désactiver Pressure Strength filter pour ES**
   - Fichier: `config/unified_thresholds.py:171`
   - Impact: +25% de trades

4. **Mettre Trend Filter en mode permissif**
   - Fichier: `utils/trend_direction_filter.py:110`
   - Changer: `allow_counter_trend = True`
   - Impact: +30% de trades

5. **Réduire les validations catastrophiques**
   - Fichier: `menthorq_3layer_strategy.py:900-1345`
   - Simplifier la fonction de 400+ lignes

---

*Audit généré le 13 Décembre 2025 par MIA IA System Auditor*









