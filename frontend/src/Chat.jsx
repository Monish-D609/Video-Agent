import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { storage } from "./storage.js";
import FormattedText from "./FormattedText.jsx";

const SUGGESTIONS = [
  "What are the main points of this video?",
  "Who is mentioned in the video?",
  "Summarize the key takeaways",
  "What are the action items or next steps?",
];

export default function Chat({ id, title = "", onUpdated }) {
  // Synchronously initialize from storage so older chats show up with 0ms delay!
  const [messages, setMessages] = useState(() => storage.getChat(id));
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [slow, setSlow] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const listRef = useRef(null);
  const textareaRef = useRef(null);

  // Sync with localStorage immediately on id change, and then background-sync with server
  useEffect(() => {
    // 1. Immediately display local messages
    const local = storage.getChat(id);
    setMessages(local);

    // 2. Background check server session for any additional messages
    api
      .session(id)
      .then((d) => {
        if (d && Array.isArray(d.messages) && d.messages.length > 0) {
          setMessages((current) => {
            // If local has fewer messages than server, use server's
            if (d.messages.length > current.length) {
              storage.saveChat(id, d.messages, { title });
              onUpdated?.(id, { messageCount: d.messages.length });
              return d.messages;
            }
            return current;
          });
        }
      })
      .catch(() => {
        // Server session endpoint not ready or 404 - local storage is our dependable source of truth
      });
  }, [id, title]);

  // Scroll to bottom on new messages
  useEffect(() => {
    const el = listRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, loading]);

  const send = async (text) => {
    const question = (text ?? input).trim();
    if (!question || loading) return;

    const userMsg = {
      role: "user",
      text: question,
      timestamp: new Date().toISOString(),
    };

    // Update state & localStorage immediately
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    storage.saveChat(id, updatedMessages, { title });
    onUpdated?.(id, { messageCount: updatedMessages.length, lastMessage: question });

    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    setLoading(true);
    const timer = setTimeout(() => setSlow(true), 6000);

    try {
      const { answer, rewritten, route } = await api.chat(id, question);
      const assistantMsg = {
        role: "assistant",
        text: answer,
        rewritten,
        route,
        timestamp: new Date().toISOString(),
      };
      const finalMessages = [...updatedMessages, assistantMsg];
      setMessages(finalMessages);
      storage.saveChat(id, finalMessages, { title });
      onUpdated?.(id, {
        messageCount: finalMessages.length,
        lastMessage: answer.slice(0, 100),
      });
    } catch (e) {
      const errorMsg = {
        role: "assistant",
        text: e.message || "Failed to get response",
        error: true,
        timestamp: new Date().toISOString(),
      };
      const finalMessages = [...updatedMessages, errorMsg];
      setMessages(finalMessages);
      storage.saveChat(id, finalMessages, { title });
    } finally {
      clearTimeout(timer);
      setSlow(false);
      setLoading(false);
    }
  };

  const clear = async () => {
    if (!window.confirm("Are you sure you want to clear this chat history?")) {
      return;
    }
    storage.clearChat(id);
    setMessages([]);
    onUpdated?.(id, { messageCount: 0, lastMessage: "" });
    try {
      await api.clearSession(id);
    } catch {}
  };

  const copyMessage = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
    // Auto adjust height up to 140px
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        140
      )}px`;
    }
  };

  return (
    <div className="chat-interface">
      {/* Top chat subheader */}
      <div className="chat-meta-bar">
        <div className="chat-meta-info">
          <span className="chat-topic-label">Conversation</span>
          {messages.length > 0 && (
            <span className="chat-history-pill">
              💾 {messages.length} {messages.length === 1 ? "message" : "messages"} saved
            </span>
          )}
        </div>
        {messages.length > 0 && (
          <button
            className="btn-clear-chat"
            onClick={clear}
            disabled={loading}
            title="Clear all messages for this video"
          >
            Clear chat
          </button>
        )}
      </div>

      {/* Message list */}
      <div className="messages" ref={listRef}>
        {messages.length === 0 && (
          <div className="chat-empty-state">
            <div className="empty-state-icon">💬</div>
            <h3>Chat with this video</h3>
            <p>
              Ask any question about what was discussed, shown, or decided in the
              video. Answers come directly from the video transcript.
            </p>
            <div className="suggestion-chips">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  className="suggestion-chip"
                  onClick={() => send(s)}
                >
                  <span className="chip-prompt">{s}</span>
                  <span className="chip-arrow">↗</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={`msg ${m.role} ${m.error ? "error" : ""}`}
          >
            {m.role === "assistant" && (
              <div className="avatar assistant-avatar" title="Video Agent AI">
                ▶
              </div>
            )}
            <div className="bubble-wrapper">
              <div className="bubble">
                {m.role === "assistant" && !m.error ? (
                  <FormattedText text={m.text} />
                ) : (
                  m.text
                )}
              </div>

              {/* Auxiliary info for assistant messages */}
              {m.role === "assistant" && !m.error && (
                <div className="msg-footer">
                  <div className="msg-badges">
                    {m.rewritten && (
                      <span className="interp" title="Question rewritten for search context">
                        🔍 Searched: {m.rewritten}
                      </span>
                    )}
                    {m.route && (
                      <span className={`route-badge route-${m.route}`}>
                        {m.route === "direct" ? "⚡ Direct Answer" : "🔍 RAG Search"}
                      </span>
                    )}
                  </div>
                  <button
                    className="copy-btn"
                    onClick={() => copyMessage(m.text, i)}
                    title="Copy message"
                  >
                    {copiedIndex === i ? "✓ Copied" : "📋 Copy"}
                  </button>
                </div>
              )}
            </div>

            {m.role === "user" && (
              <div className="avatar user-avatar" title="You">
                👤
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="msg assistant loading-msg">
            <div className="avatar assistant-avatar">▶</div>
            <div className="bubble muted loading-bubble">
              <div className="typing-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
              <span className="loading-text">
                {slow
                  ? "Still searching transcript… (large videos can take a moment)"
                  : "Searching video…"}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* ChatGPT-style floating bottom composer */}
      <div className="composer-container">
        <div className="composer-box">
          <textarea
            ref={textareaRef}
            rows={1}
            placeholder="Ask anything about this video… (Shift+Enter for new line)"
            value={input}
            onChange={handleInputChange}
            onKeyDown={onKey}
            disabled={loading}
          />
          <button
            className="composer-send-btn"
            onClick={() => send()}
            disabled={!input.trim() || loading}
            aria-label="Send message"
            title="Send (Enter)"
          >
            <svg
              viewBox="0 0 24 24"
              width="18"
              height="18"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="12" y1="19" x2="12" y2="5"></line>
              <polyline points="5 12 12 5 19 12"></polyline>
            </svg>
          </button>
        </div>
        <div className="composer-disclaimer">
          Video Agent answers strictly using speech and facts from this video.
        </div>
      </div>
    </div>
  );
}
