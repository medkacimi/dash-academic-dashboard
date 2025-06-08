#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Outil en ligne de commande pour importer des fichiers APOGEE dans la base SQLite.
Permet d'importer, supprimer, ou mettre à jour des données.
"""

import argparse
import sys
import os

# Ajoute le répertoire parent (qui contient src) au chemin pour trouver db_manager
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from db_manager import ApogeeDBManager


def main():
    """
    Point d'entrée principal du script d'import.
    Gère les arguments de la ligne de commande et exécute les opérations demandées.
    """
    parser = argparse.ArgumentParser(
        description="Outil de gestion des données académiques"
    )

    # Sous-commandes
    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")

    # Commande pour importer un fichier
    import_parser = subparsers.add_parser("import", help="Importer un fichier APOGEE")
    import_parser.add_argument("file", help="Chemin vers le fichier APOGEE à importer")
    import_parser.add_argument(
        "--db", help="Chemin vers la base de données SQLite", default="academic_data.db"
    )

    # Commande pour supprimer des données
    delete_parser = subparsers.add_parser("delete", help="Supprimer des données")
    delete_parser.add_argument(
        "--db", help="Chemin vers la base de données SQLite", default="academic_data.db"
    )
    _extracted_from_main_19(
        delete_parser,
        "Année académique à supprimer (ex: 2022/2023)",
        "Parcours à supprimer",
        "Semestre à supprimer",
    )
    # Commande pour lister les données
    list_parser = subparsers.add_parser("list", help="Lister les données disponibles")
    list_parser.add_argument(
        "--db", help="Chemin vers la base de données SQLite", default="academic_data.db"
    )
    list_parser.add_argument(
        "--type",
        choices=["years", "parcours", "semestres", "ues", "courses", "students"],
        required=True,
        help="Type de données à lister",
    )
    _extracted_from_main_19(
        list_parser,
        "Filtrer par année académique",
        "Filtrer par parcours",
        "Filtrer par semestre",
    )
    # Commande pour exporter vers Excel (pour compatibilité avec ancien système)
    export_parser = subparsers.add_parser(
        "export", help="Exporter les données vers Excel"
    )
    export_parser.add_argument(
        "--db", help="Chemin vers la base de données SQLite", default="academic_data.db"
    )
    export_parser.add_argument(
        "--output", help="Fichier de sortie Excel", default="data_tdb.xlsx"
    )
    _extracted_from_main_19(
        export_parser,
        "Filtrer par année académique",
        "Filtrer par parcours",
        "Filtrer par semestre",
    )
    # Analyse des arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Création du gestionnaire de base de données
    db_manager = ApogeeDBManager(db_path=args.db)

    # Exécution de la commande demandée
    if args.command == "import":
        import_file(db_manager, args.file)
    elif args.command == "delete":
        delete_data(db_manager, args)
    elif args.command == "list":
        list_data(db_manager, args)
    elif args.command == "export":
        export_to_excel(db_manager, args)


# TODO Rename this here and in `main`
def _extracted_from_main_19(arg0, help, arg2, arg3):
    arg0.add_argument("--annee", help=help)
    arg0.add_argument("--parcours", help=arg2)
    arg0.add_argument("--semestre", help=arg3)


def import_file(db_manager, file_path):
    """
    Importe un fichier APOGEE dans la base de données.

    Args:
        db_manager (ApogeeDBManager): Gestionnaire de base de données
        file_path (str): Chemin vers le fichier à importer
    """
    if not os.path.exists(file_path):
        print(f"Erreur: Le fichier {file_path} n'existe pas.")
        return

    try:
        count = db_manager.import_apogee_data(file_path)
        print(f"Import réussi: {count} étudiants importés depuis {file_path}")
    except Exception as e:
        print(f"Erreur lors de l'import: {e}")


def delete_data(db_manager, args):
    """
    Supprime des données selon les critères spécifiés.

    Args:
        db_manager (ApogeeDBManager): Gestionnaire de base de données
        args (Namespace): Arguments de la ligne de commande
    """
    criteria = {}

    if args.annee:
        criteria["annee"] = args.annee
    if args.parcours:
        criteria["parcours"] = args.parcours
    if args.semestre:
        criteria["semestre"] = args.semestre

    if not criteria:
        print("Erreur: Aucun critère de suppression spécifié.")
        return

    try:
        confirmation = input(
            f"Confirmer la suppression des données avec critères {criteria} ? (o/n): "
        )
        if confirmation.lower() != "o":
            print("Opération annulée.")
            return

        count = db_manager.delete_data(criteria)
        print(f"Suppression réussie: {count} enregistrements supprimés.")
    except Exception as e:
        print(f"Erreur lors de la suppression: {e}")


def list_data(db_manager, args):
    """
    Liste les données disponibles selon le type demandé.

    Args:
        db_manager (ApogeeDBManager): Gestionnaire de base de données
        args (Namespace): Arguments de la ligne de commande
    """
    try:
        if args.type == "years":
            items = db_manager.get_available_years()
            print("Années académiques disponibles:")
        elif args.type == "parcours":
            items = db_manager.get_available_parcours(year=args.annee)
            print("Parcours disponibles:")
        elif args.type == "semestres":
            items = db_manager.get_available_semestres(
                year=args.annee, parcours=args.parcours
            )
            print("Semestres disponibles:")
        elif args.type == "ues":
            items = db_manager.get_available_ues(
                year=args.annee, parcours=args.parcours, semestre=args.semestre
            )
            print("UEs disponibles:")
        elif args.type == "courses":
            items = db_manager.get_available_courses(
                year=args.annee, parcours=args.parcours, semestre=args.semestre
            )
            print("Cours disponibles:")
        elif args.type == "students":
            df = db_manager.get_students(
                year=args.annee, parcours=args.parcours, semestre=args.semestre
            )
            print("Étudiants disponibles:")
            for _, row in df.iterrows():
                print(
                    f"{row['nom_etu']} {row['prenom_etu']} - {row['parcours']} - {row['annee']}"
                )
            return

        for item in items:
            print(f"- {item}")

    except Exception as e:
        print(f"Erreur lors de la récupération des données: {e}")


def export_to_excel(db_manager, args):
    """
    Exporte les données vers un fichier Excel pour compatibilité avec l'ancien système.

    Args:
        db_manager (ApogeeDBManager): Gestionnaire de base de données
        args (Namespace): Arguments de la ligne de commande
    """
    try:
        # Récupération des données avec le format compatible
        df = db_manager.export_to_dataframe()

        # Filtre par année/parcours/semestre si nécessaire
        if args.annee or args.parcours or args.semestre:
            # Récupère les parcours correspondant aux critères
            parcours_ids = []

            criteria = []
            params = []

            if args.annee:
                criteria.append("annee = ?")
                params.append(args.annee)

            if args.parcours:
                criteria.append("parcours = ?")
                params.append(args.parcours)

            if args.semestre:
                criteria.append("semestre = ?")
                params.append(args.semestre)

            import sqlite3

            conn = sqlite3.connect(args.db)
            cursor = conn.cursor()

            where_clause = " AND ".join(criteria)
            cursor.execute(f"SELECT id FROM parcours WHERE {where_clause}", params)
            if parcours_ids := [row[0] for row in cursor.fetchall()]:
                placeholders = ",".join(["?"] * len(parcours_ids))
                cursor.execute(
                    f"""
                SELECT DISTINCT nom_etu, prenom_etu 
                FROM notes 
                WHERE id_parcours IN ({placeholders})
                """,
                    parcours_ids,
                )

                students = [(row[0], row[1]) for row in cursor.fetchall()]

                if student_filter := [
                    (df["Nom"] == nom) & (df["Prenom"] == prenom)
                    for nom, prenom in students
                ]:
                    combined_filter = student_filter[0]
                    for f in student_filter[1:]:
                        combined_filter |= f
                    df = df[combined_filter]

            conn.close()

        # Export vers Excel
        df.to_excel(args.output, index=False)
        print(f"Export réussi: {len(df)} enregistrements exportés vers {args.output}")

    except Exception as e:
        print(f"Erreur lors de l'export: {e}")


if __name__ == "__main__":
    main()
