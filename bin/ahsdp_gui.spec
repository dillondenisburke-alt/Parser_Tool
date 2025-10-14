# -*- mode: python ; coding: utf-8 -*-
import pathlib

try:
    __import__('tkinterdnd2')
    _hidden_imports = ['tkinterdnd2']
except ImportError:
    _hidden_imports = []

block_cipher = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

a = Analysis(
    ['src/ahsdp/gui.py'],
    pathex=[str(SRC)],
    binaries=[],
    datas=[
        ('README.md', '.'),
        ('LICENSE.txt', '.'),
    ],
    hiddenimports=_hidden_imports,
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
    [],
    exclude_binaries=True,
    name='ahsdp-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ahsdp_gui',
)
