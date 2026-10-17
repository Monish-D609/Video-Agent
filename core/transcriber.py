import whisper
import os
import requests
from pydub import AudioSegment

# Sarvam's sync STT-translate API rejects audio longer than 30s.
# We slice each chunk into 25s pieces (with a 5s safety margin) before sending.
SARVAM_PIECE_SECONDS = 25


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")


SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_STT_TRANSLATE_URL = "https://api.sarvam.ai/speech-to-text-translate"
SARVAM_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v2.5")

_model = None


def load_model():

    global _model

    if _model is None:
        print(f"Loading Whisper model: {WHISPER_MODEL} ...")
        _model = whisper.load_model(WHISPER_MODEL)
        print("Whisper model loaded.")
    return _model


def transcribe_chunk_whisper(chunk_path: str) -> str:

    model = load_model()

    result = model.transcribe(chunk_path, task="transcribe")
    return result["text"]


def _send_to_sarvam(piece_path: str) -> str:
    """Send one ≤30s WAV file to Sarvam and return the English transcript."""
    headers = {"api-subscription-key": SARVAM_API_KEY}

    with open(piece_path, "rb") as f:
        files = {"file": (os.path.basename(piece_path), f, "audio/wav")}
        data = {"model": SARVAM_MODEL, "with_diarization": "false"}
        response = requests.post(
            SARVAM_STT_TRANSLATE_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=120,
        )

    if not response.ok:
        print(f"\n❌ Sarvam returned {response.status_code}")
        print(f"Response body: {response.text}\n")
        response.raise_for_status()

    return response.json().get("transcript", "")


def transcribe_chunk_sarvam(chunk_path: str, done_pieces: list = None, on_piece=None) -> str:
    """
    Sarvam sync API only accepts ≤30s audio. We split this chunk into
    25-second pieces, send each separately, and join the transcripts.

    done_pieces: transcripts of pieces already paid for in an earlier run (skipped).
    on_piece:    callback(list_of_piece_texts) fired after every successful piece,
                 used to checkpoint progress to disk.
    """
    if not SARVAM_API_KEY:
        raise RuntimeError("SARVAM_API_KEY is not set in environment / .env")

    audio = AudioSegment.from_wav(chunk_path)
    piece_ms = SARVAM_PIECE_SECONDS * 1000

    pieces_text = list(done_pieces or [])
    total_pieces = (len(audio) + piece_ms - 1) // piece_ms

    for i, start in enumerate(range(0, len(audio), piece_ms)):
        if i < len(pieces_text):
            continue  # already transcribed in a previous run

        piece = audio[start: start + piece_ms]
        piece_path = f"{chunk_path}_sv_{i}.wav"
        piece.export(piece_path, format="wav")

        try:
            print(f"  → Sarvam piece {i + 1}/{total_pieces} ...")
            pieces_text.append(_send_to_sarvam(piece_path))
        finally:
            if os.path.exists(piece_path):
                os.remove(piece_path)

        if on_piece:
            on_piece(pieces_text)

    return " ".join(t.strip() for t in pieces_text if t.strip())


def transcribe_chunk(chunk_path: str, language: str = "english", raw=None, idx: int = None) -> str:
    """
    Route one chunk to Whisper or Sarvam depending on language choice.
    - english  → Whisper (local model)
    - hinglish → Sarvam (translates to English while transcribing)
    """
    if language.lower() == "hinglish":
        return transcribe_chunk_sarvam(
            chunk_path,
            done_pieces=raw.get_pieces(idx) if raw is not None else None,
            on_piece=(lambda pieces: raw.save_pieces(idx, pieces)) if raw is not None else None,
        )
    return transcribe_chunk_whisper(chunk_path)


def transcribe_all(chunks: list, language: str = "english", raw=None) -> str:
    """
    raw (optional): utils.store.RawTranscript. When given, finished chunks are
    skipped and every new chunk is saved to disk as soon as it is done.
    """
    full_transcript = ""

    engine = "Sarvam AI" if language.lower() == "hinglish" else "Whisper"
    print(f"Using {engine} for transcription.")

    for i, chunk in enumerate(chunks):

        if raw is not None and raw.chunk_done(i):
            print(f"Chunk {i + 1}/{len(chunks)} already transcribed, skipping.")
            full_transcript += raw.chunk_text(i) + " "
            continue

        print(f"Transcribing chunk {i + 1}/{len(chunks)}...")

        text = transcribe_chunk(chunk, language=language, raw=raw, idx=i)

        if raw is not None:
            raw.save_chunk(i, text)

        full_transcript += text + " "

    print("Transcription complete.")

    return full_transcript.strip()