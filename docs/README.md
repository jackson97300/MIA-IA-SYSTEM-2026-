# 🤖 MIA IA TRADING SYSTEM

## Bot de Trading Algorithmique - Futures US (ES, NQ, RTY)

---

## 📋 Description

MIA_IA_system est un système de trading automatisé professionnel utilisant:
- **MenthorQ** pour l'analyse des niveaux gamma/options
- **ML 3-Layer** pour la validation des signaux
- **Sierra Chart** comme broker via protocole DTC
- **Discord** pour les notifications temps réel

---

## 🚀 Démarrage Rapide

```powershell
# 1. Se placer dans le dossier
cd D:\MIA_IA_system

# 2. Lancer le bot
python LAUNCH/launch_production_CLEAN_v2.py

# 3. Vérifier qu'il tourne
Get-Process python
```

---

## 📁 Structure du Projet

Voir `docs/STRUCTURE_PROJET_MIA.md` pour la structure détaillée.

**Dossiers principaux:**
- `LAUNCH/` - Lanceur principal
- `core/` - Modules core
- `ml/` - Machine Learning
- `strategies/` - Stratégies
- `execution/` - Exécution ordres
- `monitoring/` - Discord
- `config/` - Configuration

---

## 🧠 Architecture ML 3-Layer

| Layer | Poids | Composants |
|-------|-------|------------|
| MenthorQ | 50% | Gamma, GEX, Blind Spots, Next Wall |
| OrderFlow | 30% | Delta, Volume, DOM, Pressure |
| Context | 20% | VWAP, Value Area, Structure |

**Seuil minimum:** 35% confidence

---

## 🕐 Sessions de Trading (Paris)

| Session | Horaires |
|---------|----------|
| London | 08:00 - 11:00 |
| US Morning | 15:50 - 17:00 |
| US Power Hour | 20:00 - 21:30 |

---

## 🛡️ Protections

- ✅ VIX Regime Filtering (stop si VIX ≥ 35)
- ✅ Economic Calendar (FOMC, NFP, CPI)
- ✅ Session Quality Monitor
- ✅ Risk Manager
- ✅ Safety Kill Switch

---

## 📊 Fichiers Critiques

| Fichier | Description |
|---------|-------------|
| `LAUNCH/launch_production_CLEAN_v2.py` | Lanceur principal |
| `config/unified_thresholds.py` | Seuils ML |
| `ml/ml_3layer_filter.py` | Cœur ML |

---

## 📝 Notes

- Backup fait le 29/11/2025
- Anciens fichiers dans `ARCHIVE/`
- Documentation dans `docs/`

---

## ⚡ Performance (30 Nov 2025)

| Métrique | Valeur | Statut |
|----------|--------|--------|
| Latence cycle | **89ms** | ✅ |
| Tests pytest | **39/39** | ✅ |
| DTC Connection | **LIVE** | ✅ |
| Modules | **27/27** | ✅ |
| Code Quality | **7.3/10** | ✅ |

**Optimisations appliquées:** -35ms latence totale
- Snapshots parallèles: -20ms
- Cache LRU: -10ms
- Variables locales: -5ms

---

## 📚 Documentation Complète

- **`.cursorrules`** - Instructions pour Claude/Cursor AI
- **`CLAUDE/INDEX_DOCUMENTATION.md`** - Index complet de la documentation
- **`CLAUDE/RESUME_RAPIDE_30NOV.md`** - Résumé 1 page session
- **`CLAUDE/SESSION_30NOV_OPTIMISATIONS_COMPLETE.md`** - Rapport complet

### Guides Techniques
- `MENTHORQ_GUIDE.md` - MenthorQ, Gamma Walls, GEX
- `OPTIONS_FLOW_GUIDE.md` - Options flow, dealer hedging
- `ORDERFLOW_GUIDE.md` - Order Flow, Delta, DOM
- `TRADING_RULES.md` - Règles strictes entry/exit
- `SNAPSHOT_REFERENCE.md` - Structure snapshot JSON

---

*Version: CLEAN v2.0 - 30 Novembre 2025*
