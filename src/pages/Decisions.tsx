import { useEffect, useState } from "react";
import { ExtractedTodo, getTodos } from "../lib/api";

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

export default function Decisions() {
  const [todos, setTodos] = useState<ExtractedTodo[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getTodos()
      .then(({ todos: extracted }) => {
        if (active) {
          setTodos(extracted);
          setError(null);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          setError(reason instanceof Error ? reason.message : String(reason));
        }
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="page">
      <h2>Decisions &amp; To-dos</h2>
      <p className="muted lead">
        Checklist items found in your notes, with their original file and date.
      </p>

      <section aria-labelledby="todos-heading">
        <h3 id="todos-heading">To-dos</h3>
        {error && <p className="error" role="alert">Could not load to-dos: {error}</p>}
        {!error && todos === null && <p className="muted" role="status">Loading to-dos…</p>}
        {!error && todos?.length === 0 && (
          <p className="muted">No checklist items found in the indexed notes.</p>
        )}
        {todos?.map((todo, index) => (
          <article className="card todo-card" key={`${todo.chunkID}-${index}`}>
            <p className={todo.completed ? "todo-task todo-completed" : "todo-task"}>
              <span className="todo-state" aria-label={todo.completed ? "Completed" : "Open"}>
                {todo.completed ? "✓" : "○"}
              </span>
              {todo.task}
            </p>
            <p className="muted todo-source" title={todo.path}>
              {fileName(todo.path)} · {todo.date} · lines {todo.start + 1}–{todo.end + 1}
            </p>
          </article>
        ))}
      </section>

      <section aria-labelledby="decisions-heading">
        <h3 id="decisions-heading">Decisions</h3>
        <p className="muted">Decision extraction is not available yet.</p>
      </section>
    </div>
  );
}
