/**
 * "Forget everything" with an explicit confirm step and a visible result.
 * Used on the Privacy page and in Settings. Calls DELETE /api/session, which
 * runs every module's reset (backend/app/session.py) and re-checks the disk.
 */
import { useState } from "react";
import { forgetEverything, ForgetResult } from "../lib/trust";

const LABELS: Record<string, string> = {
  activity_log: "activity log entries",
  index: "indexed passages",
  folders: "saved folders",
  model: "loaded models",
};

interface Props {
  onDone?: (r: ForgetResult) => void;
}

export default function ForgetButton({ onDone }: Props) {
  // idle → confirm (user must click twice) → working → idle with a result shown.
  const [state, setState] = useState<"idle" | "confirm" | "working">("idle");
  const [result, setResult] = useState<ForgetResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setState("working");
    setError(null);
    try {
      const r = await forgetEverything();
      setResult(r);
      onDone?.(r);
    } catch (e) {
      setError(String(e));
    }
    setState("idle");
  }

  if (state === "confirm") {
    return (
      <div className="confirm">
        <p>
          This clears everything the app holds: the search index, the activity log, your saved
          folder list and settings, and it unloads the AI model. <strong>Your note files are not
          touched.</strong>
        </p>
        <div className="row">
          <button className="btn danger" onClick={run}>Yes, forget everything</button>
          <button className="btn" onClick={() => setState("idle")}>Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <button className="btn danger" onClick={() => setState("confirm")} disabled={state === "working"}>
        {state === "working" ? "Forgetting…" : "Forget everything"}
      </button>
      {error && <p className="error">Could not forget: {error}</p>}
      {result && (
        <p className="done" role="status">
          <strong>Done at {new Date().toLocaleTimeString()}.</strong>{" "}
          Cleared{" "}
          {Object.entries(result.cleared)
            .map(([k, n]) => `${n ?? 0} ${LABELS[k] ?? k.replace(/_/g, " ")}`)
            .join(", ")}
          . Stored on disk now:{" "}
          {result.storage.files === 0 ? "nothing" : `${result.storage.files} files (see Privacy)`}.
        </p>
      )}
    </div>
  );
}
