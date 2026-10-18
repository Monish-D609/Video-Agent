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

const json = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  process: (source, language) =>
    fetch("/api/process", json({ source, language })).then(handle),
  upload: (file, language) => {
    const form = new FormData();
    form.append("file", file);
    form.append("language", language);
    return fetch("/api/upload", { method: "POST", body: form }).then(handle);
  },
  status: (id) => fetch(`/api/status/${id}`).then(handle),
  retry: (id) => fetch(`/api/retry/${id}`, { method: "POST" }).then(handle),
  result: (id) => fetch(`/api/result/${id}`).then(handle),
  videos: () => fetch("/api/videos").then(handle),
  chat: (id, question) =>
    fetch(`/api/chat/${id}`, json({ question })).then(handle),
  session: (id) => fetch(`/api/session/${id}`).then(handle),
  clearSession: (id) =>
    fetch(`/api/session/${id}`, { method: "DELETE" }).then(handle),
};
