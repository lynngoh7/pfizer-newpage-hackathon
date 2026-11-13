# PyInstaller spec for the sidecar. Build with scripts/build-sidecar.sh.
# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ["app/main.py"],
    pathex=["."],
    hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto",
                   "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="notes-backend",
          console=True, upx=False)
