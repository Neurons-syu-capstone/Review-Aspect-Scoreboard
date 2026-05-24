"""Pydantic 데이터 모델"""

from typing import Optional
from pydantic import BaseModel


class CategoryScore(BaseModel):
    score:     Optional[float]
    count:     int
    pos_count: int
    neg_count: int


class ProductScore(BaseModel):
    asin:          str
    brand:         str
    product_title: str
    avg_rating:    Optional[float]
    review_count:  int
    scores: dict[str, CategoryScore]


class SentenceItem(BaseModel):
    asin:          str
    brand:         str
    product_title: str
    evidence:      str
    full_review:   Optional[str]
    category:      str
    sentiment:     str  # "positive" | "negative"
    score:         float
