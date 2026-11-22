import { ExtractedTodo } from "../lib/api";

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

interface Props {
  todos: ExtractedTodo[] | null;
  error: string | null;
  onRetry: () => void;
}

export default function Decisions({ todos, error, onRetry }: Props) {
  return (
    <div className="page">
      <h2>To-dos</h2>
      <p className="muted lead">
        Checklist items found in your notes, with their original file and date.
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

    </div>
  );
}
