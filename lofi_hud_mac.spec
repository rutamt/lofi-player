# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['pynput.keyboard._darwin', 'lofi.app']
hiddenimports += collect_submodules('lofi')

datas = []
for icon_name in ['icon.ico', 'icon.icns', 'icon.png']:
    if os.path.exists(icon_name):
        datas.append((icon_name, '.'))

a = Analysis(
    ['lofi_hud.py'],
    pathex=[],
    binaries=[],
    datas=datas,
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

icon_file = 'icon.icns' if os.path.exists('icon.icns') else None

app = BUNDLE(
    coll,
    name='LoFi HUD.app',
    icon=icon_file,
    bundle_identifier='com.rutamt.lofihud',
    info_plist={
        'CFBundleName': 'LoFi HUD',
        'CFBundleDisplayName': 'LoFi HUD',
        'CFBundleIdentifier': 'com.rutamt.lofihud',
        'CFBundleVersion': '1.0.1',
        'CFBundleShortVersionString': '1.0.1',
        'NSHighResolutionCapable': True,
    },
)
