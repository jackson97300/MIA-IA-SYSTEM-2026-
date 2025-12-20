# 📋 Discord #logs - Guide Debug à Distance
**Date:** 08 Décembre 2025
**Version:** Production CLEAN v2.0

---

## 🎯 Principe : PROBLÈMES uniquement

Le salon Discord **#logs** sert au **DEBUG À DISTANCE** :
- ❌ Modules qui ne chargent pas
- ❌ Fonctions qui échouent
- ⏱️ Timeouts détectés
- 📭 Données manquantes/invalides
- 🔍 Valeurs anormales
- 🔒 Boucles bloquées
- 🔄 Retries épuisés
- 🚀 Status démarrage (modules OK/FAIL)
- ⚠️ Alertes système (VIX, Kill Switch, DTC)

**PAS de doublon avec les autres salons** (trades, monitoring, heartbeat).

---

## 📝 Fonctions de Debug Disponibles

### 🔧 DEBUG TECHNIQUE (NOUVEAU)

#### `send_module_load_error()` - Module qui ne charge pas
```python
await discord.send_module_load_error(
    module_name="TrailingStopManager",
    error="ModuleNotFoundError: No module named 'xxx'",
    is_critical=True  # True = bot peut mal fonctionner
)
```
**Message Discord:**
```
🔴 MODULE ÉCHEC - TrailingStopManager
[01:45:23] CHARGEMENT ÉCHOUÉ
📦 Module: TrailingStopManager
❌ Erreur: ModuleNotFoundError: No module named 'xxx'
⚠️ Critique: OUI - Bot peut mal fonctionner
```

---

#### `send_function_error()` - Fonction qui échoue
```python
await discord.send_function_error(
    function_name="calculate_trailing_stop",
    module="TrailingStopManager",
    error="ZeroDivisionError: division by zero",
    input_data="{'atr': 0, 'price': 5000}"
)
```
**Message Discord:**
```
❌ FONCTION ERREUR - calculate_trailing_stop
[01:45:23] EXCEPTION
📦 Module: TrailingStopManager
🔧 Fonction: calculate_trailing_stop()
❌ Erreur: ZeroDivisionError: division by zero
📥 Input: {'atr': 0, 'price': 5000}
```

---

#### `send_timeout_error()` - Timeout détecté
```python
await discord.send_timeout_error(
    operation="Lecture snapshot ML",
    timeout_seconds=5.0,
    symbol="NQ"
)
```
**Message Discord:**
```
⏱️ TIMEOUT - Lecture snapshot ML
[01:45:23] OPÉRATION TROP LENTE
🔧 Opération: Lecture snapshot ML
⏱️ Timeout: 5.0s
📊 Symbole: NQ
🔄 Action: Retry automatique...
```

---

#### `send_data_missing_error()` - Données manquantes
```python
await discord.send_data_missing_error(
    data_type="Snapshot ML",
    symbol="ES",
    expected_fields=["mid", "delta", "gex_level"]
)
```
**Message Discord:**
```
📭 DONNÉES MANQUANTES - ES
[01:45:23] DATA INVALIDE
📊 Symbole: ES
📦 Type données: Snapshot ML
❌ Champs manquants: mid, delta, gex_level
```

---

#### `send_value_anomaly()` - Valeur anormale
```python
await discord.send_value_anomaly(
    field_name="delta",
    value=-999999,
    expected_range="-10000 à +10000",
    symbol="NQ"
)
```
**Message Discord:**
```
🔍 VALEUR ANORMALE - delta
[01:45:23] ANOMALIE DÉTECTÉE
📊 Champ: delta
❓ Valeur: -999999
✅ Attendu: -10000 à +10000
📈 Symbole: NQ
```

---

#### `send_retry_exhausted()` - Retries épuisés
```python
await discord.send_retry_exhausted(
    operation="Connexion DTC",
    max_retries=3,
    last_error="Connection refused"
)
```
**Message Discord:**
```
🔄 RETRIES ÉPUISÉS - Connexion DTC
[01:45:23] ÉCHEC DÉFINITIF
🔧 Opération: Connexion DTC
🔄 Tentatives: 3/3 (toutes échouées)
❌ Dernière erreur: Connection refused
🛑 Status: Opération abandonnée
```

---

#### `send_startup_status()` - Status démarrage bot
```python
await discord.send_startup_status(
    modules_status={
        "ML3LayerFilter": True,
        "TrailingStopManager": True,
        "RiskManager": False  # Échec!
    },
    connections_status={
        "DTC_ES": True,
        "DTC_NQ": True,
        "Discord": True
    }
)
```
**Message Discord:**
```
⚠️ BOT DÉMARRÉ - 1 problème(s)
[01:45:23] DÉMARRAGE MIA

📦 Modules: 2/3 chargés
❌ Échecs: RiskManager

🔌 Connexions: 3/3 établies
```

---

#### `send_loop_stuck_alert()` - Boucle bloquée
```python
await discord.send_loop_stuck_alert(
    loop_name="Main Trading Loop",
    last_activity_seconds=45
)
```
**Message Discord:**
```
🔒 BOUCLE BLOQUÉE - Main Trading Loop
[01:45:23] WATCHDOG ALERT
🔄 Boucle: Main Trading Loop
⏱️ Dernière activité: il y a 45s
⚠️ Seuil normal: < 10s
🚨 Action requise: Vérifier si bot frozen
```

---

#### `send_memory_warning()` - Mémoire élevée
```python
await discord.send_memory_warning(
    memory_mb=1500,
    threshold_mb=1000
)
```

---

#### `send_config_validation_error()` - Config invalide
```python
await discord.send_config_validation_error(
    config_name="ProductionConfig",
    field="daily_loss_limit",
    value=-50,  # Trop petit!
    reason="Valeur doit être >= 100"
)
```

---

### ⚠️ ALERTES SYSTÈME

### 1. `send_critical_error_log()`
**Usage:** Erreurs système graves (crash module, exception non gérée)

```python
await self.discord_notifier.send_critical_error_log(
    module="TrailingStopManager",
    error_type="EXCEPTION",
    message="Impossible de calculer trailing stop: division by zero",
    impact="Position ES non protégée",
    action_taken="Position fermée manuellement"
)
```

**Exemple de message Discord:**
```
🔴 ERREUR CRITIQUE - TrailingStopManager

[2025-12-08 01:45:23] EXCEPTION
Module: TrailingStopManager
Message: Impossible de calculer trailing stop: division by zero
Impact: Position ES non protégée
Action: Position fermée manuellement
```

---

### 2. `send_vix_alert_log()`
**Usage:** VIX dépassant seuil critique (≥35)

```python
await self.discord_notifier.send_vix_alert_log(
    vix_level=36.2,
    threshold=35.0,
    action="Trading bloqué jusqu'à baisse VIX"
)
```

**Exemple de message Discord:**
```
⚠️ ALERTE VIX - Trading bloqué

[2025-12-08 14:23:11] VIX ÉLEVÉ
🔴 VIX actuel: 36.2
🛑 Seuil limite: 35.0
🔒 Action: Trading bloqué jusqu'à baisse VIX
```

---

### 3. `send_kill_switch_log()`
**Usage:** Activation kill switch (daily loss limit, etc.)

```python
await self.discord_notifier.send_kill_switch_log(
    reason="Daily loss limit atteint",
    trigger_value="-$502.50",
    daily_pnl=-502.50
)
```

**Exemple de message Discord:**
```
🔒 KILL SWITCH ACTIVÉ

[2025-12-08 16:45:00] ARRÊT D'URGENCE
🚨 Raison: Daily loss limit atteint
📊 Valeur déclencheur: -$502.50
💰 P&L journalier: -$502.50
🛑 Status: Tous les nouveaux trades sont bloqués
```

---

### 4. `send_economic_calendar_block_log()`
**Usage:** Blocage avant annonce économique ⭐⭐⭐

```python
await self.discord_notifier.send_economic_calendar_block_log(
    event_name="Non-Farm Payrolls (NFP)",
    event_time="14:30",
    stars=3,
    minutes_before=15
)
```

**Exemple de message Discord:**
```
🔒 BLOCAGE CALENDRIER - ⭐⭐⭐

[2025-12-08 14:15:00] ANNONCE ÉCONOMIQUE
📅 Événement: Non-Farm Payrolls (NFP)
⭐⭐⭐ Importance: 3/3 étoiles
🕐 Heure annonce: 14:30
⏱️ Trading bloqué: 15min avant l'annonce
🔓 Reprise: 30min après l'annonce
```

---

### 5. `send_dtc_connection_log()`
**Usage:** Changements status connexion broker DTC

```python
# Connexion perdue
await self.discord_notifier.send_dtc_connection_log(
    status="DISCONNECTED",
    symbol="ES",
    error_msg="Socket closed by remote"
)

# Reconnexion réussie
await self.discord_notifier.send_dtc_connection_log(
    status="RECONNECTED",
    symbol="ES"
)
```

**Exemple de message Discord:**
```
🔴 CONNEXION DTC PERDUE

[2025-12-08 01:35:42] CONNEXION BROKER
❌ Status: DISCONNECTED
📊 Symbole: ES
❌ Erreur: Socket closed by remote
🔄 Tentative de reconnexion automatique...
```

---

### 6. `send_data_quality_alert_log()`
**Usage:** Données périmées (>5 secondes)

```python
await self.discord_notifier.send_data_quality_alert_log(
    symbol="NQ",
    issue="Snapshot trop ancien",
    age_seconds=7.2
)
```

**Exemple de message Discord:**
```
⚠️ DONNÉES PÉRIMÉES - NQ

[2025-12-08 15:23:45] QUALITÉ DONNÉES
📊 Symbole: NQ
⚠️ Problème: Snapshot trop ancien
⏱️ Âge données: 7.2s (limite: 5s)
🔒 Action: Trading bloqué jusqu'à données fraîches
```

---

### 7. `send_daily_summary_log()`
**Usage:** Résumé journalier (1x/jour à 23:30)

```python
await self.discord_notifier.send_daily_summary_log({
    'total_trades': 12,
    'wins': 9,
    'losses': 3,
    'daily_pnl': 487.50,
    'signals_analyzed': 45,
    'signals_taken': 12,
    'ES_stats': {'trades': 6, 'wins': 5, 'pnl': 250.00},
    'NQ_stats': {'trades': 6, 'wins': 4, 'pnl': 237.50}
})
```

**Exemple de message Discord:**
```
📊 RÉSUMÉ JOURNALIER

[2025-12-08 23:30:00] FIN DE SESSION
📈 Trades: 12 (9W - 3L)
🎯 Win Rate: 75.0%
✅ P&L: +$487.50

Par symbole:
• ES: 6T (5W) 💰 +$250.00
• NQ: 6T (4W) 💰 +$237.50

Filtrage ML:
• Signaux analysés: 45
• Signaux acceptés: 12
• Sélectivité: 26.7%
```

---

### 8. `send_session_change_log()`
**Usage:** Changement de session trading (optionnel, peu critique)

```python
await self.discord_notifier.send_session_change_log(
    old_session="London",
    new_session="US Morning"
)
```

---

## 🔧 Intégration dans le Code Existant

### **Fichier:** `LAUNCH/launch_production_CLEAN_v2.py`

#### A. Activation Kill Switch (VIX ou Daily Loss Limit)

**Localisation:** Ligne ~2800-3000 (boucle principale)

```python
# Vérifier VIX
if current_vix >= 35:
    if self.can_trade:
        # 🆕 LOG DISCORD
        await self.discord_notifier.send_vix_alert_log(
            vix_level=current_vix,
            threshold=35.0,
            action="Trading bloqué jusqu'à baisse VIX"
        )
        logger.warning(f"🔴 VIX trop élevé: {current_vix:.1f} (≥35)")
        self.can_trade = False
        self.kill_switch_reason = f"VIX={current_vix:.1f}"

# Vérifier daily loss limit
if daily_pnl <= -self.config.daily_loss_limit:
    if self.can_trade:
        # 🆕 LOG DISCORD
        await self.discord_notifier.send_kill_switch_log(
            reason="Daily loss limit atteint",
            trigger_value=f"${daily_pnl:+.2f}",
            daily_pnl=daily_pnl
        )
        logger.error(f"🔒 Kill switch activé: daily loss ${daily_pnl:.2f}")
        self.can_trade = False
        self.kill_switch_reason = f"DailyLossLimit=${daily_pnl:.2f}"
```

#### B. Blocage Calendrier Économique

**Localisation:** Ligne ~2600 (check economic calendar)

```python
# Si annonce ⭐⭐⭐ dans 15min
if event_in_15min and event_stars == 3:
    # 🆕 LOG DISCORD
    await self.discord_notifier.send_economic_calendar_block_log(
        event_name=event_name,
        event_time=event_time.strftime("%H:%M"),
        stars=3,
        minutes_before=15
    )
    logger.warning(f"🔒 Trading bloqué: annonce {event_name} dans 15min")
    self.economic_block_active = True
```

#### C. Données Périmées

**Localisation:** Ligne ~2400 (validation snapshot age)

```python
# Vérifier âge snapshot
snapshot_age_ms = now_ms - snapshot.get('timestamp_ms', 0)
if snapshot_age_ms > self.config.snapshot_max_age_ms:
    age_seconds = snapshot_age_ms / 1000
    # 🆕 LOG DISCORD (seulement si >5s)
    if age_seconds > 5.0:
        await self.discord_notifier.send_data_quality_alert_log(
            symbol=symbol,
            issue="Snapshot trop ancien",
            age_seconds=age_seconds
        )
    logger.warning(f"⚠️ Snapshot {symbol} trop ancien: {age_seconds:.1f}s")
    continue
```

#### D. Résumé Journalier (23:30)

**Localisation:** Ligne ~3600 (fin de boucle principale, check heure)

```python
# Check si 23:30 (générer résumé journalier)
current_time = datetime.now()
if current_time.hour == 23 and current_time.minute == 30:
    if not self.daily_summary_sent:
        # 🆕 LOG DISCORD
        summary_data = {
            'total_trades': sum(self.daily_trades_count.values()),
            'wins': sum(1 for t in self.trade_history if t.get('pnl_net', 0) > 0),
            'losses': sum(1 for t in self.trade_history if t.get('pnl_net', 0) < 0),
            'daily_pnl': self.daily_pnl,
            'signals_analyzed': self.signals_analyzed_today,
            'signals_taken': sum(self.daily_trades_count.values()),
            'ES_stats': self._get_symbol_stats('ES'),
            'NQ_stats': self._get_symbol_stats('NQ'),
            'RTY_stats': self._get_symbol_stats('RTY')
        }

        await self.discord_notifier.send_daily_summary_log(summary_data)
        self.daily_summary_sent = True
        logger.info("📊 Résumé journalier envoyé Discord #logs")
```

### **Fichier:** `execution/sierra_dtc_connector.py`

#### E. Connexion DTC Perdue/Rétablie

**Localisation:** Ligne ~500-700 (gestion connexion)

```python
async def _handle_disconnect(self, symbol: str):
    """Gère déconnexion DTC"""
    logger.error(f"🔴 Connexion DTC perdue: {symbol}")

    # 🆕 LOG DISCORD
    if hasattr(self, 'discord_notifier') and self.discord_notifier:
        await self.discord_notifier.send_dtc_connection_log(
            status="DISCONNECTED",
            symbol=symbol,
            error_msg="Connection lost"
        )

    # Tenter reconnexion
    await self._reconnect(symbol)

async def _handle_reconnect_success(self, symbol: str):
    """Gère reconnexion réussie"""
    logger.info(f"✅ Connexion DTC rétablie: {symbol}")

    # 🆕 LOG DISCORD
    if hasattr(self, 'discord_notifier') and self.discord_notifier:
        await self.discord_notifier.send_dtc_connection_log(
            status="RECONNECTED",
            symbol=symbol
        )
```

### **Fichier:** `core/safety_kill_switch.py`

#### F. Erreurs Critiques Modules

**Localisation:** Ligne ~200 (try/except global)

```python
try:
    # Code du module
    result = await self.process_data(snapshot)
except Exception as e:
    logger.error(f"❌ Erreur critique dans {self.__class__.__name__}: {e}")

    # 🆕 LOG DISCORD
    if hasattr(self, 'discord_notifier') and self.discord_notifier:
        await self.discord_notifier.send_critical_error_log(
            module=self.__class__.__name__,
            error_type="EXCEPTION",
            message=str(e),
            impact="Module désactivé temporairement",
            action_taken="Fallback vers valeurs par défaut"
        )

    # Fallback
    return default_value
```

---

## ✅ Checklist d'Intégration

### 🚀 Démarrage Bot
- [ ] `send_startup_status()` dans `__init__` du launcher (après chargement modules)
- [ ] `send_module_load_error()` dans chaque `try/except` d'import de module

### ⚠️ Alertes Système
- [ ] `send_vix_alert_log()` quand VIX ≥ 35
- [ ] `send_kill_switch_log()` quand kill switch activé
- [ ] `send_economic_calendar_block_log()` avant annonces ⭐⭐⭐
- [ ] `send_dtc_connection_log()` sur perte/reconnexion DTC

### 🔧 Debug Technique
- [ ] `send_function_error()` dans les try/except des fonctions critiques
- [ ] `send_timeout_error()` sur les opérations avec timeout
- [ ] `send_data_missing_error()` quand snapshot incomplet
- [ ] `send_value_anomaly()` quand valeur hors range attendu
- [ ] `send_retry_exhausted()` après échec de tous les retries
- [ ] `send_loop_stuck_alert()` si boucle principale bloquée > 30s

### 📊 Résumé
- [ ] `send_daily_summary_log()` à 23:30

---

## 🧪 Tests Rapides

### Test 1: VIX Alert (simulation)
```python
await discord_notifier.send_vix_alert_log(36.5, 35.0, "Trading bloqué")
```

### Test 2: Kill Switch (simulation)
```python
await discord_notifier.send_kill_switch_log("Test manuel", "-$500", -500.0)
```

### Test 3: Economic Calendar (simulation)
```python
await discord_notifier.send_economic_calendar_block_log("NFP", "14:30", 3, 15)
```

### Test 4: DTC Disconnect (simulation)
```python
await discord_notifier.send_dtc_connection_log("DISCONNECTED", "ES", "Test")
```

### Test 5: Résumé Journalier (simulation)
```python
await discord_notifier.send_daily_summary_log({
    'total_trades': 10, 'wins': 7, 'losses': 3,
    'daily_pnl': 350.0, 'signals_analyzed': 40, 'signals_taken': 10
})
```

---

## 📊 Fréquence Attendue

| Type de Log | Fréquence | Priorité |
|-------------|-----------|----------|
| **🚀 Startup Status** | 1x/démarrage | ℹ️ INFO |
| **❌ Module Load Error** | Rare (si problème) | 🔴 URGENT |
| **❌ Function Error** | Variable (bugs) | 🔴 URGENT |
| **⏱️ Timeout Error** | Occasionnel | ⚠️ HAUTE |
| **📭 Data Missing** | Rare | ⚠️ HAUTE |
| **🔍 Value Anomaly** | Rare | ⚠️ HAUTE |
| **🔄 Retry Exhausted** | Rare | 🔴 URGENT |
| **🔒 Loop Stuck** | Très rare (bug grave) | 🔴 CRITIQUE |
| **💾 Memory Warning** | Rare | ⚠️ HAUTE |
| **⚙️ Config Error** | Au démarrage | 🟠 MOYENNE |
| VIX Alert | Rare (volatilité extrême) | ⚠️ HAUTE |
| Kill Switch | Rare (1-2x/mois max) | 🔴 URGENT |
| Economic Calendar | 0-3x/jour | 🟠 MOYENNE |
| DTC Disconnect | Rare (< 1/semaine) | 🔴 URGENT |
| Data Quality (périmée) | Occasionnel | ⚠️ HAUTE |
| Résumé Journalier | 1x/jour (23:30) | ℹ️ INFO |

**En fonctionnement NORMAL:** 3-5 messages/jour (startup + résumé + occasionnel)
**Si PROBLÈMES:** Plus de messages = plus de bugs à investiguer

---

## 🚫 Ce Qu'il NE Faut PAS Logguer dans #logs

| ❌ NE PAS LOGGUER | ✅ DÉJÀ DANS CE SALON |
|-------------------|----------------------|
| Trades ouverts/fermés | #trades-es, #trades-nq |
| Heartbeat | #monitoring |
| Signaux analysés/rejetés | (pas de spam) |
| Prix en temps réel | (pas de spam) |
| Stats continues | #performance |

**Principe #logs = PROBLÈMES uniquement**
- Si tout fonctionne → Pas de message
- Si quelque chose casse → Message immédiat
- Un message = Un problème à investiguer

---

## 📝 Notes Finales

1. **Ne pas relancer le bot automatiquement** après intégration (comme demandé)
2. **Tester en simulation** avant production
3. **Vérifier que Discord reçoit bien** chaque type de message
4. **Ajuster les seuils** si trop/pas assez de messages
5. **Documenter tout changement** dans ce fichier

---

**Dernière mise à jour:** 08 Décembre 2025, 01:50
**Status:** ✅ Implémenté, non intégré (bot éteint)
