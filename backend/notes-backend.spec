# PyInstaller spec for the sidecar. Build with scripts/build-sidecar.sh.
# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ["app/main.py"],
    pathex=["."],
    # uvicorn picks these modules by name at runtime, so PyInstaller cannot
    # see them being imported. Step 7 adds sqlite-vec here.
    hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto",
                   "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="notes-backend",
          console=True, upx=False)
