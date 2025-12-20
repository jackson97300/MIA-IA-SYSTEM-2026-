# 📅 HORAIRES DE TRADING - MIA IA SYSTEM
## Configuration Production (Heure Paris)

---

## 🟢 SESSIONS AUTORISÉES (TRADE)

```
┌─────────────────────────────────────────────────────────────┐
│  🌅 LONDON SESSION                                          │
│  ⏰ 08:00 ──────────► 11:00                                │
│  📊 Volatilité: MOYENNE                                     │
│  💰 Rentabilité: BONNE                                      │
│  ✅ AUTORISÉ                                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🇺🇸 US MORNING SESSION                                     │
│  ⏰ 15:50 ──────────► 17:00                                │
│  📊 Volatilité: HAUTE                                       │
│  💰 Rentabilité: TRÈS BONNE                                 │
│  ✅ AUTORISÉ                                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ⚡ US POWER HOUR                                           │
│  ⏰ 20:00 ──────────► 21:30                                │
│  📊 Volatilité: TRÈS HAUTE                                  │
│  💰 Rentabilité: EXCELLENTE (Meilleure session)            │
│  ✅ AUTORISÉ                                                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔴 SESSIONS BLOQUÉES (NO TRADE)

```
┌─────────────────────────────────────────────────────────────┐
│  🌙 OVERNIGHT / ASIA                                        │
│  ⏰ 00:00 ──────────► 08:00                                │
│  ❌ BLOQUÉ - Market fermé                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🕐 GAP LONDON → US                                         │
│  ⏰ 11:00 ──────────► 15:25                                │
│  ❌ BLOQUÉ - Faible liquidité                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  ⏸️  PRE-OPEN PAUSE                                         │
│  ⏰ 15:25 ──────────► 15:35                                │
│  ❌ BLOQUÉ - Attente ouverture CME                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  👀 OPR OBSERVE                                             │
│  ⏰ 15:35 ──────────► 15:50                                │
│  ❌ BLOQUÉ - Observer uniquement (sauf OPR Strategy)        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🍔 LUNCH US                                                │
│  ⏰ 17:00 ──────────► 19:30                                │
│  ❌ BLOQUÉ - Session PERDANTE 🔥                            │
│  📊 Résultats 01/12/2025:                                   │
│     • 22 trades ES                                          │
│     • Win Rate: 41% (9W-13L)                                │
│     • P&L: -$588 🩸                                         │
│  💡 Économie: +$588/jour en bloquant                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  🛑 HARD STOP                                               │
│  ⏰ 21:30 ──────────► 00:00                                │
│  ❌ BLOQUÉ - Arrêt absolu (Non-négociable)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 TIMELINE 24H (Heure Paris)

```
00:00 ━━━━━━━━ ❌ OVERNIGHT (fermé)
      │
08:00 ┏━━━━━━━ ✅ LONDON SESSION
      ┃
11:00 ┗━━━━━━━ ❌ GAP (faible liquidité)
      │
15:25 ━━━━━━━━ ❌ PRE-OPEN PAUSE
15:35 ━━━━━━━━ ❌ OPR OBSERVE
15:50 ┏━━━━━━━ ✅ US MORNING
      ┃
17:00 ┗━━━━━━━ ❌ LUNCH US 🍔 (BLOQUÉ depuis 02/12/2025)
      │
19:30 ━━━━━━━━ ❌ Transition
      │
20:00 ┏━━━━━━━ ✅ US POWER HOUR ⚡ (MEILLEUR)
      ┃
21:30 ┗━━━━━━━ 🛑 HARD STOP (arrêt absolu)
      │
00:00 ━━━━━━━━ ❌ OVERNIGHT
```

---

## 🎯 TEMPS DE TRADING TOTAL

### Par Jour:
- **London**: 3h00 (08:00-11:00)
- **US Morning**: 1h10 (15:50-17:00)
- **US Power Hour**: 1h30 (20:00-21:30)

**TOTAL: 5h40/jour** ✅

### Temps Bloqué:
- **Lunch**: 2h30 (17:00-19:30) 🔴
- **Overnight**: 8h00 (00:00-08:00) 🔴
- **Gap/Pause**: 4h25 (11:00-15:25) 🔴
- **Hard Stop**: 2h30 (21:30-00:00) 🔴

**TOTAL BLOQUÉ: 18h20/jour**

---

## 🔥 CHANGEMENT IMPORTANT (02/12/2025)

### ✅ LUNCH US 17:00-19:30 → RÉACTIVÉ

**Avant (01/12/2025 - Mode Test)**:
- Session étendue 17:00-21:30
- Lunch non bloqué (test)

**Après (02/12/2025 - Production)**:
- ❌ **LUNCH BLOQUÉ** 17:00-19:30
- Raison: **-$588/jour** sur ES
- Win Rate: **41%** (perdant)
- Économie attendue: **+$11,760/mois**

---

## 💡 NOTES IMPORTANTES

### Mode Test vs Production:
- **Test Mode**: `test_mode=True` → Bypass tous les blocks (pour développement)
- **Production**: `test_mode=False` → Filtrage strict ✅ ACTUEL

### Sessions par Priorité:
1. 🥇 **US Power Hour** (20:00-21:30) - MEILLEUR
2. 🥈 **US Morning** (15:50-17:00) - TRÈS BON
3. 🥉 **London** (08:00-11:00) - BON

### Éviter Absolument:
- ❌ **LUNCH** (17:00-19:30) - Session perdante confirmée
- ❌ **Overnight** - Market fermé
- ❌ **Post 21:30** - Hard Stop non négociable

---

## 🚀 PROCHAINE SESSION

Le bot calcule automatiquement la prochaine session et affiche:
```
⏭️  PROCHAINE SESSION: US Power Hour
📍 Tuesday 02 December 2025 à 20:00 Paris
⏳ Dans 2.5 heures
```

---

**Configuration**: `core/session_quality_monitor.py`
**Documentation**: `docs/CHANGELOG_SESSION_QUALITY_02DEC2025.md`
**Date**: 2 Décembre 2025
**Status**: ✅ PRODUCTION READY
