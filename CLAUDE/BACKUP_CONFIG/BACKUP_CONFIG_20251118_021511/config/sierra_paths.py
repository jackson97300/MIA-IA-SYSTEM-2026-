"""
Configuration des chemins Sierra Chart
Évite les chemins Windows en dur dans le code
"""

from pathlib import Path
import os
from datetime import datetime

# Chemin de base du projet
BASE_DIR = Path(os.getenv("MIA_BASE_DIR", r"D:\MIA_IA_system"))

# Chemins spécifiques
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"

# Vérification que le répertoire existe
if not BASE_DIR.exists():
    BASE_DIR.mkdir(parents=True, exist_ok=True)

# === Graphs par défaut ===
# Ordre logique: 10 (MenthorQ), 3 (temps réel + VWAP/VVA), 4 (historique/VWAP précédent), 8 (VIX)
DEFAULT_CHARTS = [10, 3, 4, 8]

# === Helpers de chemins ===
def get_today_date_str() -> str:
    """YYYYMMDD du jour (timezone locale)"""
    return datetime.now().strftime("%Y%m%d")

def get_current_date_str() -> str:
    """Alias pour compatibilité tests"""
    return get_today_date_str()

def per_chart_daily_path(chart: int, date_str: str = None) -> Path:
    """Chemin d'un fichier par graph: chart_{N}_{YYYYMMDD}.jsonl"""
    date_str = date_str or get_today_date_str()
    filename = f"chart_{chart}_{date_str}.jsonl"
    return BASE_DIR / filename

def unified_daily_path(date_str: str = None) -> Path:
    """Chemin du fichier unifié: mia_unified_{YYYYMMDD}.jsonl"""
    date_str = date_str or get_today_date_str()
    filename = f"mia_unified_{date_str}.jsonl"
    return BASE_DIR / filename