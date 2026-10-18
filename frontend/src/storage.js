/**
 * Storage manager for Video Agent chat history and metadata.
 * Persists conversations in localStorage so chats survive browser reloads,
 * navigation changes, server restarts, and offline sessions.
 */

const STORAGE_PREFIX = "video_agent_chat_";
const METADATA_KEY = "video_agent_chats_metadata";

export const storage = {
  /**
   * Get all messages for a specific video ID.
   * Synchronous - returns immediately with cached messages.
   */
  getChat(id) {
    if (!id) return [];
    try {
      const raw = localStorage.getItem(`${STORAGE_PREFIX}${id}`);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      console.warn("Failed to load chat from storage:", e);
      return [];
    }
  },

  /**
   * Save messages for a specific video ID and update its metadata in the index.
   */
  saveChat(id, messages, extraMeta = {}) {
    if (!id) return;
    try {
      localStorage.setItem(`${STORAGE_PREFIX}${id}`, JSON.stringify(messages));
      
      // Update metadata index
      const meta = this.getAllMetadata();
      const existing = meta[id] || {};
      const lastMsg = messages[messages.length - 1];
      
      meta[id] = {
        ...existing,
        ...extraMeta,
        id,
        messageCount: messages.length,
        lastMessage: lastMsg ? lastMsg.text : existing.lastMessage,
        updated_at: new Date().toISOString(),
      };
      
      localStorage.setItem(METADATA_KEY, JSON.stringify(meta));
    } catch (e) {
      console.warn("Failed to save chat to storage:", e);
    }
  },

  /**
   * Update metadata (title, language, etc.) for a video.
   */
  updateMeta(id, newMeta) {
    if (!id) return;
    try {
      const meta = this.getAllMetadata();
      meta[id] = {
        ...(meta[id] || {}),
        ...newMeta,
        id,
        updated_at: newMeta.updated_at || new Date().toISOString(),
      };
      localStorage.setItem(METADATA_KEY, JSON.stringify(meta));
    } catch (e) {
      console.warn("Failed to update metadata in storage:", e);
    }
  },

  /**
   * Get metadata map for all chats.
   */
  getAllMetadata() {
    try {
      const raw = localStorage.getItem(METADATA_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      return {};
    }
  },

  /**
   * Get sorted list of all chat sessions for the sidebar history.
   * Merges local storage metadata with any list from the backend /api/videos.
   */
  getChatList(backendVideos = []) {
    const metaMap = this.getAllMetadata();
    
    // Merge backend videos into metaMap
    for (const v of backendVideos) {
      if (!v || !v.id) continue;
      if (!metaMap[v.id]) {
        metaMap[v.id] = {
          id: v.id,
          title: v.title || "Untitled Video",
          language: v.language || "english",
          updated_at: v.updated_at || new Date().toISOString(),
          messageCount: this.getChat(v.id).length,
        };
      } else {
        // Update title or language if backend has fresher info
        if (v.title && !metaMap[v.id].title) metaMap[v.id].title = v.title;
        if (v.language) metaMap[v.id].language = v.language;
      }
    }

    // Save back merged list
    try {
      localStorage.setItem(METADATA_KEY, JSON.stringify(metaMap));
    } catch {}

    // Return as array sorted by updated_at descending
    return Object.values(metaMap).sort((a, b) => {
      const timeA = new Date(a.updated_at || 0).getTime();
      const timeB = new Date(b.updated_at || 0).getTime();
      return timeB - timeA;
    });
  },

  /**
   * Clear chat messages for a specific video while keeping metadata.
   */
  clearChat(id) {
    if (!id) return;
    try {
      localStorage.setItem(`${STORAGE_PREFIX}${id}`, JSON.stringify([]));
      const meta = this.getAllMetadata();
      if (meta[id]) {
        meta[id].messageCount = 0;
        meta[id].lastMessage = "";
        meta[id].updated_at = new Date().toISOString();
        localStorage.setItem(METADATA_KEY, JSON.stringify(meta));
      }
    } catch (e) {
      console.warn("Failed to clear chat:", e);
    }
  },

  /**
   * Completely remove a chat and its metadata from history.
   */
  deleteChat(id) {
    if (!id) return;
    try {
      localStorage.removeItem(`${STORAGE_PREFIX}${id}`);
      const meta = this.getAllMetadata();
      delete meta[id];
      localStorage.setItem(METADATA_KEY, JSON.stringify(meta));
    } catch (e) {
      console.warn("Failed to delete chat:", e);
    }
  },
};
