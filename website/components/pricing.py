"""
Section Tarifs - Version Streamlit Native
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from i18n import t
from auth.authentication import is_authenticated


def render_pricing():
    """Affiche la section tarifs avec composants Streamlit natifs"""

    # CSS
    st.markdown("""
    <style>
        .price-card {
            background: #131722;
            border: 1px solid #2A3447;
            border-radius: 16px;
            padding: 2rem;
            text-align: center;
            position: relative;
            transition: all 0.3s ease;
        }
        .price-card.highlighted {
            border-color: #00D4AA;
            box-shadow: 0 0 30px rgba(0, 212, 170, 0.15);
        }
        .price-card:hover {
            transform: translateY(-5px);
        }
        .price-badge {
            position: absolute;
            top: -12px;
            left: 50%;
            transform: translateX(-50%);
            background: #00D4AA;
            color: #0A0E17;
            padding: 4px 16px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
        }
        .price-badge.soon {
            background: #FFB300;
        }
        .price-name {
            font-size: 1.5rem;
            font-weight: 700;
            color: white;
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
        .price-amount {
            font-size: 3rem;
            font-weight: 800;
            color: #00D4AA;
        }
        .price-period {
            color: #8892A0;
            margin-bottom: 1.5rem;
        }
        .price-feat {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #B8C1CC;
            margin-bottom: 0.5rem;
            justify-content: center;
        }
        .price-feat::before {
            content: '✓';
            color: #00D4AA;
            font-weight: bold;
        }
        .price-btn-disabled {
            display: inline-block;
            width: 100%;
            padding: 12px;
            background: #2A3447;
            color: #8892A0;
            border-radius: 8px;
            margin-top: 1.5rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # Titre
    st.markdown(f"<h2 style='text-align: center; color: white; font-size: 2.5rem; margin-bottom: 0.5rem;'>{t('pricing.title')}</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #8892A0; margin-bottom: 2rem;'>{t('pricing.subtitle')}</p>", unsafe_allow_html=True)

    # 2 colonnes pour les plans
    col1, col2 = st.columns(2)

    # Plan Gratuit
    with col1:
        features_free = t('pricing.free.features')
        features_html = ""
        if isinstance(features_free, list):
            for f in features_free:
                features_html += f'<div class="price-feat">{f}</div>'

        st.markdown(f"""
        <div class="price-card highlighted">
            <span class="price-badge">{t('pricing.free.badge')}</span>
            <div class="price-name">{t('pricing.free.name')}</div>
            <div class="price-amount">{t('pricing.free.price')}</div>
            <div class="price-period">{t('pricing.free.period')}</div>
            <div>{features_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # Bouton CTA
        if st.button(t('pricing.free.cta'), key='pricing_cta_free', use_container_width=True, type='primary'):
            if is_authenticated():
                st.session_state.page = 'profile'
            else:
                st.session_state.page = 'register'
            st.rerun()

    # Plan Premium
    with col2:
        features_premium = t('pricing.premium.features')
        features_html = ""
        if isinstance(features_premium, list):
            for f in features_premium:
                features_html += f'<div class="price-feat">{f}</div>'

        st.markdown(f"""
        <div class="price-card">
            <span class="price-badge soon">{t('pricing.premium.badge')}</span>
            <div class="price-name">{t('pricing.premium.name')}</div>
            <div class="price-amount">{t('pricing.premium.price')}</div>
            <div class="price-period">{t('pricing.premium.period')}</div>
            <div>{features_html}</div>
            <div class="price-btn-disabled">{t('pricing.premium.cta')}</div>
        </div>
        """, unsafe_allow_html=True)
