"""ドキュメント関連の Pydantic モデル定義"""
from datetime import datetime

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    filename: str
    drawer_count: int
    wing: str
    room: str
    project: str = ""
    message: str
    overwritten_count: int = 0
    deleted_chunks: int = 0
    text_chunk_count: int = 0
    table_chunk_count: int = 0
    image_chunk_count: int = 0
    visual_chunk_count: int = 0


class DocumentInfo(BaseModel):
    id: int
    filename: str
    wing: str
    room: str
    project: str = ""
    drawer_count: int
    created_at: datetime


class ProjectInfo(BaseModel):
    id: int
    name: str
    created_at: datetime


class ProjectCreateRequest(BaseModel):
    name: str


class DocumentMoveProjectRequest(BaseModel):
    project: str = ""
