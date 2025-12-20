# 📚 INDEX DOCUMENTATION - MIA TRADING SYSTEM

**Dernière mise à jour:** 30 Novembre 2025

---

## 🚀 DÉMARRAGE RAPIDE

| Document | Description | Emplacement |
|----------|-------------|-------------|
| **`.cursorrules`** | Instructions projet pour Claude/Cursor | Racine |
| **`RESUME_RAPIDE_30NOV.md`** | Résumé 1 page de la session | `CLAUDE/` |
| **`docs/README.md`** | Guide démarrage rapide | `docs/` |

---

## 📖 GUIDES TECHNIQUES

### Architecture & Stratégie
| Document | Contenu | Lignes |
|----------|---------|--------|
| `docs/MENTHORQ_GUIDE.md` | MenthorQ, Gamma Walls, GEX, Blind Spots | 450 |
| `docs/OPTIONS_FLOW_GUIDE.md` | Options flow, dealer hedging, gamma flip | 380 |
| `docs/ORDERFLOW_GUIDE.md` | Order Flow, Delta, DOM, Battle Navale | 420 |
| `docs/TRADING_RULES.md` | Règles strictes entry/exit/risk | 350 |
| `docs/SNAPSHOT_REFERENCE.md` | Structure complète snapshot JSON | 500 |

### Structure Projet
| Document | Contenu |
|----------|---------|
| `docs/STRUCTURE_PROJET_MIA.md` | Architecture complète du projet |
| `docs/BACKTESTS_HISTORIQUE.md` | Historique backtests et problèmes résolus |

---

## ⚡ OPTIMISATIONS & PERFORMANCE

| Document | Description | Date |
|----------|-------------|------|
| `GUIDE_OPTIMISATION_LATENCE.md` | Guide complet optimisations (-35ms) | 30 Nov 2025 |
| `SESSION_30NOV_OPTIMISATIONS_COMPLETE.md` | Rapport complet session optimisations | 30 Nov 2025 |
| `SESSION_COMPLETE_OPTIMISATIONS.md` | Récap Quick Wins (TODO 1-4) | 30 Nov 2025 |

### Quick Wins Détaillés
| TODO | Document | Gain |
|------|----------|------|
| TODO 1 | `TODO_1_COMPLETE_VALIDATOR.md` | Sécurité |
| TODO 2 | `TODO_2_COMPLETE_PARALLEL.md` | -20ms |
| TODO 3 | `TODO_3_COMPLETE_CACHE.md` | -10ms |
| TODO 4 | `TODO_4_COMPLETE_BOUCLES.md` | -5ms |

---

## 🧪 TESTS & QUALITÉ

| Document | Description | Tests |
|----------|-------------|-------|
| `tests/README.md` | Guide des tests unitaires/intégration | 39 |
| `TESTS_PYTEST_RESULTATS.md` | Résultats initiaux pytest | - |
| `SESSION_FINALE_COMPLETE.md` | Synthèse complète tests + optimisations | - |

### Suites de Tests
| Fichier | Couverture | Lignes |
|---------|-----------|--------|
| `tests/unit/test_risk_manager.py` | RiskManager | 205 |
| `tests/unit/test_session_quality.py` | SessionQualityMonitor | 172 |
| `tests/unit/test_ml_filter.py` | ML3LayerFilter | 184 |
| `tests/integration/test_pipeline.py` | Pipeline complète | 163 |

---

## 🔍 AUDITS & ANALYSES

### Audits Système
| Document | Description | Score |
|----------|-------------|-------|
| `AUDIT_CODE_PRO_TON_SYSTEME.md` | Audit 15 dimensions PRO vs AMATEUR | 7.3/10 |
| `PLAN_ACTION_AMELIORATION.md` | Roadmap améliorations (3 phases) | - |
| `RAPPORT_AUDIT_VALIDATIONS_COMPLETES.md` | Audit 8 validations actives | - |
| `docs/AUDIT_PIPELINE_COMPLETE.md` | Audit complet pipeline + corrections | 327 lignes |

### Analyses Techniques
| Document | Sujet |
|----------|-------|
| `MARKET_VS_LIMIT_ANALYSE_CRITIQUE.md` | Market vs Limit Orders (momentum) |
| `CONSENSUS_MARKET_ORDERS.md` | Validation Market Orders optimal |

---

## 📊 BACKTESTS & RÉSULTATS

| Document | Contenu |
|----------|---------|
| `docs/BACKTESTS_HISTORIQUE.md` | Historique problèmes over-engineering |
| Backtests ES | 83.8% WR (backtest validé) |
| Backtests NQ | 81.9% WR (backtest validé) |

---

## 🔧 CONFIGURATION & SETUP

### Fichiers Critiques
| Fichier | Ne PAS Modifier Sans Raison |
|---------|----------------------------|
| `config/unified_thresholds.py` | Seuils ML calibrés |
| `ml/ml_3layer_filter.py` | Logique ML 3-Layer |
| `LAUNCH/launch_production_CLEAN_v2.py` | Lanceur principal |

### Environnement
- Python 3.11+
- Sierra Chart (DTC Protocol port 11099)
- Discord Webhooks
- Investing.com (economic calendar)

---

## 📝 LOGS & DÉCISIONS

### Sessions Complètes
| Date | Document | Statut |
|------|----------|--------|
| 30 Nov 2025 | `SESSION_30NOV_OPTIMISATIONS_COMPLETE.md` | ✅ Production |
| 30 Nov 2025 | `SESSION_FINALE_COMPLETE.md` | ✅ Tests validés |

### Décisions Importantes
| Document | Décision |
|----------|----------|
| `DECISION_TESTS_VS_LANCEMENT.md` | Lancer système avant fix tests |
| `DECISION_FINALE_TODO10.md` | Validation priorité lancement |

---

## 🎯 MÉTRIQUES SYSTÈME

### Performance
- **Latence cycle:** 89ms (objectif < 100ms) ✅
- **Throughput:** 11 cycles/seconde ✅
- **Tests:** 39/39 passés (100%) ✅

### Trading
- **Win Rate ES:** 83.8% (backtest)
- **Win Rate NQ:** 81.9% (backtest)
- **Max trades/jour:** 10-15
- **Sessions actives:** 5h40/jour

### Qualité Code
- **Score audit:** 7.3/10 (Semi-Pro+)
- **Modules:** 27/27 opérationnels
- **Documentation:** 25+ documents

---

## 🚀 COMMANDES ESSENTIELLES

```bash
# Lancer le bot
cd D:\MIA_IA_system
python LAUNCH/launch_production_CLEAN_v2.py

# Tests
pytest tests/ -v

# Vérifier processus
Get-Process python

# Arrêter le bot
Get-Process python | Stop-Process -Force

# Voir logs
Get-Content logs_advanced\trades\*.json -Tail 50
```

---

## 📂 STRUCTURE DOCUMENTATION

```
MIA_IA_system/
├── .cursorrules                    # ⭐ Instructions projet
├── CLAUDE/                         # Documentation sessions
│   ├── RESUME_RAPIDE_30NOV.md      # ⭐ Résumé 1 page
│   ├── SESSION_30NOV_*.md          # Sessions détaillées
│   ├── TODO_*_COMPLETE.md          # TODOs complétés
│   ├── GUIDE_OPTIMISATION_*.md     # Guides techniques
│   ├── AUDIT_*.md                  # Audits système
│   └── *_ANALYSE_*.md              # Analyses techniques
│
├── docs/                           # Documentation technique
│   ├── README.md                   # Guide démarrage rapide
│   ├── STRUCTURE_PROJET_MIA.md     # Architecture projet
│   ├── MENTHORQ_GUIDE.md           # Guide MenthorQ
│   ├── OPTIONS_FLOW_GUIDE.md       # Guide Options Flow
│   ├── ORDERFLOW_GUIDE.md          # Guide Order Flow
│   ├── TRADING_RULES.md            # Règles trading
│   ├── SNAPSHOT_REFERENCE.md       # Référence snapshot
│   ├── BACKTESTS_HISTORIQUE.md     # Historique backtests
│   └── AUDIT_PIPELINE_COMPLETE.md  # Audit pipeline
│
└── tests/                          # Tests automatisés
    ├── README.md                   # Guide des tests
    ├── unit/                       # Tests unitaires (3 suites)
    └── integration/                # Tests intégration (1 suite)
```

---

## 🔍 RECHERCHE RAPIDE

### Par Sujet

**ML & Trading:**
- ML 3-Layer → `.cursorrules` (lignes 78-103)
- MenthorQ → `docs/MENTHORQ_GUIDE.md`
- OrderFlow → `docs/ORDERFLOW_GUIDE.md`

**Performance:**
- Optimisations → `CLAUDE/GUIDE_OPTIMISATION_LATENCE.md`
- Latence → `CLAUDE/SESSION_30NOV_OPTIMISATIONS_COMPLETE.md`

**Tests:**
- Guide tests → `tests/README.md`
- Résultats → `CLAUDE/SESSION_FINALE_COMPLETE.md`

**Configuration:**
- Seuils ML → `config/unified_thresholds.py`
- Sessions → `.cursorrules` (lignes 115-122)
- VIX → `.cursorrules` (lignes 127-132)

---

## 📞 SUPPORT & MAINTENANCE

### En Cas de Problème

1. **Bot ne démarre pas:**
   - Vérifier logs: `logs_advanced/system_*.log`
   - Vérifier DTC: Sierra Chart connecté?
   - Guide: `docs/README.md`

2. **Tests échouent:**
   - Voir: `tests/README.md`
   - Comparer: `CLAUDE/TESTS_PYTEST_RESULTATS.md`

3. **Performance dégradée:**
   - Mesurer latence actuelle
   - Comparer baseline: 89ms
   - Guide: `CLAUDE/GUIDE_OPTIMISATION_LATENCE.md`

4. **Pas de trades:**
   - Vérifier session: `SessionQualityMonitor`
   - Vérifier VIX: doit être < 25
   - Vérifier Economic Calendar
   - Voir: `docs/BACKTESTS_HISTORIQUE.md`

---

## 🎯 PROCHAINES ÉTAPES

1. **Court terme** (1 semaine)
   - Surveiller latence production
   - Collecter métriques réelles
   - Monitorer fill rate

2. **Moyen terme** (1 mois)
   - Docker containerization
   - CI/CD pipeline
   - Monitoring Grafana

3. **Long terme** (3 mois)
   - Scalabilité horizontale
   - ML models entraînés
   - Optimisations avancées

---

**Dernière mise à jour:** 30 Novembre 2025
**Version:** MIA Trading System CLEAN V2.0
**Statut:** ✅ EN PRODUCTION
