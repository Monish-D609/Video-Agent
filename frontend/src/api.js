async function handle(res) {
  const isJson = res.headers.get("content-type")?.includes("application/json");

  if (!res.ok) {
    if (res.status === 413) {
      throw new Error("File is too large to upload directly. Please try a smaller file or paste a YouTube link.");
    }
    let message = res.statusText || `Request failed (${res.status})`;
    if (isJson) {
      try {
        const data = await res.json();
        message = data.detail || message;
      } catch {}
    }
    throw new Error(message);
  }

  if (isJson) {
    return res.json();
  }

  // If server returned 200 HTML when JSON was expected (e.g. Vercel SPA rewrite fallback)
  throw new Error(
    "Cloud backend returned an unexpected response. Please ensure your AWS EC2 backend is running and connected."
  );
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
  testConnection: async (baseUrl) => {
    const cleanUrl = (baseUrl || "").trim().replace(/\/+$/, "");
    if (!cleanUrl) throw new Error("Please enter a backend URL");
    const target = `${cleanUrl}/health`;
    const res = await fetch(target, { headers: reqHeaders(), mode: "cors" });
    return handle(res);
  },
  process: (source, language) =>
    fetch(apiUrl("/api/process"), json({ source, language })).then(handle),
  upload: (file, language, onProgress) => {
    return new Promise((resolve, reject) => {
      const form = new FormData();
      form.append("file", file);
      form.append("language", language);

      const xhr = new XMLHttpRequest();
      xhr.open("POST", apiUrl("/api/upload"));

      const headers = reqHeaders();
      for (const [key, value] of Object.entries(headers)) {
        xhr.setRequestHeader(key, value);
      }

      if (xhr.upload && onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            onProgress(percent, event.loaded, event.total);
          }
        };
      }

      xhr.onload = () => {
        const contentType = xhr.getResponseHeader("content-type") || "";
        if (xhr.status >= 200 && xhr.status < 300) {
          if (contentType.includes("application/json")) {
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch (err) {
              reject(new Error("Invalid JSON response from server"));
            }
          } else {
            reject(
              new Error(
                "Received HTML from server instead of API response. Verify that your AWS EC2 backend is running and connected."
              )
            );
          }
        } else {
          let msg = xhr.statusText || `Upload failed (${xhr.status})`;
          if (xhr.status === 413) {
            msg = "File is too large for upload. Try a smaller file or paste a YouTube URL.";
          }
          if (contentType.includes("application/json")) {
            try {
              const data = JSON.parse(xhr.responseText);
              msg = data.detail || msg;
            } catch {}
          }
          reject(new Error(msg));
        }
      };

      xhr.onerror = () => {
        reject(new Error("Network error during file upload. Check backend connection."));
      };

      xhr.send(form);
    });
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

