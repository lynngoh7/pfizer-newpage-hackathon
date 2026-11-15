# File map

One row per source file: what it does, and which build step touches it next.
Add a row whenever you create a file.

## Root
| File | Purpose | Next edit |
|---|---|---|
| `package.json` | npm scripts + frontend deps. `tauri dev`, `dev:all`, `build` | add deps as needed |
| `vite.config.ts` | Vite on fixed port 1420 (Tauri requirement) | — |
| `tsconfig.json` | strict TS config | — |
| `index.html` | single HTML entry; no external assets | — |
| `README.md` | install and run steps; pointers to docs/ | keep short |
| `docs/BRIEF.md` | product brief, feature checklist, stack, safety rules | when a decision changes |
| `docs/STATUS.md` | progress per build step + where to start | every change |
| `docs/FILES.md` | this file | every new file |
| `scripts/dev.sh` | browser-only dev: shared token for backend + Vite, sets `NOTES_DEV=1` | — |
| `scripts/dev-backend.sh` | run sidecar alone (creates venv on first run) | — |
| `scripts/build-sidecar.sh` | PyInstaller build → `src-tauri/binaries/notes-backend` | step 7 (bundle sqlite-vec) |

## Frontend `src/`
| File | Purpose | Next edit |
|---|---|---|
| `main.tsx` | React entry | — |
| `App.tsx` | view switch (home/search/decisions/conflicts/activity/settings); owns the current query | step 3: render `SearchResults`; step 4: answer view |
| `styles.css` | all styling; CSS variables, light/dark via `prefers-color-scheme`; system fonts only | per feature |
| `lib/api.ts` | backend client; gets port+token from Tauri `get_session` (or Vite env in browser dev); `apiFetch` adds bearer header | add a typed function per new route |
| `components/Sidebar.tsx` | nav + engine status dot (polls `/api/health` every 5 s) | — |
| `components/SearchBar.tsx` | single input; submits query to `App` | step 3/4: loading state |
| `pages/Home.tsx` | empty state; `.widget-grid` reserved for future widgets | out of scope now |
| `pages/Placeholder.tsx` | stub view shown for not-yet-built screens | delete once all views exist |
| `pages/Settings.tsx` | folder access (stub), engine info, forget-everything (disabled) | step 2: folder list + picker; step 5: forget everything |

## Tauri `src-tauri/`
| File | Purpose | Next edit |
|---|---|---|
| `tauri.conf.json` | window, strict CSP (`connect-src` = IPC + `127.0.0.1:*`), bundle config | step 2: none; CSP must not loosen |
| `capabilities/default.json` | webview permissions: `core:default` only | step 2: add `dialog:allow-open` for folder picker |
| `Cargo.toml` | Rust deps: tauri, serde, rand | step 2: `tauri-plugin-dialog` |
| `src/main.rs` | binary entry → `lib::run()` | — |
| `src/lib.rs` | Tauri builder; registers `get_session`; stops backend on exit | add commands as needed |
| `src/sidecar.rs` | token + port generation, spawns backend (packaged binary or Python in debug), sets `NOTES_DEV` in debug builds only, kill on drop | — |
| `icons/icon.png` | 1×1 placeholder | replace with real icon set |

## Backend `backend/`
| File | Purpose | Next edit |
|---|---|---|
| `pyproject.toml` | deps (fastapi, uvicorn), dev extras (pytest, httpx), package extra (pyinstaller) | step 2: pymupdf, markitdown; step 7: sqlite-vec |
| `notes-backend.spec` | PyInstaller spec | step 7: hidden imports for sqlite-vec |
| `app/__init__.py` | version | — |
| `app/config.py` | env → `Settings`; host hard-coded 127.0.0.1; exits if token missing; `dev` flag from `NOTES_DEV` | — (no data dir: nothing is stored on disk) |
| `app/auth.py` | bearer-token middleware, constant-time compare, every request | — |
| `app/api.py` | routes under `/api`; `GET /api/health` | every step adds routes here (or split into routers) |
| `app/main.py` | `create_app(settings)` + uvicorn entry; CORS allows the Tauri window only, plus Vite in dev mode | — |
| `tests/test_health.py` | token required; health payload; dev origin blocked unless dev mode | add a test file per module |

### Planned backend modules (not yet created)
`permissions.py` (allow/denylist, single path-check function) · `ingest.py` · `db.py` (in-memory SQLite, no note text on disk) · `search.py` · `qa.py` · `extract.py` · `conflicts.py` · `audit.py` (in memory, paths and actions only)
