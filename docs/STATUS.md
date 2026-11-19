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
New files: `backend/app/permissions.py`, `ingest.py`, `db.py`. Edit: `api.py`, `src/pages/Privacy.tsx` (folder section).
- ⬜ One function `resolve_and_check(path)` that every file read goes through (follows symlinks, blocks `.ssh`, `.env`, keychains)
- ⬜ Folder picker on the **Privacy page** (first section, placeholder is there). Grants last for the session only, not saved to disk
- ⬜ Read PDF (PyMuPDF) and DOCX / TXT / MD (markitdown), split into chunks with path, page or heading, and character offsets
- ⬜ In-memory SQLite (`:memory:`) holding path, mtime, hash and offsets. **No note text on disk, ever**
- ✅ Audit log `audit.py` (in memory). **Ingest/permissions must call** `audit.record("read" | "skipped" | "blocked" | "folder_added" | "folder_removed", path=..., outcome="short reason")`. Never pass note text
- ⬜ **Every module holding session data must register** `session.on_forget("index", fn)` (fn clears it, returns a count). Otherwise "forget everything" misses it
- ✅ `sample_notes/`: fictional notes for the demo moment plus edge cases. Guide and expected answers in `docs/SAMPLE_NOTES.md`. Run `scripts/make_sample_notes.py` after cloning

## Step 3 — Keyword search ⬜
- ⬜ FTS5 table in the same in-memory database, `search.py`
- ⬜ Results page: source cards (file, path, snippet re-read from the file, open-file button)

## Step 4 — Questions with verified citations ⬜
- ⬜ Ollama client (localhost only). Note text goes in clearly marked "untrusted data" blocks
- ✅ Citation checker `citations.py`: every quote must appear in the chunk it cites (exact after folding case, spacing, smart quotes, accents, Markdown, `...` gaps; no fuzzy matching). Unbacked claims are dropped; none left → "No supporting notes found." qa.py calls `check_answer` with the chunks it put in the prompt
- ⬜ Keep the model warm during the session, unload on quit and "forget everything"

## Step 5 — Trust panel 🔧
Covers 20 of the 50 judging points. Sidebar → **Privacy**.
- ✅ Activity log: live, newest first, paths and actions only (`GET /api/audit?after=N`)
- ✅ Stored on disk: checks the app's data, cache, log and WebKit folders (`GET /api/trust/storage`)
- ✅ Network: every socket of the engine, the app and Ollama, marked local or outside (`GET /api/trust/network`, uses psutil). Includes "check it yourself" steps (Wi-Fi off, `lsof`)
- ✅ Forget everything: confirm step, then shows what was cleared and re-checks the disk (`DELETE /api/session`). Same button in Settings
- ✅ Webview runs `incognito` and every API response is `Cache-Control: no-store`. Before this, WebKit kept an HTTP cache in `~/Library/Caches/local-notes-assistant`, which would have kept copies of note passages
- ⬜ Test in the real app (`npm run tauri dev`): confirm "Stored on disk: Nothing" after a session with incognito on. Delete old dev leftovers first: `rm -rf ~/Library/Caches/local-notes-assistant ~/Library/WebKit/local-notes-assistant`
- ⬜ Unload the Ollama model on forget (register in `session.py` once the Ollama client exists, step 4)
- ⬜ Rehearse the "turn Wi-Fi off" demo

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
3. **Step 2b, folder picker (UI).** Add `tauri-plugin-dialog`, allow `dialog:allow-open` in `capabilities/default.json`, folder list with add and remove in the "Folders the app can see" section of `src/pages/Privacy.tsx` (moved from Settings so the whole privacy story is on one page)
4. **Step 2c, reading notes.** Write `ingest.py` and `db.py` (in memory). Time it on about 200 files and note the result here

Rules: run the backend tests and `npm run build` before every commit. Add a row to `docs/FILES.md` for every new file. Every file read goes through `resolve_and_check`. Comments: one short line saying *why*, where a newcomer would get stuck; safety checks name the rule they enforce.

### Early risk to test
Loading sqlite-vec needs `enable_load_extension`. The Python that ships with macOS does not support it. Use Python from python.org or Homebrew, or add `pysqlite3-binary`.
