"""
LLM 기반 다차원 만족도 스코어보드 - 상품별 (전체 리뷰 분석 + 병렬 처리)
OpenAI gpt-4o-mini로 리뷰에서 속성별 감성을 직접 분류

pip install openai pandas tqdm
환경변수: OPENAI_API_KEY="sk-..."
"""

import json
import os
import time
import threading
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from openai import OpenAI

# ══════════════════════════════════════════════════════════
# 설정
# ══════════════════════════════════════════════════════════
INPUT_FILE       = "shoes_data/shoes_sample.json"
OUTPUT_FILE      = "shoes_data/llm_scores_by_product.json"
SENTENCES_FILE   = "shoes_data/llm_sentences.json"
CHECKPOINT_FILE  = "shoes_data/llm_checkpoint.json"

MODEL                   = "gpt-4o-mini"
MAX_REVIEWS_PER_PRODUCT = None   # None = 전체 리뷰 분석
BATCH_SIZE              = 10
MAX_WORKERS             = 3      # 동시 요청 수 (Rate Limit 문제 시 3으로 줄이세요)
MAX_RETRIES             = 3      # Rate Limit 오류 시 재시도 횟수
RETRY_SLEEP             = 10     # 재시도 대기 시간 (초)
CHECKPOINT_EVERY        = 10     # 몇 개 상품마다 중간 저장

CATEGORIES = ["comfort", "design", "size", "durability", "price"]
CAT_KR = {
    "comfort":    "착용감",
    "design":     "디자인",
    "size":       "사이즈",
    "durability": "내구성",
    "price":      "가격",
}

# ══════════════════════════════════════════════════════════
# 프롬프트
# ══════════════════════════════════════════════════════════
SYSTEM_PROMPT = """You are an expert e-commerce review analyst specializing in footwear products.
Your task is to analyze shoe reviews and classify sentiment for each aspect.

Aspects to analyze:
- comfort: fit feel, cushioning, arch support, breathability, weight, insole, padding
- design: appearance, style, color, aesthetic, look
- size: sizing accuracy, width, length, fit (too small/large/narrow/wide)
- durability: material quality, sole, stitching, how long it lasts, breaking apart
- price: value for money, affordability, worth the cost

Rules:
1. Only include aspects that are EXPLICITLY mentioned in the review
2. Sentiment must be: "positive", "negative" (NO neutral - skip if unclear)
3. Return ONLY valid JSON, no explanation
4. If no relevant aspects found, return empty aspects array
"""

def make_user_prompt(reviews: list) -> str:
    reviews_text = ""
    for i, rev in enumerate(reviews, 1):
        reviews_text += f"\n[Review {i}] Rating: {rev['rating']}/5\n{rev['text']}\n"
    return f"""Analyze these shoe reviews and extract aspect sentiments.
{reviews_text}
Return JSON in this exact format:
{{
  "reviews": [
    {{
      "review_id": 1,
      "aspects": [
        {{"aspect": "comfort", "sentiment": "positive", "evidence": "very comfortable to wear"}},
        {{"aspect": "size", "sentiment": "negative", "evidence": "runs too small"}}
      ]
    }}
  ]
}}"""

# ══════════════════════════════════════════════════════════
# STEP 1: 데이터 로드
# ══════════════════════════════════════════════════════════
print("=" * 55)
print("STEP 1: 데이터 로드")
print("=" * 55)

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

df = pd.DataFrame(data)
print(f"  총 리뷰 수 : {len(df):,}건")
print(f"  총 상품 수 : {df['parent_asin'].nunique():,}개")

# ══════════════════════════════════════════════════════════
# STEP 2: OpenAI 클라이언트 초기화
# ══════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("STEP 2: OpenAI API 초기화")
print("=" * 55)

client = OpenAI()
print(f"  모델           : {MODEL}")
print(f"  동시 요청 수   : {MAX_WORKERS}개")
mode_str = "전체 리뷰" if MAX_REVIEWS_PER_PRODUCT is None else f"상위 {MAX_REVIEWS_PER_PRODUCT}개"
print(f"  분석 범위      : 상품당 {mode_str}")

# ══════════════════════════════════════════════════════════
# STEP 3: 상품별 그룹화
# ══════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("STEP 3: 상품별 그룹화")
print("=" * 55)

grouped         = df.groupby("parent_asin")
product_meta    = {}
product_reviews = {}

for asin, group in grouped:
    product_meta[asin] = {
        "brand":         group["brand"].iloc[0],
        "product_title": group["product_title"].iloc[0],
        "avg_rating":    round(group["rating"].mean(), 2),
        "review_count":  len(group),
    }
    sorted_group = group.sort_values("helpful_vote", ascending=False)
    if MAX_REVIEWS_PER_PRODUCT:
        sorted_group = sorted_group.head(MAX_REVIEWS_PER_PRODUCT)
    product_reviews[asin] = sorted_group[["rating", "text"]].to_dict("records")

total_reviews_to_analyze = sum(len(v) for v in product_reviews.values())
total_batches_est        = sum(
    (len(v) + BATCH_SIZE - 1) // BATCH_SIZE for v in product_reviews.values()
)
est_seconds  = total_batches_est * 3.5 / MAX_WORKERS
est_hours    = int(est_seconds // 3600)
est_minutes  = int((est_seconds % 3600) // 60)
est_cost     = total_batches_est * 0.34 / 500

print(f"  상품 수              : {len(product_meta):,}개")
print(f"  분석 대상 리뷰 수    : {total_reviews_to_analyze:,}건")
print(f"  예상 배치 수         : {total_batches_est:,}회")
print(f"  예상 소요 시간       : 약 {est_hours}시간 {est_minutes}분 (병렬 {MAX_WORKERS}개)")
print(f"  예상 비용            : 약 ${est_cost:.2f}  (약 {est_cost*1400:.0f}원)")

# ══════════════════════════════════════════════════════════
# STEP 4: 체크포인트 로드
# ══════════════════════════════════════════════════════════
if os.path.exists(CHECKPOINT_FILE):
    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
        checkpoint = json.load(f)
    saved           = checkpoint.get("scores", {})
    saved_sentences = checkpoint.get("sentences", [])
    done_asins      = set(saved.keys())
    print(f"\n  체크포인트 발견 → {len(done_asins)}개 완료, 이어서 실행")
else:
    saved           = {}
    saved_sentences = []
    done_asins      = set()

# 스레드 안전을 위한 Lock
lock = threading.Lock()

# ══════════════════════════════════════════════════════════
# STEP 5: 병렬 처리 함수 정의
# ══════════════════════════════════════════════════════════
def call_openai_with_retry(reviews: list) -> list:
    """Rate Limit 오류 시 자동 재시도"""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": make_user_prompt(reviews)},
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=2000,
            )
            raw    = response.choices[0].message.content.strip()
            result = json.loads(raw)
            return result.get("reviews", [])

        except Exception as e:
            err_str = str(e)
            if "rate_limit" in err_str.lower() or "429" in err_str:
                wait = RETRY_SLEEP * (attempt + 1)
                tqdm.write(f"  [Rate Limit] {wait}초 대기 후 재시도 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(wait)
            elif "json" in err_str.lower():
                return []
            else:
                tqdm.write(f"  [WARN] API 오류: {e}")
                return []
    return []

def process_product(asin: str) -> dict:
    """
    상품 1개의 전체 배치를 병렬로 처리
    반환값: {asin: scores, sentences: [...]}
    """
    reviews    = product_reviews[asin]
    meta       = product_meta[asin]
    cat_scores = {cat: [] for cat in CATEGORIES}
    sentences  = []

    # 배치 목록 생성
    batches = [
        reviews[i:i + BATCH_SIZE]
        for i in range(0, len(reviews), BATCH_SIZE)
    ]

    # 배치 단위 병렬 처리
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as batch_executor:
        future_to_batch = {
            batch_executor.submit(call_openai_with_retry, batch): (idx, batch)
            for idx, batch in enumerate(batches)
        }
        for future in as_completed(future_to_batch):
            _, batch = future_to_batch[future]
            results  = future.result()

            for rev_result in results:
                rev_idx = rev_result.get("review_id", 1) - 1
                if rev_idx < 0 or rev_idx >= len(batch):
                    continue
                original_text = batch[rev_idx]["text"]

                for aspect_item in rev_result.get("aspects", []):
                    cat       = aspect_item.get("aspect", "")
                    sentiment = aspect_item.get("sentiment", "")
                    evidence  = aspect_item.get("evidence", "")

                    if cat not in CATEGORIES or sentiment not in ("positive", "negative"):
                        continue

                    score = 1.0 if sentiment == "positive" else -1.0
                    cat_scores[cat].append(score)
                    sentences.append({
                        "asin":          str(asin),
                        "brand":         meta["brand"],
                        "product_title": meta["product_title"],
                        "evidence":      evidence,
                        "full_review":   original_text[:300],
                        "category":      cat,
                        "sentiment":     sentiment,
                        "score":         score,
                    })

    def aggregate(score_list):
        if not score_list:
            return {"score": None, "count": 0, "pos_count": 0, "neg_count": 0}
        pos = sum(1 for s in score_list if s > 0)
        neg = sum(1 for s in score_list if s < 0)
        avg = sum(score_list) / len(score_list)
        return {
            "score":     round((avg + 1) / 2 * 10, 2),
            "count":     len(score_list),
            "pos_count": pos,
            "neg_count": neg,
        }

    return {
        "asin": asin,
        "result": {
            "brand":         meta["brand"],
            "product_title": meta["product_title"],
            "avg_rating":    meta["avg_rating"],
            "review_count":  meta["review_count"],
            "scores":        {cat: aggregate(cat_scores[cat]) for cat in CATEGORIES},
        },
        "sentences": sentences,
    }

# ══════════════════════════════════════════════════════════
# STEP 6: 상품 단위 병렬 처리
# ══════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print(f"STEP 6: LLM 분석 시작 (병렬 {MAX_WORKERS}개)")
print("=" * 55)

asins_to_process = [a for a in product_meta if a not in done_asins]
processed_count  = 0

pbar = tqdm(total=len(asins_to_process), desc="Products")

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    future_to_asin = {
        executor.submit(process_product, asin): asin
        for asin in asins_to_process
    }

    for future in as_completed(future_to_asin):
        try:
            output = future.result()
        except Exception as e:
            tqdm.write(f"  [WARN] 상품 처리 오류: {e}")
            pbar.update(1)
            continue

        asin = output["asin"]

        # Lock으로 스레드 안전하게 저장
        with lock:
            saved[asin]      = output["result"]
            saved_sentences += output["sentences"]
            processed_count += 1

            # 중간 저장
            if processed_count % CHECKPOINT_EVERY == 0:
                with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                    json.dump(
                        {"scores": saved, "sentences": saved_sentences},
                        f, ensure_ascii=False
                    )
                tqdm.write(
                    f"  [체크포인트] {processed_count}개 완료 / "
                    f"{len(saved_sentences):,}건 문장 저장"
                )

        pbar.update(1)

pbar.close()

# ══════════════════════════════════════════════════════════
# STEP 7: 최종 저장
# ══════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("STEP 7: 저장")
print("=" * 55)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(saved, f, ensure_ascii=False, indent=2)

with open(SENTENCES_FILE, "w", encoding="utf-8") as f:
    json.dump(saved_sentences, f, ensure_ascii=False, indent=2)

if os.path.exists(CHECKPOINT_FILE):
    os.remove(CHECKPOINT_FILE)

print(f"  저장 완료 : {OUTPUT_FILE}")
print(f"  문장 결과 : {SENTENCES_FILE} ({len(saved_sentences):,}건)")
print(f"  총 상품 수: {len(saved):,}개")

print("\n  -- 상위 5개 상품 샘플 --")
for asin, info in list(saved.items())[:5]:
    print(f"\n  [{info['brand']}] {info['product_title'][:45]}")
    print(f"    별점: {info['avg_rating']} / 리뷰: {info['review_count']}건")
    for cat, s in info["scores"].items():
        score_str  = f"{s['score']:.1f}" if s["score"] is not None else " N/A"
        bar_filled = int(s['score'] / 10 * 10) if s["score"] else 0
        bar        = "█" * bar_filled + "░" * (10 - bar_filled)
        pos, neg   = s.get("pos_count", 0), s.get("neg_count", 0)
        print(f"    {CAT_KR[cat]:<5}: {score_str}/10 {bar} (+{pos}/-{neg}건)")