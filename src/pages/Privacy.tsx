/**
 * Privacy page (Trust panel, build step 5): answers "how would you know?".
 * Shows, live: the app's network connections, what it has stored on disk,
 * every file it read this session, and a "forget everything" button.
 *
 * Polls only while open: activity every 2 s (new entries only, by seq),
 * network every 3 s, disk every 10 s. Nothing here is cached or saved.
 */
import { memo, useCallback, useEffect, useRef, useState } from "react";
import ForgetButton from "../components/ForgetButton";
import { AuditEntry, auditLog, network, NetworkReport, storage, StorageReport } from "../lib/trust";

const ROLE: Record<string, string> = {
  engine: "Notes engine",
  app: "Notes app window",
  model: "Ollama (local AI model)",
};

const ACTION: Record<AuditEntry["action"], string> = {
  read: "Read",
  skipped: "Skipped",
  blocked: "Blocked",
  folder_added: "Folder added",
  folder_removed: "Folder removed",
  search: "Search",
  ask: "Question",
  forget: "Forgot everything",
};

function usePoll<T>(fn: () => Promise<T>, ms: number): [T | null, string | null, () => void] {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const refresh = useCallback(() => {
    fn().then((d) => { setData(d); setError(null); }).catch((e) => setError(String(e)));
  }, [fn]);
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, ms);
    return () => clearInterval(t);
  }, [refresh, ms]);
  return [data, error, refresh];
}

function fileName(p: string) {
  return p.split(/[\\/]/).pop() || p;
}

export default function Privacy() {
  const [net, netError] = usePoll<NetworkReport>(network, 3000);
  const [disk, diskError, refreshDisk] = usePoll<StorageReport>(storage, 10000);
  const [log, setLog] = useState<AuditEntry[]>([]);
  const lastSeq = useRef(0);

  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const fresh = await auditLog(lastSeq.current);
        if (alive && fresh.length) {
          lastSeq.current = fresh[fresh.length - 1].seq;
          setLog((old) => [...old, ...fresh]);
        }
      } catch { /* engine offline: the sidebar already says so */ }
    }
    poll();
    const t = setInterval(poll, 2000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const filesRead = log.filter((e) => e.action === "read").length;

  return (
    <div className="page">
      <h2>Privacy</h2>
      <p className="muted lead">
        Your notes stay on this computer, and the app keeps no copy of them. This page shows you
        that live, so you don't have to take our word for it.
      </p>

      <div className="tiles">
        <Tile
          ok={net ? net.external === 0 : null}
          label="Internet"
          value={!net ? "Checking…" : net.external === 0 ? "Nothing leaves this computer" : `${net.external} outside connection${net.external > 1 ? "s" : ""}`}
        />
        <Tile
          ok={disk ? disk.files === 0 : null}
          label="Stored on disk"
          value={!disk ? "Checking…" : disk.files === 0 ? "Nothing" : `${disk.files} files`}
        />
        <Tile ok={null} label="This session" value={`${filesRead} file${filesRead === 1 ? "" : "s"} read`} />
      </div>

      <section className="card">
        <h3>Network connections</h3>
        <p className="muted">
          Every connection the app's own programs have open right now. "Local" means it stays
          inside this computer.
        </p>
        {netError && <p className="error">Could not check: {netError}</p>}
        {net?.processes.map((p) => (
          <div key={p.pid} className="proc">
            <div className="proc-name">
              {ROLE[p.role]} <span className="muted">· {p.name} (pid {p.pid})</span>
            </div>
            {p.error && <div className="muted">Couldn't inspect ({p.error})</div>}
            {!p.error && p.connections.length === 0 && <div className="muted">No connections</div>}
            {p.connections.map((c, i) => (
              <div key={i} className="conn">
                <span className={`badge ${c.kind === "external" ? "bad" : "good"}`}>
                  {c.kind === "listening" ? "Waiting for the app" : c.kind === "local" ? "Local" : "Outside!"}
                </span>
                <code>{c.remote ? `${c.local} → ${c.remote}` : c.local}</code>
              </div>
            ))}
          </div>
        ))}
        <details className="verify">
          <summary>Check it yourself</summary>
          <ol>
            <li>Turn Wi-Fi off. Search and answers keep working, because nothing needs the internet.</li>
            <li>
              Or open Terminal and run <code>lsof -nP -i | grep -iE "notes|ollama|python"</code>. Every
              address should start with <code>127.0.0.1</code> or <code>[::1]</code>.
            </li>
          </ol>
        </details>
      </section>

      <section className="card">
        <h3>Stored on disk</h3>
        {diskError && <p className="error">Could not check: {diskError}</p>}
        {disk && disk.files === 0 && (
          <p>
            <span className="badge good">Nothing</span> The app has written no files. These are the
            places a desktop app normally keeps data, checked just now:
          </p>
        )}
        {disk && disk.files > 0 && (
          <p className="warn-text">
            Found {disk.files} file{disk.files > 1 ? "s" : ""} in the app's folders. They are listed
            below so you can see exactly what they are.
          </p>
        )}
        <ul className="paths">
          {disk?.locations.map((l) => (
            <li key={l.path}>
              <code>{l.path}</code>{" "}
              {l.files === 0 ? (
                <span className="muted">— {l.exists ? "empty" : "doesn't exist"}</span>
              ) : (
                <>
                  <span className="warn-text">— {l.files} files, {Math.ceil(l.bytes / 1024)} KB</span>
                  <ul>{l.listed.map((f) => <li key={f}><code>{f}</code></li>)}</ul>
                </>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h3>Activity log</h3>
        <p className="muted">
          Every file the app opened, skipped or was blocked from, newest first. Kept in memory for
          this session only. It never contains the text of your notes.
        </p>
        <ActivityTable entries={log} />
      </section>

      <section className="card">
        <h3>Forget everything</h3>
        <p className="muted">Ends this session's memory now, instead of waiting until you quit.</p>
        <ForgetButton onDone={() => { setLog([]); refreshDisk(); }} />
      </section>
    </div>
  );
}

function Tile({ ok, label, value }: { ok: boolean | null; label: string; value: string }) {
  return (
    <div className={`tile ${ok === true ? "good" : ok === false ? "bad" : ""}`}>
      <div className="tile-label">{label}</div>
      <div className="tile-value">{value}</div>
    </div>
  );
}

const ActivityTable = memo(function ActivityTable({ entries }: { entries: AuditEntry[] }) {
  if (entries.length === 0) return <p className="muted">Nothing yet this session.</p>;
  return (
    <table className="log">
      <thead>
        <tr><th>Time</th><th>What</th><th>File</th><th>Details</th></tr>
      </thead>
      <tbody>
        {[...entries].reverse().map((e) => (
          <tr key={e.seq}>
            <td>{new Date(e.time * 1000).toLocaleTimeString()}</td>
            <td><span className={`badge ${e.action === "blocked" ? "bad" : ""}`}>{ACTION[e.action]}</span></td>
            <td title={e.path ?? ""}>{e.path ? fileName(e.path) : "—"}</td>
            <td className="muted">{[e.query && `“${e.query}”`, e.outcome !== "ok" && e.outcome].filter(Boolean).join(" · ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
});
