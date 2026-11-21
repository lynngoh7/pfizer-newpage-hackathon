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
- ✅ Audit log `audit.py` (in memory). **Ingest/permissions must call** `audit.record("read" | "skipped" | "blocked" | "folder_added" | "folder_removed", path=..., outcome="short reason")`. Never pass note text
- ✅ `db.py` registers `session.on_forget("index", db.clear)`. **Every new module holding session data must register too**
- ✅ `sample_notes/`: fictional notes for the demo moment plus edge cases. Guide and expected answers in `docs/SAMPLE_NOTES.md`. Run `scripts/make_sample_notes.py` after cloning

## Step 3 — Keyword search 🔧
- ✅ FTS5 table (contentless) in `db.py`, `db.keyword(q)`. `search.py` merges keyword + meaning
- ⬜ Results page: source cards (file, path, snippet re-read from the file, open-file button)

## Step 4 — Questions with verified citations 🔧
- 🔧 Ollama client `qa.py` (localhost only, on `feature/ai-qa`, not merged). System prompt treats note excerpts as untrusted data and asks for chunk ID + exact quote per claim. ⬜ Not yet called from an API route
- ✅ Citation checker `citations.py`: every quote must appear in the chunk it cites (exact after folding case, spacing, smart quotes, accents, Markdown, `...` gaps; no fuzzy matching). Unbacked claims are dropped; none left → "No supporting notes found." qa.py calls `check_answer` with the chunks it put in the prompt
- ✅ Unload on quit and "forget everything" (`models.unload`, keep_alive 0, only models that are loaded). ⬜ qa.py currently sends `keep_alive: "0"`: use `models.answer_model()` and drop that, `models.py` keeps it warm and unloads it

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
- ✅ Sidebar icons (Lucide paths inlined, no icon package; decorative, hidden from VoiceOver). Licence in `docs/THIRD_PARTY.md`
- ⬜ Step 4: list installed Ollama models in the picker and show loaded/unloaded; confirm the answer model (placeholder `llama3.2:3b`)
- ⬜ Step 2c: indexing card (files read, passages, skipped, re-index)
- ⬜ Check in the real app with VoiceOver (⌘F5) and with Increase contrast on

## Step 6 — Decisions, to-dos, conflicts ⬜
- ⬜ Pull decisions and to-dos out of notes
- ⬜ Flag notes that disagree, and newer notes that replace older ones ("superseded" badge)

## Step 7 — Later ⬜
- ✅ Search by meaning (`nomic-embed-text` vectors, merged with keyword in `search.py`). ⬜ Embed in the background so keyword search is ready first on launch
- ⬜ Summary page for managers

## Packaged app ✅
- ✅ `sh scripts/build-sidecar.sh` then `npm run tauri build` makes `Local Notes Assistant.app` (about 51 MB): double-click to open, no terminal. The backend is bundled inside and starts and stops with the app
- ✅ Tested on macOS (Intel): the built backend reads all `sample_notes/` and search works; quitting the app stops the backend
- ⚠ First launch takes about 15 s before the engine dot goes green (the backend unpacks itself; macOS scans the new binary). Later launches are faster
- ⚠ Not signed: the first time, right-click the app → Open. Ollama is still installed separately
- ⬜ Build on an Apple Silicon Mac for the demo machine (builds are per-architecture); sqlite-vec hidden imports when step 7 lands

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
- ✅ 2a. Check local Ollama model and inference (Fri). `nomic-embed-text` and `llama3.2:3b` run locally (timings under Performance notes); qa.py defaults to `qwen3:4b-instruct`
- ✅ 2b. `qa.py` with source-aware prompts (Sat), on `feature/ai-qa`, not merged yet
- 🔧 2c. Wire in `citations.py` and "No supporting notes found." (Sat). qa.py calls `check_answer`; ⬜ needs an ask route fed by `search.py` chunks
- ⬜ 2d. Compare old decisions with newer notes (Sun), needs 1c, 2c
- ✅ 2e. Unload the model on quit and forget (`models.unload` on forget, via `POST /api/engine/unload` from the launcher, and at exit; tests in `test_privacy_index.py`). qa.py should use `models.answer_model()`

**L: results UI** (step 3, 4, 6)
- ⬜ 3a. Results page with mock data (Sat)
- ⬜ 3b. Source cards and file excerpts (Sat)
- ⬜ 3c. Connect search and questions to the backend (Sat), needs 1d, 2c
- ⬜ 3d. Show decision changes and error states (Sun), needs 2d
- ⬜ 3e. Demo polish and accessibility check (Sun, P1)

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
- ⬜ Merge feature/ai-qa into main (P0, Sat)
- ⬜ Integrate citation validation and no-evidence handling (P0, Sat)
- ⬜ Add the ask route and keep the answer model warm (P0, Sat)
- ⬜ Build and run the app on the demo device with the sample notes (P0, Sun am)

**L: results UI**
- ⬜ Build functional results page with mock data (P0, Sat)
- ⬜ Display citation/source cards and file excerpts (P0, Sat)
- ⬜ Connect question/search flow to backend (P0, Sat)
- ⬜ Complete demo UI polish and accessibility check (P1, Sun am)

**C: privacy and trust, demo**
- ⬜ Merge feat/privacy-index, feat/search, db, ingest into main (P0, Sat)
- ⬜ Test storage, network and offline privacy claims (P0, Sat)
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
