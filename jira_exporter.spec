# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Get the path to the script directory
# script_dir = os.path.dirname(os.path.abspath('jira_csv_exporter.py'))
script_dir = os.path.dirname(os.path.abspath('JiraExporterCSV2.py'))

a = Analysis(
    ['JiraExporterCSV2.py'],
    pathex=[script_dir],
    binaries=[],
    datas=[
        ('templates', 'templates'),
    ],
    hiddenimports=[
        'flask',
        'jira',
        'bs4',
        'csv',
        'io',
        'tempfile',
        'uuid',
        'threading',
        'time',
        're',
        'html',
        'datetime',
        'werkzeug.security',
        'werkzeug.serving',
        'jinja2',
        'markupsafe',
        'itsdangerous',
        'click',
        'blinker'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='JiraCSVExporter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)