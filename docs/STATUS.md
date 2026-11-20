# Project status

What is done, what is next. Update this file in the same change as your code.

✅ done · 🔧 in progress · ⬜ not started

## The plan in one paragraph

Build one demo moment end to end: the manager asks about a decision made weeks ago, and the app finds it, shows the newer note that changed it, and cites both. Everything stays in memory for the session. Nothing is written to disk. A Trust panel lets the user see that for themselves.

## CI ✅
- ✅ PR template (`.github/pull_request_template.md`): what/why, how to test, checklist (tests, build, comments, docs, privacy rules)
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
- ✅ `permissions.py` with `resolve_and_check(path)` (follows symlinks, blocks `.ssh`, `.env`, keychains). ⬜ Every file read must go through it (ingest)
- ✅ Backend `GET/POST/DELETE /api/folders`
- ✅ Folder list and settings saved to `prefs.json` (`prefs.py`, paths and allowlisted settings only); restored on launch, deleted by "Forget everything". `GET/PUT /api/settings`, `GET /api/trust/saved`
- ✅ Folder/file picker (`components/FolderAccess.tsx`) on the **Privacy page**, first section. The list is saved, so it is back on the next launch
- ✅ Folder add/remove/blocked are logged (`permissions.grant_path`/`revoke_path`; launch restore logs "restored" or "missing or blocked on launch")
- 🟡 Revoke drops chunks: hook ready (`permissions.on_revoke("index", fn)`, fn(path) -> count). **db.py must register it**; tests in `tests/test_privacy_edges.py`
- 🔧 Read PDF (pypdf) and DOCX / TXT / MD (markitdown), split into chunks with path and start/end line (page for PDFs). TXT/MD/PDF chunking on `ingest` branch; skip unreadable files next
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
- ⬜ Test in the real app (`npm run tauri dev`): confirm "Saved to disk: Folder list and settings only" after a session with incognito on. Delete old dev leftovers first: `rm -rf ~/Library/Caches/local-notes-assistant ~/Library/WebKit/local-notes-assistant`
- ⬜ Unload the Ollama model on forget (register in `session.py` once the Ollama client exists, step 4)
- ⬜ Rehearse the "turn Wi-Fi off" demo

## Settings + accessibility ✅
Nothing in Settings is saved (that would put a file on disk). Accessibility follows the Mac's own settings for the same reason.
- ✅ Settings page: engine, AI model picker (one fixed model until step 4), indexing placeholder (step 2c), built-in safety facts, forget everything (always last)
- ✅ Follows macOS appearance, Increase contrast, Reduce motion. ⌘+ / ⌘− change text size (`zoomHotkeysEnabled`, needs `core:webview:allow-set-webview-zoom`)
- ✅ Keyboard focus ring on every control; `<main>` and `<nav>` landmarks; `aria-current` on the open page; engine status announced to VoiceOver
- ✅ Sidebar icons (Lucide paths inlined, no icon package; decorative, hidden from VoiceOver). Licence in `docs/THIRD_PARTY.md`
- ⬜ Step 4: list installed Ollama models in the picker and show loaded/unloaded; confirm the answer model (placeholder `llama3.2:3b`)
- ⬜ Step 2c: indexing card (files read, passages, skipped, re-index)
- ⬜ Check in the real app with VoiceOver (⌘F5) and with Increase contrast on

## Step 6 — Decisions, to-dos, conflicts ⬜
- ⬜ Pull decisions and to-dos out of notes
- ⬜ Flag notes that disagree, and newer notes that replace older ones ("superseded" badge)

## Step 7 — Later ⬜
- ⬜ Search by meaning (embeddings via `nomic-embed-text`, hybrid with keyword). Build FTS first, embed in the background, because the index is rebuilt on every launch
- ⬜ Summary page for managers

## Performance notes
- Frontend bundle after step 1: about 148 kB JS (48 kB gzipped)
- After Settings + sidebar icons: about 154 kB JS (50 kB gzipped)
- Topic grouping, 37 chunks from the main sample notes, Intel Mac, 32 GB:
  - One `llama3.2:3b` call per chunk: about 100 s, poor labels. Too slow: `long standup log.md` alone is 901 chunks
  - `nomic-embed-text` for all chunks in one call (about 5 s), group by similarity ≥ 0.75, then one LLM call to name each group: about 25 s, 6 sensible groups. 0.6 and 0.7 merge too much
  - Merging small chunks first would cut the count further

## Who does what (Fri 20 – Sun 22 Nov)

Tick a box here in the same PR as the code. Sunday evening is for recording the video.

**E: reading notes and search** (step 2c, 3)
- 🔧 1a. `ingest.py`: text extraction (Sat). TXT/MD/PDF chunking works on the `ingest` branch (29 sample files → 954 chunks). Next: skip unreadable files (`corrupt.pdf`, `password protected.pdf`, `latin1 windows.txt` crash it now) and read through `resolve_and_check`
- ⬜ 1b. `db.py`: in-memory DB and chunk metadata (Sat)
- ⬜ 1c. FTS5 keyword search, `search.py` (Sat), needs 1a, 1b
- ⬜ 1d. Ingest and search API endpoints (Sat), needs 1c
- ⬜ 1e. Tests: parsing, permissions, cleanup (Sun)
- ⬜ 1f. Group chunks by topic (`Groups` table, see `docs/DB_DESIGN.md`). Use embeddings, not one LLM call per chunk (see Performance notes)

**S: answers and decisions** (step 4, 6)
- ⬜ 2a. Check local Ollama model and inference (Fri)
- ⬜ 2b. `qa.py` with source-aware prompts (Sat), needs 2a; real chunks from 1c
- ⬜ 2c. Wire in `citations.py` and "No supporting notes found." (Sat), needs 2b
- ⬜ 2d. Compare old decisions with newer notes (Sun), needs 1c, 2c
- ⬜ 2e. Unload the model on quit and forget; AI tests (Sun), needs 2a

**L: results UI** (step 3, 4, 6)
- ⬜ 3a. Results page with mock data (Sat)
- ⬜ 3b. Source cards and file excerpts (Sat)
- ⬜ 3c. Connect search and questions to the backend (Sat), needs 1d, 2c
- ⬜ 3d. Show decision changes and error states (Sun), needs 2d
- ⬜ 3e. Demo polish and accessibility check (Sun, P1)

**C: privacy and trust** (step 2, 5)
- ✅ 4a. Audit events for folder add/remove (Sat)
- ⬜ 4b. Revoking a folder drops its chunks (Sat), needs 1b. Hook `permissions.on_revoke` ready; db.py registers it
- ⬜ 4c. Verify Forget everything clears everything (Sat), needs 1b; recheck after 2e. Grants, prefs, log tested; index part waits on 1b
- ⬜ 4d. Test storage, network and offline claims (Sun), needs 1d, 2c. Started: `tests/test_no_network.py` covers current routes
- ⬜ 4e. Edge-case tests and trust demo (Sun), needs everything above

### Dependencies
- **Critical path:** 1a/1b → 1c → 1d → 3c → 2d → 3d → demo. E's Saturday work blocks the most people, so land 1b first.
- **Agree two shapes on Friday** so nobody waits: the chunk record from `db.py` (id, path, page/heading, start, end) and the JSON for search and answer responses. Then 2b, 3a, 3b and 4b can start against stubs.
- `db.py` must register `session.on_forget("index", ...)` and offer "drop chunks for folder"; 4b and 4c depend on it.
- 2e must register the model unload in `session.py`; 4c re-checks it.
- No dependencies: 2a, 3a, 4a, so start those first.

Rules: work on a branch, never push to `main`; conventional commit messages; open a PR and fill in the template; merge only when CI is green. Run the backend tests, `npm run build` and `sh scripts/privacy-guard.sh` before pushing (README §3). Add a row to `docs/FILES.md` for every new file. Every file read goes through `resolve_and_check`. Comments: one short line saying *why*, where a newcomer would get stuck; safety checks name the rule they enforce.

### Early risk to test
Loading sqlite-vec needs `enable_load_extension`. The Python that ships with macOS does not support it. Use Python from python.org or Homebrew, or add `pysqlite3-binary`.
