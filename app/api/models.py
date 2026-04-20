"""モデル一覧API — GitHub Copilot SDK から利用可能モデルを動的取得する"""
from fastapi import APIRouter, Query

from app.services import llm

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[dict])
async def get_models(premium: bool | None = Query(default=None)) -> list[dict]:
    """Copilot SDK で利用可能なモデル一覧を返す。

    Args:
        premium: None=すべて返す（フィルタなし）,
                 True=プレミアムリクエスト消費ありのモデルのみ（cost_multiplier > 0）,
                 False=消費量が0のモデルのみ（プレミアムリクエスト不要）
    """
    return await llm.list_models(premium=premium)
