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

let sessionPromise: Promise<Session> | null = null;

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export function getSession(): Promise<Session> {
  if (!sessionPromise) {
    sessionPromise = (async () => {
      if (isTauri()) {
        const { invoke } = await import("@tauri-apps/api/core");
        return await invoke<Session>("get_session");
      }
      const port = Number(import.meta.env.VITE_BACKEND_PORT ?? 8765);
      const token = String(import.meta.env.VITE_SESSION_TOKEN ?? "");
      return { port, token };
    })();
  }
  return sessionPromise;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { port, token } = await getSession();
  const res = await fetch(`http://127.0.0.1:${port}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init.headers ?? {}),
    },
  });
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
