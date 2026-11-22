# Local Notes Assistant

![Tauri](https://img.shields.io/badge/Tauri-v2-24C8DB?logo=tauri&logoColor=white)
![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-local-000000?logo=ollama&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-in--memory-003B57?logo=sqlite&logoColor=white)

A desktop app that finds the note you mean. Everything runs on your own computer. Nothing leaves it, and the app keeps no copy of your notes.

## Contents

- [Demo](#demo)
- [Installation](#installation)
- [Development](#development)
  - [Tech stack](#tech-stack)
  - [Prerequisites](#prerequisites)
  - [Running locally](#running-locally)
  - [Contributing](#contributing)
  - [Project structure](#project-structure)
  - [Documentation](#documentation)
- [Team](#team)

## Demo

<!-- Add the demo video link and a screenshot here, e.g.
[![Demo video](docs/demo.png)](VIDEO_LINK) -->

_Demo video coming soon._

## Installation

To use it like a normal app (no terminal), follow **[docs/INSTALL.md](docs/INSTALL.md)**. It has separate steps for Mac, Windows and Linux.

Short version, from the project folder:

```sh
sh scripts/build-app.sh   # builds the app, then installs it
```

Windows: run this in Git Bash.

## Development

### Tech stack

| Part | Used for | Why we chose it |
|---|---|---|
| Tauri v2 + React | Desktop window and UI | Small app with a strict security policy and no network permissions, so the window can't reach the internet |
| Python + FastAPI | Backend | Bound to `127.0.0.1` with a session token, so only the app can talk to it |
| Ollama (`qwen3:4b-instruct`, `nomic-embed-text`) | AI answers and search by meaning | Runs the models on the computer itself. No cloud AI, so notes never leave the device |
| SQLite in memory (FTS5 + sqlite-vec) | Keyword + meaning search index | Lives in memory only and is gone when the app quits, so the app keeps no copy of your notes |
| markitdown + pypdf | Reading PDF, Word, text and Markdown | Parse files locally, with no conversion service |

More detail: [docs/BRIEF.md](docs/BRIEF.md).

### Prerequisites

Install these once:

1. **Node.js 20 or newer** — https://nodejs.org
2. **Python 3.10 or newer** — https://www.python.org/downloads
3. **Rust** (builds the desktop window). Windows: see [docs/INSTALL.md](docs/INSTALL.md). Mac/Linux: run in a terminal:
   ```sh
   curl https://sh.rustup.rs -sSf | sh
   ```
   then close and reopen the terminal.
4. **Ollama** (the local AI model) — https://ollama.com/download (Intel Mac with Homebrew: `brew install --cask ollama-app`). Then download the two models (about 2.3 GB):
   ```sh
   ollama pull qwen3:4b-instruct      # answers and topic names
   ollama pull nomic-embed-text   # search by meaning, grouping
   ```

### Running locally

```sh
npm install          # first time only
sh scripts/build-sidecar.sh # required once per machine/target before Tauri dev
npm run tauri dev    # opens the desktop window
```

The first run compiles Rust and can take a few minutes. Rebuild the sidecar after
changing backend code or Python dependencies. After that, Tauri dev is fast.
The Python backend sets itself up automatically on first run (it creates `backend/.venv`).

**Sample notes:** some files in `sample_notes/` are generated. Run this once after cloning (see [docs/SAMPLE_NOTES.md](docs/SAMPLE_NOTES.md)):

```sh
python3 -m venv /tmp/gen && /tmp/gen/bin/pip install pymupdf python-docx
/tmp/gen/bin/python scripts/make_sample_notes.py
```

**Backend dependencies changed?** (e.g. after a pull) Reinstall:

```sh
backend/.venv/bin/pip install -U pip            # old pip can't do the next line
backend/.venv/bin/pip install -e "backend[dev]"
```

**No Rust yet?** You can still work on the UI in a browser:

```sh
npm run dev:all      # then open http://127.0.0.1:1420
```

This is for development only. It still runs only on your computer, but it is not the real app and must not be used for the demo.

### Contributing

1. **Branch from main.** Never push to `main`. Name it like `feat/…`, `fix/…`, `docs/…`.
2. **Commit with a conventional message**, e.g. `feat(search): add keyword results page`.
3. **Run the same checks CI runs:**
   ```sh
   cd backend && .venv/bin/pytest && cd ..   # backend tests
   npm run build                              # frontend compiles
   sh scripts/privacy-guard.sh                # no outside URLs in the code
   ```
4. **Push your branch and open a pull request.** The PR template fills in a short checklist: tick each item.
5. **Wait for CI to go green** (GitHub runs the three checks above on every PR, about 30 s), then merge.

### Project structure

| Folder | What |
|---|---|
| `src/` | The UI (React) |
| `src-tauri/` | The desktop window (Rust). Starts the backend, no network access |
| `backend/` | The engine (Python). Reads notes, searches, talks to Ollama. Localhost only |
| `scripts/` | Helper scripts for running and packaging |
| `docs/` | Team docs, see below |

### Documentation

- [docs/STATUS.md](docs/STATUS.md) — what is done, what to pick up next
- [docs/BRIEF.md](docs/BRIEF.md) — the brief, the One Rule, the safety rules
- [docs/FILES.md](docs/FILES.md) — every file and what it does
- [docs/INSTALL.md](docs/INSTALL.md) — install the app on Mac, Windows or Linux
- [docs/DB_DESIGN.md](docs/DB_DESIGN.md) — in-memory database tables and diagram

## Team

| Name | GitHub |
|---|---|
| Cathy | [@cathyc-c](https://github.com/cathyc-c) |
| Eoin | [@ARandomGuyTH](https://github.com/ARandomGuyTH) |
| Lynn | [@lynngoh7](https://github.com/lynngoh7) |
| Shek | [@Reverie-974](https://github.com/Reverie-974)  |
