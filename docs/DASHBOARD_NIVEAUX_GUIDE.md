# 📊 DASHBOARD & MONITEUR NIVEAUX - MIA Trading Bot

## 🎯 Description

Deux outils pour suivre les niveaux MenthorQ en temps réel pendant le trading :

1. **Dashboard Streamlit** (Interface Web)
2. **Moniteur Standalone** (Logs console + fichier)

---

## 📺 1. DASHBOARD STREAMLIT

### Lancement

```powershell
# Double-cliquer sur:
LANCER_DASHBOARD_NIVEAUX.bat

# Ou en ligne de commande:
cd D:\MIA_IA_system
streamlit run core/dashboard_niveaux_multi_symbols.py
```

### Accès

- **URL:** http://localhost:8501
- **Port:** 8501 (Streamlit par défaut)

### Fonctionnalités

- ✅ **Sélection symbole** : ES / NQ / RTY
- 📍 **Niveaux les plus proches** triés par distance
- 💎 **Détection confluences** (3+ niveaux groupés)
- 🎯 **Status tradable** selon `max_entry_distance`
- 🔄 **Auto-refresh** toutes les 3 secondes
- 🎨 **Dark theme** professionnel

### Captures

```
┌─────────────────────────────────────────────┐
│  🎯 DASHBOARD NIVEAUX TEMPS RÉEL           │
├─────────────────────────────────────────────┤
│                                             │
│  📗 ES Prix    ✅ Tradables   ⚠️ Proches   │
│    6852.75         2              5         │
│                                             │
├─────────────────────────────────────────────┤
│  📍 NIVEAUX LES PLUS PROCHES                │
│                                             │
│  Type       Prix      Distance    Status    │
│  ─────────────────────────────────────────  │
│  GEX_1     6850.00    11t ↓      ⚠️ PROCHE │
│  BL_6      6850.04    10.8t ↓    ⚠️ PROCHE │
│  HVL_0DTE  6855.00    10t ↑      ⚠️ PROCHE │
│  ...                                        │
└─────────────────────────────────────────────┘
```

---

## 🖥️ 2. MONITEUR STANDALONE

### Lancement

```powershell
# Double-cliquer sur:
LANCER_MONITEUR_NIVEAUX.bat

# Ou en ligne de commande:
cd D:\MIA_IA_system
python core/niveaux_monitor.py
```

### Fonctionnalités

- 📊 **Check toutes les 10 secondes**
- 📍 **Top 5 niveaux tradables** par symbole
- 🔔 **Alertes proximité** (≤5 ticks)
- 📈 **Résumé global** toutes les minutes
- 💾 **Logs dans fichier** : `logs/niveaux_monitor.log`

### Exemple de sortie

```
============================================================
📗 [ES] Prix: 6852.75
  Niveaux tradables: 2 (≤15t)
  📍 TOP 5 NIVEAUX TRADABLES:
     🔽 GEX_1          @ 6850.00 ( 11.0t)
     🔽 BL_6           @ 6850.04 ( 10.8t)

  🔔 ALERTES PROXIMITÉ (≤5t):
     🔽 GEX_1          @ 6850.00 ( 11.0t) ⚠️
============================================================
📘 [NQ] Prix: 25714.63
  Niveaux tradables: 0 (≤20t)
  ⚠️  AUCUN niveau tradable actuellement
============================================================
📊 RÉSUMÉ GLOBAL
============================================================
📗 ES  | Prix:  6852.75 | Tradables:  2 | Alertes:  1 ✅
📘 NQ  | Prix: 25714.63 | Tradables:  0 | Alertes:  0 ⚠️
📕 RTY | Prix:  2345.50 | Tradables:  3 | Alertes:  0 ✅
============================================================
```

---

## ⚙️ Configuration

### Distances Tradables (alignées avec bot)

| Symbole | Max Entry Distance | Tick Size |
|---------|-------------------|-----------|
| **ES** | 15 ticks | 0.25 |
| **NQ** | 20 ticks | 0.25 |
| **RTY** | 15 ticks | 0.10 |

### Ajuster les paramètres

**Dashboard :**
- `REFRESH_INTERVAL = 3` (secondes)
- Via sidebar : nombre de niveaux affichés

**Moniteur :**
- `CHECK_INTERVAL = 10` (secondes)
- `ALERT_THRESHOLD = 5` (ticks)

---

## 📁 Fichiers

```
MIA_IA_system/
├── core/
│   ├── dashboard_niveaux_multi_symbols.py  # Dashboard Streamlit
│   └── niveaux_monitor.py                  # Moniteur standalone
├── LANCER_DASHBOARD_NIVEAUX.bat            # Launcher dashboard
├── LANCER_MONITEUR_NIVEAUX.bat             # Launcher moniteur
└── logs/
    └── niveaux_monitor.log                 # Logs moniteur
```

---

## 🚀 Utilisation Recommandée

### Setup Dual-Screen

```
┌─────────────┬─────────────┐
│  Écran 1    │  Écran 2    │
├─────────────┼─────────────┤
│  Sierra     │  Dashboard  │
│  Chart      │  Streamlit  │
│             │             │
│  +          │  +          │
│             │             │
│  Terminal   │  Console    │
│  Bot        │  Moniteur   │
└─────────────┴─────────────┘
```

### Workflow

1. **Lancer le bot**
   ```
   LAUNCH/launch_production_CLEAN_v2.py
   ```

2. **Lancer le dashboard** (optionnel - visuel)
   ```
   LANCER_DASHBOARD_NIVEAUX.bat
   ```

3. **Lancer le moniteur** (recommandé - logs)
   ```
   LANCER_MONITEUR_NIVEAUX.bat
   ```

---

## 🔍 Niveaux Supportés

### Priorité Maximum (🔥)
- HVL (High Volume Level)
- HVL 0DTE
- VAH / VAL (Value Area)
- POC (Point of Control)
- 1D MAX / MIN

### Priorité Élevée (⭐)
- Call Resistance 0DTE
- Put Support 0DTE
- Gamma Wall 0DTE
- Gamma Walls (1-5)
- GEX Levels (1-10)
- Blind Spots (0-9)

---

## 📊 Source de Données

Les deux outils lisent les **snapshots ML_READY** :
- Chemin : `DATA_SIERRA_CHART/ml_ready/*.json`
- Format : Snapshots générés par le dumper C++
- Fréquence : Temps réel (mises à jour du bot)

---

## ⚠️ Troubleshooting

### "Aucun snapshot trouvé"

```powershell
# Vérifier que le dossier existe
dir DATA_SIERRA_CHART\ml_ready\

# Vérifier présence de fichiers récents
dir DATA_SIERRA_CHART\ml_ready\*ES*.json
```

### Dashboard ne se lance pas

```powershell
# Installer streamlit si manquant
pip install streamlit plotly
```

### Port 8501 déjà utilisé

```powershell
# Changer le port
streamlit run core/dashboard_niveaux_multi_symbols.py --server.port 8502
```

---

## 📝 Notes

- Les deux outils sont **indépendants** du bot
- Ils **lisent** les snapshots mais ne les modifient pas
- Peuvent tourner **en parallèle** sans conflit
- Consommation CPU négligeable

---

**Créé :** 10/12/2025
**Version :** 1.0
**Author :** MIA System + Claude Sonnet 4.5
