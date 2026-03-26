"""
COMPOSANT DIALOG - SAISIE DES PARIS - TRAIL BETTING

Ce module expose le dialog st.dialog permettant à un utilisateur de saisir
ou modifier son pari pour une course donnée.

Le dialog présente pour chaque genre (hommes et femmes) trois listes
déroulantes correspondant aux places 1, 2 et 3 du podium. Les listes
sont alimentées par les favoris de la course (participants triés par
index UTMB).

En mode modification, les listes sont pré-remplies avec le pari existant.
"""

# LIBRAIRIES ----------------------------
import streamlit as st

# LOCAL LIBRAIRIES ----------------------
from src.db.queries.queries_courses import get_favoris_par_course
from src.db.queries.queries_paris   import insert_pari, update_pari


# ---------------------------------------------------------------------------
# UTILITAIRES INTERNES
# ---------------------------------------------------------------------------

def _construire_options(df_favoris) -> tuple[list[str], dict[str, str]]:
    """
    Construit les options et le mapping pour une liste déroulante de coureurs.

    Transforme le DataFrame des favoris en deux structures :
        - Une liste de labels affichés dans le selectbox.
        - Un dictionnaire label → UUID pour récupérer l'UUID sélectionné.

    Paramètres :
        df_favoris (pd.DataFrame) : DataFrame des favoris (hommes ou femmes)
                                    avec les colonnes [coureur_id, prenom, nom, rang].

    Retourne :
        tuple :
            - list[str]       : labels affichés ("1. Kilian JORNET").
            - dict[str, str]  : mapping label → UUID coureur.
    """

    options = ["— Non renseigné —"]
    mapping = {"— Non renseigné —": None}

    for _, row in df_favoris.iterrows():
        label             = f"{int(row['rang'])}. {row['prenom']} {row['nom'].upper()}"
        options.append(label)
        mapping[label]    = str(row["coureur_id"])

    return options, mapping


def _index_pari_existant(
    uuid_existant : str | None,
    mapping       : dict[str, str]
) -> int:
    """
    Retrouve l'index de l'option correspondant à un UUID de pari existant.

    Utilisé pour pré-sélectionner la bonne valeur dans le selectbox
    lors d'une modification de pari.

    Paramètres :
        uuid_existant (str | None) : UUID du coureur déjà pronostiqué,
                                     ou None si non renseigné.
        mapping       (dict)       : dictionnaire label → UUID.

    Retourne :
        int : index de l'option dans la liste (0 = non renseigné).
    """

    if not uuid_existant:
        return 0

    for i, (label, uuid) in enumerate(mapping.items()):
        if uuid == uuid_existant:
            return i

    return 0


# ---------------------------------------------------------------------------
# DIALOG
# ---------------------------------------------------------------------------

@st.dialog("🎯 Saisir un pari", width="large")
def dialog_saisir_pari(course: dict, pari_existant: dict | None = None) -> None:
    """
    Dialog de saisie ou modification d'un pari pour une course.

    Affiche le nom et la date de la course en en-tête, puis présente
    deux sections côte à côte (hommes / femmes), chacune avec trois
    selectbox pour les places 1, 2 et 3 du podium.

    Les listes déroulantes sont alimentées par les favoris de la course
    (participants triés par index UTMB). En mode modification, les
    valeurs existantes sont pré-sélectionnées.

    Un bouton "Valider" enregistre ou met à jour le pari en base.
    Un message d'avertissement est affiché si l'utilisateur sélectionne
    le même coureur à deux places différentes.

    Paramètres :
        course        (dict)       : infos de la course.
                                     Clés attendues : id, nom, format, date_course.
        pari_existant (dict | None): pari existant pour pré-remplissage.
                                     Clés attendues : id, homme_1er, homme_2eme,
                                     homme_3eme, femme_1ere, femme_2eme, femme_3eme.
                                     None si nouveau pari.

    Retourne :
        None. Enregistre le pari via insert_pari() ou update_pari().
    """

    course_id     = course["id"]
    format_course = course["format"]
    user_id       = st.session_state["user_id"]
    est_modif     = pari_existant is not None

    # En-tête du dialog
    st.markdown(f"### 🏔️ {course['nom']}")
    st.caption(f"{format_course}  —  {course['date_course']}")
    st.divider()

    # Chargement des favoris de la course
    favoris = get_favoris_par_course(course_id, format_course, top_n=40)

    options_h, mapping_h = _construire_options(favoris["hommes"])
    options_f, mapping_f = _construire_options(favoris["femmes"])

    # Récupération des UUID existants pour pré-remplissage
    h1_existant = pari_existant.get("homme_1er")  if est_modif else None
    h2_existant = pari_existant.get("homme_2eme") if est_modif else None
    h3_existant = pari_existant.get("homme_3eme") if est_modif else None
    f1_existant = pari_existant.get("femme_1ere") if est_modif else None
    f2_existant = pari_existant.get("femme_2eme") if est_modif else None
    f3_existant = pari_existant.get("femme_3eme") if est_modif else None

    # -----------------------------------------------------------------------
    # FORMULAIRE : deux colonnes hommes / femmes
    # -----------------------------------------------------------------------

    col_h, col_f = st.columns(2)

    with col_h:
        st.markdown("**🏃 Hommes**")

        sel_h1 = st.selectbox(
            "🥇 1er homme",
            options = options_h,
            index   = _index_pari_existant(h1_existant, mapping_h),
            key     = f"pari_h1_{course_id}"
        )
        sel_h2 = st.selectbox(
            "🥈 2ème homme",
            options = options_h,
            index   = _index_pari_existant(h2_existant, mapping_h),
            key     = f"pari_h2_{course_id}"
        )
        sel_h3 = st.selectbox(
            "🥉 3ème homme",
            options = options_h,
            index   = _index_pari_existant(h3_existant, mapping_h),
            key     = f"pari_h3_{course_id}"
        )

    with col_f:
        st.markdown("**🏃‍♀️ Femmes**")

        sel_f1 = st.selectbox(
            "🥇 1ère femme",
            options = options_f,
            index   = _index_pari_existant(f1_existant, mapping_f),
            key     = f"pari_f1_{course_id}"
        )
        sel_f2 = st.selectbox(
            "🥈 2ème femme",
            options = options_f,
            index   = _index_pari_existant(f2_existant, mapping_f),
            key     = f"pari_f2_{course_id}"
        )
        sel_f3 = st.selectbox(
            "🥉 3ème femme",
            options = options_f,
            index   = _index_pari_existant(f3_existant, mapping_f),
            key     = f"pari_f3_{course_id}"
        )

    # Résolution des UUID sélectionnés
    uuid_h1 = mapping_h[sel_h1]
    uuid_h2 = mapping_h[sel_h2]
    uuid_h3 = mapping_h[sel_h3]
    uuid_f1 = mapping_f[sel_f1]
    uuid_f2 = mapping_f[sel_f2]
    uuid_f3 = mapping_f[sel_f3]

    # -----------------------------------------------------------------------
    # VALIDATION : détection des doublons dans le podium
    # -----------------------------------------------------------------------

    uuids_h = [u for u in [uuid_h1, uuid_h2, uuid_h3] if u]
    uuids_f = [u for u in [uuid_f1, uuid_f2, uuid_f3] if u]

    doublon_h = len(uuids_h) != len(set(uuids_h))
    doublon_f = len(uuids_f) != len(set(uuids_f))

    if doublon_h:
        st.warning("⚠️ Tu as sélectionné le même coureur à plusieurs places (hommes).")
    if doublon_f:
        st.warning("⚠️ Tu as sélectionné la même coureuse à plusieurs places (femmes).")

    st.divider()

    # -----------------------------------------------------------------------
    # BOUTON VALIDER
    # -----------------------------------------------------------------------

    if st.button(
        "✅ Valider mon pari",
        type                = "primary",
        use_container_width = True,
        disabled            = doublon_h or doublon_f
    ):
        if est_modif:
            ok = update_pari(
                pari_id    = pari_existant["id"],
                homme_1er  = uuid_h1,
                homme_2eme = uuid_h2,
                homme_3eme = uuid_h3,
                femme_1ere = uuid_f1,
                femme_2eme = uuid_f2,
                femme_3eme = uuid_f3,
            )
            if ok:
                st.success("Pari modifié avec succès ! 🎉")

        else:
            pari = insert_pari(
                user_id    = user_id,
                course_id  = course_id,
                homme_1er  = uuid_h1,
                homme_2eme = uuid_h2,
                homme_3eme = uuid_h3,
                femme_1ere = uuid_f1,
                femme_2eme = uuid_f2,
                femme_3eme = uuid_f3,
            )
            if pari:
                st.success("Pari enregistré ! Bonne chance 🏔️")