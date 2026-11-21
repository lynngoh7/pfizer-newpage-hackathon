"""PyInstaller entry point for the packaged backend.

app/main.py uses relative imports, so it cannot be the frozen script itself;
this file imports it as part of the `app` package. Dev runs use
`python -m app.main` and never touch this file.
"""
from app.main import main

if __name__ == "__main__":
    main()
