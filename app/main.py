"""FastAPI アプリケーションのエントリーポイント — ルーター組み立て・起動処理"""
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import chat, documents, models as models_api
from app.services.runtime_policy import apply_runtime_network_policy

# 起動時に不要なテレメトリ送信を抑止する。
_applied_runtime_policy = apply_runtime_network_policy()

from app.services import llm, memory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)
if _applied_runtime_policy:
    logger.info("Runtime network policy applied: %s", ", ".join(sorted(_applied_runtime_policy.keys())))


@dataclass
class Settings:
    palace_dir: str = os.getenv("PALACE_DIR", "data/palace")
    history_db: str = os.getenv("HISTORY_DB", "data/history.db")
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    bulk_upload_dir: str = os.getenv("BULK_UPLOAD_DIR", "bulk_uploads")
    extracted_image_dir: str = os.getenv("EXTRACTED_IMAGE_DIR", "uploads/extracted_images")
    ocr_lang: str = os.getenv("OCR_LANG", "jpn+eng")
    excel_table_rows_per_chunk: int = int(os.getenv("EXCEL_TABLE_ROWS_PER_CHUNK", "10"))
    enable_visual_page_ocr: bool = os.getenv("ENABLE_VISUAL_PAGE_OCR", "true").lower() in {"1", "true", "yes", "on"}
    max_visual_ocr_pages: int = int(os.getenv("MAX_VISUAL_OCR_PAGES", "30"))
    soffice_bin: str = os.getenv("SOFFICE_BIN", "soffice")
    listen_addr: str = os.getenv("LISTEN_ADDR", "0.0.0.0:8000")
    copilot_model: str = os.getenv("COPILOT_MODEL", "claude-sonnet-4.5")


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動・終了時の初期化/クリーンアップ処理。"""
    # ディレクトリ作成
    Path(settings.palace_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.history_db).parent.mkdir(parents=True, exist_ok=True)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.bulk_upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.extracted_image_dir).mkdir(parents=True, exist_ok=True)

    # MemPalace パレスを初期化
    memory.init_palace(settings.palace_dir)

    # DB テーブルを初期化
    documents.init_db(settings.history_db)
    chat.init_db(settings.history_db)

    # GitHub Copilot SDK クライアントを起動
    await llm.start_client()

    logger.info("Application started. Palace: %s", settings.palace_dir)

    yield

    # シャットダウン時にクライアントを停止
    await llm.stop_client()
    logger.info("Application stopped.")


app = FastAPI(
    title="Spec Copilot",
    description="仕様書をMemPalaceに格納し、Copilot SDKで回答生成するRAGチャットアプリ",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API ルーター登録
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(models_api.router)

# 静的ファイル配信（SPA）
_static_dir = Path(__file__).parent.parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=str(_static_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    host, _, port = settings.listen_addr.partition(":")
    uvicorn.run("app.main:app", host=host, port=int(port or 8000), reload=True)
