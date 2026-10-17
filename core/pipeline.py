import os

from utils.audio_processor import process_input
from utils import store
from core.transcriber import transcribe_all, engine_name
from core.summarize import summarize, generate_title, CHUNK_SIZE, CHUNK_OVERLAP
from core.extractor import extract_action_items, extract_key_decisions, extract_questions

# Above this many characters, the extractors read the merged summary instead of the
# raw transcript, so a long video can't overflow the model's context window.
EXTRACT_MAX_CHARS = int(os.getenv("EXTRACT_MAX_CHARS", "18000"))


def _cached(processed, field, label, fn):
    value = processed.get(field)
    if value:
        print(f"✅ {label}: loaded from cache")
        return value
    print(f"⏳ {label}: generating...")
    value = fn()
    processed.set(field, value)   # saved immediately
    return value


def get_transcript(source, language, key, processed):
    cached = processed.get("transcript")
    if cached:
        print("✅ Transcript: loaded from processed cache (no download, no transcription).")
        return cached

    text = store.load_complete_raw_text(key)
    if text:
        print("✅ All raw chunks already transcribed, combining them (no download needed).")
    else:
        chunks = process_input(source)
        raw = store.RawTranscript(key, source, language, engine_name(language), len(chunks))
        text = transcribe_all(chunks, language, raw)

    processed.set_transcript(text)
    return text


def run_phase1(source: str, language: str = "english", force: bool = False) -> dict:
    key = store.make_key(source, language)
    if force:
        store.clear(key)

    processed = store.ProcessedStore(key, source, language)

    transcript = get_transcript(source, language, key, processed)

    processed.reset_chunk_summaries_if_changed(CHUNK_SIZE, CHUNK_OVERLAP)

    title = _cached(processed, "title", "Title", lambda: generate_title(transcript))
    summary = _cached(processed, "summary", "Summary", lambda: summarize(transcript, store=processed))

    extract_src = transcript if len(transcript) <= EXTRACT_MAX_CHARS else summary
    action_items = _cached(processed, "action_items", "Action items", lambda: extract_action_items(extract_src))
    decisions = _cached(processed, "decisions", "Key decisions", lambda: extract_key_decisions(extract_src))
    questions = _cached(processed, "questions", "Open questions", lambda: extract_questions(extract_src))

    return {
        "key": key,
        "transcript": transcript,
        "title": title,
        "summary": summary,
        "action_items": action_items,
        "decisions": decisions,
        "questions": questions,
    }