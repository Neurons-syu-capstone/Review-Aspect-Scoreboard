# Review-Aspect-Scoreboard 코드 리뷰 및 수정 내역

> 작성일: 2026-05-24  
> 목적: Review-Risk-Radar 통합 전 코드 품질 검토 및 버그 수정

---

## 수정 파일 목록

| 파일 | 수정 유형 |
|---|---|
| `frontend/src/pages/ScoreboardPage.jsx` | 버그 수정 3건 |
| `frontend/src/api/scoreboardApi.js` | 구조 개선 |
| `frontend/vite.config.js` | CORS 이슈 수정 |
| `backend/src/routers/products.py` | 성능 개선 |

---

## 수정 내역

### 1. 브랜드/검색어 변경 시 `selectedProduct` 초기화 누락

**파일:** `frontend/src/pages/ScoreboardPage.jsx`

**문제:** 브랜드 필터나 검색어를 변경하면 상품 목록이 새로 로드되지만, 이전에 선택된 상품(`selectedProduct`)이 초기화되지 않아 목록에 없는 상품이 오른쪽 메인 영역에 계속 표시됨.

**수정:**
```jsx
// Before
useEffect(() => {
  setLoading(true);
  fetchProducts({ ... })

// After
useEffect(() => {
  setSelectedProduct(null);  // 추가
  setSelectedCat(null);      // 추가
  setLoading(true);
  fetchProducts({ ... })
```

---

### 2. 무의미한 삼항 연산자

**파일:** `frontend/src/pages/ScoreboardPage.jsx`

**문제:** 브랜드 배지의 텍스트 색상을 조건으로 분기했지만 양쪽 값이 모두 `"#fff"`로 동일해 조건문이 완전히 무의미함.

**수정:**
```jsx
// Before
color: p.brand === "adidas" || p.brand === "ASICS" ? "#fff" : "#fff",

// After
color: "#fff",
```

---

### 3. `import` 문이 파일 중간에 위치

**파일:** `frontend/src/pages/ScoreboardPage.jsx`

**문제:** `InfoBanner` 컴포넌트 함수 선언 다음(70번째 줄)에 `import` 문이 있어, 해당 컴포넌트 내부에서 사용하는 `useState`가 import보다 먼저 참조되는 구조. ES Module 호이스팅으로 런타임에서는 동작하지만 ESLint 오류 발생 및 가독성 저하.

**수정:** 모든 `import` 문을 파일 최상단으로 이동.

```jsx
// Before (파일 구조)
function InfoBanner() { ... }   // line 1 — useState 사용
...
import { useState, useEffect } from "react";  // line 70 — import가 뒤에
import { fetchProducts, fetchBrands } from "../api/scoreboardApi";
...

// After (파일 구조)
import { useState, useEffect } from "react";  // line 1 — 최상단으로 이동
import { fetchProducts, fetchBrands } from "../api/scoreboardApi";
...
function InfoBanner() { ... }
```

---

### 4. `products.py` 매 요청마다 파일 읽기

**파일:** `backend/src/routers/products.py`

**문제:** `sentences.py`는 글로벌 `_cache` 변수로 메모리 캐싱을 하지만, `products.py`의 `load_scores()`는 매 API 요청마다 JSON 파일을 디스크에서 읽는 불일치 존재.

**수정:** `sentences.py`와 동일한 패턴으로 캐싱 적용.

```python
# Before
def load_scores() -> dict:
    if not DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="scores 파일이 없습니다.")
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# After
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
```

---

### 5. `InfoBanner` 레이아웃 높이 계산 오류

**파일:** `frontend/src/pages/ScoreboardPage.jsx`

**문제:** 사이드바 + 메인 영역의 높이가 `calc(100vh - 64px)` (헤더 64px만 빼는 고정값)으로 설정되어, InfoBanner를 펼치면 그 높이만큼 레이아웃이 밀려나 사이드바 스크롤이 깨짐.

**수정:** 최상위 컨테이너를 `flex-column`으로 변경하고, 사이드바+메인 영역을 `flex: 1`로 설정해 헤더와 InfoBanner가 차지하는 높이를 자동으로 제외.

```jsx
// Before
<div style={{ minHeight:"100vh", background:"#f8fafc", ... }}>
  ...
  <div style={{ display:"flex", height:"calc(100vh - 64px)" }}>

// After
<div style={{ height:"100vh", display:"flex", flexDirection:"column", background:"#f8fafc", ... }}>
  ...
  <div style={{ display:"flex", flex:1, minHeight:0 }}>
```

---

### 6. API Base URL 하드코딩 → Vite Proxy 경유로 변경

**파일:** `frontend/src/api/scoreboardApi.js`

**문제:** `BASE_URL`이 `http://localhost:8000/api`로 하드코딩되어 배포 환경에서 수정이 필요하고, FastAPI의 trailing-slash 307 redirect를 브라우저가 직접 따라가면서 CORS 오류 발생.

**수정:** `/api`로 변경해 Vite dev server proxy를 경유하도록 변경. Proxy가 server-to-server로 요청하므로 CORS 없이 동작하며, 배포 시에도 reverse proxy 설정만 맞추면 됨.

```js
// Before
const BASE_URL = "http://localhost:8000/api";

// After
const BASE_URL = "/api";
```

---

### 7. Vite Proxy redirect 미처리로 인한 CORS 오류

**파일:** `frontend/vite.config.js`

**문제:** FastAPI가 `/api/products` 요청을 `/api/products/`(trailing slash)로 307 redirect할 때, Vite proxy가 redirect를 그대로 브라우저에 전달함. 브라우저가 `http://localhost:8000`으로 직접 요청을 보내면서 CORS 오류 발생.

**수정:** `followRedirects: true` 추가. Proxy가 server 사이드에서 redirect를 처리하고 최종 응답만 브라우저에 반환.

```js
// Before
"/api": {
  target: "http://localhost:8000",
  changeOrigin: true,
},

// After
"/api": {
  target: "http://localhost:8000",
  changeOrigin: true,
  followRedirects: true,
},
```

---

## 참고: 수정하지 않은 항목

| 항목 | 이유 |
|---|---|
| `RadarChart.jsx` — null score를 0으로 표시 | 기능 동작에 영향 없음. 개선 시 null 속성을 chart 데이터에서 제외하거나 별도 표시 처리 필요 |
| `SentencePanel.jsx` — 카테고리 변경 시 탭 유지 | UX 취향 문제. 유지 또는 초기화 모두 합리적 |
| `absa_scorer.py` — 중첩 ThreadPoolExecutor | 파이프라인 스크립트로 UI와 무관. Rate limit 걸릴 경우 `max_workers` 조정으로 대응 |
