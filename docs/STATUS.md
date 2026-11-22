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

## Step 2 — Folder access + reading notes ✅
New files: `backend/app/permissions.py`, `ingest.py`, `db.py`. Edit: `api.py`, `src/pages/Privacy.tsx` (folder section).
- ✅ `permissions.py` with `resolve_and_check(path)` (follows symlinks, blocks `.ssh`, `.env`, keychains). Every file read in ingest goes through it
- ✅ Backend `GET/POST/DELETE /api/folders`
- ✅ Folder list and settings saved to `prefs.json` (`prefs.py`, paths and allowlisted settings only); restored on launch, deleted by "Forget everything". `GET/PUT /api/settings`, `GET /api/trust/saved`
- ✅ Folder/file picker (`components/FolderAccess.tsx`) on the **Privacy page**, first section. The list is saved, so it is back on the next launch
- ✅ Folder add/remove/blocked are logged (`permissions.grant_path`/`revoke_path`; launch restore logs "restored" or "missing or blocked on launch")
- ✅ Revoke drops chunks: `db.py` registers `permissions.on_revoke("index", db.drop_under)`; tests in `tests/test_db.py`
- ✅ Read PDF (pypdf) and DOCX / TXT / MD (markitdown), split into chunks with path and start/end line (page for PDFs). Unreadable files are skipped
- ✅ In-memory SQLite (`db.py`, schema in `docs/DB_DESIGN.md`): path, mtime, hash, noteDate, offsets, groups. No readable note text in any table
- ✅ Index rebuilds from restored folders on launch and after a folder is added
- ✅ Audit log `audit.py` (in memory). **Ingest/permissions must call** `audit.record("read" | "skipped" | "blocked" | "folder_added" | "folder_removed", path=..., outcome="short reason")`. Never pass note text
- ✅ `db.py` registers `session.on_forget("index", db.clear)`. **Every new module holding session data must register too**
- ✅ `sample_notes/`: fictional notes for the demo moment plus edge cases. Guide and expected answers in `docs/SAMPLE_NOTES.md`. Run `scripts/make_sample_notes.py` after cloning

## Step 3 — Keyword search ✅
- ✅ FTS5 table (contentless) in `db.py`, `db.keyword(q)`. `search.py` merges keyword + meaning
- ✅ Results page with source cards and excerpts; search submits to `/api/index` and `/api/search` (PR #23). Citations link only to source cards that exist
- ✅ Requests wait for the backend at launch (up to 20 s) instead of showing "TypeError: Load failed"

## Step 4 — Questions with verified citations 🔧
- ✅ `qa.py`: local Ollama question answering using `models.answer_model()`. Source-aware prompts treat notes as untrusted data and require exact quotations.
- ✅ `citations.py`: validates model-generated quotations against retrieved excerpts. Unsupported claims are rejected; no valid evidence → "No supporting notes found."
- ✅ `POST /api/ask`: connects search results to `qa.py` and returns structured answers, verified citations and source metadata.
- ✅ Tests: `test_qa.py` covers valid evidence, missing evidence and fabricated citations. `test_ask.py` verifies API integration.
- ✅ Live Qwen3 4B Instruct tests: valid citation accepted; unsupported question returns no evidence.
- ✅ Model lifecycle delegated to `models.py`: models remain warm during the session and are unloaded on quit or "Forget everything".
- ⬜ Verify the full question-answering workflow through the desktop UI.

## Step 5 — Trust panel 🔧
Covers 20 of the 50 judging points. Sidebar → **Privacy**.
- ✅ Activity log: live, newest first, paths and actions only (`GET /api/audit?after=N`)
- ✅ Stored on disk: checks the app's data, cache, log and WebKit folders (`GET /api/trust/storage`)
- ✅ Network: every socket of the engine, the app and Ollama, marked local or outside (`GET /api/trust/network`, uses psutil). Includes "check it yourself" steps (Wi-Fi off, `lsof`)
- ✅ Forget everything: confirm step, then shows what was cleared and re-checks the disk (`DELETE /api/session`). Same button in Settings
- ✅ Webview runs `incognito` and every API response is `Cache-Control: no-store`. Before this, WebKit kept an HTTP cache in `~/Library/Caches/local-notes-assistant`, which would have kept copies of note passages
- ⬜ Test in the real app (`npm run tauri dev`): confirm "Saved to disk: Folder list and settings only" after a session with incognito on. Delete old dev leftovers first: `rm -rf ~/Library/Caches/local-notes-assistant ~/Library/WebKit/local-notes-assistant`
- ✅ Unload the Ollama models on forget (`session.on_forget("model", models.unload)`) and on quit (launcher calls `POST /api/engine/unload` before stopping the backend, `atexit` as backup). Any new model must be listed in `models._ours()`
- ⬜ Rehearse the "turn Wi-Fi off" demo

## Settings + accessibility ✅
Nothing in Settings is saved (that would put a file on disk). Accessibility follows the Mac's own settings for the same reason.
- ✅ Settings page: engine, AI model picker (one fixed model until step 4), indexing placeholder (step 2c), built-in safety facts, forget everything (always last)
- ✅ Follows macOS appearance, Increase contrast, Reduce motion. ⌘+ / ⌘− change text size (`zoomHotkeysEnabled`, needs `core:webview:allow-set-webview-zoom`)
- ✅ Keyboard focus ring on every control; `<main>` and `<nav>` landmarks; `aria-current` on the open page; engine status announced to VoiceOver
- ✅ Sidebar icons (Lucide paths inlined, no icon package; decorative, hidden from VoiceOver). Decisions and To-dos have their own icons (list-checks, square-check). Licence in `docs/THIRD_PARTY.md`
- ⬜ Step 4: list installed Ollama models in the picker and show loaded/unloaded; confirm the answer model (`qwen3:4b-instruct`, chosen 2026-11-21)
- ⬜ Step 2c: indexing card (files read, passages, skipped, re-index)
- ⬜ Check in the real app with VoiceOver (⌘F5) and with Increase contrast on

## Capture: open in editor + new note ✅
- Source cards have **Open in editor**: the file opens in its default app (path-checked with `resolve_and_check`). The app never edits it. When the window regains focus after an Open, it re-indexes and re-runs the search, so edits show up.
- Sidebar **New note**: saves a new `.md` file (`YYYY-MM-DD Title.md`). In an allowed folder it is searchable straight away; in another folder it is not tracked. Never overwrites. The audit log shows `open_in_editor` / `note_created` with paths only.
- Code: `backend/app/notes.py`, `POST /api/files/open`, `POST /api/notes`, `src/pages/NewNote.tsx`. Tests: `backend/tests/test_notes.py`.

## Step 6 — Decisions, to-dos, conflicts 🔧
- ⬜ Pull decisions and to-dos out of notes
- ✅ To-dos can be ticked on the To-dos page. Ticks are in memory for the session only: never written to the note or to disk A clear notice says so; "Edit in note" opens the file in the user's own editor (path-checked, audit-logged)
- ✅ Flag notes that disagree, and newer notes that replace older ones. Sidebar page **Changes** (gentle wording and icon: a changed note is normal, not an error; Markdown symbols stripped from quotes and titles so they read as plain text). Search cards get the "Superseded" / "Newer note" / "Conflict" badge once the scan is done
  - How: after meaning search is ready, a background scan pairs passages from different notes dated in their file name (most similar first, at most 12 pairs; findings show as they arrive). The answer model says replaces / contradicts / none and quotes both; Python keeps a finding only if both quotes are really in the files. Memory only; cleared on reindex and forget
  - Undated files (e.g. `todo.md`) are left out: their date comes from mtime, which changes on copy
  - Code: `backend/app/conflicts.py`, `GET/POST /api/conflicts`, `src/pages/Conflicts.tsx`. Tests: `backend/tests/test_conflicts.py`

## Step 7 — Later ⬜
- ✅ Search by meaning (`nomic-embed-text` vectors, merged with keyword in `search.py`). ⬜ Embed in the background so keyword search is ready first on launch
- ⬜ Summary page for managers

## Packaged app ✅
- ✅ `sh scripts/build-sidecar.sh` then `npm run tauri build` makes `Local Notes Assistant.app` (about 51 MB): double-click to open, no terminal. The backend is bundled inside and starts and stops with the app
- ✅ Tested on macOS (Intel): the built backend reads all `sample_notes/` and search works; quitting the app stops the backend
- ✅ `sh scripts/build-app.sh` builds and installs the app: Mac → /Applications, Windows → silent installer (Start menu), Linux → .deb/.rpm (app menu); `--install` skips the build. Re-tested on macOS (Intel): installs, starts, backend stops on quit
- ✅ Windows fixes: backend `.exe` naming, no console window, whole backend process tree stopped on quit
- ⬜ Windows, Linux and Apple Silicon builds not yet run: run the **Build app** workflow (`.github/workflows/build-app.yml`) once the branch is pushed. Install steps per OS: `docs/INSTALL.md`
- ⚠ First launch takes about 15 s before the engine dot goes green (the backend unpacks itself; macOS scans the new binary). Later launches are faster
- ⚠ Not signed: the first time, right-click the app → Open. Ollama is still installed separately
- ⬜ sqlite-vec hidden imports when step 7 lands

## Performance notes
- Index build on all sample notes, Intel Mac (2026-11-21). Neighbouring small chunks are now merged up to 1000 characters (`ingest.mergeSmall`):
  - Before: 950 chunks. Keyword ready 0.8 s, embedding 180 s, grouping + naming 13 s. Total 194 s
  - After: 137 chunks. Keyword ready 0.4 s, embedding 45 s, grouping + naming 27 s. Total 72 s, all after the search is already usable
  - Plus lazy group naming (`db.topics()`): grouping 0 s. Total 46 s, almost all embedding
- Frontend bundle after step 1: about 148 kB JS (48 kB gzipped)
- After Settings + sidebar icons: about 154 kB JS (50 kB gzipped)
- Topic grouping, 37 chunks from the main sample notes, Intel Mac, 32 GB:
  - One `llama3.2:3b` call per chunk: about 100 s, poor labels. Too slow: `long standup log.md` alone is 901 chunks
  - `nomic-embed-text` for all chunks in one call (about 5 s), group by similarity ≥ 0.75, then one LLM call to name each group: about 25 s, 6 sensible groups. 0.6 and 0.7 merge too much
  - `group.py` on all 953 sample chunks (incl. edge cases): about 167 s, 12 groups. Most of it is `long standup log.md` (901 chunks). Merging small chunks first would cut this

## Who does what (Fri 20 – Sun 22 Nov)

Tick a box here in the same PR as the code. The list below is what was planned on Friday; the remaining work from Saturday 21 Nov is under **Remaining work**.

**E: reading notes and search** (step 2c, 3)
- ✅ 1a. `ingest.py`: TXT/MD/PDF/DOCX chunking; every read goes through `resolve_and_check` (symlinks out of the folder are blocked and logged); broken files skipped. `ingestAllowed()` walks the allowed folders, skipping hidden files
- ✅ 1b. `db.py`: in-memory DB, contentless FTS5, vectors, revoke/forget hooks. Sample notes: 26 files, 950 chunks indexed in 0.4 s (no Ollama). `db.build(chunks)` runs files → FTS → vectors → groups. Not yet called from an endpoint (1d)
- ✅ 1c. `search.py`: keyword (FTS5) + meaning (vectors) merged by reciprocal rank fusion; snippets re-read from the file. Without Ollama it falls back to keyword only
- ✅ 1d. `POST /api/index` returns once keyword search is ready (under 1 s on all sample notes); meaning search and topic groups build in the background. `GET /api/index` gives counts plus `phase` (meaning / grouping / ready / keyword_only) and `done`/`total` for a progress bar. `GET /api/search?q=` (shape in `API_SHAPES.md`)
- ✅ 1e. Tests: `test_ingest.py` (blocked paths, symlink escape), `test_search.py` (walk, search, fallback, stale file, revoke, forget, API)
- ✅ 1f. Group chunks by topic: `group.py`; `db.build` stores groups and keeps the vectors for search by meaning. Groups are named lazily by `db.topics()` (placeholder "Group N" until a view asks), so indexing makes no LLM calls
- ✅ Models warmed at startup and kept loaded (`models.py`); unloaded on quit and Forget everything (registered in `session.py`). Warm-up takes about 6 s in the background

**S: answers and decisions** (step 4, 6)
- ✅ 2a. Verified local Ollama inference and GPU acceleration. Tested `llama3.2:3b` and `qwen3:4b-instruct`; selected Qwen3 Instruct for more reliable citations and concise responses.
- ✅ 2b. Implemented `qa.py` with source-aware prompts and structured JSON responses. Uses `models.answer_model()` for model selection. On `feature/ai-qa`, awaiting merge.
- ✅ 2c. Integrated `citations.py` and no-evidence handling. Added `POST /api/ask` to connect `search.py` with `qa.py`. Live citation and no-evidence tests passed.
- ⬜ 2d. Compare old decisions with newer notes (reassigned to Eoin).
- ✅ 2e. Model lifecycle managed by `models.py`: kept warm during the session and unloaded on quit or "Forget everything". Removed per-request unloading from `qa.py`.

**L: results UI** (step 3, 4, 6)
- ✅ 3a. Results page with mock data (Sat)
- ✅ 3b. Source cards and file excerpts (Sat)
- 🔧 3c. Keyword and natural-language search call `/api/index` and `/api/search`; question answers await the QA API from 2c
- ⬜ 3d. Show decision changes and error states (Sun), needs 2d
- 🔧 3e. Results-page polish adds visible citation targets, announced source counts, higher text contrast and formatted Markdown excerpts; VoiceOver announces the source count, while citation-jump testing awaits an answer with citations

**C: privacy and trust** (step 2, 5)
- ✅ 4a. Audit events for folder add/remove (Sat)
- ✅ 4b. Revoking a folder drops its chunks, vectors, topics and search results at once, also mid-rebuild (`tests/test_privacy_index.py`)
- ✅ 4c. Forget everything clears grants, prefs, log, index and unloads the model, also mid-rebuild. Fixed: a forget or revoke during the minutes-long embedding step used to put vectors and topics back
- 🔧 4d. Test storage, network and offline claims (Sun). `tests/test_no_network.py` covers every route incl. index, search, model unload; ⬜ add the ask route when 2c lands (blocked on 2c)
- ⬜ 4e. Edge-case tests and trust demo (Sun), needs everything above

### Remaining work (from Sat 21 Nov)

Prototype done by Saturday night, Sunday midday at the latest. The second half of Sunday is for the demo and video.

**E: decisions**
- ⬜ Pull decisions and to-dos out of notes (P0, Sat)
- ⬜ Compare old decisions with newer notes (P0, Sat)
- ⬜ Display decision changes and error states (P0, Sun am)
- ⬜ Run edge-case tests against answers: injected instructions, empty and broken notes (P0, Sun am)

**S: answers, demo device**

- 🔧 Merge `feature/ai-qa` into `main` (PR awaiting approval).
- ✅ Integrate citation validation and no-evidence handling.
- ✅ Implement `POST /api/ask` and integrate with existing search.
- ✅ Verify local Qwen3 4B Instruct inference with valid and missing evidence.
- ✅ Backend tests: 91 passed; frontend production build passed.
- ⬜ Build and run the complete application on the demo device with fictional sample notes.


**L: results UI**
- ✅ Build functional results page with mock data (P0, Sat)
- ✅ Display citation/source cards and file excerpts (P0, Sat)
- 🔧 Connect question/search flow to backend (P0, Sat). Search done (PR #23); questions wait for the ask route
- 🔧 Complete demo UI polish and accessibility check (P1, Sun am); VoiceOver count verified, citation-jump test awaits an answer with citations

**C: privacy and trust, demo**
- ✅ Merge feat/privacy-index, feat/search, db, ingest into main (P0, Sat). PRs #15–#17
- 🔧 Test storage, network and offline privacy claims (P0, Sat). Network test covers every route; ⬜ ask route (blocked on S), ⬜ real-app storage check (Step 5)
- ✅ Capture: Open in editor + New note (PR #24). See **Capture** above
- ✅ Packaged desktop app for Mac, Windows and Linux (PR #19)
- ⬜ Prepare trust demo and rehearse it with Wi-Fi off on the demo device (P0, Sun pm)
- ⬜ Record the demo video and send the submission by 23:59 (P0, Sun pm)

If E falls behind, L takes "Display decision changes and error states" (it sits on the results page).

### Dependencies
- **Critical path:** C's merges → S's ask route with citations → L connects search and questions → E's decision changes on the results page → S runs it on the demo device → C rehearses and records. Everything up to L's connection should land on Saturday.
- **Merges first (C, S, Sat morning):** L can't connect to the backend and E can't build on `search.py` until `feat/search`, `db`, `ingest` and `feature/ai-qa` are on `main`.
- **Ask route (S) blocks** L's "Connect question/search flow" and the ask-route test in C's network checks.
- **Decision extraction (E) blocks** "Compare old decisions" and "Display decision changes". Agree the decision JSON with L on Saturday so the page can be built against a stub.
- **Demo device (S, Sun am)** needs everything merged. C's rehearsal and the video run on that device.
- No dependencies: L's mock results page, E's decision extraction, C's privacy tests. Start those first.

Rules: work on a branch, never push to `main`; conventional commit messages; open a PR and fill in the template; merge only when CI is green. Run the backend tests, `npm run build` and `sh scripts/privacy-guard.sh` before pushing (README §3). Add a row to `docs/FILES.md` for every new file. Every file read goes through `resolve_and_check`. Comments: one short line saying *why*, where a newcomer would get stuck; safety checks name the rule they enforce.

### Early risk to test
Loading sqlite-vec needs `enable_load_extension`. The Python that ships with macOS does not support it. Use Python from python.org or Homebrew, or add `pysqlite3-binary`.
