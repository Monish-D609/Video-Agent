from dotenv import load_dotenv
load_dotenv()   # MUST be before any core/ imports

import os
from utils.audio_processor import process_input
from utils import store
from core.transcriber import transcribe_all
from core.summarize import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions


source = "https://www.youtube.com/watch?v=poMYvFjPcR0"
language = "hinglish"   # "english" → Whisper, "hinglish" → Sarvam

FORCE_REGENERATE = False        # True = wipe the saved files for this video and start over
EXTRACT_MAX_CHARS = 18000       # longer transcripts: extractors read the summary (context window)


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