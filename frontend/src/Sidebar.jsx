import { useState } from "react";

export default function Sidebar({
  chats = [],
  currentId = null,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  isOpen,
  onClose,
  theme = "dark",
  toggleTheme,
}) {
  const [filter, setFilter] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);

  const filteredChats = filter.trim()
    ? chats.filter((c) =>
        (c.title || "").toLowerCase().includes(filter.toLowerCase())
      )
    : chats;

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          className="sidebar-backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside className={`sidebar ${isOpen ? "open" : ""}`}>
        {/* Top brand & close button */}
        <div className="sidebar-header">
          <button
            className="brand"
            onClick={() => {
              onNewChat();
              onClose?.();
            }}
          >
            <span className="logo">▶</span>
            <span className="brand-text">Video Agent</span>
          </button>
          <button
            className="sidebar-close-btn"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            ✕
          </button>
        </div>

        {/* ChatGPT-style New Chat button */}
        <div className="sidebar-actions">
          <button
            className="new-chat-btn"
            onClick={() => {
              onNewChat();
              onClose?.();
            }}
          >
            <span className="plus-icon">+</span>
            <span>New chat</span>
          </button>
        </div>

        {/* Optional quick search filter if multiple chats */}
        {chats.length > 4 && (
          <div className="sidebar-search">
            <input
              type="text"
              placeholder="Search chat history…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            />
            {filter && (
              <button
                className="search-clear-btn"
                onClick={() => setFilter("")}
              >
                ✕
              </button>
            )}
          </div>
        )}

        {/* Chat History Section */}
        <div className="sidebar-history-container">
          <div className="history-section-title">
            <span>Recent Chats</span>
            <span className="chat-count-badge">{chats.length}</span>
          </div>

          {filteredChats.length === 0 ? (
            <div className="history-empty">
              {filter ? (
                <p>No matching chats found</p>
              ) : (
                <>
                  <p className="history-empty-main">No saved chats yet</p>
                  <p className="history-empty-sub">
                    Drop a YouTube link or upload a video to start your first chat!
                  </p>
                </>
              )}
            </div>
          ) : (
            <ul className="chat-history-list">
              {filteredChats.map((c) => {
                const isActive = c.id === currentId;
                return (
                  <li
                    key={c.id}
                    className={`chat-history-item ${isActive ? "active" : ""}`}
                  >
                    <button
                      className="chat-history-btn"
                      onClick={() => {
                        onSelectChat(c.id);
                        onClose?.();
                      }}
                      title={c.title || "Video chat"}
                    >
                      <span className="chat-item-icon">💬</span>
                      <div className="chat-item-text">
                        <span className="chat-item-title">
                          {c.title || "Untitled Video"}
                        </span>
                        <div className="chat-item-meta">
                          {c.messageCount ? (
                            <span className="msg-count">
                              {c.messageCount} {c.messageCount === 1 ? "msg" : "msgs"}
                            </span>
                          ) : null}
                          {c.language && (
                            <span className="lang-tag">{c.language}</span>
                          )}
                        </div>
                      </div>
                    </button>
                    {confirmDeleteId === c.id ? (
                      <div className="chat-delete-confirm-group" onClick={(e) => e.stopPropagation()}>
                        <button
                          className="chat-confirm-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            e.preventDefault();
                            setConfirmDeleteId(null);
                            onDeleteChat(c.id);
                          }}
                          title="Confirm deletion"
                          aria-label="Confirm deletion"
                        >
                          ✓
                        </button>
                        <button
                          className="chat-cancel-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            e.preventDefault();
                            setConfirmDeleteId(null);
                          }}
                          title="Cancel"
                          aria-label="Cancel"
                        >
                          ✕
                        </button>
                      </div>
                    ) : (
                      <button
                        className="chat-delete-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          e.preventDefault();
                          setConfirmDeleteId(c.id);
                        }}
                        title="Delete chat from history"
                        aria-label="Delete chat"
                      >
                        🗑
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Sidebar Footer */}
        <div className="sidebar-footer">
          {toggleTheme && (
            <button
              className="sidebar-theme-toggle"
              onClick={toggleTheme}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            >
              <span className="theme-icon">{theme === "dark" ? "☀️" : "🌙"}</span>
              <span>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
            </button>
          )}
          <div className="footer-status">
            <span className="status-dot online"></span>
            <span>Local AI · Whisper & RAG</span>
          </div>
          <div className="footer-sub">Chats automatically saved</div>
        </div>
      </aside>
    </>
  );
}
