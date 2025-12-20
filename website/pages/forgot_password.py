"""
Page mot de passe oublié
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t, set_language
from auth.authentication import request_password_reset, is_authenticated, is_valid_email


def render_forgot_password():
    """Affiche la page mot de passe oublié"""
    
    if is_authenticated():
        st.session_state.page = 'landing'
        st.rerun()
    
    # CSS
    st.markdown("""
    <style>
        .auth-container {
            max-width: 450px;
            margin: 4rem auto;
            background: #131722;
            border: 1px solid #2A3447;
            border-radius: 16px;
            padding: 3rem;
        }
        
        .auth-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .auth-logo {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        .auth-title {
            font-size: 1.8rem;
            font-weight: 700;
            color: white;
            margin-bottom: 1rem;
        }
        
        .auth-description {
            color: #8892A0;
            line-height: 1.6;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # Sélecteur de langue
        lang_cols = st.columns([1, 1, 2])
        with lang_cols[0]:
            if st.button("🇫🇷", key='forgot_lang_fr'):
                set_language('fr')
                st.rerun()
        with lang_cols[1]:
            if st.button("🇬🇧", key='forgot_lang_en'):
                set_language('en')
                st.rerun()
        
        st.markdown(f"""
        <div class="auth-container">
            <div class="auth-header">
                <div class="auth-logo">🔐</div>
                <h1 class="auth-title">{t('auth.forgot_password.title')}</h1>
                <p class="auth-description">{t('auth.forgot_password.description')}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Formulaire
        with st.form("forgot_form"):
            email = st.text_input(t('auth.forgot_password.email'), placeholder="email@exemple.com")
            submitted = st.form_submit_button(t('auth.forgot_password.submit'), use_container_width=True, type="primary")
            
            if submitted:
                if not email or not is_valid_email(email):
                    st.error("Veuillez entrer un email valide")
                else:
                    success, message = request_password_reset(email)
                    st.success(message)
        
        # Lien retour
        if st.button("← " + t('auth.forgot_password.back'), key='back-login'):
            st.session_state.page = 'login'
            st.rerun()



