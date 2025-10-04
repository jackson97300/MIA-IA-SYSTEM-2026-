# MIA_IA_system_mentor_q

Pipeline marché **Sierra-only** : **Sierra → Collector → Fichier unifié** + intégration **MenthorQ**.

## 🚀 Vue rapide

- **Entrée** : `chart_{3,4,8,10}_YYYYMMDD.jsonl` (écrits par `MIA_Chart_Dumper_patched.cpp`)
- **Collector** : `launchers/collector.py` (lit 3/4/8/10, unifie, feed MenthorQ)
- **Sortie** : `mia_unified_YYYYMMDD.jsonl` (un seul fichier/jour)
- **Signal** : Battle Navale + MenthorQ + régime VIX
- **Mode** : Sierra-only (plus d'IBKR/Polygon/DTC)

## 📊 Architecture

```
Sierra Chart (.cpp) → JSONL Files → SierraTail → UnifiedWriter → mia_unified_YYYYMMDD.jsonl
                                                      ↓
                                              MenthorQ Processor
                                                      ↓
                                              Battle Navale Analyzer
```

## 🛠️ Lancer

### Test rapide
```bash
python -m launchers.collector --charts 3,4,8,10 --once
python test_menthorq_integration.py
```

### Mode production
```bash
python launchers/launch_24_7.py
```

## 📁 Structure

- **`core/`** : Modules principaux (data_collector, menthorq_battle_navale)
- **`features/`** : Fonctionnalités (sierra_stream, unifier, menthorq_processor)
- **`config/`** : Configurations (sierra_paths, menthorq_runtime)
- **`launchers/`** : Lanceurs (launch_24_7.py, collector.py)
- **`DATASET/`** : 🤖 **Pipeline ML** (assemblage, entraînement, RL)
- **`ancien_system/`** : Systèmes legacy (archivés)

## 🔧 Données collectées

- **Graph 3 (1m)** : basedata, vwap, vva, vap, depth, trade, quote
- **Graph 4 (30m)** : basedata, vwap, pvwap
- **Graph 8 (VIX)** : vix + policy
- **Graph 10 (MenthorQ)** : gamma (SG1..19), blind spots (BL1..10), swings (SG1..9)

## 🤖 Pipeline ML

Le système inclut un **pipeline ML complet** dans `DATASET/` :

- **📊 Assemblage multi-sources** : OHLC, VWAP, NBCV, MenthorQ, DOM, VIX, ATR
- **🏷️ Labels ML** : Direction H=5min, Touch VWAP, Breakouts
- **🧠 Modèles** : XGBoost, LightGBM, CatBoost, PPO, SAC
- **🎛️ Policy Overlay** : Gating dynamique, hystérésis, sizing régimique
- **📈 Métriques** : Accuracy, F1, LogLoss, MCC, PR-AUC

**Documentation ML** : Voir `DATASET/README_ML_PIPELINE.md`

## 🧪 Tests CI

Les workflows GitHub exécutent `test_menthorq_integration.py` et génèrent un **Atlas** du repo.

## 📚 Documentation

- `ARCHITECTURE.md` : Architecture détaillée
- `AUDIT_LISTE_DETAILLEE_MODULES.md` : Liste complète des modules
- `RAPPORT_FINAL_MIGRATION_SIERRA.md` : Migration vers Sierra

## ⚠️ Sécurité

- **Repo privé** : Données de marché sensibles
- **Aucune donnée marché** versionnée (JSONL exclus)
- **Mode lecture seule** : Pas de trading automatique (par défaut)
- **Sierra-only** : Plus de dépendances externes (IBKR/Polygon)
- **Trading DTC** : Ports ES (11099), NQ (11100) via Sierra Chart