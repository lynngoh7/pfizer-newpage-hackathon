interface Source {
  path: string;
  where: string;
  snippet: string;
  flag: "superseded" | "newer" | "conflict" | null;
  //used to label how notes relate to each other, e.g. if a note supersedes another note, or if there is a conflict between notes
}

interface SearchResponse {
  status: "ok" | "no_support";
  answer: string | null;
  sources: Source[];
}

const DEMO_RESPONSE: SearchResponse = {
  status: "ok",
  answer:
    "The team first chose Corvid Analytics, then dropped it and switched to Ledgerly. The beta date moved from 3 November to 17 November [1] [2].",
  sources: [
    {
      path: "sample_notes/meetings/2026-09-22 Lighthouse vendor decision.md",
      where: "Decision",
      snippet:
        "We are going with Corvid Analytics. Cheapest, fastest to integrate, Ollie's team has used it before.",
      flag: "superseded",
    },
    {
      path: "sample_notes/meetings/2026-10-20 Lighthouse vendor rethink.md",
      where: "Decision",
      snippet:
        "We're dropping Corvid and switching to Ledgerly (UK-hosted, London region). This replaces the 22 Sep decision. Beta moves from 3 Nov to 17 Nov to absorb the longer integration.",
      flag: "newer",
    },
  ],
};

function isQuestion(query: string): boolean {
  return (
    query.trim().endsWith("?") ||
    /^(who|what|when|where|why|how|did|does|is|are|can|could|should)\b/i.test(query.trim())
  );
}

function matchesDemo(query: string): boolean {
  return /\b(lighthouse|corvid|ledgerly|vendor|beta|decision)\b/i.test(query);
}

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() || path;
}

function Answer({ text }: { text: string }) {
  const parts = text.split(/(\[\d+\])/g);

  return (
    <p className="answer-text">
      {parts.map((part, index) => {
        const citation = /^\[(\d+)\]$/.exec(part);
        return citation ? (
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

function SourceCard({ source, index }: { source: Source; index: number }) {
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
    </li>
  );
}

export default function SearchResults({ query }: { query: string }) {
  const trimmedQuery = query.trim();
  if (!trimmedQuery) {
    return (
      <section className="search-results" aria-labelledby="results-title">
        <p className="results-eyebrow">Search</p>
        <h1 id="results-title">Search your notes</h1>
        <p className="results-note">Enter a keyword or ask a question in the search bar above.</p>
      </section>
    );
  }

  const response = matchesDemo(trimmedQuery)
    ? DEMO_RESPONSE
    : ({ status: "no_support", answer: null, sources: [] } satisfies SearchResponse);
  const answer = isQuestion(trimmedQuery) ? response.answer : null;

  return (
    <section className="search-results" aria-labelledby="results-title">
      <p className="results-eyebrow">Search results · Mock data</p>
      <h1 id="results-title" aria-live="polite">
        Results for “{trimmedQuery}”
      </h1>
      <p className="results-note">
        Demo results use the sample Lighthouse notes. Search is not connected to the backend yet.
      </p>

      {response.status === "no_support" ? (
        <div className="card no-results" role="status">
          <h2>No supporting notes found.</h2>
          <p className="muted">Try “Lighthouse”, “Corvid”, “Ledgerly”, or “vendor decision”.</p>
        </div>
      ) : (
        <>
          {answer && (
            <section className="card answer-card" aria-labelledby="answer-title">
              <div className="answer-heading">
                <h2 id="answer-title">Answer</h2>
                <span className="answer-label">Based on your notes</span>
              </div>
              <Answer text={answer} />
            </section>
          )}

          <section aria-labelledby="sources-title">
            <div className="sources-heading">
              <h2 id="sources-title">Sources</h2>
              <span className="muted">{response.sources.length} notes</span>
            </div>
            <ol className="source-list">
              {response.sources.map((source, index) => (
                <SourceCard key={source.path} source={source} index={index} />
              ))}
            </ol>
          </section>
        </>
      )}
    </section>
  );
}
