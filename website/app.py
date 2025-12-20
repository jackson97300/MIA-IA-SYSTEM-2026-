"""
MIA IA SYSTEM - Site Web Officiel
Application Streamlit principale
"""
import streamlit as st
import sys
from pathlib import Path

# Ajouter le répertoire website au path
sys.path.insert(0, str(Path(__file__).parent))

# Configuration de la page (DOIT ÊTRE EN PREMIER)
st.set_page_config(
    page_title="MIA IA SYSTEM",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Imports après set_page_config
from auth.authentication import init_session_state
from i18n import t, get_language
from components.styles import get_global_styles

# Pages
from pages.landing import render_landing
from pages.login import render_login
from pages.register import render_register
from pages.forgot_password import render_forgot_password
from pages.profile import render_profile


def main():
    """Point d'entrée principal"""
    
    # Initialiser la session
    init_session_state()
    
    # Appliquer les styles globaux
    st.markdown(get_global_styles(), unsafe_allow_html=True)
    
    # Masquer la sidebar et les éléments Streamlit
    st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        .stDeployButton {display: none;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Background global */
        .stApp {
            background-color: #0A0E17;
        }
        
        /* Style des inputs */
        .stTextInput input {
            background-color: #131722 !important;
            border-color: #2A3447 !important;
            color: white !important;
        }
        
        .stTextArea textarea {
            background-color: #131722 !important;
            border-color: #2A3447 !important;
            color: white !important;
        }
        
        /* Style des boutons */
        .stButton > button {
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
        }
        
        /* Labels */
        .stTextInput label, .stTextArea label, .stCheckbox label {
            color: #8892A0 !important;
        }
        
        /* Messages success/error */
        .stSuccess {
            background-color: rgba(0, 200, 83, 0.1) !important;
            border-color: #00C853 !important;
        }
        
        .stError {
            background-color: rgba(255, 82, 82, 0.1) !important;
            border-color: #FF5252 !important;
        }
        
        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #131722 !important;
            border: 1px solid #2A3447 !important;
            border-radius: 8px !important;
        }
        
        .streamlit-expanderContent {
            background-color: #1C2333 !important;
            border: 1px solid #2A3447 !important;
            border-top: none !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Router
    page = st.session_state.get('page', 'landing')
    
    if page == 'landing':
        render_landing()
    elif page == 'login':
        render_login()
    elif page == 'register':
        render_register()
    elif page == 'forgot_password':
        render_forgot_password()
    elif page == 'profile':
        render_profile()
    else:
        render_landing()


if __name__ == "__main__":
    main()



