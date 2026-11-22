import { useState } from "react";
import { ExtractedTodo, openFile } from "../lib/api";

// Ticks are session-only: kept in memory, never written back to the note
// (read-only rule, §6) or to disk (No copies). Module scope so they survive
// switching pages; they reset when the app quits.
export const ticked = new Map<string, boolean>();

/** Shared with the Home summary so both count the same ticks. */
export const todoKey = (todo: ExtractedTodo, index: number) => `${todo.chunkID}-${index}-${todo.task}`;

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

interface Props {
  todos: ExtractedTodo[] | null;
  error: string | null;
  onRetry: () => void;
}

export default function Todos({ todos, error, onRetry }: Props) {
  const [, rerender] = useState(0);
  const [openError, setOpenError] = useState<string | null>(null);
  // Hands the file to the user's own editor (path-checked, audit-logged);
  // the app itself never writes to the note (§6 read-only).
  const edit = (path: string) => {
    setOpenError(null);
    openFile(path).catch((e: unknown) => setOpenError(e instanceof Error ? e.message : String(e)));
  };
  const toggle = (key: string, done: boolean) => {
    ticked.set(key, !done);
    rerender((n) => n + 1);
  };
  return (
    <div className="page">
      <h2>To-dos</h2>
      <p className="muted lead">
        Checklist items found in your notes, with their original file and date.
      </p>

      <p className="todo-notice" role="note">
        <strong>Ticks here are for this session only,</strong> to maintain the read-only rule. They are not saved and
        do not change your notes. To tick a task for good, use <strong>Edit in note</strong>.
      </p>

      <section aria-labelledby="todos-heading">
        <h3 id="todos-heading">Tasks</h3>
        {error && (
          <div>
            <p className="error" role="alert">Could not load to-dos: {error}</p>
            <button className="btn" onClick={onRetry}>Try again</button>
          </div>
        )}
        {openError && <p className="error" role="alert">Could not open the note: {openError}</p>}
        {!error && todos === null && <p className="muted" role="status">Loading to-dos…</p>}
        {!error && todos?.length === 0 && (
          <p className="muted">No checklist items found in the indexed notes.</p>
        )}
        {todos?.map((todo, index) => {
          const key = todoKey(todo, index);
          const done = ticked.get(key) ?? todo.completed;
          return (
            <article className="card todo-card" key={key}>
              <div className="todo-row">
                <label className={done ? "todo-task todo-completed" : "todo-task"}>
                  <input
                    type="checkbox"
                    className="todo-check"
                    checked={done}
                    onChange={() => toggle(key, done)}
                  />
                  {todo.task}
                </label>
                <button
                  className="btn btn-small todo-edit"
                  onClick={() => edit(todo.path)}
                  title={`Open ${fileName(todo.path)} in your editor to change it there`}
                >
                  Edit in note
                </button>
              </div>
              <p className="muted todo-source" title={todo.path}>
                {fileName(todo.path)} · {todo.date} · lines {todo.start + 1}–{todo.end + 1}
              </p>
            </article>
          );
        })}
      </section>

    </div>
  );
}
