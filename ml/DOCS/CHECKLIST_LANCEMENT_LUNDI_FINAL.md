# ✅ CHECKLIST LANCEMENT LUNDI - Version Finale

**Date:** 15 Novembre 2025
**Status:** Prêt pour production
**Symboles:** ES + NQ
**Objectif:** 1 semaine de test en conditions réelles

---

## 📋 **PHASE 1: PRÉPARATION DIMANCHE SOIR (20h-22h)**

### ✅ 1. Vérification Configuration

```bash
# Ouvrir LAUNCH/launch_ml_v3_production.py
# Vérifier:
```

#### **A. Symboles Actifs (ligne ~4866):**
```python
ACTIVE_SYMBOLS = ["ES", "NQ"]  # ✅ ES + NQ
SUSPENDED_SYMBOLS = ["RTY"]     # ✅ RTY suspendu
```

#### **B. Fees (ligne ~1689):**
```python
fees_per_contract = {
    'ES': 1.40,   # PropFirms Moyennes - 0.12 ticks
    'NQ': 1.40,   # PropFirms Moyennes - 0.28 ticks
    'RTY': 1.40
}
```

#### **C. Stabilisation (ligne ~3900):**
```python
await asyncio.sleep(30)  # ✅ 30s de stabilisation
```

---

### ✅ 2. Vérification TP/SL Optimaux

#### **A. ConfluenceSignal (strategies/vwap_sd_options_confluence_strategy.py, ligne ~421):**
```python
TP_OPTIMAL = {
    'ES': 16,  # ✅ Filet de sécurité
    'NQ': 23,  # ✅ Filet de sécurité
    'RTY': 25
}

# Ligne ~348 (base_sl_ticks):
base_sl_ticks = {
    'ES': 12,  # ✅ Filet de sécurité
    'NQ': 12,  # ✅ Filet de sécurité
    'RTY': 15
}
```

#### **B. ML 3-Layer (strategies/ml_3layer_strategy.py, ligne ~46):**
```python
use_fixed_tp_sl = True  # ✅ Activé

sl_optimal_ticks = {
    'ES': 12,  # ✅ Filet de sécurité
    'NQ': 12,
    'RTY': 15
}

tp_optimal_ticks = {
    'ES': 16,  # ✅ Filet de sécurité
    'NQ': 23,
    'RTY': 25
}
```

---

### ✅ 3. Test Local (Dimanche 21h)

```bash
# Dans terminal:
cd D:\MIA_IA_system

# Vérifier syntaxe Python:
python -m py_compile LAUNCH/launch_ml_v3_production.py
python -m py_compile strategies/vwap_sd_options_confluence_strategy.py
python -m py_compile strategies/ml_3layer_strategy.py

# Si erreurs → corriger avant lancement
```

---

## 🚀 **PHASE 2: LANCEMENT LUNDI MATIN (8h-9h EST / 14h-15h CET)**

### ✅ 1. Préparation Environnement

```bash
# Lancer Sierra Chart (si pas déjà lancé)
# Vérifier connexion DTC active
# Vérifier compte trading connecté
```

### ✅ 2. Test 1 Tick (OBLIGATOIRE)

```bash
# Lancer le bot en mode test:
cd D:\MIA_IA_system
python LAUNCH/launch_ml_v3_production.py

# ATTENDRE 2-3 MINUTES

# Vérifier dans logs:
[ ] "Stabilisation 30s..."
[ ] "ES: TP 16t / SL 12t"
[ ] "NQ: TP 23t / SL 12t"
[ ] "Fees: 1.40 USD (0.12t ES, 0.28t NQ)"
```

### ✅ 3. Observer Premier Signal

**Quand un signal arrive:**

```
[ ] Vérifier dans Sierra Chart DOM:
    - TP apparaît (ES: entry + 4.00, NQ: entry + 5.75)
    - SL apparaît (ES: entry - 3.00, NQ: entry - 3.00)

[ ] Vérifier notification Discord:
    - Direction: LONG ou SHORT (pas UNKNOWN!)
    - Entry price
    - TP/SL prices
    - Confluence score

[ ] Observer l'exit:
    - Noter exit_reason dans logs
    - Vérifier P&L calculé correctement
```

### ✅ 4. Validation (Si OK après 1er trade)

```bash
# Si tout OK:
[ ] Laisser tourner pour la journée
[ ] Monitorer toutes les 2-3 heures
[ ] Vérifier logs Discord

# Si problème:
[ ] ARRÊTER immédiatement (Ctrl+C)
[ ] Noter l'erreur exacte
[ ] Me contacter pour diagnostic
```

---

## 📊 **PHASE 3: MONITORING QUOTIDIEN (Lundi-Vendredi)**

### ✅ 1. Matin (9h EST / 15h CET)

```bash
# Vérifier bot actif:
[ ] Processus Python tourne
[ ] Logs récents < 5 minutes
[ ] Pas d'erreurs critiques

# Vérifier connexions:
[ ] Sierra Chart connecté
[ ] DTC actif
[ ] MenthorQ data flowing
```

### ✅ 2. Midi (12h EST / 18h CET)

```bash
# Vérifier performance matinale:
[ ] Nombre de trades ES/NQ
[ ] P&L en cours
[ ] Aucune anomalie (trades fantômes, doublons)
```

### ✅ 3. Soir (16h30 EST / 22h30 CET)

```bash
# Générer résumé quotidien:
cd D:\MIA_IA_system
python ml/discord_daily_logger.py

# Vérifier:
[ ] P&L du jour par symbole
[ ] WinRate
[ ] Exit breakdown (TP/SL/Reversal/Timeout)
[ ] Meilleur/Pire trade

# Sauvegarder logs:
[ ] Copier LAUNCH/daily_trades.json (backup quotidien)
```

---

## 🎯 **PHASE 4: ANALYSE SAMEDI (Fin de semaine 1)**

### ✅ 1. Analyse Complète

```bash
# Lancer analyse hebdomadaire:
cd D:\MIA_IA_system
python ml/weekly_analysis_tool.py

# Examiner:
[ ] P&L total ES vs NQ
[ ] WinRate ES vs NQ
[ ] Profit Factor ES vs NQ
[ ] Sharpe Ratio
[ ] Max Drawdown
[ ] Exit breakdown par symbole
[ ] Consistance jour par jour
```

### ✅ 2. Dashboard Visuel

```bash
# Générer dashboard:
python ml/dashboard_es_vs_nq.py

# Analyser:
[ ] Courbes P&L cumulé
[ ] Distribution horaire
[ ] Comparaison métriques
```

### ✅ 3. Décision Semaine 2

**Si ES surperforme NQ (score > 4/6):**
```
→ Semaine 2: Focus ES
→ Augmenter taille ES, réduire NQ
```

**Si NQ surperforme ES (score > 4/6):**
```
→ Semaine 2: Focus NQ
→ Augmenter taille NQ, réduire ES
```

**Si performances équivalentes:**
```
→ Semaine 2: Garder les deux
→ Diversification bénéfique
```

---

## 🚨 **ALERTES À SURVEILLER**

### ❌ Arrêter IMMÉDIATEMENT si:

```
[ ] Trades fantômes (ordres non demandés)
[ ] Doublons (2 positions ouvertes en même temps)
[ ] OCO cassé (TP ET SL restent après fill)
[ ] P&L incohérent (calculs faux)
[ ] Pertes > -50 ticks par jour
[ ] Drawdown > -100 ticks cumulé
```

### ⚠️ Investiguer si:

```
[ ] WinRate < 40% (attendu: 45-50%)
[ ] P&L/trade < +0.5t (attendu: +1.8t ES, +2.0t NQ)
[ ] Exit breakdown: > 20% TP/SL hit (attendu: < 5%)
[ ] Timeout > 60% (attendu: 90-95%)
```

---

## 📞 **CONTACTS URGENCE**

**En cas de problème critique:**

1. **STOP immédiat:** `Ctrl+C` dans terminal
2. **Fermer positions manuelles** dans Sierra Chart
3. **Sauvegarder logs:**
   ```bash
   copy LAUNCH\daily_trades.json LAUNCH\emergency_backup.json
   copy logs\*.log logs\emergency_backup\
   ```
4. **Noter l'erreur exacte** (screenshot + texte)
5. **Me contacter** avec détails

---

## ✅ **VALIDATION FINALE DIMANCHE**

```
Configuration:
[ ] ACTIVE_SYMBOLS = ["ES", "NQ"]
[ ] TP_OPTIMAL = {ES: 16, NQ: 23}
[ ] base_sl_ticks = {ES: 12, NQ: 12}
[ ] use_fixed_tp_sl = True
[ ] fees = 1.40 USD (0.12t ES, 0.28t NQ)

Tests:
[ ] Syntaxe Python OK (py_compile)
[ ] Sierra Chart connecté
[ ] DTC actif
[ ] Compte trading OK

Outils:
[ ] weekly_analysis_tool.py prêt
[ ] dashboard_es_vs_nq.py prêt
[ ] discord_daily_logger.py prêt

Mental:
[ ] Confiant dans la config
[ ] Prêt à monitorer quotidiennement
[ ] Prêt à arrêter si problème
```

---

## 🏆 **OBJECTIFS SEMAINE 1**

### **Objectifs Primaires:**
```
✅ Zéro erreur critique (pas de crash)
✅ Zéro trade fantôme
✅ OCO fonctionnel à 100%
✅ P&L/trade > +0.5 ticks (seuil minimal)
```

### **Objectifs Secondaires:**
```
🎯 ES: +1.8 t/trade (objectif validé par backtest)
🎯 NQ: +2.0 t/trade (objectif validé par backtest)
🎯 WinRate: 45-50%
🎯 Profit Factor: > 1.5
```

### **Objectifs Tertiaires:**
```
📊 Identifier symbole le plus performant
📊 Comprendre exit breakdown réel
📊 Valider exit anticipée vs TP/SL
📊 Optimiser configuration pour semaine 2
```

---

## 🎯 **MENTALITÉ**

```
✅ Cette semaine est un TEST, pas un sprint
✅ L'objectif est d'APPRENDRE, pas de tout gagner
✅ Mieux vaut un petit gain propre qu'un gros gain sale
✅ Monitoring > Performance
✅ Stabilité > Profit maximal
```

---

## 📅 **TIMELINE COMPLÈTE**

```
Dimanche 20h-22h:  Vérification config
Lundi 8h-9h:       Lancement + Test 1 tick
Lundi 9h-16h:      Production jour 1
Lundi 16h30:       Résumé Discord
Mardi-Vendredi:    Monitoring quotidien
Samedi 10h-12h:    Analyse complète semaine 1
Samedi 14h:        Décision semaine 2
```

---

## ✅ **SIGNATURE**

```
[ ] J'ai lu TOUTE la checklist
[ ] J'ai compris les objectifs
[ ] Je suis prêt à lancer lundi
[ ] Je sais quand arrêter (alertes)
[ ] J'ai les outils d'analyse prêts

Date: _______________
Signature: _______________
```

---

**🚀 ON EST PRÊT ! LUNDI C'EST PARTI !**







