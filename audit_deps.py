#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'audit des dépendances du projet Tableau de Bord Académique.
Utilisation : python audit_deps.py
"""

import os
import sys
import importlib
import pkg_resources
import re

def check_imports(file_path):
    """Analyse un fichier Python pour détecter les modules importés."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Recherche des imports
    import_pattern = r'^import\s+([a-zA-Z0-9_.,\s]+)|^from\s+([a-zA-Z0-9_.]+)\s+import'
    imports = []
    
    for match in re.finditer(import_pattern, content, re.MULTILINE):
        if match.group(1):  # import module
            modules = [m.strip() for m in match.group(1).split(',')]
            imports.extend(modules)
        elif match.group(2):  # from module import ...
            imports.append(match.group(2).strip())
    
    # Nettoyage des imports relatifs
    cleaned_imports = []
    for imp in imports:
        base_module = imp.split('.')[0]
        if base_module not in cleaned_imports:
            cleaned_imports.append(base_module)
    
    return cleaned_imports

def is_standard_library(module_name):
    """Vérifie si un module fait partie de la bibliothèque standard Python."""
    try:
        module_info = importlib.util.find_spec(module_name)
        if module_info is None:
            return False
        
        # Vérifier si le module est dans la bibliothèque standard
        module_path = module_info.origin
        if module_path is None:
            return True  # Modules intégrés comme 'sys'
        
        return 'site-packages' not in module_path and 'dist-packages' not in module_path
    except (ImportError, AttributeError):
        return False

def check_installed_modules(required_modules):
    """Vérifie quels modules requis sont installés et leurs versions."""
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    
    results = {}
    for module in required_modules:
        if module in installed_packages:
            results[module] = {"installed": True, "version": installed_packages[module]}
        elif is_standard_library(module):
            results[module] = {"installed": True, "standard_library": True}
        else:
            results[module] = {"installed": False}
    
    return results

def find_circular_imports():
    """Recherche des imports circulaires potentiels."""
    circular_imports = []
    module_deps = {}
    
    # Construire un graphe de dépendances
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                module_name = os.path.basename(file_path).replace('.py', '')
                imports = check_imports(file_path)
                module_deps[module_name] = imports
    
    # Rechercher les cycles
    def has_path(start, end, visited=None):
        if visited is None:
            visited = set()
        
        if start == end:
            return True
        if start in visited:
            return False
        
        visited.add(start)
        for dep in module_deps.get(start, []):
            if dep in module_deps and has_path(dep, end, visited.copy()):
                return True
        
        return False
    
    # Vérifier chaque paire de modules
    for module, deps in module_deps.items():
        for dep in deps:
            if dep in module_deps and has_path(dep, module):
                circular_imports.append((module, dep))
    
    return circular_imports

def check_unused_installed_packages():
    """Identifie les packages installés mais non utilisés dans le projet."""
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    
    # Collecter tous les imports
    all_imports = set()
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                imports = check_imports(file_path)
                all_imports.update(imports)
    
    # Trouver les packages installés mais non utilisés
    unused_packages = {}
    for pkg, version in installed_packages.items():
        if pkg not in all_imports and not pkg.startswith('_'):
            # Exclure les packages de développement courants
            if pkg not in ['pip', 'setuptools', 'wheel', 'distlib', 'pytest', 'pylint', 'flake8', 'mypy', 'black']:
                unused_packages[pkg] = version
    
    return unused_packages

def main():
    """Fonction principale."""
    print("=== RAPPORT D'AUDIT DES DÉPENDANCES ===\n")
    
    # Trouver tous les fichiers Python du projet
    python_files = []
    for root, _, files in os.walk('.'):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    
    print(f"Nombre de fichiers Python trouvés: {len(python_files)}\n")
    
    # Collecter tous les imports
    all_imports = set()
    imports_by_file = {}
    for file_path in python_files:
        file_imports = check_imports(file_path)
        imports_by_file[file_path] = file_imports
        all_imports.update(file_imports)
    
    # Vérifier l'installation des modules
    module_status = check_installed_modules(all_imports)
    
    # Lister les modules requis et leur statut
    print("Modules requis par le projet :")
    for module, status in sorted(module_status.items()):
        if status.get("standard_library", False):
            print(f"  - {module} (bibliothèque standard)")
        elif status["installed"]:
            print(f"  - {module} (version installée: {status['version']})")
        else:
            print(f"  - {module} (NON INSTALLÉ)")
    
    # Vérifier les imports circulaires
    circular_imports = find_circular_imports()
    if circular_imports:
        print("\nImports circulaires détectés :")
        for module1, module2 in circular_imports:
            print(f"  - {module1} <-> {module2}")
    else:
        print("\nAucun import circulaire détecté.")
    
    # Vérifier les packages installés mais non utilisés
    unused_packages = check_unused_installed_packages()
    if unused_packages:
        print("\nPackages installés mais non utilisés dans le projet :")
        for pkg, version in sorted(unused_packages.items()):
            print(f"  - {pkg} (version: {version})")
    else:
        print("\nAucun package installé non utilisé détecté.")
    
    # Vérifier le requirements.txt
    try:
        with open('requirements.txt', 'r') as f:
            requirements = [line.strip().split('==')[0].split('>=')[0].split('<')[0] for line in f.readlines() 
                           if line.strip() and not line.startswith('#')]
        
        print("\nModules dans requirements.txt mais non utilisés :")
        unused = [req for req in requirements if req.lower() not in [m.lower() for m in all_imports]]
        if unused:
            for module in sorted(unused):
                print(f"  - {module}")
        else:
            print("  Aucun")
        
        print("\nModules utilisés mais non listés dans requirements.txt :")
        missing = [module for module in all_imports 
                  if not is_standard_library(module) 
                  and module.lower() not in [req.lower() for req in requirements]]
        if missing:
            for module in sorted(missing):
                print(f"  - {module}")
        else:
            print("  Aucun")
            
    except FileNotFoundError:
        print("\nFichier requirements.txt non trouvé !")
        print("Modules externes détectés qui devraient être dans requirements.txt :")
        external_modules = [module for module in all_imports if not is_standard_library(module)]
        for module in sorted(external_modules):
            print(f"  - {module}")
    
    # Générer un requirements.txt si demandé
    if len(sys.argv) > 1 and sys.argv[1] == "--generate-requirements":
        external_modules = [module for module in all_imports if not is_standard_library(module)]
        
        if external_modules:
            with open('requirements.txt.new', 'w') as f:
                f.write("# Requirements.txt généré automatiquement\n\n")
                for module in sorted(external_modules):
                    try:
                        version = pkg_resources.get_distribution(module).version
                        f.write(f"{module}>={version}\n")
                    except pkg_resources.DistributionNotFound:
                        f.write(f"{module}\n")
            
            print("\nNouveau fichier requirements.txt.new généré.")
            print("Vérifiez et renommez ce fichier en requirements.txt si vous êtes satisfait du contenu.")
        else:
            print("\nAucun module externe détecté, pas de requirements.txt généré.")

if __name__ == "__main__":
    main()
