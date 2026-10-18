from dotenv import load_dotenv
load_dotenv()   # MUST be before any core/ imports

import os
import time
from utils.audio_processor import process_input
from utils import store
from core.transcriber import transcribe_all
from core.summarize import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, load_rag_chain, ask_question   # <- change "rag_engine" if your RAG file is named differently
from core.vector_store import load_vector_store, get_retriever


source = "https://www.youtube.com/watch?v=poMYvFjPcR0"
language = "hinglish"   # "english" → Whisper, "hinglish" → Sarvam

FORCE_REGENERATE = False        # True = wipe the saved files for this video and start over
EXTRACT_MAX_CHARS = 18000       # longer transcripts: extractors read the summary (context window)

# ---------- RAG test settings ----------
RUN_RAG_TEST = True
REBUILD_VECTOR_STORE = True     # True = embed the transcript again; False = only load the saved vector store
SHOW_RETRIEVED = True           # print the chunks the retriever pulled for each question
TOP_K = 4                       # keep in sync with k in your RAG file

# (question, kind)   kind: "in_scope" = answer is in the video, "out_of_scope" = it is not
# Edit the in_scope questions so they match what your video actually says.
RAG_QUESTIONS = [
    ("What look did he take for the film, and who inspired it?", "in_scope"),
    ("Which actor is mentioned as having the same hairstyle?", "in_scope"),
    ("Give me a short summary of what this conversation is about.", "in_scope"),
    ("What is the capital of France?", "out_of_scope"),
]
NOT_FOUND = "could not find"    # part of the fallback sentence in your RAG prompt


# ---------- saved-file setup (downloads/raw and downloads/processed) ----------
key = store.make_key(source, language)
if FORCE_REGENERATE:
    store.clear(key)
processed = store.ProcessedStore(key, source, language)


def cached(field, label, fn):
    """Return the saved value if it exists, otherwise generate it and save it right away."""
    value = processed.get(field)
    if value:
        print(f"✅ {label}: loaded from saved file")
        return value
    print(f"⏳ {label}: generating...")
    value = fn()
    processed.set(field, value)
    return value


# ---------- transcript ----------
transcript = processed.get("transcript")
if transcript:
    print("✅ Transcript: loaded from processed file (no download, no transcription)")
else:
    transcript = store.load_complete_raw_text(key)
    if transcript:
        print("✅ All raw chunks already transcribed, combining them (no download needed)")
    else:
        chunks = process_input(source)
        raw = store.RawTranscript(key, source, language, len(chunks))
        transcript = transcribe_all(chunks, language=language, raw=raw)
    processed.set_transcript(transcript)

print("\n" + "=" * 60)
print("📝 TRANSCRIPT")
print("=" * 60)
print(transcript[:500] + "..." if len(transcript) > 500 else transcript)


title = cached("title", "Title", lambda: generate_title(transcript))
summary = cached("summary", "Summary", lambda: summarize(transcript, cache=processed))

print("\n" + "=" * 60)
print(f"📌 TITLE: {title}")
print("=" * 60)
print("\n📋 SUMMARY")
print("-" * 60)
print(summary)


extract_src = transcript if len(transcript) <= EXTRACT_MAX_CHARS else summary
action_items = cached("action_items", "Action items", lambda: extract_action_items(extract_src))
decisions = cached("decisions", "Key decisions", lambda: extract_key_decisions(extract_src))
questions = cached("questions", "Open questions", lambda: extract_questions(extract_src))

print("\n" + "=" * 60)
print("✅ ACTION ITEMS")
print("=" * 60)
print(action_items)

print("\n" + "=" * 60)
print("🔑 KEY DECISIONS")
print("=" * 60)
print(decisions)

print("\n" + "=" * 60)
print("❓ OPEN QUESTIONS")
print("=" * 60)
print(questions)


# =====================================================================
#                          RAG TEST (Phase 2)
# =====================================================================
if RUN_RAG_TEST:

    # ---------- build or load the RAG chain ----------
    print("\n" + "=" * 60)
    print("🔧 BUILD / LOAD RAG CHAIN")
    print("=" * 60)
    t0 = time.time()
    if REBUILD_VECTOR_STORE:
        rag_chain = build_rag_chain(transcript)
        print(f"Built vector store + chain in {time.time() - t0:.1f}s")
    else:
        rag_chain = load_rag_chain()
        print(f"Loaded vector store + chain in {time.time() - t0:.1f}s")

    retriever = get_retriever(load_vector_store(), k=TOP_K) if SHOW_RETRIEVED else None

    # ---------- ask the questions ----------
    rag_results = []
    for i, (rag_question, kind) in enumerate(RAG_QUESTIONS, 1):
        print("\n" + "=" * 60)
        print(f"💬 RAG Q{i} [{kind}]")
        print("=" * 60)

        if retriever is not None:
            docs = retriever.invoke(rag_question)
            print(f"🔎 Retrieved {len(docs)} chunk(s):")
            for j, d in enumerate(docs, 1):
                preview = d.page_content.replace("\n", " ")
                print(f"   [{j}] {preview[:200]}{'...' if len(preview) > 200 else ''}")
            print()

        t = time.time()
        rag_answer = ask_question(rag_chain, rag_question)
        elapsed = time.time() - t

        said_not_found = NOT_FOUND in rag_answer.lower()
        ok = said_not_found if kind == "out_of_scope" else not said_not_found
        rag_results.append((rag_question, kind, ok, elapsed))

    # ---------- reload test (simulates restarting the app) ----------
    print("\n" + "=" * 60)
    print("♻️  RELOAD TEST (load_rag_chain, no re-embedding)")
    print("=" * 60)
    try:
        reloaded_chain = load_rag_chain()
        ask_question(reloaded_chain, RAG_QUESTIONS[0][0])
        reload_ok = True
    except Exception as e:
        print(f"❌ load_rag_chain failed: {type(e).__name__}: {e}")
        reload_ok = False

    # ---------- summary ----------
    print("\n" + "=" * 60)
    print("📊 RAG SUMMARY")
    print("=" * 60)
    for rag_question, kind, ok, elapsed in rag_results:
        print(f"[{'PASS' if ok else 'CHECK'}] ({elapsed:.1f}s) [{kind}] {rag_question}")
    print(f"[{'PASS' if reload_ok else 'FAIL'}] load_rag_chain() after build")
    print("\nCHECK = read the answer yourself: an in_scope question said it couldn't find the answer "
          "(retrieval probably missed), or an out_of_scope question got answered instead of refused.")