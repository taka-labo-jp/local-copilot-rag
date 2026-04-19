"""モデルAPI のユニットテスト。

検証項目:
- GET /api/models が正常にリストを返す（LLMモック時）
"""
from unittest.mock import AsyncMock, patch

import pytest


class TestModelsApi:
    """GET /api/models のテスト。"""

    def test_list_models_mocked(self, app_client):
        """LLMをモックしてモデル一覧を取得できる。"""
        mock_models = [
            {"id": "claude-sonnet-4.5", "name": "Claude Sonnet 4.5"},
            {"id": "gpt-4o", "name": "GPT-4o"},
        ]
        with patch("app.services.llm.list_models", new_callable=AsyncMock, return_value=mock_models):
            resp = app_client.get("/api/models")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        assert body[0]["id"] == "claude-sonnet-4.5"
