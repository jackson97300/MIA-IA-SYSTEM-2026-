"""
Section Statistiques - Version Streamlit Native
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t


def render_stats():
    """Affiche la section statistiques avec composants Streamlit natifs"""

    stats = ['analysis', 'markets', 'reaction', 'research']

    # CSS
    st.markdown("""
    <style>
        .stat-box {
            text-align: center;
            padding: 1.5rem;
        }
        .stat-val {
            font-size: 2.8rem;
            font-weight: 800;
            color: #00D4AA;
            line-height: 1;
            margin-bottom: 0.5rem;
        }
        .stat-lbl {
            font-size: 0.95rem;
            color: #8892A0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Titre
    st.markdown(f"<h2 style='text-align: center; color: white; font-size: 2.5rem; margin-bottom: 2rem;'>{t('stats.title')}</h2>", unsafe_allow_html=True)

    # 4 colonnes
    cols = st.columns(4)
    for idx, col in enumerate(cols):
        stat = stats[idx]
        value = t(f'stats.items.{stat}.value')
        label = t(f'stats.items.{stat}.label')
        with col:
            st.markdown(f"""
            <div class="stat-box">
                <div class="stat-val">{value}</div>
                <div class="stat-lbl">{label}</div>
            </div>
            """, unsafe_allow_html=True)
