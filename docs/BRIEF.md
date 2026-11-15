# Project brief — Local Notes Assistant

> Read this before changing code. Section 6 is non-negotiable.

## 1. What we're building
A **fully local desktop AI assistant** that helps managers find the exact document or note they have in mind, even when their files are scattered and cluttered across the device.

**Top priority above everything else: security and trust.**
- Nothing ever leaves the machine. No cloud APIs, no telemetry, no remote fonts or CDNs.
- Answers must be grounded in the user's files, with citations. If nothing backs an answer, say so. No hallucinations.
- The app is **read-only by default**.

## 1a. Hackathon brief (AI Studio at Pfizer × Newpage — "Second Brain for Managers")

**The ask:** prototype a personal AI assistant for a manager with scattered notes (meeting notes, action items, saved links, screenshots, reminders, half-written updates) on their own device. It helps them use what they already know, while that knowledge stays local and **is never stored by the assistant**. Pick **one moment** where scattered notes let a manager down and show it working better.

**The four pain points named in the brief:** Capture (written and forgotten), Find (you know you wrote it, but not where or in what words), Connect (a decision and its context sit in separate notes), Trust (notes are too personal to hand over).

**The One Rule: "Your knowledge stays yours."**
- *On device:* nothing the assistant reads leaves the device.
- *No copies:* the assistant keeps no copy of its own. When it has finished helping, the knowledge is exactly where it was, and nowhere else.
- We must show how we uphold this **and how a user could tell**.

**Our chosen demo moment:** _TBD by team_. Recommended: "find a decision made weeks ago, and has it changed since?" (hits Find, Connect and messy notes in one query; needs no calendar). Other candidates: preparing for a meeting, connecting related ideas. Every build decision should serve this one moment end to end first.

**Minimum to pass ("good enough"):** one useful moment working end to end in a short demo, running on a device, One Rule respected, using **sample manager notes we wrote ourselves** (never anyone's real notes).

**Stretch goals (from the brief):**
- User can check for themselves that nothing left the device or was kept
- Works across more than one kind of personal content (e.g. notes + screenshots/links)
- Assistant explains in plain language where its help came from

**Judging (50 pts, 10 each):**
| Criterion | What they look for |
|---|---|
| Insight & Problem Understanding | Tackles a real capture/find/connect/trust moment; something a manager would actually use |
| Creative Use of AI & Design | Changes how someone uses what they know — **not just a chatbot over notes**; copes with messy, fragmentary, out-of-date notes |
| Working End to End | One moment working end to end on a device with our sample notes. Bonus: more than one kind of notes |
| Trust & Explainability | Honest when the answer isn't there or it's unsure; plain-language explanation of where help came from |
| Knowledge Stays Yours | Nothing leaves the device, **no copy kept**; user can verify this, choose what it sees, and change their mind |

**Questions the brief asks us to answer (design against these):**
- Helpful without remembering — how do we help without holding on to what we learn?
- How would you know — what makes a user genuinely confident their notes stayed put?
- In control — how does someone choose what it sees, and change their mind?
- Messy is normal — notes are fragmentary and out of date; what does helpful look like then?
- Honest when unsure — what happens when the answer isn't there?

**Submission:** prototype + video demo by **23:59, Sunday 22 November 2026**, emailed to careers-uobinterns@bristol.ac.uk, subject **"Pfizer Hackathon Submission"**.

### ⚠ Impact on our design: "No copies"
Our original plan stores parsed text in an encrypted SQLite index. Even encrypted, that is arguably "the assistant keeping its own copy", which breaks the One Rule. Default approach until the team decides otherwise:
- **Store no note text on disk.** The index holds only file path, mtime, content hash, chunk offsets (and embeddings/FTS data **in memory only**). Passages shown to the user are re-read from the original file at display time.
- **Session-scoped index:** build in memory (SQLite `:memory:` with FTS5 + sqlite-vec) on launch/folder grant; discard on quit, on "Clear session", and when access to a folder is revoked.
- If a persistent cache is ever needed for speed, it must be opt-in, clearly labelled in the UI, and wiped by one button. SQLCipher stays as the fallback for that case only.
- Ollama: use `keep_alive: 0` or short so the model doesn't hold context; no chat history saved to disk.
- **"How would you know" feature (demo it):** a Trust panel showing (a) the live audit log of files read, (b) zero outbound connections (e.g. the app's own network status, plus a "turn Wi-Fi off" demo), (c) what the app has stored on disk right now (should be nothing, or only the folder list), and (d) a "forget everything" button with visible confirmation.
- The audit log itself must not contain note content — paths and actions only — and is session-scoped too.
- **Folder grants are session-only too** (decided 2026-11-15): the user picks folders on launch. Then "stored on disk: nothing" is literally true. Revoking a folder drops its chunks from memory at once.
- Ollama: keep the model warm during the session (cold loads make the demo slow); unload on quit and on "forget everything".
- Browser dev mode (`npm run dev:all`) is development only. The backend accepts the Vite origin only when `NOTES_DEV=1`; packaged builds never set it. Never demo in a browser.

### Other implications
- **Not just a chatbot:** lead the UI with the chosen moment (e.g. a "Prep for meeting" view or a decision timeline), with the search bar as the entry point, not a chat transcript.
- **Messy/out-of-date notes:** the superseded/conflict detection (#6) directly scores here — surface "newer note says otherwise" prominently.
- **More than one kind of content (bonus):** screenshots (local OCR, e.g. Tesseract — must be offline) and saved links (read the link text/title from the file only; **never fetch URLs**) are candidates after P0.
- **Sample data:** create a `sample_notes/` folder of realistic, fictional manager notes (meetings, action items, a contradicting update, an outdated decision, a half-written status update, a screenshot) designed to show off the demo moment.

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
| Database | SQLite **in memory, session-scoped** (see §1a "No copies"). SQLCipher only for an opt-in persistent cache |
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
                                                          ├── index: FTS5 + sqlite-vec (SQLite in memory, session only)
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
- **Audit log (#8):** record timestamp, action, file path, and which query triggered it (no note content). Viewable in the UI, session-scoped.
- **Data wipe (#13):** delete the DB, index and logs, and reset the session.
- **No copies (One Rule):** never write note text, snippets, LLM prompts/answers or chat history to disk. Index and audit log live in memory for the session only. Show passages by re-reading the source file.
- **Never fetch URLs** found in notes; links are treated as text only.

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
6b. Trust panel ("how would you know"): audit log, stored-on-disk view, forget-everything button. Build demo around `sample_notes/`.
7. P1: embeddings + hybrid search (#10), summary screen (#11), clear data (#13)

## 9. Known risks
- Loading sqlite-vec needs `enable_load_extension`, which the macOS system Python lacks. Use python.org or Homebrew Python (or `pysqlite3-binary`) and test packaging early. SQLCipher is no longer needed unless the opt-in cache is built.
- Local LLM speed: use a small model for the demo and keep the context tight (top-k chunks only).
- Demo idea: turn Wi-Fi off live to prove everything runs offline.
- In-memory index means re-indexing on every launch. Keep the sample set small and parsing fast; show indexing progress.
- Deadline: video + prototype due 23:59 Sun 22 Nov 2026. Reserve the last day for recording the demo video.
