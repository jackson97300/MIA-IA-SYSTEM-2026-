"""
Section Newsletter
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t, get_language
from database import subscribe_newsletter
from auth.authentication import is_valid_email
from auth.email_service import send_newsletter_confirmation


def render_newsletter():
    """Affiche la section newsletter"""
    
    st.markdown("""
    <style>
        .newsletter-section {
            padding: 4rem 2rem;
            background: linear-gradient(135deg, rgba(0, 212, 170, 0.1), rgba(30, 58, 95, 0.2));
            border-radius: 20px;
            max-width: 700px;
            margin: 3rem auto;
            text-align: center;
        }
        
        .newsletter-title {
            font-size: 2rem;
            font-weight: 700;
            color: white;
            margin-bottom: 1rem;
        }
        
        .newsletter-description {
            color: #B8C1CC;
            margin-bottom: 2rem;
            font-size: 1.1rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="newsletter-section" id="newsletter">
        <h2 class="newsletter-title">📬 {t('newsletter.title')}</h2>
        <p class="newsletter-description">{t('newsletter.description')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Formulaire
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("newsletter_form", clear_on_submit=True):
            email = st.text_input(
                t('newsletter.placeholder'),
                placeholder=t('newsletter.placeholder'),
                label_visibility="collapsed"
            )
            submitted = st.form_submit_button(t('newsletter.button'), use_container_width=True)
            
            if submitted:
                if not email:
                    st.error(t('newsletter.invalid'))
                elif not is_valid_email(email):
                    st.error(t('newsletter.invalid'))
                else:
                    success = subscribe_newsletter(email, get_language())
                    if success:
                        st.success(t('newsletter.success'))
                        # Envoyer email de confirmation
                        send_newsletter_confirmation(email, get_language())
                    else:
                        st.warning(t('newsletter.error'))



