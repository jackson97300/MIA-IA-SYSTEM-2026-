# 📊 ROUTINE DE REVUE DE SESSION - GUIDE COMPLET

## 🎯 OBJECTIF

Analyser **chaque session de trading** de manière systématique pour:
- Identifier les patterns gagnants et perdants
- Ajuster les paramètres en continu
- Améliorer les performances jour après jour
- Capitaliser sur les leçons apprises

---

## 📁 STRUCTURE DES DOSSIERS

```
REVUE_DE_SESSION/
├── README_ROUTINE_REVUE_SESSION.md          (ce fichier)
├── PROMPT_FIN_SESSION_ULTRA_COMPLET.md      (prompt à envoyer à Claude)
│
├── 2025/
│   └── DECEMBRE/
│       ├── 01/                               (Analyses du 01 décembre)
│       │   ├── ANALYSE_SESSION_*.txt
│       │   ├── ANALYSE_DETAILLEE_*.md
│       │   ├── CHANGEMENTS_URGENTS_*.md
│       │   └── analysis_session_*.py
│       │
│       ├── 02/                               (Analyses du 02 décembre)
│       │   ├── ANALYSE_SESSION_02DEC2025_2323.txt
│       │   ├── ANALYSE_DETAILLEE_BE_TRAILING_02DEC.md
│       │   ├── CHANGEMENTS_URGENTS_A_APPLIQUER.md
│       │   └── analysis_session_complete_02dec.py
│       │
│       └── 03/                               (À créer pour le 03 décembre)
│
└── TEMPLATES/                                (Templates réutilisables)
    ├── template_analyse.py
    └── template_rapport.md
```

---

## 🚀 PROCÉDURE QUOTIDIENNE (FIN DE SESSION)

### ⏰ QUAND FAIRE LA REVUE ?

**À la fin de chaque session de trading**, typiquement:
- **22:00 - 22:30** (après fermeture US)
- **Ou dès que le bot s'arrête** (kill switch, objectif atteint, etc.)

---

### 📋 ÉTAPE 1: PRÉPARER LES DONNÉES

#### A. Vérifier que les logs sont complets

```powershell
# Depuis D:\MIA_IA_system

# 1. Vérifier logs de trades
Get-Content logs_advanced\trades\trades_$(Get-Date -Format "yyyyMMdd").log -Tail 20

# 2. Vérifier logs de signaux
Get-Content logs_advanced\signals\signals_$(Get-Date -Format "yyyyMMdd").log -Tail 20

# 3. Compter le nombre de trades
$date = Get-Date -Format "yyyyMMdd"
(Get-Content "logs_advanced\trades\trades_$date.log" | Select-String "ENTRY").Count
```

#### B. Créer le dossier du jour

```powershell
# Créer dossier pour aujourd'hui (exemple: 03 décembre)
$jour = Get-Date -Format "dd"
mkdir "REVUE_DE_SESSION\2025\DECEMBRE\$jour"
```

---

### 📋 ÉTAPE 2: LANCER L'ANALYSE AVEC CLAUDE

#### A. Ouvrir le prompt

1. Ouvrir le fichier: `REVUE_DE_SESSION\PROMPT_FIN_SESSION_ULTRA_COMPLET.md`
2. **COPIER TOUT LE CONTENU** du prompt

#### B. Envoyer à Claude

1. Ouvrir une **nouvelle conversation** avec Claude dans Cursor
2. **COLLER le prompt complet**
3. Attendre que Claude génère les 3 documents:
   - ✅ `ANALYSE_SESSION_[DATE].txt` - Rapport statistique
   - ✅ `ANALYSE_DETAILLEE_[SUJET]_[DATE].md` - Analyse approfondie
   - ✅ `CHANGEMENTS_URGENTS_A_APPLIQUER.md` - Actions concrètes

#### C. Informations à fournir en plus du prompt (si demandé)

Claude peut demander des infos complémentaires. Fournir:

```
1. Date de la session: [JJ/MM/AAAA]
2. Heure début/fin: [HH:MM - HH:MM]
3. Symboles tradés: ES, NQ, RTY (ou seulement certains)
4. Événements spéciaux: (annonces éco, volatilité exceptionnelle, bugs, etc.)
5. Modifications récentes: (changements de config dans les 24h)
6. Objectif de la session: (test, production, calibration)
```

---

### 📋 ÉTAPE 3: RANGER LES DOCUMENTS GÉNÉRÉS

Une fois que Claude a terminé l'analyse:

```powershell
# Déplacer tous les fichiers d'analyse vers le dossier du jour
$jour = Get-Date -Format "dd"
$mois = "DECEMBRE"
$annee = "2025"

# Déplacer les fichiers
Move-Item "ANALYSE_SESSION_*.txt" "REVUE_DE_SESSION\$annee\$mois\$jour\"
Move-Item "ANALYSE_DETAILLEE_*.md" "REVUE_DE_SESSION\$annee\$mois\$jour\"
Move-Item "CHANGEMENTS_URGENTS_*.md" "REVUE_DE_SESSION\$annee\$mois\$jour\"
Move-Item "analysis_session_*.py" "REVUE_DE_SESSION\$annee\$mois\$jour\"
```

---

### 📋 ÉTAPE 4: LIRE LES RECOMMANDATIONS

#### A. Commencer par l'Executive Summary

Ouvrir `CHANGEMENTS_URGENTS_A_APPLIQUER.md` et lire:
1. **🔴 PRIORITÉ P0** - À faire **MAINTENANT** (avant prochaine session)
2. **🟡 PRIORITÉ P1** - À faire cette semaine
3. **🟢 PRIORITÉ P2** - À faire plus tard

#### B. Analyser les tableaux

Ouvrir `ANALYSE_SESSION_[DATE].txt` et regarder:
- Win Rate global et par symbole
- Performance par heure
- Top problèmes identifiés
- Raisons de sortie (SL, TP, BE, Trailing)

#### C. Approfondir si nécessaire

Ouvrir `ANALYSE_DETAILLEE_*.md` pour:
- Exemples de trades précis
- Calculs d'impact détaillés
- Recommandations de configuration

---

### 📋 ÉTAPE 5: APPLIQUER LES CHANGEMENTS P0

#### A. Identifier les fichiers à modifier

Le document `CHANGEMENTS_URGENTS_A_APPLIQUER.md` indique:
- Quel fichier modifier (ex: `config/unified_thresholds.py`)
- Quelle ligne (ex: ligne ~150)
- Quoi changer exactement (code fourni en copier/coller)

#### B. Appliquer les modifications

**IMPORTANT**: Faire les changements **UN PAR UN** et **tester entre chaque**!

```powershell
# 1. Arrêter le bot si actif
Get-Process python | Stop-Process -Force

# 2. Faire UNE modification (ex: bloquer 16h)
# 3. Commiter le changement
git add .
git commit -m "REVUE 02DEC: Bloquer 16h (US Open) - Impact +$1650/jour"

# 4. Tester en mode SIMULATION
# Modifier LIVE_TRADING = False dans launch_production_CLEAN_v2.py
python LAUNCH/launch_production_CLEAN_v2.py

# 5. Observer 30 minutes
# 6. Si OK, passer au changement suivant
```

#### C. Créer un récapitulatif des changements appliqués

```powershell
# Créer un fichier de suivi
$jour = Get-Date -Format "dd"
$fichier = "REVUE_DE_SESSION\2025\DECEMBRE\$jour\CHANGEMENTS_APPLIQUES.md"

# Y noter:
# - [ ] P0.1 - Bloquer 16h - FAIT (02/12 23:45) - Impact: +$1650/jour
# - [ ] P0.2 - SL minimum +5t/+10t - EN COURS
# - [ ] P0.3 - Kill Switch à 4 - À FAIRE
# - [ ] P0.4 - Désactiver BE - À FAIRE
```

---

### 📋 ÉTAPE 6: VALIDER EN SIMULATION

Avant de repasser en LIVE:

```powershell
# Lancer en mode TEST
# (LIVE_TRADING = False dans launch_production_CLEAN_v2.py)
python LAUNCH/launch_production_CLEAN_v2.py

# Observer pendant 1-2 heures:
# ✅ Les nouveaux filtres fonctionnent ?
# ✅ Les trades sont acceptés/rejetés correctement ?
# ✅ Pas d'erreurs Python ?
# ✅ Performance cohérente avec les attentes ?
```

---

### 📋 ÉTAPE 7: REPASSER EN LIVE

Une fois validé en simulation:

```powershell
# 1. Arrêter le bot test
Get-Process python | Stop-Process -Force

# 2. Modifier LIVE_TRADING = True
# 3. Commiter
git add .
git commit -m "REVUE 02DEC: Passage en LIVE après validation P0"

# 4. Relancer en LIVE
python LAUNCH/launch_production_CLEAN_v2.py
```

---

### 📋 ÉTAPE 8: SUIVRE LES RÉSULTATS (J+1)

Le lendemain, comparer:

```powershell
# Créer un fichier de comparaison
$hier = (Get-Date).AddDays(-1).ToString("dd")
$aujourd_hui = Get-Date -Format "dd"

# Y noter:
# Session AVANT corrections (J-1):
# - Trades: X
# - Win Rate: Y%
# - P&L: $Z
#
# Session APRÈS corrections (J):
# - Trades: A
# - Win Rate: B%
# - P&L: $C
#
# Amélioration: +/- $D (+/-X%)
```

---

## 📊 MÉTRIQUES À SUIVRE (HEBDOMADAIRE)

Chaque **dimanche**, créer un récapitulatif hebdomadaire:

### A. Créer le dossier semaine

```powershell
mkdir "REVUE_DE_SESSION\2025\DECEMBRE\SEMAINE_01"  # 01-07 déc
mkdir "REVUE_DE_SESSION\2025\DECEMBRE\SEMAINE_02"  # 08-14 déc
# etc.
```

### B. Analyser l'évolution

Créer `REVUE_HEBDO_SEMAINE_XX.md` avec:

```markdown
# REVUE HEBDOMADAIRE - SEMAINE 01 (01-07 DÉC 2025)

## 📊 MÉTRIQUES GLOBALES

| Jour | Trades | WR% | P&L | Changements |
|------|--------|-----|-----|-------------|
| Lun 01 | 95 | 38% | +$1200 | Baseline |
| Mar 02 | 101 | 42% | +$3055 | Aucun |
| Mer 03 | 78 | 51% | +$5200 | P0 appliqués |
| Jeu 04 | 82 | 49% | +$4800 | - |
| Ven 05 | 71 | 54% | +$6100 | P1 appliqués |
| Sam 06 | 65 | 56% | +$6500 | - |
| Dim 07 | - | - | - | Repos |

**TOTAUX:**
- Trades: 492
- Win Rate moyen: 48.3%
- P&L total: +$26,855
- P&L moyen/jour: +$4,476

## 📈 ÉVOLUTION

- Amélioration WR: +18% (de 38% à 56%)
- Amélioration P&L: +442% (de $1200 à $6500)
- Réduction overtrading: -32% (de 95 à 65 trades/jour)

## ✅ CHANGEMENTS RÉUSSIS

1. Bloquer 16h → +$1650/jour confirmé
2. SL minimum → +$700/jour confirmé
3. Confidence > 0.80 → +$260/jour + réduction overtrading

## 🔄 CHANGEMENTS À TESTER SEMAINE PROCHAINE

1. Favoriser 19h (position sizing x1.5)
2. Désactiver ES SHORT (WR toujours <35%)
3. Ajouter filtre tendance HVL+VWAP
```

---

## 🛠️ OUTILS DISPONIBLES

### Script d'analyse automatique

Le script `analysis_session_complete_02dec.py` peut être réutilisé:

```powershell
# Copier le template
Copy-Item "REVUE_DE_SESSION\2025\DECEMBRE\02\analysis_session_complete_02dec.py" `
          "REVUE_DE_SESSION\TEMPLATES\template_analyse.py"

# Pour analyser une nouvelle session:
$date = Get-Date -Format "yyyyMMdd"
python REVUE_DE_SESSION\TEMPLATES\template_analyse.py --date $date
```

### Analyseurs intégrés

Les analyseurs du projet sont disponibles:
- `core/session_analyzer.py` - Analyse VIX, sessions, hot zones
- `execution/post_mortem_analyzer.py` - Post-mortem trades
- `core/rejection_diagnostic_logger.py` - Diagnostic rejets
- `core/lessons_learned_analyzer.py` - Leçons apprises

---

## 📋 CHECKLIST QUOTIDIENNE (RÉSUMÉ)

### Fin de session (22:00-22:30)
- [ ] Vérifier logs complets
- [ ] Créer dossier du jour
- [ ] Copier prompt `PROMPT_FIN_SESSION_ULTRA_COMPLET.md`
- [ ] Coller dans Claude + fournir infos session
- [ ] Attendre génération des 3 documents
- [ ] Ranger documents dans dossier du jour
- [ ] Lire Executive Summary + recommandations P0
- [ ] Décider: appliquer P0 maintenant ou demain matin?

### Lendemain matin (avant reprise trading)
- [ ] Appliquer changements P0 un par un
- [ ] Tester en SIMULATION (1-2h)
- [ ] Valider résultats
- [ ] Repasser en LIVE
- [ ] Créer fichier CHANGEMENTS_APPLIQUES.md

### Dimanche (revue hebdomadaire)
- [ ] Créer REVUE_HEBDO_SEMAINE_XX.md
- [ ] Calculer métriques globales semaine
- [ ] Analyser évolution jour par jour
- [ ] Valider impact des changements
- [ ] Planifier actions semaine prochaine

---

## 🎯 OBJECTIFS DE LA ROUTINE

### Court terme (semaine)
- Win Rate > 50%
- P&L > +$5000/semaine
- Réduction overtrading (60-80 trades/jour max)
- Pas de drawdown > $500

### Moyen terme (mois)
- Win Rate stable > 55%
- P&L > +$20,000/mois
- Profit Factor > 2.0
- Système autonome (peu d'interventions)

### Long terme (trimestre)
- Stratégie optimisée et stable
- Paramètres auto-adaptatifs (ML)
- Win Rate > 60%
- Scalabilité (multi-comptes)

---

## ⚠️ RÈGLES D'OR

1. **NE JAMAIS sauter une revue quotidienne** - C'est le cœur de l'amélioration continue!
2. **NE PAS tout changer d'un coup** - Appliquer P0, observer, puis P1, puis P2
3. **TOUJOURS tester en simulation** avant LIVE
4. **COMMITER chaque changement** avec message explicite (git)
5. **DOCUMENTER les résultats** pour suivre l'évolution
6. **RESTER DISCIPLINÉ** - Suivre les recommandations même si difficile

---

## 📞 EN CAS DE PROBLÈME

### Si Claude ne génère pas les bons documents:
1. Vérifier que le prompt est complet (tout copié)
2. Fournir les infos complémentaires demandées
3. Relancer l'analyse avec plus de détails

### Si les changements ne fonctionnent pas:
1. Vérifier que le code est correct (copier/coller exact)
2. Vérifier les logs d'erreur Python
3. Revenir à la version précédente (git checkout)
4. Demander à Claude d'analyser le problème

### Si les performances se dégradent:
1. Comparer avec session précédente (quoi a changé?)
2. Vérifier les conditions de marché (VIX, événements)
3. Rollback temporaire des changements récents
4. Faire une revue approfondie avec Claude

---

## 📚 RESSOURCES

### Fichiers clés:
- `REVUE_DE_SESSION/PROMPT_FIN_SESSION_ULTRA_COMPLET.md` - Prompt à utiliser
- `REVUE_DE_SESSION/README_ROUTINE_REVUE_SESSION.md` - Ce guide
- `REVUE_DE_SESSION/TEMPLATES/` - Templates réutilisables

### Logs à analyser:
- `logs_advanced/trades/trades_YYYYMMDD.log` - Tous les trades
- `logs_advanced/signals/signals_YYYYMMDD.log` - Signaux générés
- `logs_advanced/discord/discord_YYYYMMDD.log` - Notifications Discord

### Configurations à ajuster:
- `config/unified_thresholds.py` - Seuils ML
- `LAUNCH/launch_production_CLEAN_v2.py` - Config principale
- `core/session_quality_monitor.py` - Sessions/hot zones

---

**🎯 OBJECTIF FINAL: Système de trading qui s'améliore automatiquement chaque jour grâce à l'analyse systématique!**

✅ **Routine installée et opérationnelle!**


