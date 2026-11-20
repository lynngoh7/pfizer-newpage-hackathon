/**
 * Folder access card (step 2b): pick folders/files the app may read this
 * session, and remove them. Shown first on the Privacy page.
 * Logic and markup moved unchanged from the folder-permissions Settings page.
 */
import { useEffect, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { allowPath, getAllowedPaths, revokePath } from "../lib/api";

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export default function FolderAccess() {
  const [allowedPaths, setAllowedPaths] = useState<string[]>([]);
  const [accessError, setAccessError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
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
  );
}
