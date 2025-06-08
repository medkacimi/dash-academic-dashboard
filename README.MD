# Dash Academic Dashboard 📊🎓

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) [![Build Status](https://img.shields.io/github/actions/workflow/status/VOTRE_UTILISATEUR/NOM_DU_REPO/ci.yml?branch=main)](#) [![Stars](https://img.shields.io/github/stars/VOTRE_UTILISATEUR/NOM_DU_REPO?style=social)](#)

**Dash Academic Dashboard** est une application web interactive, développée en Python avec Dash, permettant d’extraire, traiter et visualiser les tendances des données académiques issues du système Apogée.

---

## 🚀 Fonctionnalités clés

* 🗄️ **Intégration des données**

  * Extraction et parsing des ressources Apogée (`parser_apogee.py`).
  * Gestion de la base de données SQLite (`db_manager.py`).
* 📥 **Ressources hors ligne**

  * Support de l’import de jeux de données statiques (`offline_resources.py`).
* 📈 **Tableau de bord interactif**

  * Graphiques dynamiques et filtres avec Dash (`dashboard_trends.py`)
  * Point d’entrée dédié (`main_improved.py`).
* 🔌 **Extensibilité**

  * Architecture modulaire facilitant l’ajout de nouveaux indicateurs.

---

## 🛠️ Prérequis

* Python **3.8+** 🐍
* `pip` pour la gestion des dépendances

---

## ⚙️ Installation et configuration

1. **Cloner le dépôt** :

   ```bash
   git clone https://github.com/VOTRE_UTILISATEUR/NOM_DU_REPO.git
   cd NOM_DU_REPO
   ```

2. **Environnement virtuel** (recommandé) :

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate     # Windows
   ```

3. **Installer les dépendances** :

   ```bash
   pip install -r requirements.txt
   ```

4. **Variables d’environnement** :
   Créez un fichier `.env` (non versionné) :

   ```env
   DATABASE_URL=sqlite:///academic_data.db
   # Ajoutez vos propres clés/variables ici
   ```

---

## ▶️ Utilisation

Lancez l’application Dash :

```bash
python main_improved.py
```

Accédez ensuite à `http://127.0.0.1:8050/` dans votre navigateur.

---

## 📁 Structure du projet

```text
├── parser_apogee.py       # Extraction et parsing des données Apogée
├── db_manager.py          # Gestion de la base SQLite
├── offline_resources.py   # Import de ressources hors ligne
├── dashboard_trends.py    # Code des graphiques Dash
├── main_improved.py       # Lancement de l’app
├── requirements.txt       # Dépendances Python
├── README.md              # Documentation du projet
└── .gitignore             # Fichiers ignorés par Git
```

---

## 🤝 Contribuer

Les contributions sont les bienvenues !
Merci de :

1. Forker le projet.
2. Créer une branche (`git checkout -b feature/nouvel_indicateur`).
3. Valider vos changements (`git commit -m 'Ajout d'un nouvel indicateur'`).
4. Pousser vers la branche (`git push origin feature/nouvel_indicateur`).
5. Ouvrir une Pull Request.

---
