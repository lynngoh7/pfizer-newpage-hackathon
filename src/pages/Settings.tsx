/**
 * Settings: engine info and clear data. Folder access lives on the Privacy
 * page, so everything about what the app sees and keeps is in one place.
 * "Forget everything" is the same component as on the Privacy page.
 */
import { useEffect, useState } from "react";
import { health, Health } from "../lib/api";
import ForgetButton from "../components/ForgetButton";

export default function Settings({ onOpenPrivacy }: { onOpenPrivacy: () => void }) {
  const [info, setInfo] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    health().then(setInfo).catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="page">
      <h2>Settings</h2>

      <section className="card">
        <h3>Local engine</h3>
        {error && <p className="error">Could not reach the local engine: {error}</p>}
        {info && (
          <dl className="kv">
            <dt>Status</dt>
            <dd>{info.status}</dd>
            <dt>Version</dt>
            <dd>{info.version}</dd>
            <dt>Mode</dt>
            <dd>{info.read_only ? "Read-only" : "Read/write"}</dd>
            <dt>Network</dt>
            <dd>{info.network}</dd>
          </dl>
        )}
      </section>

      <section className="card">
        <h3>Data</h3>
        <p className="muted">
          The app keeps your notes in memory for this session only and writes nothing to disk.{" "}
          Choose which folders it can see, and check for yourself, on the{" "}
          <button className="link" onClick={onOpenPrivacy}>Privacy page</button>.
        </p>
        <ForgetButton />
      </section>
    </div>
  );
}
