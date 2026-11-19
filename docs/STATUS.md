# Project status

What is done, what is next. Update this file in the same change as your code.

✅ done · 🔧 in progress · ⬜ not started

## The plan in one paragraph

Build one demo moment end to end: the manager asks about a decision made weeks ago, and the app finds it, shows the newer note that changed it, and cites both. Everything stays in memory for the session. Nothing is written to disk. A Trust panel lets the user see that for themselves.

## CI ✅
- ✅ GitHub Actions on every PR and push to main: backend `pytest` (Python 3.10), `npm ci && npm run build` (Node 22), privacy guard (`sh scripts/privacy-guard.sh`: no URLs except localhost in `src/` or `backend/app/`)

## Step 1 — App shell + backend ✅
- ✅ Desktop window (Tauri): strict CSP, no network plugins
- ✅ Launcher: new session token on every launch, starts and stops the backend
- ✅ UI: sidebar, search bar, home page, placeholder pages, Settings
- ✅ Backend: localhost only, refuses to start without a token, rejects requests without it
- ✅ Browser dev mode is allowed only when `NOTES_DEV=1` (never in packaged builds)
- ✅ Compiled and run on macOS (2026-11-15): window opens, backend starts on a random localhost port, sidebar shows the engine as ready. Only localhost ports open
- ⬜ Real app icon (`npm run tauri icon <1024px.png>`)

## Step 2 — Folder access + reading notes ⬜
New files: `backend/app/permissions.py`, `ingest.py`, `db.py`, `audit.py`. Edit: `api.py`, `src/pages/Settings.tsx`.
- ⬜ One function `resolve_and_check(path)` that every file read goes through (follows symlinks, blocks `.ssh`, `.env`, keychains)
- ⬜ Folder picker in Settings. Grants last for the session only, not saved to disk
- ⬜ Read PDF (PyMuPDF) and DOCX / TXT / MD (markitdown), split into chunks with path, page or heading, and character offsets
- ⬜ In-memory SQLite (`:memory:`) holding path, mtime, hash and offsets. **No note text on disk, ever**
- ⬜ Audit log (in memory): every file read gets a line with time, action, path, query. No note content
- ⬜ `sample_notes/`: fictional manager notes built around the demo moment (a decision, its context, a newer note that changes it, a half-written update, a to-do list)

## Step 3 — Keyword search ⬜
- ⬜ FTS5 table in the same in-memory database, `search.py`
- ⬜ Results page: source cards (file, path, snippet re-read from the file, open-file button)

## Step 4 — Questions with verified citations ⬜
- ⬜ Ollama client (localhost only). Note text goes in clearly marked "untrusted data" blocks
- ⬜ Check every quoted citation really appears in the file. Show "No supporting notes found." when none survive
- ⬜ Keep the model warm during the session, unload on quit and "forget everything"

## Step 5 — Trust panel ⬜
Covers 20 of the 50 judging points. Do not leave it to the end.
- ⬜ Activity log page (from the step 2 audit log)
- ⬜ "Stored on disk right now" view: should list nothing
- ⬜ Network view: the only open sockets are localhost. Rehearse the "turn Wi-Fi off" demo
- ⬜ "Forget everything" button: drops the index, log and folder grants, with visible confirmation

## Step 6 — Decisions, to-dos, conflicts ⬜
- ⬜ Pull decisions and to-dos out of notes
- ⬜ Flag notes that disagree, and newer notes that replace older ones ("superseded" badge)

## Step 7 — Later ⬜
- ⬜ Search by meaning (embeddings via `nomic-embed-text`, hybrid with keyword). Build FTS first, embed in the background, because the index is rebuilt on every launch
- ⬜ Summary page for managers

## Performance notes
- Frontend bundle after step 1: about 148 kB JS (48 kB gzipped)

## Pick a task

Say which one in the team chat, then update this file.

1. **App icon.** Make a 1024px PNG and run `npm run tauri icon <file.png>`
2. **Step 2a, folder permissions (backend).** Write `permissions.py` and the `GET/POST/DELETE /api/folders` routes. Tests first: symlink escape, blocked folder, revoke
3. **Step 2b, folder picker (UI).** Add `tauri-plugin-dialog`, allow `dialog:allow-open` in `capabilities/default.json`, folder list with add and remove in Settings
4. **Step 2c, reading notes.** Write `ingest.py` and `db.py` (in memory). Time it on about 200 files and note the result here
5. **Sample notes.** Write `sample_notes/` for the demo moment (see step 2)

Rules: run the backend tests and `npm run build` before every commit. Add a row to `docs/FILES.md` for every new file. Every file read goes through `resolve_and_check`.

### Early risk to test
Loading sqlite-vec needs `enable_load_extension`. The Python that ships with macOS does not support it. Use Python from python.org or Homebrew, or add `pysqlite3-binary`.
