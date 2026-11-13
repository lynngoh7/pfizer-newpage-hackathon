/**
 * Root view switch. Owns the current view and the latest query.
 *
 * To add a screen: add its id to `View` in Sidebar.tsx, a case below, and a
 * page component in src/pages/. Keep heavy views lazy-loaded (React.lazy) once
 * they carry real code; everything here is intentionally tiny.
 *
 * Fills in: step 3 (search results), step 4 (answer + citations),
 * step 5 (activity log), step 6 (decisions, conflicts).
 */
import { useState } from "react";
import Sidebar, { View } from "./components/Sidebar";
import SearchBar from "./components/SearchBar";
import Home from "./pages/Home";
import Placeholder from "./pages/Placeholder";
import Settings from "./pages/Settings";

export default function App() {
  const [view, setView] = useState<View>("home");
  const [query, setQuery] = useState("");

  function onSearch(q: string) {
    setQuery(q);
    setView("search");
  }

  let main;
  switch (view) {
    case "home":
      main = <Home />;
      break;
    case "search":
      main = (
        <Placeholder
          title={query ? `Results for “${query}”` : "Search"}
          note="Keyword search arrives in build step 3; Q&A with verified citations in step 4."
        />
      );
      break;
    case "decisions":
      main = <Placeholder title="Decisions & To-dos" note="Extraction arrives in build step 6." />;
      break;
    case "conflicts":
      main = <Placeholder title="Conflicts" note="Contradiction and superseded-note detection arrives in build step 6." />;
      break;
    case "activity":
      main = <Placeholder title="Activity Log" note="Every file read and tool call will be listed here (build step 5)." />;
      break;
    case "settings":
      main = <Settings />;
      break;
  }

  return (
    <div className="app">
      <Sidebar view={view} onNavigate={setView} />
      <div className="main">
        <SearchBar onSubmit={onSearch} />
        <section className="content">{main}</section>
      </div>
    </div>
  );
}
