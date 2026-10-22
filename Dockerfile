# ============================================================
# Stage 1: Build React Frontend
# ============================================================
FROM node:20-slim AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ============================================================
# Stage 2: Python Backend Runtime
# ============================================================
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WHISPER_MODEL=base

WORKDIR /app

# Install system dependencies: ffmpeg, curl, git
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first (saves ~2GB of unused CUDA packages)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Install application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download default models (Whisper base + HuggingFace embeddings) into cache
RUN python -c "import whisper; whisper.load_model('base'); from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application source code
COPY core/ ./core/
COPY utils/ ./utils/
COPY app.py ./

# Copy compiled frontend from builder
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Prepare directories for bind mounts
RUN mkdir -p /app/downloads /app/vector_db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
