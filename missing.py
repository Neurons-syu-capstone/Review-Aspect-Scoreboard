"""
누락 상품 확인 및 재분석
- JSON에 아예 없는 상품 탐지
- 해당 상품만 재분석 후 기존 파일에 병합

실행: python reanalyze_missing.py
"""

import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm
from openai import OpenAI

# ══════════════════════════════════════════════════════════
# 설정
# ══════════════════════════════════════════════════════════
SAMPLE_FILE    = "shoes_data/shoes_sample.json"
SCORES_FILE    = "shoes_data/llm_scores_by_product.json"
SENTENCES_FILE = "shoes_data/llm_sentences.json"

MODEL       = "gpt-4o-mini"
BATCH_SIZE  = 10
MAX_WORKERS = 3
MAX_RETRIES = 3
RETRY_SLEEP = 10

CATEGORIES = ["comfort", "design", "size", "durability", "price"]

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

def make_user_prompt(reviews):
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
# STEP 1: 누락 상품 확인
# ══════════════════════════════════════════════════════════
print("=" * 55)
print("STEP 1: 누락 상품 확인")
print("=" * 55)

with open(SCORES_FILE, "r", encoding="utf-8") as f:
    scores = json.load(f)

with open(SAMPLE_FILE, "r", encoding="utf-8") as f:
    sample_data = json.load(f)

# 샘플 전체 asin 목록
df_sample    = pd.DataFrame(sample_data)
sample_asins = set(df_sample["parent_asin"].astype(str).unique())
scores_asins = set(scores.keys())

# JSON에 아예 없는 상품
absent_asins = sample_asins - scores_asins

# JSON에 있지만 점수가 전부 None인 상품
none_asins = [
    asin for asin, info in scores.items()
    if all(s["score"] is None for s in info["scores"].values())
]

missing_asins = list(absent_asins | set(none_asins))

print(f"  샘플 전체 상품 수      : {len(sample_asins)}개")
print(f"  분석 결과 상품 수      : {len(scores_asins)}개")
print(f"  JSON에 없는 상품       : {len(absent_asins)}개")
print(f"  점수 전부 None인 상품  : {len(none_asins)}개")
print(f"  재분석 대상            : {len(missing_asins)}개")

if not missing_asins:
    print("\n  ✅ 누락 상품 없음! 모든 상품 정상 분석됐어요.")
    exit(0)

print(f"\n  누락 상품 목록:")
for asin in missing_asins:
    rows = df_sample[df_sample["parent_asin"].astype(str) == asin]
    if not rows.empty:
        row = rows.iloc[0]
        tag = "JSON없음" if asin in absent_asins else "점수None"
        print(f"    [{tag}] [{row['brand']}] {row['product_title'][:40]}")

# ══════════════════════════════════════════════════════════
# STEP 2: 누락 상품 리뷰 준비
# ══════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("STEP 2: 누락 상품 리뷰 로드")
print("=" * 55)

missing_df = df_sample[df_sample["parent_asin"].astype(str).isin(missing_asins)]

product_meta    = {}
product_reviews = {}

for asin, group in missing_df.groupby(missing_df["parent_asin"].astype(str)):
    product_meta[asin] = {
        "brand":         group["brand"].iloc[0],
        "product_title": group["product_title"].iloc[0],
        "avg_rating":    round(group["rating"].mean(), 2),
        "review_count":  len(group),
    }
    product_reviews[asin] = (
        group.sort_values("helpful_vote", ascending=False)
        [["rating", "text"]].to_dict("records")
    )

print(f"  로드 완료: {len(missing_df):,}건 리뷰 / {len(product_meta)}개 상품")

# ══════════════════════════════════════════════════════════
# STEP 3: 재분석
# ══════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("STEP 3: 재분석 시작")
print("=" * 55)

client = OpenAI()
lock   = threading.Lock()

def call_openai_with_retry(reviews):
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
            if isinstance(result, list):
                return result
            return result.get("reviews", [])
        except Exception as e:
            err_str = str(e)
            if "rate_limit" in err_str.lower() or "429" in err_str:
                wait = RETRY_SLEEP * (attempt + 1)
                tqdm.write(f"  [Rate Limit] {wait}초 대기 후 재시도")
                time.sleep(wait)
            else:
                tqdm.write(f"  [WARN] API 오류: {e}")
                return []
    return []

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

def process_product(asin):
    reviews    = product_reviews[asin]
    meta       = product_meta[asin]
    cat_scores = {cat: [] for cat in CATEGORIES}
    sentences  = []

    batches = [reviews[i:i + BATCH_SIZE] for i in range(0, len(reviews), BATCH_SIZE)]

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as batch_executor:
        future_to_batch = {
            batch_executor.submit(call_openai_with_retry, batch): batch
            for batch in batches
        }
        for future in as_completed(future_to_batch):
            batch   = future_to_batch[future]
            results = future.result()

            for rev_result in results:
                # rev_result가 딕셔너리가 아니면 스킵
                if not isinstance(rev_result, dict):
                    continue
                rev_idx = rev_result.get("review_id", 1) - 1
                if rev_idx < 0 or rev_idx >= len(batch):
                    continue
                original_text = batch[rev_idx]["text"]

                for aspect_item in rev_result.get("aspects", []):
                    # aspect_item도 딕셔너리인지 확인
                    if not isinstance(aspect_item, dict):
                        continue
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

new_sentences = []

for asin in tqdm(missing_asins, desc="Re-analyzing"):
    try:
        output = process_product(asin)
        with lock:
            scores[asin]  = output["result"]
            new_sentences += output["sentences"]
            print(f"  ✅ [{output['result']['brand']}] {output['result']['product_title'][:40]}")
    except Exception as e:
        tqdm.write(f"  [WARN] {asin} 오류: {e}")

# ══════════════════════════════════════════════════════════
# STEP 4: 저장
# ══════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("STEP 4: 저장")
print("=" * 55)

with open(SCORES_FILE, "w", encoding="utf-8") as f:
    json.dump(scores, f, ensure_ascii=False, indent=2)

if os.path.exists(SENTENCES_FILE):
    with open(SENTENCES_FILE, "r", encoding="utf-8") as f:
        existing = json.load(f)
    existing = [s for s in existing if s["asin"] not in missing_asins]
    existing += new_sentences
    with open(SENTENCES_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

print(f"  점수 파일 저장: {SCORES_FILE}  ({len(scores)}개 상품)")
print(f"  문장 파일 저장: {SENTENCES_FILE}  (+{len(new_sentences):,}건)")

still_missing = [
    asin for asin in sample_asins
    if asin not in scores or all(s["score"] is None for s in scores[asin]["scores"].values())
]
if still_missing:
    print(f"\n  ⚠️  여전히 누락: {len(still_missing)}개")
else:
    print(f"\n  ✅ 전체 {len(scores)}개 상품 분석 완료!")

print("\n대시보드 실행:")
print("  streamlit run dashboard.py")