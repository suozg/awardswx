# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Собираем всё для wx
wx_datas = collect_data_files('wx')
wx_hidden = collect_submodules('wx')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=wx_datas,
    hiddenimports=wx_hidden,
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
    name='awardswx',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # <-- отключить
    console=False,
    onefile=True,
)

#a = Analysis(
#    ['main.py'],
#    pathex=[],
#    binaries=[],
#    datas=[],
#    hiddenimports=['wx._xml'],
#    hookspath=[],
#    hooksconfig={},
#    runtime_hooks=[],
#    excludes=[],
#    noarchive=False,
#    optimize=0,
#)
#pyz = PYZ(a.pure)

#exe = EXE(
#    pyz,
#    a.scripts,
#    a.binaries,
#    a.datas,
#    [],
#    name='awardswx',
#    debug=False,
#    bootloader_ignore_signals=False,
#    strip=False,
#    upx=True,
#    upx_exclude=[],
#    runtime_tmpdir=None,
#    console=False,
#    onefile=True,
#    disable_windowed_traceback=False,
#    argv_emulation=False,
#    target_arch=None,
#    codesign_identity=None,
#    entitlements_file=None,
#)
