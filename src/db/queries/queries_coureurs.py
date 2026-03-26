"""
REQUETES SQL - COUREURS ET INDEX UTMB - TRAIL BETTING

Ce module regroupe toutes les requêtes relatives aux coureurs et à leurs
index UTMB World Series.

Formats d'index disponibles : global, 20K, 50K, 100K, 100M.

Fonctions disponibles :
    - get_tous_les_coureurs()   : liste complète des coureurs.
    - get_coureurs_par_sexe()   : coureurs filtrés par genre.
    - get_top_index_utmb()      : top N coureurs par index UTMB global ou par format.
    - get_coureur_by_id()       : détail d'un coureur par son UUID.
    - insert_coureur()          : ajout d'un nouveau coureur (admin).
    - update_index_utmb()       : mise à jour des index UTMB d'un coureur (admin).
    - upsert_coureurs_batch()   : import en masse des coureurs et index (admin).
"""

# LIBRAIRIES ----------------------------
import pandas as pd
import streamlit as st

# LOCAL LIBRAIRIES ----------------------
from src.db.connection import get_supabase_client, get_supabase_admin_client


# ---------------------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------------------

# Mapping format → colonne d'index dans la table coureurs
FORMAT_TO_COLUMN: dict[str, str] = {
    "global" : "index_utmb_global",
    "20K"    : "index_utmb_20k",
    "50K"    : "index_utmb_50k",
    "100K"   : "index_utmb_100k",
    "100M"   : "index_utmb_100m",
}


# ---------------------------------------------------------------------------
# LECTURE
# ---------------------------------------------------------------------------

def get_tous_les_coureurs() -> pd.DataFrame:
    """
    Récupère la liste complète de tous les coureurs du référentiel.

    Triés par index global décroissant pour faciliter la sélection
    dans les interfaces d'administration.

    Retourne :
        pd.DataFrame : colonnes [id, nom, prenom, nationalite, sexe, image,
                                  index_utmb_global, index_utmb_20k,
                                  index_utmb_50k, index_utmb_100k,
                                  index_utmb_100m, updated_at]
                       Retourne un DataFrame vide en cas d'erreur.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        df      = get_tous_les_coureurs()
        options = df["prenom"] + " " + df["nom"]
    """

    try:
        supabase = get_supabase_client()

        all_rows = []
        batch_size = 1000
        offset = 0

        while True:
            response = (
                supabase
                .table("vue_coureurs")
                .select("*")
                .order("index_utmb_global", desc=True)
                .range(offset, offset + batch_size - 1)
                .execute()
            )

            data = response.data

            if not data:
                break

            all_rows.extend(data)

            # stop si dernière page
            if len(data) < batch_size:
                break

            offset += batch_size

        return pd.DataFrame(all_rows) if all_rows else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des coureurs : {e}")
        return pd.DataFrame()


def get_coureurs_par_sexe(sexe: str) -> pd.DataFrame:
    """
    Récupère tous les coureurs filtrés par genre.

    Utilisé pour alimenter les listes déroulantes du dialog de pari,
    après filtrage sur les participants de la course concernée.

    Paramètres :
        sexe (str) : 'H' pour hommes, 'F' pour femmes.

    Retourne :
        pd.DataFrame : colonnes [id, nom, prenom, nationalite, index_utmb_global]
                       Triés par index décroissant.
                       Retourne un DataFrame vide en cas d'erreur.

    Lève :
        ValueError : si sexe n'est pas 'H' ou 'F'.
        Exception  : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        df      = get_coureurs_par_sexe("H")
        options = (df["prenom"] + " " + df["nom"]).tolist()
    """

    if sexe not in ("H", "F"):
        raise ValueError(f"Valeur de sexe invalide : '{sexe}'. Attendu : 'H' ou 'F'.")

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("coureurs")
            .select("id, nom, prenom, nationalite, index_utmb_global")
            .eq("sexe", sexe)
            .order("index_utmb_global", desc=True, nulls_first=False)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des coureurs ({sexe}) : {e}")
        return pd.DataFrame()


def get_top_index_utmb(format_course: str = "global", top_n: int = 20) -> dict:
    """
    Récupère le top N des coureurs par index UTMB, séparé par genre.

    Utilisé pour afficher le tableau des index UTMB de référence.

    Paramètres :
        format_course (str) : index à utiliser pour le classement.
                              Valeurs : 'global', '20K', '50K', '100K', '100M'.
                              Défaut : 'global'.
        top_n         (int) : nombre de coureurs par genre. Défaut : 20.

    Retourne :
        dict : {
            "hommes" : pd.DataFrame (top_n hommes),
            "femmes" : pd.DataFrame (top_n femmes)
        }
        Colonnes : [rang, nom, prenom, nationalite, index_global, index_format]

    Lève :
        ValueError : si format_course n'est pas une valeur valide.
        Exception  : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        top = get_top_index_utmb("100M", top_n=10)
        st.dataframe(top["hommes"])
    """

    if format_course not in FORMAT_TO_COLUMN:
        raise ValueError(
            f"Format invalide : '{format_course}'. "
            f"Valeurs acceptées : {list(FORMAT_TO_COLUMN.keys())}"
        )

    col_format = FORMAT_TO_COLUMN[format_course]

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("coureurs")
            .select(f"nom, prenom, nationalite, sexe, index_utmb_global, {col_format}")
            .not_.is_(col_format, "null")
            .order("index_utmb_global", desc=True, nulls_first=False)
            .execute()
        )

        if not response.data:
            return {"hommes": pd.DataFrame(), "femmes": pd.DataFrame()}

        df = pd.DataFrame(response.data).rename(columns={
            col_format         : "index_format",
            "index_utmb_global": "index_global",
        })

        df = df.sort_values(
            by          = ["index_format"],
            ascending   = False,
            na_position = "last"
        )

        hommes = df[df["sexe"] == "H"].head(top_n).reset_index(drop=True)
        femmes = df[df["sexe"] == "F"].head(top_n).reset_index(drop=True)

        hommes.insert(0, "rang", range(1, len(hommes) + 1))
        femmes.insert(0, "rang", range(1, len(femmes) + 1))

        return {"hommes": hommes, "femmes": femmes}

    except Exception as e:
        st.error(f"Erreur lors du chargement des index UTMB : {e}")
        return {"hommes": pd.DataFrame(), "femmes": pd.DataFrame()}


def get_coureur_by_id(coureur_id: str) -> dict | None:
    """
    Récupère le détail complet d'un coureur à partir de son UUID.

    Paramètres :
        coureur_id (str) : UUID du coureur.

    Retourne :
        dict | None : dictionnaire avec tous les champs du coureur,
                      ou None si le coureur n'existe pas.

    Lève :
        Exception : en cas d'erreur de connexion ou de requête.

    Exemple d'utilisation :
        coureur = get_coureur_by_id("123e4567-...")
        st.write(f"{coureur['prenom']} {coureur['nom']}")
    """

    try:
        supabase = get_supabase_client()
        response = (
            supabase
            .table("coureurs")
            .select("*")
            .eq("id", coureur_id)
            .limit(1)
            .execute()
        )
        return response.data

    except Exception as e:
        st.error(f"Erreur lors du chargement du coureur : {e}")
        return None


# ---------------------------------------------------------------------------
# ECRITURE - ADMIN UNIQUEMENT
# ---------------------------------------------------------------------------

def insert_coureur(
    nom               : str,
    prenom            : str,
    sexe              : str,
    nationalite       : str   = None,
    image             : str   = None,
    index_utmb_global : float = None,
    index_utmb_20k    : float = None,
    index_utmb_50k    : float = None,
    index_utmb_100k   : float = None,
    index_utmb_100m   : float = None,
) -> dict | None:
    """
    Insère un nouveau coureur dans le référentiel.

    Réservé aux administrateurs.

    Paramètres :
        nom               (str)         : nom de famille du coureur.
        prenom            (str)         : prénom du coureur.
        sexe              (str)         : 'H' ou 'F'.
        nationalite       (str | None)  : nationalité (ex : 'FRA', 'USA').
        image             (str | None)  : URL ou chemin vers la photo du coureur.
        index_utmb_global (float | None): index global UTMB (0-1000).
        index_utmb_20k    (float | None): index format 20K (0-1000).
        index_utmb_50k    (float | None): index format 50K (0-1000).
        index_utmb_100k   (float | None): index format 100K (0-1000).
        index_utmb_100m   (float | None): index format 100M (0-1000).

    Retourne :
        dict | None : données du coureur créé ou None en cas d'erreur.

    Exemple d'utilisation :
        coureur = insert_coureur("Jornet", "Kilian", "H", "ESP",
                                  index_utmb_global=987.5)
    """

    try:
        admin    = get_supabase_admin_client()
        response = (
            admin
            .table("coureurs")
            .insert({
                "nom"               : nom,
                "prenom"            : prenom,
                "sexe"              : sexe,
                "nationalite"       : nationalite,
                "image"             : image,
                "index_utmb_global" : index_utmb_global,
                "index_utmb_20k"    : index_utmb_20k,
                "index_utmb_50k"    : index_utmb_50k,
                "index_utmb_100k"   : index_utmb_100k,
                "index_utmb_100m"   : index_utmb_100m,
            })
            .execute()
        )
        return response.data[0] if response.data else None

    except Exception as e:
        st.error(f"Erreur lors de l'ajout du coureur : {e}")
        return None


def update_index_utmb(
    coureur_id        : str,
    index_utmb_global : float = None,
    index_utmb_20k    : float = None,
    index_utmb_50k    : float = None,
    index_utmb_100k   : float = None,
    index_utmb_100m   : float = None,
) -> bool:
    """
    Met à jour les index UTMB d'un coureur existant.

    Seuls les index fournis (non None) sont mis à jour pour éviter
    d'écraser des données existantes.

    Paramètres :
        coureur_id        (str)         : UUID du coureur à mettre à jour.
        index_utmb_global (float | None): nouvel index global.
        index_utmb_20k    (float | None): nouvel index 20K.
        index_utmb_50k    (float | None): nouvel index 50K.
        index_utmb_100k   (float | None): nouvel index 100K.
        index_utmb_100m   (float | None): nouvel index 100M.

    Retourne :
        bool : True si la mise à jour a réussi, False sinon.

    Exemple d'utilisation :
        ok = update_index_utmb(coureur_id, index_utmb_global=991.2)
    """

    payload = {
        k: v for k, v in {
            "index_utmb_global" : index_utmb_global,
            "index_utmb_20k"    : index_utmb_20k,
            "index_utmb_50k"    : index_utmb_50k,
            "index_utmb_100k"   : index_utmb_100k,
            "index_utmb_100m"   : index_utmb_100m,
        }.items()
        if v is not None
    }

    if not payload:
        st.warning("Aucun index à mettre à jour.")
        return False

    try:
        admin = get_supabase_admin_client()
        admin \
            .table("coureurs") \
            .update(payload) \
            .eq("id", coureur_id) \
            .execute()
        return True

    except Exception as e:
        st.error(f"Erreur lors de la mise à jour des index : {e}")
        return False


def upsert_coureurs_batch(coureurs: list[dict]) -> bool:
    """
    Insère ou met à jour un ensemble de coureurs en une seule opération.

    Utilisé pour l'import en masse des index UTMB depuis une source externe
    (fichier CSV, scraping UTMB World Series, etc.).
    La clé de déduplication est (nom, prenom, sexe).

    Paramètres :
        coureurs (list[dict]) : liste de dictionnaires coureurs.
                                Champs obligatoires : nom, prenom, sexe.
                                Champs optionnels   : nationalite, image,
                                index_utmb_global, index_utmb_20k,
                                index_utmb_50k, index_utmb_100k,
                                index_utmb_100m.

    Retourne :
        bool : True si l'upsert a réussi, False sinon.

    Exemple d'utilisation :
        ok = upsert_coureurs_batch([
            {"nom": "Jornet", "prenom": "Kilian", "sexe": "H",
             "index_utmb_global": 987.5, "index_utmb_100m": 987.5},
        ])
    """

    if not coureurs:
        st.warning("Aucun coureur à importer.")
        return False

    try:
        admin = get_supabase_admin_client()
        admin \
            .table("coureurs") \
            .upsert(coureurs, on_conflict="nom,prenom,sexe") \
            .execute()
        return True

    except Exception as e:
        st.error(f"Erreur lors de l'import des coureurs : {e}")
        return False
