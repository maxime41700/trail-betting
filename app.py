"""
POINT D'ENTREE - TRAIL BETTING

Ce fichier est le point d'entrée de l'application Streamlit.
Il initialise la configuration globale, le session_state et lance la navigation principale via le module navigation.

Lancement :
    streamlit run app.py
"""

# LIBRAIRIES ----------------------------
import streamlit as st
import yaml

# LOCAL LIBRAIRIES ----------------------
from src.components.session_state import initialize_session_state
from src.components.navigation import set_navigation
from src.functions.utils import extraire_bloc_style, get_image_base64

import os
from dotenv import load_dotenv

load_dotenv()  # ne fait rien sur Streamlit Cloud, utile en local

def get_secret(key):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return os.getenv(key)

SUPABASE_URL        = get_secret("SUPABASE_URL")
SUPABASE_ANON_KEY   = get_secret("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY= get_secret("SUPABASE_SERVICE_KEY")
DATABASE_URL        = get_secret("DATABASE_URL")


# CONFIGURATION GLOBALE
# ---------------------------------------------------------------------------
with open("config_pages.yml", "r", encoding = 'utf-8') as f:
    variables = yaml.safe_load(f)

# Configuration de l'onglet de l'app dans le navigateur
st.set_page_config(
    page_title = variables["PAGE_CONFIG"]["page_title"],
    page_icon = variables["PAGE_CONFIG"]["page_icon"],
    layout = variables["PAGE_CONFIG"]["page_layout"]
)


# INITIALISATION
# ---------------------------------------------------------------------------
# Injection des styles globaux (header + sidebar)
st.markdown(extraire_bloc_style("header", "src/assets/styles/styles.html"), unsafe_allow_html = True)
st.markdown(extraire_bloc_style("sidebar", "src/assets/styles/styles.html"), unsafe_allow_html = True)

# Initialisation du session_state avec les valeurs par défaut
initialize_session_state()


# NAVIGATION
# ---------------------------------------------------------------------------
# Lancement de la navigation principale — gère le routing entre les pages
set_navigation()