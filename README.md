# Review-Aspect-Scoreboard

> 다차원 속성별 만족도 스코어보드

LLM(gpt-4o-mini) 기반 Aspect-Level 감성 분석으로 상품 리뷰에서  
**착용감 · 디자인 · 사이즈 · 내구성 · 가격** 5개 속성별 만족도 점수를 산출하고  
React 대시보드로 시각화하는 모듈입니다.

---

## 📌 주요 기능

- **다차원 속성별 만족도 스코어보드** — 5개 속성 점수 (0~10점) + 레이더 차트
- **속성별 리뷰 문장 드릴다운** — 속성 클릭 시 긍정/부정 문장 목록 표시
- **상품 검색 및 브랜드 필터** — 사이드바에서 상품 탐색

---

## 🗂️ 디렉토리 구조

```
Review-Aspect-Scoreboard/
│
├── backend/
│   ├── main.py                    # FastAPI 앱 진입점
│   ├── requirements.txt
│   ├── data/                      # 데이터 파일
│   │   ├── llm_scores_by_product.json
│   │   └── llm_sentences.json
│   └── src/
│       ├── models/
│       │   └── schemas.py         # Pydantic 데이터 모델
│       ├── scorer/
│       │   └── absa_scorer.py     # ABSAScorer 클래스
│       └── routers/
│           ├── products.py        # 상품 목록 / 점수 API
│           └── sentences.py       # 속성별 문장 API
│
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── package.json
    └── src/
        ├── App.jsx
        ├── index.css
        ├── api/
        │   └── scoreboardApi.js   # API 호출 함수 모음
        ├── components/
        │   ├── RadarChart.jsx      # 속성별 레이더 차트
        │   ├── ScoreCard.jsx       # 속성 점수 카드
        │   └── SentencePanel.jsx   # 문장 드릴다운 패널
        └── pages/
            └── ScoreboardPage.jsx  # 메인 페이지
```

---

## ⚙️ 설치 및 실행

### 백엔드 실행

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

→ `http://localhost:5173` 접속

---

## 🔌 API 엔드포인트

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/products` | 전체 상품 목록 + 속성 점수 |
| GET | `/api/products/brands` | 브랜드 목록 |
| GET | `/api/products/{asin}` | 특정 상품 점수 |
| GET | `/api/sentences/{asin}` | 특정 상품 문장 목록 |

**Query Parameters**

```
GET /api/products?brand=Nike&search=Air Max
GET /api/sentences/{asin}?category=comfort&sentiment=negative
```

---

## 📦 ABSAScorer 사용법

```python
from src.scorer.absa_scorer import ABSAScorer

scorer = ABSAScorer(
    model       = "gpt-4o-mini",
    batch_size  = 10,
    max_workers = 3,
    max_reviews = None,  # None = 전체 리뷰 분석
)

scorer.load_data("backend/data/shoes_sample.json")
scorer.run()
scorer.save(
    "backend/data/llm_scores_by_product.json",
    "backend/data/llm_sentences.json",
)

# 결과 DataFrame으로 사용
df_scores    = scorer.get_scores_df()
df_sentences = scorer.get_sentences_df()
```

---

## 📊 점수 계산 방식

```
속성별 만족도 점수 (10점 만점) = (긍정 수 / 전체 수) × 10
```

| 점수 구간 | 의미 |
|---|---|
| 🟢 7.0 ~ 10.0 | 긍정 우세 (우수) |
| 🟡 4.0 ~ 6.9  | 긍정·부정 혼재 (보통) |
| 🔴 0.0 ~ 3.9  | 부정 우세 (미흡) |
| ⚪ N/A        | 관련 리뷰 없음 |

---

## 🔗 관련 레포지토리

| 레포지토리 | 기능 |
|---|---|
| **Review-Aspect-Scoreboard** | 다차원 속성별 만족도 스코어보드 (현재) |
| Review-Sum-Map | 시맨틱 리뷰 요약 및 키워드 맵 |
| Review-Risk-Radar | 부정 리스크 감지 및 조기 경보 |
| Review-Consultant-AI | AI 이슈 진단 및 실행 처방전 |

---

## ⚠️ 주의사항

- API 키 및 `.env` 파일은 절대 커밋하지 마세요
- `backend/data/*.json` 파일은 용량이 크므로 `.gitignore` 추가 권장
- Rate Limit 오류 발생 시 `max_workers` 를 줄이세요 (5 → 3 → 1)
