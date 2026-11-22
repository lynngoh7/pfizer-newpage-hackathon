/**
 * Home: the manager summary (P1 #11). Three quiet lists: notes that changed,
 * latest decisions, and open to-dos. One line per item (newest first) and a
 * "See all" link to the full page. Everything comes from the in-memory index;
 * nothing is saved.
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

/** Markdown marks read as noise in a one-line summary. */
function plain(text: string): string {
  return text
    .replace(/^\s*#{1,6}\s+/gm, "")
    .replace(/(\*\*|__)(.+?)\1/g, "$2")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\s*\n\s*/g, " ")
    .trim();
}

const fileName = (path: string) => path.split(/[\\/]/).pop() || path;

interface Row {
  key: string;
  text: string;
  date: string;
  title: string; // full text + source file on hover, since the line is truncated
}

const byNewest = (a: Row, b: Row) => b.date.localeCompare(a.date); // ISO dates sort as strings

interface SectionProps {
  title: string;
  to: View;
  rows: Row[] | null;
  loading: string;
  empty: string;
  onNavigate: (v: View) => void;
}

function Section({ title, to, rows, loading, empty, onNavigate }: SectionProps) {
  const id = `home-${to}`;
  return (
    <section className="home-section" aria-labelledby={id}>
      <div className="home-section-head">
        <h2 id={id}>
          {title}
          {rows && rows.length > 0 && <span className="home-count">{rows.length}</span>}
        </h2>
        <button className="link" onClick={() => onNavigate(to)} aria-label={`See all ${title.toLowerCase()}`}>
          See all
        </button>
      </div>
      {rows === null && <p className="muted home-empty" role="status">{loading}</p>}
      {rows?.length === 0 && <p className="muted home-empty">{empty}</p>}
      {rows && rows.length > 0 && (
        <ul className="home-list">
          {rows.slice(0, SHOW).map((r) => (
            <li key={r.key} title={r.title}>
              <span className="home-text">{r.text}</span>
              <span className="home-date">{r.date}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

interface Props {
  decisions: ExtractedDecision[] | null;
  todos: ExtractedTodo[] | null;
  onNavigate: (v: View) => void;
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

  const noEngine = changes?.phase === "no_engine";
  const changeRows: Row[] | null =
    changes && (changes.phase === "done" || noEngine || changes.items.length > 0)
      ? changes.items.map((item) => {
          const text = plain(item.summary || item.topic || fileName(item.newer.path));
          return {
            key: `${item.older.chunkID}-${item.newer.chunkID}`,
            text,
            date: item.newer.date,
            title: `${text}\n${fileName(item.older.path)} → ${fileName(item.newer.path)}`,
          };
        })
      : null;

  const decisionRows: Row[] | null = decisions
    ? decisions
        .map((d, i) => {
          const text = plain(d.text);
          return { key: `${d.chunkID}-${i}`, text, date: d.date, title: `${text}\n${fileName(d.path)}` };
        })
        .sort(byNewest)
    : null;

  // Index must be the original position so the key matches the To-dos page ticks.
  const todoRows: Row[] | null = todos
    ? todos
        .map((t, i) => ({ t, i }))
        .filter(({ t, i }) => !(ticked.get(todoKey(t, i)) ?? t.completed))
        .map(({ t, i }) => ({ key: `${t.chunkID}-${i}`, text: t.task, date: t.date, title: `${t.task}\n${fileName(t.path)}` }))
        .sort(byNewest)
    : null;

  return (
    <div className="home">
      <h1>What are you looking for?</h1>
      <p className="muted">Search or ask a question. Answers come only from your files, on this computer.</p>

      <div className="home-summary">
        <Section
          title="Changes"
          to="changes"
          rows={changeRows}
          loading="Comparing related notes…"
          empty={noEngine ? "Start Ollama to compare notes." : "Nothing has changed."}
          onNavigate={onNavigate}
        />
        <Section title="Decisions" to="decisions" rows={decisionRows} loading="Loading decisions…" empty="No decisions found." onNavigate={onNavigate} />
        <Section title="Open to-dos" to="todos" rows={todoRows} loading="Loading to-dos…" empty="Nothing open." onNavigate={onNavigate} />
      </div>
    </div>
  );
}
