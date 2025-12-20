"""
Section Screenshots - Version Streamlit Native
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import get_language


def render_screenshots():
    """Affiche la section screenshots avec composants Streamlit natifs"""

    lang = get_language()

    screenshots = [
        {'icon': '📊', 'label_fr': 'Dashboard Principal', 'label_en': 'Main Dashboard'},
        {'icon': '🎯', 'label_fr': 'Signaux de Trading', 'label_en': 'Trading Signals'},
        {'icon': '📈', 'label_fr': 'Statistiques', 'label_en': 'Statistics'},
    ]

    title = "Aperçu du Dashboard" if lang == 'fr' else "Dashboard Preview"
    subtitle = "Interface intuitive et professionnelle" if lang == 'fr' else "Intuitive and professional interface"

    # CSS
    st.markdown("""
    <style>
        .screenshot-box {
            background: #131722;
            border: 1px solid #2A3447;
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        .screenshot-box:hover {
            border-color: #00D4AA;
            transform: scale(1.02);
        }
        .screenshot-img {
            width: 100%;
            height: 150px;
            background: linear-gradient(135deg, #1E3A5F 0%, #131722 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3.5rem;
        }
        .screenshot-lbl {
            padding: 1rem;
            text-align: center;
            color: #B8C1CC;
            font-weight: 500;
        }
    </style>
    """, unsafe_allow_html=True)

    # Titre
    st.markdown(f"<h2 style='text-align: center; color: white; font-size: 2.5rem; margin-bottom: 0.5rem;'>{title}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #8892A0; margin-bottom: 2rem;'>{subtitle}</p>", unsafe_allow_html=True)

    # 3 colonnes
    cols = st.columns(3)
    for idx, col in enumerate(cols):
        s = screenshots[idx]
        label = s['label_fr'] if lang == 'fr' else s['label_en']
        with col:
            st.markdown(f"""
            <div class="screenshot-box">
                <div class="screenshot-img">{s['icon']}</div>
                <div class="screenshot-lbl">{label}</div>
            </div>
            """, unsafe_allow_html=True)
