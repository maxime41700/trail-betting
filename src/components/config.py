"""
CONFIGURATION DE L'APPLICATION

Ce module centralise le chargement de tous les paramètres de configuration et credentials nécessaires au fonctionnement de l'application.

Stratégie de chargement (par ordre de priorité) :
    1. st.secrets  : utilisé en production sur Streamlit Community Cloud.
    2. .env        : utilisé en développement local via python-dotenv.

Les credentials ne doivent jamais être écrits en dur dans ce fichier ni dans aucun autre fichier du projet.
"""

# LIBRAIRIES ----------------------------
import os
import streamlit as st
from dotenv import load_dotenv


class Config:
    """
    Classe de configuration centrale de l'application.

    Charge les variables d'environnement depuis st.secrets (production) ou depuis un fichier .env (développement local).
    Les attributs sont accessibles via config.SUPABASE_URL, etc.

    Attributs :
        SUPABASE_URL        (str) : URL du projet Supabase.
        SUPABASE_ANON_KEY   (str) : Clé publique anonyme Supabase (lecture seule côté client).
        SUPABASE_SERVICE_KEY(str) : Clé service Supabase (accès admin complet, à ne jamais exposer).
        DATABASE_URL        (str) : URL de connexion PostgreSQL directe (pour psycopg2).
    """

    def __init__(self) -> None:
        """
        Initialise la configuration en détectant automatiquement l'environnement.

        En production (Streamlit Cloud), st.secrets est disponible et prioritaire. En local, le fichier .env est chargé via python-dotenv.
        """

        if self._is_streamlit_cloud():
            self._load_from_st_secrets()
        else:
            load_dotenv()
            self._load_from_env()

    # METHODES PRIVEES
    def _is_streamlit_cloud(self) -> bool:
        """
        Détecte si l'application tourne sur Streamlit Community Cloud.

        Streamlit Cloud injecte automatiquement les secrets dans st.secrets. On tente un accès — si ça fonctionne, on est en production.

        Retourne:
            bool: True si st.secrets est disponible et non vide, False sinon.
        """

        try:
            return len(st.secrets) > 0
        except Exception:
            return False

    def _load_from_st_secrets(self) -> None:
        """
        Charge les credentials depuis st.secrets (Streamlit Community Cloud).

        Les secrets sont définis dans l'interface web de Streamlit Cloud, sous Settings > Secrets, au format TOML:

            SUPABASE_URL         = "https://xxxx.supabase.co"
            SUPABASE_ANON_KEY    = "eyJ..."
            SUPABASE_SERVICE_KEY = "eyJ..."
            DATABASE_URL         = "postgresql://postgres:pwd@db.xxxx.supabase.co:5432/postgres"
        """

        self.SUPABASE_URL         = st.secrets["SUPABASE_URL"]
        self.SUPABASE_ANON_KEY    = st.secrets["SUPABASE_ANON_KEY"]
        self.SUPABASE_SERVICE_KEY = st.secrets["SUPABASE_SERVICE_KEY"]
        self.DATABASE_URL         = st.secrets["DATABASE_URL"]

    def _load_from_env(self) -> None:
        """
        Charge les credentials depuis le fichier .env (développement local).

        Le fichier .env doit être placé à la racine du projet et ne doit jamais être commité (il est exclu par .gitignore).
        """

        self.SUPABASE_URL         = os.getenv("SUPABASE_URL")
        self.SUPABASE_ANON_KEY    = os.getenv("SUPABASE_ANON_KEY")
        self.SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
        self.DATABASE_URL         = os.getenv("DATABASE_URL")

        self._verifier_credentials()

    def _verifier_credentials(self) -> None:
        """
        Vérifie que les variables critiques ont bien été chargées.

        Lève une exception explicite si une variable obligatoire est manquante, plutôt que de laisser planter silencieusement plus tard dans le code.

        Lève :
            ValueError : si une variable d'environnement obligatoire est absente.
        """

        variables_requises = [
            "SUPABASE_URL",
            "SUPABASE_ANON_KEY",
            "SUPABASE_SERVICE_KEY",
            "DATABASE_URL"
        ]

        manquantes = [v for v in variables_requises if not getattr(self, v)]

        if manquantes:
            raise ValueError(
                f"Variables d'environnement manquantes dans le .env : {', '.join(manquantes)}\n"
                f"Vérifie que ton fichier .env est bien présent à la racine du projet."
            )


# INSTANCE GLOBALE
# Instance unique importée dans tous les modules qui en ont besoin : from src.components.config import config
config = Config()