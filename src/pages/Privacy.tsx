/**
 * Privacy page (Trust panel, build step 5): the whole "your knowledge stays
 * yours" story on one page, in order: which folders the app can see, proof
 * that nothing left (network) or stayed (disk), what it read (activity log),
 * and "forget everything".
 *
 * Polls only while open: activity every 2 s (new entries only, by seq),
 * network every 3 s, disk every 10 s. Nothing here is cached or saved.
 */
import { memo, useCallback, useEffect, useRef, useState } from "react";
import ForgetButton from "../components/ForgetButton";
import { AuditEntry, auditLog, network, NetworkReport, storage, StorageReport } from "../lib/trust";

// Plain-language names, in the order a user thinks of them.
const PROGRAMS: { role: "app" | "engine" | "model"; name: string }[] = [
  { role: "app", name: "Notes app" },
  { role: "engine", name: "Search engine" },
  { role: "model", name: "AI model (Ollama)" },
];

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

// Call `fn` now and every `ms` while the page is open. Returns [data, error, refresh].
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
  // A ref, not state: changing it must not re-render, it only marks how far we have read.
  const lastSeq = useRef(0);

  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const fresh = await auditLog(lastSeq.current);
        if (alive && fresh.length) {
          lastSeq.current = fresh[fresh.length - 1].seq;
          setLog((old) => [...old, ...fresh]); // append only the new lines
        }
      } catch { /* engine offline: the sidebar already says so */ }
    }
    poll();
    const t = setInterval(poll, 2000);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const filesRead = log.filter((e) => e.action === "read").length;

  const outside = net?.external ?? 0;

  return (
    <div className="page">
      <h2>Privacy</h2>
      <p className="muted lead">
        Your notes stay on this computer, and the app keeps no copy of them. This page shows you
        that live, so you don't have to take our word for it.
      </p>

      {/* Summary: a plain list, not clickable. Only a problem gets colour. */}
      <dl className="props">
        <dt>Internet</dt>
        <dd className={outside ? "error" : ""}>
          {!net ? "Checking…" : outside ? `${outside} connection${outside > 1 ? "s" : ""} outside this computer` : "Nothing has left this computer"}
        </dd>
        <dt>Saved to disk</dt>
        <dd className={disk?.files ? "error" : ""}>
          {!disk ? "Checking…" : disk.files ? `${disk.files} files` : "Nothing"}
        </dd>
        <dt>Files read</dt>
        <dd>{filesRead ? `${filesRead} this session` : "None yet"}</dd>
      </dl>

      {/* Step 2b fills this in: folder list with add/remove (Tauri dialog plugin).
          Grants are session-only, so this list starts empty on every launch. */}
      <section className="card">
        <h3>Folders the app can see</h3>
        <p className="muted">
          None yet. The app can only read folders you choose here, only for this session, and you
          can remove one at any time. Removing a folder makes the app forget it straight away.
        </p>
      </section>

      <section className="card">
        <h3>Internet</h3>
        {netError && <p className="error">Could not check: {netError}</p>}
        {net && (
          <p>
            {outside
              ? "Something is connected outside this computer. See below."
              : "The app's parts only talk to each other, inside this machine. Checked every few seconds."}
          </p>
        )}
        {net && <NetworkSummary report={net} />}
        <details className="more">
          <summary>How to check this yourself</summary>
          <ol>
            <li>Turn Wi-Fi off. Search and answers keep working, because nothing needs the internet.</li>
            <li>
              Or open Terminal and run <code>lsof -nP -i | grep -iE "notes|ollama|python"</code>. Every
              address should start with <code>127.0.0.1</code> or <code>[::1]</code>.
            </li>
          </ol>
        </details>
        {net && (
          <details className="more">
            <summary>Technical details</summary>
            <ul className="paths">
              {net.processes.map((p) => (
                <li key={p.pid}>
                  {p.name} (pid {p.pid}){p.error && ` — couldn't inspect (${p.error})`}
                  <ul>
                    {p.connections.map((c, i) => (
                      <li key={i} className={c.kind === "external" ? "error" : ""}>
                        <code>{c.remote ? `${c.local} → ${c.remote}` : `${c.local} (listening)`}</code>
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      <section className="card">
        <h3>Saved to disk</h3>
        {diskError && <p className="error">Could not check: {diskError}</p>}
        {disk && disk.files === 0 && (
          <p>All {disk.locations.length} places where apps usually keep data are empty. Checked just now.</p>
        )}
        {disk && disk.files > 0 && (
          <>
            <p className="error">
              Found {disk.files} file{disk.files > 1 ? "s" : ""} in the app's folders:
            </p>
            <ul className="paths">
              {disk.locations.filter((l) => l.files > 0).map((l) => (
                <li key={l.path}>
                  <code>{l.path}</code> <span className="muted">— {l.files} files, {Math.ceil(l.bytes / 1024)} KB</span>
                </li>
              ))}
            </ul>
          </>
        )}
        {disk && (
          <details className="more">
            <summary>Places checked</summary>
            <ul className="paths">
              {disk.locations.map((l) => (
                <li key={l.path}>
                  <code>{l.path}</code> <span className="muted">— {l.files ? `${l.files} files` : l.exists ? "empty" : "not there"}</span>
                </li>
              ))}
            </ul>
          </details>
        )}
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

// One line per program: what it is talking to, in plain words.
function NetworkSummary({ report }: { report: NetworkReport }) {
  return (
    <dl className="props">
      {PROGRAMS.map(({ role, name }) => {
        const procs = report.processes.filter((p) => p.role === role);
        const conns = procs.flatMap((p) => p.connections);
        const out = conns.filter((c) => c.kind === "external").length;
        const text = procs.length === 0 ? "Not running"
          : procs.some((p) => p.error) ? "Couldn't check"
          : out ? `Connected outside this computer (${out})`
          : conns.length ? "Only talks inside this computer"
          : "No connections";
        return [
          <dt key={`${role}-t`}>{name}</dt>,
          <dd key={`${role}-d`} className={out ? "error" : ""}>{text}</dd>,
        ];
      })}
    </dl>
  );
}

// memo: re-renders only when the log changes, not on every network/disk poll.
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
            <td className="muted">{new Date(e.time * 1000).toLocaleTimeString()}</td>
            <td className={e.action === "blocked" ? "error" : ""}>{ACTION[e.action]}</td>
            <td title={e.path ?? ""}>{e.path ? fileName(e.path) : "—"}</td>
            <td className="muted">{[e.query && `“${e.query}”`, e.outcome !== "ok" && e.outcome].filter(Boolean).join(" · ")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
});
