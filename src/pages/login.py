"""
PAGE CONNEXION / INSCRIPTION

Cette page permet aux utilisateurs de se connecter ou de créer un compte.
Elle est accessible depuis le menu de navigation et redirige automatiquement vers la page d'accueil après une authentification réussie.

Contenu :
    - Bloc d'introduction avec description de l'application.
    - Deux boutons côte à côte : "Se connecter" et "Créer un compte" qui ouvrent les dialogs correspondants.
    - Bloc informatif sur le fonctionnement de l'application.

Si l'utilisateur est déjà connecté, la page affiche un message de bienvenue avec un bouton de déconnexion.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space

# LOCAL LIBRAIRIES ----------------------
from src.components.authentification import dialog_connexion, dialog_inscription, deconnecter


# COMPOSANTS INTERNES
# ---------------------------------------------------------------------------
def afficher_bandeau_connexion() -> None:
    """
    Affiche un bandeau d'invitation à la connexion si l'utilisateur n'est pas connecté.

    Le bandeau est masqué automatiquement dès que l'utilisateur se connecte.
    """

    if st.session_state.get("authentifie"):
        return

    st.sidebar.info("***Bienvenue !*** &nbsp; Connecte-toi ou crée un compte.")


def afficher_utilisateur_connecte() -> None:
    """
    Affiche le bloc de bienvenue pour un utilisateur déjà connecté. Montre le pseudo, le rôle et un bouton de déconnexion.
    """

    pseudo = st.session_state.get("user_pseudo", "")
    role = st.session_state.get("user_role", "user")

    add_vertical_space(1)
    st.success(f"Bienvenue sur *Trail Betting* **{pseudo}** !", icon = "✅")

    if role == "admin":
        st.info("Tu as les droits administrateur 👑.")

    add_vertical_space(1)

    if st.button("⏻ &nbsp; Se déconnecter", type = "secondary"):
        deconnecter()


def afficher_formulaires_auth() -> None:
    """
    Affiche les boutons d'accès aux dialogs de connexion et d'inscription.
    """

    st.markdown(
        """
        <div style="font-size: 15px; text-align: center">
        Rejoins la communauté <i>Trail Betting</i> pour pronostiquer les podiums des plus grandes courses de trail et défier tes amis au classement.
        </div>
        """,
        unsafe_allow_html = True
    )

    add_vertical_space(3)
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])

    with col2:
        if st.button("Se connecter", type = "primary", width = 'stretch'):
            dialog_connexion()

    with col3:
        if st.button("Créer un compte", width = 'stretch'):
            dialog_inscription()


def afficher_bloc_info() -> None:
    """
    Affiche un bloc explicatif sur le fonctionnement de l'application.

    Présente les règles du jeu : comment parier, comment les points sont calculés et quand les résultats sont publiés.
    """

    with st.expander("Comment ça marche ?", expanded = False):
        st.markdown(
            """
            **🎯 Saisir un pari :**
            Pour chaque course à venir, pronostique le podium hommes et femmes parmi les favoris sélectionnés selon leur index UTMB.

            **⭐ Système de points :**
            | Pronostic | Points |
            |---|---|
            | Coureur à la bonne place | 10 pts |
            | Coureur sur le podium (mais à la mauvaise place) | 4 pts |
            | Podium complet dans le bon ordre (H ou F) | +5 pts bonus |

            **📅 Mise à jour hebdomadaire :**
            Chaque vendredi, de nouvelles courses sont ajoutées et l'avis du Duc de Savoie est publié, pour t'aider à faire tes choix.

            **🏆 Classement :**
            Les points s'accumulent au fil des courses. Le classement est mis à jour automatiquement après chaque publication de résultats.
            """
        )


# MAIN
# ---------------------------------------------------------------------------
def main() -> None:
    """
    Fonction principale de la page connexion / inscription.

    Orchestre l'affichage selon l'état de connexion :
        - Si connecté : bloc de bienvenue + bouton déconnexion.
        - Si déconnecté : boutons connexion/inscription + bloc info.
    """

    st.markdown(
        """
        <div style="font-size: 25px; font-weight: bold; font-family: system-ui; text-align: center">
        Mon compte
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(1)

    if st.session_state.get("authentifie"):
        afficher_utilisateur_connecte()

    else:
        afficher_formulaires_auth()
        add_vertical_space(2)
        afficher_bloc_info()
