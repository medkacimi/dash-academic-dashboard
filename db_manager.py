#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module de gestion de la base de données pour l'application de tableau de bord académique.
Fournit les fonctionnalités d'import, de consultation et de manipulation des données APOGEE.
"""

import os
import sqlite3
import logging
import pandas as pd
import re
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ApogeeDBManager:
    """
    Gestionnaire de base de données pour les fichiers APOGEE.
    Permet l'import, la consultation et la manipulation des données.
    """

    def __init__(self, db_path="academic_data.db"):
        """
        Initialise le gestionnaire de base de données.

        Args:
            db_path (str): Chemin vers la base de données SQLite
        """
        self.db_path = db_path
        self.initialize_db()

    def get_connection(self):
        """
        Établit une connexion à la base de données.

        Returns:
            tuple: (connexion, curseur)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Pour accéder aux colonnes par nom
            cursor = conn.cursor()
            return conn, cursor
        except sqlite3.Error as e:
            logger.error(f"Erreur de connexion à la base de données: {e}")
            raise

    def initialize_db(self):
        """
        Initialise la structure de la base de données si elle n'existe pas.
        """
        try:
            conn, cursor = self.get_connection()

            # Création de la table des étudiants si elle n'existe pas
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS etudiants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT NOT NULL,
                    prenom TEXT NOT NULL,
                    numero_etudiant TEXT,
                    parcours TEXT,
                    annee TEXT,
                    semestre TEXT,
                    UNIQUE(nom, prenom, parcours, annee, semestre)
                )
                """
            )

            # Création de la table des notes
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    etudiant_id INTEGER,
                    ue TEXT,
                    cours TEXT,
                    note REAL,
                    est_ue INTEGER DEFAULT 0,
                    FOREIGN KEY (etudiant_id) REFERENCES etudiants (id),
                    UNIQUE(etudiant_id, cours)
                )
                """
            )

            conn.commit()
            conn.close()
            logger.info("Structure de la base de données initialisée avec succès.")
        except sqlite3.Error as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
            raise

    def parse_apogee_file(self, file_path):
        """
        Parse un fichier APOGEE au format texte (relevé de notes USMB).
        Version refactorisée pour améliorer la lisibilité et la maintenabilité.

        Args:
            file_path (str): Chemin vers le fichier à analyser

        Returns:
            dict: Données extraites du fichier
        """
        try:
            # Chargement du contenu du fichier
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            logger.info(
                f"Fichier chargé: {file_path}, taille: {len(content)} caractères"
            )

            # Structure de données résultante
            data = {"parcours": self._extract_parcours_info(content), "etudiants": []}

            # Extraction des blocs d'étudiants
            student_blocks = self._extract_student_blocks(content)
            logger.info(f"Nombre d'étudiants trouvés: {len(student_blocks)}")

            # Traitement de chaque bloc d'étudiant
            for block in student_blocks:
                student_data = self._process_student_block(block)
                if student_data:
                    data["etudiants"].append(student_data)

            # Vérification finale
            if not data["etudiants"]:
                logger.warning("Aucun étudiant n'a pu être extrait du fichier.")
            else:
                logger.info(
                    f"Parsing réussi: {len(data['etudiants'])} étudiants extraits."
                )

            return data

        except Exception as e:
            logger.error(f"Erreur lors du parsing du fichier APOGEE: {e}")
            import traceback

            logger.error(f"Détails: {traceback.format_exc()}")
            raise

    def _extract_parcours_info(self, content):
        """
        Extrait les informations de parcours du contenu du fichier.

        Args:
            content (str): Contenu du fichier

        Returns:
            dict: Informations de parcours (parcours, année, semestre)
        """
        parcours_info = {"parcours": "M1 API", "semestre": "7", "annee": "2022-2023"}

        # Extraction du parcours et semestre
        semestre_parcours_match = re.search(
            r"inscrit[e]?\s+en\s+Semestre\s+(\d+)\s+([^\s\n]+)", content
        )
        if semestre_parcours_match:
            parcours_info["semestre"] = semestre_parcours_match.group(1)
            parcours_info["parcours"] = semestre_parcours_match.group(2)

        # Extraction de l'année
        annee_match = re.search(r"Année universitaire (\d{4}/\d{4})", content)
        if annee_match:
            parcours_info["annee"] = annee_match.group(1).replace("/", "-")
        else:
            # Recherche d'un format alternatif de date
            session_match = re.search(r"Session\s+S\d+\s+(\d{4}/\d{2})", content)
            if session_match:
                annee_short = session_match.group(1)
                # Conversion 2022/23 en 2022-2023
                if len(annee_short) == 7:  # Format "2022/23"
                    year_start = annee_short[:4]
                    year_end = "20" + annee_short[5:7]
                    parcours_info["annee"] = f"{year_start}-{year_end}"

        logger.info(
            f"Parcours détecté: {parcours_info['parcours']}, Année: {parcours_info['annee']}, Semestre: {parcours_info['semestre']}"
        )
        return parcours_info

    def _extract_student_blocks(self, content):
        """
        Extrait les blocs d'étudiants du contenu du fichier.

        Args:
            content (str): Contenu du fichier

        Returns:
            list: Liste des blocs d'étudiants trouvés
        """
        # Regex pour trouver les blocs d'étudiants
        student_pattern = (
            r"([A-ZÀ-ÖØ-Þ]+(?:\s[A-ZÀ-ÖØ-Þ]+)*)"
            r"\s+([A-Za-zÀ-ÖØ-öø-ÿ'-]+(?:\s[A-Za-zÀ-ÖØ-öø-ÿ'-]+)*)"
            r"\s*\nN°\s*Etudiant\s*:\s*(\d+)\s*INE\s*:\s*\S+"
            + r"\s*\nNé(?:e)? le\s*:[^\n]+"
            + r"\s*\ninscrit[e]?\s+en\s+Semestre\s+\d+[^\n]+"  # Ligne "inscrit en Semestre"
            r"(?:\s*\n)+"  # Au moins un saut de ligne pour séparer des en-têtes de notes
            r"(?:Notes et résultats\s*\n)?"  # En-tête optionnel
            r"(?:Note/Barème Pts jury Résultat Session Crédits\s*\n)?"  # En-tête optionnel
            r"\s*(UE.+?)"  # Bloc de notes, commençant par UE, non-gourmand
            # Lookahead pour la fin du bloc de notes
            r"(?="
            r"\n\s*\n"  # Deux sauts de ligne (avec espaces optionnels)
            r"(?:"  # Groupe non-capturant pour les conditions alternatives
            # Soit un nouvel étudiant (Nom Prénom \n N° Etudiant)
            r"[A-ZÀ-ÖØ-Þ]+(?:\s[A-ZÀ-ÖØ-Þ]+)*\s+[A-Za-zÀ-ÖØ-öø-ÿ'-]+(?:\s[A-Za-zÀ-ÖØ-öø-ÿ'-]+)*\s*\nN°\s*Etudiant"
            # Soit un en-tête de page "Université Savoie Mont Blanc Année universitaire"
            r"|Université Savoie Mont Blanc Année universitaire"
            r")"  # Fin du groupe non-capturant
            r"|\Z"  # Ou la fin du fichier
            r")"  # Fin du lookahead
        )

        return re.findall(student_pattern, content, re.DOTALL)

    def _process_student_block(self, block):
        """
        Traite un bloc d'étudiant pour en extraire les informations et les notes.

        Args:
            block (tuple): Bloc d'étudiant extrait par regex

        Returns:
            dict: Données de l'étudiant ou None en cas d'erreur
        """
        try:
            nom, prenom, student_number, notes_block = block

            nom = nom.strip()
            prenom = prenom.strip()
            student_number = student_number.strip()

            logger.info(
                f"Traitement de l'étudiant: {prenom} {nom}, N°: {student_number}"
            )

            # Extraction des UEs et matières
            courses = self._extract_courses(notes_block)

            logger.info(f"Étudiant traité: {prenom} {nom}, {len(courses)} cours/UEs")

            return {
                "numero_etudiant": student_number,
                "nom": nom,
                "prenom": prenom,
                "cours": courses,
            }

        except Exception as e:
            logger.error(f"Erreur lors du traitement d'un bloc étudiant: {e}")
            return None

    def _extract_courses(self, notes_block):
        """
        Extrait les UEs et matières d'un bloc de notes.

        Args:
            notes_block (str): Bloc de notes d'un étudiant

        Returns:
            list: Liste des UEs et matières avec leurs notes
        """
        courses = []

        # Extraction des UEs et leurs notes
        ue_pattern = r"(UE\d+[^0-9\n]*)\s+(\d+[\.,]\d+)\s*/20"
        ue_matches = re.findall(ue_pattern, notes_block)

        for ue_match in ue_matches:
            ue_name, ue_note_str = ue_match
            ue_name = ue_name.strip()

            try:
                ue_note = float(ue_note_str.replace(",", ".").strip())
            except ValueError:
                ue_note = 0

            # Ajouter l'UE comme cours spécial
            courses.append(
                {
                    "ue": ue_name,
                    "cours": ue_name,  # Le nom du cours est le même que l'UE
                    "note": ue_note,
                    "est_ue": 1,  # Indicateur que c'est une UE
                }
            )

            # Extraction des cours associés à cette UE
            courses.extend(self._extract_ue_courses(notes_block, ue_name))

        return courses

    def _extract_ue_courses(self, notes_block, ue_name):
        """
        Extrait les cours associés à une UE spécifique.

        Args:
            notes_block (str): Bloc de notes complet
            ue_name (str): Nom de l'UE

        Returns:
            list: Liste des cours associés à l'UE
        """
        courses = []

        # Délimitation de la section de l'UE
        ue_start = notes_block.find(ue_name)
        next_ue = notes_block.find("UE", ue_start + len(ue_name))
        if next_ue == -1:
            next_ue = len(notes_block)

        # Extrait le segment concernant cette UE
        ue_section = notes_block[ue_start:next_ue]

        # Extraction des cours (lignes qui n'ont pas "UE" et qui ont une note "/20")
        course_pattern = r"^([^U/\n][^\n]*?)\s+(\d+[\.,]\d+)\s*/20"
        course_matches = re.findall(course_pattern, ue_section, re.MULTILINE)

        for course_match in course_matches:
            course_name, course_note_str = course_match
            course_name = course_name.strip()

            # Ignorer les lignes qui contiennent des mots-clés comme "Note/Barème"
            if "Note/Barème" in course_name or "Note :" in course_name:
                continue

            try:
                course_note = float(course_note_str.replace(",", ".").strip())
            except ValueError:
                course_note = 0

            courses.append(
                {
                    "ue": ue_name,
                    "cours": course_name,
                    "note": course_note,
                    "est_ue": 0,  # Indicateur que ce n'est pas une UE
                }
            )

        return courses

    def import_apogee_data(self, file_path):
        """
        Importe les données d'un fichier APOGEE dans la base de données.

        Args:
            file_path (str): Chemin vers le fichier à importer
        Returns:
            int: Nombre d'étudiants effectivement importés
        """
        # 1) Parsing
        data = self.parse_apogee_file(file_path)
        if not data["etudiants"]:
            logger.warning("Aucun étudiant trouvé dans le fichier.")
            return 0

        parcours  = data["parcours"].get("parcours",  "Inconnu")
        annee     = data["parcours"].get("annee",     "Inconnu")
        semestre  = data["parcours"].get("semestre",  "Inconnu")

        conn, cursor = self.get_connection()
        students_imported = 0

        for student in data["etudiants"]:
            # --- 2) DÉBUT d’une transaction locale ---
            cursor.execute("SAVEPOINT import_student")
            try:
                # Étudiant (on ignore s’il existe déjà)
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO etudiants
                    (nom, prenom, numero_etudiant, parcours, annee, semestre)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        student["nom"],
                        student["prenom"],
                        student["numero_etudiant"],
                        parcours,
                        annee,
                        semestre,
                    ),
                )

                # Récupérer l’ID (nouveau ou existant)
                cursor.execute(
                    """
                    SELECT id FROM etudiants
                    WHERE nom=? AND prenom=? AND parcours=? AND annee=? AND semestre=?
                    """,
                    (
                        student["nom"],
                        student["prenom"],
                        parcours,
                        annee,
                        semestre,
                    ),
                )
                etudiant_id = cursor.fetchone()["id"]

                # Notes (doublons ignorés)
                for course in student["cours"]:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO notes
                        (etudiant_id, ue, cours, note, est_ue)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            etudiant_id,
                            course["ue"],
                            course["cours"],
                            course["note"],
                            course["est_ue"],
                        ),
                    )

                # --- 3) Fin de la transaction locale ---
                cursor.execute("RELEASE import_student")
                conn.commit()
                students_imported += 1

            except sqlite3.IntegrityError as e:
                # On annule seulement cet étudiant, pas toute l’importation
                logger.warning(
                    "Étudiant ignoré (%s %s) : %s",
                    student["prenom"],
                    student["nom"],
                    e,
                )
                cursor.execute("ROLLBACK TO import_student")

        conn.close()
        logger.info("%d étudiants importés avec succès.", students_imported)
        return students_imported

    def export_to_dataframe(self):
        """
        Exporte les données de la base en DataFrame.

        Returns:
            pd.DataFrame: DataFrame contenant les données
        """
        try:
            conn, cursor = self.get_connection()

            # Requête pour joindre les tables étudiants et notes
            cursor.execute(
                """
                SELECT
                    e.nom as Nom,
                    e.prenom as Prenom,
                    e.numero_etudiant as NumeroEtudiant,
                    e.parcours as Parcours,
                    e.annee as Annee,
                    e.semestre as Semestre,
                    n.ue as ue,
                    n.cours as cours,
                    n.note as note,
                    n.est_ue as est_ue
                FROM
                    etudiants e
                JOIN
                    notes n ON e.id = n.etudiant_id
                """
            )

            # Conversion en DataFrame
            rows = cursor.fetchall()
            df = pd.DataFrame([dict(row) for row in rows])

            conn.close()
            logger.info(f"{len(df)} enregistrements exportés avec succès.")
            return df

        except Exception as e:
            logger.error(f"Erreur lors de l'export des données: {e}")
            return pd.DataFrame()  # Retourne un DataFrame vide en cas d'erreur

    def get_available_years(self):
        """
        Récupère la liste des années académiques disponibles.

        Returns:
            list: Liste des années disponibles
        """
        try:
            conn, cursor = self.get_connection()
            cursor.execute("SELECT DISTINCT annee FROM etudiants ORDER BY annee")
            years = [row[0] for row in cursor.fetchall()]
            conn.close()
            return years
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des années: {e}")
            return []

    def get_available_parcours(self, year=None):
        """
        Récupère la liste des parcours disponibles, éventuellement filtrée par année.

        Args:
            year (str, optional): Année académique pour filtrer les parcours

        Returns:
            list: Liste des parcours disponibles
        """
        try:
            conn, cursor = self.get_connection()
            if year:
                cursor.execute(
                    "SELECT DISTINCT parcours FROM etudiants WHERE annee = ? ORDER BY parcours",
                    (year,),
                )
            else:
                cursor.execute(
                    "SELECT DISTINCT parcours FROM etudiants ORDER BY parcours"
                )
            parcours_list = [row[0] for row in cursor.fetchall()]
            conn.close()
            return parcours_list
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des parcours: {e}")
            return []

    def get_available_semestres(self, year=None, parcours=None):
        """
        Récupère la liste des semestres disponibles, éventuellement filtrée par année et parcours.

        Args:
            year (str, optional): Année académique pour filtrer
            parcours (str, optional): Parcours pour filtrer

        Returns:
            list: Liste des semestres disponibles
        """
        try:
            conn, cursor = self.get_connection()
            query = "SELECT DISTINCT semestre FROM etudiants"
            conditions = []
            params = []

            if year:
                conditions.append("annee = ?")
                params.append(year)
            if parcours:
                conditions.append("parcours = ?")
                params.append(parcours)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY semestre"

            cursor.execute(query, params)
            semestres = [row[0] for row in cursor.fetchall()]
            conn.close()
            return semestres
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des semestres: {e}")
            return []

    def get_students(self, year=None, parcours=None, semestre=None):
        """
        Récupère les étudiants avec filtres optionnels.

        Args:
            year (str, optional): Année académique
            parcours (str, optional): Parcours
            semestre (str, optional): Semestre

        Returns:
            pd.DataFrame: DataFrame des étudiants
        """
        try:
            conn, cursor = self.get_connection()
            query = "SELECT nom, prenom, numero_etudiant, parcours, annee, semestre FROM etudiants"
            conditions = []
            params = []

            if year:
                conditions.append("annee = ?")
                params.append(year)
            if parcours:
                conditions.append("parcours = ?")
                params.append(parcours)
            if semestre:
                conditions.append("semestre = ?")
                params.append(semestre)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY nom, prenom"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            df = pd.DataFrame([dict(row) for row in rows])
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des étudiants: {e}")
            return pd.DataFrame()

    def delete_data(self, criteria):
        """
        Supprime les données de la base selon les critères spécifiés.
        Supprime d'abord les notes associées, puis les étudiants.

        Args:
            criteria (dict): Dictionnaire des critères (annee, parcours, semestre)

        Returns:
            int: Nombre d'étudiants supprimés
        """
        try:
            conn, cursor = self.get_connection()
            conditions = []
            params = []

            if "annee" in criteria:
                conditions.append("annee = ?")
                params.append(criteria["annee"])
            if "parcours" in criteria:
                conditions.append("parcours = ?")
                params.append(criteria["parcours"])
            if "semestre" in criteria:
                conditions.append("semestre = ?")
                params.append(criteria["semestre"])

            if not conditions:
                logger.warning("Aucun critère de suppression fourni.")
                return 0

            where_clause = " AND ".join(conditions)

            # 1. Récupérer les IDs des étudiants à supprimer
            cursor.execute(
                f"SELECT id FROM etudiants WHERE {where_clause}", tuple(params)
            )
            student_ids_to_delete = [row[0] for row in cursor.fetchall()]

            if not student_ids_to_delete:
                logger.info("Aucun étudiant à supprimer selon les critères.")
                conn.close()
                return 0

            # 2. Supprimer les notes associées à ces étudiants
            placeholders = ",".join(["?"] * len(student_ids_to_delete))
            cursor.execute(
                f"DELETE FROM notes WHERE etudiant_id IN ({placeholders})",
                tuple(student_ids_to_delete),
            )
            notes_deleted_count = cursor.rowcount

            # 3. Supprimer les étudiants
            cursor.execute(f"DELETE FROM etudiants WHERE {where_clause}", tuple(params))
            students_deleted_count = cursor.rowcount

            conn.commit()
            conn.close()
            logger.info(
                f"{students_deleted_count} étudiants et {notes_deleted_count} notes associées supprimés."
            )
            return students_deleted_count

        except Exception as e:
            logger.error(f"Erreur lors de la suppression des données: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            if conn:
                conn.close()

    def get_student_data(self, nom, prenom, year=None, parcours=None, semestre=None):
        """
        Récupère les données d'un étudiant spécifique avec filtres optionnels.

        Args:
            nom (str): Nom de l'étudiant
            prenom (str): Prénom de l'étudiant
            year (str, optional): Année académique
            parcours (str, optional): Parcours
            semestre (str, optional): Semestre

        Returns:
            pd.DataFrame: DataFrame des notes de l'étudiant
        """
        try:
            conn, cursor = self.get_connection()

            # Construction de la requête avec filtres
            query = """
            SELECT 
                e.id as etudiant_id,
                e.nom, 
                e.prenom, 
                e.numero_etudiant, 
                e.parcours, 
                e.annee, 
                e.semestre,
                n.ue,
                n.cours,
                n.note,
                n.est_ue
            FROM 
                etudiants e
            JOIN 
                notes n ON e.id = n.etudiant_id
            WHERE 
                e.nom = ? AND e.prenom = ?
            """

            params = [nom, prenom]

            # Ajout des filtres optionnels
            if year:
                query += " AND e.annee = ?"
                params.append(year)
            if parcours:
                query += " AND e.parcours = ?"
                params.append(parcours)
            if semestre:
                query += " AND e.semestre = ?"
                params.append(semestre)

            # Exécution de la requête
            cursor.execute(query, params)
            rows = cursor.fetchall()
            df = pd.DataFrame([dict(row) for row in rows])

            conn.close()
            logger.info(f"Données récupérées pour l'étudiant {prenom} {nom} ({len(df)} enregistrements)")
            return df

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des données pour {prenom} {nom}: {e}")
            return pd.DataFrame()  # Retourne un DataFrame vide en cas d'erreur

    def get_available_ues(self, year=None, parcours=None, semestre=None):
        """
        Récupère la liste des UEs disponibles, éventuellement filtrée par année, parcours et semestre.

        Args:
            year (str, optional): Année académique pour filtrer
            parcours (str, optional): Parcours pour filtrer
            semestre (str, optional): Semestre pour filtrer

        Returns:
            list: Liste des UEs disponibles
        """
        try:
            conn, cursor = self.get_connection()
            query = "SELECT DISTINCT ue FROM notes n JOIN etudiants e ON n.etudiant_id = e.id WHERE n.est_ue = 1"
            conditions = []
            params = []

            if year:
                conditions.append("e.annee = ?")
                params.append(year)
            if parcours:
                conditions.append("e.parcours = ?")
                params.append(parcours)
            if semestre:
                conditions.append("e.semestre = ?")
                params.append(semestre)

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += " ORDER BY ue"

            cursor.execute(query, params)
            ues = [row[0] for row in cursor.fetchall()]
            conn.close()
            return ues
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des UEs: {e}")
            return []

    def get_available_courses(self, year=None, parcours=None, semestre=None, ue=None):
        """
        Récupère la liste des cours disponibles, éventuellement filtrée.

        Args:
            year (str, optional): Année académique pour filtrer
            parcours (str, optional): Parcours pour filtrer
            semestre (str, optional): Semestre pour filtrer
            ue (str, optional): UE pour filtrer

        Returns:
            list: Liste des cours disponibles
        """
        try:
            conn, cursor = self.get_connection()
            query = "SELECT DISTINCT cours FROM notes n JOIN etudiants e ON n.etudiant_id = e.id WHERE n.est_ue = 0"
            conditions = []
            params = []

            if year:
                conditions.append("e.annee = ?")
                params.append(year)
            if parcours:
                conditions.append("e.parcours = ?")
                params.append(parcours)
            if semestre:
                conditions.append("e.semestre = ?")
                params.append(semestre)
            if ue:
                conditions.append("n.ue = ?")
                params.append(ue)

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += " ORDER BY cours"

            cursor.execute(query, params)
            courses = [row[0] for row in cursor.fetchall()]
            conn.close()
            return courses
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des cours: {e}")
            return []
