#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    MIA WATCHDOG - AUTO-RESTART SYSTEM                        ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                               ║
║  Version: 1.0                                                                 ║
║  Date: 04 Décembre 2025                                                       ║
║                                                                               ║
║  🎯 OBJECTIF:                                                                 ║
║  Surveiller le bot MIA et le redémarrer automatiquement si:                  ║
║  - Le processus crash                                                         ║
║  - Le bot est frozen (pas de heartbeat)                                       ║
║  - Erreur critique détectée                                                   ║
║                                                                               ║
║  📊 FONCTIONNALITÉS:                                                          ║
║  - Monitoring processus Python                                                ║
║  - Heartbeat via fichier (le bot écrit, watchdog lit)                        ║
║  - Auto-restart avec délai exponentiel                                        ║
║  - Notifications Discord sur restart                                          ║
║  - Limite de restarts pour éviter boucle infinie                              ║
║                                                                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import subprocess
import time
import os
import sys
import json
import signal
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import requests

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [WATCHDOG] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('logs/watchdog.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class WatchdogConfig:
    """Configuration du watchdog"""

    # Chemins
    BOT_SCRIPT = "LAUNCH/launch_production_CLEAN_v2.py"
    HEARTBEAT_FILE = "logs/heartbeat.json"
    PID_FILE = "logs/bot.pid"

    # Timeouts
    HEARTBEAT_TIMEOUT_SECONDS = 120  # 2 minutes sans heartbeat = frozen
    CHECK_INTERVAL_SECONDS = 30       # Vérifier toutes les 30 secondes
    STARTUP_GRACE_PERIOD = 60         # 60s de grâce au démarrage

    # Restart policy
    MAX_RESTARTS_PER_HOUR = 5         # Max 5 restarts par heure
    RESTART_DELAY_BASE = 10           # Délai initial: 10 secondes
    RESTART_DELAY_MAX = 300           # Délai max: 5 minutes
    RESTART_DELAY_MULTIPLIER = 2      # Multiplier après chaque restart

    # Discord
    DISCORD_WEBHOOK = "https://discordapp.com/api/webhooks/1440118650190303364/mxT0RO1kbA8mNNaDRWLSjg2Y7-KS56ym3gh5THjdswhHyASn80kmfXts_cxqFDGnsHj9"

    # Sessions de trading (ne pas restart en dehors)
    TRADING_HOURS = [
        (8, 0, 11, 0),    # London: 08:00-11:00
        (15, 50, 17, 0),  # US Morning: 15:50-17:00
        (20, 0, 21, 30),  # US Power Hour: 20:00-21:30
    ]


# ============================================================================
# DISCORD NOTIFICATIONS
# ============================================================================

def send_discord_alert(title: str, message: str, color: int = 0xFF0000, fields: list = None):
    """Envoie une alerte Discord"""
    try:
        embed = {
            "title": title,
            "description": message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {"text": "MIA Watchdog v1.0"}
        }

        if fields:
            embed["fields"] = fields

        payload = {"embeds": [embed]}

        response = requests.post(
            WatchdogConfig.DISCORD_WEBHOOK,
            json=payload,
            timeout=10
        )

        if response.status_code == 204:
            logger.info(f"Discord alert sent: {title}")
        else:
            logger.warning(f"Discord alert failed: {response.status_code}")

    except Exception as e:
        logger.error(f"Discord alert error: {e}")


# ============================================================================
# HEARTBEAT MANAGEMENT
# ============================================================================

def read_heartbeat() -> Optional[dict]:
    """Lit le fichier heartbeat"""
    try:
        heartbeat_path = Path(WatchdogConfig.HEARTBEAT_FILE)
        if not heartbeat_path.exists():
            return None

        with open(heartbeat_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error reading heartbeat: {e}")
        return None


def is_heartbeat_stale() -> bool:
    """Vérifie si le heartbeat est périmé"""
    heartbeat = read_heartbeat()

    if not heartbeat:
        return True

    try:
        last_beat = datetime.fromisoformat(heartbeat.get('timestamp', ''))
        age_seconds = (datetime.now() - last_beat).total_seconds()

        if age_seconds > WatchdogConfig.HEARTBEAT_TIMEOUT_SECONDS:
            logger.warning(f"Heartbeat stale: {age_seconds:.0f}s old (max: {WatchdogConfig.HEARTBEAT_TIMEOUT_SECONDS}s)")
            return True

        return False

    except Exception as e:
        logger.error(f"Error parsing heartbeat: {e}")
        return True


def write_heartbeat_file():
    """Crée le fichier heartbeat initial"""
    try:
        Path("logs").mkdir(exist_ok=True)
        heartbeat = {
            "timestamp": datetime.now().isoformat(),
            "source": "watchdog_init",
            "status": "starting"
        }
        with open(WatchdogConfig.HEARTBEAT_FILE, 'w') as f:
            json.dump(heartbeat, f)
    except Exception as e:
        logger.error(f"Error creating heartbeat file: {e}")


# ============================================================================
# PROCESS MANAGEMENT
# ============================================================================

def is_in_trading_hours() -> bool:
    """Vérifie si on est en heures de trading"""
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute

    for start_h, start_m, end_h, end_m in WatchdogConfig.TRADING_HOURS:
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        if start_minutes <= current_minutes <= end_minutes:
            return True

    return False


def get_bot_pid() -> Optional[int]:
    """Récupère le PID du bot depuis le fichier"""
    try:
        pid_path = Path(WatchdogConfig.PID_FILE)
        if not pid_path.exists():
            return None

        with open(pid_path, 'r') as f:
            return int(f.read().strip())
    except Exception as e:
        logger.warning(f"Error reading PID file: {e}")
        return None


def save_bot_pid(pid: int):
    """Sauvegarde le PID du bot"""
    try:
        Path("logs").mkdir(exist_ok=True)
        with open(WatchdogConfig.PID_FILE, 'w') as f:
            f.write(str(pid))
    except Exception as e:
        logger.error(f"Error saving PID: {e}")


def is_process_running(pid: int) -> bool:
    """Vérifie si un processus est en cours d'exécution"""
    try:
        if sys.platform == 'win32':
            # Windows: utiliser tasklist
            result = subprocess.run(
                ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
                capture_output=True,
                text=True
            )
            return str(pid) in result.stdout
        else:
            # Linux/Mac: utiliser os.kill avec signal 0
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.SubprocessError):
        return False


def kill_bot_process():
    """Tue le processus bot s'il existe"""
    pid = get_bot_pid()
    if pid and is_process_running(pid):
        try:
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
            logger.info(f"Killed bot process PID {pid}")
            time.sleep(2)  # Attendre que le processus se termine
        except Exception as e:
            logger.error(f"Error killing process: {e}")


def start_bot() -> Optional[subprocess.Popen]:
    """Démarre le bot et retourne le processus"""
    try:
        # S'assurer qu'on est dans le bon répertoire
        project_root = Path(__file__).parent.parent
        os.chdir(project_root)

        logger.info(f"Starting bot from: {project_root}")
        logger.info(f"Script: {WatchdogConfig.BOT_SCRIPT}")

        # Démarrer le bot
        process = subprocess.Popen(
            [sys.executable, WatchdogConfig.BOT_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(project_root)
        )

        # Sauvegarder le PID
        save_bot_pid(process.pid)

        logger.info(f"Bot started with PID: {process.pid}")
        return process

    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return None


# ============================================================================
# WATCHDOG MAIN LOOP
# ============================================================================

class MIAWatchdog:
    """Watchdog principal pour MIA Trading Bot"""

    def __init__(self):
        self.bot_process: Optional[subprocess.Popen] = None
        self.restart_count = 0
        self.restart_times = []  # Pour tracker les restarts par heure
        self.current_delay = WatchdogConfig.RESTART_DELAY_BASE
        self.last_startup = None
        self.running = True

    def calculate_restart_delay(self) -> int:
        """Calcule le délai avant restart (backoff exponentiel)"""
        delay = min(
            self.current_delay,
            WatchdogConfig.RESTART_DELAY_MAX
        )
        self.current_delay = min(
            self.current_delay * WatchdogConfig.RESTART_DELAY_MULTIPLIER,
            WatchdogConfig.RESTART_DELAY_MAX
        )
        return delay

    def reset_restart_delay(self):
        """Reset le délai après un fonctionnement stable"""
        self.current_delay = WatchdogConfig.RESTART_DELAY_BASE

    def can_restart(self) -> bool:
        """Vérifie si on peut faire un restart (limite par heure)"""
        one_hour_ago = datetime.now() - timedelta(hours=1)
        self.restart_times = [t for t in self.restart_times if t > one_hour_ago]

        if len(self.restart_times) >= WatchdogConfig.MAX_RESTARTS_PER_HOUR:
            logger.error(f"Max restarts reached ({WatchdogConfig.MAX_RESTARTS_PER_HOUR}/hour)")
            send_discord_alert(
                "🛑 WATCHDOG - MAX RESTARTS ATTEINT",
                f"Le bot a été redémarré {WatchdogConfig.MAX_RESTARTS_PER_HOUR} fois en 1 heure.\n"
                "**Intervention manuelle requise!**",
                color=0xFF0000,
                fields=[
                    {"name": "Restarts cette heure", "value": str(len(self.restart_times)), "inline": True},
                    {"name": "Action", "value": "Watchdog en pause", "inline": True}
                ]
            )
            return False
        return True

    def restart_bot(self, reason: str):
        """Redémarre le bot avec notification Discord"""
        if not self.can_restart():
            return False

        delay = self.calculate_restart_delay()
        self.restart_count += 1
        self.restart_times.append(datetime.now())

        logger.warning(f"Restarting bot in {delay}s - Reason: {reason}")

        # Notification Discord
        send_discord_alert(
            "🔄 WATCHDOG - RESTART BOT",
            f"**Raison:** {reason}",
            color=0xFFA500,  # Orange
            fields=[
                {"name": "Restart #", "value": str(self.restart_count), "inline": True},
                {"name": "Délai", "value": f"{delay}s", "inline": True},
                {"name": "Heure", "value": datetime.now().strftime("%H:%M:%S"), "inline": True}
            ]
        )

        # Kill processus existant
        kill_bot_process()

        # Attendre le délai
        time.sleep(delay)

        # Créer heartbeat initial
        write_heartbeat_file()

        # Démarrer le bot
        self.bot_process = start_bot()
        self.last_startup = datetime.now()

        if self.bot_process:
            logger.info(f"Bot restarted successfully (PID: {self.bot_process.pid})")
            return True
        else:
            logger.error("Failed to restart bot!")
            return False

    def check_bot_health(self) -> tuple[bool, str]:
        """Vérifie la santé du bot. Retourne (is_healthy, reason)"""

        # 1. Vérifier si le processus existe
        pid = get_bot_pid()
        if not pid:
            return False, "No PID file found"

        if not is_process_running(pid):
            return False, f"Process {pid} not running"

        # 2. Vérifier la période de grâce après démarrage
        if self.last_startup:
            startup_age = (datetime.now() - self.last_startup).total_seconds()
            if startup_age < WatchdogConfig.STARTUP_GRACE_PERIOD:
                return True, f"In grace period ({startup_age:.0f}s/{WatchdogConfig.STARTUP_GRACE_PERIOD}s)"

        # 3. Vérifier le heartbeat
        if is_heartbeat_stale():
            return False, "Heartbeat stale (bot frozen?)"

        # 4. Tout va bien
        return True, "Healthy"

    def run(self):
        """Boucle principale du watchdog"""
        logger.info("=" * 60)
        logger.info("MIA WATCHDOG STARTING")
        logger.info("=" * 60)

        send_discord_alert(
            "🐕 WATCHDOG DÉMARRÉ",
            "Le watchdog MIA est maintenant actif et surveille le bot.",
            color=0x00FF00,  # Vert
            fields=[
                {"name": "Heartbeat Timeout", "value": f"{WatchdogConfig.HEARTBEAT_TIMEOUT_SECONDS}s", "inline": True},
                {"name": "Check Interval", "value": f"{WatchdogConfig.CHECK_INTERVAL_SECONDS}s", "inline": True},
                {"name": "Max Restarts/h", "value": str(WatchdogConfig.MAX_RESTARTS_PER_HOUR), "inline": True}
            ]
        )

        # Démarrage initial du bot
        write_heartbeat_file()
        self.bot_process = start_bot()
        self.last_startup = datetime.now()

        if not self.bot_process:
            logger.error("Failed to start bot initially!")
            return

        # Boucle principale
        stable_time = 0
        while self.running:
            try:
                time.sleep(WatchdogConfig.CHECK_INTERVAL_SECONDS)

                is_healthy, reason = self.check_bot_health()

                if is_healthy:
                    stable_time += WatchdogConfig.CHECK_INTERVAL_SECONDS

                    # Reset delay après 10 minutes de stabilité
                    if stable_time > 600:
                        self.reset_restart_delay()
                        stable_time = 0

                    logger.debug(f"Bot healthy: {reason}")
                else:
                    stable_time = 0
                    logger.warning(f"Bot unhealthy: {reason}")

                    # Vérifier si on est en heures de trading
                    if not is_in_trading_hours():
                        logger.info("Outside trading hours - skipping restart")
                        continue

                    # Restart le bot
                    if not self.restart_bot(reason):
                        logger.error("Restart failed - waiting before retry")
                        time.sleep(60)  # Attendre 1 minute avant de réessayer

            except KeyboardInterrupt:
                logger.info("Watchdog stopped by user")
                self.running = False
            except Exception as e:
                logger.error(f"Watchdog error: {e}")
                time.sleep(10)

        # Cleanup
        logger.info("Watchdog shutting down...")
        send_discord_alert(
            "🛑 WATCHDOG ARRÊTÉ",
            "Le watchdog MIA a été arrêté.",
            color=0xFF0000
        )


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Créer le dossier logs si nécessaire
    Path("logs").mkdir(exist_ok=True)

    # Démarrer le watchdog
    watchdog = MIAWatchdog()
    watchdog.run()
