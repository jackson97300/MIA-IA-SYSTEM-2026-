"""
Système de Logging Avancé MIA
==============================

Gestion centralisée des logs avec:
- Séparation par niveau (INFO, WARNING, ERROR, CRITICAL)
- Logs thématiques (trades, discord, signals, dtc)
- Format JSON structuré
- Résumé quotidien automatique
- Pointeur vers log actif

Créé le: 26 Nov 2025
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import sys


class AdvancedLogManager:
    """Gestionnaire de logs avancé avec multi-destinations"""

    def __init__(self, base_dir: str = "D:\\MIA_IA_system\\logs_advanced"):
        self.base_dir = Path(base_dir)
        self.date_str = datetime.now().strftime("%Y%m%d")
        self.datetime_str = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Créer les sous-dossiers
        self.dirs = {
            'trades': self.base_dir / 'trades',
            'discord': self.base_dir / 'discord',
            'signals': self.base_dir / 'signals',
            'dtc': self.base_dir / 'dtc',
            'performance': self.base_dir / 'performance',
            'summaries': self.base_dir / 'summaries',
            'json': self.base_dir / 'json'
        }

        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)

        # Fichiers de logs
        self.log_files = {
            'main': self.base_dir / f"bot_production_{self.datetime_str}.log",
            'info': self.base_dir / f"bot_INFO_{self.date_str}.log",
            'warning': self.base_dir / f"bot_WARNING_{self.date_str}.log",
            'error': self.base_dir / f"bot_ERROR_{self.date_str}.log",
            'critical': self.base_dir / f"bot_CRITICAL_{self.date_str}.log",
            'trades': self.dirs['trades'] / f"trades_{self.date_str}.log",
            'discord': self.dirs['discord'] / f"discord_{self.date_str}.log",
            'signals': self.dirs['signals'] / f"signals_{self.date_str}.log",
            'dtc': self.dirs['dtc'] / f"dtc_orders_{self.date_str}.log",
            'performance': self.dirs['performance'] / f"performance_{self.date_str}.log",
            'json': self.dirs['json'] / f"events_{self.date_str}.jsonl"
        }

        # Pointeur vers log actif
        self.current_log_pointer = self.base_dir / ".current_log"

        # Initialiser les loggers
        self.loggers = {}
        self._setup_loggers()

        # Écrire le pointeur
        self._write_current_log_pointer()

        # Stats pour résumé
        self.stats = {
            'start_time': datetime.now(),
            'trades': {'ES': 0, 'NQ': 0, 'RTY': 0},
            'signals_generated': 0,
            'signals_rejected': 0,
            'discord_messages': 0,
            'dtc_orders_sent': 0,
            'dtc_orders_rejected': 0,
            'errors': []
        }

    def _setup_loggers(self):
        """Configure tous les loggers"""

        # Format détaillé pour logs principaux
        detailed_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Format simplifié pour logs thématiques
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )

        # Logger principal (tous niveaux)
        self.loggers['main'] = self._create_logger(
            'main',
            self.log_files['main'],
            detailed_formatter,
            logging.DEBUG
        )

        # Loggers par niveau
        self.loggers['info'] = self._create_logger(
            'info',
            self.log_files['info'],
            detailed_formatter,
            logging.INFO
        )

        self.loggers['warning'] = self._create_logger(
            'warning',
            self.log_files['warning'],
            detailed_formatter,
            logging.WARNING
        )

        self.loggers['error'] = self._create_logger(
            'error',
            self.log_files['error'],
            detailed_formatter,
            logging.ERROR
        )

        self.loggers['critical'] = self._create_logger(
            'critical',
            self.log_files['critical'],
            detailed_formatter,
            logging.CRITICAL
        )

        # Loggers thématiques
        for theme in ['trades', 'discord', 'signals', 'dtc', 'performance']:
            self.loggers[theme] = self._create_logger(
                theme,
                self.log_files[theme],
                simple_formatter,
                logging.INFO
            )

    def _create_logger(self, name: str, filepath: Path, formatter, level) -> logging.Logger:
        """Crée un logger avec handler fichier"""
        logger = logging.getLogger(f"mia.{name}")
        logger.setLevel(level)
        logger.handlers.clear()  # Éviter doublons

        # Handler fichier avec encoding UTF-8
        handler = logging.FileHandler(filepath, encoding='utf-8')
        handler.setFormatter(formatter)
        handler.setLevel(level)

        logger.addHandler(handler)
        logger.propagate = False  # Éviter duplication

        return logger

    def _write_current_log_pointer(self):
        """Écrit le fichier pointeur vers le log actif"""
        try:
            with open(self.current_log_pointer, 'w') as f:
                f.write(f"# Log actif (démarré le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n")
                f.write(f"{self.log_files['main'].name}\n")
                f.write(f"\n# Logs thématiques du jour\n")
                f.write(f"trades: {self.log_files['trades'].relative_to(self.base_dir)}\n")
                f.write(f"discord: {self.log_files['discord'].relative_to(self.base_dir)}\n")
                f.write(f"signals: {self.log_files['signals'].relative_to(self.base_dir)}\n")
                f.write(f"dtc: {self.log_files['dtc'].relative_to(self.base_dir)}\n")
        except Exception as e:
            print(f"Erreur écriture pointeur log: {e}")

    def log_event_json(self, event_type: str, data: Dict[str, Any]):
        """Log un événement en JSON structuré"""
        try:
            event = {
                'timestamp': datetime.now().isoformat(),
                'type': event_type,
                'data': data
            }

            with open(self.log_files['json'], 'a', encoding='utf-8') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            print(f"Erreur log JSON: {e}")

    def log_trade(self, symbol: str, action: str, details: Dict[str, Any]):
        """Log un trade"""
        msg = f"[{symbol}] {action} | {details}"
        self.loggers['trades'].info(msg)

        # JSON structuré
        self.log_event_json('trade', {
            'symbol': symbol,
            'action': action,
            **details
        })

        # Stats
        if action == 'ENTRY':
            self.stats['trades'][symbol] = self.stats['trades'].get(symbol, 0) + 1

    def log_discord(self, channel: str, message_type: str, sent: bool):
        """Log un message Discord"""
        status = "✅ SENT" if sent else "❌ FAILED"
        msg = f"{status} [{channel}] {message_type}"
        self.loggers['discord'].info(msg)

        # JSON
        self.log_event_json('discord', {
            'channel': channel,
            'type': message_type,
            'sent': sent
        })

        # Stats
        if sent:
            self.stats['discord_messages'] += 1

    def log_signal(self, symbol: str, signal_type: str, accepted: bool, reason: str = ""):
        """Log un signal de trading"""
        status = "✅ ACCEPTED" if accepted else "❌ REJECTED"
        msg = f"{status} [{symbol}] {signal_type}"
        if reason:
            msg += f" | {reason}"

        self.loggers['signals'].info(msg)

        # JSON
        self.log_event_json('signal', {
            'symbol': symbol,
            'type': signal_type,
            'accepted': accepted,
            'reason': reason
        })

        # Stats
        if accepted:
            self.stats['signals_generated'] += 1
        else:
            self.stats['signals_rejected'] += 1

    def log_dtc_order(self, symbol: str, order_type: str, result: str, details: Dict[str, Any] = None):
        """Log un ordre DTC"""
        msg = f"[{symbol}] {order_type} → {result}"
        if details:
            msg += f" | {details}"

        self.loggers['dtc'].info(msg)

        # JSON
        self.log_event_json('dtc_order', {
            'symbol': symbol,
            'order_type': order_type,
            'result': result,
            'details': details or {}
        })

        # Stats
        self.stats['dtc_orders_sent'] += 1
        if 'rejected' in result.lower() or 'failed' in result.lower():
            self.stats['dtc_orders_rejected'] += 1

    def log_error(self, error_type: str, message: str, critical: bool = False):
        """Log une erreur"""
        level = logging.CRITICAL if critical else logging.ERROR

        logger = self.loggers['critical' if critical else 'error']
        logger.log(level, f"[{error_type}] {message}")

        # JSON
        self.log_event_json('error', {
            'type': error_type,
            'message': message,
            'critical': critical
        })

        # Stats
        self.stats['errors'].append({
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': error_type,
            'message': message,
            'critical': critical
        })

    def generate_daily_summary(self) -> str:
        """Génère le résumé quotidien"""
        end_time = datetime.now()
        duration = end_time - self.stats['start_time']
        hours = int(duration.total_seconds() / 3600)
        minutes = int((duration.total_seconds() % 3600) / 60)

        summary = f"""
{'='*80}
RESUME BOT - {self.date_str}
{'='*80}

DUREE
  Demarrage: {self.stats['start_time'].strftime('%H:%M:%S')}
  Arret:     {end_time.strftime('%H:%M:%S')}
  Duree:     {hours}h {minutes}min

TRADES
  ES:  {self.stats['trades'].get('ES', 0)} trades
  NQ:  {self.stats['trades'].get('NQ', 0)} trades
  RTY: {self.stats['trades'].get('RTY', 0)} trades
  TOTAL: {sum(self.stats['trades'].values())} trades

SIGNAUX
  Generes: {self.stats['signals_generated']}
  Rejetes: {self.stats['signals_rejected']}
  Taux acceptance: {(self.stats['signals_generated'] / max(1, self.stats['signals_generated'] + self.stats['signals_rejected']) * 100):.1f}%

DISCORD
  Messages envoyes: {self.stats['discord_messages']}

DTC ORDERS
  Envoyes: {self.stats['dtc_orders_sent']}
  Rejetes: {self.stats['dtc_orders_rejected']}
  Taux succes: {((self.stats['dtc_orders_sent'] - self.stats['dtc_orders_rejected']) / max(1, self.stats['dtc_orders_sent']) * 100):.1f}%

ERREURS ({len(self.stats['errors'])})
"""

        if self.stats['errors']:
            # Grouper par type
            error_types = {}
            for err in self.stats['errors']:
                err_type = err['type']
                if err_type not in error_types:
                    error_types[err_type] = []
                error_types[err_type].append(err)

            for err_type, errors in error_types.items():
                summary += f"\n  {err_type}: {len(errors)} occurrence(s)\n"
                for err in errors[:3]:  # Max 3 exemples
                    summary += f"    - {err['time']}: {err['message'][:80]}\n"
                if len(errors) > 3:
                    summary += f"    ... et {len(errors) - 3} autres\n"
        else:
            summary += "  Aucune erreur (OK)\n"

        summary += "\n" + "="*80 + "\n"

        # Sauvegarder
        summary_file = self.dirs['summaries'] / f"SUMMARY_{self.date_str}.txt"
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
        except Exception as e:
            print(f"Erreur sauvegarde résumé: {e}")

        return summary


def create_advanced_log_manager(base_dir: str = None) -> AdvancedLogManager:
    """Factory function pour créer le gestionnaire de logs"""
    if base_dir is None:
        # Lire depuis config/paths.json (chemin absolu ou relatif depuis racine projet)
        try:
            # Essayer chemin absolu d'abord
            config_path = Path("D:/MIA_IA_system/config/paths.json")
            if not config_path.exists():
                # Fallback: chemin relatif depuis LAUNCH
                config_path = Path("../config/paths.json")

            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    base_dir = config['logs']['main_dir']
        except Exception as e:
            print(f"⚠️ Erreur lecture config/paths.json: {e}")
            base_dir = "D:\\MIA_IA_system\\LAUNCH\\logs"

    return AdvancedLogManager(base_dir)


if __name__ == "__main__":
    # Test du système
    print("Test du système de logs avancé...")

    log_mgr = create_advanced_log_manager()

    # Test logs thématiques
    log_mgr.log_trade('ES', 'ENTRY', {'price': 6835.50, 'side': 'LONG'})
    log_mgr.log_discord('admin_messages', 'BOT_STARTED', True)
    log_mgr.log_signal('NQ', 'CONFLUENCE', True)
    log_mgr.log_signal('ES', 'WEAK_SIGNAL', False, "Confidence too low")
    log_mgr.log_dtc_order('NQ', 'BRACKET', 'SENT', {'tp': 25350, 'sl': 25300})
    log_mgr.log_error('DTC', "ClientOrderID field is not set", critical=True)

    # Générer résumé
    summary = log_mgr.generate_daily_summary()
    print(summary)

    print("\n[OK] Systeme de logs cree!")
    print(f"Dossier: {log_mgr.base_dir}")
    print(f"Log principal: {log_mgr.log_files['main'].name}")
    print(f"Pointeur: {log_mgr.current_log_pointer}")
