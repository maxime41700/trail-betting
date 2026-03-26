"""
MODULE DE FONCTIONS UTILITAIRES GÉNÉRIQUES

Ce fichier regroupe des fonctions utilitaires transversales utilisées dans l'application.
"""

# LIBRAIRIES ----------------------------
import streamlit as st
import importlib
import os
import base64


def load_callable(source_ref):
    """
    Charge dynamiquement une fonction Python à partir d'un chemin ou d'un nom qualifié.

    Si source_ref est un chemin vers un fichier Python, retourne le chemin (str).
    Si c'est un chemin vers une fonction Python, retourne la fonction (callable).
    """

    if os.path.isfile(source_ref):

        return source_ref

    else:
        try:
            module_path, func_name = source_ref.rsplit('.', 1)
            module = importlib.import_module(module_path)
            
            return getattr(module, func_name)

        except Exception as e:
            raise ImportError(f"Impossible de charger la fonction {source_ref}: {e}")

def get_image_base64(image_path):
    """
    Encode une image en base64 pour l'affichage dans Streamlit (HTML/CSS).

    Args:
        image_path (str): Le chemin vers l'image à encoder.

    Returns:
        str: L'image encodée en base64, sous forme de chaîne décodée (UTF-8).
    """

    with open(image_path, "rb") as img_file:

        return base64.b64encode(img_file.read()).decode()

def extraire_bloc_style(section_name: str, path: str) -> str:
    """
    Extrait un bloc de contenu d'un fichier HTML délimité par des balises de commentaire.

    Args:
        section_name (str): Le nom unique du bloc à extraire (doit correspondre au commentaire HTML).
        path (str): Le chemin du fichier HTML contenant le bloc.

    Returns:
        str: Le contenu extrait (chaîne vide si non trouvé).
    """

    start_tag = f"<!-- === START: {section_name} === -->"
    end_tag = f"<!-- === END: {section_name} === -->"

    with open(path, "r", encoding = "utf-8") as f:
        content = f.read()

    start = content.find(start_tag)
    end = content.find(end_tag, start)

    if start == -1 or end == -1:

        return ""

    bloc = content[start + len(start_tag):end].strip()

    return bloc

def render_footer():

    img_b64 = get_image_base64("src/assets/images/footer.svg")
    st.markdown(
        f'<div class="footer-image"><img src="data:image/svg+xml;base64,{img_b64}"></div>',
        unsafe_allow_html = True,
    )