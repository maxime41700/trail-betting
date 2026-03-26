"""
COMPOSANT AUTHENTIFICATION

Ce module gère l'inscription et la connexion des utilisateurs.

Fonctionnalités :
    - Connexion : vérification email + mot de passe hashé (bcrypt).
    - Inscription : création d'un compte avec validation des champs, unicité du pseudo et de l'email, hash du mot de passe.
    - Déconnexion : réinitialisation du session_state.

Les fonctions d'affichage utilisent st.dialog pour présenter les
formulaires dans une fenêtre modale.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space
import bcrypt

# LOCAL LIBRAIRIES ----------------------
from src.db.connection import get_supabase_admin_client


# FONCTIONS UTILITAIRES
# ---------------------------------------------------------------------------
def hasher_mot_de_passe(mot_de_passe: str) -> str:
    """
    Hash un mot de passe en clair avec bcrypt (12 rounds).

    Paramètres :
        mot_de_passe (str) : mot de passe en clair saisi par l'utilisateur.

    Retourne :
        str : hash bcrypt du mot de passe, prêt à être stocké en base.
    """

    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), bcrypt.gensalt(rounds = 12)).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    """
    Vérifie qu'un mot de passe en clair correspond au hash stocké en base.

    Paramètres :
        mot_de_passe (str) : mot de passe saisi par l'utilisateur à la connexion.
        hash_stocke  (str) : hash bcrypt récupéré depuis la base de données.

    Retourne :
        bool : True si le mot de passe correspond, False sinon.
    """

    return bcrypt.checkpw(mot_de_passe.encode("utf-8"), hash_stocke.encode("utf-8"))


def connecter_utilisateur(user: dict) -> None:
    """
    Injecte les informations de l'utilisateur dans le session_state.

    Appelé après une connexion ou une inscription réussie pour initialiser la session de l'utilisateur.

    Paramètres :
        user (dict) : dictionnaire contenant les champs de l'utilisateur.
    """

    st.session_state["authentifie"] = True
    st.session_state["user_id"] = user["id"]
    st.session_state["user_pseudo"] = user["pseudo"]
    st.session_state["user_role"] = user["role"]


def email_existe(email: str) -> bool:
    """
    Vérifie si un email est déjà utilisé dans la base de données.

    Paramètres :
        email (str) : adresse email à vérifier.

    Retourne :
        bool : True si l'email existe déjà, False sinon.
    """

    try:
        admin = get_supabase_admin_client()
        response = (
            admin
            .table("utilisateurs")
            .select("id")
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        return response.data is not None

    except Exception:
        return False


def pseudo_existe(pseudo: str) -> bool:
    """
    Vérifie si un pseudo est déjà utilisé dans la base de données.

    Paramètres :
        pseudo (str) : pseudo à vérifier.

    Retourne :
        bool : True si le pseudo existe déjà, False sinon.
    """

    try:
        admin = get_supabase_admin_client()
        response = (
            admin
            .table("utilisateurs")
            .select("id")
            .eq("pseudo", pseudo)
            .maybe_single()
            .execute()
        )
        return response.data is not None

    except Exception:
        return False


# CONNEXION
# ---------------------------------------------------------------------------
def connecter(email: str, mot_de_passe: str) -> bool:
    """
    Tente de connecter un utilisateur avec son email et son mot de passe.

    Récupère l'utilisateur en base via son email, puis vérifie le mot de passe avec bcrypt.
    En cas de succès, injecte les données dans le session_state via _connecter_utilisateur().

    Paramètres :
        email (str) : adresse email saisie par l'utilisateur.
        mot_de_passe (str) : mot de passe en clair saisi par l'utilisateur.

    Retourne :
        bool : True si la connexion a réussi, False sinon.

    Lève :
        Exception : en cas d'erreur de connexion à la base.
    """

    try:
        admin = get_supabase_admin_client()
        response = (
            admin
            .table("utilisateurs")
            .select("*")
            .eq("email", email)
            .maybe_single()
            .execute()
        )

        user = response.data

        # Email introuvable
        if not user:
            return False

        # Vérification du mot de passe
        if not verifier_mot_de_passe(mot_de_passe, user["mdp_hash"]):
            return False

        connecter_utilisateur(user)
        return True

    except Exception as e:
        st.error(f"Erreur lors de la connexion : {e}")
        return False


# INSCRIPTION
# ---------------------------------------------------------------------------
def inscrire(nom: str, prenom: str, email: str, pseudo: str, mot_de_passe: str) -> bool:
    """
    Crée un nouveau compte utilisateur.

    Vérifie l'unicité de l'email et du pseudo, hash le mot de passe, insère l'utilisateur en base et connecte automatiquement.

    Paramètres :
        nom          (str) : nom de famille de l'utilisateur.
        prenom       (str) : prénom de l'utilisateur.
        email        (str) : adresse email (identifiant de connexion).
        pseudo       (str) : pseudo public affiché dans le classement.
        mot_de_passe (str) : mot de passe en clair (sera hashé avant insertion).

    Retourne :
        bool : True si l'inscription a réussi, False sinon.

    Lève :
        Exception : en cas d'erreur d'insertion en base.
    """

    # Vérification unicité email et pseudo
    if email_existe(email):
        st.warning("Cette adresse email est déjà utilisée.")
        return False

    if pseudo_existe(pseudo):
        st.warning("Ce pseudo est déjà pris, choisis-en un autre.")
        return False

    try:
        admin     = get_supabase_admin_client()
        mdp_hash  = hasher_mot_de_passe(mot_de_passe)

        response  = (
            admin
            .table("utilisateurs")
            .insert({
                "nom"     : nom,
                "prenom"  : prenom,
                "email"   : email,
                "pseudo"  : pseudo,
                "mdp_hash": mdp_hash,
                "role"    : "user",
            })
            .execute()
        )

        if not response.data:
            st.error("Erreur lors de la création du compte.")
            return False

        # Connexion automatique après inscription
        connecter_utilisateur(response.data[0])
        return True

    except Exception as e:
        st.error(f"Erreur lors de l'inscription : {e}")
        return False


# DECONNEXION
# ---------------------------------------------------------------------------
def deconnecter() -> None:
    """
    Déconnecte l'utilisateur en réinitialisant le session_state.

    Remet toutes les variables de session à leurs valeurs par défaut
    via initialize_session_state(), puis force un rerun de l'application
    pour actualiser l'affichage.
    """

    # Réinitialisation explicite des clés d'authentification
    st.session_state["authentifie"] = False
    st.session_state["user_id"]     = None
    st.session_state["user_pseudo"] = None
    st.session_state["user_role"]   = None

    st.rerun()


# DIALOGS
# ---------------------------------------------------------------------------
@st.dialog("Connexion", width="small")
def dialog_connexion() -> None:
    """
    Dialog de connexion à l'application.

    Affiche un formulaire email + mot de passe. En cas de succès,
    ferme le dialog et rerun l'application pour actualiser l'état.
    Affiche un lien pour basculer vers le dialog d'inscription.
    """

    st.markdown(
        """
        <div style="font-size: 15px; font-style: oblique; text-align: center">
        Connecte-toi pour saisir tes pronostics !
        </div>
        """,
        unsafe_allow_html = True
    )

    email = st.text_input("Email")
    mot_de_passe = st.text_input("Mot de passe", type="password")

    add_vertical_space(2)
    col1, col2 = st.columns([1, 1])

    if col1.button("Se connecter", use_container_width = True, type = "primary"):
        if not email or not mot_de_passe:
            st.warning("Merci de remplir tous les champs.")
        else:
            ok = connecter(email, mot_de_passe)
            if ok:
                st.rerun()
            else:
                st.error("Email ou mot de passe incorrect.")

    if col2.button("Créer un compte", use_container_width=True):
        # Ferme ce dialog et ouvre le dialog d'inscription
        st.rerun()


@st.dialog("Créer un compte", width="small")
def dialog_inscription() -> None:
    """
    Dialog d'inscription à l'application.

    Affiche un formulaire complet (nom, prénom, email, pseudo, mot de passe
    + confirmation). Valide les champs côté client avant d'appeler inscrire().
    En cas de succès, ferme le dialog et rerun l'application.
    """

    st.markdown(
        """
        <div style="font-size: 15px; font-style: oblique; text-align: center">
        Rejoins la communauté Trail Betting !
        </div>
        """,
        unsafe_allow_html = True
    )
    add_vertical_space(1)

    col1, col2 = st.columns(2)
    with col1:
        prenom = st.text_input("Prénom")
    with col2:
        nom    = st.text_input("Nom")

    email  = st.text_input("Email")
    pseudo = st.text_input(
        "Pseudo",
        help    = "Ton nom affiché dans le classement."
    )

    col3, col4 = st.columns(2)
    with col3:
        mdp         = st.text_input("Mot de passe", type="password")
    with col4:
        mdp_confirm = st.text_input("Confirmer le mot de passe", type="password")

    add_vertical_space(1)
    if st.button("Créer mon compte", type="primary", use_container_width=True):

        # Validations côté client
        if not all([nom, prenom, email, pseudo, mdp, mdp_confirm]):
            st.warning("Merci de remplir tous les champs.")

        elif mdp != mdp_confirm:
            st.error("Les mots de passe ne correspondent pas.")

        elif "@" not in email:
            st.error("L'adresse email n'est pas valide.")

        else:
            ok = inscrire(nom, prenom, email, pseudo, mdp)
            if ok:
                st.success(f"Compte créé ! Bienvenue {pseudo} 🎉")
                st.rerun()