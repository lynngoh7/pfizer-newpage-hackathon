import { useEffect, useRef, useState } from "react";
import {
  ensureSearchIndex,
  IndexStatus,
  openFile,
  reindex,
  SearchResponse,
  SearchSource,
  searchNotes,
} from "../lib/api";

function isQuestion(query: string): boolean {
  return (
    query.trim().endsWith("?") ||
    /^(who|what|when|where|why|how|did|does|is|are|can|could|should)\b/i.test(query.trim())
  );
}

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

function Answer({ text, sourceCount }: { text: string; sourceCount: number }) {
  const parts = text.split(/(\[\d+\])/g);

  return (
    <p className="answer-text">
      {parts.map((part, index) => {
        const citation = /^\[(\d+)\]$/.exec(part);
        // Only link numbers that match a source card; anything else stays plain text.
        const n = citation ? Number(citation[1]) : 0;
        return citation && n >= 1 && n <= sourceCount ? (
          <a
            className="answer-citation"
            href={`#source-${citation[1]}`}
            key={`${part}-${index}`}
            aria-label={`Jump to source ${citation[1]}`}
          >
            {part}
          </a>
        ) : (
          part
        );
      })}
    </p>
  );
}

function SourceCard({ source, index, onOpen }: { source: SearchSource; index: number; onOpen: () => void }) {
  const [openError, setOpenError] = useState<string | null>(null);

  // Opens in the user's own editor; this app never edits the file itself.
  async function open() {
    setOpenError(null);
    try {
      await openFile(source.path);
      onOpen();
    } catch (e) {
      setOpenError(String(e));
    }
  }

  return (
    <li className="source-card card" id={`source-${index + 1}`}>
      <div className="source-heading">
        <div className="source-file">
          <span className="source-number" aria-hidden="true">
            {index + 1}
          </span>
          <div>
            <h3>{fileName(source.path)}</h3>
            <p className="source-path">{source.path}</p>
          </div>
        </div>
        {source.flag && (
          <span className={`source-flag source-flag-${source.flag}`}>
            {source.flag === "superseded" ? "Superseded" : source.flag === "newer" ? "Newer note" : "Conflict"}
          </span>
        )}
      </div>
      <p className="source-location">{source.where}</p>
      <blockquote className="source-excerpt">{source.snippet}</blockquote>
      <div className="source-actions">
        <button className="btn btn-small" onClick={open} aria-label={`Open ${fileName(source.path)} in your editor`}>
          Open in editor
        </button>
        {openError && <span className="error">{openError}</span>}
      </div>
    </li>
  );
}

export default function SearchResults({ query }: { query: string }) {
  const trimmedQuery = query.trim();
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [index, setIndex] = useState<IndexStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const editing = useRef(false);

  // After "Open in editor", the user edits elsewhere. When they come back to
  // this window, re-read the allowed folders and re-run the search so their
  // changes show up. Only after an Open, so normal focus changes cost nothing.
  useEffect(() => {
    async function onFocus() {
      if (!editing.current) return;
      editing.current = false;
      try {
        await reindex();
      } catch {
        // Search below shows its own error if the backend is down.
      }
      setAttempt((current) => current + 1);
    }
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, []);

  useEffect(() => {
    let active = true;
    setResponse(null);
    setIndex(null);
    setError(null);
    if (!trimmedQuery) {
      setLoading(false);
      return () => {
        active = false;
      };
    }

    setLoading(true);
    async function runSearch() {
      try {
        const status = await ensureSearchIndex();
        if (!active) return;
        setIndex(status);
        if (status.files === 0) {
          setResponse({ status: "no_support", answer: null, sources: [] });
          return;
        }
        const result = await searchNotes(trimmedQuery);
        if (active) setResponse(result);
      } catch (e) {
        if (active) setError(String(e));
      } finally {
        if (active) setLoading(false);
      }
    }
    void runSearch();

    return () => {
      active = false;
    };
  }, [trimmedQuery, attempt]);

  if (!trimmedQuery) {
    return (
      <section className="search-results" aria-labelledby="results-title">
        <p className="results-eyebrow">Search</p>
        <h1 id="results-title">Search your notes</h1>
        <p className="results-note">Enter a keyword or ask a question in the search bar above.</p>
      </section>
    );
  }

  const answer = isQuestion(trimmedQuery) ? response?.answer : null;
  const noFiles = index?.files === 0;
  const meaningIndexing = index?.phase === "meaning" || index?.phase === "grouping";

  return (
    <section className="search-results" aria-labelledby="results-title">
      <p className="results-eyebrow">Search results</p>
      <h1 id="results-title" aria-live="polite">
        Results for “{trimmedQuery}”
      </h1>
      <p className="results-note">Search runs on this computer and shows excerpts from your allowed files.</p>

      {loading && <p className="muted" role="status">Searching your notes…</p>}
      {error && (
        <div className="card search-error" role="alert">
          <h2>Couldn’t search your notes</h2>
          <p>{error}</p>
          <button className="btn" onClick={() => setAttempt((current) => current + 1)}>
            Try again
          </button>
        </div>
      )}
      {!loading && !error && response && response.status === "no_support" && (
        <div className="card no-results" role="status">
          <h2>{noFiles ? "No supported files are indexed." : "No supporting notes found."}</h2>
          <p className="muted">
            {noFiles
              ? "Choose folders or files on the Privacy page, then search again."
              : "Try different words or ask about another topic."}
          </p>
        </div>
      )}
      {!loading && !error && response?.status === "ok" && (
        <>
          {meaningIndexing && (
            <p className="muted" role="status">
              Keyword results are ready. Meaning-based indexing is continuing in the background.
            </p>
          )}
          {isQuestion(trimmedQuery) && !answer && (
            <p className="muted">
              Showing matching notes. AI-generated answers aren’t available yet.
            </p>
          )}
          {answer && (
            <section className="card answer-card" aria-labelledby="answer-title">
              <div className="answer-heading">
                <h2 id="answer-title">Answer</h2>
                <span className="answer-label">Based on your notes</span>
              </div>
              <Answer text={answer} sourceCount={response.sources.length} />
            </section>
          )}

          <section aria-labelledby="sources-title">
            <div className="sources-heading">
              <h2 id="sources-title">Sources</h2>
              <span className="muted">{response.sources.length} notes</span>
            </div>
            <ol className="source-list">
              {response.sources.map((source, index) => (
                <SourceCard
                  key={source.chunkID}
                  source={source}
                  index={index}
                  onOpen={() => (editing.current = true)}
                />
              ))}
            </ol>
          </section>
        </>
      )}
    </section>
  );
}
