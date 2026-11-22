/**
 * Home: the manager summary (P1 #11). Three cards: latest decisions, open
 * to-dos, and notes that changed. Each shows a few items and links to its
 * full page. Everything comes from the in-memory index; nothing is saved.
 *
 * Decisions and to-dos are loaded once by App.tsx and passed in. Changes are
 * polled here until the background scan finishes (same as the Changes page).
 */
import { useEffect, useState } from "react";
import type { View } from "../components/Sidebar";
import { ChangeReport, ExtractedDecision, ExtractedTodo, ensureSearchIndex, getChanges } from "../lib/api";
import { ticked, todoKey } from "./Todos";

const SHOW = 3;
const POLL_MS = 2000;

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

/** Markdown bold and heading marks read as noise in a one-line summary. */
function plain(text: string): string {
  return text.replace(/^\s*#{1,6}\s+/gm, "").replace(/(\*\*|__)(.+?)\1/g, "$2").replace(/\s*\n\s*/g, " ").trim();
}

interface Props {
  decisions: ExtractedDecision[] | null;
  todos: ExtractedTodo[] | null;
  onNavigate: (v: View) => void;
}

function Widget(props: { title: string; count: string | null; to: View; onNavigate: (v: View) => void; children: React.ReactNode }) {
  const id = `widget-${props.to}`;
  return (
    <section className="card widget" aria-labelledby={id}>
      <div className="widget-head">
        <h2 id={id}>{props.title}</h2>
        {props.count && <span className="muted">{props.count}</span>}
      </div>
      {props.children}
      <button className="link widget-more" onClick={() => props.onNavigate(props.to)}>
        See all {props.title.toLowerCase()} →
      </button>
    </section>
  );
}

export default function Home({ decisions, todos, onNavigate }: Props) {
  const [changes, setChanges] = useState<ChangeReport | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let active = true;
    let timer: number | undefined;
    (async () => {
      try {
        await ensureSearchIndex();
        const r = await getChanges();
        if (!active) return;
        setChanges(r);
        if (r.phase === "idle" || r.phase === "scanning") timer = window.setTimeout(() => setTick((t) => t + 1), POLL_MS);
      } catch {
        // Backend still starting: try again shortly. The Changes page shows real errors.
        if (active) timer = window.setTimeout(() => setTick((t) => t + 1), POLL_MS);
      }
    })();
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [tick]);

  // Newest first; ISO dates sort as strings.
  const latest = decisions ? [...decisions].sort((a, b) => b.date.localeCompare(a.date)) : null;
  const open = todos
    ? todos
        .map((todo, index) => ({ todo, done: ticked.get(todoKey(todo, index)) ?? todo.completed }))
        .filter((t) => !t.done)
        .map((t) => t.todo)
        .sort((a, b) => b.date.localeCompare(a.date))
    : null;
  const scanning = !changes || changes.phase === "idle" || changes.phase === "scanning";

  return (
    <div className="home">
      <h1>What are you looking for?</h1>
      <p className="muted">
        Search by keyword or ask a question in plain English. Answers come only from your own
        files, with citations. Nothing leaves this computer.
      </p>

      <div className="widget-grid">
        <Widget title="Changes" count={changes?.items.length ? String(changes.items.length) : null} to="changes" onNavigate={onNavigate}>
          {changes?.phase === "no_engine" && <p className="muted">Start Ollama to compare notes.</p>}
          {changes && changes.items.length > 0 ? (
            <ul className="widget-list">
              {changes.items.slice(0, SHOW).map((item) => (
                <li key={`${item.older.chunkID}-${item.newer.chunkID}`}>
                  <span className="change-tag">{item.kind === "superseded" ? "Updated" : "Differs"}</span>{" "}
                  {plain(item.summary || item.topic || fileName(item.newer.path))}
                  <span className="muted widget-src"> · {fileName(item.newer.path)} · {item.newer.date}</span>
                </li>
              ))}
            </ul>
          ) : scanning ? (
            <p className="muted" role="status">Comparing related notes…</p>
          ) : (
            changes?.phase === "done" && <p className="muted">Nothing has changed. Your notes agree.</p>
          )}
        </Widget>

        <Widget title="Decisions" count={latest ? String(latest.length) : null} to="decisions" onNavigate={onNavigate}>
          {latest === null && <p className="muted" role="status">Loading decisions…</p>}
          {latest?.length === 0 && <p className="muted">No decisions found.</p>}
          {latest && latest.length > 0 && (
            <ul className="widget-list">
              {latest.slice(0, SHOW).map((d, i) => (
                <li key={`${d.chunkID}-${i}`}>
                  {plain(d.text)}
                  <span className="muted widget-src"> · {fileName(d.path)} · {d.date}</span>
                </li>
              ))}
            </ul>
          )}
        </Widget>

        <Widget title="To-dos" count={open ? `${open.length} open` : null} to="todos" onNavigate={onNavigate}>
          {open === null && <p className="muted" role="status">Loading to-dos…</p>}
          {open?.length === 0 && <p className="muted">Nothing open.</p>}
          {open && open.length > 0 && (
            <ul className="widget-list">
              {open.slice(0, SHOW).map((t, i) => (
                <li key={`${t.chunkID}-${i}`}>
                  {t.task}
                  <span className="muted widget-src"> · {fileName(t.path)} · {t.date}</span>
                </li>
              ))}
            </ul>
          )}
        </Widget>
      </div>
    </div>
  );
}
