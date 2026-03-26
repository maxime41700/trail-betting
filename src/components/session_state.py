"""
MODULE DE GESTION DES SESSIONS D'ÉTAT - TRAIL BETTING

Ce module gère les variables d'état nécessaires au bon fonctionnement
de l'application. Il initialise le session_state Streamlit avec des
valeurs par défaut au démarrage, sans écraser les valeurs déjà présentes.

Fonctionnalités principales :
    - Définition centralisée de toutes les clés de session et leurs
      valeurs par défaut dans DEFAULT_STATES.
    - Initialisation idempotente : peut être appelée en haut de chaque
      page sans risque d'écraser l'état en cours.
"""

# LIBRAIRIES ----------------------------
import streamlit as st


# Dictionnaire contenant les clés et valeurs par défaut du session_state.
# Toute nouvelle variable de session doit être déclarée ici.
DEFAULT_STATES: dict = {

    # --- Authentification ---------------------------------------------------
    "authentifie"  : False,   # L'utilisateur est-il connecté ?
    "user_id"      : None,    # UUID de l'utilisateur connecté
    "user_pseudo"  : None,    # Pseudo affiché dans l'UI et le classement
    "user_role"    : None,    # 'user' ou 'admin'
}


def initialize_session_state() -> None:
    """
    Initialise les variables de session d'état si elles n'existent pas encore.

    Parcourt DEFAULT_STATES et injecte chaque clé dans st.session_state
    uniquement si elle n'est pas déjà présente. Cela permet d'appeler
    cette fonction en haut de chaque page sans écraser l'état en cours
    (par exemple, ne pas déconnecter l'utilisateur à chaque rerun).
    """

    for key, value in DEFAULT_STATES.items():
        if key not in st.session_state:
            st.session_state[key] = value