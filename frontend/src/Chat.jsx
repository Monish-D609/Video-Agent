import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import FormattedText from "frontend\src\FormattedText.jsx";

const SUGGESTIONS = [
  "What are the main points of this video?",
  "Who is mentioned in the video?",
  "Summarize the key takeaways",
];

export default function Chat({ id }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [slow, setSlow] = useState(false);
  const [ready, setReady] = useState(false);
  const listRef = useRef(null);

  // Restore the saved conversation for this video (stored on the server in downloads/session)
  useEffect(() => {
    // Reset state first so we don't flash the previous video's messages
    setMessages([]);
    setReady(false);
    api
      .session(id)
      .then((d) => setMessages(d.messages || []))
      .catch(() => {})
      .finally(() => setReady(true));
  }, [id]);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  const send = async (text) => {
    const question = (text ?? input).trim();
    if (!question || loading) return;
    setMessages((m) => [...m, { role: "user", text: question }]);
    setInput("");
    setLoading(true);
    const timer = setTimeout(() => setSlow(true), 6000);
    try {
      const { answer, rewritten, route } = await api.chat(id, question);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: answer, rewritten, route },
      ]);
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", text: e.message, error: true },
      ]);
    } finally {
      clearTimeout(timer);
      setSlow(false);
      setLoading(false);
    }
  };

  const clear = async () => {
    try {
      await api.clearSession(id);
      setMessages([]);
    } catch {}
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="chat">
      {messages.length > 0 && (
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            className="btn ghost"
            style={{ padding: "6px 12px", fontSize: 13 }}
            onClick={clear}
            disabled={loading}
          >
            Clear chat
          </button>
        </div>
      )}
      <div className="messages" ref={listRef}>
        {/* Loading skeleton while fetching session history */}
        {!ready && (
          <div className="session-loading">
            <div className="skeleton-line" style={{ width: "60%" }} />
            <div className="skeleton-line" style={{ width: "80%" }} />
            <div className="skeleton-line" style={{ width: "45%" }} />
          </div>
        )}
        {ready && messages.length === 0 && (
          <div className="empty">
            <p>
              Ask anything about this video. Answers come only from what is said
              in it.
            </p>
            <div className="chips">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role} ${m.error ? "error" : ""}`}>
            <div className="bubble">
              {m.role === "assistant" && !m.error ? (
                <FormattedText text={m.text} />
              ) : (
                m.text
              )}
            </div>
            {m.rewritten && (
              <div className="interp">Searched for: {m.rewritten}</div>
            )}
            {m.role === "assistant" && m.route && (
              <div className={`route-badge route-${m.route}`}>
                {m.route === "direct" ? "⚡ Direct" : "🔍 RAG"}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="msg assistant">
            <div className="bubble muted">
              {slow
                ? "Still working. The first question after a restart can take a minute…"
                : "Thinking…"}
            </div>
          </div>
        )}
      </div>
      <div className="composer">
        <textarea
          rows={1}
          placeholder="Ask a question about the video"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKey}
        />
        <button
          className="btn primary"
          onClick={() => send()}
          disabled={!ready || !input.trim() || loading}
        >
          Send
        </button>
      </div>
    </div>
  );
}
