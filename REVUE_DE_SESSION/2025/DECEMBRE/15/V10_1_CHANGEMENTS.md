# 🔧 V10.1 - STRATÉGIE HYBRIDE
## Date: 16 Décembre 2025

---

## ✅ CHANGEMENTS APPLIQUÉS

### 1. Layer 3: 0.20 → 0.12 (TOUTES LES SESSIONS)

```python
# AVANT (V9)
'layer3': 0.20  # Bloquait ~30% des bons trades

# APRÈS (V10.1)
'layer3': 0.12  # Permet plus de trades tout en filtrant les mauvais
```

**Fichier modifié:** `config/trading_params.py`

**Impact attendu:**
- Plus de trades acceptés (L3 était trop strict)
- Backtest montrait L3=0.10-0.12 optimal pour toutes sessions

### 2. LONDON_NQ: Déjà désactivé ✅

```python
'LONDON_NQ': {
    'enabled': False,  # Déjà désactivé dans V9
}
```

---

## 📊 RÉSULTATS BACKTEST V10 (RAPPEL)

### Validation Out-of-Sample (6 jours incluant 15/12)

| Session | V10 | ML seul | V9 | **Meilleur** |
|---------|-----|---------|-----|--------------|
| LONDON_ES | $225 | $68 | **$2,194** | V9 |
| LONDON_NQ | $25 | -$545 | -$360 | ❌ Désactivé |
| US_MORNING_ES | -$450 | **$300** | -$150 | ML seul |
| US_MORNING_NQ | **$625** | $500 | $200 | V10 |
| POWER_HOUR_ES | **$1,025** | $600 | $600 | V10 |
| POWER_HOUR_NQ | $100 | **$930** | $825 | ML seul |

### Totaux

| Config | P&L Total |
|--------|-----------|
| V9 | **$3,309** |
| ML seul | $1,853 |
| V10 | $1,550 |

---

## 🎯 POURQUOI V10.1 (HYBRIDE) ?

1. **V9 reste la base** - Meilleur en validation globale
2. **Un seul changement** - Layer 3 de 0.20 → 0.12
3. **Facile à évaluer** - Si ça ne marche pas, on revient à 0.20
4. **Layer 3 était le bloqueur** - 0.20 rejetait des trades valides

---

## 📋 PLAN DE TEST

### Semaine 1 (16-20 Décembre)
- [ ] Observer nombre de trades vs semaine précédente
- [ ] Comparer WinRate
- [ ] Noter les rejets L3 (doivent diminuer)

### Critères de succès
- ✅ Plus de trades (mais pas trop)
- ✅ WinRate stable ou meilleur
- ✅ P&L positif

### Si échec
- Revenir à `layer3: 0.20`
- Envisager désactiver filtres MenthorQ pour certaines sessions

---

## 📝 COMMANDE POUR VÉRIFIER

```powershell
# Voir la config active
python -c "from config.trading_params import MIN_LAYER_CONFIDENCE; print(MIN_LAYER_CONFIDENCE)"
```

Résultat attendu:
```python
{'ES': {'layer1': 0.3, 'layer2': 0.17, 'layer3': 0.12}, ...}
```

---

## 🚀 PROCHAINE ÉTAPE

1. **Relancer le bot** avec la nouvelle config
2. **Observer** la session London (08:00-11:00)
3. **Comparer** le nombre de trades avec hier (15/12)

---

*Document généré automatiquement le 16/12/2025*
