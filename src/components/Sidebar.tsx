/**
 * Fixed left sidebar: brand, navigation, engine status, Settings.
 * Polls /api/health every 5 s so the user can see the local engine is alive.
 * `View` is the single source of truth for screen ids.
 */
import { useEffect, useState } from "react";
import { health } from "../lib/api";

export type View = "home" | "search" | "decisions" | "conflicts" | "activity" | "settings";

interface Props {
  view: View;
  onNavigate: (v: View) => void;
}

const NAV: { id: View; label: string }[] = [
  { id: "search", label: "Search" },
  { id: "decisions", label: "Decisions & To-dos" },
  { id: "conflicts", label: "Conflicts" },
  { id: "activity", label: "Activity Log" },
];

type Backend = "checking" | "online" | "offline";

export default function Sidebar({ view, onNavigate }: Props) {
  const [backend, setBackend] = useState<Backend>("checking");

  useEffect(() => {
    let alive = true;
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

      <nav className="nav">
        {NAV.map((n) => (
          <button
            key={n.id}
            className={`nav-item ${view === n.id ? "active" : ""}`}
            onClick={() => onNavigate(n.id)}
          >
            {n.label}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className={`status status-${backend}`} title="Local backend (127.0.0.1)">
          <span className="dot" aria-hidden="true" />
          {backend === "checking" && "Connecting…"}
          {backend === "online" && "Local engine ready"}
          {backend === "offline" && "Engine offline"}
        </div>
        <button
          className={`nav-item ${view === "settings" ? "active" : ""}`}
          onClick={() => onNavigate("settings")}
        >
          Settings
        </button>
      </div>
    </aside>
  );
}
