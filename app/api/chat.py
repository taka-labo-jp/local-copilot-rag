"""チャットAPI — MemPalace 検索ツール付き Copilot SDK でストリーミング回答 + 会話履歴管理"""
import json
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.models.chat import (
    ChatMessage,
    ChatRequest,
    ChatSession,
    RetrievalLog,
    TodoApproveRequest,
    TodoCreateRequest,
    TodoDetailResponse,
    TodoDraftGenerateRequest,
    TodoFromChatRequest,
    TodoItem,
    TodoLinkItem,
    TodoPhaseLogItem,
    TodoPreviewRequest,
    TodoPreviewResponse,
    TodoStatus,
    TodoUpdateRequest,
)
from app.services import llm

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


def _get_settings():
    from app.main import settings

    return settings


def _get_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _audit_event(event: str, payload: dict[str, Any]) -> None:
    logger.info("todo_audit %s", json.dumps({"event": event, **payload}, ensure_ascii=False))


def init_db(db_path: str) -> None:
    """会話履歴テーブルを初期化する。"""
    with _get_db(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL DEFAULT '新しい会話',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_retrieval_logs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id       TEXT NOT NULL,
                call_index       INTEGER NOT NULL,
                query            TEXT NOT NULL,
                requested_k      INTEGER NOT NULL,
                wing             TEXT,
                room             TEXT,
                content_type     TEXT,
                source_files_json TEXT NOT NULL DEFAULT '[]',
                result_count     INTEGER NOT NULL,
                latency_ms       INTEGER NOT NULL,
                top_chunk_ids    TEXT NOT NULL,
                top_sources      TEXT NOT NULL,
                diagnostics_json TEXT NOT NULL,
                created_at       TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
            """
        )
        retrieval_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(chat_retrieval_logs)").fetchall()
        }
        for col, sql_type in (("wing", "TEXT"), ("room", "TEXT"), ("content_type", "TEXT"), ("source_files_json", "TEXT")):
            if col not in retrieval_columns:
                conn.execute(f"ALTER TABLE chat_retrieval_logs ADD COLUMN {col} {sql_type}")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todo_items (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id              TEXT,
                title                   TEXT NOT NULL,
                description             TEXT NOT NULL DEFAULT '',
                acceptance_criteria     TEXT NOT NULL DEFAULT '',
                status                  TEXT NOT NULL DEFAULT 'draft',
                created_from_message_id INTEGER,
                ai_draft_message_id     INTEGER,
                approved_by             TEXT,
                approved_at             TEXT,
                created_at              TEXT NOT NULL,
                updated_at              TEXT NOT NULL,
                CHECK (status IN ('draft','in_progress','review_required','done')),
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
                FOREIGN KEY (created_from_message_id) REFERENCES chat_messages(id),
                FOREIGN KEY (ai_draft_message_id) REFERENCES chat_messages(id)
            )
            """
        )
        todo_columns = {row[1] for row in conn.execute("PRAGMA table_info(todo_items)").fetchall()}
        for col, sql_type in (
            ("session_id", "TEXT"),
            ("acceptance_criteria", "TEXT NOT NULL DEFAULT ''"),
            ("created_from_message_id", "INTEGER"),
            ("ai_draft_message_id", "INTEGER"),
        ):
            if col not in todo_columns:
                conn.execute(f"ALTER TABLE todo_items ADD COLUMN {col} {sql_type}")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todo_phase_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                todo_id      INTEGER NOT NULL,
                session_id   TEXT NOT NULL,
                from_status  TEXT,
                to_status    TEXT NOT NULL,
                actor        TEXT NOT NULL,
                reason       TEXT NOT NULL DEFAULT '',
                created_at   TEXT NOT NULL,
                FOREIGN KEY (todo_id) REFERENCES todo_items(id),
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS todo_links (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                todo_id           INTEGER NOT NULL,
                session_id        TEXT NOT NULL,
                link_type         TEXT NOT NULL,
                message_id        INTEGER,
                retrieval_log_id  INTEGER,
                note              TEXT NOT NULL DEFAULT '',
                created_at        TEXT NOT NULL,
                CHECK (link_type IN ('message','retrieval','draft')),
                FOREIGN KEY (todo_id) REFERENCES todo_items(id),
                FOREIGN KEY (session_id) REFERENCES chat_sessions(id),
                FOREIGN KEY (message_id) REFERENCES chat_messages(id),
                FOREIGN KEY (retrieval_log_id) REFERENCES chat_retrieval_logs(id)
            )
            """
        )


def _ensure_session_exists(conn: sqlite3.Connection, session_id: str) -> None:
    exists = conn.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")


def _row_to_todo_item(row: sqlite3.Row) -> TodoItem:
    return TodoItem(
        id=row["id"],
        session_id=row["session_id"],
        title=row["title"],
        description=row["description"],
        acceptance_criteria=row["acceptance_criteria"] or "",
        status=row["status"],
        created_from_message_id=row["created_from_message_id"],
        ai_draft_message_id=row["ai_draft_message_id"],
        approved_by=row["approved_by"],
        approved_at=datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


def _row_to_todo_link(row: sqlite3.Row) -> TodoLinkItem:
    return TodoLinkItem(
        id=row["id"],
        todo_id=row["todo_id"],
        session_id=row["session_id"],
        link_type=row["link_type"],
        message_id=row["message_id"],
        retrieval_log_id=row["retrieval_log_id"],
        note=row["note"] or "",
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _row_to_phase_log(row: sqlite3.Row) -> TodoPhaseLogItem:
    return TodoPhaseLogItem(
        id=row["id"],
        todo_id=row["todo_id"],
        session_id=row["session_id"],
        from_status=row["from_status"],
        to_status=row["to_status"],
        actor=row["actor"],
        reason=row["reason"] or "",
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _validate_transition(current: TodoStatus, next_status: TodoStatus) -> bool:
    allowed: dict[TodoStatus, set[TodoStatus]] = {
        "draft": {"in_progress", "review_required"},
        "in_progress": {"draft", "review_required"},
        "review_required": {"in_progress"},
        "done": set(),
    }
    return next_status == current or next_status in allowed[current]


def _insert_phase_log(
    conn: sqlite3.Connection,
    *,
    todo_id: int,
    session_id: str,
    from_status: str | None,
    to_status: str,
    actor: str,
    reason: str,
) -> None:
    conn.execute(
        """
        INSERT INTO todo_phase_logs (
            todo_id, session_id, from_status, to_status, actor, reason, created_at
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (todo_id, session_id, from_status, to_status, actor, reason, datetime.now().isoformat()),
    )


def _get_session_message(conn: sqlite3.Connection, session_id: str, message_id: int) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, role, content FROM chat_messages WHERE id = ? AND session_id = ?",
        (message_id, session_id),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="対象メッセージが見つかりません")
    return row


@router.post("/chat")
async def chat(req: ChatRequest, settings=Depends(_get_settings)) -> StreamingResponse:
    """チャット指示を受け取り、Copilot SDK 経由でストリーミング応答を返す。"""
    session_id = req.session_id or str(uuid.uuid4())
    search_filters: dict[str, Any] = {}
    if req.wing:
        search_filters["wing"] = req.wing
    if req.room:
        search_filters["room"] = req.room
    if req.content_type:
        search_filters["content_type"] = req.content_type
    if req.context_files:
        files = [f.strip() for f in req.context_files if str(f).strip()]
        if files:
            search_filters["source_files"] = files

    with _get_db(settings.history_db) as conn:
        exists = conn.execute("SELECT id FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
        if not exists:
            title = req.message[:40] + ("…" if len(req.message) > 40 else "")
            conn.execute(
                "INSERT INTO chat_sessions (id, title, created_at) VALUES (?,?,?)",
                (session_id, title, datetime.now().isoformat()),
            )
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (session_id, "user", req.message, datetime.now().isoformat()),
        )

    async def event_stream():
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
        yield f"data: {json.dumps({'type': 'status', 'status': 'thinking'})}\n\n"

        collected = []
        retrieval_logs: list[dict[str, Any]] = []
        pending_status_events: list[dict[str, Any]] = []

        def _on_search(item: dict[str, Any]) -> None:
            item["call_index"] = len(retrieval_logs) + 1
            retrieval_logs.append(item)
            pending_status_events.append({"type": "status", "status": "searching", "query": item.get("query", "")})

        try:
            async for chunk in llm.generate_stream(
                prompt=req.message,
                palace_path=settings.palace_dir,
                model=req.model,
                reasoning_mode=req.reasoning_mode,
                on_search=_on_search,
                search_filters=search_filters or None,
            ):
                while pending_status_events:
                    yield f"data: {json.dumps(pending_status_events.pop(0))}\n\n"
                collected.append(chunk)
                yield f"data: {json.dumps({'type': 'delta', 'content': chunk})}\n\n"
        except Exception as e:
            logger.exception("生成エラー")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        full_response = "".join(collected)
        if full_response or retrieval_logs:
            now = datetime.now().isoformat()
            with _get_db(settings.history_db) as conn:
                if full_response:
                    conn.execute(
                        "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
                        (session_id, "assistant", full_response, now),
                    )

                for item in retrieval_logs:
                    diagnostics = item.get("diagnostics", {})
                    conn.execute(
                        """
                        INSERT INTO chat_retrieval_logs (
                            session_id, call_index, query, requested_k, wing, room, content_type, source_files_json, result_count,
                            latency_ms, top_chunk_ids, top_sources, diagnostics_json, created_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """,
                        (
                            session_id,
                            int(item.get("call_index", 0)),
                            str(item.get("query", "")),
                            int(item.get("requested_k", 0)),
                            item.get("wing"),
                            item.get("room"),
                            item.get("content_type"),
                            json.dumps(item.get("source_files", []), ensure_ascii=False),
                            int(item.get("result_count", 0)),
                            int(diagnostics.get("elapsed_ms", 0)),
                            json.dumps(item.get("top_chunk_ids", []), ensure_ascii=False),
                            json.dumps(item.get("top_sources", []), ensure_ascii=False),
                            json.dumps(diagnostics, ensure_ascii=False),
                            now,
                        ),
                    )

        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/history", response_model=list[ChatSession])
async def list_sessions(settings=Depends(_get_settings)) -> list[ChatSession]:
    """会話セッション一覧を返す（最新順）。"""
    with _get_db(settings.history_db) as conn:
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.title,
                s.created_at,
                (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id) AS message_count,
                (SELECT COUNT(*) FROM todo_items t WHERE t.session_id = s.id) AS todo_count
            FROM chat_sessions s
            ORDER BY s.created_at DESC
            """
        ).fetchall()
    return [
        ChatSession(
            id=r["id"],
            title=r["title"],
            created_at=datetime.fromisoformat(r["created_at"]),
            message_count=r["message_count"],
            todo_count=r["todo_count"],
        )
        for r in rows
    ]


@router.get("/history/{session_id}", response_model=list[ChatMessage])
async def get_session_messages(session_id: str, settings=Depends(_get_settings)) -> list[ChatMessage]:
    """指定セッションのメッセージ一覧を返す。"""
    with _get_db(settings.history_db) as conn:
        rows = conn.execute(
            "SELECT id, session_id, role, content, created_at FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")
    return [
        ChatMessage(
            id=r["id"],
            session_id=r["session_id"],
            role=r["role"],
            content=r["content"],
            created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in rows
    ]


@router.get("/history/{session_id}/retrievals", response_model=list[RetrievalLog])
async def get_session_retrieval_logs(session_id: str, settings=Depends(_get_settings)) -> list[RetrievalLog]:
    """指定セッションのretrievalログを返す。"""
    with _get_db(settings.history_db) as conn:
        rows = conn.execute(
            "SELECT id, session_id, call_index, query, requested_k, wing, room, content_type, source_files_json, result_count, latency_ms, "
            "top_chunk_ids, top_sources, diagnostics_json, created_at "
            "FROM chat_retrieval_logs WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()

    return [
        RetrievalLog(
            id=r["id"],
            session_id=r["session_id"],
            call_index=r["call_index"],
            query=r["query"],
            requested_k=r["requested_k"],
            wing=r["wing"],
            room=r["room"],
            content_type=r["content_type"],
            source_files=json.loads(r["source_files_json"] or "[]"),
            result_count=r["result_count"],
            latency_ms=r["latency_ms"],
            top_chunk_ids=json.loads(r["top_chunk_ids"] or "[]"),
            top_sources=json.loads(r["top_sources"] or "[]"),
            diagnostics=json.loads(r["diagnostics_json"] or "{}"),
            created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in rows
    ]


@router.get("/history/{session_id}/todos", response_model=list[TodoItem])
async def list_todos(
    session_id: str,
    status: TodoStatus | None = Query(default=None),
    settings=Depends(_get_settings),
) -> list[TodoItem]:
    """セッション単位TODOを一覧で返す。"""
    with _get_db(settings.history_db) as conn:
        _ensure_session_exists(conn, session_id)
        if status:
            rows = conn.execute(
                "SELECT * FROM todo_items WHERE session_id = ? AND status = ? ORDER BY updated_at DESC, id DESC",
                (session_id, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM todo_items WHERE session_id = ? ORDER BY updated_at DESC, id DESC",
                (session_id,),
            ).fetchall()
    return [_row_to_todo_item(r) for r in rows]


@router.post("/history/{session_id}/todos", response_model=TodoItem)
async def create_todo(
    session_id: str,
    payload: TodoCreateRequest,
    settings=Depends(_get_settings),
) -> TodoItem:
    """セッション単位TODOを作成する。"""
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="title は必須です")

    now = datetime.now().isoformat()
    with _get_db(settings.history_db) as conn:
        _ensure_session_exists(conn, session_id)
        source_message_id = payload.created_from_message_id
        if source_message_id is not None:
            message_row = _get_session_message(conn, session_id, source_message_id)
            if message_row["role"] != "assistant":
                raise HTTPException(status_code=400, detail="assistant回答のみTODO化できます")
        cur = conn.execute(
            """
            INSERT INTO todo_items (
                session_id, title, description, acceptance_criteria, status,
                created_from_message_id, approved_by, approved_at, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                session_id,
                title,
                payload.description,
                payload.acceptance_criteria,
                "draft",
                source_message_id,
                None,
                None,
                now,
                now,
            ),
        )
        todo_id = int(cur.lastrowid)
        if source_message_id is not None:
            conn.execute(
                """
                INSERT INTO todo_links (todo_id, session_id, link_type, message_id, retrieval_log_id, note, created_at)
                VALUES (?,?,?,?,?,?,?)
                """,
                (todo_id, session_id, "message", source_message_id, None, "from-answer", now),
            )
        _insert_phase_log(
            conn,
            todo_id=todo_id,
            session_id=session_id,
            from_status=None,
            to_status="draft",
            actor="system",
            reason="create-from-answer" if source_message_id is not None else "create",
        )
        row = conn.execute("SELECT * FROM todo_items WHERE id = ?", (todo_id,)).fetchone()

    _audit_event(
        "todo_created",
        {
            "session_id": session_id,
            "todo_id": todo_id,
            "status": "draft",
            "message_id": source_message_id,
        },
    )
    return _row_to_todo_item(row)


@router.post("/history/{session_id}/todos/preview", response_model=TodoPreviewResponse)
async def preview_todo_from_answer(
    session_id: str,
    payload: TodoPreviewRequest,
    settings=Depends(_get_settings),
) -> TodoPreviewResponse:
    """assistant回答からTODO草案を生成して返す。"""
    with _get_db(settings.history_db) as conn:
        _ensure_session_exists(conn, session_id)
        message_row = _get_session_message(conn, session_id, payload.message_id)
        if message_row["role"] != "assistant":
            raise HTTPException(status_code=400, detail="assistant回答のみTODO化できます")

    preview = await llm.generate_todo_draft_from_answer(
        answer_text=message_row["content"],
        model=payload.model,
    )
    _audit_event(
        "todo_preview_generated",
        {"session_id": session_id, "message_id": payload.message_id, "model": payload.model},
    )
    return TodoPreviewResponse(**preview)


@router.post("/history/{session_id}/todos/from-chat", response_model=TodoItem)
async def create_todo_from_chat(
    session_id: str,
    payload: TodoFromChatRequest,
    settings=Depends(_get_settings),
) -> TodoItem:
    """チャットメッセージ起点でTODOを作成し、根拠リンクを保存する。"""
    now = datetime.now().isoformat()
    with _get_db(settings.history_db) as conn:
        _ensure_session_exists(conn, session_id)
        msg = _get_session_message(conn, session_id, payload.message_id)
        if msg["role"] != "assistant":
            raise HTTPException(status_code=400, detail="assistant回答のみTODO化できます")

        title = (payload.title or "").strip() or msg["content"][:40].strip() or "TODO"
        cur = conn.execute(
            """
            INSERT INTO todo_items (
                session_id, title, description, acceptance_criteria, status,
                created_from_message_id, approved_by, approved_at, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (
                session_id,
                title,
                payload.description,
                payload.acceptance_criteria,
                "draft",
                payload.message_id,
                None,
                None,
                now,
                now,
            ),
        )
        todo_id = int(cur.lastrowid)

        conn.execute(
            """
            INSERT INTO todo_links (todo_id, session_id, link_type, message_id, retrieval_log_id, note, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (todo_id, session_id, "message", payload.message_id, None, "from-chat", now),
        )

        _insert_phase_log(
            conn,
            todo_id=todo_id,
            session_id=session_id,
            from_status=None,
            to_status="draft",
            actor="system",
            reason="from-answer",
        )
        row = conn.execute("SELECT * FROM todo_items WHERE id = ?", (todo_id,)).fetchone()

    _audit_event(
        "todo_from_chat_created",
        {"session_id": session_id, "todo_id": todo_id, "message_id": payload.message_id},
    )
    return _row_to_todo_item(row)


@router.patch("/history/{session_id}/todos/{todo_id}", response_model=TodoItem)
async def update_todo(
    session_id: str,
    todo_id: int,
    payload: TodoUpdateRequest,
    settings=Depends(_get_settings),
) -> TodoItem:
    """セッション単位TODOを更新する。"""
    if payload.title is None and payload.description is None and payload.status is None and payload.acceptance_criteria is None:
        raise HTTPException(status_code=400, detail="更新項目がありません")

    with _get_db(settings.history_db) as conn:
        _ensure_session_exists(conn, session_id)
        exists = conn.execute(
            "SELECT * FROM todo_items WHERE id = ? AND session_id = ?",
            (todo_id, session_id),
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="TODOが見つかりません")

        next_title = exists["title"]
        if payload.title is not None:
            next_title = payload.title.strip()
            if not next_title:
                raise HTTPException(status_code=400, detail="title は空にできません")

        next_description = exists["description"] if payload.description is None else payload.description
        next_acceptance = (
            exists["acceptance_criteria"] if payload.acceptance_criteria is None else payload.acceptance_criteria
        )

        next_status = exists["status"] if payload.status is None else payload.status
        current_status = exists["status"]
        if next_status == "done":
            raise HTTPException(status_code=400, detail="done は approve API でのみ遷移できます")
        if payload.status is not None and not _validate_transition(current_status, next_status):
            raise HTTPException(status_code=409, detail=f"不正な遷移です: {current_status} -> {next_status}")

        now = datetime.now().isoformat()
        conn.execute(
            """
            UPDATE todo_items
            SET title = ?, description = ?, acceptance_criteria = ?, status = ?, updated_at = ?
            WHERE id = ? AND session_id = ?
            """,
            (next_title, next_description, next_acceptance, next_status, now, todo_id, session_id),
        )

        if payload.status is not None and payload.status != current_status:
            _insert_phase_log(
                conn,
                todo_id=todo_id,
                session_id=session_id,
                from_status=current_status,
                to_status=payload.status,
                actor="user",
                reason="manual-update",
            )
            _audit_event(
                "todo_status_changed",
                {"session_id": session_id, "todo_id": todo_id, "from": current_status, "to": payload.status},
            )

        row = conn.execute(
            "SELECT * FROM todo_items WHERE id = ? AND session_id = ?",
            (todo_id, session_id),
        ).fetchone()

    return _row_to_todo_item(row)


@router.post("/history/{session_id}/todos/{todo_id}/approve", response_model=TodoItem)
async def approve_todo(
    session_id: str,
    todo_id: int,
    payload: TodoApproveRequest,
    settings=Depends(_get_settings),
) -> TodoItem:
    """レビュー承認してTODOを完了状態にする。"""
    approved_by = payload.approved_by.strip()
    if not approved_by:
        raise HTTPException(status_code=400, detail="approved_by は必須です")

    now = datetime.now().isoformat()
    with _get_db(settings.history_db) as conn:
        _ensure_session_exists(conn, session_id)
        exists = conn.execute(
            "SELECT * FROM todo_items WHERE id = ? AND session_id = ?",
            (todo_id, session_id),
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="TODOが見つかりません")
        if exists["status"] != "review_required":
            raise HTTPException(status_code=409, detail="review_required のTODOのみ承認できます")

        conn.execute(
            """
            UPDATE todo_items
            SET status = 'done', approved_by = ?, approved_at = ?, updated_at = ?
            WHERE id = ? AND session_id = ?
            """,
            (approved_by, now, now, todo_id, session_id),
        )
        _insert_phase_log(
            conn,
            todo_id=todo_id,
            session_id=session_id,
            from_status="review_required",
            to_status="done",
            actor=approved_by,
            reason="approve",
        )
        row = conn.execute(
            "SELECT * FROM todo_items WHERE id = ? AND session_id = ?",
            (todo_id, session_id),
        ).fetchone()

    _audit_event("todo_approved", {"session_id": session_id, "todo_id": todo_id, "approved_by": approved_by})
    return _row_to_todo_item(row)


@router.post("/history/{session_id}/todos/{todo_id}/draft", response_model=TodoItem)
async def generate_todo_design_draft(
    session_id: str,
    todo_id: int,
    payload: TodoDraftGenerateRequest,
    settings=Depends(_get_settings),
) -> TodoItem:
    """TODOを元に基本設計ドラフトを生成し、assistantメッセージとして保存する。"""
    with _get_db(settings.history_db) as conn:
        _ensure_session_exists(conn, session_id)
        todo_row = conn.execute(
            "SELECT * FROM todo_items WHERE id = ? AND session_id = ?",
            (todo_id, session_id),
        ).fetchone()
        if not todo_row:
            raise HTTPException(status_code=404, detail="TODOが見つかりません")

        linked_msg_rows = conn.execute(
            """
            SELECT m.id, m.role, m.content, m.created_at
            FROM todo_links l
            JOIN chat_messages m ON m.id = l.message_id
            WHERE l.todo_id = ? AND l.session_id = ? AND l.message_id IS NOT NULL
            ORDER BY l.id ASC
            """,
            (todo_id, session_id),
        ).fetchall()
        linked_retrieval_rows = conn.execute(
            """
            SELECT r.*
            FROM todo_links l
            JOIN chat_retrieval_logs r ON r.id = l.retrieval_log_id
            WHERE l.todo_id = ? AND l.session_id = ? AND l.retrieval_log_id IS NOT NULL
            ORDER BY l.id ASC
            """,
            (todo_id, session_id),
        ).fetchall()

    _audit_event("todo_draft_generation_started", {"session_id": session_id, "todo_id": todo_id, "model": payload.model})
    draft_text = await llm.generate_basic_design_draft(
        title=todo_row["title"],
        description=todo_row["description"],
        acceptance_criteria=todo_row["acceptance_criteria"] or "",
        related_messages=[f"- [{r['role']}] {r['content'][:400]}" for r in linked_msg_rows[:8]],
        retrieval_summaries=[
            f"- query={r['query']} / sources={','.join(json.loads(r['top_sources'] or '[]')[:3])}"
            for r in linked_retrieval_rows[:8]
        ],
        palace_path=settings.palace_dir,
        model=payload.model,
    )
    if not draft_text:
        raise HTTPException(status_code=500, detail="AIドラフト生成に失敗しました")

    now = datetime.now().isoformat()
    with _get_db(settings.history_db) as conn:
        cur = conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (session_id, "assistant", draft_text, now),
        )
        message_id = int(cur.lastrowid)

        conn.execute(
            "UPDATE todo_items SET ai_draft_message_id = ?, updated_at = ? WHERE id = ? AND session_id = ?",
            (message_id, now, todo_id, session_id),
        )
        conn.execute(
            """
            INSERT INTO todo_links (todo_id, session_id, link_type, message_id, retrieval_log_id, note, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (todo_id, session_id, "draft", message_id, None, "basic-design-draft", now),
        )
        row = conn.execute(
            "SELECT * FROM todo_items WHERE id = ? AND session_id = ?",
            (todo_id, session_id),
        ).fetchone()

    _audit_event(
        "todo_draft_generation_finished",
        {"session_id": session_id, "todo_id": todo_id, "message_id": message_id},
    )
    return _row_to_todo_item(row)


@router.get("/history/{session_id}/todos/{todo_id}", response_model=TodoDetailResponse)
async def get_todo_detail(
    session_id: str,
    todo_id: int,
    settings=Depends(_get_settings),
) -> TodoDetailResponse:
    """TODO詳細（リンク・フェーズログ含む）を返す。"""
    with _get_db(settings.history_db) as conn:
        _ensure_session_exists(conn, session_id)
        row = conn.execute(
            "SELECT * FROM todo_items WHERE id = ? AND session_id = ?",
            (todo_id, session_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="TODOが見つかりません")

        links = conn.execute(
            "SELECT * FROM todo_links WHERE todo_id = ? AND session_id = ? ORDER BY id ASC",
            (todo_id, session_id),
        ).fetchall()
        phase_logs = conn.execute(
            "SELECT * FROM todo_phase_logs WHERE todo_id = ? AND session_id = ? ORDER BY id ASC",
            (todo_id, session_id),
        ).fetchall()

    return TodoDetailResponse(
        item=_row_to_todo_item(row),
        links=[_row_to_todo_link(r) for r in links],
        phase_logs=[_row_to_phase_log(r) for r in phase_logs],
    )


@router.delete("/history/{session_id}/todos/{todo_id}")
async def delete_todo(session_id: str, todo_id: int, settings=Depends(_get_settings)) -> dict[str, Any]:
    """セッション単位TODOを削除する。"""
    with _get_db(settings.history_db) as conn:
        _ensure_session_exists(conn, session_id)
        exists = conn.execute(
            "SELECT id FROM todo_items WHERE id = ? AND session_id = ?",
            (todo_id, session_id),
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="TODOが見つかりません")

        conn.execute("DELETE FROM todo_links WHERE todo_id = ? AND session_id = ?", (todo_id, session_id))
        conn.execute("DELETE FROM todo_phase_logs WHERE todo_id = ? AND session_id = ?", (todo_id, session_id))
        conn.execute("DELETE FROM todo_items WHERE id = ? AND session_id = ?", (todo_id, session_id))

    _audit_event("todo_deleted", {"session_id": session_id, "todo_id": todo_id})
    return {"message": "削除しました", "todo_id": todo_id}


@router.delete("/history/{session_id}")
async def delete_session(session_id: str, settings=Depends(_get_settings)) -> dict[str, Any]:
    """指定セッションと関連データを削除する。"""
    with _get_db(settings.history_db) as conn:
        _ensure_session_exists(conn, session_id)

        todo_ids = conn.execute("SELECT id FROM todo_items WHERE session_id = ?", (session_id,)).fetchall()
        for row in todo_ids:
            conn.execute("DELETE FROM todo_links WHERE todo_id = ?", (row["id"],))
            conn.execute("DELETE FROM todo_phase_logs WHERE todo_id = ?", (row["id"],))

        conn.execute("DELETE FROM todo_items WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_retrieval_logs WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))

    _audit_event("session_deleted", {"session_id": session_id})
    return {"message": "削除しました", "session_id": session_id}
