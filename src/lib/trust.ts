/**
 * Client for the Trust panel routes (backend/app/routes_trust.py).
 * Kept separate from api.ts so step 2-4 work there does not clash.
 */
import { apiFetch } from "./api";

export interface AuditEntry {
  seq: number;
  time: number; // unix seconds
  action: "read" | "skipped" | "blocked" | "folder_added" | "folder_removed" | "search" | "ask" | "forget";
  path: string | null;
  query: string | null;
  outcome: string;
}

export interface Connection {
  local: string;
  remote: string | null;
  kind: "listening" | "local" | "external";
}

export interface NetworkReport {
  external: number;
  processes: {
    role: "engine" | "app" | "model";
    pid: number;
    name: string;
    connections: Connection[];
    error: string | null;
  }[];
}

export interface StorageReport {
  files: number;
  locations: { path: string; exists: boolean; files: number; bytes: number; listed: string[] }[];
}

export interface ForgetResult {
  cleared: Record<string, number | null>;
  storage: StorageReport;
}

// `after` = last seq the page already has; the backend returns only newer entries.
export const auditLog = (after = 0) => apiFetch<AuditEntry[]>(`/api/audit?after=${after}`);
export const network = () => apiFetch<NetworkReport>("/api/trust/network");
export const storage = () => apiFetch<StorageReport>("/api/trust/storage");
export const forgetEverything = () => apiFetch<ForgetResult>("/api/session", { method: "DELETE" });
