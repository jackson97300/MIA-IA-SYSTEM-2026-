"""
Section Fonctionnalités - Version Streamlit Native
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t


def render_features():
    """Affiche la section fonctionnalités avec composants Streamlit natifs"""

    features = [
        {'key': 'realtime', 'icon': '📊'},
        {'key': 'signals', 'icon': '🎯'},
        {'key': 'automated', 'icon': '🤖'},
        {'key': 'multiplatform', 'icon': '📱'},
        {'key': 'alerts', 'icon': '🔔'},
        {'key': 'dashboard', 'icon': '📈'},
        {'key': 'education', 'icon': '🎓'},
        {'key': 'calendar', 'icon': '📅'},
    ]

    # CSS pour les cards
    st.markdown("""
    <style>
        .feature-box {
            background: #131722;
            border: 1px solid #2A3447;
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            transition: all 0.3s ease;
            height: 100%;
        }
        .feature-box:hover {
            border-color: #00D4AA;
            transform: translateY(-3px);
        }
        .feature-icon-big {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        .feature-title-text {
            font-size: 1.2rem;
            font-weight: 600;
            color: white;
            margin-bottom: 0.5rem;
        }
        .feature-desc-text {
            color: #8892A0;
            font-size: 0.95rem;
            line-height: 1.5;
        }
    </style>
    """, unsafe_allow_html=True)

    # Titre de section
    st.markdown(f"<h2 style='text-align: center; color: white; font-size: 2.5rem; margin-bottom: 0.5rem;'>{t('features.title')}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #8892A0; margin-bottom: 2rem;'>{t('features.subtitle')}</p>", unsafe_allow_html=True)

    # Grille 4x2
    for row in range(2):
        cols = st.columns(4)
        for col_idx, col in enumerate(cols):
            feat_idx = row * 4 + col_idx
            if feat_idx < len(features):
                f = features[feat_idx]
                title = t(f"features.items.{f['key']}.title")
                desc = t(f"features.items.{f['key']}.description")
                with col:
                    st.markdown(f"""
                    <div class="feature-box">
                        <div class="feature-icon-big">{f['icon']}</div>
                        <div class="feature-title-text">{title}</div>
                        <div class="feature-desc-text">{desc}</div>
                    </div>
                    """, unsafe_allow_html=True)
        st.write("")  # Espacement entre les lignes
