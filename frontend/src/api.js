async function handle(res) {
  if (!res.ok) {
    let message = res.statusText;
    try {
      const data = await res.json();
      message = data.detail || message;
    } catch {}
    throw new Error(message);
  }
  return res.json();
}

function getAuthHeaders() {
  if (typeof window !== "undefined") {
    try {
      const params = new URLSearchParams(window.location.search);
      const urlToken = params.get("token");
      if (urlToken) {
        localStorage.setItem("video_agent_access_token", urlToken);
      }
      const token = urlToken || localStorage.getItem("video_agent_access_token");
      if (token) {
        return { "X-Access-Token": token };
      }
    } catch {}
  }
  return {};
}

function reqHeaders(extra = {}) {
  return {
    ...getAuthHeaders(),
    ...extra,
  };
}

const json = (body) => ({
  method: "POST",
  headers: reqHeaders({ "Content-Type": "application/json" }),
  body: JSON.stringify(body),
});

export function getApiBase() {
  if (typeof window !== "undefined") {
    try {
      const params = new URLSearchParams(window.location.search);
      const queryApi = params.get("api");
      if (queryApi) {
        const cleaned = queryApi.replace(/\/+$/, "");
        localStorage.setItem("video_agent_backend_url", cleaned);
        return cleaned;
      }
      const saved = localStorage.getItem("video_agent_backend_url");
      if (saved) return saved.replace(/\/+$/, "");
      if (import.meta.env.VITE_API_URL) {
        return import.meta.env.VITE_API_URL.replace(/\/+$/, "");
      }
    } catch {}
  }
  return "";
}

export function setApiBase(url) {
  if (typeof window !== "undefined") {
    if (!url) {
      localStorage.removeItem("video_agent_backend_url");
    } else {
      localStorage.setItem("video_agent_backend_url", url.trim().replace(/\/+$/, ""));
    }
  }
}

export function apiUrl(path) {
  const base = getApiBase();
  return base ? `${base}${path}` : path;
}

export const api = {
  health: () => fetch(apiUrl("/health")).then(handle),
  process: (source, language) =>
    fetch(apiUrl("/api/process"), json({ source, language })).then(handle),
  upload: (file, language) => {
    const form = new FormData();
    form.append("file", file);
    form.append("language", language);
    return fetch(apiUrl("/api/upload"), { method: "POST", headers: reqHeaders(), body: form }).then(handle);
  },
  status: (id) => fetch(apiUrl(`/api/status/${id}`), { headers: reqHeaders() }).then(handle),
  retry: (id) => fetch(apiUrl(`/api/retry/${id}`), { method: "POST", headers: reqHeaders() }).then(handle),
  result: (id) => fetch(apiUrl(`/api/result/${id}`), { headers: reqHeaders() }).then(handle),
  videos: () => fetch(apiUrl("/api/videos"), { headers: reqHeaders() }).then(handle),
  chat: (id, question) =>
    fetch(apiUrl(`/api/chat/${id}`), json({ question })).then(handle),
  session: (id) => fetch(apiUrl(`/api/session/${id}`), { headers: reqHeaders() }).then(handle),
  clearSession: (id) =>
    fetch(apiUrl(`/api/session/${id}`), { method: "DELETE", headers: reqHeaders() }).then(handle),
};

