"""チャットAPI のユニットテスト。

検証項目:
- 会話セッション作成・一覧取得
- メッセージ履歴取得
- セッション削除（正常系・存在しないID）
- 存在しないセッションのメッセージ取得→404
- Retrieval ログ取得
"""
import io
import json
from unittest.mock import AsyncMock, patch

import pytest


class TestChatHistory:
    """GET /api/history のテスト。"""

    def test_list_empty_history(self, app_client):
        """初期状態では空リストを返す。"""
        resp = app_client.get("/api/history")
        assert resp.status_code == 200
        assert resp.json() == []


class TestChatSessionMessages:
    """GET /api/history/{session_id} のテスト。"""

    def test_get_nonexistent_session(self, app_client):
        """存在しないセッションのメッセージ取得は404を返す。"""
        resp = app_client.get("/api/history/nonexistent-id")
        assert resp.status_code == 404


class TestDeleteSession:
    """DELETE /api/history/{session_id} のテスト。"""

    def test_delete_nonexistent_session(self, app_client):
        """存在しないセッションの削除は404を返す。"""
        resp = app_client.delete("/api/history/nonexistent-id")
        assert resp.status_code == 404


class TestChatEndpoint:
    """POST /api/chat のテスト（LLM はモック）。"""

    def test_chat_creates_session_and_streams(self, app_client):
        """チャットリクエストでセッションが作成されSSEストリームが返る。"""

        async def mock_stream(*args, **kwargs):
            yield "テスト応答"

        with patch("app.services.llm.generate_stream", side_effect=mock_stream):
            resp = app_client.post(
                "/api/chat",
                json={"message": "テスト質問です"},
            )
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        # SSEデータをパース
        lines = resp.text.strip().split("\n\n")
        events = []
        for line in lines:
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

        # session_id イベントが先頭にある
        assert events[0]["type"] == "session_id"
        session_id = events[0]["session_id"]
        assert session_id  # 空でない

        # delta イベントが含まれる
        deltas = [e for e in events if e["type"] == "delta"]
        assert len(deltas) >= 1
        assert deltas[0]["content"] == "テスト応答"

        # done イベントが末尾にある
        assert events[-1]["type"] == "done"

    def test_chat_with_existing_session(self, app_client):
        """既存セッションIDを指定してチャットできる。"""

        async def mock_stream(*args, **kwargs):
            yield "回答"

        with patch("app.services.llm.generate_stream", side_effect=mock_stream):
            resp1 = app_client.post(
                "/api/chat",
                json={"message": "1問目"},
            )
        events1 = []
        for line in resp1.text.strip().split("\n\n"):
            if line.startswith("data: "):
                events1.append(json.loads(line[6:]))
        sid = events1[0]["session_id"]

        with patch("app.services.llm.generate_stream", side_effect=mock_stream):
            resp2 = app_client.post(
                "/api/chat",
                json={"message": "2問目", "session_id": sid},
            )
        assert resp2.status_code == 200

        # セッション一覧に1つだけ存在する
        history = app_client.get("/api/history").json()
        assert len(history) == 1
        assert history[0]["id"] == sid

    def test_chat_saves_messages(self, app_client):
        """チャット後にメッセージ履歴が保存される。"""

        async def mock_stream(*args, **kwargs):
            yield "保存テスト"

        with patch("app.services.llm.generate_stream", side_effect=mock_stream):
            resp = app_client.post(
                "/api/chat",
                json={"message": "質問"},
            )
        events = []
        for line in resp.text.strip().split("\n\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        sid = events[0]["session_id"]

        msgs = app_client.get(f"/api/history/{sid}").json()
        assert len(msgs) == 2  # user + assistant
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "質問"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == "保存テスト"

    def test_chat_with_filters(self, app_client):
        """検索フィルタ付きリクエストが正常に処理される。"""

        async def mock_stream(*args, **kwargs):
            yield "フィルタ応答"

        with patch("app.services.llm.generate_stream", side_effect=mock_stream):
            resp = app_client.post(
                "/api/chat",
                json={
                    "message": "フィルタテスト",
                    "wing": "specifications",
                    "room": "test",
                    "content_type": "text",
                    "context_files": ["spec.txt"],
                },
            )
        assert resp.status_code == 200

    def test_chat_error_handling(self, app_client):
        """LLMストリームでエラーが発生した場合、errorイベントが返る。"""

        async def mock_stream_error(*args, **kwargs):
            raise RuntimeError("LLM接続エラー")
            yield  # noqa: unreachable — ジェネレータにするため

        with patch("app.services.llm.generate_stream", side_effect=mock_stream_error):
            resp = app_client.post(
                "/api/chat",
                json={"message": "エラーテスト"},
            )
        assert resp.status_code == 200  # SSE自体は200
        events = []
        for line in resp.text.strip().split("\n\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) >= 1


class TestRetrievalLogs:
    """GET /api/history/{session_id}/retrievals のテスト。"""

    def test_retrieval_logs_empty(self, app_client):
        """検索ログがないセッションでは空リストを返す。"""

        async def mock_stream(*args, **kwargs):
            yield "ok"

        with patch("app.services.llm.generate_stream", side_effect=mock_stream):
            resp = app_client.post(
                "/api/chat",
                json={"message": "ログテスト"},
            )
        events = []
        for line in resp.text.strip().split("\n\n"):
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
        sid = events[0]["session_id"]

        logs = app_client.get(f"/api/history/{sid}/retrievals").json()
        assert logs == []
