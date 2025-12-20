# 📊 BACKTESTS - MIA IA Trading System

## 🎯 Architecture

Cette architecture centralise tous les backtests du projet pour garantir:
- ✅ **Reproductibilité** - Chaque backtest peut être relancé
- ✅ **Traçabilité** - Historique complet des tests
- ✅ **Comparabilité** - Même config = mêmes résultats
- ✅ **Documentation** - Chaque test a son README

---

## 📁 Structure

```
BACKTESTS/
├── README.md                          # Ce fichier
├── config/
│   └── backtest_config.py             # ⚙️ Configuration partagée
│
├── templates/
│   └── template_backtest.py           # 📝 Template réutilisable
│
├── YYYY-MM-DD_nom_test/               # 📂 Un dossier par backtest
│   ├── README.md                      # Résumé du backtest
│   ├── backtest.py                    # Script principal
│   ├── results.json                   # Résultats JSON (optionnel)
│   └── output.txt                     # Output console (optionnel)
│
└── ...
```

---

## 🆕 Créer un nouveau backtest

### 1. Créer le dossier

Nommer le dossier: `YYYY-MM-DD_description_courte`

Exemples:
- `2025-12-06_pressure_strength`
- `2025-12-10_nouveau_seuil_layer1`
- `2025-12-15_comparaison_tp_sl`

### 2. Copier le template

```powershell
cd D:\MIA_IA_system\BACKTESTS
Copy-Item templates\template_backtest.py 2025-12-XX_mon_test\backtest.py
```

### 3. Configurer le backtest

Dans `backtest.py`, modifier:
- `TEST_NAME` - Nom du test
- `TEST_DESCRIPTION` - Description
- `DATE_RANGE` - Période à tester
- `CUSTOM_PARAMS` - Paramètres à tester

### 4. Exécuter (2 étapes obligatoires)

```powershell
cd D:\MIA_IA_system

# ÉTAPE 1: Test sur échantillon (validation rapide)
python BACKTESTS\2025-12-XX_mon_test\backtest.py

# ÉTAPE 2: Si le test est OK → Backtest complet
python BACKTESTS\2025-12-XX_mon_test\backtest.py --full
```

⚠️ **TOUJOURS tester sur échantillon d'abord !** Le mode test utilise 5000 snapshots pour valider que tout fonctionne avant de lancer sur les millions de données.

### 5. Documenter les résultats

Créer un `README.md` dans le dossier avec:
- Objectif du test
- Paramètres testés
- Résultats clés
- Décision (APPLIQUER / REJETER)

---

## 🎮 Modes de Lancement

| Commande | Mode | Description |
|----------|------|-------------|
| `python backtest.py` | 🧪 TEST | Échantillon 5000 snaps, validation rapide |
| `python backtest.py --full` | 📊 COMPLET | Toutes les données, résultats définitifs |
| `python backtest.py --no-progress` | Silencieux | Sans barre de progression |

### Workflow Recommandé (4 étapes)

```
┌─────────────────┐     ✅ OK     ┌─────────────────┐
│  🧪 MODE TEST   │ ──────────► │  📊 MODE FULL   │
│  (30 secondes)  │              │  (5-10 minutes) │
└─────────────────┘              └─────────────────┘
        │                                │
        │ ❌ Erreur                       │ Résultats
        ▼                                ▼
┌─────────────────┐              ┌─────────────────┐
│   🔧 DEBUG      │              │  📋 RAPPORT     │
│  Corriger code  │              │  Créer README   │
└─────────────────┘              └─────────────────┘
                                         │
                                         ▼
                                 ┌─────────────────┐
                                 │  👤 VALIDATION  │
                                 │   MANUELLE !    │
                                 │  (toi qui décide│
                                 └─────────────────┘
                                         │
                          ✅ Approuvé    │    ❌ Rejeté
                                ┌────────┴────────┐
                                ▼                 ▼
                        ┌───────────────┐  ┌───────────────┐
                        │ 🚀 IMPLÉMENTER│  │ 📁 ARCHIVER   │
                        │  (manuellement)│  │  (garder trace)│
                        └───────────────┘  └───────────────┘
```

⚠️ **IMPORTANT:** L'implémentation en production est TOUJOURS manuelle après ta validation !

---

## 📊 Barre de Progression

Le template inclut une barre de progression (tqdm) qui affiche:
- Avancement en temps réel
- Nombre de trades trouvés
- P&L courant
- Temps estimé restant

```
🔄 BASELINE |████████████████░░░░░░░░░░░░░░░░░░░░░░░░| 45,000/144,817 [32s<45s] trades=12, wins=4, pnl=$375
```

---

## ⚙️ Configuration Partagée

Le fichier `config/backtest_config.py` contient:

| Section | Description |
|---------|-------------|
| `SYMBOLS` | Symboles à tester (ES, NQ, RTY) |
| `SESSIONS` | Horaires des sessions |
| `ML_THRESHOLDS` | Seuils ML de production |
| `TP_SL_CONFIG` | Configuration TP/SL |
| `DATA_PATHS` | Chemins des données |

**⚠️ Important:** Ces valeurs doivent correspondre EXACTEMENT à `unified_thresholds.py`

---

## 📋 Checklist Backtest Valide

Avant de valider un backtest:

- [ ] **Période suffisante** - Minimum 5 jours de données
- [ ] **Sessions correctes** - London, US Morning, Power Hour uniquement
- [ ] **Filtres production** - Tous les filtres actifs (ML, distance, cooldown)
- [ ] **Simulation réaliste** - TP/SL avec prix réels (high/low)
- [ ] **Comparaison** - Test avec ET sans le changement
- [ ] **Résultats documentés** - README avec décision

---

## 📊 Historique des Backtests

| Date | Test | Résultat | Statut |
|------|------|----------|--------|
| 2025-12-06 | pressure_strength par session | +$1,125/semaine, +1.4% WR | ✅ VALIDÉ & APPLIQUÉ |

### Statuts possibles

| Statut | Description |
|--------|-------------|
| 🧪 EN TEST | Backtest en cours |
| 📋 EN ATTENTE | Résultats prêts, en attente de ta validation |
| ✅ VALIDÉ | Approuvé par toi, prêt à implémenter |
| ✅ APPLIQUÉ | Implémenté en production |
| ❌ REJETÉ | Refusé après analyse des résultats |
| 📁 ARCHIVÉ | Conservé pour référence future |

---

## 🔧 Commandes Utiles

```powershell
# Lister tous les backtests
Get-ChildItem D:\MIA_IA_system\BACKTESTS -Directory

# Lancer un backtest
python BACKTESTS\2025-12-XX_test\backtest.py

# Voir les résultats récents
Get-ChildItem D:\MIA_IA_system\BACKTESTS -Recurse -Filter "results.json" | Sort-Object LastWriteTime -Descending | Select-Object -First 5
```

---

## ⚠️ Règles Importantes

1. **Ne jamais modifier les backtests passés** - Créer un nouveau dossier
2. **Toujours comparer AVEC et SANS** le changement proposé
3. **Documenter les échecs aussi** - Ils sont utiles pour éviter les erreurs
4. **Utiliser la config partagée** - Évite les divergences avec la production
