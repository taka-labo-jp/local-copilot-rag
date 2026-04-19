#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] python3 が見つかりません。Python 3.12+ をインストールしてください。"
  exit 1
fi

echo "[INFO] 仮想環境を作成します (.venv)"
"$PYTHON_BIN" -m venv .venv

source .venv/bin/activate

echo "[INFO] pip を更新します"
pip install --upgrade pip

echo "[INFO] 依存関係をインストールします"
pip install -r requirements.txt

EMBEDDING_MODEL="${EMBEDDING_MODEL:-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2}"
echo "[INFO] 埋め込みモデルを事前取得します (${EMBEDDING_MODEL})"
python - <<PY
from sentence_transformers import SentenceTransformer

model_name = "${EMBEDDING_MODEL}"
SentenceTransformer(model_name)
print(f"[INFO] embedding model ready: {model_name}")
PY

if [[ ! -f .env ]]; then
  echo "[INFO] .env を .env.example から作成します"
  cp .env.example .env
else
  echo "[INFO] .env は既に存在します。スキップします"
fi

mkdir -p data/palace uploads bulk_uploads uploads/extracted_images

echo ""
echo "[DONE] セットアップが完了しました"
echo ""
echo "次の手順:"
echo "  1) source .venv/bin/activate"
echo "  2) uvicorn app.main:app --env-file .env --host 0.0.0.0 --port 8080"
echo ""
echo "補足 (Linux): OCR を有効にする場合は OS 依存ツールを導入してください"
echo "  sudo apt-get update"
echo "  sudo apt-get install -y ffmpeg tesseract-ocr tesseract-ocr-jpn tesseract-ocr-eng libreoffice"
