"""
Footer du site - Version Streamlit Native
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t


def render_footer():
    """Affiche le footer avec composants Streamlit natifs"""

    # CSS
    st.markdown("""
    <style>
        .footer-container {
            background: #0A0E17;
            border-top: 1px solid #2A3447;
            padding: 2rem 1rem;
            margin-top: 3rem;
        }
        .footer-title {
            color: white;
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.75rem;
        }
        .footer-link {
            display: block;
            color: #8892A0;
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
            text-decoration: none;
        }
        .footer-link:hover {
            color: #00D4AA;
        }
        .footer-bottom-section {
            text-align: center;
            padding-top: 1.5rem;
            margin-top: 1.5rem;
            border-top: 1px solid #2A3447;
        }
        .footer-copy {
            color: #8892A0;
            font-size: 0.85rem;
            margin-bottom: 1rem;
        }
        .footer-warn {
            color: #FFB300;
            font-size: 0.8rem;
            background: rgba(255, 179, 0, 0.1);
            padding: 1rem;
            border-radius: 8px;
            max-width: 700px;
            margin: 0 auto;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='footer-container'>", unsafe_allow_html=True)

    # 4 colonnes
    cols = st.columns(4)

    # Colonne 1 - Logo
    with cols[0]:
        st.markdown(f"""
        <div class="footer-title">🤖 MIA IA SYSTEM</div>
        <p style="color: #8892A0; font-size: 0.9rem;">{t('footer.description')}</p>
        """, unsafe_allow_html=True)

    # Colonne 2 - Liens
    with cols[1]:
        st.markdown(f"""
        <div class="footer-title">{t('footer.links.title')}</div>
        <a href="#" class="footer-link">{t('footer.links.home')}</a>
        <a href="#features" class="footer-link">{t('footer.links.features')}</a>
        <a href="#pricing" class="footer-link">{t('footer.links.pricing')}</a>
        <a href="#faq" class="footer-link">{t('footer.links.faq')}</a>
        """, unsafe_allow_html=True)

    # Colonne 3 - Légal
    with cols[2]:
        st.markdown(f"""
        <div class="footer-title">{t('footer.legal.title')}</div>
        <a href="#terms" class="footer-link">{t('footer.legal.terms')}</a>
        <a href="#privacy" class="footer-link">{t('footer.legal.privacy')}</a>
        <a href="#mentions" class="footer-link">{t('footer.legal.mentions')}</a>
        <a href="#risk" class="footer-link">{t('footer.legal.risk')}</a>
        """, unsafe_allow_html=True)

    # Colonne 4 - Contact
    with cols[3]:
        st.markdown(f"""
        <div class="footer-title">{t('footer.contact.title')}</div>
        <a href="mailto:MIA.IA.SYSTEM@GMAIL.COM" class="footer-link">📧 {t('footer.contact.email')}</a>
        """, unsafe_allow_html=True)

    # Bottom
    st.markdown(f"""
    <div class="footer-bottom-section">
        <p class="footer-copy">{t('footer.copyright')}</p>
        <p class="footer-warn">{t('footer.risk_warning')}</p>
    </div>
    </div>
    """, unsafe_allow_html=True)
