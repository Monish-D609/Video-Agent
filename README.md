# AI Video Agent

Turn any video into something you can read, search and talk to.

Give it a YouTube link or a local video/audio file. It transcribes the speech, writes a title and summary, pulls out action items, decisions and open questions, and lets you **chat with the video**. Answers are grounded only in what is actually said in it.

It supports **English** and **Hinglish** (Hindi mixed with English). Hinglish speech is translated into English while it is transcribed, so everything downstream works in English.

> 🚀 **Deploying to AWS?** See the comprehensive [AWS Deployment Guide](DEPLOYMENT.md) for AWS CDK deployment, cost-controlled single-instance EC2 architecture, S3 backups, and cost control scripts.

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

## How to run it on your device

Follow these step-by-step instructions to set up and run the Video Agent locally from scratch.

### 1. Prerequisites

Ensure the following tools are installed on your device:

1. **Python 3.10 or higher**
   - Verify: `python --version` (or `python3 --version`)
   - Download: [python.org](https://www.python.org/downloads/) *(On Windows, check "Add python.exe to PATH" during installation)*.
2. **FFmpeg** *(Required for audio extraction, chunking, and conversion)*
   - Verify: `ffmpeg -version`
   - **Windows**: Run `winget install Gyan.FFmpeg` or `choco install ffmpeg`. Alternatively, download a build from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and add its `bin` folder to your System `PATH`.
   - **macOS**: Run `brew install ffmpeg`
   - **Linux (Ubuntu/Debian)**: Run `sudo apt update && sudo apt install -y ffmpeg`
3. **Node.js 18+ and npm** *(Required to run the web frontend)*
   - Verify: `node -v` and `npm -v`
   - Download: [nodejs.org](https://nodejs.org/) (LTS recommended).
4. **Git**
   - Verify: `git --version`
   - Download: [git-scm.com](https://git-scm.com/)

---

### 2. Clone the repository

Open your terminal and clone the repository:

```bash
git clone https://github.com/Monish-D609/Video-Agent.git
cd Video-Agent
```

---

### 3. Set up the Python backend

Create an isolated virtual environment and install the Python dependencies.

#### 3.1 Create and activate the virtual environment

- **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
  *(If PowerShell blocks script execution, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process` first).*

- **Windows (Command Prompt):**
  ```cmd
  python -m venv .venv
  .venv\Scripts\activate.bat
  ```

- **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

#### 3.2 Install Python packages

Ensure your virtual environment is active, then install the dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> [!NOTE]
> `requirements.txt` installs PyTorch for CPU by default. If you have an NVIDIA GPU and want faster local Whisper transcription, install the CUDA build of PyTorch following instructions at [pytorch.org](https://pytorch.org/get-started/locally/).

---

### 4. Configure environment variables (`.env`)

The backend requires API credentials for Cloudflare Workers AI (summarization, structured insights, RAG chat) and optionally Sarvam AI (for Hinglish audio).

Create your `.env` file from the example template:

- **Windows:** `copy .env.example .env`
- **macOS / Linux:** `cp .env.example .env`

Open `.env` in your code editor and populate the variables:

```env
# Cloudflare Workers AI (Required)
CLOUDFLARE_ACCOUNT_ID=your_cloudflare_account_id
CLOUDFLARE_API_TOKEN=your_cloudflare_api_token

# Hinglish Translation (Required only if analyzing Hinglish speech)
SARVAM_API_KEY=your_sarvam_api_key

# Optional configuration overrides (defaults shown)
WHISPER_MODEL=small
CLOUDFLARE_MODEL=@cf/meta/llama-3.1-8b-instruct-fp8
CLOUDFLARE_MAX_TOKENS=1024
SARVAM_STT_MODEL=saaras:v2.5
CACHE_DIR=downloads
```

#### How to obtain your API keys:

1. **Cloudflare Workers AI:**
   - Sign up or log in at [dash.cloudflare.com](https://dash.cloudflare.com/).
   - In the dashboard, click **Workers & Pages** to find your **Account ID** in the right-hand panel.
   - Go to **My Profile** → **API Tokens** → **Create Token**.
   - Choose the **Workers AI** template (or configure permissions for `Workers AI: Read/Write`).
   - Copy the generated token into `CLOUDFLARE_API_TOKEN`.

2. **Sarvam AI (Hinglish only):**
   - Register at [dashboard.sarvam.ai](https://dashboard.sarvam.ai/).
   - Copy your API key and set `SARVAM_API_KEY`.
   - *(If you only process English videos, you can leave this blank—local Whisper runs completely offline on your device).*

---

### 5. Install frontend dependencies

Navigate to the `frontend` directory and install the Node.js packages:

```bash
cd frontend
npm install
cd ..
```

---

### 6. Run the application

You can run the app in **Development Mode** (dual-terminal with hot-reloading) or **Single-Server Mode** (production build served via FastAPI).

#### Option A: Development Mode (Recommended)

1. **Terminal 1 — Backend:**
   Activate your virtual environment from the project root and start Uvicorn:
   ```bash
   uvicorn app:app --port 8000 --reload
   ```
   *(Backend starts at `http://localhost:8000`)*

2. **Terminal 2 — Frontend:**
   Navigate to the frontend folder and run Vite:
   ```bash
   cd frontend
   npm run dev
   ```
   *(Frontend starts at `http://localhost:5173` and automatically proxies `/api` calls to port 8000)*

3. Open your browser and navigate to: **`http://localhost:5173`**

---

#### Option B: Single-Server Mode (FastAPI serves built frontend)

1. **Build the frontend bundle:**
   ```bash
   cd frontend
   npm run build
   cd ..
   ```
2. **Start the FastAPI server:**
   ```bash
   uvicorn app:app --port 8000
   ```
3. Open your browser and navigate to: **`http://localhost:8000`**

---

### 7. Verifying your setup

1. Open the web interface in your browser.
2. In the input section, paste a YouTube link or upload a local video/audio file (`.mp4`, `.mp3`, `.wav`, etc.).
3. Choose the spoken language (**English** or **Hinglish**) and click **Analyze video**.
4. **First-run notice:**
   - On the first English run, Whisper downloads the `small` model weights (~461 MB) to your local cache.
   - On the first chat query, Hugging Face downloads the embedding model (`all-MiniLM-L6-v2`).
   - All completed stages are automatically saved under `downloads/` so subsequent runs resume instantly without repeating work.

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