"""
FastAPI layer over the existing pipeline. Nothing in core/ or utils/ is modified.

Run (from the project root, venv active):
    uvicorn app:app --port 8000
"""
from dotenv import load_dotenv
load_dotenv()   # MUST be before any core/ imports

import glob
import json
import os
import re
import shutil
import threading

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils.audio_processor import process_input
from utils import store
from core.transcriber import transcribe_all
from core.summarize import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question


EXTRACT_MAX_CHARS = 18000       # same rule as test.py
LANGUAGES = ("english", "hinglish")
KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")
FIELDS = ("title", "summary", "action_items", "decisions", "questions")

UPLOAD_DIR = os.path.join(store.CACHE_DIR, "uploads")     # downloads/uploads
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Video Agent")

JOBS = {}                          # key -> {status, stage, error, source, language}
JOBS_LOCK = threading.Lock()
PIPELINE_LOCK = threading.Lock()   # one heavy job at a time (Whisper / vector store)

RAG = {"key": None, "chain": None} # the vector store holds one video at a time
RAG_LOCK = threading.Lock()


# ----------------------------- helpers -----------------------------

def _load_processed(key: str):
    if not KEY_RE.match(key):
        raise HTTPException(400, "Invalid id")
    path = os.path.join(store.PROCESSED_DIR, f"{key}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _is_complete(data) -> bool:
    return bool(data) and all(data.get(f) for f in ("transcript",) + FIELDS)


def _ensure_chain(key: str, transcript: str):
    """Return the RAG chain for this video, (re)building it if another video was active."""
    with RAG_LOCK:
        if RAG["key"] != key:
            RAG["chain"] = build_rag_chain(transcript)
            RAG["key"] = key
        return RAG["chain"]


# ----------------------------- pipeline -----------------------------

def _run_pipeline(key: str, source: str, language: str):
    job = JOBS[key]
    with PIPELINE_LOCK:
        try:
            processed = store.ProcessedStore(key, source, language)

            def cached(field, fn):
                value = processed.get(field)
                if value:
                    return value
                value = fn()
                processed.set(field, value)
                return value

            transcript = processed.get("transcript")
            if not transcript:
                transcript = store.load_complete_raw_text(key)
                if not transcript:
                    job["stage"] = "fetching"
                    chunks = process_input(source)
                    raw = store.RawTranscript(key, source, language, len(chunks))
                    job["stage"] = "transcribing"
                    transcript = transcribe_all(chunks, language=language, raw=raw)
                processed.set_transcript(transcript)

            job["stage"] = "summarizing"
            cached("title", lambda: generate_title(transcript))
            summary = cached("summary", lambda: summarize(transcript, cache=processed))

            job["stage"] = "extracting"
            extract_src = transcript if len(transcript) <= EXTRACT_MAX_CHARS else summary
            cached("action_items", lambda: extract_action_items(extract_src))
            cached("decisions", lambda: extract_key_decisions(extract_src))
            cached("questions", lambda: extract_questions(extract_src))

            job["stage"] = "indexing"
            _ensure_chain(key, transcript)

            job["status"], job["stage"] = "done", "done"
        except Exception as e:
            print(f"❌ Pipeline failed for {key}: {type(e).__name__}: {e}")
            job["status"] = "error"
            job["error"] = f"{type(e).__name__}: {e}"


def _start(key: str, source: str, language: str):
    with JOBS_LOCK:
        job = JOBS.get(key)
        if job and job["status"] == "processing":
            return
        if _is_complete(_load_processed(key)):
            JOBS[key] = {"status": "done", "stage": "done", "source": source, "language": language}
            return
        JOBS[key] = {"status": "processing", "stage": "queued", "source": source, "language": language}
    threading.Thread(target=_run_pipeline, args=(key, source, language), daemon=True).start()


# ----------------------------- API -----------------------------

class ProcessRequest(BaseModel):
    source: str
    language: str = "english"


class ChatRequest(BaseModel):
    question: str


def _check_language(language: str) -> str:
    language = language.lower()
    if language not in LANGUAGES:
        raise HTTPException(400, "Language must be 'english' or 'hinglish'")
    return language


@app.post("/api/process")
def process(req: ProcessRequest):
    source = req.source.strip()
    language = _check_language(req.language)
    if not source.startswith(("http://", "https://")):
        raise HTTPException(400, "Enter a valid link starting with http:// or https://")
    key = store.make_key(source, language)
    if not KEY_RE.match(key):
        raise HTTPException(400, "Unsupported link")
    _start(key, source, language)
    return {"id": key}


@app.post("/api/upload")
def upload(file: UploadFile = File(...), language: str = Form("english")):
    language = _check_language(language)
    name = os.path.basename(file.filename or "upload")
    path = os.path.join(UPLOAD_DIR, name)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    key = store.make_key(path, language)
    _start(key, path, language)
    return {"id": key}


@app.get("/api/status/{key}")
def status(key: str):
    job = JOBS.get(key)
    if job:
        return dict(job)
    data = _load_processed(key)
    if _is_complete(data):
        return {"status": "done", "stage": "done", "source": data.get("source"), "language": data.get("language")}
    raise HTTPException(404, "Video not found")


@app.post("/api/retry/{key}")
def retry(key: str):
    info = JOBS.get(key) or _load_processed(key)
    if not info or not info.get("source"):
        raise HTTPException(404, "Video not found")
    _start(key, info["source"], info["language"])
    return {"id": key}


@app.get("/api/result/{key}")
def result(key: str):
    data = _load_processed(key)
    if not _is_complete(data):
        raise HTTPException(404, "Not ready")
    return {k: data.get(k) for k in ("key", "source", "language", "transcript") + FIELDS}


@app.get("/api/videos")
def videos():
    items = []
    for path in glob.glob(os.path.join(store.PROCESSED_DIR, "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if _is_complete(data):
            items.append({
                "id": data["key"],
                "title": data["title"],
                "language": data.get("language"),
                "updated_at": data.get("updated_at") or "",
            })
    items.sort(key=lambda x: x["updated_at"], reverse=True)
    return items[:20]


@app.post("/api/chat/{key}")
def chat(key: str, req: ChatRequest):
    question = req.question.strip()
    if not question:
        raise HTTPException(400, "Empty question")
    data = _load_processed(key)
    if not data or not data.get("transcript"):
        raise HTTPException(404, "Video not found")
    try:
        chain = _ensure_chain(key, data["transcript"])
        return {"answer": ask_question(chain, question)}
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


# Serve the built frontend (after `npm run build`) from the same server
if os.path.isdir("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")