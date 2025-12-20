"""
Section FAQ
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t


def render_faq():
    """Affiche la section FAQ"""
    
    st.markdown("""
    <style>
        .faq-section {
            padding: 5rem 2rem;
            background: linear-gradient(180deg, transparent, rgba(19, 23, 34, 0.5));
        }
        
        .faq-container {
            max-width: 800px;
            margin: 0 auto;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="faq-section" id="faq">
        <h2 class="section-title">{t('faq.title')}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Utiliser les expanders Streamlit pour la FAQ
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        for i in range(1, 7):
            question = t(f'faq.items.{i}.question')
            answer = t(f'faq.items.{i}.answer')
            
            with st.expander(f"❓ {question}"):
                st.markdown(f"<p style='color: #B8C1CC; line-height: 1.7;'>{answer}</p>", unsafe_allow_html=True)



