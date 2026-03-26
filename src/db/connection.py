"""
MODULE DE CONNEXION A LA BASE DE DONNEES

Ce module centralise la gestion des connexions à la base de données PostgreSQL hébergée sur Supabase.

Deux modes de connexion sont disponibles selon le besoin:
    - Client Supabase : via supabase-py, pour les opérations CRUD standard soumises au Row Level Security (RLS).
    - Connexion directe psycopg2 : pour les appels aux fonctions PL/pgSQL et les requêtes complexes via pd.read_sql().

Les connexions sont mises en cache via @st.cache_resource pour n'être instanciées qu'une seule fois par session Streamlit,
évitant les reconnexions inutiles à chaque rerun.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
from supabase import create_client, Client

# LOCAL LIBRAIRIES ----------------------
from src.components.config import config


SCHEMA = "trail_betting_db"


# CLIENT SUPABASE
@st.cache_resource
def get_supabase_client() -> Client:
    """
    Instancie et retourne le client Supabase (clé anonyme).

    Utilise la ANON_KEY, soumise au Row Level Security défini dans le schema.
    A utiliser pour toutes les opérations standard : lecture des courses, insertion d'un pari, lecture du classement.

    Le décorateur @st.cache_resource garantit qu'une seule instance est créée pour toute la durée de vie de l'application.

    Retourne :
        Client : instance du client Supabase prête à l'emploi.

    Lève :
        Exception : si la connexion échoue (URL ou clé incorrecte).
    """

    try:
        client = create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)
        return client.schema(SCHEMA)

    except Exception as e:
        st.error(f"Impossible de se connecter à Supabase : {e}")
        raise


@st.cache_resource
def get_supabase_admin_client() -> Client:
    """
    Instancie et retourne le client Supabase avec la clé service (admin).

    Utilise la SERVICE_KEY qui bypasse le Row Level Security. A utiliser UNIQUEMENT pour les opérations d'administration:
        - Scoring des paris après publication des résultats.
        - Saisie des résultats par les admins.
        - Mise à jour des index UTMB.

    Ne jamais exposer ce client côté interface utilisateur standard.

    Retourne :
        Client : instance du client Supabase admin prête à l'emploi.

    Lève :
        Exception : si la connexion échoue (URL ou clé incorrecte).
    """

    try:
        client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
        return client.schema(SCHEMA)

    except Exception as e:
        st.error(f"Impossible de se connecter à Supabase (admin) : {e}")
        raise


# UTILITAIRES
def verifier_connexions() -> bool:
    """
    Vérifie que la connexion Supabase est active.

    Effectue une requête légère sur la table utilisateurs pour s'assurer que le client répond correctement. Utile au démarrage de l'application.

    Retourne :
        bool : True si la connexion est active, False sinon.
    """

    try:
        client = get_supabase_client()
        client.table("utilisateurs").select("id").limit(1).execute()
        return True

    except Exception as e:
        st.error(f"Connexion Supabase KO : {e}")
        return False