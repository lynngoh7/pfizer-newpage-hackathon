# Project status

Build order follows the brief. Update this file in the same change as the code.

Legend: ✅ done · 🔧 in progress · ⬜ not started

## Step 1 — App shell + sidecar ✅
- ✅ Tauri v2 config: strict CSP, `core:default` capability only, no network plugins
- ✅ Rust launcher: per-launch 256-bit session token, free localhost port, spawns backend, kills it on exit, `get_session` command
- ✅ React layout: fixed sidebar, wide search bar, home with reserved widget grid, placeholder views, Settings page showing engine health
- ✅ FastAPI sidecar: 127.0.0.1 only, refuses to start without token, 401 on every route without bearer token, `/api/health`
- ✅ Backend tests (`backend/tests/test_health.py`), dev scripts, PyInstaller spec
- ⬜ Not yet compiled on a machine with Rust (`cargo` was missing). First person with `rustup`: run `npm run tauri dev` and fix anything that breaks.
- ⬜ Real app icons (`npm run tauri icon <1024px.png>`); current icon is a 1×1 placeholder

## Step 2 — Folder access + ingest ⬜
Files to create/edit: `backend/app/permissions.py`, `backend/app/ingest.py`, `backend/app/db.py`, routes in `api.py`, `src/pages/Settings.tsx`, Tauri dialog plugin for folder picker.
- ⬜ Allowlist/denylist with one `resolve_and_check(path)` function (follows symlinks)
- ⬜ Folder picker in Settings → add/remove folders
- ⬜ Parse PDF (PyMuPDF), DOCX/TXT/MD (markitdown) → chunks with path, page/heading, offsets
- ⬜ SQLCipher DB, chunk metadata table

## Step 3 — Keyword search ⬜
- ⬜ FTS5 table + `search.py` keyword search
- ⬜ Results UI: source cards (file, path, snippet, open-file button)

## Step 4 — Q&A with verified citations ⬜
- ⬜ Ollama client (localhost only), untrusted-data delimiting, citation verification, "No supporting notes found."

## Step 5 — Audit log ⬜
## Step 6 — Decisions/to-dos, conflicts ⬜
## Step 7 — P1: embeddings + hybrid search, summary screen, clear data ⬜

## Performance notes
- Frontend bundle after step 1: ~148 kB JS (48 kB gzip). Keep an eye on this; lazy-load non-home views when they grow.

## Where to start (pick one, say so in the team chat, update this file)

1. **Compile the desktop shell** — install Rust (`curl https://sh.rustup.rs -sSf | sh`), run `npm install && npm run tauri dev`. Fix any compile errors in `src-tauri/`. Confirm the sidebar shows "Local engine ready". Then replace the placeholder icon.
2. **Step 2a: folder permissions (backend)** — create `backend/app/permissions.py` with the allowlist/denylist and a single `resolve_and_check(path)` that follows symlinks and rejects `.ssh`, `.env`, keychains, etc. Add `GET/POST/DELETE /api/folders`. Tests first: symlink escape, denylist hit, revoke.
3. **Step 2b: folder picker (frontend + Tauri)** — add `tauri-plugin-dialog`, `dialog:allow-open` in `capabilities/default.json`, and a folder list with add/remove in `src/pages/Settings.tsx` calling the routes from 2a.
4. **Step 2c: ingest** — `backend/app/ingest.py`: walk allowed folders, parse PDF (PyMuPDF), DOCX/TXT/MD (markitdown), chunk with path, page/heading and char offsets. Store in `db.py` (SQLCipher). Benchmark on a folder of ~200 files and note the time here.

Rules of the road: run `backend/.venv/bin/pytest` and `npm run build` before every commit; add a row to `docs/FILES.md` for every new file; keep every file access behind `resolve_and_check`.
