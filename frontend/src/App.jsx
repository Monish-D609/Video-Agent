import { useEffect, useState, useCallback } from "react";
import { api } from "./api.js";
import { storage } from "./storage.js";
import Home from "./Home.jsx";
import Job from "./Job.jsx";
import Sidebar from "./Sidebar.jsx";

// The open video lives in the URL (#/v/<id>), so refresh and back button work naturally.
const parse = () => {
  const m = window.location.hash.match(/^#\/v\/([\w-]+)$/);
  return m ? m[1] : null;
};

export default function App() {
  const [id, setId] = useState(parse);
  const [chatList, setChatList] = useState(() => storage.getChatList());
  const [sidebarOpen, setSidebarOpen] = useState(true);

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

  const handleDeleteChat = (chatId) => {
    storage.deleteChat(chatId);
    if (id === chatId) {
      open(null);
    }
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
    </div>
  );
}
