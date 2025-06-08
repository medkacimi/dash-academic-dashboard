# Dash Academic Dashboard

Une application Dash pour visualiser des tendances académiques à partir de données Apogée.

## Fonctionnalités

* Tableau de bord interactif avec graphiques de tendances (`dashboard_trends.py`).
* Gestion de la base de données SQLite (`db_manager.py`).
* Extraction et parsing des ressources hors ligne (`offline_resources.py`).
* Récupération et traitement des données Apogée (`parser_apogee.py`).

## Prérequis

* Python 3.8+
* [pip](https://pip.pypa.io/en/stable/)

## Installation

1. Cloner le dépôt :

   ```bash
   git clone https://github.com/VOTRE_UTILISATEUR/NOM_DU_REPO.git
   cd NOM_DU_REPO
   ```

2. Créer et activer un environnement virtuel (optionnel mais recommandé) :

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. Installer les dépendances :

   ```bash
   pip install -r requirements.txt
   ```

## Configuration

* Assurez-vous d’avoir un fichier de configuration `.env` (non versionné) avec :

  ```env
  DATABASE_URL=sqlite:///academic_data.db
  # Autres variables si nécessaire
  ```

## Lancer l'application

Pour démarrer le serveur Dash :

```bash
python main_improved.py
```

L’application sera accessible à l’adresse `http://127.0.0.1:8050/`.

## Structure du projet

├── dashboard_trends.py     # Code du dash et des graphiques
├── db_manager.py          # Gestion de la base de données
├── main_improved.py       # Point d'entrée de l'application
├── offline_resources.py   # Chargement des ressources hors ligne
├── parser_apogee.py       # Extraction et parsing des données Apogée
├── requirements.txt       # Liste des dépendances
├── README.md              # Documentation du projet
└── .gitignore             # Fichiers et dossiers ignorés

## Contribuer

Les contributions sont les bienvenues ! Merci d’ouvrir une issue ou une pull request.

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
