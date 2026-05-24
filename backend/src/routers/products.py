"""상품 목록 / 상품별 점수 API"""

import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from src.models.schemas import ProductScore, CategoryScore

router = APIRouter()

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "llm_scores_by_product.json"

_cache: dict = {}

def load_scores() -> dict:
    global _cache
    if _cache:
        return _cache
    if not DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="scores 파일이 없습니다.")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        _cache = json.load(f)
    return _cache

CATEGORIES = ["comfort", "design", "size", "durability", "price"]


@router.get("/", response_model=list[ProductScore])
def get_products(
    brand: Optional[str] = Query(None, description="브랜드 필터"),
    search: Optional[str] = Query(None, description="상품명 검색"),
):
    """전체 상품 목록 + 속성 점수 반환"""
    raw = load_scores()
    results = []

    for asin, info in raw.items():
        if brand and info.get("brand", "") != brand:
            continue
        if search and search.lower() not in info.get("product_title", "").lower():
            continue

        scores = {}
        for cat in CATEGORIES:
            s = info.get("scores", {}).get(cat, {})
            scores[cat] = CategoryScore(
                score     = s.get("score"),
                count     = s.get("count", 0),
                pos_count = s.get("pos_count", s.get("positive", 0)),
                neg_count = s.get("neg_count", s.get("negative", 0)),
            )

        results.append(ProductScore(
            asin          = asin,
            brand         = info.get("brand", "Unknown"),
            product_title = info.get("product_title", ""),
            avg_rating    = info.get("avg_rating"),
            review_count  = info.get("review_count", 0),
            scores        = scores,
        ))

    return results


@router.get("/brands", response_model=list[str])
def get_brands():
    """브랜드 목록 반환"""
    raw = load_scores()
    brands = sorted(set(info.get("brand", "") for info in raw.values()))
    return [b for b in brands if b]


@router.get("/{asin}", response_model=ProductScore)
def get_product(asin: str):
    """특정 상품 점수 반환"""
    raw = load_scores()
    if asin not in raw:
        raise HTTPException(status_code=404, detail=f"상품 {asin}을 찾을 수 없습니다.")

    info = raw[asin]
    scores = {}
    for cat in CATEGORIES:
        s = info.get("scores", {}).get(cat, {})
        scores[cat] = CategoryScore(
            score     = s.get("score"),
            count     = s.get("count", 0),
            pos_count = s.get("pos_count", s.get("positive", 0)),
            neg_count = s.get("neg_count", s.get("negative", 0)),
        )

    return ProductScore(
        asin          = asin,
        brand         = info.get("brand", "Unknown"),
        product_title = info.get("product_title", ""),
        avg_rating    = info.get("avg_rating"),
        review_count  = info.get("review_count", 0),
        scores        = scores,
    )
