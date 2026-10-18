import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";

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
  const listRef = useRef(null);

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
      const { answer } = await api.chat(id, question);
      setMessages((m) => [...m, { role: "assistant", text: answer }]);
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

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="chat">
      <div className="messages" ref={listRef}>
        {messages.length === 0 && (
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
            <div className="bubble">{m.text}</div>
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
          disabled={!input.trim() || loading}
        >
          Send
        </button>
      </div>
    </div>
  );
}
