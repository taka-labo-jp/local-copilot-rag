"""モデルAPI のユニットテスト。

検証項目:
- GET /api/models が正常にリストを返す（LLMモック時）
- GET /api/models?premium=false が消費量0のモデルのみを返す
"""
from unittest.mock import AsyncMock, patch

import pytest


class TestModelsApi:
    """GET /api/models のテスト。"""

    def test_list_models_mocked(self, app_client):
        """LLMをモックしてモデル一覧を取得できる。"""
        mock_models = [
            {"id": "claude-sonnet-4.5", "name": "Claude Sonnet 4.5", "billing": {"cost_multiplier": 1.0}},
            {"id": "gpt-4o", "name": "GPT-4o", "billing": {"cost_multiplier": 1.0}},
        ]
        with patch("app.services.llm.list_models", new_callable=AsyncMock, return_value=mock_models):
            resp = app_client.get("/api/models")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 2
        assert body[0]["id"] == "claude-sonnet-4.5"

    def test_list_models_premium_false(self, app_client):
        """premium=false のとき消費量0のモデルのみを返す。"""
        mock_models = [
            {"id": "free-model", "name": "Free Model", "billing": {"cost_multiplier": 0}},
        ]
        with patch("app.services.llm.list_models", new_callable=AsyncMock, return_value=mock_models) as mock:
            resp = app_client.get("/api/models?premium=false")
        assert resp.status_code == 200
        mock.assert_called_once_with(premium=False)
        body = resp.json()
        assert len(body) == 1
        assert body[0]["id"] == "free-model"

    def test_list_models_premium_true(self, app_client):
        """premium=true のとき list_models に True が渡される。"""
        mock_models = [
            {"id": "premium-model", "name": "Premium Model", "billing": {"cost_multiplier": 1.0}},
        ]
        with patch("app.services.llm.list_models", new_callable=AsyncMock, return_value=mock_models) as mock:
            resp = app_client.get("/api/models?premium=true")
        assert resp.status_code == 200
        mock.assert_called_once_with(premium=True)
        body = resp.json()
        assert len(body) == 1
        assert body[0]["id"] == "premium-model"

    def test_list_models_no_premium_param(self, app_client):
        """premium パラメータなしのとき list_models に None が渡される（全件返す）。"""
        mock_models = [
            {"id": "model-a", "name": "Model A", "billing": {"cost_multiplier": 0}},
            {"id": "model-b", "name": "Model B", "billing": {"cost_multiplier": 1.0}},
        ]
        with patch("app.services.llm.list_models", new_callable=AsyncMock, return_value=mock_models) as mock:
            resp = app_client.get("/api/models")
        assert resp.status_code == 200
        mock.assert_called_once_with(premium=None)
        assert len(resp.json()) == 2
