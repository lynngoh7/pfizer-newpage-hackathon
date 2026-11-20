/**
 * Settings: what the app runs on and how it keeps notes safe, in plain words.
 *
 * Settings are saved to prefs.json with the folder list (backend/app/prefs.py):
 * setting values only, never note text (One Rule, "no copies").
 * Accessibility comes from the Mac's own settings, so there is nothing to save.
 *
 * Fills in: step 2c (Indexing card: files read, chunks, skipped, re-index),
 * step 4 (AI model card: real model list and warm/unloaded state from Ollama).
 */
import { Fragment, useEffect, useState } from "react";
import { getSettings, health, Health, saveSettings } from "../lib/api";
import ForgetButton from "../components/ForgetButton";

// Fixed until step 4 lists installed models. The picker stays so the layout is final.
// Placeholder name: confirm the demo model in step 4.
const ANSWER_MODELS = ["llama3.2:3b"];
const SEARCH_MODEL = "nomic-embed-text";

// Short labels so they fit the .props label column.
const SAFETY: { fact: string; why: string }[] = [
  {
    fact: "Read-only",
    why: "The app can open your notes but has no way to change, move or delete them.",
  },
  {
    fact: "Ignores note instructions",
    why: "Text in a file is treated as information, never as a command. Only you tell the app what to do.",
  },
  {
    fact: "Checks every quote",
    why: "Each quote in an answer must really appear in the note it cites. Anything it can't back up is removed, and if nothing is left it says “No supporting notes found.”",
  },
  {
    fact: "Never opens links",
    why: "Web addresses in your notes are read as plain text. The app never visits them.",
  },
];

export default function Settings({ onOpenPrivacy }: { onOpenPrivacy: () => void }) {
  const [info, setInfo] = useState<Health | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [model, setModel] = useState(ANSWER_MODELS[0]);

  useEffect(() => {
    health().then(setInfo).catch((e) => setError(String(e)));
    getSettings().then((s) => s.answer_model && setModel(s.answer_model)).catch(() => {});
  }, []);

  function chooseModel(m: string) {
    setModel(m);
    saveSettings({ answer_model: m }).catch((e) => setError(String(e)));
  }

  return (
    <div className="page">
      <h2>Settings</h2>
      <p className="muted lead">
        Your settings and folder list are saved on this computer, so they are still here next time.
        Your notes are never copied.
      </p>

      <section className="card" aria-labelledby="s-engine">
        <h3 id="s-engine">Engine</h3>
        {error && <p className="error">Could not reach the local engine: {error}</p>}
        <dl className="props">
          <dt>Status</dt>
          <dd className={error ? "error" : ""}>{error ? "Not running" : info ? "Running on this computer" : "Checking…"}</dd>
          <dt>Mode</dt>
          <dd>{info ? (info.read_only ? "Read-only" : "Can change files") : "…"}</dd>
          <dt>Internet</dt>
          <dd>{info ? (info.network === "localhost-only" ? "Not used" : info.network) : "…"}</dd>
        </dl>
        {info && (
          <details className="more">
            <summary>Technical details</summary>
            <dl className="props">
              <dt>Version</dt>
              <dd>{info.version}</dd>
              <dt>Network</dt>
              <dd><code>{info.network}</code></dd>
            </dl>
          </details>
        )}
      </section>

      <section className="card" aria-labelledby="s-model">
        <h3 id="s-model">AI model</h3>
        {/* Enabled, not `disabled`: VoiceOver skips disabled fields and their text is too faint. */}
        <div className="field">
          <label htmlFor="answer-model">Answers</label>
          <span className="select">
            <select
              id="answer-model"
              value={model}
              onChange={(e) => chooseModel(e.target.value)}
              aria-describedby="answer-model-help"
            >
              {ANSWER_MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
            </select>
          </span>
        </div>
        <p id="answer-model-help" className="muted">
          Runs on this computer through Ollama. More models will be available later.
        </p>
        <dl className="props">
          <dt>Search by meaning</dt>
          <dd>{SEARCH_MODEL}</dd>
        </dl>
      </section>

      <section className="card" aria-labelledby="s-index">
        <h3 id="s-index">Indexing</h3>
        <p className="muted">
          Choose folders on the{" "}
          <button className="link" onClick={onOpenPrivacy}>Privacy page</button>.
        </p>
      </section>

      <section className="card" aria-labelledby="s-a11y">
        <h3 id="s-a11y">Accessibility</h3>
        <p className="muted">
          The app follows your Mac's appearance, reduce motion and increase contrast settings. Press
          ⌘+ or ⌘− to change text size for this session.
        </p>
      </section>

      {/* Facts, not settings: these rules are built in and can't be switched off. */}
      <section className="card" aria-labelledby="s-safety">
        <h3 id="s-safety">How your notes are kept safe</h3>
        <p className="muted">Built in, and can't be turned off.</p>
        <dl className="props">
          {SAFETY.map((s) => (
            <Fragment key={s.fact}>
              <dt>{s.fact}</dt>
              <dd>{s.why}</dd>
            </Fragment>
          ))}
        </dl>
      </section>

      {/* Always last on the page, as on Privacy. */}
      <section className="card" aria-labelledby="s-forget">
        <h3 id="s-forget">Forget everything</h3>
        <p className="muted">
          Clears this session's memory and the saved folder list and settings. To see what the app can see and check that nothing left
          or stayed, open the <button className="link" onClick={onOpenPrivacy}>Privacy page</button>.
        </p>
        <ForgetButton />
      </section>
    </div>
  );
}
