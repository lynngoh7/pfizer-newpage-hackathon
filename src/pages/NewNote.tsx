/**
 * New note (Capture). The user types a thought and saves it as a new .md file.
 *
 * Saving to one of the allowed folders = tracked (searchable). Saving
 * anywhere else = not tracked (the app won't read it). The backend only ever
 * creates a new file, never overwrites, and logs the path, never the text.
 * Nothing is kept by the app: the note is the user's own file.
 */
import { useEffect, useState } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { createNote, getAllowedPaths, NewNoteResult, openFile } from "../lib/api";

const OTHER = "__other__";

function isTauri(): boolean {
  return typeof window !== "undefined" && "__TAURI_INTERNALS__" in window;
}

export default function NewNote() {
  const [folders, setFolders] = useState<string[]>([]);
  const [folder, setFolder] = useState("");
  const [other, setOther] = useState<string | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<NewNoteResult | null>(null);

  useEffect(() => {
    getAllowedPaths()
      .then(({ paths }) => {
        // Only folders can hold a new note; single allowed files are skipped.
        const dirs = paths.filter((p) => !/\.(md|txt|pdf|docx)$/i.test(p));
        setFolders(dirs);
        setFolder(dirs[0] ?? OTHER);
      })
      .catch((e) => setError(String(e)));
  }, []);

  async function pickOther() {
    setError(null);
    if (!isTauri()) {
      setError("Folder selection is available in the desktop app.");
      return;
    }
    const picked = await open({ directory: true, multiple: false });
    if (typeof picked === "string") setOther(picked);
  }

  const target = folder === OTHER ? other : folder;

  async function save() {
    if (!target || !body.trim()) return;
    setBusy(true);
    setError(null);
    try {
      setSaved(await createNote(target, title, body));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setSaved(null);
    setTitle("");
    setBody("");
  }

  if (saved) {
    return (
      <section className="new-note">
        <h1>Note saved</h1>
        <div className="card">
          <dl className="props">
            <dt>Saved to</dt>
            <dd><code>{saved.path}</code></dd>
            <dt>Searchable</dt>
            <dd>{saved.tracked ? "Yes, it's in a folder the app can see" : "No, the app can't see this folder"}</dd>
          </dl>
          <div className="access-actions">
            <button className="btn" onClick={() => openFile(saved.path).catch((e) => setError(String(e)))}
              disabled={!saved.tracked} title={saved.tracked ? undefined : "The app can only open files in allowed folders"}>
              Open in editor
            </button>
            <button className="btn" onClick={reset}>Write another</button>
          </div>
          {error && <p className="error">{error}</p>}
        </div>
      </section>
    );
  }

  return (
    <section className="new-note">
      <h1>New note</h1>
      <p className="muted lead">
        Saved as a Markdown file in the folder you choose. The app keeps no copy.
      </p>
      <div className="card">
        <input className="note-title" placeholder="Title (optional)" value={title}
          onChange={(e) => setTitle(e.target.value)} maxLength={200} aria-label="Title" />
        <textarea className="note-body" placeholder="Write your thought…" value={body}
          onChange={(e) => setBody(e.target.value)} rows={12} aria-label="Note" />
        <div className="field">
          <label htmlFor="note-folder">Save in</label>
          <div className="select">
            <select id="note-folder" value={folder} onChange={(e) => setFolder(e.target.value)}>
              {folders.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
              <option value={OTHER}>Another folder (not searchable)…</option>
            </select>
          </div>
        </div>
        {folder === OTHER && (
          <div className="access-actions">
            <button className="btn" onClick={pickOther}>Choose folder</button>
            <span className="muted">
              {other ? <code>{other}</code> : "No folder chosen."} The app won't read notes saved here.
            </span>
          </div>
        )}
        <div className="access-actions">
          <button className="btn" onClick={save} disabled={busy || !target || !body.trim()}>
            {busy ? "Saving…" : "Save note"}
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </div>
    </section>
  );
}
