"""ドキュメントアップロードAPI — ファイルを受け取り markitdown で変換して Chroma に登録"""
import json
import logging
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.models.document import (
    DocumentInfo,
    DocumentMoveProjectRequest,
    DocumentUploadResponse,
    ProjectCreateRequest,
    ProjectInfo,
)
from app.services import converter, llm, memory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["documents"])

# 許可する拡張子（markitdown が対応する形式）
ALLOWED_EXTENSIONS = {
    ".docx", ".xlsx", ".pptx",
    ".doc", ".xls", ".ppt",
    ".pdf", ".html", ".htm",
    ".md", ".txt", ".csv",
    ".json", ".xml", ".epub", ".zip",
    # 画像ファイル（AI vision 解析）
    *converter.IMAGE_EXTENSIONS,
    # drawio / dia 図形ファイル（XML チャンク）
    *converter.DRAWIO_EXTENSIONS,
}


def _get_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def init_db(db_path: str) -> None:
    """ドキュメントメタデータテーブルを初期化する。"""
    with _get_db(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                filename    TEXT NOT NULL,
                wing        TEXT NOT NULL,
                room        TEXT NOT NULL,
                drawer_count INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL
            )
            """
        )
        if not _column_exists(conn, "documents", "project"):
            conn.execute("ALTER TABLE documents ADD COLUMN project TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL UNIQUE,
                created_at  TEXT NOT NULL
            )
            """
        )


# FastAPI の依存関数用にアプリ設定を受け取る
def _get_settings():
    from app.main import settings
    return settings


async def _register_document(
    chunks: list[dict[str, Any]],
    source_filename: str,
    wing: str,
    room_name: str,
    project: str,
    settings,
) -> DocumentUploadResponse:
    """変換済みMarkdownを知識ベースに登録する共通処理。"""
    filename = source_filename or "file.md"

    with _get_db(settings.history_db) as conn:
        rows = conn.execute(
            "SELECT id FROM documents WHERE filename = ?",
            (filename,),
        ).fetchall()

    overwritten_count = len(rows)
    deleted_chunks = 0

    if overwritten_count > 0:
        converter.delete_extracted_images(settings.extracted_image_dir, filename)
        deleted_chunks = memory.delete_document_chunks(
            palace_path=settings.palace_dir,
            source_filename=filename,
        )
        with _get_db(settings.history_db) as conn:
            conn.execute("DELETE FROM documents WHERE filename = ?", (filename,))

    try:
        drawer_count = await memory.add_document(
            source_filename=filename,
            palace_path=settings.palace_dir,
            wing=wing,
            room=room_name,
            chunks=chunks,
        )
    except Exception as e:
        logger.exception("知識ベース登録エラー: %s", filename)
        raise HTTPException(status_code=500, detail=f"知識ベース登録エラー: {e}") from e

    with _get_db(settings.history_db) as conn:
        conn.execute(
            "INSERT INTO documents (filename, wing, room, project, drawer_count, created_at) VALUES (?,?,?,?,?,?)",
            (filename, wing, room_name, project.strip(), drawer_count, datetime.now().isoformat()),
        )

    if overwritten_count > 0:
        message = (
            f"{filename} を上書きしました。"
            f" 新規チャンク: {drawer_count}件 / 削除チャンク: {deleted_chunks}件"
        )
    else:
        message = f"{drawer_count} 件のチャンクをChromaに登録しました"

    type_counts = Counter(
        str((item.get("metadata") or {}).get("content_type", "text"))
        for item in chunks
    )

    return DocumentUploadResponse(
        filename=filename,
        drawer_count=drawer_count,
        wing=wing,
        room=room_name,
        project=project.strip(),
        message=message,
        overwritten_count=overwritten_count,
        deleted_chunks=deleted_chunks,
        text_chunk_count=type_counts.get("text", 0),
        table_chunk_count=type_counts.get("table", 0),
        image_chunk_count=type_counts.get("image", 0),
        visual_chunk_count=type_counts.get("visual_page", 0),
        diagram_chunk_count=type_counts.get("diagram", 0),
    )


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    wing: str = Form(default="specifications"),
    room: str = Form(default=""),
    project: str = Form(default=""),
    settings=Depends(_get_settings),
) -> DocumentUploadResponse:
    """仕様書ファイルをアップロードし、ローカル知識ベースに登録する。"""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"未対応の形式です: {suffix}。対応形式: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="空のファイルです")

    # 形式に応じてチャンク化する。
    try:
        if suffix in converter.IMAGE_EXTENSIONS:
            # 画像は AI vision で解析してチャンクを生成する。
            description = await llm.analyze_image_with_ai(
                image_bytes=file_bytes,
                filename=file.filename or "image.png",
                model=settings.copilot_model,
            )
            chunks = [
                {
                    "text": f"File: {file.filename}\n{description}",
                    "metadata": {
                        "content_type": "image",
                        "extractor": "copilot-vision",
                    },
                }
            ]
        elif suffix in converter.DRAWIO_EXTENSIONS:
            # drawio は XML チャンクとして登録する。
            chunks = converter.convert_drawio_to_chunks(
                file_bytes=file_bytes,
                source_filename=file.filename or "diagram.drawio",
            )
        else:
            chunks = converter.convert_to_chunks(
                file_bytes=file_bytes,
                filename=file.filename or "file.md",
                image_root_dir=settings.extracted_image_dir,
                excel_rows_per_chunk=settings.excel_table_rows_per_chunk,
                ocr_lang=settings.ocr_lang,
                enable_visual_page_ocr=settings.enable_visual_page_ocr,
                max_visual_ocr_pages=settings.max_visual_ocr_pages,
                soffice_bin=settings.soffice_bin,
            )
    except Exception as e:
        logger.exception("変換エラー: %s", file.filename)
        raise HTTPException(status_code=500, detail=f"ファイル変換エラー: {e}") from e

    if not chunks:
        raise HTTPException(status_code=400, detail="有効なテキストを抽出できませんでした")

    room_name = room.strip() or Path(file.filename or "file").stem
    return await _register_document(
        chunks=chunks,
        source_filename=file.filename or "file.md",
        wing=wing,
        room_name=room_name,
        project=project,
        settings=settings,
    )


@router.post("/bulk-upload")
async def bulk_upload_from_folder(
    project: str = Form(""),
    settings=Depends(_get_settings),
) -> StreamingResponse:
    """サーバー側フォルダ内のファイルを再帰的に一括取り込みし、進捗を SSE で送信する。"""
    bulk_dir = Path(settings.bulk_upload_dir)
    bulk_dir.mkdir(parents=True, exist_ok=True)

    files = sorted([p for p in bulk_dir.rglob("*") if p.is_file()])

    async def event_stream():
        uploaded = 0
        failed = 0
        total = len(files)

        yield f"data: {json.dumps({'type': 'start', 'total': total})}\n\n"

        for idx, path in enumerate(files):
            suffix = path.suffix.lower()
            if suffix not in ALLOWED_EXTENSIONS:
                failed += 1
                yield f"data: {json.dumps({'type': 'file_result', 'filename': path.name, 'status': 'failed', 'reason': f'未対応の形式です: {suffix}', 'index': idx + 1, 'total': total})}\n\n"
                continue

            try:
                file_bytes = path.read_bytes()
                if len(file_bytes) == 0:
                    raise ValueError("空のファイルです")

                # project パラメータを優先し、未指定ならフォルダ構造を無視して空文字（未分類）
                file_project = project

                if suffix in converter.IMAGE_EXTENSIONS:
                    description = await llm.analyze_image_with_ai(
                        image_bytes=file_bytes,
                        filename=path.name,
                        model=settings.copilot_model,
                    )
                    chunks = [
                        {
                            "text": f"File: {path.name}\n{description}",
                            "metadata": {
                                "content_type": "image",
                                "extractor": "copilot-vision",
                            },
                        }
                    ]
                elif suffix in converter.DRAWIO_EXTENSIONS:
                    chunks = converter.convert_drawio_to_chunks(
                        file_bytes=file_bytes,
                        source_filename=path.name,
                    )
                else:
                    chunks = converter.convert_to_chunks(
                        file_bytes=file_bytes,
                        filename=path.name,
                        image_root_dir=settings.extracted_image_dir,
                        excel_rows_per_chunk=settings.excel_table_rows_per_chunk,
                        ocr_lang=settings.ocr_lang,
                        enable_visual_page_ocr=settings.enable_visual_page_ocr,
                        max_visual_ocr_pages=settings.max_visual_ocr_pages,
                        soffice_bin=settings.soffice_bin,
                    )
                if not chunks:
                    raise ValueError("有効なテキストを抽出できませんでした")

                resp = await _register_document(
                    chunks=chunks,
                    source_filename=path.name,
                    wing="specifications",
                    room_name=path.stem,
                    project=file_project,
                    settings=settings,
                )
                uploaded += 1
                yield f"data: {json.dumps({'type': 'file_result', 'filename': path.name, 'status': 'uploaded', 'drawer_count': resp.drawer_count, 'overwritten_count': resp.overwritten_count, 'index': idx + 1, 'total': total})}\n\n"
            except Exception as e:
                failed += 1
                yield f"data: {json.dumps({'type': 'file_result', 'filename': str(path.relative_to(bulk_dir)), 'status': 'failed', 'reason': str(e), 'index': idx + 1, 'total': total})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'uploaded': uploaded, 'failed': failed, 'total': total})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/projects", response_model=list[ProjectInfo])
async def list_projects(settings=Depends(_get_settings)) -> list[ProjectInfo]:
    """登録済みプロジェクト一覧を返す。"""
    with _get_db(settings.history_db) as conn:
        rows = conn.execute(
            "SELECT id, name, created_at FROM projects ORDER BY name ASC"
        ).fetchall()
    return [
        ProjectInfo(id=r["id"], name=r["name"], created_at=datetime.fromisoformat(r["created_at"]))
        for r in rows
    ]


@router.post("/projects", response_model=ProjectInfo)
async def create_project(payload: ProjectCreateRequest, settings=Depends(_get_settings)) -> ProjectInfo:
    """新規プロジェクトを作成する。"""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="プロジェクト名は必須です")
    created_at = datetime.now().isoformat()
    try:
        with _get_db(settings.history_db) as conn:
            cur = conn.execute(
                "INSERT INTO projects (name, created_at) VALUES (?, ?)",
                (name, created_at),
            )
        return ProjectInfo(id=cur.lastrowid, name=name, created_at=datetime.fromisoformat(created_at))
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=409, detail="同名プロジェクトが既に存在します") from e


@router.delete("/projects/{project_id}")
async def delete_project(project_id: int, settings=Depends(_get_settings)) -> dict:
    """プロジェクトを削除し、配下仕様書を未分類に移す。"""
    with _get_db(settings.history_db) as conn:
        row = conn.execute("SELECT name FROM projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="プロジェクトが見つかりません")
        name = row["name"]
        moved = conn.execute(
            "UPDATE documents SET project = '' WHERE project = ?",
            (name,),
        ).rowcount
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    return {"message": "プロジェクトを削除しました", "moved_documents": moved}


@router.patch("/{doc_id}/project")
async def move_document_project(
    doc_id: int,
    payload: DocumentMoveProjectRequest,
    settings=Depends(_get_settings),
) -> dict:
    """仕様書を別プロジェクトに移動する。"""
    target = payload.project.strip()
    with _get_db(settings.history_db) as conn:
        row = conn.execute("SELECT id FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="ドキュメントが見つかりません")
        if target:
            exists = conn.execute("SELECT id FROM projects WHERE name = ?", (target,)).fetchone()
            if exists is None:
                raise HTTPException(status_code=404, detail="移動先プロジェクトが見つかりません")
        conn.execute("UPDATE documents SET project = ? WHERE id = ?", (target, doc_id))
    return {"message": "移動しました", "project": target}


@router.delete("/{doc_id}")
async def delete_document(doc_id: int, settings=Depends(_get_settings)) -> dict:
    """指定ドキュメントのメタデータとチャンクを削除する。"""
    with _get_db(settings.history_db) as conn:
        row = conn.execute(
            "SELECT id, filename, wing, room FROM documents WHERE id=?",
            (doc_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="ドキュメントが見つかりません")
        deleted_chunks = memory.delete_document_chunks(
            palace_path=settings.palace_dir,
            source_filename=row["filename"],
            wing=row["wing"],
            room=row["room"],
        )
        converter.delete_extracted_images(settings.extracted_image_dir, row["filename"])
        conn.execute("DELETE FROM documents WHERE id=?", (doc_id,))
    logger.info("Document deleted: id=%d chunks=%d", doc_id, deleted_chunks)
    return {"message": "削除しました", "deleted_chunks": deleted_chunks}


@router.get("", response_model=list[DocumentInfo])
async def list_documents(settings=Depends(_get_settings)) -> list[DocumentInfo]:
    """登録済みドキュメント一覧を返す。"""
    with _get_db(settings.history_db) as conn:
        rows = conn.execute(
            "SELECT id, filename, wing, room, project, drawer_count, created_at FROM documents ORDER BY id DESC"
        ).fetchall()

    return [
        DocumentInfo(
            id=r["id"],
            filename=r["filename"],
            wing=r["wing"],
            room=r["room"],
            project=r["project"] or "",
            drawer_count=r["drawer_count"],
            created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in rows
    ]
