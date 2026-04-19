# Spec Copilot

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](#環境要件)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

仕様書ファイルを取り込み、ローカル知識ベース検索（LangChain + ChromaDB）と GitHub Copilot SDK を組み合わせて回答を生成する RAG チャットアプリです。

> [!WARNING]
> 生成AIによって実装したものであり、ハルシネーションが含まれる可能性があります。

## 主な機能
- 仕様書アップロード（単体 + フォルダ再帰一括）
- プロジェクト単位のドキュメント整理（追加 / 移動 / 空プロジェクト削除）
- コンテキスト指定検索（ファイル・分類・プロジェクト単位で追加）
- 会話履歴と retrieval 診断ログ
- ダーク/ライトモード切替
- UI 言語切替（日本語 / 英語）
- Query Transform + Reranking による検索精度改善

## UI

### ライトモード + 日本語
![](./docs/images/light_japanase.png)

### ダークモード + 英語
![](./docs/images/dark_english.png)


## アーキテクチャ
- Web/API: FastAPI
- 変換: markitdown + Pandas + openpyxl + Tesseract OCR（+ 任意でLibreOfficeページOCR）
- 検索: LangChain + ChromaDB（ローカル永続）
- 埋め込み: sentence-transformers
- 生成: GitHub Copilot SDK

## 対応拡張子
現在の実装でアップロード受け付け対象としている拡張子は以下です。

| 区分 | 拡張子 |
| --- | --- |
| Office | `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt` |
| 文書 | `.pdf`, `.html`, `.htm`, `.md`, `.txt` |
| データ | `.csv`, `.json`, `.xml` |
| 追加形式 | `.epub`, `.zip` |

実装定義は [app/api/documents.py](app/api/documents.py) の `ALLOWED_EXTENSIONS` にあります。

## 環境要件
- Python 3.12+
- Linux/macOS 推奨

補足:
- ChromaDB サーバーの別立ては不要です（`langchain-chroma` のローカル永続利用）。
- `setup.sh` 実行時に `sentence-transformers` の埋め込みモデルを事前取得します。
- OCRには OS 側の `tesseract` バイナリが必要です。

## セットアップ

### 1. 自動セットアップ（推奨）
```bash
./setup.sh
```

### 2. 手動セットアップ
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. 起動
```bash
source .venv/bin/activate
uvicorn app.main:app --env-file .env --host 0.0.0.0 --port 8080
```

アクセス先: `http://localhost:8080`

## 設定
主要設定は [.env.example](.env.example) を参照してください。

- `COPILOT_MODEL`
- `LISTEN_ADDR`
- `HISTORY_DB`
- `UPLOAD_DIR`
- `PALACE_DIR`
- `BULK_UPLOAD_DIR`
- `EXTRACTED_IMAGE_DIR`
- `OCR_LANG`
- `EMBEDDING_MODEL`
- `EMBEDDING_LOCAL_FILES_ONLY`
- `DISABLE_RUNTIME_TELEMETRY`
- `EXCEL_TABLE_ROWS_PER_CHUNK`
- `ENABLE_VISUAL_PAGE_OCR`
- `MAX_VISUAL_OCR_PAGES`
- `SOFFICE_BIN`

### OCRセットアップ（Linux）
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg tesseract-ocr tesseract-ocr-jpn tesseract-ocr-eng libreoffice
```

## 使い方
1. サイドバーから仕様書をアップロード
2. 必要に応じてプロジェクトへ整理
3. コンテキスト（⊕ボタン or 右クリック）で検索対象を限定
4. チャットで質問し、必要に応じて retrieval ログで挙動確認

## API（抜粋）
- `POST /api/documents`
- `POST /api/documents/bulk-upload`
- `GET /api/documents`
- `DELETE /api/documents/{doc_id}`
- `GET /api/documents/projects`
- `POST /api/documents/projects`
- `DELETE /api/documents/projects/{project_id}`
- `PATCH /api/documents/{doc_id}/project`
- `POST /api/chat`
- `GET /api/history`
- `GET /api/history/{session_id}/retrievals`

## 認証: GitHub Copilot CLI

このアプリは **GitHub Copilot SDK** を使用して LLM 応答を生成します。API キーの手動管理は不要で、GitHub Copilot CLI の認証トークンが自動的に利用されます。

### 前提条件
1. GitHub Copilot のサブスクリプションが有効であること
2. GitHub Copilot CLI がインストール・認証済みであること

### セットアップ
```bash
# GitHub CLI をインストール（未導入の場合）
# https://cli.github.com/

# GitHub にログイン
gh auth login

# Copilot 拡張をインストール
gh extension install github/gh-copilot

# 認証状態を確認
gh auth status
gh copilot --version
```

認証済みの状態でアプリを起動すると、`github-copilot-sdk` が OS のトークンストアから認証情報を自動取得します。`.env` に API キーを記載する必要はありません。

## 外部通信ポリシー

このリポジトリでは、通常運用時（セットアップ完了後）に発生する外部通信を最小化する設計を採用しています。

- LLM 応答生成の外部通信: **GitHub Copilot SDK のみ**
- フロントエンド: `marked` は CDN ではなく `static/vendor/marked.min.js` をローカル配信
- 検索・履歴・文書保存: ChromaDB / SQLite をローカル利用
- 埋め込みモデル: `setup.sh` で事前取得し、実行時は `EMBEDDING_LOCAL_FILES_ONLY=true` でローカルキャッシュのみ参照
- ランタイム抑止: `DISABLE_RUNTIME_TELEMETRY=true`（既定）で `posthog/opentelemetry/huggingface telemetry` を無効化

注意:
- 依存パッケージのインストール、GitHub CLI/Copilot CLI 認証、埋め込みモデルの初回取得はセットアップ時の外部通信に含まれます。

### システム構成図（ASCII）

```text
┌────────────────────────────────────────────────────────────┐
│ Browser (127.0.0.1)                                        │
│  - static/index.html                                       │
│  - static/app.js                                           │
│  - static/vendor/marked.min.js (local)                    │
└───────────────┬────────────────────────────────────────────┘
		│ HTTP (local)
		▼
┌────────────────────────────────────────────────────────────┐
│ FastAPI App (app/main.py)                                 │
│  /api/chat /api/documents /api/history                    │
└───────┬───────────────────────────────┬────────────────────┘
	│                               │
	│ local                         │ local
	▼                               ▼
┌──────────────────────────┐   ┌────────────────────────────┐
│ ChromaDB (data/palace)   │   │ SQLite (data/history.db)   │
│ + Embeddings cache(local)│   │ chat/doc metadata          │
└──────────────────────────┘   └────────────────────────────┘
	│
	│ external (only for LLM response)
	▼
┌────────────────────────────────────────────────────────────┐
│ GitHub Copilot SDK                                         │
│  - authenticated via GitHub Copilot CLI token store        │
└────────────────────────────────────────────────────────────┘
```

## セキュリティ

### 確認済みセキュリティ対策

| カテゴリ | 対策内容 | 状態 |
| --- | --- | --- |
| **シークレット管理** | API キー/トークン/パスワードのハードコードなし。`.env` 実体は `.gitignore` 対象 | ✅ |
| **認証・認可** | GitHub Copilot SDK のトークンは OS 認証ストア経由で取得。アプリ内に認証情報を保持しない | ✅ |
| **SQL インジェクション** | 全 SQL クエリがパラメタライズドクエリ（`?` プレースホルダ）で実行。テストで攻撃文字列を検証済み | ✅ |
| **ファイルアップロード** | 拡張子ホワイトリスト方式（16種のみ許可）。実行可能形式は全てブロック | ✅ |
| **パストラバーサル** | アップロードファイルはファイルシステムに直接保存されず、一時ファイル経由で markitdown 変換後にテキストのみ DB 登録 | ✅ |
| **XSS** | フロントエンドは DOM 操作（`textContent`）ベース。`innerHTML` の使用箇所は Markdown レンダリング向けのサニタイズ済み出力のみ | ✅ |
| **データ隔離** | 実データ保存先（`data/`, `uploads/`, `bulk_uploads/`, `test_samples/`）を `.gitignore` で除外 | ✅ |
| **プロンプトインジェクション** | システムプロンプトで knowledge_search 結果を `<context>` タグで囲みデータとして扱う指示を明示。命令実行を禁止 | ✅ |
| **外部コマンド実行** | `subprocess.run` は LibreOffice OCR 用のみ。`shell=False`（デフォルト）で実行、120秒タイムアウト付き | ✅ |
| **依存パッケージ** | `requirements.txt` でバージョン固定。定期的な `pip audit` の実施を推奨 | ✅ |

### 既知の制約・改善候補

| 項目 | 現状 | 推奨改善 |
| --- | --- | --- |
| CORS | `allow_origins=["*"]`（開発用の全許可） | 本番ではオリジンを明示的に制限する |
| レートリミット | 未実装 | 公開環境では `slowapi` 等の導入を推奨 |
| ファイルサイズ制限 | FastAPI/uvicorn のデフォルト（約100MB） | 環境変数で明示的な上限を設定する |
| HTTPS | ローカル実行前提で HTTP | リバースプロキシ（nginx 等）で TLS 終端する |
| セキュリティヘッダ | CSP/X-Frame-Options 等未設定 | 本番ではミドルウェアまたはリバースプロキシで付与する |
| 認証・認可 | アプリレベルのユーザー認証なし | マルチユーザー環境では OAuth 等を導入する |
| ログ | 標準出力のみ | 本番では構造化ログ + ログ集約基盤を推奨 |

### セキュリティスキャン
```bash
# 依存パッケージの脆弱性チェック
pip install pip-audit
pip-audit

# シークレットスキャン（grep ベース）
grep -RInE '(password|secret|token|api_key)\s*=' --include='*.py' --include='*.env*' .
```

## ライセンス
MIT License。詳細は [LICENSE](LICENSE) を参照してください。
