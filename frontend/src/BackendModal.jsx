import { useState } from "react";
import { api, getApiBase, setApiBase } from "./api.js";

export default function BackendModal({ isOpen, onClose, onConnected }) {
  const [url, setUrl] = useState(() => getApiBase());
  const [testing, setTesting] = useState(false);
  const [status, setStatus] = useState(null); // { ok: bool, message: string }

  if (!isOpen) return null;

  const handleTestAndSave = async (e) => {
    e?.preventDefault();
    const clean = url.trim().replace(/\/+$/, "");
    if (!clean) {
      setApiBase("");
      setStatus({ ok: false, message: "Backend URL cleared." });
      onConnected?.(false);
      return;
    }

    setTesting(true);
    setStatus(null);
    try {
      await api.testConnection(clean);
      setApiBase(clean);
      setStatus({ ok: true, message: "Successfully connected to AWS Cloud Backend!" });
      onConnected?.(true);
      setTimeout(() => {
        onClose();
      }, 1200);
    } catch (err) {
      setStatus({
        ok: false,
        message: err.message || "Failed to reach backend. Check URL or verify EC2 is running.",
      });
      onConnected?.(false);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Cloud Backend Connection</h3>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <form onSubmit={handleTestAndSave}>
          <p className="modal-desc">
            Connect this frontend to your on-demand AWS EC2 backend.
          </p>

          <label className="modal-label">
            AWS Backend / Cloudflare HTTPS URL:
            <input
              type="url"
              className="input modal-input"
              placeholder="https://xxxx.trycloudflare.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              autoFocus
            />
          </label>

          {status && (
            <div className={`modal-status ${status.ok ? "success" : "error"}`}>
              {status.ok ? "✓ " : "⚠ "}
              {status.message}
            </div>
          )}

          <div className="modal-hint">
            <strong>How to get this URL:</strong>
            <ol>
              <li>Double-click <code>run.bat</code> on your computer.</li>
              <li>Wait for the instance to start (~60s).</li>
              <li>Copy the HTTPS tunnel URL (or open the link with <code>?api=...</code>).</li>
            </ol>
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn ghost"
              onClick={() => {
                setApiBase("");
                setUrl("");
                setStatus({ ok: false, message: "Backend URL cleared." });
                onConnected?.(false);
              }}
            >
              Reset
            </button>
            <button type="submit" className="btn primary" disabled={testing}>
              {testing ? "Testing…" : "Test & Connect"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
