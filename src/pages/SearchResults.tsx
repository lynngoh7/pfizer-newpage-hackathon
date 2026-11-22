import { useEffect, useRef, useState } from "react";
import {
  AskClaim,
  AskResponse,
  ensureSearchIndex,
  IndexStatus,
  askNotes,
  openFile,
  reindex,
  SearchResponse,
  SearchSource,
  searchNotes,
} from "../lib/api";
import MarkdownExcerpt from "../components/MarkdownExcerpt";

type ResultsResponse = SearchResponse | AskResponse;

function isQuestion(query: string): boolean {
  return (
    query.trim().endsWith("?") ||
    /^(who|what|when|where|why|how|did|does|is|are|can|could|should)\b/i.test(query.trim())
  );
}

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

function isMarkdownFile(path: string): boolean {
  return /\.(md|markdown|mkd|mdown)$/i.test(path);
}

function isMarkdownHeadingLocation(location: string): boolean {
  return /^\s{0,3}#{1,6}\s+/.test(location);
}

function Answer({ claims, sources }: { claims: AskClaim[]; sources: SearchSource[] }) {
  const resolvedClaims = claims.map((claim) => ({
    claim,
    citedSources: [...new Set(claim.citations.map((citation) => citation.chunk_id))]
      .map((chunkID) => ({
        chunkID,
        sourceIndex: sources.findIndex((source) => source.chunkID === chunkID),
      }))
      .filter((citation) => citation.sourceIndex !== -1),
  }));
  const hiddenClaimCount = resolvedClaims.filter(({ citedSources }) => citedSources.length === 0).length;
  const hiddenClaimMessage =
    hiddenClaimCount === 1
      ? "One answer claim was hidden because its verified source card was missing."
      : `${hiddenClaimCount} answer claims were hidden because their verified source cards were missing.`;

  return (
    <div className="answer-text">
      {hiddenClaimCount > 0 && (
        <p className="muted" role="status">{hiddenClaimMessage}</p>
      )}
      {resolvedClaims.map(({ claim, citedSources }, claimIndex) => {
        if (citedSources.length === 0) return null;
        return (
          <p className="answer-claim" key={`claim-${claimIndex}`}>
            {claim.text}
            {citedSources.map(({ chunkID, sourceIndex }) => {
              const sourceId = `source-${sourceIndex + 1}`;
              return (
                <a
                  className="answer-citation"
                  href={`#${sourceId}`}
                  key={`${claimIndex}-${chunkID}`}
                  aria-label={`Jump to source ${sourceIndex + 1}`}
                  onClick={() => document.getElementById(sourceId)?.focus()}
                >
                  {" "}[{sourceIndex + 1}]
                </a>
              );
            })}
          </p>
        );
      })}
    </div>
  );
}

function citationQuotesByChunk(response: ResultsResponse | null): Map<number, string[]> {
  const quotesByChunk = new Map<number, string[]>();
  if (!response || !("claims" in response)) return quotesByChunk;

  for (const claim of response.claims) {
    for (const citation of claim.citations) {
      const quotes = quotesByChunk.get(citation.chunk_id) ?? [];
      if (!quotes.includes(citation.quote)) quotes.push(citation.quote);
      quotesByChunk.set(citation.chunk_id, quotes);
    }
  }
  return quotesByChunk;
}

function SourceCard({
  source,
  index,
  onOpen,
  citationQuotes,
}: {
  source: SearchSource;
  index: number;
  onOpen: () => void;
  citationQuotes: string[];
}) {
  const [openError, setOpenError] = useState<string | null>(null);
  const markdown = isMarkdownFile(source.path);
  const showLocation = !markdown || !isMarkdownHeadingLocation(source.where);
  const extraEvidence = citationQuotes.filter((quote) => !source.snippet.includes(quote));

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
    <li className="source-card card" id={`source-${index + 1}`} tabIndex={-1}>
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
      {showLocation && <p className="source-location">{source.where}</p>}
      {extraEvidence.map((quote, quoteIndex) => (
        <blockquote className="source-evidence" key={`${source.chunkID}-${quoteIndex}`}>
          <p className="source-evidence-label">Verified evidence</p>
          {markdown ? <MarkdownExcerpt text={quote} /> : <p>{quote}</p>}
        </blockquote>
      ))}
      <blockquote className="source-excerpt">
        {markdown ? <MarkdownExcerpt text={source.snippet} /> : source.snippet}
      </blockquote>
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
  const question = isQuestion(trimmedQuery);
  const [response, setResponse] = useState<ResultsResponse | null>(null);
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
        const result = question ? await askNotes(trimmedQuery) : await searchNotes(trimmedQuery);
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
  }, [trimmedQuery, question, attempt]);

  if (!trimmedQuery) {
    return (
      <section className="search-results" aria-labelledby="results-title">
        <p className="results-eyebrow">Search</p>
        <h1 id="results-title">Search your notes</h1>
        <p className="results-note">Enter a keyword or ask a question in the search bar above.</p>
      </section>
    );
  }

  const answerClaims =
    question && response && "claims" in response ? response.claims : [];
  const noFiles = index?.files === 0;
  const meaningIndexing = index?.phase === "meaning" || index?.phase === "grouping";
  const sourceCount = response?.sources.length ?? 0;
  const sourceCountLabel = `${sourceCount} ${sourceCount === 1 ? "source" : "sources"}`;
  const citationQuotes = citationQuotesByChunk(response);

  return (
    <section className="search-results" aria-labelledby="results-title" aria-busy={loading}>
      <p className="results-eyebrow">Search results</p>
      <h1 id="results-title" aria-live="polite">
        Results for “{trimmedQuery}”
      </h1>
      <p className="results-note">Search runs on this computer and shows excerpts from your allowed files.</p>

      {loading && (
        <p className="muted" role="status">
          {question ? "Searching your notes and verifying an answer…" : "Searching your notes…"}
        </p>
      )}
      {error && (
        <div className="card search-error" role="alert">
          <h2>{question ? "Couldn’t answer your question" : "Couldn’t search your notes"}</h2>
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
          {answerClaims.length > 0 && (
            <section className="card answer-card" aria-labelledby="answer-title">
              <div className="answer-heading">
                <h2 id="answer-title">Answer</h2>
                <span className="answer-label">Based on your notes</span>
              </div>
              <Answer claims={answerClaims} sources={response.sources} />
            </section>
          )}
          {question && response.status === "ok" && answerClaims.length === 0 && (
            <p className="muted" role="status">No verified answer claims were returned.</p>
          )}

          <section aria-labelledby="sources-title">
            <div className="sources-heading">
              <h2 id="sources-title" aria-label={`Sources, ${sourceCountLabel}`}>Sources</h2>
              <span className="muted" role="status" aria-live="polite" aria-atomic="true">
                {sourceCountLabel}
              </span>
            </div>
            <ol className="source-list">
              {response.sources.map((source, index) => (
                <SourceCard
                  key={source.chunkID}
                  source={source}
                  index={index}
                  onOpen={() => (editing.current = true)}
                  citationQuotes={citationQuotes.get(source.chunkID) ?? []}
                />
              ))}
            </ol>
          </section>
        </>
      )}
    </section>
  );
}
