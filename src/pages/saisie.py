"""
PAGE SAISIE - ADMINISTRATION - TRAIL BETTING

Page réservée aux administrateurs pour la mise à jour hebdomadaire
du contenu de l'application (chaque vendredi).

Trois onglets disponibles :
    1. Ajouter une course : saisie obligatoire de tous les champs
       (événement, nom, format, distance, dénivelé, lieu, date, avis expert).
    2. Ajouter les participants : sélection d'une course et import d'un
       fichier CSV/Excel contenant les colonnes Nom, Prenom, Sexe.
       Réconciliation automatique obligatoire avec la table coureurs —
       les participants introuvables sont signalés et ignorés.
    3. Ajouter les résultats : sélection d'une course et saisie du podium
       hommes et femmes à partir de la liste des participants inscrits.

Accès réservé aux utilisateurs avec role = 'admin'.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
import pandas as pd
from streamlit_extras.add_vertical_space import add_vertical_space

# LOCAL LIBRAIRIES ----------------------
from src.functions.utils                import extraire_bloc_style
from src.db.queries.queries_courses     import insert_course
from src.db.queries.queries_coureurs    import get_tous_les_coureurs
from src.db.queries.queries_resultats   import insert_resultats, resultats_existent
from src.db.connection                  import get_supabase_admin_client


# ---------------------------------------------------------------------------
# UTILITAIRES INTERNES
# ---------------------------------------------------------------------------

def _verifier_acces_admin() -> bool:
    """
    Vérifie que l'utilisateur connecté a le rôle admin.

    Affiche un message d'erreur et stoppe l'exécution si ce n'est pas le cas.

    Retourne :
        bool : True si l'utilisateur est admin, False sinon.
    """

    if not st.session_state.get("authentifie"):
        st.error("🔐 Tu dois être connecté pour accéder à cette page.")
        st.stop()
        return False

    if st.session_state.get("user_role") != "admin":
        st.error("🚫 Accès réservé aux administrateurs.")
        st.stop()
        return False

    return True


def _get_toutes_les_courses() -> pd.DataFrame:
    """
    Récupère toutes les courses (passées et à venir) pour les sélecteurs admin.

    Retourne :
        pd.DataFrame : colonnes [id, nom, evenement, format, date_course]
                       triées par date décroissante.
    """

    try:
        admin    = get_supabase_admin_client()
        response = (
            admin
            .table("courses")
            .select("id, nom, evenement, format, date_course")
            .order("date_course", desc=True)
            .execute()
        )
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des courses : {e}")
        return pd.DataFrame()


def _label_course(row: pd.Series) -> str:
    """
    Génère un label lisible pour une course dans les selectbox.

    Format : "Événement — Nom (Format) — JJ/MM/AAAA"

    Paramètres :
        row (pd.Series) : ligne du DataFrame courses.

    Retourne :
        str : label formaté pour affichage dans un selectbox.
    """

    evenement = f"{row['evenement']} — " if row.get("evenement") else ""
    date      = pd.to_datetime(row["date_course"]).strftime("%d/%m/%Y")
    return f"{evenement}{row['nom']} ({row['format']}) — {date}"


# ---------------------------------------------------------------------------
# ONGLET 1 : AJOUTER UNE COURSE
# ---------------------------------------------------------------------------

def _onglet_ajouter_course() -> None:
    """
    Affiche le formulaire de création d'une nouvelle course.

    Tous les champs sont obligatoires : événement, nom, format, distance,
    dénivelé, lieu et date. L'avis expert est le seul champ optionnel.
    Vérifie l'absence de doublon sur (nom, date_course) avant insertion.

    Retourne :
        None
    """

    st.markdown("#### ➕ Nouvelle course")
    st.caption("Tous les champs sont obligatoires sauf l'avis expert.")

    add_vertical_space(1)

    col1, col2 = st.columns(2)

    with col1:
        evenement   = st.text_input(
            "Événement *",
            placeholder = "Val d'Aran by UTMB",
            help        = "Nom de l'événement parent (ex : UTMB Mont-Blanc)."
        )
        nom         = st.text_input(
            "Nom de la course *",
            placeholder = "CCC"
        )
        format_c    = st.selectbox(
            "Format *",
            options = ["20K", "50K", "100K", "100M"]
        )
        lieu        = st.text_input(
            "Lieu *",
            placeholder = "Chamonix, France"
        )

    with col2:
        date_course = st.date_input("Date de la course *")
        distance    = st.number_input(
            "Distance (km) *",
            min_value = 0.1,
            step      = 0.5,
            format    = "%.1f"
        )
        denivele    = st.number_input(
            "Dénivelé positif (m) *",
            min_value = 0,
            step      = 100,
        )

    avis_expert = st.text_area(
        "Avis du Duc de Savoie",
        placeholder = "Analyse et pronostic de la course... (optionnel)",
        height      = 120
    )

    add_vertical_space(1)

    if st.button("✅ Ajouter la course", type="primary"):

        # Validation des champs obligatoires
        champs_vides = []
        if not evenement : champs_vides.append("Événement")
        if not nom       : champs_vides.append("Nom")
        if not lieu      : champs_vides.append("Lieu")
        if distance <= 0 : champs_vides.append("Distance")
        if denivele <= 0 : champs_vides.append("Dénivelé")

        if champs_vides:
            st.warning(f"Champs obligatoires manquants : {', '.join(champs_vides)}.")
            return

        # Vérification doublon sur (nom, date_course)
        try:
            admin    = get_supabase_admin_client()
            response = (
                admin
                .table("courses")
                .select("id")
                .eq("nom", nom)
                .eq("date_course", str(date_course))
                .limit(1)
                .execute()
            )
            if response.data:
                st.warning(
                    f"Une course **{nom}** existe déjà à cette date. "
                    "Vérifie le calendrier avant d'ajouter."
                )
                return
        except Exception as e:
            st.error(f"Erreur lors de la vérification des doublons : {e}")
            return

        # Insertion
        course = insert_course(
            evenement     = evenement,
            nom           = nom,
            format_course = format_c,
            distance      = float(distance),
            denivele      = float(denivele),
            lieu          = lieu,
            date_course   = str(date_course),
            avis_expert   = avis_expert if avis_expert else None,
        )

        if course:
            st.success(f"Course **{nom}** ajoutée avec succès ! 🎉")
            st.rerun()


# ---------------------------------------------------------------------------
# ONGLET 2 : AJOUTER LES PARTICIPANTS
# ---------------------------------------------------------------------------

def _reconcilier_participants(
    df_import   : pd.DataFrame,
    df_coureurs : pd.DataFrame,
    course_id   : str                  # ← nouveau paramètre
) -> tuple[list[dict], list[dict], pd.DataFrame]:
    """
    Réconcilie les participants importés avec le référentiel coureurs.

    Pour chaque ligne du fichier importé (Nom, Prenom, Sexe), tente de
    trouver le coureur correspondant dans df_coureurs via une jointure
    insensible à la casse sur (nom, prenom, sexe).

    Seuls les participants trouvés dans le référentiel sont conservés.
    Les non-trouvés sont retournés dans un DataFrame séparé pour signalement.

    Paramètres :
        df_import   (pd.DataFrame) : données importées depuis le fichier.
                                     Colonnes attendues : Nom, Prenom, Sexe.
        df_coureurs (pd.DataFrame) : référentiel complet des coureurs.

    Retourne :
        tuple :
            - list[dict]   : participants réconciliés prêts pour insertion,
                             avec coureur_id, nom, prenom, sexe.
            - pd.DataFrame : participants non trouvés dans le référentiel.
    """

    df_import   = df_import.copy()
    df_coureurs = df_coureurs.copy()

    # Normalisation
    df_import["nom_norm"]    = df_import["Nom"].str.strip().str.upper()
    df_import["prenom_norm"] = df_import["Prenom"].str.strip().str.upper()
    df_import["sexe_norm"]   = df_import["Sexe"].str.strip().str.upper()

    df_coureurs["nom_norm"]    = df_coureurs["nom"].str.strip().str.upper()
    df_coureurs["prenom_norm"] = df_coureurs["prenom"].str.strip().str.upper()
    df_coureurs["sexe_norm"]   = df_coureurs["sexe"].str.strip().str.upper()

    # Jointure sur (nom, prenom, sexe)
    merged = df_import.merge(
        df_coureurs[["id", "nom_norm", "prenom_norm", "sexe_norm"]],
        on  = ["nom_norm", "prenom_norm", "sexe_norm"],
        how = "left"
    )

    trouves     = merged[merged["id"].notna()]
    non_trouves = merged[merged["id"].isna()][["Nom", "Prenom", "Sexe"]]

    # Chargement des coureur_id déjà en base pour cette course
    admin = get_supabase_admin_client()
    existants_resp = (
        admin
        .schema("trail_betting_db")
        .table("participants_course")
        .select("coureur_id")
        .eq("course_id", course_id)
        .execute()
    )
    deja_inseres = {p["coureur_id"] for p in existants_resp.data}

    participants_nouveaux  = []
    participants_existants = []

    for _, row in trouves.iterrows():
        entry = {
            "coureur_id": row["id"],
            "nom"       : row["Nom"],
            "prenom"    : row["Prenom"],
            "sexe"      : row["sexe_norm"],
        }
        if row["id"] in deja_inseres:
            participants_existants.append(entry)
        else:
            participants_nouveaux.append(entry)

    return participants_nouveaux, participants_existants, non_trouves.reset_index(drop=True)

def _insert_participants_reconcilies(
    course_id    : str,
    participants : list[dict]       # uniquement les nouveaux
) -> bool:
    """
    Insère les participants réconciliés dans la table participants_course.

    Stratégie delete + insert : supprime d'abord les participants existants
    pour cette course, puis insère les nouveaux.

    Paramètres :
        course_id    (str)        : UUID de la course.
        participants (list[dict]) : participants réconciliés avec coureur_id,
                                    nom, prenom, sexe.

    Retourne :
        bool : True si l'insertion a réussi, False sinon.
    """
    if not participants:
        return True

    try:
        admin = get_supabase_admin_client()

        rows = [
            {
                "course_id" : course_id,
                "coureur_id": p["coureur_id"],
                "nom"       : p["nom"],
                "prenom"    : p["prenom"],
                "sexe"      : p["sexe"],
            }
            for p in participants
        ]
        admin.schema("trail_betting_db").table("participants_course").insert(rows).execute()
        return True

    except Exception as e:
        st.error(f"Erreur lors de l'enregistrement des participants : {e}")
        return False

def _onglet_participants() -> None:
    """
    Affiche l'interface d'import des participants pour une course.

    Étapes :
        1. Sélection de la course cible.
        2. Upload d'un fichier CSV ou Excel avec colonnes Nom, Prenom, Sexe.
        3. Réconciliation automatique obligatoire avec la table coureurs.
        4. Affichage des participants trouvés et non trouvés.
        5. Confirmation et insertion des participants réconciliés uniquement.

    Retourne :
        None
    """

    st.markdown("#### 👥 Participants d'une course")
    st.caption(
        "Importe un fichier CSV ou Excel avec les colonnes **Nom**, **Prenom**, **Sexe**. "
        "Seuls les coureurs présents dans le référentiel seront intégrés."
    )

    add_vertical_space(1)

    # Sélection de la course
    df_courses = _get_toutes_les_courses()

    if df_courses.empty:
        st.info("Aucune course disponible. Commence par en ajouter une.")
        return

    labels_courses = (
        df_courses
        .sort_values(["evenement", "date_course"], na_position="last")
        .apply(_label_course, axis=1)
        .tolist()
    )
    df_courses = df_courses.sort_values(["evenement", "date_course"], na_position="last").reset_index(drop=True)

    idx_course     = st.selectbox(
        "Course cible *",
        options     = range(len(labels_courses)),
        format_func = lambda i: labels_courses[i],
        key         = "select_course_participants"
    )
    course_id = df_courses.iloc[idx_course]["id"]

    add_vertical_space(1)

    # Upload du fichier
    fichier = st.file_uploader(
        "Fichier participants (CSV ou Excel)",
        type = ["csv", "xlsx", "xls"],
        key  = "upload_participants"
    )

    if not fichier:
        return

    # Lecture du fichier
    try:
        df_import = (
            pd.read_csv(fichier , sep=";")
            if fichier.name.endswith(".csv")
            else pd.read_excel(fichier)
        )
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier : {e}")
        return

    # Vérification des colonnes obligatoires
    colonnes_requises  = {"Nom", "Prenom", "Sexe"}
    colonnes_manquantes = colonnes_requises - set(df_import.columns)

    if colonnes_manquantes:
        st.error(
            f"Colonnes manquantes dans le fichier : {', '.join(colonnes_manquantes)}. "
            "Les colonnes attendues sont exactement : **Nom**, **Prenom**, **Sexe**."
        )
        return

    st.success(f"Fichier chargé : **{len(df_import)} lignes** détectées.")

    # Réconciliation — on passe course_id en paramètre
    df_coureurs = get_tous_les_coureurs()
    participants_nouveaux, participants_existants, non_trouves = _reconcilier_participants(
        df_import, df_coureurs, course_id
    )

    add_vertical_space(1)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"**🆕 Nouveaux : {len(participants_nouveaux)}**")
        if participants_nouveaux:
            st.dataframe(
                pd.DataFrame(participants_nouveaux)[["nom", "prenom", "sexe"]],
                use_container_width=True,
                hide_index=True
            )

    with col2:
        st.markdown(f"**⏭️ Déjà enregistrés : {len(participants_existants)}**")
        if participants_existants:
            st.dataframe(
                pd.DataFrame(participants_existants)[["nom", "prenom", "sexe"]],
                use_container_width=True,
                hide_index=True
            )

    with col3:
        st.markdown(f"**❌ Non trouvés : {len(non_trouves)}**")
        if not non_trouves.empty:
            st.dataframe(non_trouves, use_container_width=True, hide_index=True)

    if not participants_nouveaux:
        st.info("Aucun nouveau participant à enregistrer.")
        return

    add_vertical_space(1)

    if st.button(
        f"✅ Enregistrer {len(participants_nouveaux)} nouveaux participants",
        type="primary"
    ):
        ok = _insert_participants_reconcilies(course_id, participants_nouveaux)
        if ok:
            st.success(f"**{len(participants_nouveaux)} participants** enregistrés ! 🎉")

# ---------------------------------------------------------------------------
# ONGLET 3 : AJOUTER LES RESULTATS
# ---------------------------------------------------------------------------

def _get_resultats_bruts(course_id: str) -> dict | None:
    """
    Récupère les résultats bruts d'une course (avec UUID des coureurs).

    Utilisé pour pré-remplir les selectbox en mode édition.

    Paramètres :
        course_id (str) : UUID de la course.

    Retourne :
        dict | None : résultats avec UUID des coureurs, ou None si inexistants.
    """

    try:
        admin    = get_supabase_admin_client()
        response = (
            admin
            .table("resultats")
            .select("*")
            .eq("course_id", course_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    except Exception as e:
        st.error(f"Erreur lors du chargement des résultats : {e}")
        return None


def _onglet_resultats() -> None:
    """
    Affiche l'interface de saisie ou modification des résultats d'une course.

    Deux modes :
        - Insertion : aucun résultat existant, bouton "Enregistrer".
        - Edition   : résultats existants pré-remplis, bouton "Modifier".
          Note : le trigger de scoring ne se relance pas sur un UPDATE.

    Retourne :
        None
    """

    st.markdown("#### 🏆 Résultats d'une course")
    st.caption(
        "Saisis le podium officiel. "
        "Cette action déclenche le calcul automatique des points pour tous les paris."
    )

    add_vertical_space(1)

    # Sélection de la course
    df_courses = _get_toutes_les_courses()

    if df_courses.empty:
        st.info("Aucune course disponible.")
        return

    labels_courses = (
        df_courses
        .sort_values(["evenement", "date_course"], na_position="last")
        .apply(_label_course, axis=1)
        .tolist()
    )
    df_courses = df_courses.sort_values(["evenement", "date_course"], na_position="last").reset_index(drop=True)

    idx_course = st.selectbox(
        "Course *",
        options     = range(len(labels_courses)),
        format_func = lambda i: labels_courses[i],
        key         = "select_course_resultats"
    )
    course_id = df_courses.iloc[idx_course]["id"]

    add_vertical_space(1)

    # Détection du mode : insertion ou édition
    resultats_existants = _get_resultats_bruts(course_id)
    est_edition         = resultats_existants is not None

    if est_edition:
        st.info("📝 Des résultats existent déjà pour cette course. Tu peux les modifier.", icon="✏️")

    # Chargement des participants
    try:
        admin    = get_supabase_admin_client()
        response = (
            admin
            .table("participants_course")
            .select("coureur_id, nom, prenom, sexe")
            .eq("course_id", course_id)
            .execute()
        )
        df_participants = pd.DataFrame(response.data) if response.data else pd.DataFrame()

    except Exception as e:
        st.error(f"Erreur lors du chargement des participants : {e}")
        return

    if df_participants.empty:
        st.info(
            "Aucun participant enregistré pour cette course. "
            "Importe d'abord les participants dans l'onglet **Participants**."
        )
        return

    # Séparation H / F
    df_h = df_participants[df_participants["sexe"] == "H"].reset_index(drop=True)
    df_f = df_participants[df_participants["sexe"] == "F"].reset_index(drop=True)

    # Construction des options selectbox
    def _build_opts(df: pd.DataFrame) -> tuple[list, dict]:
        options = ["— Non renseigné —"]
        mapping = {"— Non renseigné —": None}
        for _, row in df.iterrows():
            label          = f"{row['prenom']} {row['nom'].upper()}"
            options.append(label)
            mapping[label] = str(row["coureur_id"])
        return options, mapping

    def _index_existant(uuid_existant: str | None, mapping: dict) -> int:
        """Retrouve l'index d'un UUID existant dans le mapping pour pré-sélection."""
        if not uuid_existant:
            return 0
        for i, uuid in enumerate(mapping.values()):
            if uuid == uuid_existant:
                return i
        return 0

    opts_h, map_h = _build_opts(df_h)
    opts_f, map_f = _build_opts(df_f)

    # Pré-remplissage en mode édition
    h1_pre = resultats_existants.get("homme_1er")  if est_edition else None
    h2_pre = resultats_existants.get("homme_2eme") if est_edition else None
    h3_pre = resultats_existants.get("homme_3eme") if est_edition else None
    f1_pre = resultats_existants.get("femme_1ere") if est_edition else None
    f2_pre = resultats_existants.get("femme_2eme") if est_edition else None
    f3_pre = resultats_existants.get("femme_3eme") if est_edition else None

    col_h, col_f = st.columns(2)

    with col_h:
        st.markdown("**🏃 Hommes**")
        sel_h1 = st.selectbox("🥇 1er",  opts_h, index=_index_existant(h1_pre, map_h), key=f"res_h1_{course_id}")
        sel_h2 = st.selectbox("🥈 2ème", opts_h, index=_index_existant(h2_pre, map_h), key=f"res_h2_{course_id}")
        sel_h3 = st.selectbox("🥉 3ème", opts_h, index=_index_existant(h3_pre, map_h), key=f"res_h3_{course_id}")

    with col_f:
        st.markdown("**🏃‍♀️ Femmes**")
        sel_f1 = st.selectbox("🥇 1ère",  opts_f, index=_index_existant(f1_pre, map_f), key=f"res_f1_{course_id}")
        sel_f2 = st.selectbox("🥈 2ème",  opts_f, index=_index_existant(f2_pre, map_f), key=f"res_f2_{course_id}")
        sel_f3 = st.selectbox("🥉 3ème",  opts_f, index=_index_existant(f3_pre, map_f), key=f"res_f3_{course_id}")

    uuid_h1 = map_h[sel_h1]
    uuid_h2 = map_h[sel_h2]
    uuid_h3 = map_h[sel_h3]
    uuid_f1 = map_f[sel_f1]
    uuid_f2 = map_f[sel_f2]
    uuid_f3 = map_f[sel_f3]

    # Détection des doublons
    uuids_h   = [u for u in [uuid_h1, uuid_h2, uuid_h3] if u]
    uuids_f   = [u for u in [uuid_f1, uuid_f2, uuid_f3] if u]
    doublon_h = len(uuids_h) != len(set(uuids_h))
    doublon_f = len(uuids_f) != len(set(uuids_f))

    if doublon_h:
        st.warning("⚠️ Le même coureur est sélectionné à plusieurs places (hommes).")
    if doublon_f:
        st.warning("⚠️ La même coureuse est sélectionnée à plusieurs places (femmes).")

    add_vertical_space(1)

    label_bouton = "✏️ Modifier les résultats" if est_edition else "✅ Enregistrer les résultats"

    if st.button(label_bouton, type="primary", disabled=doublon_h or doublon_f):

        if est_edition:
            from src.db.queries.queries_resultats import update_resultats
            ok = update_resultats(
                course_id  = course_id,
                homme_1er  = uuid_h1,
                homme_2eme = uuid_h2,
                homme_3eme = uuid_h3,
                femme_1ere = uuid_f1,
                femme_2eme = uuid_f2,
                femme_3eme = uuid_f3,
            )
            if ok:
                st.success("Résultats modifiés ! ✅")
                st.caption(
                    "⚠️ Note : le recalcul automatique des points ne se relance pas "
                    "sur une modification. Si nécessaire, contacte l'administrateur DB."
                )
        else:
            resultat = insert_resultats(
                course_id  = course_id,
                admin_id   = st.session_state["user_id"],
                homme_1er  = uuid_h1,
                homme_2eme = uuid_h2,
                homme_3eme = uuid_h3,
                femme_1ere = uuid_f1,
                femme_2eme = uuid_f2,
                femme_3eme = uuid_f3,
            )
            if resultat:
                st.success(
                    "Résultats enregistrés ! 🎉 "
                    "Les points ont été calculés automatiquement pour tous les paris."
                )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Fonction principale de la page d'administration.

    Vérifie les droits admin, injecte les styles CSS puis affiche
    les trois onglets de saisie.

    Retourne :
        None
    """

    _verifier_acces_admin()

    st.markdown(
        extraire_bloc_style("page", "src/assets/styles/styles.html"),
        unsafe_allow_html=True
    )

    st.markdown("<h2 class='section-titre'>⚙️ Administration</h2>", unsafe_allow_html=True)
    st.caption(
        f"Connecté en tant que **{st.session_state.get('user_pseudo')}** — accès admin"
    )

    add_vertical_space(1)

    tab_course, tab_participants, tab_resultats = st.tabs([
        "➕ Ajouter une course",
        "👥 Participants",
        "🏆 Résultats",
    ])

    with tab_course:
        add_vertical_space(1)
        _onglet_ajouter_course()

    with tab_participants:
        add_vertical_space(1)
        _onglet_participants()

    with tab_resultats:
        add_vertical_space(1)
        _onglet_resultats()
