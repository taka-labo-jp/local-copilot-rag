"""モデル一覧API — GitHub Copilot SDK から利用可能モデルを動的取得する"""
from fastapi import APIRouter

from app.services import llm

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[dict])
async def get_models() -> list[dict]:
    """Copilot SDK で利用可能なモデル一覧を返す。"""
    return await llm.list_models()
