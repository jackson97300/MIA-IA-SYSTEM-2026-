# 📊 RAPPORT D'OPTIMISATION DES SEUILS MIA
## Analyse Multi-Jours + Backtest (Décembre 2025)

---

## 1. ÉCHANTILLON ANALYSÉ

| Période | Jours | Trades ML_3Layer |
|---------|-------|------------------|
| 04-17 Décembre 2025 | 9 jours | **202 trades** |

### Répartition
- **ES**: 115 trades (57%)
- **NQ**: 87 trades (43%)
- **LONG**: 99 trades (49%)
- **SHORT**: 103 trades (51%)

---

## 2. PERFORMANCE ACTUELLE (Sans optimisation)

| Métrique | Valeur |
|----------|--------|
| Win Rate | 45.5% |
| Profit Factor | 1.01 |
| P&L Total | $211 |
| Trades/jour | ~22 |

**Diagnostic**: Le bot prend trop de trades de mauvaise qualité.

---

## 3. CONFIGURATIONS TESTÉES

### 3.1 Résultats du Backtest

| Config | MQ≥ | OF≥ | CTX≥ | CONF≥ | WR | Trades | P&L | PF |
|--------|-----|-----|------|-------|-----|--------|------|-----|
| ACTUEL | 0 | 0 | 0 | 0.35 | 45.5% | 202 | $211 | 1.01 |
| **MODERE** ⭐ | 0.58 | 0.22 | 0.16 | 0.96 | **48.8%** | 82 | **$4,270** | **1.43** |
| ORDERFLOW | 0 | 0.22 | 0 | 0.35 | 48.2% | 137 | $3,586 | 1.23 |
| BALANCED | 0.55 | 0.20 | 0.16 | 0.95 | 46.3% | 108 | $3,881 | 1.32 |
| CONFLUENCE | 0 | 0 | 0 | 1.00 | 45.8% | 155 | $1,100 | 1.06 |
| AGRESSIF | 0.62 | 0.24 | 0.18 | 1.05 | 43.3% | 30 | -$1,785 | 0.69 |

### 3.2 Validation Croisée K-Fold (5 folds)

| Config | WR Moyen K-Fold | P&L Total |
|--------|-----------------|-----------|
| ACTUEL | 45.5% | $124 |
| **MODERE** ⭐ | **51.5%** | **$4,183** |
| ORDERFLOW | 49.7% | $3,498 |
| BALANCED | 47.6% | $3,793 |

---

## 4. ANALYSE TENDANCE vs CONTRE-TENDANCE

| Alignement | Trades | Win Rate |
|------------|--------|----------|
| AVEC_TENDANCE | 36 | 41.7% |
| CONTRE_TENDANCE | 8 | 50.0% |
| NEUTRE | 158 | 46.2% |

**Observation**: L'alignement tendance n'est pas un facteur discriminant sur cet échantillon.

---

## 5. PROBLÈMES IDENTIFIÉS

### Trades Perdants avec:
- **OrderFlow < 0.20**: 28.2% des losses
- **Context < 0.16**: 10.9% des losses
- **Confluence < 1.00**: 23.6% des losses

### Par Symbole (avec BALANCED):
- **ES**: WR 46.4%, P&L -$1,042 ⚠️
- **NQ**: WR 46.2%, P&L +$4,923 ✅

---

## 6. RECOMMANDATION FINALE

### 🏆 Configuration MODERE (Recommandée)

```python
# unified_thresholds.py

MIN_LAYER_THRESHOLDS = {
    'ES': {
        'menthorq_min': 0.58,
        'orderflow_min': 0.22,
        'context_min': 0.16,
    },
    'NQ': {
        'menthorq_min': 0.58,
        'orderflow_min': 0.22,
        'context_min': 0.16,
    },
}

MIN_CONFLUENCE_TOTAL = 0.96
```

### Impact Attendu

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Win Rate | 45.5% | 48.8% | **+3.3%** |
| Profit Factor | 1.01 | 1.43 | **+41%** |
| P&L (9 jours) | $211 | $4,270 | **+$4,059** |
| Trades/jour | ~22 | ~9 | -59% |

---

## 7. ALTERNATIVES

### Option 2: ORDERFLOW_ONLY (Plus de volume)

```python
# Si tu veux plus de trades avec un bon compromis
MIN_ORDERFLOW = 0.22  # Seul seuil ajouté
MIN_CONFLUENCE = 0.35  # Inchangé
```

**Impact**: WR 48.2%, 137 trades, P&L $3,586

### Option 3: BALANCED (Compromis)

```python
MIN_LAYER_THRESHOLDS = {
    'menthorq_min': 0.55,
    'orderflow_min': 0.20,
    'context_min': 0.16,
}
MIN_CONFLUENCE = 0.95
```

**Impact**: WR 46.3%, 108 trades, P&L $3,881

---

## 8. PROCHAINES ÉTAPES

1. ✅ **Backtest validé** sur 202 trades (9 jours)
2. ⏳ **Appliquer les seuils MODERE** en production
3. ⏳ **Monitorer** pendant 1 semaine
4. ⏳ **Ajuster** si nécessaire

---

## 9. AVERTISSEMENTS

⚠️ **Taille d'échantillon**: 202 trades est un échantillon décent mais pas énorme. Prévoir une période de test de 1-2 semaines en production.

⚠️ **Réduction du volume**: Les seuils MODERE réduisent le volume de 59%. S'assurer que c'est acceptable.

⚠️ **Performance ES faible**: Considérer des seuils différenciés ES/NQ si le pattern persiste.

---

*Rapport généré le 18 Décembre 2025*
*Basé sur 202 trades ML_3Layer analysés sur 9 jours*

