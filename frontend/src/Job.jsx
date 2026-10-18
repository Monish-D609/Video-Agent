import { useEffect, useState } from "react";
import { api } from "./api.js";
import Results from "./Results.jsx";

const STEPS = [
  ["fetching", "Fetching audio"],
  ["transcribing", "Transcribing speech"],
  ["summarizing", "Writing the summary"],
  ["extracting", "Extracting action items, decisions and questions"],
  ["indexing", "Preparing the chat"],
];

function Processing({ stage }) {
  const current = STEPS.findIndex(([id]) => id === stage);
  return (
    <section className="card narrow">
      <h2>Analyzing your video</h2>
      <p className="muted">
        {stage === "queued"
          ? "Waiting for another video to finish…"
          : "This can take a few minutes for long videos. Progress is saved, so you can safely leave and come back."}
      </p>
      <ol className="steps">
        {STEPS.map(([id, label], i) => {
          const state = i < current ? "done" : i === current ? "active" : "";
          return (
            <li key={id} className={state}>
              <span className="dot">
                {state === "done" ? (
                  "✓"
                ) : state === "active" ? (
                  <i className="spinner" />
                ) : (
                  ""
                )}
              </span>
              {label}
            </li>
          );
        })}
      </ol>
    </section>
  );
}

export default function Job({ id, onHome }) {
  const [st, setSt] = useState(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let stop = false;
    let timer;
    const tick = async () => {
      try {
        const s = await api.status(id);
        if (stop) return;
        setSt(s);
        if (s.status === "processing") timer = setTimeout(tick, 2000);
      } catch (e) {
        if (!stop) setSt({ status: "error", error: e.message, fatal: true });
      }
    };
    tick();
    return () => {
      stop = true;
      clearTimeout(timer);
    };
  }, [id, nonce]);

  const retry = async () => {
    try {
      await api.retry(id);
      setSt(null);
      setNonce((n) => n + 1);
    } catch (e) {
      setSt({ status: "error", error: e.message, fatal: true });
    }
  };

  if (!st) return <p className="muted center">Loading…</p>;
  if (st.status === "processing") return <Processing stage={st.stage} />;
  if (st.status === "error")
    return (
      <section className="card narrow">
        <h2>Something went wrong</h2>
        <div className="error">{st.error}</div>
        <p className="muted">
          Everything finished before the error is saved, so retrying continues
          where it stopped.
        </p>
        <div className="actions">
          {!st.fatal && (
            <button className="btn primary" onClick={retry}>
              Try again
            </button>
          )}
          <button className="btn ghost" onClick={onHome}>
            Back
          </button>
        </div>
      </section>
    );
  return <Results id={id} />;
}
