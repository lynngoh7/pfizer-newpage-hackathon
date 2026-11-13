/**
 * Home / empty state. Deliberately sparse: this grid is where customisable
 * widgets (calendar, to-dos, …) will live later. Not in scope now.
 */
export default function Home() {
  return (
    <div className="home">
      <h1>What are you looking for?</h1>
      <p className="muted">
        Search by keyword or ask a question in plain English. Answers come only from your own
        files, with citations. Nothing leaves this computer.
      </p>
      <div className="widget-grid" aria-hidden="true">
        {/* Reserved for future widgets */}
      </div>
    </div>
  );
}
