"""チャット関連の Pydantic モデル定義"""
from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    model: str = "claude-sonnet-4.5"
    reasoning_mode: bool = False
    wing: str | None = None
    room: str | None = None
    content_type: str | None = None
    context_files: list[str] | None = None


class ChatMessage(BaseModel):
    id: int
    session_id: str
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime


class ChatSession(BaseModel):
    id: str
    title: str
    created_at: datetime
    message_count: int


class RetrievalLog(BaseModel):
    id: int
    session_id: str
    call_index: int
    query: str
    requested_k: int
    wing: str | None = None
    room: str | None = None
    content_type: str | None = None
    source_files: list[str] = []
    result_count: int
    latency_ms: int
    top_chunk_ids: list[str]
    top_sources: list[str]
    diagnostics: dict
    created_at: datetime
