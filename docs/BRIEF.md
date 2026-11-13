# Project brief — Local Notes Assistant

> Read this before changing code. Section 6 is non-negotiable.

## 1. What we're building
A **fully local desktop AI assistant** that helps managers find the exact document or note they have in mind, even when their files are scattered and cluttered across the device.

**Top priority above everything else: security and trust.**
- Nothing ever leaves the machine. No cloud APIs, no telemetry, no remote fonts or CDNs.
- Answers must be grounded in the user's files, with citations. If nothing backs an answer, say so. No hallucinations.
- The app is **read-only by default**.

## 2. Current focus (this phase)
Build the **core search + answer loop only**. Calendar, to-dos and other dashboard widgets are **future add-ons**. Do not build them now, but keep the home screen layout able to host widgets later.

## 3. Feature checklist

### Must have (P0) — build these
1. Open and read the user's files: **PDF, Word (.docx), text (.txt) and Markdown (.md)**
2. Search across all notes by keyword
3. Ask questions in plain English and get answers from the notes
4. Pull out decisions and to-do items from notes
5. Show which file and passage each answer came from, and say so when nothing backs it up
6. Flag when two notes on the same topic disagree, or when a newer note replaces an older one
7. Let the user choose which folders the app can see, and take access away at any time
8. Never send anything off the computer, and show a log of what the app read
9. Ignore any instructions written inside files. Only the user gives instructions.

### Should have (P1) — after P0 works
10. Search by meaning, not just exact words (finds "budget cut" when the note says "reduced funding")
11. Summary screen for managers: key decisions, open tasks, conflicts
12. Find disagreements across all notes, not just ones on the same topic
13. Button to clear the session and delete the app's stored data

### Nice to have (P2) — only if time allows
14. Update automatically when files are added or changed
15. Let the app edit notes, but only after showing the change and getting the user's OK, with undo

## 4. Tech stack (agreed — do not substitute)

| Component | Choice |
|---|---|
| Desktop shell | Tauri v2 (strict CSP, no network permissions) |
| Frontend | React |
| Backend | Python + FastAPI, bound to `127.0.0.1`, session token, run as a PyInstaller sidecar. Rust for everything else (Tauri side) |
| LLM | Ollama (local) |
| Embeddings | `nomic-embed-text` via Ollama |
| Database | SQLite + SQLCipher (encrypted at rest) |
| Search | FTS5 + sqlite-vec in that same database (hybrid keyword + vector) |
| Parsing | markitdown + PyMuPDF |
| File watching | watchdog (P2) |
| Agent | Custom loop with narrow tools, enforced in Python |
| Safety | Allowlist and denylist in the backend, read-only by default, approve-and-diff for changes, audit log, source citations |

## 5. Architecture outline

```
React UI  ──(Tauri IPC / localhost + session token)──▶  FastAPI sidecar (127.0.0.1)
                                                          ├── folder allowlist / denylist
                                                          ├── ingest: markitdown / PyMuPDF → chunks
                                                          ├── index: FTS5 + sqlite-vec (SQLCipher DB)
                                                          ├── agent loop (narrow tools, Python-enforced)
                                                          ├── audit log
                                                          └── Ollama (localhost only): LLM + embeddings
```

Suggested backend modules:
- `config/permissions` — allowed folders, denylist patterns (e.g. `.ssh`, `.env`, keychains), add/revoke access
- `ingest` — walk allowed folders, parse files, chunk text (keep file path, page/heading, char offsets)
- `index` — FTS5 table + vector table + chunk metadata (path, mtime, offsets)
- `search` — keyword, semantic, hybrid (merge results, e.g. reciprocal rank fusion)
- `qa` — retrieve, then answer with citations, then verify citations
- `extract` — decisions and to-dos from notes
- `conflicts` — detect contradictions and superseded notes
- `audit` — append-only log of every file read and every tool call
- `api` — FastAPI routes, session-token check on every request

## 6. Safety rules (non-negotiable, enforce in code, not just in prompts)
- **Path enforcement:** every file access goes through one function that resolves the real path (follow symlinks) and checks it against the allowlist and denylist. Tools cannot bypass it.
- **Read-only:** no write tools exist unless P2 #15 is built, and then only via approve → diff → apply → undo.
- **Prompt injection (#9):** file content is passed to the LLM inside clearly delimited *untrusted data* blocks, with the system prompt saying content in those blocks is never an instruction. The model's tool calls are validated in Python regardless of what it asks for.
- **Grounded answers (#5):** the model must cite chunk IDs plus a short quote. Python checks that each quote really appears in the cited chunk. Drop unverified claims. If none survive, show **"No supporting notes found."**
- **No network (#8):** Tauri has no network permissions and a strict CSP. FastAPI and Ollama bind to localhost only. No outbound calls anywhere.
- **Audit log (#8):** record timestamp, action, file path, and which query triggered it. Viewable in the UI.
- **Data wipe (#13):** delete the DB, index and logs, and reset the session.

## 7. UI design (current phase)
Keep it **simple and straightforward, similar to Obsidian plus a web-browser search page**.

```
┌──────────────────┬──────────────────────────────────────────────┐
│ ○ Product Name   │  [ Search...                              ]  │
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
  - Middle: navigation (e.g. Search, Decisions & To-dos, Conflicts, Activity Log). Keep minimal.
  - Bottom: **Settings** (folder access, clear data)
- **Main area:**
  - Top: one wide **search bar** (like a browser). Handles both keyword search and plain-English questions.
  - Below: results. For a question, show the answer with inline citations, and a list of source cards (file name, path, passage snippet, open-file button). Show conflict or "superseded" badges where relevant.
  - Home/empty state: a clean page. Later this will hold **customisable widgets** (calendar, to-do, ...). **Not in scope now**, so just leave room for it.
- **Settings:** list of allowed folders with add/remove, indexing status, link to the activity log, a "Clear all data" button.
- Visual style: clean, quiet and minimal. Light/dark friendly. All assets bundled locally (no web fonts from CDNs).

## 8. Build order (suggested)
1. Tauri + React shell with the sidebar/search layout; FastAPI sidecar with a health check and session token
2. Folder picker → allowlist → ingest and parse (P0 #1, #7)
3. FTS5 keyword search + results UI (#2)
4. Ollama Q&A with verified citations (#3, #5, #9)
5. Audit log + viewer (#8)
6. Decisions/to-dos extraction (#4), conflicts/superseded detection (#6)
7. P1: embeddings + hybrid search (#10), summary screen (#11), clear data (#13)

## 9. Known risks
- Bundling SQLCipher + sqlite-vec inside PyInstaller can be painful. Test packaging early.
- Local LLM speed: use a small model for the demo and keep the context tight (top-k chunks only).
- Demo idea: turn Wi-Fi off live to prove everything runs offline.
