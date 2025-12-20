# 🎯 BACKTEST MENTHORQ - Système Complet

Système de backtest exhaustif pour la méthode MenthorQ qui teste:
- **80+ niveaux techniques** (GEX, Blind Spots, VWAP, IB, etc.)
- **Multiple configurations SL/TP**
- **Toutes les heures de trading**
- **Différents seuils de confiance**
- **Différentes confluence strengths**

## 📁 Structure

```
backtesting/
├── __init__.py
├── menthorq_backtester.py      # Moteur principal
├── backtest_analyzer.py         # Analyseur de résultats
├── backtest_reporter.py         # Générateur de rapports
├── run_backtest.py              # Script de lancement
├── config/
│   └── backtest_config.yaml     # Configuration
└── results/                     # Résultats générés
    ├── EXECUTIVE_SUMMARY.md
    ├── DETAILED_REPORT.md
    ├── backtest_data.json
    └── backtest_results.xlsx
```

## 🚀 Utilisation

### 1. Configuration

Modifier `config/backtest_config.yaml` :

```yaml
symbols:
  - ES
  - NQ

date_range:
  start: '2025-11-05'
  end: '2025-11-21'

data_path: 'DATA_SIERRA_CHART/DATA_2025/NOVEMBRE'
```

### 2. Lancement

```bash
cd backtesting
python run_backtest.py
```

### 3. Résultats

Les résultats sont générés dans `results/` :

- **EXECUTIVE_SUMMARY.md** : Résumé exécutif (2 pages)
- **DETAILED_REPORT.md** : Rapport complet
- **backtest_data.json** : Données brutes
- **backtest_results.xlsx** : Tables Excel détaillées

## 📊 Questions Répondues

Le système répond à **7 questions clés** :

1. ✅ **Quels niveaux sont les plus pertinents?**
   → Top 10 niveaux par win rate et P&L

2. ✅ **Quels SL/TP sont les plus performants?**
   → Meilleure config par symbole

3. ✅ **Quelles heures de trading sont les plus profitables?**
   → Heatmap hourly performance

4. ✅ **Quels moments éviter de trader?**
   → Liste précise avec raisons

5. ✅ **Quels seuils de confiance sont optimaux?**
   → Seuils Layer 1/2/3 par symbole

6. ✅ **Quelle confluence strength minimale?**
   → Strength recommandée (2, 3, 4, 5 niveaux)

7. ✅ **Quel contexte marché favorable?**
   → VIX range, volume, HVL position, etc.

## ⚙️ Dépendances

```bash
pip install pandas numpy pyyaml openpyxl
```

## 📝 Notes

- Utilise les snapshots ML_READY existants
- Teste toutes les combinaisons SL/TP
- Génère statistiques complètes
- Export multiple formats

## 🎯 Objectif

Pouvoir dire avec **CERTITUDE et DATA** :

✅ "GEX_3 + Blind Spot 2 + VWAP = 68% win rate"
✅ "SL 25t + TP R:R 1.8:1 = meilleure config NQ"
✅ "Trade entre 10h-11h30 et 14h-15h30 ET uniquement"
✅ "ÉVITER 9h30-10h (win rate 32%) et 15h45-16h (volatilité)"

---

**Date**: 23 Novembre 2025
**Version**: 1.0
