# 🔍 AUDIT COMPLET REJETS NQ - 11 DÉCEMBRE 2025

## 📊 STATISTIQUES GLOBALES

| Métrique | Valeur |
|----------|--------|
| **Rejets totaux NQ** | 1518 |
| **Rejets totaux ES** | 5555 |
| **Trades NQ exécutés** | 3 (tous SHORT) |
| **Trades ES exécutés** | 5 (tous SHORT) |

---

## 🔴 PROBLÈME PRINCIPAL IDENTIFIÉ

### 100% des rejets NQ étaient des signaux LONG

| Direction | Rejetés | Exécutés |
|-----------|---------|----------|
| **LONG** | 1518 (100%) | 0 |
| **SHORT** | 0 (0%) | 3 |

**Conclusion:** Le système a rejeté TOUS les signaux LONG sur NQ, même ceux avec confiance >1.0

---

## 📈 DISTRIBUTION DES CATÉGORIES DE REJET NQ

| Catégorie | Nombre | % |
|-----------|--------|---|
| **DUAL_MODE_TREND** | 1079 | 71% |
| **DUAL_MODE_RANGE** | 392 | 26% |
| **INTRADAY_BRACKET_MIDDLE** | 47 | 3% |

---

## 🎯 ANALYSE PAR CATÉGORIE

### 1. DUAL_MODE_TREND (1079 rejets - 71%)

**Raison:** "LONG contre bias BEARISH"

Le système détecte un **biais bearish** (score entre -0.40 et -0.90) et refuse tous les signaux LONG, même avec haute confiance.

**Exemples concrets:**
```
TREND: LONG contre bias BEARISH (-0.87): 79 fois
TREND: LONG contre bias BEARISH (-0.83): 72 fois
TREND: LONG contre bias BEARISH (-0.85): 67 fois
TREND: LONG contre bias BEARISH (-0.88): 66 fois
TREND: LONG contre bias BEARISH (-0.89): 57 fois
```

**Problème:** Le bias reste BEARISH trop longtemps, même quand le prix fait des rebonds significatifs.

### 2. DUAL_MODE_RANGE (392 rejets - 26%)

**Raison:** Range hors des limites acceptées

**Exemples:**
```
RANGE: Range invalide (409t, requis: 15-60): 208 fois
RANGE: Range invalide (1018t, requis: 15-60): 180 fois
```

**Problème:** Le range NQ (409 ticks = $204.50, ou 1018 ticks = $509) dépasse largement la limite de 60 ticks ($30).

**💡 Note:** Ces seuils sont configurés pour ES (12-50 ticks = $150-625), pas pour NQ où les mouvements sont plus amples!

### 3. INTRADAY_BRACKET_MIDDLE (47 rejets - 3%)

**Raison:** "BAS du range mais bias BEARISH" ou "MILIEU du bracket"

Le système refuse les entrées en zone neutre (30-70% du range intraday).

---

## ⏰ DISTRIBUTION PAR HEURE (UTC)

| Heure | Rejets | Session |
|-------|--------|---------|
| 04h | 436 | Asia/London |
| 07h | 156 | London |
| 08h | 182 | London |
| 16h | 128 | **US Afternoon** |
| 11h | 104 | Lunch |
| 00h | 62 | Night |

**Observation:** Beaucoup de rejets pendant les heures de trading actives.

---

## 🔥 SIGNAUX NQ À HAUTE CONFIANCE REJETÉS

**1334 signaux NQ avec confiance ≥ 0.9 ont été rejetés !**

Parmi eux, **1016 signaux avec confiance ≥ 1.0** (très haute qualité) ont été bloqués.

### Exemples de signaux perdus:
```
00:39:39 | LONG | Conf: 1.06 | Rejeté: TREND contre bias BEARISH
00:46:55 | LONG | Conf: 1.07 | Rejeté: TREND contre bias BEARISH
14:XX:XX | LONG | Conf: 1.21 | Rejeté: TREND contre bias BEARISH
```

---

## 🆚 COMPARAISON NQ vs ES

| Aspect | NQ | ES |
|--------|----|----|
| Rejets total | 1518 | 5555 |
| % DUAL_MODE_TREND | 71% | 60% |
| % DUAL_MODE_RANGE | 26% | 31% |
| Trades exécutés | 3 | 5 |
| Ratio rejet/trade | 506:1 | 1111:1 |

ES a un ratio encore pire, mais ES a quand même exécuté plus de trades.

---

## 🚨 PROBLÈMES IDENTIFIÉS

### 1. Biais BEARISH Persistant
Le `mia_bullish_score` reste négatif trop longtemps après un mouvement baissier, bloquant les rebonds.

**Score typique observé:** -0.40 à -0.90 (fortement bearish)

### 2. Seuils de Range Non Adaptés à NQ
- ES: 12-50 ticks acceptable
- NQ: 15-60 ticks configuré mais NQ bouge souvent 400-1000 ticks!

**NQ tick = $5 vs ES tick = $12.50** → Les seuils doivent être multipliés par ~2.5 pour NQ

### 3. Mode "Trend Only" Trop Restrictif
Le système en mode DUAL_MODE refuse les contre-tendance, même quand:
- La confiance ML est très haute (>1.0)
- Le prix touche un support majeur
- L'OrderFlow montre un retournement

---

## 💡 RECOMMANDATIONS

### Court Terme (Urgent)

1. **Ajuster les seuils de Range pour NQ**
   ```python
   # Actuel
   NQ: range_min=15, range_max=60

   # Recommandé
   NQ: range_min=30, range_max=150  # Adapté à la volatilité NQ
   ```

2. **Réduire le seuil bearish pour bloquer LONG**
   ```python
   # Actuel: bloque LONG si bias < -0.25
   # Recommandé: bloque LONG si bias < -0.50
   ```

### Moyen Terme

3. **Implémenter un "Override Confluence Majeure"**
   - Si confiance >1.2 ET support MenthorQ proche → autoriser contre-tendance

4. **Accélérer la détection de retournement**
   - Fenêtre de calcul du bias: 30min → 10min
   - Poids accru sur le momentum récent

### Long Terme

5. **Séparer complètement la config NQ vs ES**
   - NQ est 2-3x plus volatile
   - Tous les seuils doivent être adaptés

---

## 📝 CONCLUSION

Le système est **trop conservateur sur NQ** avec un taux de rejet de **506:1** (506 rejets pour 1 trade).

Les 3 trades NQ exécutés étaient SHORT car c'était la seule direction alignée avec le bias persistant.

**Priorité #1:** Adapter les seuils pour NQ (range, bias threshold)
**Priorité #2:** Permettre des contre-tendance à haute confiance

---

*Audit généré le 11 décembre 2025*














