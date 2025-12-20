"""
Reader simple pour les fichiers ML_READY unifiés
Lit les fichiers ml_*.jsonl générés par le dumper G3
"""
import json
import glob
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MLReadyReader:
    """Lecteur de fichiers ML_READY unifiés"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.live_config = config.get("live_mode", {})
        self.watch_dirs = self.live_config.get("realtime", {}).get("watch_dirs", [])
        self.chart_mapping = self.live_config.get("chart_mapping", {"NQ": 9, "ES": 3})

        logger.info(f"📁 MLReadyReader initialisé")
        logger.info(f"   Watch dirs: {self.watch_dirs}")
        logger.info(f"   Chart mapping: {self.chart_mapping}")

    def get_live_snapshot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Récupère la dernière ligne du fichier ML_READY pour un symbole

        Args:
            symbol: Symbole (ES ou NQ)

        Returns:
            Dernière ligne JSON du fichier ou None
        """
        try:
            # Trouver le chart ID pour ce symbole
            chart_id = self.chart_mapping.get(symbol)
            if not chart_id:
                logger.warning(f"⚠️ [{symbol}] Aucun chart mapping trouvé")
                return None

            # Trouver le répertoire correspondant
            chart_dir = None
            for watch_dir in self.watch_dirs:
                if f"CHART_{chart_id}" in watch_dir:
                    chart_dir = watch_dir
                    break

            if not chart_dir:
                logger.warning(f"⚠️ [{symbol}] Aucun watch_dir trouvé pour chart {chart_id}")
                return None

            # Chercher le fichier ml_*.jsonl
            pattern = os.path.join(chart_dir, "ml_*.jsonl")
            files = glob.glob(pattern)

            if not files:
                logger.debug(f"📊 [{symbol}] Aucun fichier ML_READY trouvé dans {chart_dir}")
                return None

            # Prendre le fichier le plus récent
            latest_file = max(files, key=os.path.getmtime)

            # Lire la dernière ligne (optimisé pour gros fichiers)
            with open(latest_file, 'rb') as f:
                # Aller à la fin du fichier
                try:
                    f.seek(-2, os.SEEK_END)
                    # Remonter jusqu'au dernier \n
                    while f.read(1) != b'\n':
                        f.seek(-2, os.SEEK_CUR)
                except OSError:
                    # Fichier trop petit, lire depuis le début
                    f.seek(0)

                last_line = f.readline().decode('utf-8').strip()

            if not last_line:
                logger.debug(f"📊 [{symbol}] Fichier vide: {latest_file}")
                return None

            # Parser le JSON
            data = json.loads(last_line)

            # Vérifier que c'est le bon symbole
            file_symbol = data.get("sym", "")
            if symbol in file_symbol or file_symbol.startswith(symbol):
                logger.debug(f"✅ [{symbol}] Données récupérées depuis {os.path.basename(latest_file)}")
                return data
            else:
                logger.warning(f"⚠️ [{symbol}] Symbole incorrect dans fichier: {file_symbol}")
                return None

        except FileNotFoundError:
            logger.debug(f"📊 [{symbol}] Fichier non trouvé")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"❌ [{symbol}] Erreur parsing JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ [{symbol}] Erreur lecture fichier: {e}")
            return None

    def read_latest_snapshot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Alias pour get_live_snapshot() - pour compatibilité avec le lanceur

        Args:
            symbol: Symbole (ES ou NQ)

        Returns:
            Dernière ligne JSON du fichier ou None
        """
        return self.get_live_snapshot(symbol)

    def is_live_mode_enabled(self) -> bool:
        """Vérifie si le mode live est activé"""
        return bool(self.watch_dirs)


def create_ml_ready_reader(config: Dict[str, Any]) -> MLReadyReader:
    """Factory pour créer un MLReadyReader"""
    return MLReadyReader(config)
