# 🛡️ GUIDE PROTECTION ANTI-CRASH - MIA TRADING SYSTEM

## Date: 14 Décembre 2025 (v2.0 - Corrigé)

---

## 📋 VUE D'ENSEMBLE

Ce système offre 3 niveaux de protection pour que le bot survive aux crashes:

| Niveau | Protection | Fichier |
|--------|------------|---------|
| 1️⃣ | Windows redémarre auto après BSOD | `CONFIGURE_AUTO_REBOOT_BSOD.bat` |
| 2️⃣ | Watchdog surveille et redémarre le bot | `LAUNCH/mia_watchdog.py` (EXISTE DÉJÀ) |
| 3️⃣ | Tâche planifiée lance le watchdog au boot | `INSTALL_WATCHDOG_WINDOWS.bat` |

---

## ✅ CE QUI EXISTE DÉJÀ (Pas besoin de créer!)

Le projet a DÉJÀ un système complet:

| Composant | Fichier | Status |
|-----------|---------|--------|
| **Watchdog Python** | `LAUNCH/mia_watchdog.py` | ✅ 482 lignes, complet |
| **Heartbeat** | Dans `launch_production_CLEAN_v2.py` | ✅ `_write_heartbeat()` |
| **Smart Launcher** | `LAUNCH/smart_launcher.ps1` | ✅ Lance bot + watchdog |
| **Fichiers PID/Heartbeat** | `logs/bot.pid` + `logs/heartbeat.json` | ✅ |

---

## 🔧 INSTALLATION EN 2 ÉTAPES

### ÉTAPE 1: Configurer Windows Anti-BSOD

1. Aller dans `D:\MIA_IA_system\COMMANDE_MIA\`
2. **Clic droit** sur `CONFIGURE_AUTO_REBOOT_BSOD.bat`
3. Sélectionner **"Exécuter en tant qu'administrateur"**
4. Suivre les instructions

**Ce que ça fait:**
- Windows redémarre automatiquement après un écran bleu
- Pas de blocage sur l'écran d'erreur

---

### ÉTAPE 2: Installer la tâche planifiée

1. Aller dans `D:\MIA_IA_system\COMMANDE_MIA\`
2. **Clic droit** sur `INSTALL_WATCHDOG_WINDOWS.bat`
3. Sélectionner **"Exécuter en tant qu'administrateur"**
4. Répondre "O" pour démarrer le watchdog maintenant

**Ce que ça fait:**
- Crée une tâche planifiée "MIA_Watchdog"
- Le watchdog démarre automatiquement au boot de Windows
- Il surveille le bot et le redémarre si crash

---

## 📊 COMMENT ÇA MARCHE

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│     WINDOWS DÉMARRE (après BSOD ou reboot)                      │
│           │                                                     │
│           ▼                                                     │
│     ┌─────────────┐    (Tâche planifiée - délai 1 min)         │
│     │  WATCHDOG   │◄───────────────────────────────────────┐   │
│     │  démarre    │                                         │   │
│     └──────┬──────┘                                         │   │
│            │                                                │   │
│            ▼                                                │   │
│     ┌─────────────┐                                         │   │
│     │    BOT      │ ──── heartbeat.json ────────────────────│   │
│     │  démarre    │      (toutes les 30 cycles)             │   │
│     └──────┬──────┘                                         │   │
│            │                                                │   │
│            │ CRASH!                                         │   │
│            ▼                                                │   │
│     ┌─────────────┐                                         │   │
│     │  WATCHDOG   │                                         │   │
│     │  détecte    │ ──── (2 min sans heartbeat)             │   │
│     └──────┬──────┘                                         │   │
│            │                                                │   │
│            ▼                                                │   │
│     ┌─────────────┐                                         │   │
│     │  WATCHDOG   │                                         │   │
│     │  REDÉMARRE  │ ───────────────────────────────────────►│   │
│     │  le BOT     │          (notification Discord)         │   │
│     └─────────────┘                                         │   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ PARAMÈTRES (dans `LAUNCH/mia_watchdog.py`)

```python
HEARTBEAT_TIMEOUT_SECONDS = 120  # 2 min sans heartbeat = frozen
CHECK_INTERVAL_SECONDS = 30      # Vérifier toutes les 30 secondes
MAX_RESTARTS_PER_HOUR = 5        # Max 5 restarts par heure
RESTART_DELAY_BASE = 10          # Délai initial avant restart

# Sessions de trading (pas de restart hors heures)
TRADING_HOURS = [
    (8, 0, 11, 0),    # London: 08:00-11:00
    (15, 50, 17, 0),  # US Morning: 15:50-17:00
    (20, 0, 21, 30),  # US Power Hour: 20:00-21:30
]
```

---

## 🛠️ COMMANDES UTILES

```powershell
# Voir le status de la tâche planifiée
schtasks /query /tn "MIA_Watchdog"

# Démarrer manuellement le watchdog
schtasks /run /tn "MIA_Watchdog"

# Supprimer la tâche planifiée
schtasks /delete /tn "MIA_Watchdog" /f

# Voir les logs watchdog
Get-Content D:\MIA_IA_system\logs\watchdog.log -Tail 50

# Voir le dernier heartbeat
Get-Content D:\MIA_IA_system\logs\heartbeat.json
```

---

## ⚠️ PROTECTION CONTRE BOUCLE INFINIE

Le watchdog a une protection intégrée:

- **Maximum 5 redémarrages par heure**
- Si dépassé → watchdog s'arrête et envoie alerte Discord
- Évite de boucler infiniment si problème grave

---

## 📋 CHECKLIST INSTALLATION

- [ ] `CONFIGURE_AUTO_REBOOT_BSOD.bat` exécuté en admin
- [ ] `INSTALL_WATCHDOG_WINDOWS.bat` exécuté en admin
- [ ] Tâche planifiée vérifiée (`schtasks /query /tn "MIA_Watchdog"`)
- [ ] Test: Lancer le bot, tuer le processus, vérifier restart auto

---

## 🧪 TEST

Pour tester que tout fonctionne:

1. Lancer le bot normalement via `COMMANDE_MIA\START_BOT.bat`
2. Vérifier que `logs\heartbeat.json` se met à jour
3. Tuer le processus Python manuellement
4. Attendre 2-3 minutes
5. Le watchdog devrait redémarrer le bot automatiquement
6. Vérifier `logs\watchdog.log`

---

## 📁 STRUCTURE FINALE

```
D:\MIA_IA_system\
├── COMMANDE_MIA\
│   ├── CONFIGURE_AUTO_REBOOT_BSOD.bat   ← Config Windows anti-BSOD
│   ├── INSTALL_WATCHDOG_WINDOWS.bat     ← Installe tâche planifiée
│   ├── START_BOT.bat                    ← Lance le bot
│   ├── STOP_BOT.bat                     ← Arrête le bot
│   └── CRASH_PROTECTION\
│       ├── GUIDE_PROTECTION_CRASH.md    ← Ce guide
│       └── configure_auto_reboot.bat    ← Original
│
├── LAUNCH\
│   ├── launch_production_CLEAN_v2.py    ← Bot principal
│   ├── mia_watchdog.py                  ← Watchdog (482 lignes)
│   └── smart_launcher.ps1               ← Launcher PowerShell
│
└── logs\
    ├── bot.pid                          ← PID du bot
    ├── heartbeat.json                   ← Heartbeat pour watchdog
    └── watchdog.log                     ← Logs du watchdog
```

---

*Guide v2.0 - 14 Décembre 2025 - MIA IA TRADING SYSTEM*


