import { invoke } from "@tauri-apps/api/core";

/**
 * Backend client. Every request carries the per-launch session token.
 *
 * In Tauri, the Rust side spawns the sidecar, picks the port and generates
 * the token; we fetch both via the `get_session` command. In plain browser
 * dev (vite only), fall back to VITE_BACKEND_PORT / VITE_SESSION_TOKEN set by
 * scripts/dev.sh.
 */

export interface Session {
  port: number;
  token: string;
}

// Fetched once and reused: the port and token never change during a run.
let sessionPromise: Promise<Session> | null = null;

// True inside the desktop window, false in a plain browser (dev only).
function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export function getSession(): Promise<Session> {
  if (!sessionPromise) {
    sessionPromise = (async () => {
      if (isTauri()) {
        // Ask the Rust side (src-tauri/src/lib.rs, `get_session`) for port + token.
        return await invoke<Session>("get_session");
      }
      const port = Number(import.meta.env.VITE_BACKEND_PORT ?? 8765);
      const token = String(import.meta.env.VITE_SESSION_TOKEN ?? "");
      return { port, token };
    })();
  }
  return sessionPromise;
}

// The window opens before the backend sidecar is listening, so the first
// requests fail at the network level ("TypeError: Load failed" in WebKit).
// Retry those quietly for a while instead of showing red errors at launch.
// HTTP errors (401, 404, 500...) are real answers and are never retried.
const STARTUP_WAIT_MS = 20000;
const RETRY_MS = 300;
const startedAt = Date.now();

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { port, token } = await getSession();
  let res: Response;
  for (;;) {
    try {
      res = await fetch(`http://127.0.0.1:${port}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          ...(init.headers ?? {}),
        },
      });
      break;
    } catch (e) {
      if (!(e instanceof TypeError) || Date.now() - startedAt > STARTUP_WAIT_MS) throw e;
      await new Promise((r) => setTimeout(r, RETRY_MS));
    }
  }
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export interface Health {
  status: "ok";
  version: string;
  read_only: boolean;
  network: "localhost-only";
}

export function health(): Promise<Health> {
  return apiFetch<Health>("/api/health");
}

export interface FolderAccess {
  paths: string[];
}

export function getAllowedPaths(): Promise<FolderAccess> {
  return apiFetch<FolderAccess>("/api/folders");
}

export function allowPath(path: string): Promise<FolderAccess> {
  return apiFetch<FolderAccess>("/api/folders", {
    method: "POST",
    body: JSON.stringify({ path }),
  });
}

export function revokePath(path: string): Promise<FolderAccess> {
  return apiFetch<FolderAccess>(`/api/folders?path=${encodeURIComponent(path)}`, {
    method: "DELETE",
  });
}

export interface ExtractedTodo {
  task: string;
  completed: boolean;
  chunkID: number;
  path: string;
  date: string;
  start: number;
  end: number;
}

let todosPromise: Promise<{ todos: ExtractedTodo[] }> | null = null;

export function getTodos(): Promise<{ todos: ExtractedTodo[] }> {
  if (!todosPromise) {
    todosPromise = apiFetch<{ todos: ExtractedTodo[] }>("/api/todos").catch((error: unknown) => {
      todosPromise = null;
      throw error;
    });
  }
  return todosPromise;
}

export interface ExtractedDecision {
  text: string;
  chunkID: number;
  path: string;
  date: string;
  start: number;
  end: number;
}

let decisionsPromise: Promise<{ decisions: ExtractedDecision[] }> | null = null;

export function getDecisions(): Promise<{ decisions: ExtractedDecision[] }> {
  if (!decisionsPromise) {
    decisionsPromise = apiFetch<{ decisions: ExtractedDecision[] }>("/api/decisions").catch(
      (error: unknown) => {
        decisionsPromise = null;
        throw error;
      },
    );
  }
  return decisionsPromise;
}

export interface SearchSource {
  chunkID: number;
  path: string;
  date: string;
  where: string;
  snippet: string;
  flag: "superseded" | "newer" | "conflict" | null;
}

export interface SearchResponse {
  status: "ok" | "no_support";
  answer: string | null;
  sources: SearchSource[];
}

export interface IndexStatus {
  files: number;
  chunks: number;
  groups: number;
  vectors: number;
  phase: "empty" | "meaning" | "grouping" | "ready" | "keyword_only";
  done: number;
  total: number;
  read?: number;
}

export function getIndexStatus(): Promise<IndexStatus> {
  return apiFetch<IndexStatus>("/api/index");
}

export function reindex(): Promise<IndexStatus> {
  return apiFetch<IndexStatus>("/api/index", { method: "POST" });
}

let indexPromise: Promise<IndexStatus> | null = null;

export function ensureSearchIndex(): Promise<IndexStatus> {
  if (!indexPromise) {
    indexPromise = getIndexStatus()
      .then((status) => (status.phase === "empty" ? reindex() : status))
      .finally(() => {
        indexPromise = null;
      });
  }
  return indexPromise;
}

export function searchNotes(query: string): Promise<SearchResponse> {
  return apiFetch<SearchResponse>(`/api/search?q=${encodeURIComponent(query)}`);
}

// Saved settings (backend/app/prefs.py). Only allowlisted values, never note text.
export interface SavedSettings {
  answer_model?: string;
}

export const getSettings = () => apiFetch<SavedSettings>("/api/settings");
export const saveSettings = (s: SavedSettings) =>
  apiFetch<SavedSettings>("/api/settings", { method: "PUT", body: JSON.stringify(s) });

// Capture (backend/app/notes.py). The app never edits a note: "open" hands it
// to the user's default app; createNote only ever writes a new file.
export const openFile = (path: string) =>
  apiFetch<{ opened: string }>("/api/files/open", { method: "POST", body: JSON.stringify({ path }) });

export interface NewNoteResult {
  path: string;
  tracked: boolean;
}

export const createNote = (folder: string, title: string, body: string) =>
  apiFetch<NewNoteResult>("/api/notes", { method: "POST", body: JSON.stringify({ folder, title, body }) });

// Changes (backend/app/changes.py): notes that disagree or replace older ones.
// Found by the local model, quotes verified in Python, kept in memory only.
export interface ConflictSide extends SearchSource {
  quote: string;
}

export interface ConflictItem {
  kind: "superseded" | "conflict";
  summary: string;
  topic: string | null;
  older: ConflictSide;
  newer: ConflictSide;
}

export interface ConflictReport {
  phase: "idle" | "scanning" | "done" | "no_engine";
  done: number;
  total: number;
  items: ConflictItem[];
}

export const getConflicts = () => apiFetch<ConflictReport>("/api/changes");
export const rescanConflicts = () => apiFetch<ConflictReport>("/api/changes", { method: "POST" });
