# FLOW.md — Review-Aspect-Scoreboard 파이프라인 흐름

---

## 전체 흐름

```
shoes_sample.json
      │
      ▼
┌─────────────────────────────┐
│     ABSAScorer              │  absa_scorer.py
│                             │
│  1. load_data()             │  데이터 로드 + 상품별 그룹화
│  2. run()                   │  LLM 분석 + 누락 재분석
│  3. save()                  │  JSON 저장
└─────────────────────────────┘
      │
      ├──▶ llm_scores_by_product.json   (상품별 속성 점수)
      └──▶ llm_sentences.json           (문장별 분류 결과)
                  │
                  ▼
┌─────────────────────────────┐
│     FastAPI 백엔드           │  main.py
│                             │
│  GET /api/products          │  상품 목록 + 점수
│  GET /api/sentences/{asin}  │  속성별 문장
└─────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────┐
│     React 프론트엔드         │  ScoreboardPage.jsx
│                             │
│  사이드바 상품 선택           │
│  레이더 차트 + 점수 카드      │
│  속성 클릭 → 문장 드릴다운    │
└─────────────────────────────┘
```

---

## 1단계 — ABSAScorer 분석 파이프라인

### load_data()

```
shoes_sample.json 로드
      │
      ▼
parent_asin 기준 상품별 그룹화
      │
      ├─ product_meta    {asin: {brand, product_title, avg_rating, review_count}}
      └─ product_reviews {asin: [{rating, text}, ...]}
           └─ helpful_vote 높은 순 정렬 (max_reviews 설정 시 상위 N개만 사용)
```

### run() → _run_analysis()

```
미완료 상품 목록 추출 (체크포인트 기반)
      │
      ▼
ThreadPoolExecutor (max_workers=3) — 상품 단위 병렬 처리
      │
      └─ _process_product(asin)
              │
              ▼
         리뷰를 BATCH_SIZE(10개)씩 배치로 묶음
              │
              ▼
         ThreadPoolExecutor — 배치 단위 병렬 API 호출
              │
              └─ _call_openai(batch)
                      │
                      ▼
                 OpenAI gpt-4o-mini API
                 - system prompt : 분석 지침 (5개 속성 정의)
                 - user prompt   : 리뷰 10개 + JSON 형식 지정
                 - response_format: json_object
                 - temperature   : 0 (일관된 결과)
                 - max_tokens    : 2000
                      │
                      ▼
                 응답 파싱
                 {
                   "reviews": [
                     {
                       "review_id": 1,
                       "aspects": [
                         {"aspect": "comfort",  "sentiment": "positive", "evidence": "..."},
                         {"aspect": "size",     "sentiment": "negative", "evidence": "..."}
                       ]
                     }
                   ]
                 }
                      │
                      ▼
                 타입 검증 (isinstance 체크)
                 → rev_result, aspect_item 이 dict인지 확인
                 → 아니면 스킵
                      │
                      ▼
                 카테고리별 점수 누적
                 positive → +1.0
                 negative → -1.0
                 중립     → API 단계에서 이미 제외
```

### run() → _reanalyze_missing()

```
샘플 전체 asin  vs  저장된 scores asin 비교
      │
      ├─ absent_asins : JSON에 아예 없는 상품
      └─ none_asins   : 점수가 전부 None인 상품
              │
              ▼
      누락 상품만 _process_product() 재실행
              │
              ▼
      기존 scores, sentences에 병합
```

### 점수 집계 — _aggregate()

```
카테고리별 [+1.0, +1.0, -1.0, +1.0, ...] 점수 리스트
      │
      ▼
평균 계산 → [-1, +1] 범위
      │
      ▼
10점 척도 변환: (avg + 1) / 2 × 10
      │
      ▼
{
  "score":     7.3,   ← 10점 만점
  "count":     42,    ← 분석된 문장 수
  "pos_count": 31,    ← 긍정 문장 수
  "neg_count": 11     ← 부정 문장 수
}
```

### 병렬 처리 구조

```
상품 A ─┐
상품 B ─┤ ThreadPoolExecutor (max_workers=3)  — 상품 단위
상품 C ─┘
   │
   └─ 각 상품 내부
         배치1 ─┐
         배치2 ─┤ ThreadPoolExecutor (max_workers=3)  — 배치 단위
         배치3 ─┘
```

### Rate Limit 처리

```
API 호출
   │
   ├─ 성공 → 결과 반환
   └─ 실패
        ├─ 429 Rate Limit
        │     └─ RETRY_SLEEP × (시도 횟수) 초 대기 → 최대 3번 재시도
        └─ 그 외 오류 → 빈 리스트 반환 (해당 배치 스킵)
```

---

## 2단계 — FastAPI 백엔드

```
uvicorn main:app --reload --port 8000
      │
      ├─ GET /api/products
      │       └─ llm_scores_by_product.json 읽기
      │           → brand / search 쿼리 파라미터 필터링
      │           → ProductScore 리스트 반환
      │
      ├─ GET /api/products/brands
      │       └─ 브랜드 목록 반환
      │
      ├─ GET /api/products/{asin}
      │       └─ 특정 상품 점수 반환
      │
      └─ GET /api/sentences/{asin}
              └─ llm_sentences.json 읽기 (메모리 캐시)
                  → category / sentiment 쿼리 파라미터 필터링
                  → SentenceItem 리스트 반환
```

---

## 3단계 — React 프론트엔드

```
ScoreboardPage 마운트
      │
      ├─ fetchBrands()     → GET /api/products/brands
      └─ fetchProducts()   → GET /api/products

사용자가 상품 클릭
      │
      └─ selectedProduct 상태 업데이트
              │
              ├─ RadarChart    렌더링 (scores 데이터)
              └─ ScoreCard × 5 렌더링 (속성별 점수)

사용자가 속성 카드 클릭
      │
      └─ selectedCat 상태 업데이트
              │
              └─ SentencePanel
                      │
                      └─ fetchSentences(asin, { category })
                              → GET /api/sentences/{asin}?category=comfort
                              │
                              ├─ 긍정 탭: sentiment === "positive" 필터
                              └─ 부정 탭: sentiment === "negative" 필터
```

---

## 출력 파일 구조

### llm_scores_by_product.json

```json
{
  "B078GSXGWZ": {
    "brand":         "Skechers",
    "product_title": "Skechers Women's Go Joy Walking Shoe",
    "avg_rating":    4.21,
    "review_count":  396,
    "scores": {
      "comfort":    {"score": 8.3, "count": 142, "pos_count": 125, "neg_count": 17},
      "design":     {"score": 7.9, "count":  88, "pos_count":  76, "neg_count": 12},
      "size":       {"score": 6.1, "count": 103, "pos_count":  62, "neg_count": 41},
      "durability": {"score": 5.8, "count":  64, "pos_count":  38, "neg_count": 26},
      "price":      {"score": 7.5, "count":  71, "pos_count":  57, "neg_count": 14}
    }
  }
}
```

### llm_sentences.json

```json
[
  {
    "asin":          "B078GSXGWZ",
    "brand":         "Skechers",
    "product_title": "Skechers Women's Go Joy Walking Shoe",
    "evidence":      "very comfortable to wear all day",
    "full_review":   "I wear these to work every day...",
    "category":      "comfort",
    "sentiment":     "positive",
    "score":         1.0
  }
]
```

---

## 한계점

| 항목 | 내용 |
|---|---|
| 감성 이진 분류 | positive / negative만 있고 강도 차이 없음 (긍정 0.9도, 긍정 0.1도 모두 +1.0) |
| 속성 분류 기준 | LLM 프롬프트 의존, 모델마다 결과 미세하게 다를 수 있음 |
| 다국어 리뷰 | 스페인어 등 비영어 리뷰가 포함될 수 있음 (후처리로 제거 가능) |
| 비용 | 전체 분석 시 약 $1~2 발생 (gpt-4o-mini 기준) |
| 속도 | 네트워크 요청 기반으로 로컬 GPU와 무관 |
