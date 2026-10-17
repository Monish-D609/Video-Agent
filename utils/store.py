"""
JSON persistence so a crash never costs you finished work.

downloads/
  raw/<key>.json        chunk-wise transcripts (written after every chunk / Sarvam piece)
  processed/<key>.json  combined transcript + title, summaries, action items, etc.

Lives inside the existing downloads/ folder, so the project's folder layout is unchanged.

<key> = <video id or file hash>_<language>, so english and hinglish runs
of the same video never overwrite each other.
"""
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

CACHE_DIR = os.getenv("CACHE_DIR", "downloads")
RAW_DIR = os.path.join(CACHE_DIR, "raw")
PROCESSED_DIR = os.path.join(CACHE_DIR, "processed")
os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


# ----------------------------- helpers -----------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        print(f"⚠️  Cache file {path} is unreadable, ignoring it.")
        return None


def _write_json(path: str, data: dict) -> None:
    """Atomic write: a crash mid-write can never corrupt the existing cache file."""
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _video_id(source: str) -> str:
    if source.startswith(("http://", "https://")):
        u = urlparse(source)
        host = u.netloc.lower()
        if "youtu.be" in host:
            vid = u.path.strip("/").split("/")[0]
            if vid:
                return vid
        if "youtube.com" in host:
            q = parse_qs(u.query)
            if "v" in q:
                return q["v"][0]
            parts = [p for p in u.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live"):
                return parts[1]
        return "url_" + hashlib.sha1(source.encode()).hexdigest()[:12]

    # local file: size + first 4 MB, so renaming/moving the file keeps the same key
    h = hashlib.sha1()
    h.update(str(os.path.getsize(source)).encode())
    with open(source, "rb") as f:
        h.update(f.read(4 * 1024 * 1024))
    return "file_" + h.hexdigest()[:12]


def _engine(language: str) -> str:
    """Engine + model name stored in the raw cache, so switching model never reuses stale text."""
    if language.lower() == "hinglish":
        return "sarvam:" + os.getenv("SARVAM_STT_MODEL", "saaras:v2.5")
    return "whisper:" + os.getenv("WHISPER_MODEL", "small")


def make_key(source: str, language: str) -> str:
    return f"{_video_id(source)}_{language.lower()}"


def clear(key: str) -> None:
    """Delete both cache files for a key (used for force re-runs)."""
    for d in (RAW_DIR, PROCESSED_DIR):
        p = os.path.join(d, f"{key}.json")
        if os.path.exists(p):
            os.remove(p)


# ----------------------------- raw -----------------------------

def load_complete_raw_text(key: str):
    """Return the combined transcript if every raw chunk is already done, else None.
    Lets the pipeline skip downloading/converting/chunking entirely."""
    data = _read_json(os.path.join(RAW_DIR, f"{key}.json"))
    if not data or not data.get("complete"):
        return None
    chunks = data["chunks"]
    # same joining as transcribe_all(): text + " ", then strip
    return "".join(chunks[str(i)]["text"] + " " for i in range(data["total_chunks"])).strip()


class RawTranscript:
    """Chunk-wise transcripts. Saved after every chunk (and after every Sarvam piece)."""

    def __init__(self, key, source, language, total_chunks):
        engine = _engine(language)
        self.path = os.path.join(RAW_DIR, f"{key}.json")
        old = _read_json(self.path)

        if old and old.get("engine") == engine and old.get("total_chunks") == total_chunks:
            self.data = old
            done = sum(self.chunk_done(i) for i in range(total_chunks))
            print(f"♻️  Resuming raw transcription: {done}/{total_chunks} chunks already done.")
        else:
            if old:
                print("⚠️  Engine or chunk count changed since last run; starting a fresh raw cache.")
            self.data = {
                "key": key,
                "source": source,
                "language": language,
                "engine": engine,
                "total_chunks": total_chunks,
                "created_at": _now(),
                "complete": False,
                "chunks": {},
            }
            self._flush()

    def _flush(self):
        self.data["updated_at"] = _now()
        _write_json(self.path, self.data)

    def _chunk(self, i):
        return self.data["chunks"].setdefault(str(i), {"status": "partial", "pieces": [], "text": ""})

    def chunk_done(self, i) -> bool:
        return self.data["chunks"].get(str(i), {}).get("status") == "done"

    def chunk_text(self, i) -> str:
        return self.data["chunks"][str(i)]["text"]

    def get_pieces(self, i) -> list:
        return list(self.data["chunks"].get(str(i), {}).get("pieces", []))

    def save_pieces(self, i, pieces: list):
        self._chunk(i)["pieces"] = list(pieces)
        self._flush()

    def save_chunk(self, i, text: str):
        c = self._chunk(i)
        c["status"] = "done"
        c["text"] = text
        c.pop("pieces", None)
        self.data["complete"] = all(self.chunk_done(j) for j in range(self.data["total_chunks"]))
        self._flush()


# ----------------------------- processed -----------------------------

class ProcessedStore:
    """Combined transcript plus every LLM output, saved the moment it is generated."""

    FIELDS = ("title", "summary", "action_items", "decisions", "questions")

    def __init__(self, key, source, language):
        self.path = os.path.join(PROCESSED_DIR, f"{key}.json")
        self.data = _read_json(self.path) or {
            "key": key,
            "source": source,
            "language": language,
            "created_at": _now(),
            "transcript": None,
            "chunk_summaries": {},
            **{f: None for f in self.FIELDS},
        }

    def _flush(self):
        self.data["updated_at"] = _now()
        _write_json(self.path, self.data)

    def get(self, field):
        return self.data.get(field)

    def set(self, field, value):
        self.data[field] = value
        self._flush()

    def set_transcript(self, text: str):
        if self.data.get("transcript") != text:
            # transcript changed -> everything derived from it is stale
            self.data["chunk_summaries"] = {}
            for f in self.FIELDS:
                self.data[f] = None
        self.data["transcript"] = text
        self._flush()

    @staticmethod
    def _chunk_id(chunk_text: str) -> str:
        return hashlib.sha1(chunk_text.encode("utf-8")).hexdigest()[:16]

    def get_chunk_summary(self, chunk_text: str):
        return self.data["chunk_summaries"].get(self._chunk_id(chunk_text))

    def set_chunk_summary(self, chunk_text: str, summary: str):
        self.data["chunk_summaries"][self._chunk_id(chunk_text)] = summary
        self._flush()