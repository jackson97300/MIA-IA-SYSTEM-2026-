"""
Page d'accueil / Landing Page
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from components.header import render_header
from components.hero import render_hero
from components.about import render_about
from components.features import render_features
from components.how_it_works import render_how_it_works
from components.screenshots import render_screenshots
from components.stats import render_stats
from components.pricing import render_pricing
from components.faq import render_faq
from components.newsletter import render_newsletter
from components.contact import render_contact
from components.footer import render_footer


def render_landing():
    """Affiche la landing page complète"""
    
    # Header
    render_header()
    
    # Hero Section
    render_hero()
    
    # À propos / Histoire
    render_about()
    
    # Fonctionnalités
    render_features()
    
    # Comment ça marche
    render_how_it_works()
    
    # Screenshots
    render_screenshots()
    
    # Statistiques
    render_stats()
    
    # Tarifs
    render_pricing()
    
    # FAQ
    render_faq()
    
    # Newsletter
    render_newsletter()
    
    # Contact
    render_contact()
    
    # Footer
    render_footer()



