#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard complémentaire ("Suivi des moyennes sur plusieurs années")
===================================================================

Ce module Dash fournit :
- Le suivi de la **moyenne par semestre d'un étudiant** sur toutes les années disponibles ;
- Le suivi de la **moyenne d'un cours pour tout le groupe** sur plusieurs années ;
- L'évolution d'un **cours (moyenne générale)** sur plusieurs années ;

Hypothèses / rappel :
- La moyenne générale est calculée uniquement à partir des lignes où `est_ue == 1` (moyenne des UE).
- Les données proviennent de la base *academic_data.db* déjà générée par l'application principale.
- Le tableau de bord est autonome, mais peut être rattaché à votre application existante via une nouvelle route (`/trends`).

Utilisation rapide :
-------------------
```
python dashboard_trends.py  # puis ouvrir http://127.0.0.1:8050
```
Ou, dans l'application principale :
- Ajouter un lien dans `navbar` vers `/trends`.
- Importer `register_trends_callbacks(app)` pour enregistrer les callbacks sans dupliquer l'application.

"""

import logging
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import (
    Dash,
    html,
    dcc,
    Input,
    Output,
    State,
    no_update,
    callback,
)
from db_manager import ApogeeDBManager

# -----------------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# BASE DE DONNÉES & CHARGEMENT DES DONNÉES
# -----------------------------------------------------------------------------
try:
    from db_manager import ApogeeDBManager
except ImportError as exc:  # pragma: no cover
    raise SystemExit("db_manager.py introuvable – vérifiez votre PYTHONPATH") from exc

DB_PATH = Path(__file__).with_suffix(".db").name  # academic_data.db par défaut

db_manager = ApogeeDBManager(db_path=str(DB_PATH))

# Chargement initial
RAW_DF: pd.DataFrame = db_manager.export_to_dataframe()
if RAW_DF.empty:  # pragma: no cover
    logger.warning(
        "Aucune donnée trouvée. Importez d'abord quelques fichiers APOGEE avant de lancer le dashboard !"
    )

# -----------------------------------------------------------------------------
# MÉTADONNÉES POUR LES CONTRÔLES
# -----------------------------------------------------------------------------
STUDENTS = []
COURSES = []

if not RAW_DF.empty:
    # Vérifier si les colonnes nécessaires existent
    required_columns = ["Nom", "Prenom", "cours", "est_ue"]
    if all(col in RAW_DF.columns for col in required_columns):
        STUDENTS = (
            RAW_DF.drop_duplicates(subset=["Nom", "Prenom"])[["Nom", "Prenom"]]
            .apply(lambda x: f"{x['Prenom']} {x['Nom']}", axis=1)
            .sort_values()
            .tolist()
        )

        COURSES = RAW_DF[RAW_DF["est_ue"] == 0]["cours"].dropna().unique().tolist()
        COURSES.sort()
    else:
        logger.warning("Certaines colonnes requises sont manquantes dans le DataFrame")

# -----------------------------------------------------------------------------
# APPLICATION DASH
# -----------------------------------------------------------------------------
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
app.title = "Suivi des moyennes – Historique"

# -----------------------------------------------------------------------------
# LAYOUT
# -----------------------------------------------------------------------------
app.layout = dbc.Container(
    [
        html.H2("Évolution des moyennes sur plusieurs années", className="my-4"),
        dbc.Row(
            [
                # ------------------------- COLONNE CONTRÔLES -----------------
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("Filtres"),
                                dbc.CardBody(
                                    [
                                        html.Label("Type de suivi", className="mb-2"),
                                        dcc.RadioItems(
                                            id="view-type",
                                            options=[
                                                {
                                                    "label": "Étudiant",
                                                    "value": "student",
                                                },
                                                {
                                                    "label": "Cours (groupe)",
                                                    "value": "course",
                                                },
                                            ],
                                            value="student",
                                            className="mb-4",
                                        ),
                                        html.Div(id="dynamic-input"),
                                        html.Label("Tri", className="mt-4 mb-2"),
                                        dcc.Dropdown(
                                            id="sort-order",
                                            options=[
                                                {
                                                    "label": "Année croissante",
                                                    "value": "asc",
                                                },
                                                {
                                                    "label": "Année décroissante",
                                                    "value": "desc",
                                                },
                                            ],
                                            value="asc",
                                            clearable=False,
                                        ),
                                    ]
                                ),
                            ],
                            className="shadow-sm",
                        )
                    ],
                    md=4,
                ),
                # ---------------------- COLONNE GRAPHIQUE -------------------
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardHeader("Moyenne par année"),
                                dbc.CardBody([dcc.Graph(id="trends-graph")]),
                            ],
                            className="shadow-sm",
                        )
                    ],
                    md=8,
                ),
            ],
            align="stretch",
        ),
    ],
    fluid=True,
    style={"padding": "2rem", "backgroundColor": "#f0f2f5"},
)

# -----------------------------------------------------------------------------
# CALLBACKS
# -----------------------------------------------------------------------------


@app.callback(Output("dynamic-input", "children"), Input("view-type", "value"))
def update_dynamic_input(view):
    """Affiche dynamiquement le contrôle adapté (étudiant ou cours)."""

    if not STUDENTS and not COURSES:
        return html.Div(
            "Aucune donnée disponible. Veuillez d'abord importer des données APOGEE.",
            className="alert alert-warning",
        )

    if view == "student":
        if not STUDENTS:
            return html.Div(
                "Aucun étudiant trouvé dans les données.",
                className="alert alert-warning",
            )
        return [
            html.Label("Étudiant", className="mb-2"),
            dcc.Dropdown(
                id="student-select",
                options=[{"label": s, "value": s} for s in STUDENTS],
                value=STUDENTS[0] if STUDENTS else None,
                clearable=False,
            ),
        ]
    else:  # course
        if not COURSES:
            return html.Div(
                "Aucun cours trouvé dans les données.", className="alert alert-warning"
            )
        return [
            html.Label("Cours", className="mb-2"),
            dcc.Dropdown(
                id="course-select",
                options=[{"label": c, "value": c} for c in COURSES],
                value=COURSES[0] if COURSES else None,
                clearable=False,
            ),
        ]


@app.callback(
    Output("trends-graph", "figure"),
    [
        Input("view-type", "value"),
        Input("student-select", "value"),
        Input("course-select", "value"),
        Input("sort-order", "value"),
    ],
)
def update_trends(view, student, course, order):
    """Construit la figure selon la vue sélectionnée."""

    if RAW_DF.empty:
        return go.Figure()

    # --------------------------- ÉTUDIANT -----------------------------
    if view == "student" and student:
        try:
            prenom, nom = student.split(" ", 1)
        except ValueError:
            return go.Figure()
        subset = RAW_DF[
            (RAW_DF["Nom"] == nom)
            & (RAW_DF["Prenom"] == prenom)
            & (RAW_DF["est_ue"] == 1)  # Moyenne générale = moyenne des UE
        ]
        grouped = subset.groupby("Annee")["note"].mean().reset_index()
        label = f"Moyenne semestrielle de {student}"

    # --------------------------- COURS -------------------------------
    elif view == "course" and course:
        subset = RAW_DF[RAW_DF["cours"] == course]
        grouped = subset.groupby("Annee")["note"].mean().reset_index()
        label = f"Moyenne du cours : {course}"

    else:  # Aucune sélection valable
        return go.Figure()

    # Ordre de tri
    grouped = grouped.sort_values("Annee", ascending=(order == "asc"))

    # --------------------------- FIGURE ------------------------------
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=grouped["Annee"],
            y=grouped["note"],
            mode="lines+markers",
            name=label,
        )
    )
    fig.update_layout(
        xaxis_title="Année académique",
        yaxis_title="Moyenne /20",
        hovermode="x unified",
        template="plotly_white",
        margin=dict(l=40, r=20, t=40, b=40),
    )
    return fig


# -----------------------------------------------------------------------------
# ENREGISTREMENT DANS UNE APP EXISTANTE (facultatif)
# -----------------------------------------------------------------------------


def register_trends_callbacks(external_app):
    """Permet d'enregistrer ces callbacks dans une app Dash déjà existante."""

    for callback in app.callback_map.values():
        external_app.callback(**callback["callback"])(
            *callback["inputs"], **callback["state"]
        )


# -----------------------------------------------------------------------------
# MAIN (pour exécution autonome)
# -----------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    app.run(debug=True)
