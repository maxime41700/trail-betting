"""
REQUETES SQL - CLASSEMENT

Ce module regroupe toutes les requêtes relatives au classement général des utilisateurs et à l'historique de leurs performances.
Les jointures complexes sont déléguées aux vues SQL définies dans views.sql.

Fonctions disponibles :
    - get_classement_general()      : classement complet de tous les utilisateurs.
    - get_stats_par_user()          : statistiques détaillées d'un utilisateur.
    - get_historique_points_user()  : évolution des points d'un utilisateur course par course.
"""

# LIBRAIRIES ----------------------------
import pandas as pd
import streamlit as st

# LOCAL LIBRAIRIES ----------------------
from src.db.connection import get_supabase_client


# LECTURE - CLASSEMENT
def get_classement_general() -> pd.DataFrame:
    """
    Récupère le classement général via la vue vue_classement_general.

    Calcule pour chaque utilisateur son rang, ses points cumulés,
    le nombre de paris déposés/scorés et son taux de réussite.
    Les administrateurs sont exclus du classement.

    Retourne :
        pd.DataFrame : colonnes [rang, pseudo, points_total, nb_paris,
                                  nb_paris_scores, taux_reussite]
                       Triés par points décroissants puis pseudo alphabétique.
                       Retourne un DataFrame vide en cas d'erreur.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.
    """

    try:
        supabase = get_supabase_client()
        response = supabase.table("vue_classement_general").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement du classement : {e}")
        return pd.DataFrame()


def get_stats_par_user(user_id: str) -> dict | None:
    """
    Récupère les statistiques détaillées d'un utilisateur.

    Filtre la vue vue_classement_general sur l'user_id pour extraire
    les métriques personnelles affichées sur le profil de l'utilisateur.

    Paramètres :
        user_id (str) : UUID de l'utilisateur.

    Retourne :
        dict | None : clés [rang, pseudo, points_total, nb_paris,
                      nb_paris_scores, taux_reussite],
                      ou None si l'utilisateur n'est pas trouvé.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        stats = get_stats_par_user(st.session_state["user_id"])
        if stats:
            st.metric("Rang",   f"#{stats['rang']}")
            st.metric("Points", stats["points_total"])
    """

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("vue_classement_general")
            .select("*")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return response.data

    except Exception as e:
        st.error(f"Erreur lors du chargement des statistiques : {e}")
        return None


def get_historique_points_user(user_id: str) -> pd.DataFrame:
    """
    Récupère l'historique des points d'un utilisateur via vue_historique_points.

    Retourne toutes les courses scorées avec le cumul progressif des points,
    prêt à être affiché dans un graphique d'évolution.
    Seules les courses avec résultats publiés sont incluses.

    Paramètres :
        user_id (str) : UUID de l'utilisateur.

    Retourne :
        pd.DataFrame : colonnes [date_course, course_nom, course_format,
                                  points_gagnes, cumul_points,
                                  homme_1er_parie, homme_1er_reel,
                                  femme_1ere_pariee, femme_1ere_reelle]
                       Triés par date croissante.
                       Retourne un DataFrame vide si aucun historique.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        df = get_historique_points_user(user_id)
        st.line_chart(df.set_index("date_course")["cumul_points"])
    """

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("vue_historique_points")
            .select("*")
            .eq("user_id", user_id)
            .order("date_course", desc=False)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement de l'historique : {e}")
        return pd.DataFrame()