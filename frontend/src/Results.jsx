import { useEffect, useState } from "react";
import { api } from "./api.js";
import FormattedText from "./FormattedText.jsx";
import Chat from "./Chat.jsx";

const TABS = [
  ["summary", "Summary"],
  ["chat", "Chat"],
  ["actions", "Action items"],
  ["decisions", "Decisions"],
  ["questions", "Open questions"],
  ["transcript", "Transcript"],
];

export default function Results({ id }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("summary");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api
      .result(id)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <p className="muted center">Loading…</p>;

  const copyTranscript = async () => {
    await navigator.clipboard.writeText(data.transcript);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const isLink = /^https?:\/\//.test(data.source || "");

  return (
    <>
      <section className="result-head">
        <h1>{data.title}</h1>
        <p className="muted">
          <span className="tag">{data.language}</span>
          {isLink && (
            <a href={data.source} target="_blank" rel="noreferrer">
              Open source video ↗
            </a>
          )}
        </p>
      </section>

      <nav className="tabs">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            className={tab === key ? "active" : ""}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </nav>

      <section className="card">
        {tab === "summary" && <FormattedText text={data.summary} />}
        {tab === "actions" && <FormattedText text={data.action_items} />}
        {tab === "decisions" && <FormattedText text={data.decisions} />}
        {tab === "questions" && <FormattedText text={data.questions} />}
        {tab === "transcript" && (
          <>
            <div className="actions end">
              <button className="btn ghost" onClick={copyTranscript}>
                {copied ? "Copied ✓" : "Copy transcript"}
              </button>
            </div>
            <pre className="transcript">{data.transcript}</pre>
          </>
        )}
        {/* stays mounted so the conversation survives switching tabs */}
        <div hidden={tab !== "chat"}>
          <Chat id={id} />
        </div>
      </section>
    </>
  );
}
