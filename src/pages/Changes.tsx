/**
 * Changes (view id "changes"): pairs of notes where a newer one replaces or disagrees with an
 * older one. The backend finds them in the background once the index is
 * ready (backend/app/changes.py); this page polls until the scan is done.
 * Both quotes are checked against the files before they reach this page.
 */
import { useEffect, useState } from "react";
import { ConflictItem, ConflictReport, ConflictSide, ensureSearchIndex, getConflicts, openFile, rescanConflicts } from "../lib/api";

const POLL_MS = 2000;

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

/** Markdown symbols (#, **, - [ ], >, `) read as noise here. Strip them for
 * display only; the quote was already verified against the raw file text. */
function plain(text: string): string {
  return text
    .replace(/^\s*#{1,6}\s+/gm, "")
    .replace(/^\s*>\s?/gm, "")
    .replace(/^\s*[-*+]\s+\[[ xX]\]\s+/gm, "")
    .replace(/^\s*[-*+]\s+/gm, "• ")
    .replace(/(\*\*|__)(.+?)\1/g, "$2")
    .replace(/(^|\W)[*_](\S.*?)[*_](?=\W|$)/g, "$1$2")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/\s*\n\s*/g, " ")
    .trim();
}

function Side({ label, side }: { label: string; side: ConflictSide }) {
  const [error, setError] = useState<string | null>(null);
  return (
    <div className="conflict-side">
      <p className="conflict-side-label">
        {label} · {side.date}
      </p>
      <h3>{fileName(side.path)}</h3>
      <p className="source-location">{plain(side.where)}</p>
      <blockquote className="conflict-quote">“{plain(side.quote)}”</blockquote>
      <div className="source-actions">
        <button
          className="btn btn-small"
          onClick={() => openFile(side.path).catch((e) => setError(String(e)))}
          aria-label={`Open ${fileName(side.path)} in your editor`}
        >
          Open in editor
        </button>
        {error && <span className="error">{error}</span>}
      </div>
    </div>
  );
}

function Item({ item }: { item: ConflictItem }) {
  const superseded = item.kind === "superseded";
  return (
    <li className="card conflict-card">
      <div className="source-heading">
        <div>
          {item.topic && <p className="results-eyebrow">{plain(item.topic)}</p>}
          <h2>{(item.summary && plain(item.summary)) || (superseded ? "A newer note changes this" : "These notes disagree")}</h2>
        </div>
        <span className="change-tag">{superseded ? "Updated" : "Differs"}</span>
      </div>
      <div className="conflict-sides">
        <Side label="Earlier" side={item.older} />
        <Side label="Latest" side={item.newer} />
      </div>
    </li>
  );
}

export default function Changes() {
  const [report, setReport] = useState<ConflictReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    (async () => {
      try {
        await ensureSearchIndex();
        const r = await getConflicts();
        if (!active) return;
        setReport(r);
        setError(null);
        // Idle means the meaning index is still building; scanning means in progress.
        if (r.phase === "idle" || r.phase === "scanning") timer = window.setTimeout(() => setTick((t) => t + 1), POLL_MS);
      } catch (e) {
        if (active) setError(String(e));
      }
    })();
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [tick]);

  async function rescan() {
    try {
      setReport(await rescanConflicts());
      setTick((t) => t + 1);
    } catch (e) {
      setError(String(e));
    }
  }

  const busy = report?.phase === "idle" || report?.phase === "scanning";

  return (
    <section className="search-results" aria-labelledby="changes-title">
      <p className="results-eyebrow">Changes</p>
      <h1 id="changes-title">Notes that were updated or differ</h1>
      <p className="results-note">
        Compared on this computer by the local model. Each quote below was checked against the file before it was shown.
      </p>

      {error && (
        <div className="card search-error" role="alert">
          <h2>Couldn’t check your notes</h2>
          <p>{error}</p>
        </div>
      )}
      {report?.phase === "idle" && <p className="muted" role="status">Waiting for meaning search to finish indexing…</p>}
      {report?.phase === "scanning" && (
        <p className="muted" role="status">
          Comparing related notes… {report.done} of {report.total || "?"}
        </p>
      )}
      {report?.phase === "no_engine" && (
        <div className="card" role="alert">
          <h2>The local AI engine isn’t running</h2>
          <p className="muted">Start Ollama, then check again.</p>
          <button className="btn" onClick={rescan}>Check again</button>
        </div>
      )}
      {report?.phase === "done" && report.items.length === 0 && (
        <div className="card no-results" role="status">
          <h2>Nothing has changed.</h2>
          <p className="muted">Compared {report.total} pairs of related notes. They all agree.</p>
        </div>
      )}
      {report && report.items.length > 0 && (
        <ol className="source-list">
          {report.items.map((item) => (
            <Item key={`${item.older.chunkID}-${item.newer.chunkID}`} item={item} />
          ))}
        </ol>
      )}
      {report?.phase === "done" && (
        <p>
          <button className="btn btn-small" onClick={rescan} disabled={busy}>Check again</button>
        </p>
      )}
    </section>
  );
}
