/**
 * Settings: folder access, engine info, clear data.
 * Step 5 wires "Forget everything" to DELETE /api/session (Trust panel).
 */
import { useEffect, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { allowPath, getAllowedPaths, health, Health, revokePath } from "../lib/api";

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export default function Settings() {
  const [info, setInfo] = useState<Health | null>(null);
  const [allowedPaths, setAllowedPaths] = useState<string[]>([]);
  const [accessError, setAccessError] = useState<string | null>(null);
  const [engineError, setEngineError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    health().then(setInfo).catch((e) => setEngineError(String(e)));
    getAllowedPaths()
      .then(({ paths }) => setAllowedPaths(paths))
      .catch((e) => setAccessError(String(e)));
  }, []);

  async function addLocations(directory: boolean) {
    setAccessError(null);
    if (!isTauri()) {
      setAccessError("File and folder selection is available in the desktop app.");
      return;
    }

    setBusy(true);
    try {
      const selected = await open({ directory, multiple: true });
      if (!selected) return;
      const paths = Array.isArray(selected) ? selected : [selected];
      for (const path of paths) {
        const result = await allowPath(path);
        setAllowedPaths(result.paths);
      }
    } catch (e) {
      setAccessError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function removeLocation(path: string) {
    setAccessError(null);
    setBusy(true);
    try {
      const result = await revokePath(path);
      setAllowedPaths(result.paths);
    } catch (e) {
      setAccessError(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <h2>Settings</h2>

      <section className="card">
        <h3>Folder access</h3>
        <p className="muted">
          Choose which folders and individual files the assistant can read. Access is limited to
          this session, and you can revoke it at any time.
        </p>
        <div className="access-actions">
          <button className="btn" onClick={() => addLocations(true)} disabled={busy}>
            Add folder
          </button>
          <button className="btn" onClick={() => addLocations(false)} disabled={busy}>
            Add files
          </button>
        </div>
        {accessError && <p className="error" role="alert">{accessError}</p>}
        {allowedPaths.length === 0 ? (
          <p className="muted">No folders or files are currently allowed.</p>
        ) : (
          <ul className="access-list">
            {allowedPaths.map((path) => (
              <li key={path}>
                <span className="access-path" title={path}>{path}</span>
                <button
                  className="btn"
                  onClick={() => removeLocation(path)}
                  disabled={busy}
                  aria-label={`Remove access to ${path}`}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h3>Local engine</h3>
        {engineError && <p className="error">Could not reach the local engine: {engineError}</p>}
        {info && (
          <dl className="kv">
            <dt>Status</dt>
            <dd>{info.status}</dd>
            <dt>Version</dt>
            <dd>{info.version}</dd>
            <dt>Mode</dt>
            <dd>{info.read_only ? "Read-only" : "Read/write"}</dd>
            <dt>Network</dt>
            <dd>{info.network}</dd>
          </dl>
        )}
      </section>

      <section className="card">
        <h3>Data</h3>
        <p className="muted">
          The app keeps your notes in memory for this session only and writes nothing to disk.
          “Forget everything” (clears the session) arrives with the Trust panel in build step 5.
        </p>
        <button className="btn danger" disabled>
          Forget everything
        </button>
      </section>
    </div>
  );
}
