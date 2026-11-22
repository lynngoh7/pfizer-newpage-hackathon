import { ExtractedDecision } from "../lib/api";

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

function location(decision: ExtractedDecision): string {
  if (decision.path.toLowerCase().endsWith(".pdf")) {
    return decision.start === decision.end
      ? `page ${decision.start + 1}`
      : `pages ${decision.start + 1}–${decision.end + 1}`;
  }
  return decision.start === decision.end
    ? `line ${decision.start + 1}`
    : `lines ${decision.start + 1}–${decision.end + 1}`;
}

function formatDecision(text: string) {
  return text.split(/(\*\*.+?\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

interface Props {
  decisions: ExtractedDecision[] | null;
  error: string | null;
  onRetry: () => void;
}

export default function Decisions({ decisions, error, onRetry }: Props) {
  return (
    <div className="page">
      <h2>Decisions</h2>
      <p className="muted lead">Explicit decisions found in your notes, with their original source.</p>
      {error && (
        <div>
          <p className="error" role="alert">Could not load decisions: {error}</p>
          <button className="btn" onClick={onRetry}>Try again</button>
        </div>
      )}
      {!error && decisions === null && <p className="muted" role="status">Loading decisions…</p>}
      {!error && decisions?.length === 0 && (
        <p className="muted">No explicit decisions found in the indexed notes.</p>
      )}
      {decisions?.map((decision, index) => (
        <article className="card" key={`${decision.chunkID}-${index}`}>
          <p>{formatDecision(decision.text)}</p>
          <p className="muted todo-source" title={decision.path}>
            {fileName(decision.path)} · {decision.date} · {location(decision)}
          </p>
        </article>
      ))}
    </div>
  );
}
