/**
 * Root view switch. Owns the current view and the latest query.
 *
 * To add a screen: add its id to `View` in Sidebar.tsx, a case below, and a
 * page component in src/pages/. Keep heavy views lazy-loaded (React.lazy) once
 * they carry real code; everything here is intentionally tiny.
 *
 * Fills in: step 3 (search results), step 4 (answer + citations),
 * step 6 (decisions, conflicts). Privacy (step 5) is lazy-loaded.
 */
import { lazy, Suspense, useState } from "react";
import Sidebar, { View } from "./components/Sidebar";
import SearchBar from "./components/SearchBar";
import Home from "./pages/Home";
import Placeholder from "./pages/Placeholder";
import SearchResults from "./pages/SearchResults";
import Settings from "./pages/Settings";

// Lazy: this page's code downloads only when first opened, keeping startup fast.
const Privacy = lazy(() => import("./pages/Privacy"));
const NewNote = lazy(() => import("./pages/NewNote"));
const Conflicts = lazy(() => import("./pages/Conflicts"));

export default function App() {
  const [view, setView] = useState<View>("home");
  const [query, setQuery] = useState("");

  function onSearch(q: string) {
    setQuery(q);
    setView("search");
  }

  // Pick the page for the current view. No router library: one switch is enough.
  let main;
  switch (view) {
    case "home":
      main = <Home />;
      break;
    case "search":
      main = <SearchResults query={query} />;
      break;
    case "newnote":
      main = (
        <Suspense fallback={null}>
          <NewNote />
        </Suspense>
      );
      break;
    case "decisions":
      main = <Placeholder title="Decisions & To-dos" note="Extraction arrives in build step 6." />;
      break;
    case "conflicts":
      main = (
        <Suspense fallback={null}>
          <Conflicts />
        </Suspense>
      );
      break;
    case "privacy":
      main = (
        // Suspense shows nothing for the split second the lazy page loads.
        <Suspense fallback={null}>
          <Privacy />
        </Suspense>
      );
      break;
    case "settings":
      main = <Settings onOpenPrivacy={() => setView("privacy")} />;
      break;
  }

  return (
    <div className="app">
      <Sidebar view={view} onNavigate={setView} />
      <div className="main">
        <SearchBar onSubmit={onSearch} />
        {/* <main> landmark: VoiceOver users can jump straight to the page content. */}
        <main className="content">{main}</main>
      </div>
    </div>
  );
}
