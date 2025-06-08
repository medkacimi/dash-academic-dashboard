# Tableau de Bord Académique 📊🎓

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE) [![Build Status](https://img.shields.io/github/actions/workflow/status/VOTRE_UTILISATEUR/TableauDeBordAcademique/ci.yml?branch=main)](#)

**Tableau de Bord Académique** est une application web interactive, développée en Python avec Dash, pour extraire, traiter et visualiser les tendances des données académiques issues du système Apogée.

---

## 🚀 Fonctionnalités clés

* 🗄️ **Intégration des données**

  * Extraction et parsing des ressources Apogée via `parser_apogee.py`
  * Gestion et migrations de la base SQLite (`db_manager.py`)
* 📥 **Ressources hors ligne**

  * Import et audit de jeux de données statiques (`offline_resources.py`, `audit_deps.py`)
* 📈 **Tableau de bord interactif**

  * Graphiques dynamiques et filtres avec Dash (`dashboard_trends.py`)
  * Point d’entrée principal : `main_improved.py`
* ⚙️ **Packaging et distribution**

  * Fichier de spécification PyInstaller (`build.spec`)
  * Déploiement standalone dans `dist/TableauDeBordAcademique`
* 🔌 **Extensibilité & configuration**

  * Architecture modulaire facilitant l’ajout de nouveaux modules et indicateurs

---

## 🛠️ Prérequis

* Python **3.8+** 🐍
* `pip` ou `poetry` pour la gestion des dépendances

---

## ⚙️ Installation & configuration

1. **Cloner le dépôt**

   ```bash
   git clone https://github.com/VOTRE_UTILISATEUR/TableauDeBordAcademique.git
   cd TableauDeBordAcademique
   ```

2. **Environnement virtuel** (fortement recommandé)

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   venv\Scripts\activate    # Windows
   ```

3. **Installer les dépendances**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configurer les variables d’environnement**

   Créez un fichier `.env` (non versionné) à la racine :

   ```env
   DATABASE_URL=sqlite:///academic_data.db
   # Autres clés si nécessaire
   ```

---

## ▶️ Lancer l’application

```bash
python main_improved.py
```

Puis ouvrez votre navigateur à l’adresse : `http://127.0.0.1:8050/`

---

## 📂 Structure du projet

```text
├── .vscode/                         # Configurations VSCode
├── assets/                          # Fichiers statiques (CSS, images)
├── build/                           # Dossiers générés par PyInstaller
│   └── build/
├── dist/TableauDeBordAcademique/    # Application standalone générée
├── parser_apogee.py                 # Extraction et parsing des données Apogée
├── db_manager.py                    # Gestion de la base SQLite
├── offline_resources.py             # Import des ressources hors ligne
├── audit_deps.py                    # Audit des dépendances de données
├── dashboard_trends.py              # Création des graphiques Dash
├── main_improved.py                 # Point d’entrée de l’application
├── build.spec                       # Spécification PyInstaller
├── requirements.txt                 # Dépendances Python
├── README.md                        # Documentation du projet
└── .gitignore                       # Fichiers ignorés par Git
```

---

## 🤝 Contribuer

Les contributions sont les bienvenues ! Merci de :

1. Forker le projet.
2. Créer une branche (`git checkout -b feature/mon-ajout`).
3. Valider vos changements (`git commit -m 'Ajout: description courte'`).
4. Pousser vers GitHub (`git push origin feature/mon-ajout`).
5. Ouvrir une Pull Request.

---
