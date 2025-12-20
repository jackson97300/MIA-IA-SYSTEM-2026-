"""
Configuration du site MIA IA SYSTEM
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════════
# CHEMINS
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
I18N_DIR = BASE_DIR / "i18n"
ASSETS_DIR = BASE_DIR / "static"  # Chemin relatif compatible Linux/VPS

# Créer les dossiers si nécessaire
DATA_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# BASE DE DONNÉES
# ═══════════════════════════════════════════════════════════════════════════════

DATABASE_PATH = DATA_DIR / "mia_users.db"

# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL
# ═══════════════════════════════════════════════════════════════════════════════

EMAIL_CONFIG = {
    "address": os.getenv("EMAIL_ADDRESS", "MIA.IA.SYSTEM@GMAIL.COM"),
    "password": os.getenv("EMAIL_PASSWORD", ""),
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
}

# ═══════════════════════════════════════════════════════════════════════════════
# URLS
# ═══════════════════════════════════════════════════════════════════════════════

SITE_URL = os.getenv("SITE_URL", "https://mia-ia-system.com")
COPILOT_URL = os.getenv("COPILOT_URL", "http://localhost:8503")

# ═══════════════════════════════════════════════════════════════════════════════
# GOOGLE OAUTH
# ═══════════════════════════════════════════════════════════════════════════════

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# ═══════════════════════════════════════════════════════════════════════════════
# SECRET KEY
# ═══════════════════════════════════════════════════════════════════════════════

SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret_key_in_production")

# ═══════════════════════════════════════════════════════════════════════════════
# COULEURS DU THÈME
# ═══════════════════════════════════════════════════════════════════════════════

COLORS = {
    "primary": "#1E3A5F",           # Bleu foncé
    "secondary": "#00D4AA",         # Vert turquoise
    "accent": "#FFD700",            # Or
    "background": "#0A0E17",        # Noir profond
    "background_card": "#131722",   # Cartes
    "background_light": "#1C2333",  # Sections alternées
    "text_primary": "#FFFFFF",      # Texte principal
    "text_secondary": "#8892A0",    # Texte secondaire
    "success": "#00C853",           # Vert succès
    "warning": "#FFB300",           # Orange warning
    "error": "#FF5252",             # Rouge erreur
    "border": "#2A3447",            # Bordures
}

# ═══════════════════════════════════════════════════════════════════════════════
# INFORMATIONS LÉGALES (À COMPLÉTER)
# ═══════════════════════════════════════════════════════════════════════════════

LEGAL_INFO = {
    "owner_name": "[À COMPLÉTER]",
    "owner_status": "[Particulier / Auto-entrepreneur / Société]",
    "owner_email": "MIA.IA.SYSTEM@GMAIL.COM",
    "host_name": "Cloudflare, Inc.",
    "host_address": "101 Townsend St, San Francisco, CA 94107, USA",
    "domain": "mia-ia-system.com",
}
