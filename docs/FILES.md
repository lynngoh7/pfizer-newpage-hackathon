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
| `docs/API_SHAPES.md` | agreed JSON shape for search/answer responses (UI ↔ backend) | when search/qa output changes |
| `docs/FILES.md` | this file | every new file |
| `.github/pull_request_template.md` | checklist shown when opening a PR (tests, docs, privacy rules) | when team rules change |
| `scripts/dev.sh` | browser-only dev: shared token for backend + Vite, sets `NOTES_DEV=1` | — |
| `scripts/dev-backend.sh` | run sidecar alone (creates venv on first run) | — |
| `scripts/privacy-guard.sh` | fails if `src/` or `backend/app/` contain a URL other than localhost; run by CI | — |
| `.github/workflows/ci.yml` | CI: backend tests, frontend build, privacy guard on PRs and pushes to main | — |
| `scripts/make_sample_notes.py` | generates the .docx/.pdf/.png samples, symlinks and file dates in `sample_notes/` (dev only: needs pymupdf, python-docx) | when sample notes change |
| `docs/THIRD_PARTY.md` | licence notices for code copied in (Lucide icons) | when copying in third-party code |
| `docs/SAMPLE_NOTES.md` | sample notes guide: demo story, test questions, edge cases | when sample notes change |
| `sample_notes/` | fictional manager notes + `edge_cases/`. Never real notes | add files as needed |
| `scripts/build-sidecar.sh` | PyInstaller build → `src-tauri/binaries/notes-backend` | step 7 (bundle sqlite-vec) |

## Frontend `src/`
| File | Purpose | Next edit |
|---|---|---|
| `main.tsx` | React entry | — |
| `App.tsx` | view switch (home/search/decisions/conflicts/privacy/settings); owns the current query; Privacy is lazy-loaded | step 3: render `SearchResults`; step 4: answer view |
| `styles.css` | all styling; CSS variables; follows macOS light/dark, increase contrast, reduce motion; focus rings; system fonts only | per feature |
| `lib/trust.ts` | client + types for the Trust panel routes (audit, network, storage, forget) | step 5 |
| `lib/api.ts` | backend client; gets port+token from Tauri `get_session` (or Vite env in browser dev); `apiFetch` adds bearer header | add a typed function per new route |
| `components/Sidebar.tsx` | nav + engine status dot (polls `/api/health` every 5 s); status is a plain label (not clickable), announced to VoiceOver when it changes; inline Lucide nav icons (no icon package) | — |
| `components/SearchBar.tsx` | single input; submits query to `App` | step 3/4: loading state |
| `components/FolderAccess.tsx` | add/remove folders and files the app may read this session (Tauri dialog); first card on Privacy | step 2c: show indexing progress |
| `components/ForgetButton.tsx` | "Forget everything" with confirm step and visible result; used on Privacy and Settings | — |
| `pages/Privacy.tsx` | Trust panel: folder access (`FolderAccess`), summary, network, saved to disk, activity log, forget everything | — |
| `pages/Home.tsx` | empty state; `.widget-grid` reserved for future widgets | out of scope now |
| `pages/Placeholder.tsx` | stub view shown for not-yet-built screens | delete once all views exist |
| `pages/Settings.tsx` | engine, AI model picker (choice saved to `prefs.json`), indexing, accessibility note, built-in safety facts, forget everything (always last) | step 2c: indexing card; step 4: real model list from Ollama |

## Tauri `src-tauri/`
| File | Purpose | Next edit |
|---|---|---|
| `tauri.conf.json` | window (`incognito`: the webview keeps nothing on disk), strict CSP (`connect-src` = IPC + `127.0.0.1:*`), bundle config | step 2: none; CSP must not loosen |
| `capabilities/default.json` | webview permissions: `core:default`, webview zoom (⌘+/⌘−), `dialog:allow-open` | keep permissions minimal |
| `Cargo.toml` | Rust deps: tauri, dialog plugin, serde, rand | — |
| `src/main.rs` | binary entry → `lib::run()` | — |
| `src/lib.rs` | Tauri builder; registers dialog plugin and `get_session`; stops backend on exit | add commands as needed |
| `src/sidecar.rs` | token + port generation, spawns backend (packaged binary or Python in debug), sets `NOTES_DEV` in debug builds only, kill on drop | — |
| `icons/icon.png` | 1×1 placeholder | replace with real icon set |

## Backend `backend/`
| File | Purpose | Next edit |
|---|---|---|
| `pyproject.toml` | **the one place to add Python deps**: deps (fastapi, uvicorn, psutil), dev extras (pytest, httpx), package extra (pyinstaller) | step 2: pymupdf, markitdown; step 7: sqlite-vec |
| `notes-backend.spec` | PyInstaller spec | step 7: hidden imports for sqlite-vec |
| `app/__init__.py` | version | — |
| `app/config.py` | env → `Settings`; host hard-coded 127.0.0.1; exits if token missing; `dev` flag from `NOTES_DEV` | — (the only saved file is `prefs.json`, see `prefs.py`) |
| `app/auth.py` | bearer-token middleware, constant-time compare, every request; marks every response `no-store` | — |
| `app/api.py` | routes under `/api`; health, folder/file grants (`GET/POST/DELETE /api/folders`, saved via `prefs`), `GET/PUT /api/settings` | every step adds routes here (or split into routers) |
| `app/prefs.py` | the one file saved to disk: `prefs.json` with folder paths + allowlisted settings, never note content; restores folders on launch; deleted by forget | add a key to `SAVED_SETTINGS` for each new setting |
| `app/permissions.py` | allowlist (filled from `prefs.json` on launch) + denylist; `resolve_and_check(path)` is the one path check every file read uses | step 2c: ingest calls it; add audit records |
| `app/main.py` | `create_app(settings)` + uvicorn entry; CORS allows the Tauri window only, plus Vite in dev mode | — |
| `app/audit.py` | in-memory activity log: fixed action list, path, query, short outcome. Never note text | step 2: ingest/permissions call `record` |
| `app/session.py` | "forget everything": modules register a reset with `on_forget`; `forget()` runs them all | every module that holds session data |
| `app/trust.py` | read-only checks: app processes' sockets (psutil), files in the app's data folders (`prefs.json` is expected, anything else is flagged) | — |
| `app/routes_trust.py` | `/api/audit`, `/api/trust/network`, `/api/trust/saved`, `/api/trust/storage`, `DELETE /api/session` | — |
| `app/citations.py` | citation checker: verifies each cited quote is in its chunk, drops unbacked claims, returns NO_SUPPORT if none survive. Pure, no I/O | step 4: called by `qa.py` |
| `tests/test_citations.py` | quote matching, rejections, claim filtering, one real sample note | — |
| `tests/test_trust.py` | audit rules, forget, connection kinds, storage report, routes need token | — |
| `tests/conftest.py` | points `prefs.json` at a temp folder for every test | — |
| `tests/test_privacy_edges.py` | forget clears everything, revoke hook, symlink/deny/missing-folder edge cases, no note text in log or prefs | 4b/4c: add real index checks when db.py lands |
| `tests/test_no_network.py` | blocks non-loopback connects and DNS, runs a whole session through the API; fails on any outbound attempt | 4d: add search and ask calls when 1d and 2c land |
| `tests/test_prefs.py` | saved folders/settings, paths only, allowlist, restore, forget, disk check | — |
| `tests/test_permissions.py` | grants, protected paths, symlink escape, revoke | — |
| `tests/test_health.py` | token required; health payload; dev origin blocked unless dev mode | add a test file per module |

### Planned backend modules (not yet created)
`ingest.py` · `db.py` (in-memory SQLite, no note text on disk) · `search.py` · `qa.py` (calls `citations.check_answer`) · `extract.py` · `conflicts.py`
