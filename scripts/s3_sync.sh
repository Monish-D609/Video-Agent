#!/usr/bin/env bash
# ============================================================
# S3 Sync Helper for Video Agent
# Synchronizes transcripts, processed results, and chat history.
# Excludes heavy audio files and raw user uploads.
# ============================================================
set -euo pipefail

ACTION="${1:-backup}"
APP_DIR="${APP_DIR:-/opt/video-agent}"
BUCKET_FILE="${BUCKET_FILE:-/etc/video-agent/bucket.name}"

if [[ -z "${S3_BUCKET:-}" ]]; then
    if [[ -f "$BUCKET_FILE" ]]; then
        S3_BUCKET="$(cat "$BUCKET_FILE" | tr -d '[:space:]')"
    else
        echo "❌ Error: S3_BUCKET is not set and $BUCKET_FILE was not found." >&2
        exit 1
    fi
fi

DOWNLOADS_DIR="$APP_DIR/downloads"
mkdir -p "$DOWNLOADS_DIR/raw" "$DOWNLOADS_DIR/processed" "$DOWNLOADS_DIR/session"

AUDIO_EXCLUDES=(
    --exclude "*.wav"
    --exclude "*.mp3"
    --exclude "*.mp4"
    --exclude "*.m4a"
    --exclude "*.webm"
    --exclude "*.flac"
    --exclude "*.ogg"
    --exclude "*.tmp"
)

if [[ "$ACTION" == "backup" ]]; then
    echo "📦 Backing up state to s3://$S3_BUCKET ..."
    # Sync chunk-wise transcripts (JSON only)
    aws s3 sync "$DOWNLOADS_DIR/raw" "s3://$S3_BUCKET/raw" "${AUDIO_EXCLUDES[@]}"
    # Sync combined processed JSON
    aws s3 sync "$DOWNLOADS_DIR/processed" "s3://$S3_BUCKET/processed" "${AUDIO_EXCLUDES[@]}"
    # Sync chat session JSON
    aws s3 sync "$DOWNLOADS_DIR/session" "s3://$S3_BUCKET/session" "${AUDIO_EXCLUDES[@]}"
    echo "✅ S3 backup complete."

elif [[ "$ACTION" == "restore" ]]; then
    echo "📥 Restoring state from s3://$S3_BUCKET ..."
    aws s3 sync "s3://$S3_BUCKET/raw" "$DOWNLOADS_DIR/raw"
    aws s3 sync "s3://$S3_BUCKET/processed" "$DOWNLOADS_DIR/processed"
    aws s3 sync "s3://$S3_BUCKET/session" "$DOWNLOADS_DIR/session"
    echo "✅ S3 restore complete."

else
    echo "Usage: $0 [backup|restore]" >&2
    exit 1
fi
