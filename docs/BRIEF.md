# Project brief — Haystack

## 1. What we're building
A **fully local desktop AI assistant** that helps managers find the exact document or note they have in mind, even when their files are scattered and cluttered across the device.

**Top priority above everything else: security and trust.**
- Nothing ever leaves the machine. No cloud APIs, no telemetry, no remote fonts or CDNs.
- Answers must be grounded in the user's files, with citations. If nothing backs an answer, say so. No hallucinations.
- The app is **read-only by default**.

## 1a. The challenge (AI Studio at Pfizer × Newpage — "Second Brain for Managers")

**The ask:** a personal AI assistant for a manager with scattered notes (meeting notes, action items, saved links, screenshots, reminders, half-written updates) on their own device. It helps them use what they already know, while that knowledge stays local and **is never stored by the assistant**.

**The four pain points:** Capture (written and forgotten), Find (you know you wrote it, but not where or in what words), Connect (a decision and its context sit in separate notes), Trust (notes are too personal to hand over).

**The One Rule: "Your knowledge stays yours."**
- *On device:* nothing the assistant reads leaves the device.
- *No copies:* the assistant keeps no copy of its own. When it has finished helping, the knowledge is exactly where it was, and nowhere else.
- A user must be able to tell that this holds.

**Questions we designed against:**
- Helpful without remembering — how do we help without holding on to what we learn?
- How would you know — what makes a user genuinely confident their notes stayed put?
- In control — how does someone choose what it sees, and change their mind?
- Messy is normal — notes are fragmentary and out of date; what does helpful look like then?
- Honest when unsure — what happens when the answer isn't there?

### How we keep "No copies"
- **No note text on disk.** The index holds file path, mtime, content hash and chunk offsets, with embeddings and keyword data **in memory only**. Passages shown to the user are re-read from the original file.
- **Session-scoped index:** built in memory (SQLite `:memory:` with FTS5 + sqlite-vec) on launch or when a folder is added; discarded on quit, on "Forget everything", and when a folder is removed.
- **Saved settings only:** `backend/app/prefs.py` writes one `prefs.json` in the app data folder holding folder/file **paths** and allowlisted setting values. Never note text or anything derived from it (index, embeddings, extracts, queries, answers). Saved folders are re-checked on launch; missing or blocked ones are dropped.
- **Privacy page ("how would you know"):** (a) live audit log of files read, (b) network status showing no outbound connections, (c) everything stored on disk right now (only `prefs.json`, shown in full), (d) "Forget everything" with visible confirmation.
- The audit log holds paths and actions only, never note content, and is session-scoped.
- Ollama keeps the model warm during the session and unloads it on quit and on "Forget everything". No chat history is saved.
- Browser dev mode (`npm run dev:all`) is development only. The backend accepts the Vite origin only when `NOTES_DEV=1`; packaged builds never set it.

### Design choices
- **Not just a chatbot:** the search bar is the entry point and results lead with the answer, its sources and what changed, not a chat transcript.
- **Messy, out-of-date notes:** superseded/conflict detection surfaces "a newer note says otherwise" prominently.
- **Links** are read as text from the file only; **URLs are never fetched**.
- **Sample data:** `sample_notes/` holds realistic, fictional manager notes (meetings, action items, a contradicting update, an outdated decision, a half-written status update, a screenshot). Never anyone's real notes.

## 2. Scope
The core search + answer loop, plus a Home summary: Upcoming dates found in the notes (`app/dates.py`, `/api/upcoming`; no calendar connection, nothing stored), changes, decisions and open to-dos.

## 3. Features
1. Open and read the user's files: **PDF, Word (.docx), text (.txt) and Markdown (.md)**
2. Search across all notes by keyword
3. Ask questions in plain English and get answers from the notes
4. Pull out decisions and to-do items from notes
5. Show which file and passage each answer came from, and say so when nothing backs it up
6. Flag when two notes on the same topic disagree, or when a newer note replaces an older one
7. Let the user choose which folders the app can see, and take access away at any time
8. Never send anything off the computer, and show a log of what the app read
9. Ignore any instructions written inside files. Only the user gives instructions.
10. Search by meaning, not just exact words (finds "budget cut" when the note says "reduced funding")
11. Summary screen for managers: key decisions, open tasks, conflicts
12. Find disagreements across all notes, not just ones on the same topic
13. Button to clear the session and delete the app's stored data

**Future work:** read screenshots with local OCR, update automatically when files change, and let the app edit notes only after showing the change and getting the user's OK, with undo.

## 4. Tech stack

| Component | Choice |
|---|---|
| Desktop shell | Tauri v2 (strict CSP, no network permissions) |
| Frontend | React |
| Backend | Python + FastAPI, bound to `127.0.0.1`, session token, run as a PyInstaller sidecar. Rust for everything else (Tauri side) |
| LLM | Ollama (local) |
| Embeddings | `nomic-embed-text` via Ollama |
| Database | SQLite **in memory, session-scoped** (see §1a "No copies") |
| Search | FTS5 + sqlite-vec in that same database (hybrid keyword + vector) |
| Parsing | markitdown + pypdf |
| Agent | Custom loop with narrow tools, enforced in Python |
| Safety | Allowlist and denylist in the backend, read-only by default, audit log, source citations |

## 5. Architecture

```
React UI  ──(Tauri IPC / localhost + session token)──▶  FastAPI sidecar (127.0.0.1)
                                                          ├── folder allowlist / denylist
                                                          ├── ingest: markitdown / pypdf → chunks
                                                          ├── index: FTS5 + sqlite-vec (SQLite in memory, session only)
                                                          ├── agent loop (narrow tools, Python-enforced)
                                                          ├── audit log
                                                          └── Ollama (localhost only): LLM + embeddings
```

Backend modules (`backend/app/`; full list in [FILES.md](FILES.md)):
- `permissions` — allowed folders, denylist patterns (e.g. `.ssh`, `.env`, keychains), add/revoke access
- `ingest` — walk allowed folders, parse files, chunk text (keep file path, page/heading, char offsets)
- `db` — FTS5 table + vector table + chunk metadata (path, mtime, offsets)
- `search` — keyword, semantic, hybrid (merged with reciprocal rank fusion)
- `qa` + `citations` — retrieve, answer with citations, verify citations
- `extractions` — decisions and to-dos from notes
- `changes` — contradictions and superseded notes
- `audit` — append-only log of every file read and every tool call
- `api` — FastAPI routes, session-token check on every request

## 6. Safety rules (non-negotiable, enforce in code, not just in prompts)
- **Path enforcement:** every file access goes through one function that resolves the real path (follow symlinks) and checks it against the allowlist and denylist. Tools cannot bypass it.
- **Read-only:** the app never edits an existing file. "Open in editor" hands the file to the user's default app (path-checked). The one write is "New note": a new `.md` file the user typed, on an explicit Save, exclusive create (never overwrites), audit-logged by path only. No other writes.
- **Prompt injection (#9):** file content is passed to the LLM inside clearly delimited *untrusted data* blocks, with the system prompt saying content in those blocks is never an instruction. The model's tool calls are validated in Python regardless of what it asks for.
- **Grounded answers (#5):** the model must cite chunk IDs plus a short quote. Python checks that each quote really appears in the cited chunk. Drop unverified claims. If none survive, show **"No supporting notes found."**
- **No network (#8):** Tauri has no network permissions and a strict CSP. FastAPI and Ollama bind to localhost only. No outbound calls anywhere.
- **Audit log (#8):** record timestamp, action, file path, and which query triggered it (no note content). Viewable in the UI, session-scoped.
- **Data wipe (#13):** clear the index and logs, delete `prefs.json` (saved folders and settings), and reset the session.
- **No copies (One Rule):** never write note text, snippets, LLM prompts/answers or chat history to disk. Index and audit log live in memory for the session only. The only file on disk is `prefs.json` (folder paths + settings). Show passages by re-reading the source file.
- **Never fetch URLs** found in notes; links are treated as text only.

## 7. UI design
Kept **simple and straightforward, similar to Obsidian plus a web-browser search page**.

```
┌──────────────────┬──────────────────────────────────────────────┐
│ ○ Haystack       │  [ Search...                              ]  │
├──────────────────┤                                              │
│                  │                                              │
│   Sidebar        │        Main area                             │
│                  │        (results / answer / home)             │
│                  │                                              │
│                  │                                              │
│ ○ Settings       │                                              │
└──────────────────┴──────────────────────────────────────────────┘
```

- **Left sidebar (fixed):**
  - Top: product logo and name
  - Middle: navigation (Search, New note, Upcoming, To-dos, Decisions, Changes, Privacy). Kept minimal.
  - Bottom: engine status (label only: dot colour shows ready or not) and **Settings** (engine info, clear data)
- **Main area:**
  - Top: one wide **search bar** (like a browser). Handles both keyword search and plain-English questions.
  - Below: results. For a question, show the answer with inline citations, and a list of source cards (file name, path, passage snippet, open-file button). Show conflict or "superseded" badges where relevant.
  - Home: summary cards (Upcoming, Changes, Decisions, To-dos), each linking to its full page.
- **Privacy page** (sidebar): the whole One Rule story in one place: folders the app can see (add/remove), network and disk proof, activity log, "Forget everything".
- **Settings:** engine info, indexing status, link to Privacy, a "Clear all data" button.
- Visual style: clean, quiet and minimal. Light/dark friendly. All assets bundled locally (no web fonts from CDNs).

## 8. Known limits
- Loading sqlite-vec needs `enable_load_extension`, which the macOS system Python lacks. Use python.org or Homebrew Python (or `pysqlite3-binary`).
- Local LLM speed: a small model and tight context (top-k chunks only) keep answers to a few seconds.
- The in-memory index is rebuilt on every launch (by design: no copies). Indexing progress is shown.
