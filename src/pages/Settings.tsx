/**
 * Settings: folder access, engine info, clear data.
 * Step 2 replaces the folder stub with a list + picker (Tauri dialog plugin).
 * Step 5 wires "Forget everything" to DELETE /api/session (Trust panel).
 */
import { useEffect, useState } from "react";
import { health, Health } from "../lib/api";

export default function Settings() {
  const [info, setInfo] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    health().then(setInfo).catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="page">
      <h2>Settings</h2>

      <section className="card">
        <h3>Folder access</h3>
        <p className="muted">
          No folders yet. You choose exactly which folders the app may read, and can revoke access
          at any time. (Folder picker arrives in build step 2.)
        </p>
      </section>

      <section className="card">
        <h3>Local engine</h3>
        {error && <p className="error">Could not reach the local engine: {error}</p>}
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
