#!/usr/bin/env bash
set -euo pipefail

MODELS_DIR=${1:-"models"}
mkdir -p "$MODELS_DIR"

echo "Downloading faster-whisper small model (placeholder)..."
if command -v wget >/dev/null 2>&1; then
  wget -qO- https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin?download=1 \
    > "$MODELS_DIR/ggml-small.bin" || true
else
  echo "wget not found, please download models manually" >&2
fi

echo "Download language ID model"
if command -v wget >/dev/null 2>&1; then
  wget -qO "$MODELS_DIR/lid.176.bin" https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin || true
fi

echo "Models prepared in $MODELS_DIR"
