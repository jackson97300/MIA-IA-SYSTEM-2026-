"""
Système de traduction FR/EN
"""
import json
import streamlit as st
from pathlib import Path

# Langues disponibles
LANGUAGES = {
    'fr': {'name': 'Français', 'flag': '🇫🇷'},
    'en': {'name': 'English', 'flag': '🇬🇧'}
}

# Cache des traductions
_translations = {}


def load_translations():
    """Charge les fichiers de traduction"""
    global _translations

    i18n_dir = Path(__file__).parent

    for lang in LANGUAGES.keys():
        filepath = i18n_dir / f"{lang}.json"
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                _translations[lang] = json.load(f)
        else:
            _translations[lang] = {}


def get_language() -> str:
    """Retourne la langue actuelle"""
    return st.session_state.get('language', 'fr')


def set_language(lang: str):
    """Définit la langue"""
    if lang in LANGUAGES:
        st.session_state.language = lang


def t(key: str, **kwargs):
    """
    Traduit une clé

    Usage:
        t('hero.title')
        t('welcome', name='John')
    """
    # Recharger les traductions si nécessaire
    if not _translations:
        load_translations()

    lang = get_language()
    translations = _translations.get(lang, {})

    # Navigation par points (ex: 'hero.title')
    keys = key.split('.')
    value = translations

    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
            if value is None:
                break
        else:
            value = None
            break

    # Si non trouvé, essayer en anglais comme fallback
    if value is None:
        value = _translations.get('en', {})
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return key
            else:
                return key

    # Si c'est une liste ou un dict, le retourner tel quel
    if isinstance(value, (list, dict)):
        return value

    # Remplacer les variables pour les strings
    if isinstance(value, str) and kwargs:
        for k, v in kwargs.items():
            value = value.replace(f'{{{k}}}', str(v))

    return value if value is not None else key


def reload_translations():
    """Force le rechargement des traductions"""
    global _translations
    _translations = {}
    load_translations()


# Charger les traductions au démarrage
load_translations()
