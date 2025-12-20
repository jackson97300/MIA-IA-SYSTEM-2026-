# 🚀 QUICK START - LANCEMENT BOT MIA

**Dernière mise à jour:** 29 Novembre 2025

---

## ✅ CHECKLIST PRÉ-LANCEMENT (5 min)

### 1. SIERRA CHART

```
☑ Sierra Chart lancé
☑ Connecté au broker (File → Connect to Data Feed)
☑ Charts ouverts:
   - Chart #3: ESZ25_FUT_CME
   - Chart #9: NQZ25_FUT_CME
   - Chart #1: RTYZ25_FUT_CME
☑ Dumper C++ actif (génère snapshots)
```

### 2. DTC PROTOCOL SERVER

```
Global Settings → General Settings → DTC:

☑ Enable DTC Protocol Server
☑ Allow DTC Client Connections
☑ Listening Port: 11099
☑ Send Order/Position Updates
☑ Allow Trading
☐ Require Authentication (DÉCOCHÉ)
☐ Require TLS (DÉCOCHÉ)

⚠️ REDÉMARRER Sierra Chart après modification !
```

### 3. SIMULATION TRADING

```
Global Settings → General Settings → Trade:

☑ Enable Simulated Trading
☑ Allow Multiple Entries/Exits
Simulated Order Fill Delay: 0 ms
Fill Market Orders at: Bid/Ask

Comptes:
☑ Sim1 (ES) - 50,000 USD
☑ Sim2 (NQ) - 50,000 USD
☑ Sim3 (RTY) - 50,000 USD
```

---

## 🧪 TESTS AVANT LANCEMENT

### Test 1: DTC Connection

```powershell
python LAUNCH/test_dtc_simple.py
```

**Attendu:**
```
✅ CONNEXION RÉUSSIE !
✅ LOGON_RESPONSE confirmé
✅ Mode: LIVE (DTC actif)
```

**Si erreur "Connection refused":**
→ Vérifier checklist ci-dessus
→ Redémarrer Sierra Chart

---

### Test 2: Snapshots disponibles

```powershell
ls snapshots\$(Get-Date -Format "yyyyMMdd")
```

**Attendu:** Fichiers `*.json` récents (< 5 secondes)

**Si vide:**
→ Activer dumper C++ dans Sierra Chart

---

## 🚀 LANCEMENT BOT

```powershell
cd D:\MIA_IA_system
python LAUNCH\launch_production_CLEAN_v2.py
```

**Logs startup attendus:**

```
✅ [1/27] MLReadyReader
✅ [2/27] ML3LayerIntegratedSystem
...
✅ [27/27] GammaWallProtector

✅ DTC connecté pour ES
✅ DTC connecté pour NQ
✅ Connexion DTC terminée - Mode LIVE

🔍 SANITY CHECK: Vérification positions orphelines...
✅ Aucune position orpheline détectée

⏳ Pause stabilisation (20s)...
✅ Stabilisation terminée

🚀 DÉMARRAGE BOUCLE PRINCIPALE
```

---

## 🛑 ARRÊT BOT

```powershell
# Méthode 1: Ctrl+C dans le terminal

# Méthode 2: Arrêt forcé
Get-Process python | Stop-Process -Force
```

---

## 📊 MONITORING TEMPS RÉEL

### Discord

- **#admin** - Démarrages, arrêts, erreurs critiques
- **#trades** - Tous les trades (ouverture + fermeture)
- **#alertes** - Alertes temps réel
- **#logs** - Heartbeat toutes les 5 minutes

### Logs fichiers

```powershell
# Logs principaux
Get-Content logs_advanced\trades\*.json -Tail 50

# Logs signals
Get-Content logs_advanced\signals\*.json -Tail 50

# Logs Discord
Get-Content logs_advanced\discord\*.log -Tail 50
```

---

## ⚠️ EN CAS DE PROBLÈME

### Bot ne trade pas

1. **Vérifier session de trading**
   ```
   London: 08:00-11:00 (Paris)
   US Morning: 15:50-17:00 (Paris)
   US Power: 20:00-21:30 (Paris)
   ```

2. **Vérifier VIX**
   ```
   VIX ≥ 35 → Bot arrêté
   VIX 25-35 → Skip trades
   ```

3. **Vérifier Economic Calendar**
   ```
   Annonce ⭐⭐⭐ → Blocage -15min/+30min
   ```

4. **Vérifier données**
   ```
   Age > 5s → Rejection automatique
   ```

### DTC déconnecté

```powershell
# Relancer test
python LAUNCH/test_dtc_simple.py

# Si échec → Vérifier Sierra Chart connecté
# Redémarrer Sierra Chart si nécessaire
```

### Données périmées

```powershell
# Vérifier dumper C++ actif
# Vérifier snapshots récents
ls snapshots\$(Get-Date -Format "yyyyMMdd") | Select-Object -Last 5
```

---

## 📈 MÉTRIQUES ATTENDUES

### Performance

```
Win Rate cible: > 50%
Ratio R/R: 1:1.5
Trades/jour: 10-15
Durée sessions: ~5h40/jour
```

### Latence

```
Connexion DTC: ~2s (initial)
Ordres: 10-50ms
Lecture snapshot: 1-10ms
Pipeline ML: 2-10ms
Total signal→fill: <1s
```

---

## 🔗 LIENS RAPIDES

**Documentation:**
- `docs/README.md` - Guide principal
- `docs/DATA_QUALITY_PROTECTION.md` - Protection données
- `docs/BACKTESTS_HISTORIQUE.md` - Historique performances
- `.cursorrules` - Instructions complètes Cursor

**Tests:**
- `LAUNCH/test_dtc_simple.py` - Test connexion DTC
- `LAUNCH/test_latency_orders.py` - Test latence complète

**Logs session:**
- `CLAUDE/SESSION_29NOV_DTC_DATA_QUALITY.md` - Détails session

---

## 🎯 OBJECTIF ACTUEL

**PHASE 10: Paper Trading 48h**

1. ✅ DTC validé et fonctionnel
2. ✅ Data Quality Checker créé
3. ⏳ Activer dumper C++ (snapshots)
4. ⏳ Lancer bot 48h en observation
5. ⏳ Analyser résultats
6. ⏳ Passage LIVE après validation

---

**🚀 Le système est prêt ! Il ne manque que les snapshots temps réel du dumper C++.**
