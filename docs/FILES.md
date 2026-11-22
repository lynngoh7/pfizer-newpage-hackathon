# File map

One row per source file: what it does, and when it would need changing.

## Root
| File | Purpose | Next edit |
|---|---|---|
| `package.json` | npm scripts + frontend deps. `tauri dev`, `dev:all`, `build` | add deps as needed |
| `vite.config.ts` | Vite on fixed port 1420 (Tauri requirement) | — |
| `tsconfig.json` | strict TS config | — |
| `src/vite-env.d.ts` | Vite type declarations for TypeScript | — |
| `index.html` | single HTML entry; no external assets | — |
| `README.md` | install and run steps; pointers to docs/ | keep short |
| `docs/BRIEF.md` | product brief, feature checklist, stack, safety rules | when a decision changes |
| `docs/DB_DESIGN.md` | in-memory DB tables (Files, Chunks, Groups, keyword index, vectors) + diagram | when db.py changes the schema |
| `docs/FILES.md` | this file | every new file |
| `scripts/dev.sh` | browser-only dev: shared token for backend + Vite, sets `NOTES_DEV=1` | — |
| `scripts/dev-backend.sh` | run sidecar alone (creates venv on first run) | — |
| `scripts/privacy-guard.sh` | fails if `src/` or `backend/app/` contain a URL other than localhost; run by CI | — |
| `.github/workflows/ci.yml` | CI: backend tests, frontend build, privacy guard on PRs and pushes to main | — |
| `.github/workflows/build-app.yml` | Builds the app on Apple Silicon Mac, Intel Mac, Windows and Linux, checks the bundled backend starts, attaches installers (manual only, to save Actions minutes) | — |
| `scripts/make_sample_notes.py` | generates the .docx/.pdf/.png samples, symlinks and file dates in `sample_notes/` (dev only: needs pymupdf, python-docx) | when sample notes change |
| `docs/THIRD_PARTY.md` | licence notices for code copied in (Lucide icons) | when copying in third-party code |
| `docs/SAMPLE_NOTES.md` | sample notes guide: demo story, test questions, edge cases | when sample notes change |
| `docs/INSTALL.md` | install the app: step by step for Mac, Windows, Linux (installer or build yourself) | when packaging changes |
| `sample_notes/` | fictional manager notes + `edge_cases/`. Never real notes | add files as needed |
| `scripts/build-sidecar.sh` | PyInstaller build → `src-tauri/binaries/notes-backend-<target-triple>` (`.exe` on Windows; the name Tauri's `externalBin` needs). Works in Git Bash | step 7 (bundle sqlite-vec) |
| `scripts/build-app.sh` | Builds backend + app and installs it (Mac /Applications, Windows installer, Linux .deb/.rpm; `--install` = last build only) | — |

## Frontend `src/`
| File | Purpose | Next edit |
|---|---|---|
| `main.tsx` | React entry | — |
| `App.tsx` | view switch (home/search/decisions/changes/privacy/settings); owns the current query; Privacy is lazy-loaded | step 4: connect the answer view |
| `styles.css` | all styling; CSS variables; follows macOS light/dark, increase contrast, reduce motion; focus rings; system fonts only | per feature |
| `lib/trust.ts` | client + types for the Trust panel routes (audit, network, storage, forget) | step 5 |
| `lib/api.ts` | backend client; gets port+token from Tauri `get_session` (or Vite env in browser dev); typed functions for health, folders, indexing and search | add a typed function per new route |
| `components/Sidebar.tsx` | nav + engine status dot; exports `NavIcon` (also used on Home) (polls `/api/health` every 5 s); status is a plain label (not clickable), announced to VoiceOver when it changes; inline Lucide nav icons (no icon package), one per page: Decisions and To-dos are separate pages with different icons | — |
| `components/SearchBar.tsx` | single input; submits query to `App` | step 3/4: loading state |
| `components/FolderAccess.tsx` | add/remove folders and files the app may read this session (Tauri dialog); re-indexes after adding locations | step 2c: show indexing progress |
| `components/ForgetButton.tsx` | "Forget everything" with confirm step and visible result; used on Privacy and Settings | — |
| `pages/NewNote.tsx` | Capture: write a new note, save as `.md` in an allowed folder (searchable) or another folder (not tracked) | — |
| `pages/Privacy.tsx` | Trust panel: folder access (`FolderAccess`), summary, network, saved to disk, activity log, forget everything | — |
| `public/haystack-logo.svg` | same logo cropped to the tile (no macOS icon margin) so it reads at sidebar size | — |
| `pages/Home.tsx` | manager summary: Upcoming dates, Changes, Decisions and open To-dos (counts the session ticks via `todoKey`), each linking to its full page; built from the in-memory index, nothing saved | — |
| `pages/SearchResults.tsx` | routes keyword queries to `/api/search` and questions to `/api/ask`; links verified answer claims to their source cards | demo polish and accessibility checks |
| `components/MarkdownExcerpt.tsx` | safely formats common Markdown headings, lists, task checkboxes, quotes, code and inline emphasis in source excerpts; links remain text | expand Markdown support if needed |
| `pages/Decisions.tsx` | lists decisions from `/api/decisions` with source file | — |
| `pages/Todos.tsx` | lists to-dos from `/api/todos`; ticks are session-only (memory, never written), exported with `todoKey` so Home counts the same ticks; "Edit in note" opens the file in the user's editor | — |
| `pages/Upcoming.tsx` | full list from `/api/upcoming`: overdue open to-dos, then everything from today on; "Open note" opens the file. Lazy-loaded; data passed in from `App.tsx` | — |
| `pages/Changes.tsx` | "Changes" page (view id `changes`, lazy-loaded): polls `/api/changes`, earlier vs latest note side by side with verified quotes (Markdown symbols stripped for display), gentle "Updated"/"Differs" tags | — |
| `pages/Settings.tsx` | engine, AI model picker (choice saved to `prefs.json`), indexing, accessibility note, built-in safety facts, forget everything (always last) | step 2c: indexing card; step 4: real model list from Ollama |

## Tauri `src-tauri/`
| File | Purpose | Next edit |
|---|---|---|
| `tauri.conf.json` | window (`incognito`: the webview keeps nothing on disk), strict CSP (`connect-src` = IPC + `127.0.0.1:*`), bundle config | step 2: none; CSP must not loosen |
| `capabilities/default.json` | webview permissions: `core:default`, webview zoom (⌘+/⌘−), `dialog:allow-open` | keep permissions minimal |
| `Cargo.toml` | Rust deps: tauri, dialog plugin, serde, rand | — |
| `src/main.rs` | binary entry → `lib::run()` | — |
| `src/lib.rs` | Tauri builder; registers dialog plugin and `get_session`; stops backend on exit | add commands as needed |
| `src/sidecar.rs` | token + port generation, spawns backend (packaged binary or Python in debug), sets `NOTES_DEV` in debug builds only, on quit asks the backend to unload the model, then SIGTERM (SIGKILL after 3 s) so the PyInstaller child isn't orphaned (Windows: `taskkill /T`); hides the backend console window on Windows | — |
| `icons/` | placeholder app icon set (blue circle), made with `npx tauri icon <1024px png>` | replace with real logo |

## Backend `backend/`
| File | Purpose | Next edit |
|---|---|---|
| `pyproject.toml` | **the one place to add Python deps**: deps (fastapi, uvicorn, psutil, pypdf, markitdown[docx]), dev extras (pytest, httpx), package extra (pyinstaller) | step 2: markitdown; step 7: sqlite-vec |
| `notes-backend.spec` | PyInstaller spec (entry: `run_backend.py`) |
| `run_backend.py` | PyInstaller entry point; imports `app.main` as a package so relative imports work | — | step 7: hidden imports for sqlite-vec |
| `app/__init__.py` | version | — |
| `app/config.py` | env → `Settings`; host hard-coded 127.0.0.1; exits if token missing; `dev` flag from `NOTES_DEV` | — (the only saved file is `prefs.json`, see `prefs.py`) |
| `app/auth.py` | bearer-token middleware, constant-time compare, every request; marks every response `no-store` | — |
| `app/api.py` | routes under `/api`; health, folder/file grants (`GET/POST/DELETE /api/folders`, saved via `prefs`), `GET/PUT /api/settings`, search, `POST /api/ask`, `GET/POST /api/changes` | every step adds routes here (or split into routers) |
| `app/prefs.py` | the one file saved to disk: `prefs.json` with folder paths + allowlisted settings, never note content; restores folders on launch; deleted by forget | add a key to `SAVED_SETTINGS` for each new setting |
| `app/permissions.py` | allowlist (filled from `prefs.json` on launch) + denylist; `resolve_and_check(path)` is the one path check every file read uses | step 2c: ingest calls it; add audit records |
| `app/main.py` | `create_app(settings)` + uvicorn entry; CORS allows the Tauri window only, plus Vite in dev mode | — |
| `app/audit.py` | in-memory activity log: fixed action list, path, query, short outcome. Never note text | step 2: ingest/permissions call `record` |
| `app/ingest.py` | split TXT (blank lines), MD and DOCX (headings; DOCX via markitdown), PDF (pages, pypdf) into `Chunk`s with path + start/end line or page; broken files skipped and logged; every read via `resolve_and_check`; `ingestAllowed()` walks allowed folders; `mergeSmall()` joins small neighbouring chunks | — |
| `app/group.py` | group chunks by topic: `nomic-embed-text` vectors → similarity groups (≥ 0.75) → one `qwen3:4b-instruct` call names each group. Memory only, Ollama on 127.0.0.1. | — (`db.build` calls it) |
| `app/models.py` | warm `nomic-embed-text` + answer model at startup (keep_alive -1), the one place that unloads them (`unload()`: forget hook, `POST /api/engine/unload` on quit, atexit), only models Ollama reports as loaded. Ollama on 127.0.0.1, no note text sent | step 4: qa uses `answer_model()` |
| `app/db.py` | in-memory SQLite index: Files/Chunks/Groups, contentless FTS5 keyword search, vectors (Python dict until sqlite-vec loads), `passage()` re-reads text and refuses changed files; revoke + forget hooks; `topics()` names groups lazily | — (`search.py` calls it) |
| `app/session.py` | "forget everything": modules register a reset with `on_forget`; `forget()` runs them all | every module that holds session data |
| `app/extractions.py` | extracts to-dos and decisions from indexed passages (text re-read from the file): `todos()` returns checkbox items, `decisions()` returns `## Decision` sections and `DECISION:` labels | — |
| `app/dates.py` | finds lines that name a date ("24 Nov", "2026-12-01", "next Friday" read against the note's date) for `/api/upcoming`; vague phrases skipped; nothing stored | — |
| `app/trust.py` | read-only checks: app processes' sockets (psutil), files in the app's data folders (`prefs.json` is expected, anything else is flagged) | — |
| `app/routes_trust.py` | `/api/audit`, `/api/trust/network`, `/api/trust/saved`, `/api/trust/storage`, `DELETE /api/session` | — |
| `app/citations.py` | citation checker: verifies each cited quote is in its chunk, drops unbacked claims, returns NO_SUPPORT if none survive. Pure, no I/O | step 4: called by `qa.py` |
| `tests/test_citations.py` | quote matching, rejections, claim filtering, one real sample note | — |
| `tests/test_trust.py` | audit rules, forget, connection kinds, storage report, routes need token | — |
| `tests/conftest.py` | points `prefs.json` at a temp folder for every test | — |
| `tests/test_privacy_edges.py` | forget clears everything, revoke hook, symlink/deny/missing-folder edge cases, no note text in log or prefs | — |
| `tests/test_privacy_index.py` | revoke and forget through the API on the real index, revoke/forget during a rebuild leave no vectors or topics, model unload | — |
| `tests/test_ingest.py` | TXT/MD/DOCX chunk boundaries; broken files skipped and logged with no content, no half-read chunks left + blocked paths and symlink escapes | — |
| `app/notes.py` | Capture: `open_file` (path-checked, opens in the default app, never edits) and `create_note` (new `.md` only, never overwrites, denylist-checked) | — |
| `app/search.py` | build the index from allowed folders (`reindex`: keyword at once, vectors + groups in a background thread, `status()` for progress), hybrid search (keyword + meaning, RRF), source cards re-read from files; keyword only without Ollama | 2b: `qa.py` uses `rank()` + `source()` |
| `app/changes.py` | "Changes": pairs passages from different dated notes (most similar first, max 12), asks the answer model if the newer one replaces or contradicts the older, keeps only findings whose two quotes are really in the files. Background scan once the index is ready; memory only; cleared on reindex/forget, revoked files filtered. `flag()` sets the search badge | — |
| `tests/test_changes.py` | verified quotes only, injected/unknown replies ignored, search flags, forget/revoke, Ollama down | — |
| `tests/test_notes.py` | open: allowlist/denylist enforced; new note: tracked/untracked, never overwrites, no text in audit | — |
| `tests/test_search.py` | folder walk, search shape, Ollama fallback, stale files, revoke/forget, `/api/index` + `/api/search` | — |
| `tests/test_db.py` | keyword search, no text stored, FTS syntax safe, revoke/forget empty the index, changed file not shown, groups and meaning search | — |
| `tests/test_group.py` | clustering, one naming call per group, injected/bad topics fall back, Ollama local only (Ollama faked) | — |
| `tests/test_no_network.py` | blocks non-loopback connects and DNS, runs a whole session through the API; includes `/api/ask` with inference mocked | step 5: real-app storage and offline demo checks |
| `tests/test_prefs.py` | saved folders/settings, paths only, allowlist, restore, forget, disk check | — |
| `tests/test_permissions.py` | grants, protected paths, symlink escape, revoke | — |
| `tests/test_health.py` | token required; health payload; dev origin blocked unless dev mode | add a test file per module |
| `app/qa.py` | Local Ollama Q&A using retrieved excerpts; generates claims and validates citations through `citations.py`. Uses `models.answer_model()` | Test full desktop workflow |
| `tests/test_extractions.py` | to-do and decision extraction; full passage sent to the model | — |
| `tests/test_qa.py` | Tests valid citations, missing evidence and fabricated quotations using mocked Ollama responses | Add further edge cases |
| `tests/test_ask.py` | Tests `POST /api/ask` integration with mocked search and Q&A results | Test real authenticated workflow |
