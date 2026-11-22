/**
 * Upcoming: every dated line found in the notes (from /api/upcoming, built by
 * backend/app/dates.py). Two lists: open to-dos whose date has passed, then
 * everything from today on, soonest first. Past lines that aren't open to-dos
 * are history, not plans, so they are left out. Loaded once by App.tsx and
 * passed in, like Decisions and To-dos. Nothing is saved.
 */
import { useState } from "react";
import { DatedLine, openFile } from "../lib/api";

const fileName = (path: string) => path.split(/[\\/]/).pop() || path;
const longDate = (iso: string) =>
  new Date(`${iso}T00:00`).toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", year: "numeric" });

/** The line without its list or checkbox marker, and without Markdown bold. */
export const lineText = (text: string) =>
  text
    .replace(/^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?/, "")
    .replace(/(\*\*|__)(.+?)\1/g, "$2")
    .trim();

export const todayIso = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

interface Props {
  items: DatedLine[] | null;
  error: string | null;
  onRetry: () => void;
}

export default function Upcoming({ items, error, onRetry }: Props) {
  const [openError, setOpenError] = useState<string | null>(null);
  const today = todayIso();
  const overdue = items?.filter((d) => d.todo && d.when < today) ?? [];
  const ahead = items?.filter((d) => d.when >= today) ?? [];

  // Hands the file to the user's own app (path-checked, audit-logged); §6 read-only.
  const open = (path: string) => {
    setOpenError(null);
    openFile(path).catch((e: unknown) => setOpenError(e instanceof Error ? e.message : String(e)));
  };

  const list = (rows: DatedLine[], late: boolean) =>
    rows.map((d, i) => (
      <article className="card todo-card" key={`${d.chunkID}-${i}`}>
        <div className="todo-row">
          <span className="todo-task">
            <span className={late ? "home-row-date overdue" : "home-row-date"}>{longDate(d.when)}</span>{" "}
            {lineText(d.text)}
          </span>
          <button className="btn btn-small todo-edit" onClick={() => open(d.path)}
            title={`Open ${fileName(d.path)} in your editor`}>
            Open note
          </button>
        </div>
        <p className="muted todo-source" title={d.path}>
          {fileName(d.path)} · written {d.noteDate}{d.todo ? " · to-do" : ""}
        </p>
      </article>
    ));

  return (
    <div className="page">
      <h2>Upcoming</h2>
      <p className="muted lead">
        Dates found in your notes. Days like “Friday” are read from the date the note was written;
        vague ones like “end of month” are skipped.
      </p>
      {error && (
        <div>
          <p className="error" role="alert">Could not load dates: {error}</p>
          <button className="btn" onClick={onRetry}>Try again</button>
        </div>
      )}
      {openError && <p className="error" role="alert">Could not open the note: {openError}</p>}
      {!error && items === null && <p className="muted" role="status">Loading dates…</p>}
      {items && overdue.length === 0 && ahead.length === 0 && (
        <p className="muted">No upcoming dates found in the indexed notes.</p>
      )}
      {overdue.length > 0 && (
        <section aria-labelledby="upcoming-overdue">
          <h3 id="upcoming-overdue">Overdue to-dos</h3>
          {list(overdue, true)}
        </section>
      )}
      {ahead.length > 0 && (
        <section aria-labelledby="upcoming-ahead">
          <h3 id="upcoming-ahead">Coming up</h3>
          {list(ahead, false)}
        </section>
      )}
    </div>
  );
}
