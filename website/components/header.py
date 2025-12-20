"""
Header du site avec navigation et sélecteur de langue
"""
import streamlit as st
import sys
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t, get_language, set_language, LANGUAGES
from auth.authentication import is_authenticated, logout_user, get_current_user
from config import STATIC_DIR


def get_logo_base64():
    """Retourne le logo encodé en base64"""
    logo_path = STATIC_DIR / "logo_mia_dark.jpeg"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


def render_header():
    """Affiche le header du site"""

    logo_b64 = get_logo_base64()

    # CSS pour le header avec animations
    header_css = """
    <style>
        .header-logo-container {
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
        }

        .header-logo {
            height: 50px;
            width: 50px;
            border-radius: 50%;
            object-fit: cover;
            object-position: center 35%;
            clip-path: circle(50% at center);
            border: 2px solid rgba(212, 175, 55, 0.6);
            box-shadow:
                0 0 15px rgba(212, 175, 55, 0.4),
                0 0 30px rgba(0, 180, 220, 0.2);
            transition: all 0.3s ease;
            animation: headerGlow 3s ease-in-out infinite;
            image-rendering: -webkit-optimize-contrast;
        }

        .header-logo:hover {
            transform: scale(1.1);
            box-shadow:
                0 0 25px rgba(212, 175, 55, 0.6),
                0 0 40px rgba(0, 180, 220, 0.3);
        }

        @keyframes headerGlow {
            0%, 100% {
                box-shadow:
                    0 0 15px rgba(212, 175, 55, 0.4),
                    0 0 30px rgba(0, 180, 220, 0.2);
                border-color: rgba(212, 175, 55, 0.6);
            }
            50% {
                box-shadow:
                    0 0 25px rgba(212, 175, 55, 0.6),
                    0 0 40px rgba(0, 180, 220, 0.4);
                border-color: rgba(212, 175, 55, 0.9);
            }
        }

        .header-title {
            font-size: 1.3rem;
            font-weight: 700;
            background: linear-gradient(90deg, #FFFFFF, #00D4AA, #D4AF37, #00D4AA, #FFFFFF);
            background-size: 200% auto;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            animation: shimmer 4s linear infinite;
        }

        @keyframes shimmer {
            0% { background-position: 0% center; }
            100% { background-position: 200% center; }
        }
    </style>
    """

    st.markdown(header_css, unsafe_allow_html=True)

    # Structure du header avec colonnes Streamlit
    col1, col2, col3 = st.columns([2, 4, 2])

    with col1:
        # Logo avec animation
        if logo_b64:
            st.markdown(f"""
            <div class="header-logo-container">
                <img src="data:image/jpeg;base64,{logo_b64}" class="header-logo" alt="MIA">
                <span class="header-title">MIA IA SYSTEM</span>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="header-logo-container">
                <span style="font-size: 2rem;">🤖</span>
                <span class="header-title">MIA IA SYSTEM</span>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        # Navigation
        nav_cols = st.columns(5)
        with nav_cols[0]:
            if st.button(t('nav.home'), key='nav_home', use_container_width=True):
                st.session_state.page = 'landing'
                st.rerun()
        with nav_cols[1]:
            if st.button(t('nav.features'), key='nav_features', use_container_width=True):
                st.session_state.scroll_to = 'features'
        with nav_cols[2]:
            if st.button(t('nav.pricing'), key='nav_pricing', use_container_width=True):
                st.session_state.scroll_to = 'pricing'
        with nav_cols[3]:
            if st.button(t('nav.faq'), key='nav_faq', use_container_width=True):
                st.session_state.scroll_to = 'faq'
        with nav_cols[4]:
            if st.button(t('nav.contact'), key='nav_contact', use_container_width=True):
                st.session_state.scroll_to = 'contact'

    with col3:
        # Actions (langue + auth)
        action_cols = st.columns([1, 1, 2])

        # Sélecteur de langue
        current_lang = get_language()
        with action_cols[0]:
            if st.button("FR", key='lang_fr', use_container_width=True,
                        type="primary" if current_lang == 'fr' else "secondary"):
                set_language('fr')
                st.rerun()
        with action_cols[1]:
            if st.button("EN", key='lang_en', use_container_width=True,
                        type="primary" if current_lang == 'en' else "secondary"):
                set_language('en')
                st.rerun()

        # Bouton auth
        with action_cols[2]:
            if is_authenticated():
                user = get_current_user()
                name = user.get('name', 'User')[:10] if user else 'User'
                if st.button(f"👤 {name}", key='nav_profile', use_container_width=True):
                    st.session_state.page = 'profile'
                    st.rerun()
            else:
                if st.button(t('nav.login'), key='nav_login', use_container_width=True):
                    st.session_state.page = 'login'
                    st.rerun()

    # Ligne de séparation
    st.markdown("<hr style='margin: 0; border-color: #2A3447;'>", unsafe_allow_html=True)
