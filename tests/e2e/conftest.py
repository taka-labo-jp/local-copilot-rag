"""E2E テスト共通フィクスチャ

pytest-playwright を使用してローカルの FastAPI サーバーに対して E2E テストを実行する。

実行前にサーバーが起動している必要がある:
    uvicorn app.main:app --host 0.0.0.0 --port 8080

または BASE_URL 環境変数でカスタム URL を指定:
    BASE_URL=http://localhost:18080 pytest tests/e2e/
"""
import os

import pytest

BASE_URL = os.environ.get("BASE_URL", "http://localhost:18080")


@pytest.fixture(scope="session")
def base_url():
    """pytest-playwright が使う base_url を返す。"""
    return BASE_URL
