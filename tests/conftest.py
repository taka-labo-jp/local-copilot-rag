"""テスト共通フィクスチャ — FastAPI TestClient / 一時DB / 一時ディレクトリ"""
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def tmp_dirs(tmp_path):
    """テスト用の一時ディレクトリ群を生成する。"""
    palace = tmp_path / "palace"
    palace.mkdir()
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    bulk = tmp_path / "bulk_uploads"
    bulk.mkdir()
    extracted = tmp_path / "extracted_images"
    extracted.mkdir()
    db_path = str(tmp_path / "test.db")
    return {
        "palace": str(palace),
        "uploads": str(uploads),
        "bulk": str(bulk),
        "extracted": str(extracted),
        "db": db_path,
        "root": tmp_path,
    }


@pytest.fixture()
def mock_settings(tmp_dirs):
    """app.main.settings をテスト用一時ディレクトリに差し替えるフィクスチャ。"""
    from app.main import Settings

    return Settings(
        palace_dir=tmp_dirs["palace"],
        history_db=tmp_dirs["db"],
        upload_dir=tmp_dirs["uploads"],
        bulk_upload_dir=tmp_dirs["bulk"],
        extracted_image_dir=tmp_dirs["extracted"],
        ocr_lang="eng",
        excel_table_rows_per_chunk=10,
        enable_visual_page_ocr=False,
        max_visual_ocr_pages=1,
        soffice_bin="soffice",
    )


@pytest.fixture()
def app_client(mock_settings, tmp_dirs):
    """テスト用 TestClient を返す。

    - DB/Palace の初期化を実行
    - LLM クライアントの起動は mock でスキップ
    - _get_settings を差し替えて一時ディレクトリを使用
    """
    from app.api import chat, documents
    from app.services import memory

    # DB テーブル初期化
    documents.init_db(mock_settings.history_db)
    chat.init_db(mock_settings.history_db)
    memory.init_palace(mock_settings.palace_dir)

    from app.main import app

    # 依存関数を差し替え
    def _override_settings():
        return mock_settings

    app.dependency_overrides[documents._get_settings] = _override_settings
    app.dependency_overrides[chat._get_settings] = _override_settings

    # models API は LLM 不要だが念のためモック
    from app.api import models as models_api

    client = TestClient(app, raise_server_exceptions=False)
    yield client

    app.dependency_overrides.clear()
