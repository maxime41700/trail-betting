"""
REQUETES SQL - RESULTATS - TRAIL BETTING

Ce module regroupe toutes les requêtes relatives aux résultats officiels
des courses (podiums hommes et femmes).

Fonctions disponibles :
    - get_resultats_par_course() : résultats officiels d'une course.
    - get_derniers_resultats()   : derniers résultats publiés toutes courses.
    - resultats_existent()       : vérifie si des résultats existent pour une course.
    - insert_resultats()         : saisie des résultats officiels (admin).
    - update_resultats()         : modification des résultats existants (admin).
"""

# LIBRAIRIES ----------------------------
import pandas as pd
import streamlit as st

# LOCAL LIBRAIRIES ----------------------
from src.db.connection import get_supabase_client, get_supabase_admin_client


# ---------------------------------------------------------------------------
# LECTURE
# ---------------------------------------------------------------------------

def get_resultats_par_course(course_id: str) -> dict | None:
    """
    Récupère les résultats officiels d'une course via la vue vue_resultats_course.

    Retourne les noms complets des coureurs du podium plutôt que leurs UUID.

    Paramètres :
        course_id (str) : UUID de la course.

    Retourne :
        dict | None : clés [course_nom, date_course,
                      homme_1er, homme_2eme, homme_3eme,
                      femme_1ere, femme_2eme, femme_3eme]
                      ou None si aucun résultat publié.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        res = get_resultats_par_course(course_id)
        if res:
            st.write(f"1er homme : {res['homme_1er']}")
    """

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("vue_resultats_course")
            .select("*")
            .eq("course_id", course_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    except Exception as e:
        st.error(f"Erreur lors du chargement des résultats : {e}")
        return None


def get_derniers_resultats(limit: int = 5) -> pd.DataFrame:
    """
    Récupère les derniers résultats publiés via la vue vue_derniers_resultats.

    Paramètres :
        limit (int) : nombre de courses à retourner. Défaut : 5.

    Retourne :
        pd.DataFrame : colonnes [date_course, course_nom, course_format,
                                  homme_1er, femme_1ere, saisi_at]
                       Triées par date décroissante.
                       Retourne un DataFrame vide en cas d'erreur.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.
    """

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("vue_derniers_resultats")
            .select("*")
            .limit(limit)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des derniers résultats : {e}")
        return pd.DataFrame()


def resultats_existent(course_id: str) -> bool:
    """
    Vérifie si des résultats officiels ont déjà été saisis pour une course.

    Paramètres :
        course_id (str) : UUID de la course.

    Retourne :
        bool : True si des résultats existent, False sinon.

    Exemple d'utilisation :
        if resultats_existent(course_id):
            st.warning("Des résultats existent déjà pour cette course.")
    """

    try:
        admin    = get_supabase_admin_client()
        response = (
            admin
            .table("resultats")
            .select("id")
            .eq("course_id", course_id)
            .limit(1)
            .execute()
        )
        return isinstance(response.data, list) and len(response.data) > 0

    except Exception as e:
        st.error(f"Erreur lors de la vérification des résultats : {e}")
        return False


# ---------------------------------------------------------------------------
# ECRITURE - ADMIN UNIQUEMENT
# ---------------------------------------------------------------------------

def insert_resultats(
    course_id   : str,
    admin_id    : str,
    homme_1er   : str | None = None,
    homme_2eme  : str | None = None,
    homme_3eme  : str | None = None,
    femme_1ere  : str | None = None,
    femme_2eme  : str | None = None,
    femme_3eme  : str | None = None,
) -> dict | None:
    """
    Saisit les résultats officiels d'une course.

    Réservé aux administrateurs. L'insertion déclenche automatiquement
    le trigger fn_scorer_paris_apres_resultats() qui calcule les points
    de tous les paris et met à jour les totaux utilisateurs.

    Paramètres :
        course_id  (str)       : UUID de la course.
        admin_id   (str)       : UUID de l'admin saisissant les résultats.
        homme_1er  (str | None): UUID du coureur arrivé 1er.
        homme_2eme (str | None): UUID du coureur arrivé 2ème.
        homme_3eme (str | None): UUID du coureur arrivé 3ème.
        femme_1ere (str | None): UUID de la coureuse arrivée 1ère.
        femme_2eme (str | None): UUID de la coureuse arrivée 2ème.
        femme_3eme (str | None): UUID de la coureuse arrivée 3ème.

    Retourne :
        dict | None : données du résultat créé ou None en cas d'erreur.

    Exemple d'utilisation :
        res = insert_resultats(
            course_id  = course_id,
            admin_id   = st.session_state["user_id"],
            homme_1er  = uuid_kilian,
            femme_1ere = uuid_courtney,
        )
        if res:
            st.success("Résultats enregistrés. Les paris ont été scorés automatiquement.")
    """

    try:
        admin    = get_supabase_admin_client()
        response = (
            admin
            .table("resultats")
            .insert({
                "course_id" : course_id,
                "saisi_par" : admin_id,
                "homme_1er" : homme_1er,
                "homme_2eme": homme_2eme,
                "homme_3eme": homme_3eme,
                "femme_1ere": femme_1ere,
                "femme_2eme": femme_2eme,
                "femme_3eme": femme_3eme,
            })
            .execute()
        )
        return response.data[0] if response.data else None

    except Exception as e:
        st.error(f"Erreur lors de la saisie des résultats : {e}")
        return None


def update_resultats(
    course_id   : str,
    homme_1er   : str | None = None,
    homme_2eme  : str | None = None,
    homme_3eme  : str | None = None,
    femme_1ere  : str | None = None,
    femme_2eme  : str | None = None,
    femme_3eme  : str | None = None,
) -> bool:
    """
    Met à jour les résultats officiels d'une course existante.

    Utilisé en mode édition lorsque des résultats ont déjà été saisis
    et que l'admin souhaite les corriger depuis l'application.
    Le trigger de scoring ne se relance pas automatiquement sur un UPDATE.

    Paramètres :
        course_id  (str)       : UUID de la course.
        homme_1er  (str | None): UUID du coureur arrivé 1er.
        homme_2eme (str | None): UUID du coureur arrivé 2ème.
        homme_3eme (str | None): UUID du coureur arrivé 3ème.
        femme_1ere (str | None): UUID de la coureuse arrivée 1ère.
        femme_2eme (str | None): UUID de la coureuse arrivée 2ème.
        femme_3eme (str | None): UUID de la coureuse arrivée 3ème.

    Retourne :
        bool : True si la mise à jour a réussi, False sinon.

    Exemple d'utilisation :
        ok = update_resultats(course_id, homme_1er=uuid_kilian)
        if ok:
            st.success("Résultats mis à jour.")
    """

    try:
        admin = get_supabase_admin_client()
        admin \
            .table("resultats") \
            .update({
                "homme_1er" : homme_1er,
                "homme_2eme": homme_2eme,
                "homme_3eme": homme_3eme,
                "femme_1ere": femme_1ere,
                "femme_2eme": femme_2eme,
                "femme_3eme": femme_3eme,
            }) \
            .eq("course_id", course_id) \
            .execute()
        return True

    except Exception as e:
        st.error(f"Erreur lors de la mise à jour des résultats : {e}")
        return False
