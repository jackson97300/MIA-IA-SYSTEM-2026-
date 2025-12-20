"""
Section Comment ça marche - Version Streamlit Native
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t


def render_how_it_works():
    """Affiche la section Comment ça marche avec composants Streamlit natifs"""

    steps = [
        {'num': 1, 'icon': '📝'},
        {'num': 2, 'icon': '🔐'},
        {'num': 3, 'icon': '👀'},
        {'num': 4, 'icon': '💰'},
    ]

    # CSS
    st.markdown("""
    <style>
        .step-box {
            text-align: center;
            padding: 1rem;
        }
        .step-number {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #00D4AA, #00B894);
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 1.3rem;
            font-weight: 700;
            color: #0A0E17;
            margin-bottom: 0.75rem;
        }
        .step-icon-big {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        .step-title-text {
            font-size: 1.1rem;
            font-weight: 600;
            color: white;
            margin-bottom: 0.3rem;
        }
        .step-desc-text {
            color: #8892A0;
            font-size: 0.9rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # Titre
    st.markdown(f"<h2 style='text-align: center; color: white; font-size: 2.5rem; margin-bottom: 0.5rem;'>{t('how_it_works.title')}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #8892A0; margin-bottom: 2rem;'>{t('how_it_works.subtitle')}</p>", unsafe_allow_html=True)

    # 4 colonnes
    cols = st.columns(4)
    for idx, col in enumerate(cols):
        step = steps[idx]
        title = t(f"how_it_works.steps.{step['num']}.title")
        desc = t(f"how_it_works.steps.{step['num']}.description")
        with col:
            st.markdown(f"""
            <div class="step-box">
                <div class="step-number">{step['num']}</div>
                <div class="step-icon-big">{step['icon']}</div>
                <div class="step-title-text">{title}</div>
                <div class="step-desc-text">{desc}</div>
            </div>
            """, unsafe_allow_html=True)
