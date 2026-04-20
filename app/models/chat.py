"""チャット関連の Pydantic モデル定義"""
from datetime import datetime
from typing import Literal

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
    todo_count: int = 0


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


TodoStatus = Literal["draft", "in_progress", "review_required", "done"]
TodoLinkType = Literal["message", "retrieval", "draft"]


class TodoCreateRequest(BaseModel):
    title: str
    description: str = ""
    acceptance_criteria: str = ""
    created_from_message_id: int | None = None


class TodoUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    acceptance_criteria: str | None = None
    status: TodoStatus | None = None


class TodoApproveRequest(BaseModel):
    approved_by: str = "reviewer"


class TodoFromChatRequest(BaseModel):
    message_id: int
    title: str | None = None
    description: str = ""
    acceptance_criteria: str = ""


class TodoDraftGenerateRequest(BaseModel):
    model: str = "claude-sonnet-4.5"


class TodoPreviewRequest(BaseModel):
    message_id: int
    model: str = "claude-sonnet-4.5"


class TodoPreviewResponse(BaseModel):
    title: str
    description: str = ""
    acceptance_criteria: str = ""


class TodoLinkItem(BaseModel):
    id: int
    todo_id: int
    session_id: str
    link_type: TodoLinkType
    message_id: int | None = None
    retrieval_log_id: int | None = None
    note: str = ""
    created_at: datetime


class TodoPhaseLogItem(BaseModel):
    id: int
    todo_id: int
    session_id: str
    from_status: TodoStatus | None = None
    to_status: TodoStatus
    actor: str
    reason: str = ""
    created_at: datetime


class TodoItem(BaseModel):
    id: int
    session_id: str
    title: str
    description: str
    acceptance_criteria: str
    status: TodoStatus
    created_from_message_id: int | None = None
    ai_draft_message_id: int | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class TodoDetailResponse(BaseModel):
    item: TodoItem
    links: list[TodoLinkItem]
    phase_logs: list[TodoPhaseLogItem]
