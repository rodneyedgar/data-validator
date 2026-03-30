from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


PROJECT_ROOT = Path(SPEC).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
ICON_PATH = PROJECT_ROOT / "assets" / "app.ico"
VERSION_INFO_PATH = PROJECT_ROOT / "windows_version_info.txt"


hiddenimports = collect_submodules("cnds_validator")

datas = []
icon = str(ICON_PATH) if ICON_PATH.exists() else None
version = str(VERSION_INFO_PATH) if VERSION_INFO_PATH.exists() else None


a = Analysis(
    [str(PROJECT_ROOT / "launch_cnds_validator.py")],
    pathex=[str(SRC_DIR)],
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CNDS Data Validation",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    icon=icon,
    version=version,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="CNDS Data Validation",
)
