#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module d'utilitaires pour garantir le fonctionnement hors ligne de l'application Dash.
Permet de télécharger et stocker localement toutes les ressources nécessaires.
"""

import os
import sys
import logging
import requests
import shutil
from pathlib import Path
from dash import Dash

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class OfflineResourceManager:
    """
    Gestionnaire de ressources pour le mode hors ligne.
    Télécharge et gère les fichiers nécessaires au fonctionnement hors ligne.
    """

    def __init__(self, assets_folder="assets"):
        """
        Initialise le gestionnaire de ressources.

        Args:
            assets_folder (str): Chemin vers le dossier des ressources
        """
        # Déterminer le chemin absolu du dossier d'assets
        try:
            base_path = sys._MEIPASS  # Pour PyInstaller
        except AttributeError:
            base_path = os.path.abspath(".")

        self.assets_folder = os.path.join(base_path, assets_folder)

        # S'assurer que le dossier existe
        os.makedirs(self.assets_folder, exist_ok=True)

        # Liste des ressources Bootstrap à télécharger
        self.bootstrap_resources = [
            {
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css",
                "filename": "bootstrap.min.css",
                "folder": "css",
            },
            {
                "url": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js",
                "filename": "bootstrap.bundle.min.js",
                "folder": "js",
            },
        ]

        # Liste des ressources Plotly à télécharger
        self.plotly_resources = [
            {
                "url": "https://cdn.plot.ly/plotly-2.20.0.min.js",
                "filename": "plotly.min.js",
                "folder": "js",
            }
        ]

    def download_resource(self, url, dest_path):
        """
        Télécharge une ressource si elle n'existe pas déjà.

        Args:
            url (str): URL de la ressource
            dest_path (str): Chemin de destination

        Returns:
            bool: True si téléchargé avec succès ou déjà présent, False sinon
        """
        if os.path.exists(dest_path):
            logger.info(f"La ressource existe déjà: {dest_path}")
            return True

        try:
            logger.info(f"Téléchargement de {url} vers {dest_path}")
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Téléchargement réussi: {dest_path}")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du téléchargement de {url}: {str(e)}")
            return False

    def ensure_resources(self):
        """
        S'assure que toutes les ressources nécessaires sont disponibles localement.

        Returns:
            bool: True si toutes les ressources sont disponibles, False sinon
        """
        success = True

        # Ressources Bootstrap
        for resource in self.bootstrap_resources:
            folder_path = os.path.join(self.assets_folder, resource["folder"])
            os.makedirs(folder_path, exist_ok=True)

            dest_path = os.path.join(folder_path, resource["filename"])
            if not self.download_resource(resource["url"], dest_path):
                success = False

        # Ressources Plotly
        for resource in self.plotly_resources:
            folder_path = os.path.join(self.assets_folder, resource["folder"])
            os.makedirs(folder_path, exist_ok=True)

            dest_path = os.path.join(folder_path, resource["filename"])
            if not self.download_resource(resource["url"], dest_path):
                success = False

        return success

    def create_custom_css(self):
        """
        Crée un fichier CSS personnalisé pour charger les ressources locales.

        Returns:
            str: Chemin vers le fichier CSS créé
        """
        custom_css_path = os.path.join(self.assets_folder, "custom.css")

        with open(custom_css_path, "w", encoding="utf-8") as f:
            f.write(
                """
/* Styles personnalisés pour l'application */
body {
    font-family: 'Segoe UI', Roboto, sans-serif;
    background-color: #f0f2f5;
}

.card {
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.card-header {
    border-radius: 8px 8px 0 0 !important;
}
"""
            )

        logger.info(f"Fichier CSS personnalisé créé: {custom_css_path}")
        return custom_css_path

    def configure_app_for_offline(self, app):
        """
        Configure une application Dash pour fonctionner hors ligne.

        Args:
            app (Dash): Application Dash à configurer

        Returns:
            Dash: Application configurée
        """
        if not isinstance(app, Dash):
            logger.error("L'objet fourni n'est pas une application Dash")
            return app

        # Configurer pour servir localement
        app.scripts.config.serve_locally = True
        app.css.config.serve_locally = True

        # Injecter les chemins des ressources locales
        def create_js_tags():
            """Créer des balises script pour les ressources JS locales"""
            js_files = []
            for folder, _, files in os.walk(os.path.join(self.assets_folder, "js")):
                for file in files:
                    if file.endswith(".js"):
                        rel_path = os.path.join(
                            os.path.relpath(folder, self.assets_folder), file
                        )
                        js_files.append(f'<script src="/{rel_path}"></script>')
            return "\n".join(js_files)

        # Injecter notre HTML personnalisé
        app.index_string = f"""
<!DOCTYPE html>
<html>
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        <link rel="stylesheet" href="/css/bootstrap.min.css">
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            <script src="/js/bootstrap.bundle.min.js"></script>
            <script src="/js/plotly.min.js"></script>
            {{%renderer%}}
        </footer>
    </body>
</html>
"""

        logger.info("Application Dash configurée pour le mode hors ligne")
        return app


def prepare_offline_app(app=None, assets_folder="assets", ensure_resources=True):
    """
    Prépare une application Dash pour fonctionner en mode hors ligne.

    Args:
        app (Dash, optional): Application Dash existante à configurer
        assets_folder (str): Chemin vers le dossier des ressources
        ensure_resources (bool): Si True, télécharge les ressources manquantes

    Returns:
        tuple: (OfflineResourceManager, Dash app)
    """
    # Initialiser le gestionnaire de ressources
    resource_manager = OfflineResourceManager(assets_folder)

    # Télécharger les ressources si nécessaire
    if ensure_resources:
        resource_manager.ensure_resources()
        resource_manager.create_custom_css()

    # Configurer l'application si fournie
    if app:
        app = resource_manager.configure_app_for_offline(app)

    return resource_manager, app


if __name__ == "__main__":
    # Si exécuté directement, télécharger toutes les ressources
    resource_manager = OfflineResourceManager()
    success = resource_manager.ensure_resources()

    if success:
        logger.info("Toutes les ressources ont été téléchargées avec succès.")
        sys.exit(0)
    else:
        logger.error(
            "Des erreurs se sont produites lors du téléchargement des ressources."
        )
        sys.exit(1)
