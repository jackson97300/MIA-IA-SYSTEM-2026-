# 🌐 DASHBOARD NIVEAUX - GUIDE RAPIDE

## 📺 C'EST UN SITE WEB LOCAL!

Le dashboard Streamlit est un **site web** qui tourne sur votre machine.

### Lancement

**Double-cliquer sur:**
```
LANCER_DASHBOARD_NIVEAUX.bat
```

**Ou en ligne de commande:**
```powershell
cd D:\MIA_IA_system
python -m streamlit run core/dashboard_niveaux_multi_symbols.py
```

### Accès

Une fois lancé, ouvrez votre navigateur web (Chrome, Firefox, Edge) et allez à:

```
http://localhost:8501
```

Le site s'affichera automatiquement !

### Fonctionnalités

✅ **Sélection symbole** : ES / NQ / RTY dans la sidebar
📍 **Niveaux tradables** : Liste triée par distance
💎 **Confluences** : Zones avec 3+ niveaux groupés
🔄 **Auto-refresh** : Mise à jour automatique toutes les 3s
📊 **Dark theme** : Interface professionnelle sombre

### Interface

```
┌─────────────────────────────────────────┐
│  🎯 DASHBOARD NIVEAUX TEMPS RÉEL       │
│                                         │
│  📗 ES    ✅ Tradables   ⚠️ Proches    │
│  6856.63       2             5          │
│                                         │
│  📍 NIVEAUX LES PLUS PROCHES            │
│  ─────────────────────────────────────  │
│  BL_2    6855.65   4t ↓    ✅ TRADABLE │
│  GEX_1   6850.00   26t ↓   ⚠️ PROCHE   │
│  HVL     6825.00   127t ↓  ❌ LOIN     │
└─────────────────────────────────────────┘
```

### Arrêter le dashboard

- Appuyez sur `Ctrl+C` dans la fenêtre du terminal
- Ou fermez simplement la fenêtre du terminal

---

## 🖥️ MONITEUR LOGS (Alternative sans navigateur)

Si vous préférez voir les niveaux dans la console (sans navigateur) :

**Lancer:**
```
LANCER_MONITEUR_NIVEAUX.bat
```

**Sortie console toutes les 10 secondes:**
```
============================================================
📗 [ES] Prix: 6856.63
  Niveaux tradables: 2 (≤15t)
  📍 TOP 5 NIVEAUX TRADABLES:
     🔽 BL_2          @ 6855.65 (  4.0t)
     🔽 GEX_1         @ 6850.00 ( 26.0t)
============================================================
```

---

## ⚠️ Troubleshooting

### "Module streamlit not found"
```powershell
python -m pip install streamlit plotly
```

### Port 8501 déjà utilisé
```powershell
# Changer le port
python -m streamlit run core/dashboard_niveaux_multi_symbols.py --server.port 8502
```

### Aucun snapshot trouvé
- Vérifiez que le bot tourne
- Vérifiez que `DATA_SIERRA_CHART/DATA_2025/DECEMBRE/20251210/` existe

---

**Le dashboard tourne en parallèle du bot sans le perturber !** 🚀
