"""
Page profil utilisateur
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t, get_language, set_language
from auth.authentication import (
    is_authenticated, 
    get_current_user, 
    logout_user,
    is_valid_password
)
from database import update_user_password, update_user_language
from config import COPILOT_URL


def render_profile():
    """Affiche la page profil"""
    
    if not is_authenticated():
        st.session_state.page = 'login'
        st.rerun()
    
    user = get_current_user()
    
    # CSS
    st.markdown("""
    <style>
        .profile-container {
            max-width: 600px;
            margin: 2rem auto;
        }
        
        .profile-header {
            background: #131722;
            border: 1px solid #2A3447;
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            margin-bottom: 2rem;
        }
        
        .profile-avatar {
            font-size: 4rem;
            margin-bottom: 1rem;
        }
        
        .profile-name {
            font-size: 1.5rem;
            font-weight: 700;
            color: white;
            margin-bottom: 0.5rem;
        }
        
        .profile-email {
            color: #8892A0;
        }
        
        .profile-section {
            background: #131722;
            border: 1px solid #2A3447;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
        
        .profile-section-title {
            font-size: 1.1rem;
            font-weight: 600;
            color: white;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col2:
        # Header avec infos utilisateur
        name = user.get('name', 'Utilisateur') if user else 'Utilisateur'
        email = user.get('email', '') if user else ''
        
        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-avatar">👤</div>
            <div class="profile-name">{name}</div>
            <div class="profile-email">{email}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Bouton accès Dashboard
        st.markdown(f"""
        <div class="profile-section">
            <h3 class="profile-section-title">🚀 {t('nav.dashboard')}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"🚀 {t('hero.cta_primary')}", use_container_width=True, type="primary"):
            st.markdown(f'<meta http-equiv="refresh" content="0;url={COPILOT_URL}">', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Section Langue
        st.markdown("""
        <div class="profile-section">
            <h3 class="profile-section-title">🌍 Langue / Language</h3>
        </div>
        """, unsafe_allow_html=True)
        
        lang_col1, lang_col2 = st.columns(2)
        current_lang = get_language()
        with lang_col1:
            if st.button("🇫🇷 Français", use_container_width=True, 
                        type="primary" if current_lang == 'fr' else "secondary"):
                set_language('fr')
                if user:
                    update_user_language(user['id'], 'fr')
                st.rerun()
        with lang_col2:
            if st.button("🇬🇧 English", use_container_width=True,
                        type="primary" if current_lang == 'en' else "secondary"):
                set_language('en')
                if user:
                    update_user_language(user['id'], 'en')
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Section Mot de passe
        change_password = "Changer le mot de passe" if get_language() == 'fr' else "Change password"
        st.markdown(f"""
        <div class="profile-section">
            <h3 class="profile-section-title">🔐 {change_password}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("change_password_form"):
            new_password = st.text_input(
                t('auth.reset_password.password'), 
                type="password"
            )
            confirm_password = st.text_input(
                t('auth.reset_password.confirm'), 
                type="password"
            )
            
            if st.form_submit_button(t('common.save'), use_container_width=True):
                if new_password != confirm_password:
                    st.error("Les mots de passe ne correspondent pas")
                elif new_password:
                    is_valid, error = is_valid_password(new_password)
                    if not is_valid:
                        st.error(error)
                    else:
                        if user:
                            update_user_password(user['id'], new_password)
                        st.success(t('auth.reset_password.success'))
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Section Déconnexion
        logout_text = "Déconnexion" if get_language() == 'fr' else "Logout"
        if st.button(f"🚪 {logout_text}", use_container_width=True):
            logout_user()
            st.session_state.page = 'landing'
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Retour accueil
        if st.button("← " + t('nav.home'), key='back-home-profile'):
            st.session_state.page = 'landing'
            st.rerun()



