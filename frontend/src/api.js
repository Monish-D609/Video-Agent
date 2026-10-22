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

export const api = {
  process: (source, language) =>
    fetch("/api/process", json({ source, language })).then(handle),
  upload: (file, language) => {
    const form = new FormData();
    form.append("file", file);
    form.append("language", language);
    return fetch("/api/upload", { method: "POST", headers: reqHeaders(), body: form }).then(handle);
  },
  status: (id) => fetch(`/api/status/${id}`, { headers: reqHeaders() }).then(handle),
  retry: (id) => fetch(`/api/retry/${id}`, { method: "POST", headers: reqHeaders() }).then(handle),
  result: (id) => fetch(`/api/result/${id}`, { headers: reqHeaders() }).then(handle),
  videos: () => fetch("/api/videos", { headers: reqHeaders() }).then(handle),
  chat: (id, question) =>
    fetch(`/api/chat/${id}`, json({ question })).then(handle),
  session: (id) => fetch(`/api/session/${id}`, { headers: reqHeaders() }).then(handle),
  clearSession: (id) =>
    fetch(`/api/session/${id}`, { method: "DELETE", headers: reqHeaders() }).then(handle),
};
