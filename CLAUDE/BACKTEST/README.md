# 🔬 BACKTEST ES PURE V2.3 - 17 JOURS COMPLET

## 📦 Package Complet pour Cursor

Ce package contient tout ce qu'il faut pour backtester la stratégie ES Pure MenthorQ V2.3 sur 17 jours de données (5-27 Novembre 2025).

---

## 📋 Fichiers Inclus

1. **run_backtest_17_days.py** - Script principal à exécuter
2. **backtester_es_pure_v2.py** - Engine de backtest
3. **es_pure_menthorq_v2.py** - Stratégie ES Pure V2.3 (OrderFlow STRICT)
4. **README.md** - Ce fichier

---

## 🚀 INSTALLATION RAPIDE

### Étape 1 : Créer un Dossier

Dans Cursor, crée un nouveau dossier pour le projet :

```
D:\Trading\ES_Backtest_V2.3\
```

### Étape 2 : Copier les Fichiers

Place les 3 fichiers Python dans ce dossier :
- `run_backtest_17_days.py`
- `backtester_es_pure_v2.py`
- `es_pure_menthorq_v2.py`

### Étape 3 : Ouvrir dans Cursor

Ouvre le dossier `D:\Trading\ES_Backtest_V2.3\` dans Cursor.

---

## ⚙️ CONFIGURATION

**IMPORTANT** : Vérifie que le chemin vers tes données est correct dans `run_backtest_17_days.py` :

```python
# Ligne 25 du fichier
BASE_PATH = Path(r"D:\MIA_IA_system\DATA_SIERRA_CHART\DATA_2025\NOVEMBRE")
```

Si ton dossier est ailleurs, modifie cette ligne.

---

## ▶️ EXÉCUTION

### Dans Cursor :

1. **Ouvre le Terminal** : `Ctrl + ù` ou Menu > Terminal > New Terminal

2. **Lance le script** :
   ```bash
   python run_backtest_17_days.py
   ```

3. **Attends les résultats** (environ 2-5 minutes pour 17 jours)

---

## 📊 RÉSULTATS

Le script génère :

### 1. **Console Output**
- Résultats jour par jour
- Stats globales finales
- Win Rate, P&L, Profit Factor, etc.

### 2. **Rapport HTML**
- Fichier : `BACKTEST_REPORT_17_DAYS_ES_V2.3.html`
- Tableaux détaillés par jour, setup, session
- Visualisations claires
- Ouvre-le dans ton navigateur

---

## 🎯 CE QUI EST TESTÉ

### Stratégie : **ES Pure MenthorQ V2.3**

**Optimisations V2.3 :**
- ✅ OrderFlow = VALIDATEUR STRICT (rejette si non confirmé)
- ✅ Seuil OrderFlow : 0.60 (strict)
- ✅ SL : 16 ticks
- ✅ BE Trigger : 7 ticks
- ✅ Trail Activation : 10 ticks
- ✅ Near Level : 8 ticks
- ❌ hvl_magnet DÉSACTIVÉ (0% WR)

**EDGE :**
- MenthorQ (Options) = LEADER → Propose les niveaux
- OrderFlow = VALIDATEUR → Confirme OU REJETTE

**Setups Actifs :**
1. GAMMA_WALL_DEFENSE (fade aux GEX 1-10, Call Res, Put Sup)
2. VWAP_REVERSION (retour au VWAP)
3. BREAKOUT (break de niveau avec volume)
4. PULLBACK_CLEAN (pullback propre)

---

## 📈 RÉSULTATS ATTENDUS (1 jour test)

Sur le jour du 24 Nov (test) :
- **Win Rate : 75%** (6W / 2L)
- **P&L : -$31.50** (quasi breakeven)
- **Profit Factor : 0.92**
- **Max DD : -$231**

Le test sur 17 jours permettra de valider si ces résultats sont reproductibles.

---

## 🔧 DÉPANNAGE

### Erreur : "Le chemin n'existe pas"
→ Vérifie le `BASE_PATH` ligne 25 de `run_backtest_17_days.py`

### Erreur : "Module not found"
→ Les 3 fichiers .py doivent être dans le MÊME dossier

### Erreur : "Permission denied"
→ Lance Cursor en tant qu'Administrateur

### Pas de fichiers pour certaines dates
→ Normal si tu n'as pas tradé ces jours-là, le script les skip automatiquement

---

## 📞 SUPPORT

En cas de problème, vérifie :
1. Les 3 fichiers .py sont bien dans le même dossier
2. Le chemin `BASE_PATH` est correct
3. Les fichiers JSONL existent dans `DATA_2025\NOVEMBRE\{date}\CHART_3\ML_READY\`

---

## 🎉 PROCHAINES ÉTAPES

Après avoir lancé le backtest :

1. **Analyse les résultats HTML**
2. **Vérifie le Win Rate** (objectif > 65%)
3. **Vérifie le Profit Factor** (objectif > 1.2)
4. **Analyse les sessions** (London vs US)
5. **Vérifie les setups** (gamma_wall_defense devrait être le top)

Si les résultats sont bons :
- ✅ **Passer au LIVE SIM** avec ces paramètres
- ✅ Tester sur **NQ** avec les mêmes principes
- ✅ Ajouter **filtres supplémentaires** si nécessaire

---

**Auteur** : Jackson  
**Date** : 27 Novembre 2025  
**Version** : ES Pure MenthorQ V2.3 - OrderFlow STRICT

🔥 **Bon backtest !** 🚀
