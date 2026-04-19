"""Pydantic モデル のバリデーションテスト。

検証項目:
- ChatRequest の必須フィールド・デフォルト値
- DocumentUploadResponse のフィールドマッピング
- RetrievalLog の JSON パース
- 不正値のバリデーションエラー
"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.chat import ChatMessage, ChatRequest, ChatSession, RetrievalLog
from app.models.document import (
    DocumentInfo,
    DocumentMoveProjectRequest,
    DocumentUploadResponse,
    ProjectCreateRequest,
    ProjectInfo,
)


class TestChatRequest:
    """ChatRequest モデルのテスト。"""

    def test_minimal_request(self):
        """message のみで作成できる。"""
        req = ChatRequest(message="テスト")
        assert req.message == "テスト"
        assert req.session_id is None
        assert req.model == "claude-sonnet-4.5"
        assert req.reasoning_mode is False
        assert req.wing is None
        assert req.context_files is None

    def test_full_request(self):
        """全フィールド指定で作成できる。"""
        req = ChatRequest(
            message="テスト",
            session_id="abc-123",
            model="gpt-4o",
            reasoning_mode=True,
            wing="specifications",
            room="design",
            content_type="table",
            context_files=["a.txt", "b.pdf"],
        )
        assert req.session_id == "abc-123"
        assert req.reasoning_mode is True
        assert req.context_files == ["a.txt", "b.pdf"]

    def test_missing_message(self):
        """message なしはバリデーションエラー。"""
        with pytest.raises(ValidationError):
            ChatRequest()


class TestDocumentModels:
    """ドキュメント関連モデルのテスト。"""

    def test_upload_response_defaults(self):
        """DocumentUploadResponse のデフォルト値。"""
        resp = DocumentUploadResponse(
            filename="test.txt",
            drawer_count=5,
            wing="specifications",
            room="test",
            message="ok",
        )
        assert resp.project == ""
        assert resp.overwritten_count == 0
        assert resp.text_chunk_count == 0
        assert resp.image_chunk_count == 0

    def test_document_info(self):
        """DocumentInfo が正しく生成される。"""
        doc = DocumentInfo(
            id=1,
            filename="spec.pdf",
            wing="specifications",
            room="design",
            drawer_count=10,
            created_at=datetime(2025, 1, 1),
        )
        assert doc.id == 1
        assert doc.project == ""

    def test_project_create_request(self):
        """ProjectCreateRequest の検証。"""
        req = ProjectCreateRequest(name="MyProject")
        assert req.name == "MyProject"

    def test_move_project_request_default(self):
        """DocumentMoveProjectRequest のデフォルト（未分類への移動）。"""
        req = DocumentMoveProjectRequest()
        assert req.project == ""


class TestRetrievalLog:
    """RetrievalLog モデルのテスト。"""

    def test_retrieval_log(self):
        """全フィールドが正しくマッピングされる。"""
        log = RetrievalLog(
            id=1,
            session_id="sess-1",
            call_index=1,
            query="テスト",
            requested_k=5,
            result_count=3,
            latency_ms=42,
            top_chunk_ids=["c1", "c2"],
            top_sources=["a.txt"],
            diagnostics={"elapsed_ms": 42},
            created_at=datetime(2025, 1, 1),
        )
        assert log.wing is None
        assert log.source_files == []

    def test_retrieval_log_with_filters(self):
        """フィルタ付き RetrievalLog。"""
        log = RetrievalLog(
            id=2,
            session_id="sess-2",
            call_index=1,
            query="test",
            requested_k=10,
            wing="specifications",
            room="design",
            content_type="table",
            source_files=["a.xlsx"],
            result_count=5,
            latency_ms=100,
            top_chunk_ids=[],
            top_sources=[],
            diagnostics={},
            created_at=datetime(2025, 6, 1),
        )
        assert log.wing == "specifications"
        assert log.source_files == ["a.xlsx"]


class TestChatSession:
    """ChatSession モデルのテスト。"""

    def test_chat_session(self):
        """ChatSession の基本検証。"""
        session = ChatSession(
            id="sid-1",
            title="テスト会話",
            created_at=datetime(2025, 1, 1),
            message_count=3,
        )
        assert session.id == "sid-1"
        assert session.message_count == 3
