"""
Page d'inscription
"""
import streamlit as st
import sys
import base64
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t, get_language, set_language
from auth.authentication import register_user, is_authenticated
from auth.email_service import send_welcome_email
from database import subscribe_newsletter
from config import STATIC_DIR


def get_logo_base64():
    """Retourne le logo encodé en base64"""
    logo_path = STATIC_DIR / "logo_mia_dark.jpeg"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


def render_register():
    """Affiche la page d'inscription"""

    # Rediriger si déjà connecté
    if is_authenticated():
        st.session_state.page = 'landing'
        st.rerun()

    # CSS
    st.markdown("""
    <style>
        .auth-container {
            max-width: 450px;
            margin: 2rem auto;
            background: #131722;
            border: 1px solid #2A3447;
            border-radius: 16px;
            padding: 2.5rem;
        }

        .auth-header {
            text-align: center;
            margin-bottom: 1.5rem;
        }

        .auth-logo {
            font-size: 3rem;
            margin-bottom: 0.75rem;
        }

        .auth-title {
            font-size: 1.6rem;
            font-weight: 700;
            color: white;
        }

        .password-hint {
            font-size: 0.8rem;
            color: #8892A0;
            margin-top: -10px;
            margin-bottom: 10px;
        }

        .auth-divider {
            display: flex;
            align-items: center;
            margin: 1rem 0;
            color: #8892A0;
        }

        .auth-divider::before,
        .auth-divider::after {
            content: '';
            flex: 1;
            height: 1px;
            background: #2A3447;
        }

        .auth-divider span {
            padding: 0 1rem;
            font-size: 0.9rem;
        }

        .google-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            width: 100%;
            padding: 12px;
            background: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            color: #333;
            cursor: not-allowed;
            opacity: 0.7;
        }
    </style>
    """, unsafe_allow_html=True)

    # Layout
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Sélecteur de langue
        lang_col1, lang_col2, lang_col3 = st.columns([1, 2, 1])
        with lang_col3:
            lang_cols = st.columns(2)
            with lang_cols[0]:
                if st.button("🇫🇷", key='reg_lang_fr', use_container_width=True):
                    set_language('fr')
                    st.rerun()
            with lang_cols[1]:
                if st.button("🇬🇧", key='reg_lang_en', use_container_width=True):
                    set_language('en')
                    st.rerun()

        logo_b64 = get_logo_base64()
        if logo_b64:
            logo_html = f'<img src="data:image/jpeg;base64,{logo_b64}" style="height: 80px; width: auto; border-radius: 12px;">'
        else:
            logo_html = '<div class="auth-logo">🤖</div>'

        st.markdown(f"""
        <div class="auth-container">
            <div class="auth-header">
                {logo_html}
                <h1 class="auth-title" style="margin-top: 1rem;">{t('auth.register.title')}</h1>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Bouton Google (désactivé)
        st.markdown(f"""
        <button class="google-btn" disabled title="Configuration Google OAuth requise">
            <svg width="18" height="18" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            {t('auth.register.google')}
        </button>
        <div class="auth-divider"><span>{t('auth.register.or')}</span></div>
        """, unsafe_allow_html=True)

        # Formulaire d'inscription
        with st.form("register_form"):
            name = st.text_input(t('auth.register.name'), placeholder="John Doe")
            email = st.text_input(t('auth.register.email'), placeholder="email@exemple.com")
            password = st.text_input(t('auth.register.password'), type="password")
            st.markdown(f"<p class='password-hint'>{t('auth.register.password_hint')}</p>", unsafe_allow_html=True)
            confirm_password = st.text_input(t('auth.register.confirm_password'), type="password")

            terms = st.checkbox(t('auth.register.terms'))
            newsletter = st.checkbox(t('auth.register.newsletter'), value=True)

            submitted = st.form_submit_button(t('auth.register.submit'), use_container_width=True, type="primary")

            if submitted:
                lang = get_language()
                if not terms:
                    st.error("Vous devez accepter les conditions" if lang == 'fr' else "You must accept the terms")
                elif password != confirm_password:
                    st.error("Les mots de passe ne correspondent pas" if lang == 'fr' else "Passwords don't match")
                else:
                    success, message = register_user(email, password, name, lang)
                    if success:
                        st.success(message)
                        # Envoyer email de bienvenue
                        send_welcome_email(email, name, lang)
                        # Inscrire à la newsletter si coché
                        if newsletter:
                            subscribe_newsletter(email, lang)
                        st.session_state.page = 'login'
                        st.rerun()
                    else:
                        st.error(message)

        # Lien connexion
        if st.button(t('auth.register.login_link'), key='login-link', use_container_width=True):
            st.session_state.page = 'login'
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Bouton retour
        if st.button("← " + t('nav.home'), key='back-home-reg'):
            st.session_state.page = 'landing'
            st.rerun()
