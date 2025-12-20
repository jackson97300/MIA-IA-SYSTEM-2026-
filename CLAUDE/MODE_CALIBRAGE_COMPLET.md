# 🔬 MODE CALIBRAGE - COLLECTE DE DONNÉES QUALITÉ

**Date:** 18 Novembre 2025  
**Phase:** Calibrage et apprentissage  
**Objectif:** Collecter données de qualité sur toutes les sessions

---

## 🎯 PHILOSOPHIE DU CALIBRAGE

```
┌─────────────────────────────────────────────────┐
│  "Pas de limite de gain/perte"                  │
│  "On veut des données, mais des données qualité"│
│                                                 │
│  → LAISSER LE SYSTÈME APPRENDRE                │
│  → TRADER TOUTES LES SESSIONS                  │
│  → COLLECTER UN MAXIMUM D'INFORMATIONS         │
└─────────────────────────────────────────────────┘

Phase actuelle: APPRENTISSAGE
Phase suivante: OPTIMISATION (quand données suffisantes)
```

---

## 📊 CONFIGURATION MODE CALIBRAGE

### Symboles actifs
```
✅ ES (S&P 500) - ACTIF
✅ NQ (Nasdaq) - ACTIF
⏸️ RTY (Russell) - EN ATTENTE (après stabilisation ES/NQ)
```

### Sessions de trading
```
🌏 ASIA:    18:00 → 03:00 (9h)
🌍 EUROPE:  03:00 → 09:30 (6h30)
🇺🇸 US:     09:30 → 16:00 (6h30)
🌙 AFTER:   16:00 → 18:00 (2h)

TOTAL: 24h de trading
```

### Limites
```
❌ PAS de limite de gain journalier
❌ PAS de limite de perte journalière
❌ PAS d'arrêt automatique

MAIS:
✅ Surveillance active
✅ Kill switch manuel si problème technique
✅ Monitoring qualité des données
```

---

## 🎯 OBJECTIFS DU CALIBRAGE

### Objectif #1: Volume de données
```
TARGET: 30 jours de calibrage
├─ ~200 trades/jour × 30 jours = 6,000 trades
├─ Couvre toutes les sessions
├─ Couvre tous les régimes de marché
└─ Dataset complet pour optimisation

Minimum requis: 3,000 trades sur 15 jours
```

### Objectif #2: Qualité des données
```
Pour chaque trade, collecter:
├─ Snapshot complet au moment de l'entrée
├─ Snapshot complet au moment de la sortie
├─ Tous les scores (Confluence, ML, MenthorQ, etc.)
├─ Raison d'entrée (stratégie, setup)
├─ Raison de sortie (SL, TP, trailing, manuel)
├─ MFE/MAE (Maximum Favorable/Adverse Excursion)
├─ Conditions de marché (régime, biais, session)
└─ Performance post-sortie (aurait-on dû rester?)

Format: JSON ultra-détaillé (comme vos snapshots actuels)
```

### Objectif #3: Couverture complète
```
Sessions à couvrir:
├─ ASIA: 30 jours × 9h = 270h
├─ EUROPE: 30 jours × 6.5h = 195h
├─ US: 30 jours × 6.5h = 195h
└─ AFTER: 30 jours × 2h = 60h

Régimes à capturer:
├─ Trending UP (bull runs)
├─ Trending DOWN (sell-offs)
├─ Range-bound (consolidation)
├─ High volatility (VIX > 20)
├─ Low volatility (VIX < 15)
├─ News events (FOMC, CPI, etc.)
└─ Normal trading

Symboles:
├─ ES: Tous régimes, toutes sessions
└─ NQ: Tous régimes, toutes sessions
```

---

## 📋 CONFIGURATION OPTIMALE POUR CALIBRAGE

### Fichier: trading_config.py

```python
# ═══════════════════════════════════════════════════════
# MODE CALIBRAGE - COLLECTE DE DONNÉES
# Date: 18 Novembre 2025
# Phase: Apprentissage et calibrage
# ═══════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────
# SYMBOLES
# ──────────────────────────────────────────────────────
ACTIVE_SYMBOLS = ["ES", "NQ"]  # ES et NQ actifs
# ACTIVE_SYMBOLS = ["ES", "NQ", "RTY"]  # RTY après stabilisation

# ──────────────────────────────────────────────────────
# SESSIONS (24h trading)
# ──────────────────────────────────────────────────────
TRADING_24H = True  # Trader toutes les sessions
# Ou spécifier manuellement:
# TRADING_START = "00:00"
# TRADING_END = "23:59"

# Sessions définies pour analytics
SESSIONS = {
    "ASIA": {"start": "18:00", "end": "03:00"},
    "EUROPE": {"start": "03:00", "end": "09:30"},
    "US": {"start": "09:30", "end": "16:00"},
    "AFTER": {"start": "16:00", "end": "18:00"}
}

# ──────────────────────────────────────────────────────
# LIMITES (MODE CALIBRAGE = PAS DE LIMITES)
# ──────────────────────────────────────────────────────
MAX_DAILY_LOSS = None  # Pas de limite de perte
MAX_DAILY_PROFIT = None  # Pas de limite de gain
MAX_CONSECUTIVE_LOSSES = None  # Pas d'arrêt automatique

# MAIS kill switch manuel disponible
MANUAL_KILL_SWITCH_ENABLED = True

# ──────────────────────────────────────────────────────
# PARAMÈTRES DE TRADING (CONSERVATEURS POUR QUALITÉ)
# ──────────────────────────────────────────────────────

# Stops (légèrement élargis pour laisser respirer)
NQ_STOP_LOSS = 13  # ticks (vs 10 original)
NQ_TAKE_PROFIT = 26  # ticks (ratio 1:2)

ES_STOP_LOSS = 10  # ticks (vs 8 original) 
ES_TAKE_PROFIT = 20  # ticks (ratio 1:2)

# Trailing stop
TRAILING_STOP_ENABLED = True
TRAILING_STOP_TRIGGER = 12  # ticks (légèrement élargi)
TRAILING_STOP_DISTANCE = 6  # ticks

# ──────────────────────────────────────────────────────
# SEUILS DE QUALITÉ (FILTRAGE MINIMUM)
# ──────────────────────────────────────────────────────

# Confluence
MIN_CONFLUENCE = 0.45  # Légèrement abaissé pour plus de trades
# MIN_CONFLUENCE = 0.50  # ← Original

# ML
ML_ENABLED = True  # Garder ML actif pour collecter données
ML_MIN_CONFIDENCE = 0.52  # Légèrement abaissé
# ML_MIN_CONFIDENCE = 0.55  # ← Original

# Mais on COLLECTE toutes les prédictions ML même rejetées
LOG_REJECTED_SIGNALS = True  # IMPORTANT!

# ──────────────────────────────────────────────────────
# RISK MANAGEMENT (RAISONNABLE)
# ──────────────────────────────────────────────────────

RISK_PER_TRADE = 100  # $ - Risk par trade
MAX_POSITIONS_PER_SYMBOL = 1  # Une position à la fois par symbole
MAX_TOTAL_POSITIONS = 2  # Max 2 positions simultanées (1 ES + 1 NQ)

# Position sizing basé sur risk
POSITION_SIZING_METHOD = "risk_based"  # vs fixed

# ──────────────────────────────────────────────────────
# COLLECTE DE DONNÉES (CRITIQUE!)
# ──────────────────────────────────────────────────────

# Snapshots complets
SAVE_ENTRY_SNAPSHOT = True
SAVE_EXIT_SNAPSHOT = True
SAVE_REJECTED_SNAPSHOTS = True  # IMPORTANT pour analyse!

# Logging détaillé
LOG_LEVEL = "DEBUG"  # Maximum de détails
LOG_ALL_DECISIONS = True
LOG_ALL_SCORES = True
LOG_ALL_FEATURES = True

# Export des trades
EXPORT_TRADES_FORMAT = "JSON"  # Format détaillé
EXPORT_FREQUENCY = "REALTIME"  # Export en temps réel
BACKUP_SNAPSHOTS_DAILY = True

# ──────────────────────────────────────────────────────
# MONITORING & ALERTES
# ──────────────────────────────────────────────────────

# Discord notifications (ajustées pour calibrage)
DISCORD_ENABLED = True
DISCORD_NOTIFY_TRADES = True  # Tous les trades
DISCORD_NOTIFY_HOURLY_SUMMARY = True  # Résumé horaire
DISCORD_NOTIFY_SESSION_SUMMARY = True  # Résumé par session
DISCORD_NOTIFY_DAILY_SUMMARY = True  # Résumé journalier

# Alertes importantes seulement
DISCORD_ALERT_LARGE_LOSS = 500  # Alert si perte > $500 sur 1 trade
DISCORD_ALERT_TECHNICAL_ISSUE = True  # Problèmes techniques

# ──────────────────────────────────────────────────────
# SÉCURITÉ & SANITY CHECKS
# ──────────────────────────────────────────────────────

# Data quality checks
CHECK_DATA_FRESHNESS = True
MAX_DATA_AGE_MS = 2000  # 2 secondes max
REJECT_STALE_DATA = True

# Connexion DTC
CHECK_DTC_CONNECTION = True
RECONNECT_ON_DISCONNECT = True

# Sanity checks
CHECK_SPREAD_BEFORE_ENTRY = True
MAX_SPREAD_TICKS_NQ = 2
MAX_SPREAD_TICKS_ES = 2

CHECK_VOLUME_BEFORE_ENTRY = True
MIN_VOLUME_NQ = 100  # Contrats
MIN_VOLUME_ES = 100

# ──────────────────────────────────────────────────────
# MODE PAPER/LIVE
# ──────────────────────────────────────────────────────

TRADING_MODE = "PAPER"  # Ou "LIVE" selon votre compte
# Pour calibrage, PAPER est recommandé initialement

# Si LIVE, comptes simulés
ACCOUNT_ES = "SIM1"
ACCOUNT_NQ = "SIM2"
ACCOUNT_RTY = "SIM3"  # Pour plus tard
```

---

## 📊 STRUCTURE DES DONNÉES À COLLECTER

### Format des snapshots de trades
```json
{
  "trade_id": "20251118_001_NQ_SHORT",
  "timestamp_entry": 1731888000000,
  "timestamp_exit": 1731891360000,
  "symbol": "NQ",
  "direction": "SHORT",
  "
  
  "entry": {
    "price": 24908.00,
    "snapshot": {
      // Tout votre snapshot habituel (50+ features)
      "mid": 24908.00,
      "spread": 0.75,
      "confluence": 0.84,
      "menthorq_score": 0.65,
      "ml_prediction": "SHORT",
      "ml_confidence": 0.68,
      "vwap": 24902.07,
      "d_vwap": 11.55,
      "gamma_wall": 26000.00,
      // ... tous les autres
    },
    "strategy": "menthorq_3layer_strategy",
    "setup": "RETEST_PREMIUM",
    "scores": {
      "confluence": 0.84,
      "menthorq": 0.65,
      "orderflow": 0.25,
      "context": 0.27,
      "ml_confidence": 0.68
    },
    "market_context": {
      "bias": "NEUTRAL",
      "regime": "mean_reversion",
      "session": "US",
      "vix": 16.93,
      "atr": 5.57
    }
  },
  
  "exit": {
    "price": 24907.50,
    "reason": "STOP_LOSS",
    "snapshot": {
      // Snapshot complet au moment de la sortie
    },
    "duration_minutes": 56.03,
    "pnl_usd": -4.00,
    "pnl_ticks": -0.5
  },
  
  "performance": {
    "mfe_ticks": 9.0,  // Maximum Favorable
    "mae_ticks": -0.5,  // Maximum Adverse
    "efficiency": -0.06,  // -6%
    "hold_time_minutes": 56.03,
    "slippage_entry_ticks": 0.25,
    "slippage_exit_ticks": 0.25
  },
  
  "post_analysis": {
    "price_5min_after": 24905.00,  // Où était le prix 5min après?
    "price_15min_after": 24900.00,
    "price_30min_after": 24895.00,
    "should_have_held": true,  // Aurait-on dû rester?
    "optimal_exit_price": 24899.00,  // Meilleur exit possible
    "optimal_pnl": 36.00  // P&L qu'on aurait pu avoir
  },
  
  "session_context": {
    "session_name": "US",
    "session_elapsed_minutes": 210,
    "session_pnl_before": 1200.00,
    "trades_in_session": 45,
    "win_rate_in_session": 0.48
  }
}
```

---

## 🎯 MÉTRIQUES À MONITORER PENDANT LE CALIBRAGE

### Dashboard temps réel
```
┌─────────────────────────────────────────────────┐
│ MODE CALIBRAGE - JOUR 5/30                      │
├─────────────────────────────────────────────────┤
│                                                 │
│ TRADES COLLECTÉS: 987 / 6000 (16%)            │
│                                                 │
│ PAR SESSION:                                    │
│ ├─ ASIA:   198 trades (20%)                   │
│ ├─ EUROPE: 156 trades (16%)                   │
│ ├─ US:     489 trades (50%)                   │
│ └─ AFTER:  144 trades (14%)                   │
│                                                 │
│ PAR SYMBOLE:                                    │
│ ├─ ES: 423 trades (43%)                       │
│ └─ NQ: 564 trades (57%)                       │
│                                                 │
│ RÉGIMES COUVERTS:                              │
│ ├─ Trending: 456 trades (46%)                 │
│ ├─ Range: 389 trades (39%)                    │
│ └─ High Vol: 142 trades (14%)                 │
│                                                 │
│ QUALITÉ DONNÉES:                               │
│ ├─ Snapshots complets: 987/987 (100%) ✅      │
│ ├─ Data staleness: 0 rejets ✅                │
│ └─ Missing features: 0 ✅                      │
│                                                 │
│ PERFORMANCE (indicatif):                       │
│ ├─ P&L Net: +$2,456.80                        │
│ ├─ Win Rate: 44.2%                            │
│ └─ Trades/jour: 197                           │
└─────────────────────────────────────────────────┘
```

### Métriques de qualité
```
DATA QUALITY SCORE: 98/100 ✅

├─ Freshness: 100% (pas de stale data)
├─ Completeness: 100% (tous les champs remplis)
├─ Coverage: 96% (sessions bien couvertes)
├─ Variety: 94% (régimes variés)
└─ Volume: 16% (987/6000 trades)

READY FOR OPTIMIZATION: NON (16% seulement)
CONTINUE CALIBRATION: 24 jours restants
```

---

## 📋 CHECKLIST QUOTIDIENNE (MODE CALIBRAGE)

### Matin (avant session)
- [ ] Vérifier connexion DTC
- [ ] Vérifier que ES + NQ sont actifs
- [ ] Vérifier logs de la nuit (ASIA/EUROPE)
- [ ] Vérifier espace disque (snapshots lourds)
- [ ] Backup des données de la veille

### Pendant les sessions
- [ ] Monitor Discord (résumés horaires)
- [ ] Check data quality toutes les 4h
- [ ] Vérifier qu'aucun crash
- [ ] Surveiller que les snapshots sont bien sauvés

### Soir (fin de session US)
- [ ] Analyser le résumé journalier
- [ ] Compter trades collectés
- [ ] Vérifier couverture sessions
- [ ] Noter événements spéciaux (news, volatilité)
- [ ] Backup final de la journée

### Hebdomadaire (dimanche)
- [ ] Analyser la semaine
- [ ] Calculer % progression calibrage
- [ ] Vérifier équilibre sessions/régimes
- [ ] Ajuster si besoin (mais minimalement!)
- [ ] Préparer rapport pour vous

---

## 🎯 CRITÈRES DE FIN DE CALIBRAGE

### Quand arrêter le calibrage?
```
Minimum absolu: 3,000 trades sur 15 jours
Optimal: 6,000 trades sur 30 jours

ET

✅ Couverture sessions: Chaque session ≥ 15% des trades
✅ Couverture symboles: ES et NQ ≥ 40% chacun
✅ Couverture régimes: Trending + Range + Vol ≥ 30% chacun
✅ Qualité données: 100% snapshots complets
✅ Pas de bias majeur (ex: 90% trades pendant US seulement)
```

### Ensuite: Phase d'optimisation
```
1. Analyse exhaustive des 6,000 trades
2. Identification patterns gagnants/perdants
3. Optimisation ML (retrain sur nouvelles données)
4. Optimisation seuils (backtest sur données réelles)
5. Optimisation stratégies (quoi activer/désactiver)
6. Optimisation paramètres (stops, TP, sizing)
7. Backtest complet sur données collectées
8. Validation sur 3-5 jours forward
9. Passage en production optimisée
```

---

## ⚠️ PIÈGES À ÉVITER EN MODE CALIBRAGE

### Piège #1: Trop optimiser pendant le calibrage
```
❌ NE FAITES PAS:
- Changer les paramètres tous les jours
- Désactiver une stratégie après 1 mauvaise journée
- Sur-réagir aux pertes

✅ FAITES:
- Garder la config stable
- Noter les observations
- Collecter des données
- Optimiser APRÈS le calibrage
```

### Piège #2: Arrêter trop tôt
```
❌ 500 trades = PAS ASSEZ
❌ 1000 trades = INSUFFISANT
✅ 3000 trades = MINIMUM
✅✅ 6000 trades = OPTIMAL
```

### Piège #3: Data de mauvaise qualité
```
❌ Snapshots incomplets
❌ Data stale acceptée
❌ Features manquantes
❌ Timestamps incorrects

→ Garbage in, garbage out!
```

### Piège #4: Bias de survie
```
Si vous n'activez ES qu'après qu'il performe:
→ Vous ratez les données "ES en difficulté"
→ Optimisation biaisée

Gardez ES + NQ actifs TOUT LE TEMPS!
```

---

## 🚀 ACTIONS IMMÉDIATES POUR DÉMARRER

### 1. Vérifier/Modifier la configuration (15 min)
```
Fichiers à vérifier:
├─ trading_config.py
│   ├─ ACTIVE_SYMBOLS = ["ES", "NQ"] ✅
│   ├─ TRADING_24H = True ✅
│   ├─ MAX_DAILY_LOSS = None ✅
│   └─ LOG_REJECTED_SNAPSHOTS = True ✅
│
├─ symbol_profiles.py
│   ├─ NQ stops: 13 ticks ✅
│   └─ ES stops: 10 ticks ✅
│
└─ ml_3layer_integration_config.py
    └─ LOG_ALL_PREDICTIONS = True ✅
```

### 2. Créer dossier de calibrage (5 min)
```bash
# Structure pour données de calibrage
D:\MIA_IA_system\CALIBRAGE_PHASE\
├─ TRADES\
│   ├─ 2025-11-18\
│   ├─ 2025-11-19\
│   └─ ...
├─ SNAPSHOTS\
│   ├─ entry\
│   └─ exit\
├─ ANALYTICS\
│   ├─ daily_summary\
│   └─ weekly_reports\
└─ CONFIG_HISTORY\
    └─ backups\
```

### 3. Lancer le monitoring (10 min)
```
- Ouvrir Discord
- Activer notifications
- Préparer dashboard (optionnel)
- Vérifier que logs s'écrivent
```

### 4. START TRADING! 🚀
```
python launch_ml_v3_production.py --mode calibration

Ou votre commande habituelle de lancement
```

---

## 📞 SUPPORT PENDANT LE CALIBRAGE

**Je suis là pour:**
- ✅ Analyser les résumés hebdomadaires
- ✅ Vérifier la qualité des données
- ✅ Recommander des ajustements mineurs
- ✅ Créer des rapports d'analyse
- ✅ Répondre à vos questions

**Fréquence recommandée:**
- Check rapide: Tous les 2-3 jours
- Analyse détaillée: Toutes les semaines
- Rapport complet: Fin du calibrage (30 jours)

---

## 🎯 RÉSUMÉ - CE QUI CHANGE

### Par rapport à avant
```
AVANT (Production classique):
- Limites de gain/perte
- Optimisation continue
- Focus sur P&L

MAINTENANT (Calibrage):
- Pas de limites
- Config stable
- Focus sur DATA
```

### Configuration mode calibrage
```
✅ ES + NQ actifs 24h/24
✅ Toutes les sessions
✅ Pas de limites gain/perte
✅ Stops légèrement élargis (qualité > quantité)
✅ Logging maximal
✅ Snapshots complets
✅ 30 jours minimum
```

---

**PRÊT À DÉMARRER LE CALIBRAGE?**

Dites-moi si vous voulez que je:
1. Génère le fichier de config complet
2. Crée un script de monitoring
3. Prépare les prompts Cursor pour analyse hebdomadaire
4. Autre chose?

**LET'S COLLECT QUALITY DATA! 📊🚀**
