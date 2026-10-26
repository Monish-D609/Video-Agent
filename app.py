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
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from core.rag_engine import build_rag_chain, ask_question, get_llm


EXTRACT_MAX_CHARS = 18000       # same rule as test.py
LANGUAGES = ("english", "hinglish")
KEY_RE = re.compile(r"^[A-Za-z0-9_-]+$")
FIELDS = ("title", "summary", "action_items", "decisions", "questions")

UPLOAD_DIR = os.path.join(store.CACHE_DIR, "uploads")     # downloads/uploads
os.makedirs(UPLOAD_DIR, exist_ok=True)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Video Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

APP_ACCESS_TOKEN = os.getenv("APP_ACCESS_TOKEN", "").strip()


@app.middleware("http")
async def verify_token_middleware(request, call_next):
    """Optional access guard to protect Cloudflare/Sarvam credits from unauthorized use."""
    if not APP_ACCESS_TOKEN:
        return await call_next(request)

    path = request.url.path
    # Allow /health and static frontend/assets without requiring token
    if path == "/health" or not path.startswith("/api/"):
        return await call_next(request)

    token = request.headers.get("x-access-token") or request.query_params.get("token")
    if token != APP_ACCESS_TOKEN:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=401, content={"detail": "Unauthorized: Invalid or missing access token"})

    return await call_next(request)


@app.get("/health")
def health():
    return {"status": "ok"}


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
            RAG["chain"] = build_rag_chain(transcript, key=key)
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
            err_msg = f"{type(e).__name__}: {e}"
            lower_err = str(e).lower()
            if any(term in lower_err for term in ("sign in to confirm", "bot", "429", "too many requests", "blocked")):
                err_msg = (
                    f"YouTube blocked audio extraction from this cloud server: {e}. "
                    "Datacenter IPs are frequently challenged by YouTube bot detection. "
                    "Please download the video/audio locally and use the 'Upload file' tab instead."
                )
            print(f"❌ Pipeline failed for {key}: {err_msg}")
            job["status"] = "error"
            job["error"] = err_msg


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


# The RAG chain has no memory: it searches the transcript with the raw question only.
# So "what are the good sides to this?" would search for the words "good sides to this".
# We first turn the question into a standalone one, using the chat history and video title.
CONDENSE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You rewrite questions about a video so they make sense on their own. "
     "The video is titled: {title}. "
     "Using the conversation so far, rewrite the user's last question as ONE standalone question, "
     "replacing words like 'this', 'it', 'that' or 'they' with what they refer to. "
     "Do not answer it and do not add facts. If it is already standalone, return it unchanged. "
     "Return only the question."),
    ("human", "Conversation so far:\n{history}\n\nLast question: {question}"),
])


def _standalone_question(question: str, history, title: str) -> str:
    convo = "\n".join(f"{m['role'].capitalize()}: {m['text']}" for m in history[-6:])
    try:
        chain = CONDENSE_PROMPT | get_llm() | StrOutputParser()
        rewritten = chain.invoke(
            {"title": title or "Untitled", "history": convo or "(none)", "question": question}
        ).strip().strip('"')
        if rewritten and len(rewritten) <= 400:
            return rewritten
    except Exception as e:
        print(f"⚠️ Could not rewrite the question, using the original: {e}")
    return question


# --------------- query router ---------------
# Intent categories for query routing
_SUMMARY_PATTERNS = re.compile(
    r"\b(summar|overview|what('?s| is) (this|the) (video|talk|lecture|podcast|recording) about"
    r"|what (was|were) (discussed|covered|talked about)"
    r"|main (point|topic|idea|takeaway)"
    r"|give me a (brief|quick|short) (overview|summary)"
    r"|tldr|tl;dr)",
    re.IGNORECASE,
)
_META_PATTERNS = re.compile(
    r"\b(title|what('?s| is) (the )?title|what('?s| is) (this|the) video called"
    r"|language|how long|duration|transcript|full text)",
    re.IGNORECASE,
)
_GREETING_PATTERNS = re.compile(
    r"^\s*(hi|hello|hey|sup|howdy|greetings|good (morning|afternoon|evening))[\.!?]?\s*$",
    re.IGNORECASE,
)
_CONVO_PATTERNS = re.compile(
    r"^\s*(thanks?|thank you|okay|ok|got it|great|cool|nice|awesome|understood|makes sense|sure|alright|perfect)[\.!?]?\s*$",
    re.IGNORECASE,
)


def _route_query(question: str, data: dict) -> str | None:
    """Try to answer certain query types directly without hitting the vector store.
    Returns a string answer, or None if the question should go through RAG."""
    q = question.strip()

    # Greetings — respond without touching RAG
    if _GREETING_PATTERNS.match(q):
        title = data.get("title") or "this video"
        return f"Hi! I'm here to help you explore **{title}**. Ask me anything about what was said in it."

    # Short conversational acknowledgements
    if _CONVO_PATTERNS.match(q):
        return "Sure! Feel free to ask anything else about the video."

    # Summary / overview requests — serve cached summary directly
    if _SUMMARY_PATTERNS.search(q) and data.get("summary"):
        return data["summary"]

    # Title / meta questions — answer from cached data
    if _META_PATTERNS.search(q):
        title = data.get("title") or "Untitled"
        language = data.get("language") or "unknown"
        if re.search(r"\btitle\b|what.*called", q, re.IGNORECASE):
            return f"The title of this video is: **{title}**"
        if re.search(r"\blanguage\b", q, re.IGNORECASE):
            return f"This video was transcribed in **{language}**."
        if re.search(r"\btranscript\b|\bfull text\b", q, re.IGNORECASE):
            return "You can view the full transcript in the **Transcript** tab above."

    # Action items / decisions / open questions — serve cached extractions
    if re.search(r"\baction item|\btask|\bto.?do\b", q, re.IGNORECASE) and data.get("action_items"):
        return data["action_items"]
    if re.search(r"\bdecision|\bwhat was decided|\bagreed\b", q, re.IGNORECASE) and data.get("decisions"):
        return data["decisions"]
    if re.search(r"\bopen question|\bunresolved|\bunanswered\b", q, re.IGNORECASE) and data.get("questions"):
        return data["questions"]

    # Fallthrough: let RAG handle it
    return None


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
        history = store.load_session(key)["messages"]          # saved conversation = the memory

        # Step 1: query routing
        # Try to answer directly from cached data (summary, title, extractions)
        # before touching the vector store. This avoids irrelevant embedding hits.
        direct_answer = _route_query(question, data)
        if direct_answer is not None:
            store.append_messages(key, [
                {"role": "user", "text": question},
                {"role": "assistant", "text": direct_answer, "route": "direct"},
            ])
            return {"answer": direct_answer, "rewritten": None, "route": "direct"}

        # Step 2: rewrite the question into a standalone one, then RAG
        standalone = _standalone_question(question, history, data.get("title"))
        chain = _ensure_chain(key, data["transcript"])
        answer = ask_question(chain, standalone)
        rewritten = standalone if standalone != question else None
        store.append_messages(key, [
            {"role": "user", "text": question},
            {"role": "assistant", "text": answer, "rewritten": rewritten, "route": "rag"},
        ])
        return {"answer": answer, "rewritten": rewritten, "route": "rag"}
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


@app.get("/api/session/{key}")
def get_session(key: str):
    if not _load_processed(key):
        raise HTTPException(404, "Video not found")
    return {"messages": store.load_session(key)["messages"]}


@app.delete("/api/session/{key}")
def delete_session(key: str):
    _load_processed(key)   # validates the id
    store.clear_session(key)
    return {"ok": True}


# Serve the built frontend (after `npm run build`) from the same server
if os.path.isdir("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")