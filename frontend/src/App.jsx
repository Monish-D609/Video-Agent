import { useEffect, useState, useCallback } from "react";
import { api, getApiBase } from "./api.js";
import { storage } from "./storage.js";
import Home from "./Home.jsx";
import Job from "./Job.jsx";
import Sidebar from "./Sidebar.jsx";
import BackendModal from "./BackendModal.jsx";

// The open video lives in the URL (#/v/<id>), so refresh and back button work naturally.
const parse = () => {
  const m = window.location.hash.match(/^#\/v\/([\w-]+)$/);
  return m ? m[1] : null;
};

export default function App() {
  const [id, setId] = useState(parse);
  const [chatList, setChatList] = useState(() => storage.getChatList());
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [backendModalOpen, setBackendModalOpen] = useState(false);
  const [backendConnected, setBackendConnected] = useState("checking");

  // Health check
  const checkHealth = useCallback(() => {
    setBackendConnected("checking");
    api
      .health()
      .then(() => setBackendConnected("connected"))
      .catch(() => setBackendConnected("offline"));
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // Theme management: persisted in localStorage with system preference fallback
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem("video_agent_theme");
    if (saved === "dark" || saved === "light") return saved;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("video_agent_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "dark" ? "light" : "dark"));
  };

  // Sync hash change
  useEffect(() => {
    const onHash = () => setId(parse());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // Fetch backend videos on mount and merge with local storage chat metadata
  const refreshChats = useCallback(() => {
    api
      .videos()
      .then((backendVideos) => {
        const merged = storage.getChatList(backendVideos || []);
        setChatList(merged);
      })
      .catch(() => {
        // Fallback to local storage if offline or backend error
        setChatList(storage.getChatList());
      });
  }, []);

  useEffect(() => {
    refreshChats();
  }, [refreshChats, id]);

  const open = (next) => {
    window.location.hash = next ? `/v/${next}` : "/";
    setId(next);
  };

  const handleDeleteChat = async (chatId) => {
    // 1. Immediately remove from state for instant UI feedback
    setChatList((prev) => prev.filter((c) => c.id !== chatId));

    // 2. Mark as permanently deleted in local storage tombstone
    storage.deleteChat(chatId);

    // 3. If currently viewing this chat, close it immediately
    if (id === chatId) {
      open(null);
    }

    // 4. Request server session clearance
    try {
      await api.clearSession(chatId);
    } catch {}

    // 5. Sync chat list (deleted chat will be strictly excluded)
    refreshChats();
  };

  const activeChat = chatList.find((c) => c.id === id);

  return (
    <div className="chatgpt-layout">
      {/* ChatGPT-style persistent sidebar */}
      <Sidebar
        chats={chatList}
        currentId={id}
        onSelectChat={(selectedId) => open(selectedId)}
        onNewChat={() => open(null)}
        onDeleteChat={handleDeleteChat}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        theme={theme}
        toggleTheme={toggleTheme}
      />

      {/* Main chat & content area */}
      <div className="main-viewport">
        {/* Sleek top app bar */}
        <header className="chat-topbar">
          <div className="topbar-left">
            <button
              className="sidebar-toggle-btn"
              onClick={() => setSidebarOpen((prev) => !prev)}
              title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
              aria-label="Toggle sidebar"
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <line x1="9" y1="3" x2="9" y2="21" />
              </svg>
            </button>
            <div className="current-chat-header-info">
              {id ? (
                <span className="current-chat-title">
                  {activeChat?.title || "Video Chat"}
                </span>
              ) : (
                <span className="current-chat-title-brand">
                  <span className="logo-small">▶</span> Video Agent
                </span>
              )}
            </div>
          </div>

          <div className="topbar-right">
            <button
              className={`backend-status-pill ${backendConnected}`}
              onClick={() => setBackendModalOpen(true)}
              title="Click to view or edit AWS Cloud Backend connection settings"
            >
              <span className="status-dot" />
              {backendConnected === "connected"
                ? "Cloud Connected"
                : backendConnected === "checking"
                ? "Connecting…"
                : "Connect Backend"}
            </button>

            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              aria-label="Toggle theme"
            >
              {theme === "dark" ? (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="5"></circle>
                  <line x1="12" y1="1" x2="12" y2="3"></line>
                  <line x1="12" y1="21" x2="12" y2="23"></line>
                  <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
                  <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
                  <line x1="1" y1="12" x2="3" y2="12"></line>
                  <line x1="21" y1="12" x2="23" y2="12"></line>
                  <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
                  <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
                </svg>
              ) : (
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
                </svg>
              )}
            </button>
            {id && (
              <button
                className="btn-new-chat-top"
                onClick={() => open(null)}
                title="Start a new video chat"
              >
                <span className="plus-icon">+</span> New chat
              </button>
            )}
          </div>
        </header>

        {/* If on Vercel and backend is offline/not configured, show notice */}
        {backendConnected !== "connected" &&
          typeof window !== "undefined" &&
          window.location.hostname.includes("vercel.app") && (
            <div className="backend-offline-banner">
              <span>
                ⚠ <strong>AWS Backend is not connected:</strong> Start <code>run.bat</code> on your PC or configure your Cloudflare URL.
              </span>
              <button onClick={() => setBackendModalOpen(true)}>Connect URL</button>
            </div>
          )}

        {/* Main body: either Job (with Chat default) or Home */}
        <main className="content-scroll-area">
          <div className="page-container">
            {id ? (
              <Job
                key={id}
                id={id}
                initialTab="chat"
                onHome={() => open(null)}
                onChatUpdated={refreshChats}
              />
            ) : (
              <Home onOpen={open} />
            )}
          </div>
        </main>
      </div>

      <BackendModal
        isOpen={backendModalOpen}
        onClose={() => setBackendModalOpen(false)}
        onConnected={(ok) => {
          if (ok) {
            checkHealth();
            refreshChats();
          }
        }}
      />
    </div>
  );
}
