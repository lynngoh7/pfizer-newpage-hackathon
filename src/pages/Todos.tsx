import { useState } from "react";
import { ExtractedTodo } from "../lib/api";

// Ticks are session-only: kept in memory, never written back to the note
// (read-only rule, §6) or to disk (No copies). Module scope so they survive
// switching pages; they reset when the app quits.
const ticked = new Map<string, boolean>();

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
  const toggle = (key: string, done: boolean) => {
    ticked.set(key, !done);
    rerender((n) => n + 1);
  };
  return (
    <div className="page">
      <h2>To-dos</h2>
      <p className="muted lead">
        Checklist items found in your notes, with their original file and date. Ticks last for this session only and never change your notes.
      </p>

      <section aria-labelledby="todos-heading">
        <h3 id="todos-heading">Tasks</h3>
        {error && (
          <div>
            <p className="error" role="alert">Could not load to-dos: {error}</p>
            <button className="btn" onClick={onRetry}>Try again</button>
          </div>
        )}
        {!error && todos === null && <p className="muted" role="status">Loading to-dos…</p>}
        {!error && todos?.length === 0 && (
          <p className="muted">No checklist items found in the indexed notes.</p>
        )}
        {todos?.map((todo, index) => {
          const key = `${todo.chunkID}-${index}-${todo.task}`;
          const done = ticked.get(key) ?? todo.completed;
          return (
            <article className="card todo-card" key={key}>
              <label className={done ? "todo-task todo-completed" : "todo-task"}>
                <input
                  type="checkbox"
                  className="todo-check"
                  checked={done}
                  onChange={() => toggle(key, done)}
                />
                {todo.task}
              </label>
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
