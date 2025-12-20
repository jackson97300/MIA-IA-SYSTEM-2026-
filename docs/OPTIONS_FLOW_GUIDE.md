# 📈 GUIDE OPTIONS FLOW - Comprendre le Flux Options

## Introduction

Le marché des options influence directement le marché des futures.
Les dealers (market makers) doivent constamment hedger leurs positions options,
ce qui crée des mouvements prévisibles sur les futures.

---

## 🎓 Concepts Fondamentaux

### 1. Delta Hedging des Dealers

**Principe:**
- Quand un client achète un CALL, le dealer est SHORT gamma
- Pour rester neutre, le dealer doit ACHETER le sous-jacent
- L'inverse pour les PUTS

**Conséquence:**
- Les gros strikes options créent des "zones magnétiques"
- Le prix est "attiré" vers ces niveaux

### 2. Gamma Exposure (GEX)

**Définition:** Mesure de combien les dealers doivent hedger pour chaque mouvement de $1.

**GEX Positif:**
- Dealers sont LONG gamma
- Ils vendent quand ça monte, achètent quand ça baisse
- → Compression de la volatilité
- → Prix "collé" aux strikes

**GEX Négatif:**
- Dealers sont SHORT gamma
- Ils achètent quand ça monte, vendent quand ça baisse
- → Amplification de la volatilité
- → Mouvements explosifs

---

## 📊 Niveaux Clés dans le Snapshot

### Call Resistance
```json
"call_resistance": 25400.00
```

**Interprétation:**
- Niveau où beaucoup de CALLS sont ouverts
- Les dealers ont vendu ces calls
- Si le prix monte vers 25400, les dealers doivent acheter pour hedger
- MAIS une fois au-dessus, ils doivent vendre massivement
- → Crée une résistance naturelle

### Put Support
```json
"put_support": 24800.00
```

**Interprétation:**
- Niveau où beaucoup de PUTS sont ouverts
- Les dealers ont vendu ces puts
- Si le prix baisse vers 24800, les dealers doivent vendre pour hedger
- MAIS une fois en-dessous, ils doivent acheter massivement
- → Crée un support naturel

### HVL (Highest Volume Level)
```json
"hvl": 24825.00
```

**Interprétation:**
- Strike avec le plus grand volume d'options
- "Centre de gravité" du marché
- Le prix a tendance à graviter vers ce niveau
- Surtout important en fin de semaine (expiration)

---

## 🔄 Gamma Flip

### Détection
```json
"gamma_flip_up": false,
"gamma_flip_down": false,
"gamma_side": "below"
```

**Gamma Flip = Changement de régime!**

- `gamma_side: "below"` → Prix sous le gamma wall principal
- Quand le prix TRAVERSE le gamma wall:
  - `gamma_flip_up: true` ou `gamma_flip_down: true`
  - Le comportement du marché CHANGE
  - Souvent suivi d'accélération

### Trading autour du Gamma Flip
- **Avant flip:** Attendre confirmation
- **Pendant flip:** Volatilité élevée, prudence
- **Après flip:** Nouveau trend possible

---

## 📐 Value Area Options

### VVA (Volume Value Area)
```json
"vva": {
    "vah": 25523.50,  // Value Area High
    "val": 24101.00,  // Value Area Low
    "vpoc": 24800.00  // Volume Point of Control
}
```

**Interprétation:**
- 70% du volume options est entre VAL et VAH
- VPOC = Prix le plus tradé
- Prix hors de la value area = Extension, retour probable

### Position dans la Value Area
```json
"in_value_area": true
```
- `true` = Prix dans la zone "normale"
- `false` = Prix en extension, attention!

---

## 🎯 Expected Move (1 Day)

```json
"1d_max": 25294.04,
"1d_min": 24602.46
```

**Calcul:** Basé sur la volatilité implicite des options.

**Interprétation:**
- Le marché "price" un range de ~692 points pour la journée
- Prix actuel: 25065
- Marge haute: +229 points
- Marge basse: -463 points

**Trading:**
- Mouvement vers 1d_max/1d_min = Potentiel retournement
- Cassure au-delà = Événement exceptionnel

---

## 🌊 Régime de Volatilité

### VIX
```json
"vix": 16.93
```

| VIX | Régime | Action |
|-----|--------|--------|
| < 15 | Calme | Trading normal |
| 15-20 | Normal | Trading normal |
| 20-25 | Élevé | Prudence |
| 25-35 | Très élevé | Skip trades |
| > 35 | Extrême | STOP TOTAL |

### Volatility Regime
```json
"volatility_regime": 1.000000,
"volatility_regime5": 2.000000,
"volatility_regime_cont": 0.136944
```

- `volatility_regime`: 1-5 (1=calme, 5=extrême)
- `volatility_regime_cont`: Score continu (0-1)

---

## 📊 Structure de Marché Options

### Overnight & Initial Balance
```json
"structure": {
    "onh": 24516.63,      // Overnight High
    "onl": 24513.88,      // Overnight Low
    "ibh": 24874.75,      // Initial Balance High
    "ibl": 24603.63,      // Initial Balance Low
    "awap_onh": 24827.03, // AWAP au ONH
    "awap_onl": 24827.03, // AWAP au ONL
    "awap_ibo": 24889.86  // AWAP à l'open IB
}
```

**Utilisation:**
- IB (Initial Balance) = Premier 30-60 min de session
- Cassure IBH → Potentiel trend haussier
- Cassure IBL → Potentiel trend baissier
- Prix dans IB → Range, attendre cassure

---

## 🔧 Application Pratique

### Scénario LONG
1. Prix au-dessus du HVL ✅
2. Put support proche en-dessous (protection) ✅
3. Call resistance loin au-dessus (room to run) ✅
4. VIX < 25 ✅
5. Pas de gamma flip récent ✅

### Scénario SHORT
1. Prix en-dessous du HVL ✅
2. Call resistance proche au-dessus (protection) ✅
3. Put support loin en-dessous (room to run) ✅
4. VIX < 25 ✅
5. Pas de gamma flip récent ✅

### Éviter de trader
- VIX > 25 ⚠️
- Prix proche d'un gamma flip ⚠️
- Prix hors de la value area sans momentum ⚠️
- Juste avant expiration options (vendredi) ⚠️

---

## 📝 Intégration dans le ML

Ces données options alimentent le **Layer 1 (MenthorQ)** qui représente **50%** du score total.

Le système analyse:
1. Position relative aux niveaux options
2. Distance aux supports/résistances
3. Régime de volatilité
4. Confluence des niveaux

---

*Document technique MIA_IA_system - Version 1.0*
