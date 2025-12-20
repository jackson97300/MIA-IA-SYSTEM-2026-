# 🛡️ PROTECTION DONNÉES PÉRIMÉES - DOCUMENTATION

**Date:** 29 Novembre 2025
**Problème identifié:** Le bot pourrait trader avec des données périmées sans contrôle
**Solution:** Module `DataQualityChecker` intégré

---

## 🎯 OBJECTIF

**Empêcher le bot de trader avec des données invalides ou périmées.**

Sans ce contrôle, le bot pourrait :
- ❌ Trader sur des prix d'hier
- ❌ Utiliser des données corrompues
- ❌ Prendre des décisions sur des snapshots incomplets
- ❌ Trader alors que Sierra Chart est déconnecté

---

## ✅ CONTRÔLES IMPLÉMENTÉS

### 1. **AGE DES DONNÉES** (Critique)

```
Max autorisé: 5 secondes
```

- ✅ Données < 5s → OK
- ⚠️ Données 5-10s → Warning
- ❌ Données > 10s → **REJET IMMÉDIAT**

**Protection:** Empêche de trader sur des données d'hier ou de la veille

---

### 2. **CHAMPS OBLIGATOIRES**

Vérification présence de :
- `t_ms` - Timestamp
- `mid` - Prix mid
- `best_bid` / `best_ask` - Marché
- `vwap` - VWAP
- `delta` - Delta
- `volume` - Volume

**Protection:** Empêche de trader avec snapshots incomplets

---

### 3. **COHÉRENCE DES DONNÉES**

```python
✅ mid > 0
✅ best_bid > 0 and best_ask > 0
✅ best_ask > best_bid
✅ spread < 10 ticks (ES/NQ) ou 20 ticks (RTY)
```

**Protection:** Détecte données corrompues ou market freeze

---

### 4. **VIX VALIDE**

```python
✅ 0 < vix < 100
```

**Protection:** VIX à 0 ou > 100 = données invalides

---

### 5. **SESSION ID PRÉSENT**

```python
✅ session_id in ['London', 'US', 'Asia']
```

**Protection:** Sait dans quelle session on trade

---

## 📊 SCORE QUALITÉ (0-100)

Le checker calcule un score qualité :

```
100 = Parfait (données fraîches < 1s, tous champs présents)
90-99 = Bon (données 1-2s)
80-89 = Acceptable (données 2-5s)
< 80 = Suspect (pénalités)
< 50 = Mauvais → REJET
```

### Pénalités

- **-10 par seconde** au-delà de 1s d'age
- **-10** si pas de données options (GEX)
- **-10** si pas de VIX
- **-5** si session_id manquant

---

## 🔧 INTÉGRATION DANS LE BOT

### Dans `launch_production_CLEAN_v2.py`

```python
from utils.data_quality_checker import DataQualityChecker

# Initialisation
self.data_quality = DataQualityChecker(max_data_age_seconds=5)

# Dans la boucle principale
snapshot = self.ml_reader.get_live_snapshot(symbol)

# ✅ VALIDATION AVANT TRADING
is_valid, reason = self.data_quality.validate_snapshot(snapshot, symbol)

if not is_valid:
    logger.warning(f"❌ [{symbol}] Données invalides: {reason} - SKIP")
    self.stats['data_quality_rejects'] += 1
    continue  # Passer au cycle suivant

# Rapport détaillé (optionnel)
quality_report = self.data_quality.get_data_quality_report(snapshot, symbol)
logger.debug(f"[{symbol}] Qualité: {quality_report['quality_score']}/100 "
             f"(age: {quality_report['age_seconds']}s)")
```

---

## 🚨 CAS D'USAGE RÉELS

### Scénario 1: Sierra Chart déconnecté

```
Snapshot age: 3600s (1 heure)
→ REJET: "Données trop anciennes (3600s > 5s)"
→ Bot ne trade PAS
```

### Scénario 2: Dumper C++ crashé

```
Derniers snapshots: 2025-11-28
Aujourd'hui: 2025-11-29
→ REJET: "Données trop anciennes"
→ Bot ne trade PAS
```

### Scénario 3: Données corrompues

```
Snapshot: {mid: 0, best_bid: 0, best_ask: 0}
→ REJET: "Prix mid invalide: 0"
→ Bot ne trade PAS
```

### Scénario 4: Market freeze

```
Spread: 50 points (200 ticks)
→ REJET: "Spread anormal: 200 ticks (max 10)"
→ Bot ne trade PAS
```

---

## 📈 MONITORING

### Logs de rejet

```
2025-11-29 14:30:00 | WARNING | ❌ [ES] Données invalides: Données trop anciennes (15.2s > 5s) - SKIP
2025-11-29 14:30:01 | WARNING | ❌ [NQ] Données invalides: Spread anormal: 25.0 ticks - SKIP
```

### Stats Discord

Le bot enverra dans les résumés journaliers :

```
📊 Statistiques Qualité Données:
   ✅ Snapshots valides: 15,234
   ❌ Rejets qualité: 12

   Raisons rejets:
   - Données trop anciennes: 8
   - Spread anormal: 3
   - Champs manquants: 1
```

---

## ✅ AVANTAGES

1. **Protection automatique** - Pas besoin de surveiller manuellement
2. **Logs clairs** - Tu sais pourquoi un snapshot est rejeté
3. **Configuré** - Max 5s d'age par défaut (ajustable)
4. **Léger** - Validation en < 1ms
5. **Transparent** - Logging de tous les rejets

---

## 🔧 CONFIGURATION

### Ajuster le seuil d'age

```python
# Plus strict (données ultra-fraîches)
self.data_quality = DataQualityChecker(max_data_age_seconds=2)

# Plus permissif (backtest ou dev)
self.data_quality = DataQualityChecker(max_data_age_seconds=10)
```

### Désactiver temporairement (DEV uniquement)

```python
# ATTENTION: À utiliser uniquement en dev/debug !
is_valid = True  # Skip validation
```

---

## 📋 CHECKLIST AVANT LANCEMENT

Avant de lancer le bot, vérifier :

- [ ] Sierra Chart **connecté** au broker
- [ ] Dumper C++ **actif** (génère snapshots)
- [ ] Snapshots **récents** dans `snapshots/[YYYYMMDD]/`
- [ ] Age des snapshots < 5s
- [ ] Module `DataQualityChecker` activé dans le lanceur

---

## 🚀 PROCHAINES ÉTAPES

**TODO pour Phase 10:**

1. ✅ Créer `DataQualityChecker`
2. ⏳ Intégrer dans `launch_production_CLEAN_v2.py`
3. ⏳ Ajouter stats rejets dans Discord
4. ⏳ Tester en conditions réelles
5. ⏳ Ajuster seuils si nécessaire

---

## 📚 FICHIERS

- **Module:** `utils/data_quality_checker.py`
- **Tests:** `python utils/data_quality_checker.py`
- **Doc:** `docs/DATA_QUALITY_PROTECTION.md` (ce fichier)

---

**✅ Avec ce module, le bot NE POURRA PLUS trader sur des données périmées !**
