# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/templates', 'app/templates'),
        ('app/static', 'app/static'),
        ('app/document_templates', 'app/document_templates'),
        ('config.py', '.'),
    ],
    hiddenimports=[
        # Flask e extensões
        'flask',
        'flask_login',
        'flask_sqlalchemy',
        'flask_wtf',
        'wtforms',
        # Servidor
        'waitress',
        # Banco de dados
        'sqlalchemy',
        'sqlalchemy.dialects.sqlite',
        # Processamento de dados
        'pandas',
        'pandas.io.formats.excel',
        'openpyxl',
        'openpyxl.styles',
        'openpyxl.styles.fills',
        'openpyxl.styles.alignment',
        # Word documents
        'docx',
        'docx.oxml',
        'docx.oxml.ns',
        # Utilitários
        'werkzeug',
        'werkzeug.utils',
        'werkzeug.security',
        'jinja2',
        'markupsafe',
        'itsdangerous',
        'click',
        'email.mime.text',
        'email.header',
        'smtplib',
        'qrcode',
        'PIL',
        'cryptography',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AlmoxarifadoDigital',
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
    icon=None,
)
