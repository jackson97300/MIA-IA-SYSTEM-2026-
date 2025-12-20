"""
Helper pour lire facilement les logs MIA
========================================

Utilisation rapide des logs sans chercher les fichiers!

Exemples:
    python utils/log_reader.py --today trades
    python utils/log_reader.py --today discord
    python utils/log_reader.py --summary
    python utils/log_reader.py --errors
"""

import json
from pathlib import Path
from datetime import datetime
import argparse
import sys


class LogReader:
    """Lecteur de logs MIA simplifié"""

    def __init__(self):
        # Charger chemins depuis config
        self.config = self._load_config()
        self.base_dir = Path(self.config['logs']['main_dir'])
        self.date_str = datetime.now().strftime("%Y%m%d")

    def _load_config(self) -> dict:
        """Charge la configuration des chemins"""
        try:
            with open('config/paths.json', 'r') as f:
                return json.load(f)
        except Exception:
            # Fallback
            return {
                'logs': {
                    'main_dir': 'D:\\MIA_IA_system\\LAUNCH\\logs'
                }
            }

    def get_current_log(self) -> str:
        """Lit le fichier pointeur pour trouver le log actif"""
        pointer_file = self.base_dir / ".current_log"

        if not pointer_file.exists():
            # Fallback: chercher le plus récent
            log_files = list(self.base_dir.glob("bot_production_*.log"))
            if log_files:
                latest = max(log_files, key=lambda p: p.stat().st_mtime)
                return latest.name
            return None

        try:
            with open(pointer_file, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if line.strip() and not line.startswith('#'):
                        return line.strip()
        except Exception as e:
            print(f"Erreur lecture pointeur: {e}")
            return None

    def read_trades_log(self, lines: int = 50):
        """Lit le log des trades du jour"""
        log_file = self.base_dir / 'trades' / f"trades_{self.date_str}.log"
        self._read_log_file(log_file, lines)

    def read_discord_log(self, lines: int = 50):
        """Lit le log Discord du jour"""
        log_file = self.base_dir / 'discord' / f"discord_{self.date_str}.log"
        self._read_log_file(log_file, lines)

    def read_signals_log(self, lines: int = 50):
        """Lit le log des signaux du jour"""
        log_file = self.base_dir / 'signals' / f"signals_{self.date_str}.log"
        self._read_log_file(log_file, lines)

    def read_dtc_log(self, lines: int = 50):
        """Lit le log DTC du jour"""
        log_file = self.base_dir / 'dtc' / f"dtc_orders_{self.date_str}.log"
        self._read_log_file(log_file, lines)

    def read_errors_log(self, critical_only: bool = False):
        """Lit le log des erreurs"""
        if critical_only:
            log_file = self.base_dir / f"bot_CRITICAL_{self.date_str}.log"
        else:
            log_file = self.base_dir / f"bot_ERROR_{self.date_str}.log"

        self._read_log_file(log_file, lines=100)

    def read_summary(self):
        """Lit le résumé quotidien"""
        summary_file = self.base_dir / 'summaries' / f"SUMMARY_{self.date_str}.txt"

        if not summary_file.exists():
            print(f"[X] Resume non trouve: {summary_file}")
            print("   Le resume est genere a l'arret du bot ou a 23h59")
            return

        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                print(f.read())
        except Exception as e:
            print(f"Erreur lecture résumé: {e}")

    def read_json_events(self, event_type: str = None, lines: int = 50):
        """Lit les événements JSON"""
        json_file = self.base_dir / 'json' / f"events_{self.date_str}.jsonl"

        if not json_file.exists():
            print(f"[X] Fichier JSON non trouve: {json_file}")
            return

        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                events = [json.loads(line) for line in f.readlines()]

            # Filtrer par type si demandé
            if event_type:
                events = [e for e in events if e['type'] == event_type]

            # Afficher les derniers
            for event in events[-lines:]:
                print(json.dumps(event, indent=2))
                print("-" * 40)

        except Exception as e:
            print(f"Erreur lecture JSON: {e}")

    def _read_log_file(self, log_file: Path, lines: int = 50):
        """Lit les dernières lignes d'un fichier log"""
        if not log_file.exists():
            print(f"[X] Fichier non trouve: {log_file}")
            print(f"   Le fichier sera cree au premier evenement")
            return

        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()

            # Afficher les dernières lignes
            print(f"\n{'='*80}")
            print(f"{log_file.name} (dernieres {min(lines, len(all_lines))} lignes)")
            print('='*80 + '\n')

            for line in all_lines[-lines:]:
                print(line.rstrip())

        except Exception as e:
            print(f"Erreur lecture fichier: {e}")

    def list_available_logs(self):
        """Liste tous les logs disponibles aujourd'hui"""
        print(f"\n{'='*80}")
        print(f"LOGS DISPONIBLES - {self.date_str}")
        print('='*80 + '\n')

        # Log principal
        current = self.get_current_log()
        if current:
            main_log = self.base_dir / current
            size_mb = main_log.stat().st_size / (1024 * 1024) if main_log.exists() else 0
            print(f"[PRINCIPAL]:")
            print(f"   {current}")
            print(f"   Taille: {size_mb:.2f} MB\n")

        # Logs par niveau
        print("LOGS PAR NIVEAU:")
        for level in ['INFO', 'WARNING', 'ERROR', 'CRITICAL']:
            log_file = self.base_dir / f"bot_{level}_{self.date_str}.log"
            if log_file.exists():
                size_mb = log_file.stat().st_size / (1024 * 1024)
                print(f"   {level:10} : {log_file.name:40} ({size_mb:.2f} MB)")

        # Logs thématiques
        print("\nLOGS THEMATIQUES:")
        themes = ['trades', 'discord', 'signals', 'dtc', 'performance']
        for theme in themes:
            theme_dir = self.base_dir / theme
            if theme_dir.exists():
                log_file = theme_dir / f"{theme}_{self.date_str}.log"
                if log_file.exists():
                    size_kb = log_file.stat().st_size / 1024
                    lines = len(open(log_file, 'r', encoding='utf-8').readlines())
                    print(f"   {theme:10} : {log_file.name:40} ({size_kb:.1f} KB, {lines} lignes)")

        # Résumé
        print("\nRESUME:")
        summary_file = self.base_dir / 'summaries' / f"SUMMARY_{self.date_str}.txt"
        if summary_file.exists():
            print(f"   [OK] Disponible: {summary_file.name}")
        else:
            print(f"   [ATTENTE] Pas encore genere (sera cree a l'arret du bot)")

        print("\n" + "="*80)


def main():
    parser = argparse.ArgumentParser(description="Lecteur de logs MIA simplifié")
    parser.add_argument('--today', choices=['trades', 'discord', 'signals', 'dtc', 'errors'],
                       help="Afficher un log thématique du jour")
    parser.add_argument('--summary', action='store_true', help="Afficher le résumé quotidien")
    parser.add_argument('--list', action='store_true', help="Lister tous les logs disponibles")
    parser.add_argument('--json', type=str, help="Afficher événements JSON (optionnel: filtrer par type)")
    parser.add_argument('--critical', action='store_true', help="Erreurs critiques uniquement")
    parser.add_argument('--lines', type=int, default=50, help="Nombre de lignes à afficher (défaut: 50)")

    args = parser.parse_args()

    reader = LogReader()

    if args.list:
        reader.list_available_logs()

    elif args.summary:
        reader.read_summary()

    elif args.today:
        if args.today == 'trades':
            reader.read_trades_log(args.lines)
        elif args.today == 'discord':
            reader.read_discord_log(args.lines)
        elif args.today == 'signals':
            reader.read_signals_log(args.lines)
        elif args.today == 'dtc':
            reader.read_dtc_log(args.lines)
        elif args.today == 'errors':
            reader.read_errors_log(args.critical)

    elif args.json:
        event_type = args.json if args.json != 'all' else None
        reader.read_json_events(event_type, args.lines)

    else:
        # Par défaut: lister les logs
        reader.list_available_logs()
        print("\n[INFO] Utilisation:")
        print("   python utils/log_reader.py --list")
        print("   python utils/log_reader.py --today trades")
        print("   python utils/log_reader.py --today discord")
        print("   python utils/log_reader.py --today errors --critical")
        print("   python utils/log_reader.py --summary")
        print("   python utils/log_reader.py --json trade")


if __name__ == "__main__":
    main()
