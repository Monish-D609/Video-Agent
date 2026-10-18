/**
 * Storage manager for Video Agent chat history and metadata.
 * Persists conversations in localStorage so chats survive browser reloads,
 * navigation changes, server restarts, and offline sessions.
 * 
 * Supports tombstones for deleted chats so deleted items are NEVER resurrected
 * by backend /api/videos responses.
 */

const STORAGE_PREFIX = "video_agent_chat_";
const METADATA_KEY = "video_agent_chats_metadata";
const DELETED_KEY = "video_agent_deleted_chats";
const CLEARED_KEY = "video_agent_cleared_chats";

export const storage = {
  /**
   * Get set of IDs that the user has explicitly deleted.
   */
  getDeletedIds() {
    try {
      const raw = localStorage.getItem(DELETED_KEY);
      const arr = raw ? JSON.parse(raw) : [];
      return Array.isArray(arr) ? arr : [];
    } catch {
      return [];
    }
  },

  /**
   * Check if an ID has been deleted by the user.
   */
  isDeleted(id) {
    if (!id) return false;
    return this.getDeletedIds().includes(id);
  },

  /**
   * Get all messages for a specific video ID.
   * Synchronous - returns immediately with cached messages.
   */
  getChat(id) {
    if (!id || this.isDeleted(id)) return [];
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
      // If user is adding messages, make sure it's not marked as deleted or cleared
      this.undelete(id);
      this.removeClearedMark(id);

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
    if (!id || this.isDeleted(id)) return;
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
   * Merges local storage metadata with any list from the backend /api/videos,
   * STRICTLY filtering out any deleted chats.
   */
  getChatList(backendVideos = []) {
    const deletedIds = this.getDeletedIds();
    const metaMap = this.getAllMetadata();
    
    // Purge any deleted IDs that might be lingering in metaMap
    for (const delId of deletedIds) {
      if (metaMap[delId]) {
        delete metaMap[delId];
      }
    }

    // Merge backend videos into metaMap ONLY if NOT deleted
    for (const v of backendVideos) {
      if (!v || !v.id || deletedIds.includes(v.id)) continue;
      
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

    // Save cleaned/merged list back to storage
    try {
      localStorage.setItem(METADATA_KEY, JSON.stringify(metaMap));
    } catch {}

    // Return as array sorted by updated_at descending, strictly excluding deleted IDs
    return Object.values(metaMap)
      .filter((item) => item && item.id && !deletedIds.includes(item.id))
      .sort((a, b) => {
        const timeA = new Date(a.updated_at || 0).getTime();
        const timeB = new Date(b.updated_at || 0).getTime();
        return timeB - timeA;
      });
  },

  /**
   * Mark a chat conversation as explicitly cleared (messages = 0).
   */
  clearChat(id) {
    if (!id) return;
    try {
      localStorage.setItem(`${STORAGE_PREFIX}${id}`, JSON.stringify([]));
      
      // Mark as cleared with timestamp so background sync never resurrects old server messages
      const cleared = this.getClearedMap();
      cleared[id] = Date.now();
      localStorage.setItem(CLEARED_KEY, JSON.stringify(cleared));

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
   * Check if a chat was cleared and should not restore older messages.
   */
  isCleared(id) {
    if (!id) return false;
    const cleared = this.getClearedMap();
    return !!cleared[id];
  },

  getClearedMap() {
    try {
      const raw = localStorage.getItem(CLEARED_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  },

  removeClearedMark(id) {
    try {
      const cleared = this.getClearedMap();
      if (cleared[id]) {
        delete cleared[id];
        localStorage.setItem(CLEARED_KEY, JSON.stringify(cleared));
      }
    } catch {}
  },

  /**
   * Completely remove a chat from history (Tombstone).
   * It will never be re-added from backend /api/videos.
   */
  deleteChat(id) {
    if (!id) return;
    try {
      // 1. Add to tombstone deleted IDs list
      const deletedIds = this.getDeletedIds();
      if (!deletedIds.includes(id)) {
        deletedIds.push(id);
        localStorage.setItem(DELETED_KEY, JSON.stringify(deletedIds));
      }

      // 2. Remove messages
      localStorage.removeItem(`${STORAGE_PREFIX}${id}`);

      // 3. Remove from metadata map
      const meta = this.getAllMetadata();
      delete meta[id];
      localStorage.setItem(METADATA_KEY, JSON.stringify(meta));

      // 4. Record as cleared
      this.clearChat(id);
    } catch (e) {
      console.warn("Failed to delete chat:", e);
    }
  },

  /**
   * Remove from deleted tombstone (e.g. if user re-submits this video afresh).
   */
  undelete(id) {
    if (!id) return;
    try {
      const deletedIds = this.getDeletedIds().filter((d) => d !== id);
      localStorage.setItem(DELETED_KEY, JSON.stringify(deletedIds));
    } catch {}
  },
};
