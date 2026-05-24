"""속성별 문장 API"""

import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from src.models.schemas import SentenceItem

router = APIRouter()

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "llm_sentences.json"

_cache: list = []

def load_sentences() -> list:
    global _cache
    if _cache:
        return _cache
    if not DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="sentences 파일이 없습니다.")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        _cache = json.load(f)
    return _cache


@router.get("/{asin}", response_model=list[SentenceItem])
def get_sentences(
    asin:      str,
    category:  Optional[str] = Query(None, description="속성 필터 (comfort/design/size/durability/price)"),
    sentiment: Optional[str] = Query(None, description="감성 필터 (positive/negative)"),
):
    """
    특정 상품의 속성별 문장 반환

    - category: comfort / design / size / durability / price
    - sentiment: positive / negative
    """
    data = load_sentences()

    results = [s for s in data if str(s.get("asin", "")) == str(asin)]

    if not results:
        raise HTTPException(status_code=404, detail=f"상품 {asin}의 문장 데이터가 없습니다.")

    if category:
        results = [s for s in results if s.get("category") == category]
    if sentiment:
        results = [s for s in results if s.get("sentiment") == sentiment]

    return [
        SentenceItem(
            asin          = str(s.get("asin", "")),
            brand         = s.get("brand", ""),
            product_title = s.get("product_title", ""),
            evidence      = s.get("evidence", s.get("sentence_en", "")),
            full_review   = s.get("full_review", ""),
            category      = s.get("category", ""),
            sentiment     = s.get("sentiment", ""),
            score         = float(s.get("score", 0)),
        )
        for s in results
    ]
