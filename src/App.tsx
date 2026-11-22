/**
 * Root view switch. Owns the current view and the latest query.
 *
 * To add a screen: add its id to `View` in Sidebar.tsx, a case below, and a
 * page component in src/pages/. Keep heavy views lazy-loaded (React.lazy) once
 * they carry real code; everything here is intentionally tiny.
 *
 * Fills in: step 3 (search results), step 4 (answer + citations),
 * step 6 (decisions, changes). Privacy (step 5) is lazy-loaded.
 */
import { lazy, Suspense, useEffect, useState } from "react";
import Sidebar, { View } from "./components/Sidebar";
import SearchBar from "./components/SearchBar";
import Home from "./pages/Home";
import Decisions from "./pages/Decisions";
import Todos from "./pages/Todos";
import SearchResults from "./pages/SearchResults";
import Settings from "./pages/Settings";
import { ExtractedDecision, ExtractedTodo, getDecisions, getTodos } from "./lib/api";

const TODO_RETRY_DELAY_MS = 1000;
const TODO_MAX_ATTEMPTS = 60;
const DECISION_RETRY_DELAY_MS = 1000;
const DECISION_MAX_ATTEMPTS = 60;

// Lazy: this page's code downloads only when first opened, keeping startup fast.
const Privacy = lazy(() => import("./pages/Privacy"));
const NewNote = lazy(() => import("./pages/NewNote"));
const Changes = lazy(() => import("./pages/Changes"));

export default function App() {
  const [view, setView] = useState<View>("home");
  const [query, setQuery] = useState("");
  const [todos, setTodos] = useState<ExtractedTodo[] | null>(null);
  const [todosError, setTodosError] = useState<string | null>(null);
  const [todoLoadAttempt, setTodoLoadAttempt] = useState(0);
  const [decisions, setDecisions] = useState<ExtractedDecision[] | null>(null);
  const [decisionsError, setDecisionsError] = useState<string | null>(null);
  const [decisionLoadAttempt, setDecisionLoadAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    async function loadTodos() {
      for (let attempt = 1; attempt <= TODO_MAX_ATTEMPTS && active; attempt += 1) {
        try {
          const { todos: extracted } = await getTodos();
          if (active) {
            setTodos(extracted);
            setTodosError(null);
          }
          return;
        } catch (reason: unknown) {
          if (attempt === TODO_MAX_ATTEMPTS) {
            if (active) {
              setTodosError(reason instanceof Error ? reason.message : String(reason));
            }
            return;
          }
          await new Promise((resolve) => setTimeout(resolve, TODO_RETRY_DELAY_MS));
        }
      }
    }

    void loadTodos();
    return () => {
      active = false;
    };
  }, [todoLoadAttempt]);

  useEffect(() => {
    let active = true;
    async function loadDecisions() {
      for (let attempt = 1; attempt <= DECISION_MAX_ATTEMPTS && active; attempt += 1) {
        try {
          const { decisions: extracted } = await getDecisions();
          if (active) {
            setDecisions(extracted);
            setDecisionsError(null);
          }
          return;
        } catch (reason: unknown) {
          if (attempt === DECISION_MAX_ATTEMPTS) {
            if (active) {
              setDecisionsError(reason instanceof Error ? reason.message : String(reason));
            }
            return;
          }
          await new Promise((resolve) => setTimeout(resolve, DECISION_RETRY_DELAY_MS));
        }
      }
    }

    void loadDecisions();
    return () => {
      active = false;
    };
  }, [decisionLoadAttempt]);

  function onSearch(q: string) {
    setQuery(q);
    setView("search");
  }

  // Pick the page for the current view. No router library: one switch is enough.
  let main;
  switch (view) {
    case "home":
      main = <Home decisions={decisions} todos={todos} onNavigate={setView} />;
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
    case "todos":
      main = (
        <Todos
          todos={todos}
          error={todosError}
          onRetry={() => {
            setTodosError(null);
            setTodoLoadAttempt((attempt) => attempt + 1);
          }}
        />
      );
      break;
    case "decisions":
      main = (
        <Decisions
          decisions={decisions}
          error={decisionsError}
          onRetry={() => {
            setDecisionsError(null);
            setDecisionLoadAttempt((attempt) => attempt + 1);
          }}
        />
      );
      break;
    case "changes":
      main = (
        <Suspense fallback={null}>
          <Changes />
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
