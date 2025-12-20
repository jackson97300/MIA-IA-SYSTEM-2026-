# ⚠️ CHANGEMENTS URGENTS À APPLIQUER - 05 DÉCEMBRE 2025

**Contexte**: Session 04/12 rentable (+$337) mais **SURTRADING MASSIF** (30 trades vs 10-15 cible)

---

## 🔥 PRIORITÉ #1: ANTI-SURTRADING

### **Problème**
- 30 trades au lieu de 10-15
- 19 trades en 70 minutes (US Morning)
- Cooldown 2 minutes **TROP COURT**

### **Solution**

**Fichier**: `LAUNCH/launch_production_CLEAN_v2.py`

```python
# LIGNE ~101
# AVANT:
cooldown_ms: int = 120000  # 2 minutes

# APRÈS:
cooldown_ms: int = 300000  # 🔥 5 MINUTES - Anti-surtrading
```

**Impact**: Maximum ~6-8 trades par session au lieu de 15-20

---

## 🔥 PRIORITÉ #2: AUGMENTER CONFIDENCE NQ

### **Problème**
- NQ: Win Rate 33% (déficitaire -$837)
- 12 SL Hit contre seulement 6 Wins
- Trop de trades de mauvaise qualité acceptés

### **Solution**

**Fichier**: `config/unified_thresholds.py`

```python
# LIGNE ~50
MIN_TOTAL_CONFIDENCE = {
    'ES': 35,   # ✅ OK (WR 58%)
    'NQ': 45,   # 🔥 AUGMENTÉ: 35 → 45 (sélection stricte)
    'RTY': 40
}
```

**Impact**: Moins de trades NQ mais **meilleure qualité**

---

## 🔥 PRIORITÉ #3: CIRCUIT BREAKER "LOSS STREAK"

### **Problème**
- 10 SL Hit consécutifs sur NQ (16:09 → 16:54)
- Pas de protection contre spirale de losses

### **Solution**

**Fichier**: `LAUNCH/launch_production_CLEAN_v2.py`

**Ajouter dans la classe `Config`** (ligne ~90):
```python
# Nouvelle config
max_consecutive_losses: int = 3  # Stop trading symbole après 3 losses
loss_streak_cooldown_ms: int = 1800000  # 30 minutes de pause
```

**Ajouter dans `__init__` du Launcher** (ligne ~700):
```python
# Tracking losses consécutives
self.consecutive_losses: Dict[str, int] = {
    'ES': 0,
    'NQ': 0,
    'RTY': 0
}
self.loss_streak_block_until: Dict[str, Optional[datetime]] = {
    'ES': None,
    'NQ': None,
    'RTY': None
}
```

**Ajouter dans `_process_signal()`** (avant l'exécution, ligne ~1900):
```python
# ═══════════════════════════════════════════════════════════════
# CIRCUIT BREAKER: Loss Streak Protection
# ═══════════════════════════════════════════════════════════════
if self.loss_streak_block_until.get(symbol):
    if datetime.now() < self.loss_streak_block_until[symbol]:
        remaining = (self.loss_streak_block_until[symbol] - datetime.now()).total_seconds() / 60
        logger.warning(
            f"   ❌ [{symbol}] CIRCUIT BREAKER: "
            f"{self.consecutive_losses[symbol]} losses consécutives. "
            f"Pause encore {remaining:.1f}min"
        )
        return
    else:
        # Fin du cooldown
        logger.info(f"✅ [{symbol}] Circuit breaker levé - Reprise trading")
        self.loss_streak_block_until[symbol] = None
        self.consecutive_losses[symbol] = 0
```

**Ajouter dans `_close_position_internal()`** (après fermeture, ligne ~2400):
```python
# Update loss streak
if 'LOSS' in reason or 'SL Hit' in str(reason):
    self.consecutive_losses[symbol] += 1

    # Vérifier circuit breaker
    if self.consecutive_losses[symbol] >= self.config.max_consecutive_losses:
        cooldown_end = datetime.now() + timedelta(milliseconds=self.config.loss_streak_cooldown_ms)
        self.loss_streak_block_until[symbol] = cooldown_end

        logger.error(
            f"🔴 [{symbol}] CIRCUIT BREAKER ACTIVÉ: "
            f"{self.consecutive_losses[symbol]} losses consécutives! "
            f"Pause 30min (jusqu'à {cooldown_end.strftime('%H:%M')})"
        )
else:
    # Win → Reset streak
    self.consecutive_losses[symbol] = 0
```

**Impact**:
- Stop trading après 3 losses consécutives
- Évite les spirales de pertes
- Protection psychologique

---

## 📊 PRIORITÉ #4: BLOC HORAIRE 16:30-17:00 (Optionnel)

### **Problème**
- 16:30-17:00 = Fin session US = Volatilité extrême
- Beaucoup de faux signaux et whipsaws

### **Solution** (À TESTER)

**Fichier**: `core/session_quality_monitor.py`

**Ajouter un bloc** (ligne ~400):
```python
# US Close Volatility Block (16:30-17:00)
if self.enable_us:
    if hour == 16 and minute >= 30:
        next_session_info = self._get_next_session_info(now)
        return True, f"[🔴 US CLOSE BLOCK] Volatilité extrême fin de session (16:30-17:00). {next_session_info}"
```

**Impact**:
- Évite 5-10 trades de mauvaise qualité
- Focus sur US Power Hour (20:00-21:30)

⚠️ **À VALIDER**: Analyser logs 05/12 pour décider si nécessaire

---

## ✅ DÉJÀ APPLIQUÉ AUJOURD'HUI

1. ✅ **Filtre proximité strict** (10 ticks ES/NQ) - 17:15
2. ✅ **BE Trigger NQ réduit** (30t → 25t) - 17:53

---

## 📋 CHECKLIST AVANT SESSION 05/12

### **À FAIRE MAINTENANT**:
- [ ] Augmenter `cooldown_ms` à 300000 (5 min)
- [ ] Augmenter `MIN_TOTAL_CONFIDENCE['NQ']` à 45%
- [ ] Implémenter Circuit Breaker loss streak

### **À TESTER**:
- [ ] Observer si cooldown 5min réduit nombre de trades
- [ ] Vérifier Win Rate NQ avec confidence 45%
- [ ] Analyser si circuit breaker se déclenche

### **À DÉCIDER**:
- [ ] Bloc 16:30-17:00 nécessaire ? (analyser logs 05/12)
- [ ] BE 25t efficace sur NQ ? (observer MFE/MAE)

---

## 🎯 OBJECTIFS SESSION 05/12

| Métrique | Cible | Mesure |
|----------|-------|--------|
| **Nombre Trades** | **<15** | vs 30 hier |
| **Win Rate** | **>50%** | vs 43% hier |
| **NQ Win Rate** | **>45%** | vs 33% hier |
| **P&L** | **>$200** | vs $337 hier |
| **Discipline** | **Aucune série >3 losses** | vs 10 hier |

---

## ⚠️ POINTS D'ATTENTION

1. **Cooldown 5min** = Moins de trades mais **meilleure qualité**
2. **Confidence NQ 45%** = Peut bloquer certains trades (normal)
3. **Circuit Breaker** = Pause forcée si série noire (protection)
4. **BE 25t NQ** = Devrait protéger mieux les trades gagnants

**Philosophie**: **QUALITÉ > QUANTITÉ**

---

**Date création**: 04/12/2025 22:15
**À appliquer avant**: Session London 05/12 (08:00)
**Priorité**: 🔥 CRITIQUE
