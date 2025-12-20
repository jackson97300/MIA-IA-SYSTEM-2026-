"""
Section Contact
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t, get_language
from database import save_contact_message
from auth.authentication import is_valid_email


def render_contact():
    """Affiche la section contact"""
    
    st.markdown("""
    <style>
        .contact-section {
            padding: 5rem 2rem;
        }
        
        .contact-container {
            max-width: 600px;
            margin: 0 auto;
            background: #131722;
            border: 1px solid #2A3447;
            border-radius: 16px;
            padding: 2.5rem;
        }
        
        .contact-email {
            text-align: center;
            margin-bottom: 2rem;
            padding: 1rem;
            background: rgba(0, 212, 170, 0.1);
            border-radius: 8px;
        }
        
        .contact-email a {
            color: #00D4AA;
            font-size: 1.1rem;
            font-weight: 500;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="contact-section" id="contact">
        <h2 class="section-title">{t('contact.title')}</h2>
        <p class="section-subtitle">{t('contact.description')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Formulaire de contact
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div class="contact-email">
            📧 <a href="mailto:MIA.IA.SYSTEM@GMAIL.COM">MIA.IA.SYSTEM@GMAIL.COM</a>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("contact_form", clear_on_submit=True):
            name = st.text_input(t('contact.form.name'))
            email = st.text_input(t('contact.form.email'))
            message = st.text_area(t('contact.form.message'), height=150)
            
            submitted = st.form_submit_button(t('contact.form.submit'), use_container_width=True)
            
            if submitted:
                lang = get_language()
                if not name or not email or not message:
                    st.error("Veuillez remplir tous les champs" if lang == 'fr' else "Please fill all fields")
                elif not is_valid_email(email):
                    st.error("Email invalide" if lang == 'fr' else "Invalid email")
                else:
                    save_contact_message(name, email, message)
                    st.success(t('contact.success'))



