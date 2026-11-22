/**
 * Fixed left sidebar: brand, navigation, engine status, Settings.
 * Polls /api/health every 5 s so the user can see the local engine is alive.
 * The status is a plain label: dot colour and text change, nothing to click.
 * `View` is the single source of truth for screen ids.
 */
import { useEffect, useState } from "react";
import { health } from "../lib/api";

export type View = "home" | "search" | "newnote" | "decisions" | "todos" | "conflicts" | "privacy" | "settings";

interface Props {
  view: View;
  onNavigate: (v: View) => void;
}

// Icon paths from Lucide (ISC licence), the set Obsidian uses. Inlined so
// nothing is fetched and no icon package is added to the bundle.
const ICONS: Record<Exclude<View, "home">, JSX.Element> = {
  search: <><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></>,
  newnote: <><path d="M12 20h9" /><path d="M16.38 3.62a1 1 0 0 1 3 3L7.37 18.64a2 2 0 0 1-.86.5l-2.87.84a.5.5 0 0 1-.62-.62l.84-2.87a2 2 0 0 1 .5-.86z" /></>,
  decisions: <><path d="m3 17 2 2 4-4" /><path d="m3 7 2 2 4-4" /><path d="M13 6h8" /><path d="M13 12h8" /><path d="M13 18h8" /></>,
  todos: <><path d="m3 17 2 2 4-4" /><path d="M13 18h8" /><path d="M13 6h8" /><path d="M13 12h8" /><path d="m3 7 2 2 4-4" /></>,
  conflicts: <><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3" /><path d="M12 9v4" /><path d="M12 17h.01" /></>,
  privacy: <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />,
  settings: <><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></>,
};

// Decorative: the button text already names the tab.
function NavIcon({ id }: { id: Exclude<View, "home"> }) {
  return (
    <svg className="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {ICONS[id]}
    </svg>
  );
}

const NAV: { id: Exclude<View, "home">; label: string }[] = [
  { id: "search", label: "Search" },
  { id: "newnote", label: "New note" },
  { id: "decisions", label: "Decisions" },
  { id: "todos", label: "To-dos" },
  { id: "conflicts", label: "Conflicts" },
  { id: "privacy", label: "Privacy" },
];

type Backend = "checking" | "online" | "offline";

export default function Sidebar({ view, onNavigate }: Props) {
  const [backend, setBackend] = useState<Backend>("checking");

  useEffect(() => {
    let alive = true; // stops setState after the component is gone
    async function ping() {
      try {
        await health();
        if (alive) setBackend("online");
      } catch {
        if (alive) setBackend("offline");
      }
    }
    ping();
    const t = setInterval(ping, 5000);
    // Cleanup when the sidebar unmounts: stop polling.
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  return (
    <aside className="sidebar">
      <button className="brand" onClick={() => onNavigate("home")} aria-label="Home">
        <span className="logo" aria-hidden="true" />
        <span className="brand-name">Local Notes</span>
      </button>

      <nav className="nav" aria-label="Main">
        {NAV.map((n) => (
          <button
            key={n.id}
            className={`nav-item ${view === n.id ? "active" : ""}`}
            aria-current={view === n.id ? "page" : undefined}
            onClick={() => onNavigate(n.id)}
          >
            <NavIcon id={n.id} />
            {n.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        {/* A label, not a button. Announced only when it changes (e.g. engine goes offline); the colour dot alone isn't enough. */}
        <div className={`status status-${backend}`} aria-live="polite">
          <span className="dot" aria-hidden="true" />
          {backend === "checking" && "Connecting…"}
          {backend === "online" && "Local engine ready"}
          {backend === "offline" && "Engine offline"}
        </div>
        <button
          className={`nav-item ${view === "settings" ? "active" : ""}`}
          aria-current={view === "settings" ? "page" : undefined}
          onClick={() => onNavigate("settings")}
        >
          <NavIcon id="settings" />
          Settings
        </button>
      </div>
    </aside>
  );
}
