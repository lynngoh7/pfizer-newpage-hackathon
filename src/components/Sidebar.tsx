/**
 * Fixed left sidebar: brand, navigation, engine status, Settings.
 * Polls /api/health every 5 s so the user can see the local engine is alive.
 * The status is a plain label: dot colour and text change, nothing to click.
 * `View` is the single source of truth for screen ids.
 */
import { useEffect, useState } from "react";
import { health } from "../lib/api";

export type View = "home" | "search" | "decisions" | "conflicts" | "privacy" | "settings";

interface Props {
  view: View;
  onNavigate: (v: View) => void;
}

const NAV: { id: View; label: string }[] = [
  { id: "search", label: "Search" },
  { id: "decisions", label: "Decisions & To-dos" },
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
          Settings
        </button>
      </div>
    </aside>
  );
}
