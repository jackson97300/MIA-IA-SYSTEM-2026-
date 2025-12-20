"""
Section Hero de la landing page
"""
import streamlit as st
import sys
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t
from auth.authentication import is_authenticated
from config import COPILOT_URL, STATIC_DIR


def get_logo_base64():
    """Retourne le logo encodé en base64"""
    logo_path = STATIC_DIR / "logo_mia_dark.jpeg"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


def render_hero():
    """Affiche la section hero"""

    logo_b64 = get_logo_base64()

    # CSS pour la section hero - fond harmonisé avec le logo
    hero_css = """
    <style>
        .hero-section {
            text-align: center;
            padding: 5rem 2rem 5rem 2rem;
            background: linear-gradient(180deg,
                rgba(10, 14, 23, 1) 0%,
                rgba(18, 28, 45, 1) 50%,
                rgba(10, 14, 23, 1) 100%);
            position: relative;
        }

        .hero-logo-container {
            margin-bottom: 2rem;
            animation: float 4s ease-in-out infinite;
            display: inline-block;
            position: relative;
        }

        /* Anneau doré externe avec glow */
        .hero-logo-container::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 280px;
            height: 280px;
            border: 3px solid rgba(212, 175, 55, 0.6);
            border-radius: 50%;
            z-index: 1;
            box-shadow:
                0 0 30px rgba(212, 175, 55, 0.4),
                0 0 60px rgba(0, 180, 220, 0.2),
                inset 0 0 30px rgba(212, 175, 55, 0.1);
            animation: ringPulse 3s ease-in-out infinite;
        }

        /* Second anneau externe */
        .hero-logo-container::after {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 320px;
            height: 320px;
            border: 1px solid rgba(212, 175, 55, 0.2);
            border-radius: 50%;
            z-index: 0;
            animation: ringPulse2 4s ease-in-out infinite;
        }

        @keyframes ringPulse {
            0%, 100% {
                transform: translate(-50%, -50%) scale(1);
                box-shadow:
                    0 0 30px rgba(212, 175, 55, 0.4),
                    0 0 60px rgba(0, 180, 220, 0.2),
                    inset 0 0 30px rgba(212, 175, 55, 0.1);
            }
            50% {
                transform: translate(-50%, -50%) scale(1.02);
                box-shadow:
                    0 0 50px rgba(212, 175, 55, 0.6),
                    0 0 80px rgba(0, 180, 220, 0.3),
                    inset 0 0 40px rgba(212, 175, 55, 0.2);
            }
        }

        @keyframes ringPulse2 {
            0%, 100% {
                transform: translate(-50%, -50%) scale(1);
                opacity: 0.3;
            }
            50% {
                transform: translate(-50%, -50%) scale(1.03);
                opacity: 0.6;
            }
        }

        .hero-logo {
            height: 250px;
            width: 250px;
            border-radius: 50%;
            object-fit: cover;
            object-position: center 35%;
            position: relative;
            z-index: 2;
            clip-path: circle(50% at center);
            box-shadow:
                0 0 40px rgba(212, 175, 55, 0.5),
                0 0 80px rgba(0, 180, 220, 0.3);
            transition: all 0.4s ease;
            border: 3px solid rgba(212, 175, 55, 0.7);
            animation: logoGlow 4s ease-in-out infinite;
            image-rendering: -webkit-optimize-contrast;
            image-rendering: crisp-edges;
        }

        @keyframes logoGlow {
            0%, 100% {
                box-shadow:
                    0 0 40px rgba(212, 175, 55, 0.5),
                    0 0 80px rgba(0, 180, 220, 0.3);
                border-color: rgba(212, 175, 55, 0.7);
            }
            50% {
                box-shadow:
                    0 0 60px rgba(212, 175, 55, 0.7),
                    0 0 100px rgba(0, 180, 220, 0.4);
                border-color: rgba(212, 175, 55, 0.9);
            }
        }

        .hero-logo:hover {
            transform: scale(1.05);
        }

        .hero-icon {
            font-size: 8rem;
            margin-bottom: 1rem;
            animation: float 4s ease-in-out infinite;
        }

        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-20px); }
        }

        .hero-title {
            font-size: 3.5rem;
            font-weight: 800;
            color: white;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #FFFFFF, #00D4AA, #D4AF37);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .hero-subtitle {
            font-size: 1.5rem;
            color: #00D4AA;
            margin-bottom: 1rem;
            font-weight: 500;
        }

        .hero-description {
            font-size: 1.2rem;
            color: #8892A0;
            max-width: 700px;
            margin: 0 auto 2.5rem auto;
            line-height: 1.7;
        }
    </style>
    """

    st.markdown(hero_css, unsafe_allow_html=True)

    # Récupérer les traductions
    hero_title = t('hero.title')
    hero_subtitle = t('hero.subtitle')
    hero_description = t('hero.description')

    # Construire le HTML du hero
    if logo_b64:
        logo_html = f'<div class="hero-logo-container"><img src="data:image/jpeg;base64,{logo_b64}" class="hero-logo" alt="MIA IA SYSTEM"></div>'
    else:
        logo_html = '<div class="hero-icon">🤖</div>'

    hero_html = f'''<div class="hero-section">
{logo_html}
<h1 class="hero-title">{hero_title}</h1>
<p class="hero-subtitle">{hero_subtitle}</p>
<p class="hero-description">{hero_description}</p>
</div>'''

    st.markdown(hero_html, unsafe_allow_html=True)

    # Boutons CTA avec Streamlit natif
    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        cta_text = t('hero.cta_primary')
        if st.button(f"🚀 {cta_text}", key='hero-cta', use_container_width=True, type='primary'):
            if is_authenticated():
                st.markdown(f'<meta http-equiv="refresh" content="0;url={COPILOT_URL}">', unsafe_allow_html=True)
            else:
                st.session_state.page = 'login'
                st.rerun()
