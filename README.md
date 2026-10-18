# AI Video Agent

Turn any video into something you can read, search and talk to.

Give it a YouTube link or a local video/audio file. It transcribes the speech, writes a title and summary, pulls out action items, decisions and open questions, and lets you **chat with the video**. Answers are grounded only in what is actually said in it.

It supports **English** and **Hinglish** (Hindi mixed with English). Hinglish speech is translated into English while it is transcribed, so everything downstream works in English.

---

## How it works

```
 YouTube URL / local file
          │
          ▼
 ┌─────────────────────┐   yt-dlp + FFmpeg, 16 kHz mono WAV, 10-minute chunks
 │  1. Audio ingest    │
 └─────────┬───────────┘
           ▼
 ┌─────────────────────┐   English  → Whisper (runs locally)
 │  2. Transcription   │   Hinglish → Sarvam AI API (25 s pieces, translated to English)
 └─────────┬───────────┘
           ▼   saved to downloads/raw after every chunk / piece
 ┌─────────────────────┐   title · chunk summaries → overall summary
 │  3. Understanding   │   action items · key decisions · open questions
 └─────────┬───────────┘   (Cloudflare Workers AI)
           ▼   saved to downloads/processed after every step
 ┌─────────────────────┐   transcript split → embeddings → vector store
 │  4. Chat (RAG)      │   top 4 chunks retrieved per question → LLM answers from them only
 └─────────────────────┘
```

The project is built in phases:

| Phase | What | Status |
| --- | --- | --- |
| 1 | Ingest, transcription, summaries, extraction, saved results | Done |
| 2 | Chat with the video (RAG) | Done |
| 3 | Web app (FastAPI + React) | First version built |

---

## Features

- **Two input types:** YouTube link or an uploaded local video/audio file.
- **Two transcription engines:** local Whisper for English, Sarvam AI for Hinglish.
- **Crash-proof and cheap to re-run:** every finished chunk, summary and extraction is saved to JSON. A crash, a rate limit or a closed terminal never forces you to redo transcription (which costs time and Sarvam credits).
- **Structured insights:** title, overall summary, action items (with owner and deadline when stated), key decisions and open questions.
- **Grounded chat:** the assistant answers only from the transcript and says *"I could not find this information in the meeting transcript."* when the answer isn't there.
- **Follow-ups that make sense:** each question is first rewritten into a standalone one using the video title and the saved conversation, so "what are the good sides to this?" works.
- **Saved chat sessions:** every conversation is stored locally as JSON, so it is still there after closing the tab or restarting the server.
- **Free-tier friendly LLM:** uses Cloudflare Workers AI, which includes a daily free allowance of neurons.

---

## Project structure

```
Video Agent/
├── app.py                 # FastAPI backend (wraps the pipeline for the website)
├── requirements.txt
├── .env                   # your API keys (not committed)
│
├── core/
│   ├── transcriber.py     # Whisper / Sarvam transcription, resumable
│   ├── summarize.py       # title, chunk-wise and overall summary
│   ├── extractor.py       # action items, decisions, open questions
│   ├── vector_store.py    # chunking + embeddings + vector store
│   └── rag_engine.py      # build_rag_chain / load_rag_chain / ask_question
│
├── utils/
│   ├── audio_processor.py # download, convert to WAV, chunk audio
│   └── store.py           # JSON saving / resuming (raw, processed, session)
│
├── downloads/             # created at runtime (git-ignored)
│   ├── raw/               # chunk-wise transcripts
│   ├── processed/         # combined transcript + title, summary, extractions
│   ├── session/           # chat history per video, saved after every answer
│   └── uploads/           # files uploaded through the website
│
└── frontend/              # React (Vite) web app
    └── src/               # App, Home, Job, Results, Chat, FormattedText, api.js, styles.css
```

---

## Setup

### Requirements
- Python 3.10+
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on your PATH (not installable through pip)
- Node.js 18+ (only for the website)

### Install

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
```

### Environment variables

Create a `.env` file in the project root:

```
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_API_TOKEN=your_workers_ai_token
SARVAM_API_KEY=your_sarvam_key
```

| Variable | Required | Purpose |
| --- | --- | --- |
| `CLOUDFLARE_ACCOUNT_ID` | yes | Your Cloudflare account id |
| `CLOUDFLARE_API_TOKEN` | yes | API token with Workers AI permission |
| `SARVAM_API_KEY` | for Hinglish | Sarvam AI speech-to-text-translate |
| `CLOUDFLARE_MODEL` | no | Override the LLM. Default: `@cf/meta/llama-3.1-8b-instruct-fp8` |
| `CLOUDFLARE_MAX_TOKENS` | no | Max tokens per LLM reply. Default 1024; use 2048 if summaries get cut off |
| `WHISPER_MODEL` | no | Whisper size. Default: `small` |
| `SARVAM_STT_MODEL` | no | Default: `saaras:v2.5` |
| `CACHE_DIR` | no | Where `raw/` and `processed/` are saved. Default: `downloads` |

Notes:
- The Cloudflare token comes from *My Profile → API Tokens* (the "Workers AI" template works). The account id is shown on the Workers AI page.
- No quotes around values, no spaces around `=`.

---

## Running

Terminal 1, from the project root:

```bash
uvicorn app:app --port 8000
```

Terminal 2:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

For a single server, build the frontend once (`npm run build` inside `frontend/`) and just run `uvicorn app:app`. The site is then served at http://localhost:8000.

**The site:** paste a link or upload a file, choose English or Hinglish, and press *Analyze video*. A progress checklist runs, then you get tabs for Summary, Chat, Action items, Decisions, Open questions and Transcript. Videos you have already processed are listed under *Recent videos* and open instantly.

---

## Saving and resuming

Nothing finished is ever generated twice. Results are saved under `downloads/`, keyed by `<YouTube id or file hash>_<language>`, so English and Hinglish runs of the same video never overwrite each other.

| File | Contains | Written |
| --- | --- | --- |
| `downloads/raw/<key>.json` | Chunk-wise transcripts (for Hinglish, every 25 s Sarvam piece) | After every chunk / piece |
| `downloads/processed/<key>.json` | Combined transcript, title, chunk summaries, summary, action items, decisions, questions | After every step |
| `downloads/session/<key>.json` | The website's chat history for that video (questions, answers and how each follow-up was understood, with timestamps) | After every answer |

On every run the pipeline checks, in order:
1. Combined transcript already saved? Skip download and transcription completely.
2. All raw chunks done? Just combine them, with no download.
3. Some chunks done? Re-download, then skip the finished chunks and pieces.
4. Each LLM step (title, each chunk summary, summary, extractions) is skipped if already saved.

Files are written atomically, so a crash in the middle of saving cannot corrupt a result. Changing the engine, model or number of chunks invalidates the raw file so stale text is never reused.

---

## API

Used by the website; also handy for testing.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/process` | Start from a link: `{ "source": "...", "language": "english" \| "hinglish" }` |
| `POST` | `/api/upload` | Start from an uploaded file (multipart: `file`, `language`) |
| `GET` | `/api/status/{id}` | `processing` / `done` / `error`, plus the current stage |
| `POST` | `/api/retry/{id}` | Continue a failed job from its saved progress |
| `GET` | `/api/result/{id}` | Title, summary, extractions and transcript |
| `GET` | `/api/videos` | Recently processed videos |
| `POST` | `/api/chat/{id}` | Ask a question: `{ "question": "..." }`. The exchange is saved to the session |
| `GET` | `/api/session/{id}` | The saved chat history for a video |
| `DELETE` | `/api/session/{id}` | Clear a video's chat history |

Videos are processed one at a time. A second job waits in the queue.

---

## Tech stack

- **Transcription:** OpenAI Whisper (local), Sarvam AI (API)
- **Audio:** yt-dlp, FFmpeg, pydub
- **LLM:** Cloudflare Workers AI (Llama 3.1 8B FP8 by default), accessed through its OpenAI-compatible endpoint with `langchain-openai`
- **Orchestration:** LangChain (LCEL)
- **RAG:** Hugging Face embeddings + ChromaDB
- **Backend:** FastAPI + Uvicorn
- **Frontend:** React + Vite (plain CSS)

---

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `Error code: 410 ... Model has been deprecated` | Cloudflare retired the model. Pick a current one from the [Workers AI model catalog](https://developers.cloudflare.com/workers-ai/models/) and set `CLOUDFLARE_MODEL` in `.env`. |
| Daily free neurons used up | Everything finished is saved. Run again tomorrow and it continues where it stopped. |
| Summary ends mid-sentence | Raise `CLOUDFLARE_MAX_TOKENS` to `2048`. |
| `No supported JavaScript runtime` warning from yt-dlp | Harmless while downloads work. If YouTube downloads start failing, install Deno or Node.js. |
| `ffmpeg` not found | Install FFmpeg and make sure it is on your PATH. |
| Chat is slow on the first question | The vector store holds one video at a time. Switching videos rebuilds the index. |

---

## Known limitations and ideas

- **One video in the vector store at a time.** Switching videos re-embeds the transcript. Per-video collections would remove the wait.
- **Long videos.** The final summary step merges all chunk summaries in one call. For very long videos this may exceed the model's context, so a hierarchical merge (merge in groups, then merge the groups) is the next fix.
- **Extraction input.** For transcripts over 18,000 characters, action items, decisions and questions are extracted from the summary instead of the full transcript to stay inside the context window (`EXTRACT_MAX_CHARS`).
- **Model quality.** The default 8B model is cheap, but it sometimes produces odd lines (for example "Q: None") in the summary. A larger Workers AI model can be selected through `CLOUDFLARE_MODEL`, at a higher neuron cost.
- **Not built yet:** exporting results (PDF/TXT), streaming chat answers, and deleting videos from the website.