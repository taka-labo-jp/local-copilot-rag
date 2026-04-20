"""チャットAPI — MemPalace 検索ツール付き Copilot SDK でストリーミング回答 + 会話履歴管理"""
import json
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.models.chat import ChatMessage, ChatRequest, ChatSession, RetrievalLog
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
        _columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(chat_retrieval_logs)").fetchall()
        }
        for col, sql_type in (("wing", "TEXT"), ("room", "TEXT"), ("content_type", "TEXT"), ("source_files_json", "TEXT")):
            if col not in _columns:
                conn.execute(f"ALTER TABLE chat_retrieval_logs ADD COLUMN {col} {sql_type}")


@router.post("/chat")
async def chat(req: ChatRequest, settings=Depends(_get_settings)) -> StreamingResponse:
    """チャット指示を受け取り、Copilot SDK 経由でストリーミング応答を返す。

    SDK が mempalace_search ツールを自律的に呼び出して仕様書情報を取得し、回答を生成する。
    応答は Server-Sent Events (SSE) 形式でストリーミングされる。
    """
    session_id = req.session_id or str(uuid.uuid4())
    search_filters: dict[str, str] = {}
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

    # セッションが新規の場合は作成
    with _get_db(settings.history_db) as conn:
        exists = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not exists:
            title = req.message[:40] + ("…" if len(req.message) > 40 else "")
            conn.execute(
                "INSERT INTO chat_sessions (id, title, created_at) VALUES (?,?,?)",
                (session_id, title, datetime.now().isoformat()),
            )
        # ユーザーメッセージを保存
        conn.execute(
            "INSERT INTO chat_messages (session_id, role, content, created_at) VALUES (?,?,?,?)",
            (session_id, "user", req.message, datetime.now().isoformat()),
        )

    async def event_stream():
        # セッションIDをまず送信
        yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id})}\n\n"
        # 思考中ステータス
        yield f"data: {json.dumps({'type': 'status', 'status': 'thinking'})}\n\n"

        collected = []
        retrieval_logs: list[dict[str, Any]] = []
        pending_status_events: list[dict] = []

        def _on_search(item: dict[str, Any]) -> None:
            item["call_index"] = len(retrieval_logs) + 1
            retrieval_logs.append(item)
            pending_status_events.append(
                {"type": "status", "status": "searching", "query": item.get("query", "")}
            )

        try:
            async for chunk in llm.generate_stream(
                prompt=req.message,
                palace_path=settings.palace_dir,
                model=req.model,
                reasoning_mode=req.reasoning_mode,
                on_search=_on_search,
                search_filters=search_filters or None,
            ):
                # 検索イベントが溜まっていれば先に送信
                while pending_status_events:
                    yield f"data: {json.dumps(pending_status_events.pop(0))}\n\n"
                collected.append(chunk)
                yield f"data: {json.dumps({'type': 'delta', 'content': chunk})}\n\n"
        except Exception as e:
            logger.exception("生成エラー")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
            return

        # アシスタントの回答を履歴に保存
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
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history", response_model=list[ChatSession])
async def list_sessions(settings=Depends(_get_settings)) -> list[ChatSession]:
    """会話セッション一覧を返す（最新順）。"""
    with _get_db(settings.history_db) as conn:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.created_at,
                   COUNT(m.id) AS message_count
            FROM chat_sessions s
            LEFT JOIN chat_messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY s.created_at DESC
            """
        ).fetchall()
    return [
        ChatSession(
            id=r["id"],
            title=r["title"],
            created_at=datetime.fromisoformat(r["created_at"]),
            message_count=r["message_count"],
        )
        for r in rows
    ]


@router.get("/history/{session_id}", response_model=list[ChatMessage])
async def get_session_messages(
    session_id: str, settings=Depends(_get_settings)
) -> list[ChatMessage]:
    """指定セッションのメッセージ一覧を返す。"""
    with _get_db(settings.history_db) as conn:
        rows = conn.execute(
            "SELECT id, session_id, role, content, created_at "
            "FROM chat_messages WHERE session_id = ? ORDER BY id ASC",
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
async def get_session_retrieval_logs(
    session_id: str, settings=Depends(_get_settings)
) -> list[RetrievalLog]:
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


@router.delete("/history/{session_id}")
async def delete_session(session_id: str, settings=Depends(_get_settings)) -> dict:
    """指定セッションとそのメッセージを削除する。"""
    with _get_db(settings.history_db) as conn:
        exists = conn.execute(
            "SELECT id FROM chat_sessions WHERE id = ?", (session_id,)
        ).fetchone()
        if not exists:
            raise HTTPException(status_code=404, detail="セッションが見つかりません")
        conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    return {"message": "削除しました", "session_id": session_id}
