import { useEffect, useRef, useState } from "react";
import { api, getApiBase } from "./api.js";
import { storage } from "./storage.js";

const LANGS = [
  ["english", "English"],
  ["hinglish", "Hinglish"],
];

export default function Home({ onOpen }) {
  const [mode, setMode] = useState("link");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState(null);
  const [language, setLanguage] = useState("english");
  const [busy, setBusy] = useState(false);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [uploadStats, setUploadStats] = useState("");
  const [error, setError] = useState("");
  const [recent, setRecent] = useState([]);
  const [drag, setDrag] = useState(false);
  const fileInput = useRef(null);

  useEffect(() => {
    api
      .videos()
      .then((items) => {
        const active = (items || []).filter((v) => !storage.isDeleted(v.id));
        setRecent(active);
      })
      .catch(() => {});
  }, []);

  const canSubmit = mode === "link" ? url.trim().length > 0 : !!file;

  const submit = async (e) => {
    e.preventDefault();
    if (!canSubmit || busy) return;

    const apiBase = getApiBase();
    if (!apiBase && typeof window !== "undefined" && window.location.hostname.includes("vercel.app")) {
      setError("Cloud backend is not connected! Click 'Connect Backend' in the top-right to enter your Cloudflare tunnel URL.");
      return;
    }

    setBusy(true);
    setError("");
    setUploadPercent(0);
    setUploadStats("");
    try {
      const { id } =
        mode === "link"
          ? await api.process(url.trim(), language)
          : await api.upload(file, language, (pct, loaded, total) => {
              setUploadPercent(pct);
              const mbLoaded = (loaded / (1024 * 1024)).toFixed(1);
              const mbTotal = (total / (1024 * 1024)).toFixed(1);
              setUploadStats(`${pct}% (${mbLoaded} MB / ${mbTotal} MB)`);
            });
      onOpen(id);
    } catch (err) {
      setError(err.message || "Failed to process media");
      setBusy(false);
      setUploadPercent(0);
      setUploadStats("");
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDrag(false);
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  };

  return (
    <>
      <section className="hero">
        <h1>Chat with any video</h1>
        <p>
          Paste a YouTube link or upload a file. Get a summary, action items and
          answers to your questions.
        </p>
      </section>

      <form className="card" onSubmit={submit}>
        <div className="seg" role="tablist">
          <button
            type="button"
            className={mode === "link" ? "active" : ""}
            onClick={() => setMode("link")}
          >
            YouTube link
          </button>
          <button
            type="button"
            className={mode === "file" ? "active" : ""}
            onClick={() => setMode("file")}
          >
            Upload file
          </button>
        </div>

        {mode === "link" ? (
          <input
            className="input"
            type="url"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            autoFocus
          />
        ) : (
          <div
            className={`drop ${drag ? "over" : ""}`}
            onClick={() => fileInput.current?.click()}
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={onDrop}
          >
            <input
              ref={fileInput}
              type="file"
              accept="video/*,audio/*"
              hidden
              onChange={(e) => setFile(e.target.files[0] || null)}
            />
            {file ? (
              <strong>{file.name}</strong>
            ) : (
              <span>Drop a video or audio file here, or click to browse</span>
            )}
          </div>
        )}

        {busy && mode === "file" && (
          <div className="upload-progress-card">
            <div className="upload-progress-header">
              <span>{uploadPercent < 100 ? "Uploading media to AWS Cloud…" : "Upload complete! Initializing AI worker…"}</span>
              <span className="upload-progress-percent">{uploadStats || `${uploadPercent}%`}</span>
            </div>
            <div className="upload-progress-track">
              <div
                className="upload-progress-indicator"
                style={{ width: `${Math.max(uploadPercent, 4)}%` }}
              />
            </div>
          </div>
        )}

        <div className="row">
          <div>
            <div className="label">Spoken language</div>
            <div className="seg small">
              {LANGS.map(([value, label]) => (
                <button
                  type="button"
                  key={value}
                  className={language === value ? "active" : ""}
                  onClick={() => setLanguage(value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <button className="btn primary" disabled={!canSubmit || busy}>
            {busy
              ? mode === "file"
                ? `Uploading ${uploadPercent}%…`
                : "Starting…"
              : "Analyze video"}
          </button>
        </div>

        {language === "hinglish" && (
          <p className="hint">
            Hinglish is transcribed with Sarvam AI and translated to English.
          </p>
        )}
        {error && <div className="error">{error}</div>}
      </form>

      {recent.length > 0 && (
        <section className="recent">
          <h2>Recent videos</h2>
          <ul>
            {recent.map((v) => (
              <li key={v.id}>
                <button onClick={() => onOpen(v.id)}>
                  <span className="title">{v.title}</span>
                  <span className="tag">{v.language}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}
