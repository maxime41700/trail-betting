"""
REQUETES SQL - COURSES ET PARTICIPANTS - TRAIL BETTING

Ce module regroupe toutes les requêtes relatives aux courses et à leurs
participants (coureurs inscrits).

Fonctions disponibles :
    - get_courses_a_venir()         : liste des courses à venir sans résultats.
    - get_course_by_id()            : détail d'une course par son UUID.
    - get_participants_par_course() : coureurs inscrits à une course donnée.
    - get_favoris_par_course()      : top N favoris H/F selon l'index UTMB.
    - insert_course()               : création d'une nouvelle course (admin).
    - update_avis_expert()          : mise à jour de l'avis du Duc (admin).
    - update_participants()         : mise à jour des inscrits d'une course (admin).
"""

# LIBRAIRIES ----------------------------
import pandas as pd
import streamlit as st

# LOCAL LIBRAIRIES ----------------------
from src.db.connection import get_supabase_client, get_supabase_admin_client


# ---------------------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------------------

# Formats UTMB valides et colonnes d'index associées
FORMAT_TO_COLUMN: dict[str, str] = {
    "global" : "index_utmb_global",
    "20K"    : "index_utmb_20k",
    "50K"    : "index_utmb_50k",
    "100K"   : "index_utmb_100k",
    "100M"   : "index_utmb_100m",
}

FORMATS_COURSE = ["20K", "50K", "100K", "100M"]


# ---------------------------------------------------------------------------
# LECTURE - COURSES
# ---------------------------------------------------------------------------

def get_courses_a_venir() -> pd.DataFrame:
    """
    Récupère toutes les courses à venir via la vue vue_courses_a_venir.

    Les courses sont triées par date croissante (défini dans la vue).

    Retourne :
        pd.DataFrame : colonnes [id, nom, evenement, format, lieu,
                                  distance, denivele, date_course, avis_expert]
                       Retourne un DataFrame vide si aucune course à venir.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        df = get_courses_a_venir()
        for _, course in df.iterrows():
            st.expander(course["nom"])
    """

    try:
        supabase = get_supabase_client()
        
        response = supabase.table("vue_courses_a_venir").select("*").execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des courses à venir : {e}")
        return pd.DataFrame()


def get_course_by_id(course_id: str) -> dict | None:
    """
    Récupère le détail complet d'une course à partir de son UUID.

    Paramètres :
        course_id (str) : UUID de la course recherchée.

    Retourne :
        dict | None : dictionnaire avec tous les champs de la course,
                      ou None si la course n'existe pas.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        course = get_course_by_id("123e4567-...")
        if course:
            st.write(course["nom"])
    """

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("courses")
            .select("*")
            .eq("id", course_id)
            .limit(1)
            .execute()
        )
        return response.data

    except Exception as e:
        st.error(f"Erreur lors du chargement de la course {course_id} : {e}")
        return None


# ---------------------------------------------------------------------------
# LECTURE - PARTICIPANTS ET FAVORIS
# ---------------------------------------------------------------------------

def get_participants_par_course(course_id: str) -> pd.DataFrame:
    """
    Récupère la liste des coureurs inscrits à une course via vue_participants_course.

    Paramètres :
        course_id (str) : UUID de la course.

    Retourne :
        pd.DataFrame : colonnes [coureur_id, nom, prenom, nationalite, sexe,
                                  index_utmb_global, index_utmb_20k,
                                  index_utmb_50k, index_utmb_100k, index_utmb_100m]
                       Retourne un DataFrame vide si aucun participant.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        df     = get_participants_par_course("123e4567-...")
        hommes = df[df["sexe"] == "H"]
    """

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("vue_participants_course")
            .select("*")
            .eq("course_id", course_id)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des participants : {e}")
        return pd.DataFrame()


def get_favoris_par_course(course_id: str, format_course: str, top_n: int = 10) -> dict:
    """
    Calcule le top N des favoris hommes et femmes pour une course donnée.

    Récupère les participants via la vue, trie par index UTMB global puis
    par index spécifique au format en critère secondaire, et sépare par genre.

    Paramètres :
        course_id     (str) : UUID de la course.
        format_course (str) : format UTMB ('20K', '50K', '100K', '100M').
        top_n         (int) : nombre de favoris à retourner par genre. Défaut : 10.

    Retourne :
        dict : {
            "hommes" : pd.DataFrame (top_n hommes triés par index),
            "femmes" : pd.DataFrame (top_n femmes triées par index)
        }
        Colonnes : [rang, coureur_id, nom, prenom, nationalite,
                    index_utmb_global, index_utmb_format]

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        favoris = get_favoris_par_course(course_id, "100M", top_n=10)
        st.dataframe(favoris["hommes"])
    """

    col_format = FORMAT_TO_COLUMN.get(format_course, "index_utmb_global")

    df = get_participants_par_course(course_id)

    if df.empty:
        return {"hommes": pd.DataFrame(), "femmes": pd.DataFrame()}

    # Tri par index global puis index format (critère secondaire)
    df = df.sort_values(
        by          = ["index_utmb_global", col_format],
        ascending   = [False, False],
        na_position = "last"
    )

    # Renommage pour l'affichage
    df = df.rename(columns={col_format: "index_utmb_format"})

    hommes = df[df["sexe"] == "H"].head(top_n).reset_index(drop=True)
    femmes = df[df["sexe"] == "F"].head(top_n).reset_index(drop=True)

    hommes.insert(0, "rang", range(1, len(hommes) + 1))
    femmes.insert(0, "rang", range(1, len(femmes) + 1))

    return {"hommes": hommes, "femmes": femmes}


# ---------------------------------------------------------------------------
# ECRITURE - ADMIN UNIQUEMENT
# ---------------------------------------------------------------------------

def insert_course(
    evenement     : str,
    nom           : str,
    format_course : str,
    distance      : float,
    denivele      : float,
    lieu          : str,
    date_course   : str,
    avis_expert   : str = None,
) -> dict | None:
    """
    Insère une nouvelle course dans la base de données.

    Réservé aux administrateurs. Utilise le client admin (SERVICE_KEY)
    pour bypasser le Row Level Security.

    Paramètres :
        evenement     (str)         : nom de l'événement parent
                                      (ex : 'Val d'Aran by UTMB').
        nom           (str)         : nom de la course (ex : 'CCC').
        format_course (str)         : format UTMB ('20K', '50K', '100K', '100M').
        distance      (float)       : distance en kilomètres.
        denivele      (float)       : dénivelé positif en mètres.
        lieu          (str)         : lieu de la course.
        date_course   (str)         : date au format 'YYYY-MM-DD'.
        avis_expert   (str | None)  : analyse du Duc (optionnelle à la création).

    Retourne :
        dict | None : données de la course créée (avec son UUID généré),
                      ou None en cas d'erreur.

    Exemple d'utilisation :
        course = insert_course(
            evenement     = "UTMB Mont-Blanc",
            nom           = "CCC",
            format_course = "100K",
            distance      = 101.0,
            denivele      = 6100.0,
            lieu          = "Courmayeur",
            date_course   = "2025-08-28",
        )
    """

    try:
        admin    = get_supabase_admin_client()
        response = (
            admin
            .table("courses")
            .insert({
                "evenement"         : evenement,
                "nom"               : nom,
                "format"            : format_course,
                "distance"          : distance,
                "denivele"          : denivele,
                "lieu"              : lieu,
                "date_course"       : date_course,
                "avis_expert"       : avis_expert,
                "resultats_publies" : False,
            })
            .execute()
        )
        return response.data[0] if response.data else None

    except Exception as e:
        st.error(f"Erreur lors de la création de la course : {e}")
        return None


def update_avis_expert(course_id: str, avis_expert: str) -> bool:
    """
    Met à jour l'avis du Duc (expert trail) pour une course donnée.

    Réservé aux administrateurs. Appelé chaque vendredi lors de la
    mise à jour hebdomadaire du contenu éditorial.

    Paramètres :
        course_id   (str) : UUID de la course à mettre à jour.
        avis_expert (str) : texte de l'analyse du Duc.

    Retourne :
        bool : True si la mise à jour a réussi, False sinon.

    Exemple d'utilisation :
        ok = update_avis_expert(course_id, "Kilian favori incontestable...")
        if ok:
            st.success("Avis mis à jour.")
    """

    try:
        admin = get_supabase_admin_client()
        admin \
            .table("courses") \
            .update({"avis_expert": avis_expert}) \
            .eq("id", course_id) \
            .execute()
        return True

    except Exception as e:
        st.error(f"Erreur lors de la mise à jour de l'avis expert : {e}")
        return False


def update_participants(course_id: str, coureur_ids: list[str]) -> bool:
    """
    Met à jour la liste des participants inscrits à une course.

    Supprime tous les participants existants puis réinsère la nouvelle liste
    (stratégie delete + insert pour éviter les doublons).
    Réservé aux administrateurs.

    Paramètres :
        course_id   (str)       : UUID de la course.
        coureur_ids (list[str]) : liste des UUID des coureurs inscrits.

    Retourne :
        bool : True si la mise à jour a réussi, False sinon.

    Exemple d'utilisation :
        ok = update_participants(course_id, [uuid1, uuid2, uuid3])
        if ok:
            st.success(f"{len(coureur_ids)} participants enregistrés.")
    """

    try:
        admin = get_supabase_admin_client()

        admin \
            .table("participants_course") \
            .delete() \
            .eq("course_id", course_id) \
            .execute()

        if coureur_ids:
            rows = [
                {"course_id": course_id, "coureur_id": cid}
                for cid in coureur_ids
            ]
            admin.table("participants_course").insert(rows).execute()

        return True

    except Exception as e:
        st.error(f"Erreur lors de la mise à jour des participants : {e}")
        return False
