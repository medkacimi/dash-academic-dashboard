#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Application Dash optimisée pour Python 3.11 avec mode 100% offline.
Tableau de bord académique avec les fonctionnalités suivantes:
- Import multiple de fichiers APOGEE avec détection de doublons
- Administration des données (suppression)
- Mode 100% offline avec ressources embarquées
- Tableau de bord étudiant simplifié
"""

import os
import sys
import logging
import pandas as pd
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
import base64
import tempfile
import json
from pathlib import Path
from dashboard_trends import register_trends_callbacks  # nouveau


# Import moderne pour Dash
from dash import (
    Dash,
    html,
    dcc,
    callback,
    Input,
    Output,
    State,
    callback_context,
    no_update,
)
from dash.exceptions import PreventUpdate

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import du gestionnaire de base de données
try:
    from db_manager import ApogeeDBManager

    DB_AVAILABLE = True
except ImportError as e:
    DB_AVAILABLE = False
    logger.error(f"Module db_manager non disponible: {str(e)}")

    # Définir une classe ApogeeDBManager minimale de remplacement
    class ApogeeDBManager:
        def __init__(self, *args, **kwargs):
            pass

        def export_to_dataframe(self, *args, **kwargs):
            return pd.DataFrame()


# Configuration du mode offline
OFFLINE_MODE = True
db_path = "academic_data.db"


def get_resource_path(relative_path):
    """
    Récupère le chemin absolu d'une ressource, fonctionne en mode développement et déployé

    Args:
        relative_path (str): Chemin relatif vers la ressource

    Returns:
        str: Chemin absolu vers la ressource
    """
    try:
        base_path = sys._MEIPASS  # Pour PyInstaller
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# Exemple d'utilisation
def load_database():
    """
    Exemple de chargement d'une base de données
    """
    db_path = get_resource_path("academic_data.db")
    print(f"Chargement de la base de données depuis: {db_path}")
    # Utiliser db_path avec sqlite3, etc.
    return db_path


# =============================================================================
# FONCTION DE CHARGEMENT DES DONNÉES
# =============================================================================


def load_data(db_path=None):
    """
    Charge les données depuis la base SQLite.

    Args:
        db_path (str, optional): Chemin vers la base de données SQLite

    Returns:
        pd.DataFrame: DataFrame contenant les données
        dict: Métadonnées (années, parcours, semestres disponibles)
    """
    if not DB_AVAILABLE:
        logger.error("Erreur : Module db_manager non disponible.")
        return pd.DataFrame(), {}

    if not db_path:
        db_path = "academic_data.db"

    try:
        db_manager = ApogeeDBManager(db_path=db_path)
        # Récupération des données au format compatible
        df = db_manager.export_to_dataframe()

        # Récupération des métadonnées
        metadata = {
            "years": db_manager.get_available_years(),
            "parcours": db_manager.get_available_parcours(),
            "semestres": db_manager.get_available_semestres(),
        }

        logger.info(f"Données chargées avec succès depuis {db_path}.")
        return df, metadata

    except Exception as e:
        logger.error(f"Erreur lors de la connexion à la base de données : {e}")
        return pd.DataFrame(), {}


# =============================================================================
# INITIALISATION DE L'APPLICATION
# =============================================================================

# Chargement initial des données
try:
    df, metadata = load_data(db_path)
except Exception as e:
    logger.error(f"Erreur lors du chargement initial des données: {e}")
    df, metadata = pd.DataFrame(), {}

# =============================================================================
# DÉFINITION DU THÈME DE COULEURS
# =============================================================================

# Palette de couleurs professionnelle pour l'université
colors = {
    "background": "#f0f2f5",  # Fond général légèrement bleuté
    "text": "#2c3e50",  # Bleu foncé pour le texte
    "primary": "#3498db",  # Bleu vif pour les éléments principaux
    "secondary": "#95a5a6",  # Gris pour les éléments secondaires
    "success": "#2ecc71",  # Vert pour les indicateurs positifs
    "warning": "#e74c3c",  # Rouge pour les indicateurs négatifs
    "graph_bg": "#ffffff",  # Fond blanc pour les graphiques
    "panel": "#ffffff",  # Fond blanc pour les panneaux
    "accent": "#9b59b6",  # Violet pour les accents
    "min_max": "#34495e",  # Bleu foncé pour min/max
}

# Configuration des ressources pour mode offline
if OFFLINE_MODE:
    # Mode offline - utiliser uniquement des ressources locales
    external_stylesheets = [dbc.themes.BOOTSTRAP]
    assets_folder = get_resource_path("assets")
    logger.info(
        f"Utilisation des ressources locales pour le mode offline dans {assets_folder}"
    )
else:
    # Mode online avec Font Awesome
    external_stylesheets = [
        dbc.themes.BOOTSTRAP,
        "https://use.fontawesome.com/releases/v5.15.1/css/all.css",
    ]
    assets_folder = "assets"
    logger.info("Utilisation des ressources en ligne (mode connecté).")

# Création de l'application Dash avec le thème Bootstrap
app = Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
    assets_folder=assets_folder,
    serve_locally=True,  # Servir tous les assets localement
)

# Forcer le mode offline
app.scripts.config.serve_locally = True
app.css.config.serve_locally = True

# =============================================================================
# PRÉPARATION DES DONNÉES POUR L'INTERFACE
# =============================================================================

# Création de la liste des étudiants pour le menu déroulant
student_options = []
if not df.empty:
    try:
        # Extraction des étudiants uniques et formatage pour l'affichage
        unique_students = sorted(
            df.drop_duplicates(subset=["Nom", "Prenom"])[["Nom", "Prenom"]]
            .apply(lambda x: f"{x['Prenom']} {x['Nom']}", axis=1)
            .tolist()
        )
        student_options = [
            {"label": student, "value": student} for student in unique_students
        ]
        logger.info(f"{len(student_options)} étudiants chargés pour le menu déroulant.")
    except Exception as e:
        logger.error(f"Erreur lors de la préparation des options d'étudiants: {e}")

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================


def process_file_content(content, filename, db_path):
    """
    Traite le contenu d'un fichier importé et vérifie les conflits.

    Args:
        content (str): Contenu encodé en base64 du fichier
        filename (str): Nom du fichier
        db_path (str): Chemin vers la base de données

    Returns:
        tuple: (message_statut, info_conflit)
    """
    if not filename.endswith(".txt"):
        return (
            html.P(
                f"❌ {filename}: Format incorrect (doit être .txt)",
                className="text-danger",
            ),
            None,
        )

    try:
        # Décoder le contenu
        content_type, content_string = content.split(",")
        decoded = base64.b64decode(content_string)

        # Sauver temporairement
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(decoded)

        # Parser pour vérifier les données
        db_manager = ApogeeDBManager(db_path=db_path)
        parsed_data = db_manager.parse_apogee_file(temp_file_path)

        # Vérifier que des étudiants ont été trouvés
        if not parsed_data["etudiants"]:
            os.unlink(temp_file_path)
            return (
                html.P(
                    f"❌ {filename}: Aucun étudiant trouvé dans le fichier",
                    className="text-danger",
                ),
                None,
            )

        # Vérifier si des données existent déjà
        parcours = parsed_data["parcours"].get("parcours", "Inconnu")
        annee = parsed_data["parcours"].get("annee", "Inconnu")
        semestre = parsed_data["parcours"].get("semestre", "Inconnu")

        # Vérifier si ces données existent déjà
        existing_data = db_manager.get_students(
            year=annee, parcours=parcours, semestre=semestre
        )

        if not existing_data.empty:
            conflict_info = {
                "filename": filename,
                "parcours": parcours,
                "annee": annee,
                "semestre": semestre,
                "content": content,
                "nb_etudiants": len(parsed_data["etudiants"]),
            }

            return (
                html.P(
                    f"⚠️ {filename}: Données déjà existantes pour {parcours}, {annee}, {semestre}",
                    className="text-warning",
                ),
                conflict_info,
            )
        else:
            # Importer directement
            success = db_manager.import_apogee_data(temp_file_path)

            # Supprimer le fichier temporaire après import
            os.unlink(temp_file_path)

            if success > 0:
                return (
                    html.P(
                        f"✅ {filename}: Importé avec succès ({success} étudiants)",
                        className="text-success",
                    ),
                    None,
                )
            else:
                return (
                    html.P(
                        f"❌ {filename}: Erreur lors de l'import (aucun étudiant importé)",
                        className="text-danger",
                    ),
                    None,
                )

    except Exception as e:
        logger.error(f"Erreur lors du traitement du fichier {filename}: {str(e)}")
        return (
            html.P(f"❌ {filename}: Erreur - {str(e)}", className="text-danger"),
            None,
        )


# =============================================================================
# CRÉATION DES LAYOUTS DE PAGE
# =============================================================================

# Layout de la barre de navigation
navbar = dbc.NavbarSimple(
    children=[
        dbc.NavItem(dbc.NavLink("Import de données", href="/", active="exact")),
        dbc.NavItem(dbc.NavLink("Tableau de bord", href="/dashboard", active="exact")),
        dbc.NavItem(dbc.NavLink("Suivi historique", href="/trends", active="exact")),
    ],
    brand="Tableau de Bord Académique",
    brand_href="/",
    color="primary",
    dark=True,
    className="mb-4",
)


# Layout des filtres globaux (Parcours > Année > Semestre)
def create_filters_layout():
    """
    Crée le layout des filtres globaux avec l'ordre: Parcours > Année > Semestre.
    """
    if metadata:
        year_options = [
            {"label": year, "value": year} for year in metadata.get("years", [])
        ]
        parcours_options = [
            {"label": p, "value": p} for p in metadata.get("parcours", [])
        ]
        semestre_options = [
            {"label": s, "value": s} for s in metadata.get("semestres", [])
        ]

        return dbc.Card(
            [
                dbc.CardHeader(
                    html.H5("Filtres", className="text-white mb-0"),
                    className="bg-primary",
                ),
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Label(
                                            "Parcours:",
                                            className="font-weight-bold mb-2",
                                        ),
                                        dcc.Dropdown(
                                            id="parcours-dropdown",
                                            options=parcours_options,
                                            value=None,
                                            clearable=True,
                                            className="mb-3",
                                        ),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        html.Label(
                                            "Année académique:",
                                            className="font-weight-bold mb-2",
                                        ),
                                        dcc.Dropdown(
                                            id="year-dropdown",
                                            options=year_options,
                                            value=None,
                                            clearable=True,
                                            className="mb-3",
                                        ),
                                    ],
                                    md=4,
                                ),
                                dbc.Col(
                                    [
                                        html.Label(
                                            "Semestre:",
                                            className="font-weight-bold mb-2",
                                        ),
                                        dcc.Dropdown(
                                            id="semestre-dropdown",
                                            options=semestre_options,
                                            value=None,
                                            clearable=True,
                                            className="mb-3",
                                        ),
                                    ],
                                    md=4,
                                ),
                            ]
                        )
                    ],
                    className="px-4",
                ),
            ],
            className="shadow-sm mb-4",
        )
    else:
        return html.Div()


# Layout du tableau de bord étudiant
def build_dashboard_layout() -> dbc.Container:
    """
    Construit le layout du tableau de bord à partir des données
    et métadonnées *actuelles* (df, metadata).
    """
    global df, metadata

    # ⇢ Recalcul des options étudiants
    student_options = []
    if not df.empty:
        unique = (
            df.drop_duplicates(subset=["Nom", "Prenom"])[["Nom", "Prenom"]]
            .apply(lambda x: f"{x['Prenom']} {x['Nom']}", axis=1)
            .sort_values()
            .tolist()
        )
        student_options = [{"label": s, "value": s} for s in unique]

    return dbc.Container(
        [
            create_filters_layout(),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            "Sélection de l'étudiant",
                                            className="text-white mb-0",
                                        ),
                                        className="bg-primary",
                                    ),
                                    dbc.CardBody(
                                        [
                                            html.Label(
                                                "Étudiant :",
                                                className="font-weight-bold mb-2",
                                            ),
                                            dcc.Dropdown(
                                                id="student-dropdown",
                                                options=student_options,
                                                value=(
                                                    student_options[0]["value"]
                                                    if student_options
                                                    else None
                                                ),
                                                clearable=False,
                                                className="mb-4",
                                            ),
                                            html.Label(
                                                "Unité d'Enseignement :",
                                                className="font-weight-bold mb-2",
                                            ),
                                            dcc.Dropdown(
                                                id="ue-dropdown",
                                                options=[],
                                                multi=False,
                                                clearable=True,
                                                className="mb-3",
                                            ),
                                            dcc.Store(id="student-data-store"),
                                        ],
                                        className="px-4",
                                    ),
                                ],
                                className="shadow-sm h-100",
                            )
                        ],
                        md=12,
                        lg=4,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            "Statistiques globales",
                                            className="text-white mb-0",
                                        ),
                                        className="bg-primary",
                                    ),
                                    dbc.CardBody(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        [
                                                            html.Div(
                                                                id="moyenne-generale",
                                                                className="text-center p-3 border rounded shadow-sm",
                                                            )
                                                        ],
                                                        width=6,
                                                    ),
                                                    dbc.Col(
                                                        [
                                                            html.Div(
                                                                id="nombre-matieres",
                                                                className="text-center p-3 border rounded shadow-sm",
                                                            )
                                                        ],
                                                        width=6,
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="px-4",
                                    ),
                                ],
                                className="shadow-sm h-100",
                            )
                        ],
                        md=12,
                        lg=8,
                    ),
                ],
                className="mb-4",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            "Performance par matière",
                                            className="text-white mb-0",
                                        ),
                                        className="bg-primary",
                                    ),
                                    dbc.CardBody(
                                        [dcc.Graph(id="grades-graph")], className="px-4"
                                    ),
                                ],
                                className="shadow-sm h-100",
                            )
                        ],
                        md=12,
                        lg=8,
                    ),
                    dbc.Col(
                        [
                            dbc.Card(
                                [
                                    dbc.CardHeader(
                                        html.H5(
                                            "Répartition par UE",
                                            className="text-white mb-0",
                                        ),
                                        className="bg-primary",
                                    ),
                                    dbc.CardBody(
                                        [dcc.Graph(id="average-grade-pie-chart")],
                                        className="px-4",
                                    ),
                                ],
                                className="shadow-sm h-100",
                            )
                        ],
                        md=12,
                        lg=4,
                    ),
                ]
            ),
        ],
        fluid=True,
        style={
            "backgroundColor": colors["background"],
            "minHeight": "100vh",
            "padding": "2rem",
            "fontFamily": "Segoe UI, Roboto, sans-serif",
        },
    )


# Layout de la page d'import
import_page_layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.H3(
                                        "Importation de fichiers APOGEE",
                                        className="text-white mb-0",
                                    ),
                                    className="bg-primary",
                                ),
                                dbc.CardBody(
                                    [
                                        html.P(
                                            "Importez des fichiers APOGEE pour commencer à utiliser le tableau de bord.",
                                            className="mb-4",
                                        ),
                                        # Section d'upload multiple
                                        html.Div(
                                            [
                                                html.H4(
                                                    "1. Importer des fichiers",
                                                    className="mb-3",
                                                ),
                                                dcc.Upload(
                                                    id="upload-multiple-apogee",
                                                    children=html.Div(
                                                        [
                                                            html.Span(
                                                                "⬆",
                                                                style={
                                                                    "fontSize": "3em",
                                                                    "color": colors[
                                                                        "primary"
                                                                    ],
                                                                },
                                                            ),
                                                            html.H5(
                                                                "Glisser-déposer des fichiers APOGEE ou cliquer pour sélectionner",
                                                                className="mb-2",
                                                            ),
                                                            html.P(
                                                                "Plusieurs fichiers peuvent être sélectionnés simultanément.",
                                                                className="text-muted",
                                                            ),
                                                        ],
                                                        style={
                                                            "height": "100px",
                                                            "lineHeight": "100px",
                                                            "textAlign": "center",
                                                        },
                                                    ),
                                                    style={
                                                        "width": "100%",
                                                        "borderWidth": "2px",
                                                        "borderStyle": "dashed",
                                                        "borderRadius": "10px",
                                                        "padding": "40px",
                                                        "textAlign": "center",
                                                        "marginBottom": "20px",
                                                        "backgroundColor": "#f8f9fa",
                                                    },
                                                    multiple=True,
                                                ),
                                                html.Div(id="upload-multiple-status"),
                                            ],
                                            className="mb-5",
                                        ),
                                        # Section de gestion des données
                                        html.Div(
                                            [
                                                html.H4(
                                                    "2. Gérer les données existantes",
                                                    className="mb-3",
                                                ),
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            [
                                                                html.Label(
                                                                    "Parcours:",
                                                                    className="font-weight-bold",
                                                                ),
                                                                dcc.Dropdown(
                                                                    id="admin-parcours-dropdown",
                                                                    options=[],
                                                                    className="mb-3",
                                                                ),
                                                            ],
                                                            md=4,
                                                        ),
                                                        dbc.Col(
                                                            [
                                                                html.Label(
                                                                    "Année:",
                                                                    className="font-weight-bold",
                                                                ),
                                                                dcc.Dropdown(
                                                                    id="admin-year-dropdown",
                                                                    options=[],
                                                                    className="mb-3",
                                                                ),
                                                            ],
                                                            md=4,
                                                        ),
                                                        dbc.Col(
                                                            [
                                                                html.Label(
                                                                    "Semestre:",
                                                                    className="font-weight-bold",
                                                                ),
                                                                dcc.Dropdown(
                                                                    id="admin-semestre-dropdown",
                                                                    options=[],
                                                                    className="mb-3",
                                                                ),
                                                            ],
                                                            md=4,
                                                        ),
                                                    ]
                                                ),
                                                dbc.Row(
                                                    [
                                                        dbc.Col(
                                                            [
                                                                dbc.Button(
                                                                    "Supprimer le semestre sélectionné",
                                                                    id="delete-semester-btn",
                                                                    color="danger",
                                                                    className="mb-3",
                                                                    disabled=True,
                                                                ),
                                                            ]
                                                        )
                                                    ]
                                                ),
                                                html.Div(id="admin-status"),
                                            ],
                                            className="border-top pt-4",
                                        ),
                                        # Bouton pour accéder au tableau de bord
                                        html.Div(
                                            [
                                                dbc.Button(
                                                    "Accéder au tableau de bord",
                                                    id="access-dashboard-btn",
                                                    color="primary",
                                                    size="lg",
                                                    className="mt-5",
                                                    disabled=True,
                                                    href="/dashboard",
                                                )
                                            ],
                                            className="text-center",
                                        ),
                                    ]
                                ),
                            ],
                            className="shadow-lg",
                        )
                    ]
                )
            ],
            justify="center",
            className="mt-5",
        )
    ],
    style={
        "backgroundColor": colors["background"],
        "minHeight": "100vh",
        "padding": "2rem",
        "fontFamily": "Segoe UI, Roboto, sans-serif",
    },
)

# Modal pour les conflits de doublons
conflict_modal = dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("Conflit de données détecté")),
        dbc.ModalBody(
            [
                html.Div(id="conflict-message"),
                html.Hr(),
                html.P("Que souhaitez-vous faire avec ces données existantes ?"),
                html.Div(id="conflict-details", className="alert alert-info"),
            ]
        ),
        dbc.ModalFooter(
            [
                dbc.Button(
                    "Remplacer les données",
                    id="confirm-replace",
                    className="ms-auto",
                    color="warning",
                ),
                dbc.Button(
                    "Annuler l'import",
                    id="cancel-import",
                    className="ms-auto",
                    color="secondary",
                ),
            ]
        ),
    ],
    id="conflict-modal",
    size="lg",
)
# Définition du footer
footer = html.Footer(
    dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.P(
                            [
                                "© 2025 Mohamed KACIMI - ",
                                html.A(
                                    "À propos", href="/about", className="text-light"
                                ),
                            ],
                            className="text-center text-light my-3",
                        ),
                        className="col-12",
                    )
                ]
            )
        ],
        fluid=True,
    ),
    className="bg-primary mt-5",
)
# Layout de la page "À propos"
about_layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader(
                                    html.H3(
                                        "À propos de l'application",
                                        className="text-white mb-0",
                                    ),
                                    className="bg-primary",
                                ),
                                dbc.CardBody(
                                    [
                                        html.H4(
                                            "Tableau de Bord Académique",
                                            className="mb-3",
                                        ),
                                        html.P(
                                            """
                                            Cette application permet de visualiser et gérer les résultats
                                            académiques des étudiants à partir des données APOGEE.
                                            """
                                        ),
                                        html.Hr(),
                                        html.H5("Fonctionnalités"),
                                        html.Ul(
                                            [
                                                html.Li("Import de données APOGEE"),
                                                html.Li(
                                                    "Visualisation des résultats par étudiant"
                                                ),
                                                html.Li(
                                                    "Analyse par UE et par matière"
                                                ),
                                                html.Li(
                                                    "Gestion administrative des données"
                                                ),
                                            ]
                                        ),
                                        html.Hr(),
                                        html.H5("Crédits"),
                                        html.P(
                                            [
                                                "Développé par ",
                                                html.Strong("Mohamed KACIMI"),
                                                " © 2025",
                                            ]
                                        ),
                                        html.P(
                                            [
                                                "Version: 1.0.0",
                                                html.Br(),
                                                "Contact: ",
                                                html.A(
                                                    "mohamed.kacimi@example.com",
                                                    href="mailto:mohamed.kacimi@example.com",
                                                ),
                                            ],
                                            className="text-muted",
                                        ),
                                        html.Div(
                                            [
                                                dbc.Button(
                                                    "Retour au tableau de bord",
                                                    color="primary",
                                                    href="/dashboard",
                                                    className="mt-3",
                                                )
                                            ],
                                            className="text-center mt-4",
                                        ),
                                    ]
                                ),
                            ],
                            className="shadow-sm",
                        )
                    ],
                    md=10,
                    lg=8,
                    className="mx-auto",
                )
            ],
            className="py-5",
        )
    ],
    fluid=True,
    style={
        "backgroundColor": colors["background"],
        "minHeight": "100vh",
        "padding": "2rem",
        "fontFamily": "Segoe UI, Roboto, sans-serif",
    },
)
# Mise à jour du layout principal pour inclure le footer
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        navbar,
        html.Div(id="page-content"),
        # Stockage de l'état des filtres globaux
        dcc.Store(id="filters-store"),
        # Stockage des fichiers en attente de traitement
        dcc.Store(id="pending-files"),
        # Modal de conflit
        conflict_modal,
        # Footer
        footer,
    ]
)

# =============================================================================
# CALLBACKS (INTERACTIVITÉ)
# =============================================================================


# Routage entre les vues
@callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    global df, metadata

    if pathname == "/dashboard":
        # Toujours recharger les données avant d'afficher la page
        df, metadata = load_data(db_path)

        if df.empty:
            return import_page_layout  # base encore vide
        return build_dashboard_layout()  # ← nouveau
    elif pathname == "/about":
        return about_layout
    elif pathname == "/trends":
        return dashboard_trends.app.layout  # ou build_dashboard_trends()

    # Page d'accueil (import)
    return import_page_layout


# Callback pour activer le bouton d'accès au dashboard
@callback(
    Output("access-dashboard-btn", "disabled"),
    Input("url", "pathname"),  # Déclencher lors du chargement de la page
)
def enable_dashboard_access(pathname):
    """
    Active le bouton d'accès au tableau de bord si des données sont disponibles.
    """
    global df
    # Recharger les données à chaque appel pour s'assurer que le bouton est correctement activé/désactivé
    try:
        df, _ = load_data(db_path)
    except Exception as e:
        logger.error(f"Erreur lors du rechargement des données: {e}")

    return df.empty


# Callback pour gérer l'import multiple de fichiers
@callback(
    [
        Output("upload-multiple-status", "children"),
        Output("pending-files", "data"),
        Output("conflict-modal", "is_open", allow_duplicate=True),
        Output("conflict-message", "children"),
        Output("conflict-details", "children"),
        Output("access-dashboard-btn", "disabled", allow_duplicate=True),
    ],
    [Input("upload-multiple-apogee", "contents")],
    [State("upload-multiple-apogee", "filename")],
    prevent_initial_call=True,
)
def handle_multiple_file_upload(contents_list, filenames_list):
    """
    Gère l'import de plusieurs fichiers APOGEE simultanément avec détection de doublons.
    """
    if contents_list is None:
        return "", None, False, "", "", True

    if not isinstance(contents_list, list):
        contents_list = [contents_list]
        filenames_list = [filenames_list]

    logger.info(f"Traitement de {len(contents_list)} fichiers importés.")

    status_messages = []
    conflicts = []

    for content, filename in zip(contents_list, filenames_list):
        message, conflict_info = process_file_content(content, filename, db_path)
        status_messages.append(message)

        if conflict_info:
            conflicts.append(conflict_info)

    # Gérer les conflits
    if conflicts:
        conflict_message = html.Div(
            [
                html.H5(
                    "Les données suivantes existent déjà dans la base :",
                    className="mb-3 text-danger",
                ),
            ]
        )

        conflict_details = []
        for conflict in conflicts:
            conflict_details.append(
                html.Div(
                    [
                        html.Strong(f"Fichier: {conflict['filename']}"),
                        html.Br(),
                        html.Span(f"Parcours: {conflict['parcours']}"),
                        html.Br(),
                        html.Span(f"Année: {conflict['annee']}"),
                        html.Br(),
                        html.Span(f"Semestre: {conflict['semestre']}"),
                        html.Br(),
                        html.Span(f"Nombre d'étudiants: {conflict['nb_etudiants']}"),
                        html.Hr() if conflict != conflicts[-1] else None,
                    ]
                )
            )

        logger.warning(f"Conflits détectés dans {len(conflicts)} fichiers.")

        return (
            status_messages,
            conflicts,
            True,
            conflict_message,
            conflict_details,
            True,
        )
    else:
        # Recharger les données si au moins un import réussi
        global df, metadata, student_options

        df, metadata = load_data(db_path)

        # Mettre à jour les options d'étudiants
        if not df.empty:
            try:
                unique_students = sorted(
                    df.drop_duplicates(subset=["Nom", "Prenom"])[["Nom", "Prenom"]]
                    .apply(lambda x: f"{x['Prenom']} {x['Nom']}", axis=1)
                    .tolist()
                )
                student_options = [
                    {"label": student, "value": student} for student in unique_students
                ]
            except Exception as e:
                logger.error(
                    f"Erreur lors de la mise à jour des options d'étudiants: {e}"
                )

        logger.info("Données rechargées après import réussi.")

        return status_messages, None, False, "", "", df.empty


# Callback pour résoudre les conflits de doublons
@callback(
    [
        Output("upload-multiple-status", "children", allow_duplicate=True),
        Output("conflict-modal", "is_open", allow_duplicate=True),
        Output("access-dashboard-btn", "disabled", allow_duplicate=True),
    ],
    [Input("confirm-replace", "n_clicks"), Input("cancel-import", "n_clicks")],
    [State("pending-files", "data")],
    prevent_initial_call=True,
)
def resolve_conflicts(confirm_clicks, cancel_clicks, conflicts):
    """
    Résout les conflits de doublons selon le choix de l'utilisateur.
    """
    ctx = callback_context

    if not ctx.triggered:
        raise PreventUpdate

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "cancel-import":
        logger.info("Import annulé par l'utilisateur.")
        return "", False, True

    elif button_id == "confirm-replace" and conflicts:
        logger.info(f"Remplacement de données confirmé pour {len(conflicts)} fichiers.")

        status_messages = []
        db_manager = ApogeeDBManager(db_path=db_path)

        for conflict in conflicts:
            try:
                # Supprimer les anciennes données
                delete_criteria = {
                    "annee": conflict["annee"],
                    "parcours": conflict["parcours"],
                    "semestre": conflict["semestre"],
                }

                db_manager.delete_data(delete_criteria)

                # Importer les nouvelles données
                content_type, content_string = conflict["content"].split(",")
                decoded = base64.b64decode(content_string)

                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".txt"
                ) as temp_file:
                    temp_file_path = temp_file.name
                    temp_file.write(decoded)

                nb_etudiants = db_manager.import_apogee_data(temp_file_path)

                os.unlink(temp_file_path)

                if nb_etudiants > 0:
                    status_messages.append(
                        html.P(
                            f"✅ {conflict['filename']}: Données remplacées ({nb_etudiants} étudiants)",
                            className="text-success",
                        )
                    )
                else:
                    status_messages.append(
                        html.P(
                            f"⚠️ {conflict['filename']}: Données remplacées mais aucun étudiant importé",
                            className="text-warning",
                        )
                    )

            except Exception as e:
                logger.error(f"Erreur lors du remplacement des données: {str(e)}")
                status_messages.append(
                    html.P(
                        f"❌ {conflict['filename']}: Erreur - {str(e)}",
                        className="text-danger",
                    )
                )

        # Recharger les données
        global df, metadata, student_options

        df, metadata = load_data(db_path)

        # Mettre à jour les options d'étudiants
        if not df.empty:
            try:
                unique_students = sorted(
                    df.drop_duplicates(subset=["Nom", "Prenom"])[["Nom", "Prenom"]]
                    .apply(lambda x: f"{x['Prenom']} {x['Nom']}", axis=1)
                    .tolist()
                )
                student_options = [
                    {"label": student, "value": student} for student in unique_students
                ]
            except Exception as e:
                logger.error(
                    f"Erreur lors de la mise à jour des options d'étudiants: {e}"
                )

        logger.info("Données rechargées après remplacement.")

        return status_messages, False, df.empty


# Callback pour mettre à jour les dropdowns d'administration
@callback(
    [
        Output("admin-parcours-dropdown", "options"),
        Output("admin-parcours-dropdown", "value"),
        Output("admin-year-dropdown", "options"),
        Output("admin-year-dropdown", "value"),
        Output("admin-semestre-dropdown", "options"),
        Output("admin-semestre-dropdown", "value"),
        Output("delete-semester-btn", "disabled"),
    ],
    [
        Input("url", "pathname"),  # Déclencher à chaque changement de page
        Input("admin-parcours-dropdown", "value"),
        Input("admin-year-dropdown", "value"),
    ],
)
def update_admin_dropdowns(pathname, selected_parcours, selected_year):
    """
    Met à jour les dropdowns d'administration selon les choix de l'utilisateur.
    """
    ctx = callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    if not DB_AVAILABLE:
        return [], None, [], None, [], None, True

    db_manager = ApogeeDBManager(db_path=db_path)

    # Options de parcours
    parcours_list = db_manager.get_available_parcours()
    parcours_options = [{"label": p, "value": p} for p in parcours_list]

    # Si déclenchement initial ou changement de page, réinitialiser les valeurs
    if trigger_id == "url" or trigger_id is None:
        return parcours_options, None, [], None, [], None, True

    # Options d'année (dépend du parcours)
    if selected_parcours:
        year_list = db_manager.get_available_years()
        year_options = [{"label": y, "value": y} for y in year_list]
    else:
        year_options = []

    # Si le parcours change, réinitialiser l'année et le semestre
    if trigger_id == "admin-parcours-dropdown":
        return parcours_options, selected_parcours, year_options, None, [], None, True

    # Options de semestre (dépend du parcours et de l'année)
    if selected_parcours and selected_year:
        semestre_list = db_manager.get_available_semestres(
            year=selected_year, parcours=selected_parcours
        )
        semestre_options = [{"label": s, "value": s} for s in semestre_list]

        # Si l'année change, réinitialiser le semestre
        if trigger_id == "admin-year-dropdown":
            return (
                parcours_options,
                selected_parcours,
                year_options,
                selected_year,
                semestre_options,
                None,
                True,
            )
    else:
        semestre_options = []

    # Conserver les valeurs actuelles pour les autres cas
    return (
        parcours_options,
        selected_parcours,
        year_options,
        selected_year,
        semestre_options,
        no_update,  # Garder la valeur actuelle du semestre
        True,  # Le bouton reste désactivé jusqu'à la sélection d'un semestre
    )


# Callback pour activer/désactiver le bouton de suppression
@callback(
    Output("delete-semester-btn", "disabled", allow_duplicate=True),
    [Input("admin-semestre-dropdown", "value")],
    [
        State("admin-parcours-dropdown", "value"),
        State("admin-year-dropdown", "value"),
    ],
    prevent_initial_call=True,
)
def toggle_delete_button(selected_semestre, selected_parcours, selected_year):
    """
    Active ou désactive le bouton de suppression en fonction des sélections.
    """
    return not (selected_parcours and selected_year and selected_semestre)


# Callback pour supprimer un semestre
@callback(
    [
        Output("admin-status", "children"),
        Output(
            "admin-parcours-dropdown", "value", allow_duplicate=True
        ),  # Réinitialiser les sélections
        Output("admin-year-dropdown", "value", allow_duplicate=True),
        Output("admin-semestre-dropdown", "value", allow_duplicate=True),
    ],
    Input("delete-semester-btn", "n_clicks"),
    [
        State("admin-parcours-dropdown", "value"),
        State("admin-year-dropdown", "value"),
        State("admin-semestre-dropdown", "value"),
    ],
    prevent_initial_call=True,
)
def delete_semester(n_clicks, parcours, year, semestre):
    """
    Supprime les données d'un semestre sélectionné.
    """
    if n_clicks is None or not all([parcours, year, semestre]):
        return "", no_update, no_update, no_update

    try:
        logger.info(
            f"Tentative de suppression du semestre: {parcours} - {year} - {semestre}"
        )

        db_manager = ApogeeDBManager(db_path=db_path)

        criteria = {"annee": year, "parcours": parcours, "semestre": semestre}
        deleted_count = db_manager.delete_data(criteria)

        # Recharger les données
        global df, metadata, student_options

        df, metadata = load_data(db_path)

        # Mettre à jour les options d'étudiants
        if not df.empty:
            try:
                unique_students = sorted(
                    df.drop_duplicates(subset=["Nom", "Prenom"])[["Nom", "Prenom"]]
                    .apply(lambda x: f"{x['Prenom']} {x['Nom']}", axis=1)
                    .tolist()
                )
                student_options = [
                    {"label": student, "value": student} for student in unique_students
                ]
            except Exception as e:
                logger.error(
                    f"Erreur lors de la mise à jour des options d'étudiants: {e}"
                )

        if deleted_count > 0:
            logger.info(
                f"Semestre supprimé avec succès: {deleted_count} enregistrements"
            )

            # Réinitialiser les sélections après suppression
            return (
                dbc.Alert(
                    f"Semestre supprimé avec succès ({deleted_count} enregistrements)",
                    color="success",
                    dismissable=True,
                ),
                None,
                None,
                None,
            )
        else:
            logger.warning("Aucune donnée trouvée pour le semestre spécifié")

            return (
                dbc.Alert(
                    "Aucune donnée trouvée pour ce semestre",
                    color="info",
                    dismissable=True,
                ),
                no_update,
                no_update,
                no_update,
            )

    except Exception as e:
        logger.error(f"Erreur lors de la suppression du semestre: {str(e)}")

        return (
            dbc.Alert(
                f"Erreur: {str(e)}",
                color="danger",
                dismissable=True,
            ),
            no_update,
            no_update,
            no_update,
        )


# Callback pour stocker les filtres globaux
@callback(
    Output("filters-store", "data"),
    [
        Input("year-dropdown", "value"),
        Input("parcours-dropdown", "value"),
        Input("semestre-dropdown", "value"),
    ],
)
def store_filters(year, parcours, semestre):
    """
    Stocke les valeurs des filtres globaux.
    """
    return {"year": year, "parcours": parcours, "semestre": semestre}


# Callback pour préparer les données de l'étudiant sélectionné
@callback(
    Output("student-data-store", "data"),
    [Input("student-dropdown", "value"), Input("filters-store", "data")],
)
def prepare_student_data(selected_student, filters):
    """
    Prépare les données pour l'étudiant sélectionné.
    Cette fonction est appelée chaque fois qu'un nouvel étudiant est sélectionné.
    """
    if not selected_student or not isinstance(selected_student, str) or df.empty:
        return None

    try:
        # Séparation du prénom et du nom
        parts = selected_student.split(" ", 1)
        if len(parts) != 2:
            logger.warning(f"Format de nom d'étudiant incorrect: {selected_student}")
            return None

        prenom, nom = parts

        # Récupération des données via le gestionnaire de BDD
        db_manager = ApogeeDBManager(db_path=db_path)

        # Récupération des données filtrées
        year = filters.get("year") if filters else None
        parcours = filters.get("parcours") if filters else None
        semestre = filters.get("semestre") if filters else None

        student_df = db_manager.get_student_data(
            nom, prenom, year=year, parcours=parcours, semestre=semestre
        )

        if student_df.empty:
            logger.warning(f"Aucune donnée trouvée pour l'étudiant: {selected_student}")
            return None

        # Transformation au format attendu par l'UI
        student_data = student_df.to_dict("records")
        ues = sorted(list(set(item["ue"] for item in student_data)))

        # Préparation du dictionnaire de données commun
        return {
            "student_records": student_data,  # Notes et matières
            "available_ues": ues,  # Liste des UEs disponibles
            "student_name": selected_student,  # Nom pour l'affichage
        }

    except Exception as e:
        logger.error(f"Erreur lors de la préparation des données: {str(e)}")
        import traceback

        logger.error(f"Détails: {traceback.format_exc()}")
        return None


# Callback pour la mise à jour du menu déroulant des UEs
@callback(
    [Output("ue-dropdown", "options"), Output("ue-dropdown", "value")],
    Input("student-data-store", "data"),
)
def update_ue_dropdown(student_data):
    """
    Met à jour les options du menu déroulant des UEs en fonction de l'étudiant sélectionné.
    """
    if not student_data:
        return [], None

    # Création des options pour le dropdown des UEs
    ue_options = [
        {"label": ue, "value": ue} for ue in sorted(student_data["available_ues"])
    ]

    return ue_options, None  # Réinitialisation de la sélection


# Callback pour la mise à jour du graphique des notes
# Mise à jour de la fonction update_grades_graph
@callback(
    Output("grades-graph", "figure"),
    [Input("student-data-store", "data"), Input("ue-dropdown", "value")],
)
def update_grades_graph(student_data, selected_ue):
    """
    Génère le graphique des notes de l'étudiant avec amélioration de l'affichage.
    """
    if not student_data:
        return go.Figure().update_layout(
            title="Aucun étudiant sélectionné.",
            plot_bgcolor="rgba(255,255,255,0.9)",
            paper_bgcolor="rgba(255,255,255,0)",
            height=450,
        )

    # Préparation des données
    student_df = pd.DataFrame(student_data["student_records"])

    # Adaptation aux données SQLite
    if "est_ue" in student_df.columns:
        # Filtrage des cours (pas des UEs)
        student_df = student_df[student_df["est_ue"] == 0]

        # Renommage des colonnes pour compatibilité
        student_df = student_df.rename(
            columns={"cours": "Matière", "note": "Note", "ue": "UE"}
        )

    if selected_ue:
        student_df = student_df[student_df["UE"] == selected_ue]

    if student_df.empty:
        return go.Figure().update_layout(
            title="Aucune note disponible.",
            plot_bgcolor="rgba(255,255,255,0.9)",
            paper_bgcolor="rgba(255,255,255,0)",
            height=450,
        )

    # Création du graphique
    fig = go.Figure()

    # Création d'un tableau de couleurs pour chaque note selon les critères
    colors_per_grade = []
    for note in student_df["Note"]:
        if note < 10:
            colors_per_grade.append("red")  # Rouge pour notes < 10
        elif note == 10:
            colors_per_grade.append("orange")  # Orange pour notes = 10
        else:
            colors_per_grade.append("green")  # Vert pour notes > 10

    # Calcul de la longueur maximale des noms de matières pour adapter le graphique
    max_label_length = max([len(str(matiere)) for matiere in student_df["Matière"]])
    bottom_margin = min(40 + max_label_length * 5, 200)  # Marge dynamique

    # Barres des notes de l'étudiant avec couleurs conditionnelles
    fig.add_trace(
        go.Bar(
            x=student_df["Matière"],
            y=student_df["Note"],
            name="Note de l'étudiant",
            marker_color=colors_per_grade,
            hovertemplate="Note: %{y:.2f}/20<extra></extra>",
        )
    )

    # Personnalisation avancée
    fig.update_layout(
        title=dict(
            text=f"Performance détaillée de {student_data['student_name']}",
            font=dict(size=20, family="Segoe UI, Roboto", color=colors["text"]),
            x=0.5,
            y=0.95,
        ),
        xaxis=dict(title="", tickangle=-45, gridcolor="rgba(0,0,0,0.1)", showgrid=True),
        yaxis=dict(
            title="Note /20", range=[0, 20], gridcolor="rgba(0,0,0,0.1)", showgrid=True
        ),
        plot_bgcolor="rgba(255,255,255,0.9)",
        paper_bgcolor="rgba(255,255,255,0)",
        height=max(450, 300 + len(student_df) * 15),  # Hauteur adaptative
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1,
        ),
        margin=dict(l=40, r=40, t=80, b=bottom_margin),  # Marge inférieure adaptative
        hovermode="closest",
    )

    # Ligne de la moyenne avec annotation
    fig.add_shape(
        type="line",
        x0=-0.5,
        y0=10,
        x1=len(student_df["Matière"].unique()) - 0.5,
        y1=10,
        line=dict(color=colors["secondary"], width=1.5, dash="dot"),
    )

    # Ajout d'une annotation pour la ligne de moyenne
    fig.add_annotation(
        x=len(student_df["Matière"].unique()) - 0.5,
        y=10,
        xref="x",
        yref="y",
        text="Moyenne requise",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=1,
        ax=50,
        ay=-20,
        font=dict(size=10, color=colors["secondary"]),
    )

    return fig


# Callback pour la mise à jour du graphique UE
@callback(
    Output("average-grade-pie-chart", "figure"), Input("student-data-store", "data")
)
def update_average_grade_chart(student_data):
    """
    Génère un diagramme à barres verticales montrant la moyenne par UE.
    """
    if not student_data:
        return go.Figure().update_layout(
            title="Aucun étudiant sélectionné.",
            plot_bgcolor="rgba(255,255,255,0.9)",
            paper_bgcolor="rgba(255,255,255,0)",
            height=450,
        )

    # Préparation des données
    filtered_df = pd.DataFrame(student_data["student_records"])

    # Adaptation aux données SQLite
    if "est_ue" in filtered_df.columns:
        # Filtrage des UEs uniquement
        filtered_df = filtered_df[filtered_df["est_ue"] == 1]

        # Renommage des colonnes pour compatibilité
        filtered_df = filtered_df.rename(
            columns={"ue": "UE", "note": "Note", "cours": "Matière"}
        )

    if filtered_df.empty:
        return go.Figure().update_layout(
            title="Aucune donnée disponible.",
            plot_bgcolor="rgba(255,255,255,0.9)",
            paper_bgcolor="rgba(255,255,255,0)",
            height=450,
        )

    # Les notes UE sont déjà dans le dataframe
    average_grades = filtered_df[["UE", "Note"]].copy()

    # Trier par UE pour une meilleure lisibilité
    average_grades = average_grades.sort_values("UE")

    # Générer les couleurs pour les barres en fonction des moyennes
    bar_colors = []
    for note in average_grades["Note"]:
        if note < 10:
            bar_colors.append(colors["warning"])  # Rouge pour notes < 10
        elif note == 10:
            bar_colors.append("orange")  # Orange pour notes = 10
        else:
            bar_colors.append(colors["success"])  # Vert pour notes > 10

    # Création du diagramme à barres verticales
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=average_grades["UE"],
            y=average_grades["Note"],
            text=average_grades["Note"].apply(lambda x: f"{x:.1f}"),
            textposition="auto",
            marker_color=bar_colors,
            hovertemplate="<b>%{x}</b><br>Moyenne: %{y:.1f}/20<extra></extra>",
        )
    )

    # Ajout d'une ligne horizontale à 10/20 pour la moyenne requise
    fig.add_shape(
        type="line",
        x0=-0.5,
        y0=10,
        x1=len(average_grades["UE"]) - 0.5,
        y1=10,
        line=dict(color=colors["secondary"], width=1.5, dash="dot"),
    )

    # Personnalisation du graphique
    fig.update_layout(
        title=dict(
            text=f"Moyenne par UE",
            font=dict(size=20, family="Segoe UI, Roboto", color=colors["text"]),
            x=0.5,
            y=0.95,
        ),
        xaxis=dict(title="", tickangle=-45, gridcolor="rgba(0,0,0,0.1)", showgrid=True),
        yaxis=dict(
            title="Note /20",
            range=[0, 20],
            gridcolor="rgba(0,0,0,0.1)",
            showgrid=True,
            tickvals=[0, 5, 10, 15, 20],
        ),
        plot_bgcolor="rgba(255,255,255,0.9)",
        paper_bgcolor="rgba(255,255,255,0)",
        height=450,
        margin=dict(l=40, r=40, t=80, b=40),
        bargap=0.3,
    )

    # Ajout d'une annotation pour la ligne de moyenne
    fig.add_annotation(
        x=len(average_grades["UE"]) - 0.5,
        y=10,
        xref="x",
        yref="y",
        text="Moyenne requise",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=1,
        ax=50,
        ay=-20,
        font=dict(size=10, color=colors["secondary"]),
    )

    return fig


# Callback pour la mise à jour des statistiques globales
# Mise à jour de la fonction update_statistics
@callback(
    [Output("moyenne-generale", "children"), Output("nombre-matieres", "children")],
    Input("student-data-store", "data"),
)
def update_statistics(student_data):
    """
    Calcule et affiche les statistiques globales de l'étudiant avec format amélioré.
    """
    if not student_data:
        return "Pas de données", "Pas de données"

    filtered_df = pd.DataFrame(student_data["student_records"])

    if filtered_df.empty:
        return "Pas de données", "Pas de données"

    # IMPORTANT: La moyenne générale est calculée sur la moyenne des UE uniquement
    ue_df = filtered_df[filtered_df["est_ue"] == 1]

    if not ue_df.empty:
        moyenne = ue_df["note"].mean()
    else:
        moyenne = 0

    # Compter les matières (cours, pas UEs)
    nb_matieres = len(filtered_df[filtered_df["est_ue"] == 0]["cours"].unique())

    # Création des éléments HTML avec style conditionnel
    moyenne_html = html.Div(
        [
            html.H4("Moyenne générale", className="text-muted"),
            html.H2(
                f"{moyenne:.2f}/20",
                className=f"{'text-success font-weight-bold' if moyenne >= 10 else 'text-danger font-weight-bold'}",
            ),
            html.P(
                "Moyenne calculée sur les UEs",
                className="text-muted small",
                style={"fontSize": "0.8rem"},
            ),
        ]
    )

    matieres_html = html.Div(
        [
            html.H4("Nombre de matières", className="text-muted"),
            html.H2(f"{nb_matieres}", className="text-primary font-weight-bold"),
            html.P(
                "Hors UEs",
                className="text-muted small",
                style={"fontSize": "0.8rem"},
            ),
        ]
    )

    return moyenne_html, matieres_html


# =============================================================================
# FONCTIONS D'AIDE ADDITIONNELLES
# =============================================================================


def create_empty_db_if_not_exists():
    """
    Crée une base de données vide si elle n'existe pas déjà.
    Utile pour le premier démarrage.
    """
    if not os.path.exists(db_path):
        logger.info(f"Création d'une base de données vide à l'emplacement: {db_path}")
        db_manager = ApogeeDBManager(db_path=db_path)
        # Force l'initialisation de la structure
        db_manager.initialize_db()
        return True
    return False


# =============================================================================
# LANCEMENT DE L'APPLICATION
# =============================================================================

if __name__ == "__main__":
    # Créer la base de données si elle n'existe pas
    if not os.path.exists(db_path) and DB_AVAILABLE:
        logger.info("Initialisation de la base de données...")
        create_empty_db_if_not_exists()

    # Créer le dossier assets s'il n'existe pas
    assets_path = Path("assets")
    assets_path.mkdir(exist_ok=True)

    # Détermination du port et du mode debug
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("DEBUG", "False").lower() == "true"

    logger.info(f"Démarrage de l'application en mode offline sur le port {port}")
    app.run(debug=debug, port=port)

# Enregistrer les callbacks de la nouvelle page
register_trends_callbacks(app)
