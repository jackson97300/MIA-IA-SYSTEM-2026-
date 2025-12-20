"""
Styles CSS globaux pour le site
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import COLORS


def get_global_styles() -> str:
    """Retourne les styles CSS globaux"""
    return f"""
    <style>
        /* Import Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');
        
        /* Variables CSS */
        :root {{
            --primary: {COLORS['primary']};
            --secondary: {COLORS['secondary']};
            --accent: {COLORS['accent']};
            --background: {COLORS['background']};
            --background-card: {COLORS['background_card']};
            --background-light: {COLORS['background_light']};
            --text-primary: {COLORS['text_primary']};
            --text-secondary: {COLORS['text_secondary']};
            --success: {COLORS['success']};
            --warning: {COLORS['warning']};
            --error: {COLORS['error']};
            --border: {COLORS['border']};
        }}
        
        /* Reset et base */
        .stApp {{
            background-color: var(--background) !important;
            font-family: 'Inter', sans-serif !important;
        }}
        
        /* Masquer le header Streamlit par défaut */
        header[data-testid="stHeader"] {{
            display: none !important;
        }}
        
        /* Masquer le footer Streamlit */
        footer {{
            display: none !important;
        }}
        
        /* Masquer le menu hamburger */
        .stDeployButton {{
            display: none !important;
        }}
        
        #MainMenu {{
            visibility: hidden !important;
        }}
        
        /* Liens */
        a {{
            color: var(--secondary) !important;
            text-decoration: none !important;
            transition: opacity 0.2s ease;
        }}
        
        a:hover {{
            opacity: 0.8;
        }}
        
        /* Boutons primaires */
        .btn-primary {{
            background: linear-gradient(135deg, var(--secondary), #00B894) !important;
            color: var(--background) !important;
            padding: 12px 28px !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            border: none !important;
            cursor: pointer !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
            display: inline-block !important;
            text-align: center !important;
        }}
        
        .btn-primary:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(0, 212, 170, 0.3) !important;
        }}
        
        /* Boutons secondaires */
        .btn-secondary {{
            background: transparent !important;
            color: var(--text-primary) !important;
            padding: 12px 28px !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            border: 2px solid var(--border) !important;
            cursor: pointer !important;
            transition: all 0.2s ease !important;
        }}
        
        .btn-secondary:hover {{
            border-color: var(--secondary) !important;
            color: var(--secondary) !important;
        }}
        
        /* Cards */
        .card {{
            background: var(--background-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            padding: 24px !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        }}
        
        .card:hover {{
            transform: translateY(-4px) !important;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3) !important;
        }}
        
        /* Titres de section */
        .section-title {{
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            color: var(--text-primary) !important;
            text-align: center !important;
            margin-bottom: 0.5rem !important;
        }}
        
        .section-subtitle {{
            font-size: 1.1rem !important;
            color: var(--text-secondary) !important;
            text-align: center !important;
            margin-bottom: 3rem !important;
        }}
        
        /* Inputs */
        .stTextInput > div > div > input {{
            background-color: var(--background-card) !important;
            border: 1px solid var(--border) !important;
            color: var(--text-primary) !important;
            border-radius: 8px !important;
            padding: 12px 16px !important;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: var(--secondary) !important;
            box-shadow: 0 0 0 2px rgba(0, 212, 170, 0.2) !important;
        }}
        
        /* Text area */
        .stTextArea > div > div > textarea {{
            background-color: var(--background-card) !important;
            border: 1px solid var(--border) !important;
            color: var(--text-primary) !important;
            border-radius: 8px !important;
        }}
        
        /* Streamlit buttons override */
        .stButton > button {{
            background: linear-gradient(135deg, var(--secondary), #00B894) !important;
            color: var(--background) !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 12px 28px !important;
            font-weight: 600 !important;
            transition: all 0.2s ease !important;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 25px rgba(0, 212, 170, 0.3) !important;
        }}
        
        /* Expander (pour FAQ) */
        .streamlit-expanderHeader {{
            background-color: var(--background-card) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            color: var(--text-primary) !important;
        }}
        
        .streamlit-expanderContent {{
            background-color: var(--background-light) !important;
            border: 1px solid var(--border) !important;
            border-top: none !important;
            color: var(--text-secondary) !important;
        }}
        
        /* Checkbox */
        .stCheckbox > label {{
            color: var(--text-secondary) !important;
        }}
        
        /* Select box */
        .stSelectbox > div > div {{
            background-color: var(--background-card) !important;
            border-color: var(--border) !important;
        }}
        
        /* Divider */
        hr {{
            border: none !important;
            border-top: 1px solid var(--border) !important;
            margin: 2rem 0 !important;
        }}
        
        /* Animations */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .fade-in {{
            animation: fadeIn 0.6s ease forwards;
        }}
        
        @keyframes float {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-10px); }}
        }}
        
        /* Responsive */
        @media (max-width: 768px) {{
            .section-title {{
                font-size: 1.8rem !important;
            }}
            
            .section-subtitle {{
                font-size: 1rem !important;
            }}
        }}
    </style>
    """



