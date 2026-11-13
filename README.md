# Local Notes Assistant (hackathon prototype)

Fully local desktop assistant that finds the note you mean. Nothing leaves the machine.
See [docs/BRIEF.md](docs/BRIEF.md) for the brief, stack and safety rules.

## Layout

| Path | What |
|---|---|
| `src/` | React UI (sidebar + search layout) |
| `src-tauri/` | Tauri v2 shell: strict CSP, no network plugins, spawns the sidecar and issues the session token |
| `backend/` | FastAPI sidecar, bound to 127.0.0.1, session token required on every request |
| `scripts/` | dev and packaging helpers |

## Prerequisites

- Node 20+ (`npm install`)
- Python 3.10+
- Rust toolchain (`rustup`) for the desktop shell
- Ollama (later steps)

## Run

```sh
npm install
npm run tauri dev        # full app: Rust launcher starts backend + webview
npm run dev:all          # browser only (no Rust): backend + Vite on http://127.0.0.1:1420
```

Backend tests:

```sh
cd backend && .venv/bin/pytest
```

Package the sidecar: `sh scripts/build-sidecar.sh` (then `npm run tauri build`).

## Security model (step 1)

- Tauri capability exposes only `core:default`; no shell/fs/http plugins reach the webview.
- CSP allows connections only to Tauri IPC and `http://127.0.0.1:*`.
- The Rust launcher generates a 256-bit session token per launch, passes it to the backend via env and to the UI via the `get_session` command.
- The backend hard-codes host `127.0.0.1`, refuses to start without a token, and returns 401 on every route without it.

## Docs for the team

- [docs/BRIEF.md](docs/BRIEF.md) — product brief, feature checklist, tech stack, safety rules
- [docs/STATUS.md](docs/STATUS.md) — what's done, in progress, next (per build step)
- [docs/FILES.md](docs/FILES.md) — every source file, what it does, which step edits it next
