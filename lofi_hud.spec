# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['pynput.keyboard._win32', 'lofi.app']
hiddenimports += collect_submodules('lofi')


a = Analysis(
    ['lofi_hud.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Strip out unnecessary Tcl/Tk timezone database (600+ useless files)
a.datas = [x for x in a.datas if 'tzdata' not in x[0]]

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='lofi_hud',
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
    icon=['icon.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='lofi_hud',
)
