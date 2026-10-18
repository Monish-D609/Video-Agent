import { useEffect, useState } from "react";
import { api } from "./api.js";
import { storage } from "./storage.js";
import FormattedText from "./FormattedText.jsx";
import Chat from "./Chat.jsx";

const TABS = [
  ["chat", "💬 Chat"],
  ["summary", "📄 Summary"],
  ["actions", "✅ Action items"],
  ["decisions", "📌 Decisions"],
  ["questions", "❓ Open questions"],
  ["transcript", "📜 Transcript"],
];

export default function Results({ id, initialTab = "chat", onChatUpdated }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState(initialTab);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api
      .result(id)
      .then((d) => {
        setData(d);
        // Persist title and metadata in local storage for chat history listing
        if (d && d.title) {
          storage.updateMeta(id, {
            title: d.title,
            language: d.language,
            source: d.source,
          });
          onChatUpdated?.();
        }
      })
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) return <div className="error">{error}</div>;
  if (!data) return <p className="muted center">Loading video insights…</p>;

  const copyTranscript = async () => {
    await navigator.clipboard.writeText(data.transcript);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const isLink = /^https?:\/\//.test(data.source || "");

  return (
    <div className="results-wrapper">
      {/* Video header info */}
      <section className="result-head">
        <div className="result-title-row">
          <h1>{data.title}</h1>
          <div className="result-meta-tags">
            {data.language && <span className="tag">{data.language}</span>}
            {isLink && (
              <a
                className="source-link"
                href={data.source}
                target="_blank"
                rel="noreferrer"
                title="Open original video"
              >
                Open video ↗
              </a>
            )}
          </div>
        </div>
      </section>

      {/* Navigation tabs */}
      <nav className="tabs">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            className={`tab-btn ${tab === key ? "active" : ""}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </nav>

      {/* Main card */}
      <section className="card result-card">
        {tab !== "chat" && (
          <div className="tab-back-bar">
            <button className="btn-back-to-chat" onClick={() => setTab("chat")}>
              ← Back to Chat
            </button>
          </div>
        )}

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

        {/* Chat stays mounted so conversation state survives switching tabs */}
        <div className="chat-tab-panel" hidden={tab !== "chat"}>
          <Chat
            id={id}
            title={data.title}
            onUpdated={() => onChatUpdated?.()}
          />
        </div>
      </section>
    </div>
  );
}
