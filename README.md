# Local Notes Assistant

A desktop app that finds the note you mean. Everything runs on your own computer. Nothing leaves it, and the app keeps no copy of your notes.

## 1. Install these once

1. **Node.js 20 or newer** — https://nodejs.org
2. **Python 3.10 or newer** — https://www.python.org/downloads
3. **Rust** (builds the desktop window) — run in a terminal:
   ```sh
   curl https://sh.rustup.rs -sSf | sh
   ```
   then close and reopen the terminal.
4. **Ollama** (the local AI model) — https://ollama.com/download. Needed from build step 4 onwards.

## 2. Run the app

```sh
npm install          # first time only
npm run tauri dev    # opens the desktop window
```

The first run compiles Rust and can take a few minutes. After that it is fast.
The Python backend sets itself up automatically on first run (it creates `backend/.venv`).

**No Rust yet?** You can still work on the UI in a browser:

```sh
npm run dev:all      # then open http://127.0.0.1:1420
```

This is for development only. It still runs only on your computer, but it is not the real app and must not be used for the demo.

## 3. Before you commit

```sh
cd backend && .venv/bin/pytest && cd ..   # backend tests
npm run build                              # frontend compiles
```

## 4. Where things are

| Folder | What |
|---|---|
| `src/` | The UI (React) |
| `src-tauri/` | The desktop window (Rust). Starts the backend, no network access |
| `backend/` | The engine (Python). Reads notes, searches, talks to Ollama. Localhost only |
| `scripts/` | Helper scripts for running and packaging |
| `docs/` | Team docs, see below |

## 5. Read next

- [docs/STATUS.md](docs/STATUS.md) — what is done, what to pick up next
- [docs/BRIEF.md](docs/BRIEF.md) — the brief, the One Rule, the safety rules
- [docs/FILES.md](docs/FILES.md) — every file and what it does

## Packaging (later)

`sh scripts/build-sidecar.sh` then `npm run tauri build`.
