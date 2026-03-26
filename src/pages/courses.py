"""
PAGE COURSES A VENIR

Cette page affiche la liste des courses à venir sous forme de volets dépliables.

Pour chaque course, l'utilisateur peut consulter :
    - Le top 10 des favoris hommes et femmes selon l'index UTMB global et l'index spécifique au format de la course.
    - L'avis du Duc de Savoie (expert trail).
    - Un bouton pour saisir ou modifier son pari via un dialog st.dialog.

L'accès à la saisie d'un pari nécessite d'être connecté.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.stylable_container import stylable_container

# LOCAL LIBRAIRIES ----------------------
from src.functions.utils import get_image_base64
from src.db.queries.queries_courses import get_courses_a_venir, get_favoris_par_course
from src.db.queries.queries_paris import pari_existe, get_pari_par_user_et_course
from src.functions.paris_dialog import dialog_saisir_pari

# Dictionnaire de mapping format → image
FORMAT_IMAGES = {
    "20K": "src/assets/images/20K.png",
    "50K": "src/assets/images/50K.png",
    "100K": "src/assets/images/100K.png",
    "100M": "src/assets/images/100M.png"
}


# COMPOSANTS INTERNES
# ---------------------------------------------------------------------------
def afficher_favoris(course_id: str, format_course: str) -> None:
    """
    Affiche le top 10 des favoris hommes et femmes pour une course.
    Présente deux tableaux côte à côte : favoris hommes à gauche, favoris femmes à droite.

    Paramètres :
        course_id (str) : UUID de la course.
        format_course (str) : format UTMB pour choisir l'index pertinent.
    """

    favoris = get_favoris_par_course(course_id, format_course, top_n = 10)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div style="font-size: 14px; font-weight: bold; font-family: system-ui; margin-bottom: 8px; color: #D20606">
            Favoris Hommes :
            </div>
            """,
            unsafe_allow_html = True
        )

        df_h = favoris["hommes"]
        if df_h.empty:
            st.caption("Aucun favori disponible.")
        else:
            # Sélection et renommage des colonnes pour l'affichage
            df_affichage = df_h[["rang", "prenom", "nom", "nationalite", "index_utmb_global", "index_utmb_format"]]
            df_affichage["coureur"] = df_affichage["prenom"] + " " + df_affichage["nom"].str.upper()
            df_affichage = df_affichage[["rang", "coureur", "nationalite", "index_utmb_global", "index_utmb_format"]
            ].rename(columns = {
                "rang": "Rang",
                "coureur": "Coureur",
                "nationalite": "Nationalité",
                "index_utmb_global": "Index global",
                "index_utmb_format": f"Index {format_course}"
            })
            st.dataframe(df_affichage, width = 'stretch', hide_index = True)

    with col2:
        st.markdown(
            f"""
            <div style="font-size: 14px; font-weight: bold; font-family: system-ui; margin-bottom: 8px; color: #D20606"">
            Favorites Femmes :
            </div>
            """,
            unsafe_allow_html = True
        )

        df_f = favoris["femmes"]
        if df_f.empty:
            st.caption("Aucune favorite disponible.")
        else:
            # Sélection et renommage des colonnes pour l'affichage
            df_affichage = df_f[["rang", "prenom", "nom", "nationalite", "index_utmb_global", "index_utmb_format"]]
            df_affichage["coureuse"] = df_affichage["prenom"] + " " + df_affichage["nom"].str.upper()
            df_affichage = df_affichage[["rang", "coureuse", "nationalite", "index_utmb_global", "index_utmb_format"]
            ].rename(columns = {
                "rang": "Rang",
                "coureuse": "Coureuse",
                "nationalite": "Nationalité",
                "index_utmb_global": "Index global",
                "index_utmb_format": f"Index {format_course}"
            })
            st.dataframe(df_affichage, width = 'stretch', hide_index = True)


def afficher_avis_expert(avis_expert: str | None) -> None:
    """
    Affiche l'avis du Duc de Savoie pour une course.
    Affiche un message par défaut si l'avis n'a pas encore été saisi.

    Paramètres :
        avis_expert (str | None) : texte de l'analyse du Duc, ou None.
    """

    st.markdown("**L'avis du Duc de Savoie &nbsp; ❤**")
    if avis_expert:
        st.info(avis_expert)
    else:
        st.caption("L'avis de ton souverain n'est pas encore disponible pour cette course.")


def afficher_bouton_pari(course: dict) -> None:
    """
    Affiche le bouton de saisie ou modification du pari pour une course.

    Si l'utilisateur n'est pas connecté, affiche un message d'invitation à la connexion.
    Si un pari existe déjà, le bouton passe en mode modification. Le clic ouvre le dialog de saisie du pari.

    Paramètres :
        course (dict) : dictionnaire contenant les infos de la course.
    """

    # Utilisateur non connecté : invitation à se connecter
    if not st.session_state.get("authentifie"):
        st.caption("Connecte-toi pour saisir un pari.")
        return

    # Détermination du libellé selon l'existence d'un pari
    a_deja_parie = pari_existe(st.session_state["user_id"], course["id"])
    label_bouton = "Modifier mon pari" if a_deja_parie else "Saisir un pari"

    if st.button(label_bouton, key = f"btn_pari_{course['id']}"):
        # Récupération du pari existant pour pré-remplissage éventuel
        pari_existant = get_pari_par_user_et_course(st.session_state["user_id"], course["id"]) if a_deja_parie else None
        dialog_saisir_pari(course = course, pari_existant = pari_existant)


def afficher_volet_course(course: dict) -> None:
    """
    Affiche un volet dépliable complet pour une course.

    Contient dans l'ordre :
        1. Les informations générales (lieu, date, format).
        2. Le top 10 des favoris H/F.
        3. L'avis du Duc.
        4. Le bouton de saisie du pari.

    Paramètres :
        course (dict) : dictionnaire avec les champs de la course.
    """

    # Label du volet : nom + date + format
    label_expander = (f"{course['nom']}  —  " f"{course['format']}  —  "f"{course['date_course']}")
    with st.expander(label_expander, expanded = False):

        # Informations générales
        col1, col2, col3 = st.columns(3)
        with col1:
            img_path = FORMAT_IMAGES.get(course["format"])
            img_b64 = get_image_base64(img_path)
            st.markdown(
            """
            <div style="font-size: 14px;">
            Format
            </div>
            """,
            unsafe_allow_html = True
        )
            st.markdown(
                f'<img src="data:image/png;base64,{img_b64}" style="width:130px; height:auto; margin-top: 10px">',
                unsafe_allow_html = True
            )
        col2.metric("Lieu", course["lieu"] or "—")
        col3.metric("Date", str(course["date_course"]))

        # CONTAINER
        with stylable_container(
            key = f"container_ombre_{course}",
            css_styles = """
                {
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    background-color: white;
                    padding: 8px 6px 24px;
                    box-shadow: 3px 3px 5px rgba(0, 32, 96, 0.25); /* Ombre bleue (#002060) */
                }
            """,
        ):
            col1, col2 = st.columns(2)

            # Top 10 favoris
            afficher_favoris(course["id"], course["format"])

        col1, col2 = st.columns(2)
        # Avis du Duc
        with col1:
            add_vertical_space(1)
            afficher_bouton_pari(course)

        # Bouton pari
        with col2:
            # CONTAINER AVIS DU DUC
            with stylable_container(
                key = f"container_infos_{course}",
                css_styles = """
                    {
                        border-radius: 0.5rem;
                        background-color: #FCF4F0;
                        border: 1px solid rgba(49, 51, 63, 0.2);
                        border-color: #D20606;
                        padding: 10px 10px 11px;
                    }
                """
            ):
                afficher_avis_expert(course.get("avis_expert"))


# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    """
    Fonction principale de la page courses à venir.

    Orchestre l'affichage :
        1. Injection des styles CSS.
        2. Titre de la page.
        3. Message si aucune course à venir.
        4. Un volet dépliable par course à venir.
    """

    st.markdown(
        """
        <div style="font-size: 25px; font-weight: bold; font-family: system-ui; text-align: center">
        Courses à venir
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(1)

    # Chargement des courses
    df_courses = get_courses_a_venir()
    if df_courses.empty:
        st.info("Aucune course à venir pour le moment. Reviens vendredi pour les prochaines annonces !")
        return

    # Affichage groupé par événement
    evenements = df_courses["evenement"].fillna("Autres courses").unique()
    for evenement in evenements:
        st.markdown(
            f"""
            <div style="font-size: 15px; font-family: system-ui; margin-bottom: 8px">
            ◼ &nbsp; <span style="font-style: italic">{evenement}</span>
            </div>
            """,
            unsafe_allow_html = True
        )

        df_evenement = df_courses[df_courses["evenement"].fillna("Autres courses") == evenement]

        for _, course in df_evenement.iterrows():
            afficher_volet_course(course.to_dict())
        add_vertical_space(1)