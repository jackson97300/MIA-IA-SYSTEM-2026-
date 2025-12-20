"""
Section À propos / Histoire de MIA
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t


def render_about():
    """Affiche la section À propos"""
    
    st.markdown("""
    <style>
        .about-section {
            padding: 5rem 2rem;
            background: linear-gradient(180deg, transparent, rgba(19, 23, 34, 0.5));
        }
        
        .about-container {
            max-width: 800px;
            margin: 0 auto;
            background: #131722;
            border: 1px solid #2A3447;
            border-radius: 16px;
            padding: 3rem;
        }
        
        .about-title {
            font-size: 2rem;
            font-weight: 700;
            color: white;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .about-story {
            color: #B8C1CC;
            font-size: 1.1rem;
            line-height: 1.9;
            white-space: pre-line;
        }
        
        .about-signature {
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px solid #2A3447;
            color: #00D4AA;
            font-style: italic;
            font-size: 1.1rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    story = t('about.story').replace('\\n', '\n')
    
    st.markdown(f"""
    <div class="about-section" id="about">
        <div class="about-container">
            <h2 class="about-title">📖 {t('about.title')}</h2>
            <p class="about-story">{story}</p>
            <p class="about-signature">{t('about.signature')}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)



