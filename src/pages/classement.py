"""
PAGE CLASSEMENT

Cette page affiche le classement général des participants ainsi que les statistiques personnelles de l'utilisateur connecté.

Contenu :
    - Bloc statistiques personnelles (rang, points, taux de réussite) affiché uniquement si l'utilisateur est connecté.
    - Classement général de tous les participants avec rang, pseudo, points, nombre de paris et taux de réussite.
    - Historique personnel des points course par course (graphique d'évolution du cumul) affiché si l'utilisateur est connecté et a au moins un pari scoré.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space

# LOCAL LIBRAIRIES ----------------------
from src.db.queries.queries_classement import get_classement_general, get_stats_par_user, get_historique_points_user


# COMPOSANTS INTERNES
# ---------------------------------------------------------------------------
def afficher_stats_personnelles(user_id: str) -> None:
    """
    Affiche le bloc de statistiques personnelles de l'utilisateur connecté.

    Présente 4 métriques côte à côte : rang actuel, points cumulés, nombre de paris scorés et taux de réussite.
    Le bloc est masqué si l'utilisateur n'a pas encore de paris scorés.

    Paramètres :
        user_id (str) : UUID de l'utilisateur connecté.
    """

    stats = get_stats_par_user(user_id)

    if not stats:
        st.caption("Tes statistiques apparaîtront ici une fois tes premiers paris scorés.")
        return
    
    st.markdown("#### 📊 Tes statistiques")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        label = "🏅 Rang",
        value = f"#{stats[0]['rang']}",
    )
    col2.metric(
        label = "⭐ Points",
        value = stats[0]["points_total"],
    )
    col3.metric(
        label = "🎯 Paris scorés",
        value = f"{stats[0]['nb_paris_scores']} / {stats[0]['nb_paris']}",
    )
    col4.metric(
        label = "📈 Taux de réussite",
        value = f"{stats[0]['taux_reussite']} %",
    )


def afficher_historique(user_id: str) -> None:
    """
    Affiche le graphique d'évolution des points cumulés de l'utilisateur.

    Trace une courbe du cumul de points au fil des courses, avec en dessous un tableau détaillé par course (points gagnés, pronostics vs résultats réels).
    Le bloc est masqué si aucun historique n'est disponible.

    Paramètres :
        user_id (str) : UUID de l'utilisateur connecté.
    """

    df = get_historique_points_user(user_id)

    if df.empty:
        return

    st.markdown("#### 📈 Évolution de tes points")

    # Graphique d'évolution du cumul
    st.line_chart(
        df.set_index("date_course")["cumul_points"],
        use_container_width = True,
    )

    add_vertical_space(1)

    # Tableau détaillé par course
    st.markdown("**Détail par course**")

    df_affichage = df[[
        "date_course","course_evt" ,"course_nom", "course_format",
        "points_gagnes",
        "homme_1er_parie", "homme_1er_reel",
        "femme_1ere_pariee", "femme_1ere_reelle",
    ]].rename(columns={
        "date_course"       : "Date",
        "course_evt"        : "Evénement",
        "course_nom"        : "Course",
        "course_format"     : "Format",
        "points_gagnes"     : "Points",
        "homme_1er_parie"   : "🏃 Pronostic",
        "homme_1er_reel"    : "🏃 Réel",
        "femme_1ere_pariee" : "🏃‍♀️ Pronostic",
        "femme_1ere_reelle" : "🏃‍♀️ Réel",
    })

    st.dataframe(df_affichage, width='stretch', hide_index=True)


def afficher_classement_general() -> None:
    """
    Affiche le tableau du classement général de tous les participants.
    """

    st.markdown(
        f"""
        <div style="font-size: 16px; font-weight: bold; font-style:oblique; font-family: system-ui; margin-bottom: 8px; color: #D20606">
        Classement général :
        </div>
        """,
        unsafe_allow_html = True
    )

    df = get_classement_general()

    if df.empty:
        st.info("Le classement est vide pour le moment. Sois le premier à parier !")
        return

    # Sélection et renommage des colonnes pour l'affichage
    df_affichage = df[["rang", "pseudo", "points_total", "nb_paris_scores", "nb_paris", "taux_reussite"]]

    # Formatage du nombre de paris : "3 / 5"
    df_affichage["paris"] = (df_affichage["nb_paris_scores"].astype(str) + " / " + df_affichage["nb_paris"].astype(str))

    df_affichage = df_affichage[["rang", "pseudo", "points_total", "paris", "taux_reussite"]
    ].rename(columns = {
        "rang": "Rang",
        "pseudo": "Pseudo",
        "points_total": "Points",
        "paris": "Paris scorés",
        "taux_reussite": "Réussite (%)"
    })

    st.dataframe(df_affichage, width = 'stretch', hide_index = True,
        column_config = {
            "Réussite (%)": st.column_config.ProgressColumn(
                label = "Réussite (%)",
                min_value = 0,
                max_value = 100,
                format = "%d%%",
            )
        }
    )


# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    """
    Fonction principale de la page classement.

    Orchestre l'affichage dans l'ordre :
        1. Injection des styles CSS.
        2. Titre de la page.
        3. Bloc statistiques personnelles (si connecté).
        4. Historique personnel des points (si connecté et données disponibles).
        5. Classement général de tous les participants.
    """

    st.markdown(
        """
        <div style="font-size: 25px; font-weight: bold; font-family: system-ui; text-align: center">
        Classement
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(1)

    # Bloc personnel : stats + historique (uniquement si connecté)
    if st.session_state.get("authentifie"):

        user_id = st.session_state["user_id"]

        afficher_stats_personnelles(user_id)

        add_vertical_space(1)
        st.divider()
        add_vertical_space(1)

        afficher_historique(user_id)

        add_vertical_space(1)
        st.divider()
        add_vertical_space(1)

    else:
        add_vertical_space(1)
        st.info("Tu auras accès à tes statistiques personnelles et ton historique une fois connecté.")
        add_vertical_space(1)

    # Classement général (visible par tous)
    afficher_classement_general()