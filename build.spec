# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Liste des modules à exclure pour réduire la taille
excluded_modules = [
    'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'tkinter', 'IPython',  
    'scipy', 'pandas.tests', 'matplotlib.tests', 'numpy.random._examples',
    'pytest', 'setuptools', 'docutils', 'sphinx', 'unittest', 'debugpy',
    'nbconvert', 'nbformat', 'notebook'
]

# Collecter les données des packages
datas = [
    ('assets', 'assets')
]

# Ajout de données dash-bootstrap-components
datas += collect_data_files('dash_bootstrap_components')

# Détection et ajout de ressources SQLite si nécessaire
if os.path.exists('academic_data.db'):
    datas.append(('academic_data.db', '.'))
else:
    print("Warning: Database file 'academic_data.db' not found")

a = Analysis(
    ['main_improved.py'],  # Script principal
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'plotly.graph_objects',
        'dash_bootstrap_components',
        'sqlite3', 
        'pandas',
        'base64',
        'tempfile',
        'json'
    ] + collect_submodules('dash'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TableauDeBordAcademique',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False, 
    upx=False,    
    console=True,  
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,  
    upx=True,   
    upx_exclude=[],
    name='TableauDeBordAcademique',
)