"""
Gestion de l'authentification
"""
import streamlit as st
from typing import Optional, Dict, Tuple
import re
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import (
    create_user, 
    authenticate_user, 
    get_user_by_email,
    get_user_by_id,
    create_password_reset_token,
    verify_reset_token,
    mark_reset_token_used,
    update_user_password
)


def is_valid_email(email: str) -> bool:
    """Vérifie si l'email est valide"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_valid_password(password: str) -> Tuple[bool, str]:
    """
    Vérifie si le mot de passe est valide
    Retourne (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères"
    if not re.search(r'[A-Z]', password):
        return False, "Le mot de passe doit contenir au moins une majuscule"
    if not re.search(r'[0-9]', password):
        return False, "Le mot de passe doit contenir au moins un chiffre"
    return True, ""


def init_session_state():
    """Initialise les variables de session"""
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'language' not in st.session_state:
        st.session_state.language = 'fr'
    if 'page' not in st.session_state:
        st.session_state.page = 'landing'


def login_user(user: Dict):
    """Connecte un utilisateur"""
    st.session_state.user = user
    st.session_state.authenticated = True
    st.session_state.language = user.get('language', 'fr')


def logout_user():
    """Déconnecte l'utilisateur"""
    st.session_state.user = None
    st.session_state.authenticated = False
    st.session_state.page = 'landing'


def get_current_user() -> Optional[Dict]:
    """Récupère l'utilisateur connecté"""
    return st.session_state.get('user')


def is_authenticated() -> bool:
    """Vérifie si l'utilisateur est authentifié"""
    return st.session_state.get('authenticated', False)


def require_auth():
    """Décorateur/fonction pour exiger l'authentification"""
    if not is_authenticated():
        st.session_state.page = 'login'
        st.rerun()


def register_user(email: str, password: str, name: str, language: str = 'fr') -> Tuple[bool, str]:
    """
    Enregistre un nouvel utilisateur
    Retourne (success, message)
    """
    # Vérifications
    if not is_valid_email(email):
        return False, "Email invalide"
    
    is_valid, error = is_valid_password(password)
    if not is_valid:
        return False, error
    
    if not name or len(name) < 2:
        return False, "Le nom doit contenir au moins 2 caractères"
    
    # Vérifier si l'email existe déjà
    if get_user_by_email(email):
        return False, "Cet email est déjà utilisé"
    
    # Créer l'utilisateur
    user_id = create_user(email, password, name, language)
    
    if user_id:
        return True, "Compte créé avec succès!"
    else:
        return False, "Erreur lors de la création du compte"


def login_with_credentials(email: str, password: str) -> Tuple[bool, str]:
    """
    Authentifie avec email/password
    Retourne (success, message)
    """
    if not email or not password:
        return False, "Veuillez remplir tous les champs"
    
    user = authenticate_user(email, password)
    
    if user:
        login_user(user)
        return True, "Connexion réussie!"
    else:
        return False, "Email ou mot de passe incorrect"


def request_password_reset(email: str) -> Tuple[bool, str]:
    """
    Demande un reset de mot de passe
    Retourne (success, message)
    """
    user = get_user_by_email(email)
    
    if not user:
        # Pour la sécurité, on ne révèle pas si l'email existe
        return True, "Si cet email existe, vous recevrez un lien de réinitialisation"
    
    token = create_password_reset_token(user['id'])
    
    # TODO: Envoyer l'email avec le token
    # Pour l'instant, afficher le token en développement
    print(f"Reset token for {email}: {token}")
    
    return True, "Si cet email existe, vous recevrez un lien de réinitialisation"


def reset_password_with_token(token: str, new_password: str) -> Tuple[bool, str]:
    """
    Reset le mot de passe avec un token
    Retourne (success, message)
    """
    is_valid, error = is_valid_password(new_password)
    if not is_valid:
        return False, error
    
    user_id = verify_reset_token(token)
    
    if not user_id:
        return False, "Lien invalide ou expiré"
    
    success = update_user_password(user_id, new_password)
    
    if success:
        mark_reset_token_used(token)
        return True, "Mot de passe mis à jour avec succès!"
    
    return False, "Erreur lors de la mise à jour du mot de passe"



