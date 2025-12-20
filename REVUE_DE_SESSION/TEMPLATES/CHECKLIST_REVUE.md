# 📋 CHECKLIST REVUE DE SESSION

**Date**: ___/___/2025
**Session**: ___h___ à ___h___
**Symboles**: ☐ ES  ☐ NQ  ☐ RTY

---

## ⏰ PRÉPARATION (5 min)

- [ ] Vérifier que les logs sont complets
- [ ] Créer dossier du jour: `REVUE_DE_SESSION\2025\[MOIS]\[JJ]`
- [ ] Copier `PROMPT_FIN_SESSION_ULTRA_COMPLET.md`

---

## 🤖 ANALYSE AVEC CLAUDE (15-20 min)

- [ ] Ouvrir nouvelle conversation Claude
- [ ] Coller le prompt complet
- [ ] Fournir infos complémentaires si demandé:
  - Date session: ___/___/___
  - Heure début/fin: ___:___ - ___:___
  - Événements spéciaux: _________________
  - Modifs récentes: _________________

- [ ] Attendre génération des 3 documents:
  - [ ] `ANALYSE_SESSION_*.txt`
  - [ ] `ANALYSE_DETAILLEE_*.md`
  - [ ] `CHANGEMENTS_URGENTS_*.md`

---

## 📁 RANGEMENT (2 min)

- [ ] Déplacer tous les fichiers vers dossier du jour
- [ ] Vérifier que tous les documents sont présents

---

## 📖 LECTURE RECOMMANDATIONS (10 min)

### Executive Summary
- [ ] Lire le problème principal identifié
- [ ] Lire la solution prioritaire
- [ ] Noter l'impact estimé: $___/jour

### Tableaux
- [ ] Win Rate global: ___%
- [ ] P&L session: $___
- [ ] Meilleure heure: ___h (+$___)
- [ ] Pire heure: ___h (-$___)

### Top 3 Problèmes
1. _________________ (-$___)
2. _________________ (-$___)
3. _________________ (-$___)

---

## 🔴 CHANGEMENTS P0 (À FAIRE MAINTENANT)

### Changement 1:
- [ ] Fichier: _________________
- [ ] Modification: _________________
- [ ] Impact: +$___/jour
- [ ] Status: ☐ Appliqué  ☐ Testé  ☐ Validé

### Changement 2:
- [ ] Fichier: _________________
- [ ] Modification: _________________
- [ ] Impact: +$___/jour
- [ ] Status: ☐ Appliqué  ☐ Testé  ☐ Validé

### Changement 3:
- [ ] Fichier: _________________
- [ ] Modification: _________________
- [ ] Impact: +$___/jour
- [ ] Status: ☐ Appliqué  ☐ Testé  ☐ Validé

### Changement 4:
- [ ] Fichier: _________________
- [ ] Modification: _________________
- [ ] Impact: +$___/jour
- [ ] Status: ☐ Appliqué  ☐ Testé  ☐ Validé

---

## 🧪 TESTS (30-60 min)

- [ ] Arrêter le bot: `Get-Process python | Stop-Process -Force`
- [ ] Modifier `LIVE_TRADING = False`
- [ ] Relancer en SIMULATION
- [ ] Observer 1-2 heures
- [ ] Vérifier:
  - [ ] Nouveaux filtres actifs
  - [ ] Trades acceptés/rejetés correctement
  - [ ] Pas d'erreurs Python
  - [ ] Performance cohérente

---

## ✅ VALIDATION & LIVE

- [ ] Tests concluants
- [ ] Modifier `LIVE_TRADING = True`
- [ ] Commit git: `git commit -m "REVUE [DATE]: [CHANGEMENTS]"`
- [ ] Relancer en LIVE
- [ ] Surveiller 1ère heure

---

## 🟡 CHANGEMENTS P1 (CETTE SEMAINE)

### Changement 1:
- [ ] _________________
- [ ] Planifié pour: ___/___

### Changement 2:
- [ ] _________________
- [ ] Planifié pour: ___/___

---

## 🟢 CHANGEMENTS P2 (PLUS TARD)

### Changement 1:
- [ ] _________________
- [ ] Planifié pour: ___/___

### Changement 2:
- [ ] _________________
- [ ] Planifié pour: ___/___

---

## 📊 SUIVI J+1

**À remplir le lendemain**

### Session AVANT corrections (J-1):
- Trades: ___
- Win Rate: ___%
- P&L: $___

### Session APRÈS corrections (J):
- Trades: ___
- Win Rate: ___%
- P&L: $___

### Amélioration:
- Trades: +/- ___
- Win Rate: +/- ___%
- P&L: +/- $___ (+/-___%)

### Validation:
- [ ] Amélioration confirmée
- [ ] Garder les changements
- OU
- [ ] Dégradation observée
- [ ] Rollback nécessaire

---

## 💬 NOTES LIBRES

_Observations, idées, questions pour Claude..._

---

**✅ Revue terminée le**: ___/___/___ à ___h___
**⏱️ Temps total**: ___ minutes
**🎯 Impact estimé**: +$___/jour


