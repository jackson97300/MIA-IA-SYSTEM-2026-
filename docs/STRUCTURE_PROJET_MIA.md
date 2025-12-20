# 📁 STRUCTURE DU PROJET MIA_IA_system
## Version CLEAN v2 - 29 Novembre 2025

---

## 🎯 VUE D'ENSEMBLE

```
MIA_IA_system/
│
├── 🚀 PRODUCTION (Pipeline Active)
│   ├── LAUNCH/                    # Lanceur principal
│   ├── core/                      # Modules core
│   ├── ml/                        # Machine Learning 3-Layer
│   ├── strategies/                # Stratégies de trading
│   ├── execution/                 # Exécution des ordres
│   ├── monitoring/                # Discord & Alertes
│   ├── features/                  # Calculateurs de features
│   ├── config/                    # Configurations
│   └── utils/                     # Utilitaires
│
├── 📊 DONNÉES
│   ├── snapshots/                 # Snapshots ML (dumper)
│   ├── snapshots_trades/          # Captures trades pour ML
│   ├── DATA_SIERRA_CHART/         # Données marché Sierra
│   ├── logs/                      # Logs système
│   ├── logs_advanced/             # Logs avancés thématiques
│   ├── data/                      # Données runtime
│   └── models/                    # Modèles ML entraînés
│
├── 🔧 OUTILS
│   ├── extracteur/                # Dumper C++ Sierra Chart
│   ├── backtesting/               # Scripts backtest
│   └── backtests/                 # Résultats backtest
│
└── 🗄️ ARCHIVE
    └── ARCHIVE/                   # Anciens fichiers (backup)
```

---

## 🚀 DOSSIERS DE PRODUCTION

### 📂 LAUNCH/ (Lanceur Principal)
```
LAUNCH/
└── launch_production_CLEAN_v2.py   # ⭐ LANCEUR PRINCIPAL (2,338 lignes)
```

**Responsabilités:**
- Orchestration des 27 modules essentiels
- Boucle principale de trading
- Gestion des positions
- Notifications Discord
- Protection VIX et Economic Calendar

---

### 📂 core/ (Modules Core)
```
core/
├── __init__.py                     # Exports du module
├── logger.py                       # Système de logging
├── session_quality_monitor.py      # Filtre sessions (London/US)
├── drawdown_monitor.py             # Surveillance drawdown
├── safety_kill_switch.py           # Arrêt d'urgence
├── trailing_stop_manager.py        # Gestion trailing stops
├── performance_profiler.py         # Profiling performance
├── execution_latency_tracker.py    # Tracking latence
├── lessons_learned_analyzer.py     # Analyse post-mortem
├── signal_explainer_ml_ready.py    # Explication signaux
├── decision_messenger_ml_ready.py  # Messages décisions
├── rejection_diagnostic_logger.py  # Diagnostic rejets
├── gamma_wall_protection.py        # Protection gamma walls
├── trading_types.py                # Types de trading
├── base_types.py                   # Types de base
├── battle_navale.py                # Analyse DOM
├── patterns_detector.py            # Détection patterns
├── sierra_order_router.py          # Routage ordres Sierra
├── structure_data.py               # Données structure
├── catastrophe_monitor.py          # Surveillance catastrophes
├── session_analyzer.py             # Analyse sessions
├── mentor_system.py                # Système mentor
├── menthorq_battle_navale.py       # MenthorQ + Battle Navale
├── menthorq_integration.py         # Intégration MenthorQ
├── menthorq_execution_rules.py     # Règles exécution
├── mia_unifier_stub.py             # Unifier MIA
├── fast_filters_first.py           # Filtres rapides
├── adaptive_thresholds.py          # Seuils adaptatifs
├── market_snapshot.py              # Snapshots marché
├── menthorq_cache.py               # Cache MenthorQ
├── battle_navale_cache.py          # Cache Battle Navale
├── vwap_band_calculator.py         # Calcul bandes VWAP
├── confluence_detector.py          # Détection confluences
└── market_context_analyzer.py      # Analyse contexte marché
```

---

### 📂 ml/ (Machine Learning 3-Layer)
```
ml/
├── __init__.py
├── ml_3layer_filter.py             # ⭐ FILTRE 3-LAYER PRINCIPAL
├── ml_3layer_integrated_system.py  # Système intégré
└── ml_mia_qscore.py                # Q-Score MIA
```

**Architecture 3-Layer:**
```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 1: MenthorQ (50%)                                     │
│ ├── Gamma Walls (10%)                                       │
│ ├── GEX Levels (10%)                                        │
│ ├── Blind Spots (8%)                                        │
│ ├── Next Wall (8%)                                          │
│ ├── Distances (8%)                                          │
│ └── Confluence (6%)                                         │
├─────────────────────────────────────────────────────────────┤
│ LAYER 2: OrderFlow (30%)                                    │
│ ├── Delta (12%)                                             │
│ ├── Volume (6%)                                             │
│ ├── DOM Imbalance (6%)                                      │
│ ├── Institutional Pressure (4%)                             │
│ └── Battle Navale (2%)                                      │
├─────────────────────────────────────────────────────────────┤
│ LAYER 3: Context (20%)                                      │
│ ├── VWAP Position (6%)                                      │
│ ├── Value Area (5%)                                         │
│ ├── Market Structure (5%)                                   │
│ └── Volatility (4%)                                         │
└─────────────────────────────────────────────────────────────┘
```

---

### 📂 strategies/ (Stratégies)
```
strategies/
├── __init__.py
├── menthorq_3layer_strategy.py     # ⭐ STRATÉGIE PRINCIPALE
├── strategy_manager_optimized_v3.py # Gestionnaire stratégies
└── bracket_detector_ml_ready.py    # Détecteur brackets
```

---

### 📂 execution/ (Exécution Ordres)
```
execution/
├── __init__.py
├── risk_manager.py                 # Gestion risques
├── sierra_dtc_connector.py         # ⭐ CONNECTEUR DTC SIERRA
├── post_mortem_analyzer.py         # Analyse post-mortem
├── trade_snapshotter_ml_ready.py   # ⭐ CAPTURE TRADES POUR ML
├── order_manager.py                # Gestion ordres
└── sierra_connector.py             # Connecteur Sierra
```

---

### 📂 monitoring/ (Discord & Alertes)
```
monitoring/
├── __init__.py
├── discord_notifier.py             # ⭐ NOTIFICATIONS DISCORD
├── discord_message_aggregator.py   # Agrégation messages
└── discord_styles.py               # Styles embeds Discord
```

---

### 📂 features/ (Calculateurs Features)
```
features/
├── __init__.py
├── ml_ready_reader.py              # ⭐ LECTEUR SNAPSHOTS ML
├── dom_health_analyzer.py          # Analyse santé DOM
├── feature_calculator_optimized.py # Calculateur features
├── confluence_analyzer.py          # Analyse confluences
├── market_regime.py                # Régime marché
├── vwap_bands_analyzer.py          # Analyse bandes VWAP
├── menthorq_integration.py         # Intégration MenthorQ
├── menthorq_dealers_bias.py        # Biais dealers
└── advanced/
    └── volatility_regime.py        # Régime volatilité
```

---

### 📂 config/ (Configurations)
```
config/
├── __init__.py
├── unified_thresholds.py           # ⭐ SEUILS UNIFIÉS (CRITIQUE)
├── loader_v2.py                    # Chargeur config v2
├── sierra_config.py                # Config Sierra
├── trading_config.py               # Config trading
└── constants.py                    # Constantes
```

**unified_thresholds.py - Seuils Critiques:**
```python
# Poids des Layers
LAYER_WEIGHTS = {
    "menthorq": 0.50,    # 50%
    "orderflow": 0.30,   # 30%
    "context": 0.20      # 20%
}

# Confidence minimale
MIN_TOTAL_CONFIDENCE = {
    'ES': 0.35,
    'NQ': 0.35,
    'RTY': 0.40
}
```

---

### 📂 utils/ (Utilitaires)
```
utils/
├── __init__.py
├── advanced_logging.py             # ⭐ LOGS AVANCÉS
├── enhanced_data_validator.py      # Validation données
├── economic_calendar.py            # ⭐ CALENDRIER ÉCONOMIQUE
└── data_validator.py               # Validation données
```

---

## 📊 DOSSIERS DE DONNÉES

### 📂 snapshots/ (1.17M fichiers)
```
snapshots/
└── [YYYYMMDD]/
    └── [SYMBOL]_[TIMESTAMP].json   # Snapshots ML du dumper G3
```
**Usage:** Données temps réel du dumper C++ pour ML

---

### 📂 snapshots_trades/ (226K fichiers)
```
snapshots_trades/
├── daily/                          # Snapshots journaliers
├── ml_ready/                       # Données prêtes pour ML
├── archive/                        # Archives
└── rejected_signals/               # ⭐ SIGNAUX REJETÉS (pour entraînement)
```
**Usage:** Capture de chaque trade/rejet pour analyse et entraînement ML

---

### 📂 logs_advanced/ (Logs Thématiques)
```
logs_advanced/
├── trades/                         # Logs trades
├── discord/                        # Logs Discord
├── signals/                        # Logs signaux
├── dtc/                            # Logs DTC/ordres
├── performance/                    # Logs performance
├── summaries/                      # Résumés quotidiens
└── json/                           # Events JSON
```

---

### 📂 DATA_SIERRA_CHART/ (Données Marché)
```
DATA_SIERRA_CHART/
└── DATA_2025/
    └── [MOIS]/
        └── [YYYYMMDD]/
            └── [SYMBOL]_ml_ready.jsonl
```
**Usage:** Données historiques pour backtest et analyse

---

## 🔧 DOSSIERS OUTILS

### 📂 extracteur/ (Dumper C++)
```
extracteur/
├── MIA_Dumper_G3_Unifier.cpp       # ⭐ DUMPER PRINCIPAL
├── MIA_Dumper_G3_Unifier.dll       # DLL compilée
└── PATCH_ADVANCED_METRICS_V1.md    # Documentation
```
**Usage:** DLL Sierra Chart pour extraire données en temps réel

---

## 🗄️ ARCHIVE

### 📂 ARCHIVE/ (Anciens Fichiers)
```
ARCHIVE/
├── docs_md/                        # 774 fichiers .md archivés
├── scripts_py/                     # 145 fichiers .py archivés
├── scripts_bat/                    # 64 fichiers .bat/.ps1 archivés
├── docs_txt/                       # Fichiers .txt archivés
├── backups_zip/                    # 12 fichiers .zip
├── data_json/                      # Fichiers .json archivés
└── old_folders/                    # 24 dossiers archivés
    ├── core_unused/
    ├── ml_unused/
    ├── strategies_unused/
    ├── execution_unused/
    ├── features_unused/
    ├── monitoring_unused/
    ├── config_unused/
    ├── utils_unused/
    └── launch_unused/
```

---

## 📋 FICHIERS CRITIQUES

| Fichier | Importance | Description |
|---------|------------|-------------|
| `LAUNCH/launch_production_CLEAN_v2.py` | ⭐⭐⭐ | Lanceur principal |
| `config/unified_thresholds.py` | ⭐⭐⭐ | Seuils ML (NE PAS MODIFIER) |
| `ml/ml_3layer_filter.py` | ⭐⭐⭐ | Cœur du système ML |
| `strategies/menthorq_3layer_strategy.py` | ⭐⭐⭐ | Stratégie principale |
| `execution/sierra_dtc_connector.py` | ⭐⭐⭐ | Connexion broker |
| `execution/trade_snapshotter_ml_ready.py` | ⭐⭐ | Capture pour ML |
| `utils/economic_calendar.py` | ⭐⭐ | Protection annonces |
| `core/session_quality_monitor.py` | ⭐⭐ | Filtre sessions |

---

## 🚀 COMMANDES DE LANCEMENT

### Lancer le Bot
```powershell
cd D:\MIA_IA_system
python LAUNCH/launch_production_CLEAN_v2.py
```

### Vérifier le Processus
```powershell
Get-Process python
```

### Arrêter le Bot
```powershell
Get-Process python | Stop-Process -Force
```

---

## 📊 STATISTIQUES

| Métrique | Valeur |
|----------|--------|
| Dossiers de production | 9 |
| Dossiers de données | 7 |
| Dossiers outils | 3 |
| Fichiers à la racine | 0 |
| Modules chargés | 27 + 1 bonus |
| Snapshots ML | 1,171,718 |
| Snapshots trades | 226,735 |

---

## 📝 NOTES

1. **NE PAS SUPPRIMER** les fichiers dans les dossiers Python - les `__init__.py` les importent tous
2. **BACKUP** fait le 29/11/2025 avant nettoyage
3. **ARCHIVE/** contient tous les anciens fichiers si besoin de récupérer
4. **unified_thresholds.py** = source unique des seuils ML

---

*Dernière mise à jour: 29 Novembre 2025*
*Version: CLEAN v2.0*
