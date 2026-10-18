import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";
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
    setBusy(true);
    setError("");
    try {
      const { id } =
        mode === "link"
          ? await api.process(url.trim(), language)
          : await api.upload(file, language);
      onOpen(id);
    } catch (err) {
      setError(err.message);
      setBusy(false);
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
            {busy ? "Starting…" : "Analyze video"}
          </button>
        </div>

        <p className="hint">
          {language === "hinglish"
            ? "Hinglish is transcribed with Sarvam AI and translated to English."
            : "English is transcribed locally with Whisper."}
        </p>
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
