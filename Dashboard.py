"""
다차원 만족도 스코어보드 Streamlit 대시보드
llm_scores_by_product.json + llm_sentences.json 시각화

실행: streamlit run dashboard.py
pip install streamlit plotly pandas
"""

import json
import os
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ══════════════════════════════════════════════════════════
# 설정
# ══════════════════════════════════════════════════════════
SCORE_FILE     = "shoes_data/llm_scores_by_product.json"
SENTENCES_FILE = "shoes_data/llm_sentences.json"

CATEGORIES = ["comfort", "design", "size", "durability", "price"]
CAT_KR = {
    "comfort":    "착용감",
    "design":     "디자인",
    "size":       "사이즈",
    "durability": "내구성",
    "price":      "가격",
}
CAT_EMOJI = {
    "comfort": "🦶", "design": "🎨",
    "size": "📏", "durability": "🔩", "price": "💰",
}
COLOR_MAP = {
    "Skechers": "#0057A8", "Nike": "#FF6B35", "adidas": "#1A1A1A",
    "Crocs": "#F6C700",    "ASICS": "#003DA5", "Merrell": "#4A7C3F",
    "PUMA": "#E31837",     "KEEN": "#F4A100",  "Clarks": "#8B6914",
    "NINE WEST": "#C71585",
}

# ══════════════════════════════════════════════════════════
# 페이지 설정
# ══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="신발 리뷰 다차원 만족도 스코어보드",
    page_icon="👟",
    layout="wide",
)

# ══════════════════════════════════════════════════════════
# 데이터 로드
# ══════════════════════════════════════════════════════════
@st.cache_data
def load_scores(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    rows = []
    for asin, info in raw.items():
        row = {
            "asin":          asin,
            "brand":         info.get("brand", "Unknown"),
            "product_title": info.get("product_title", ""),
            "avg_rating":    info.get("avg_rating"),
            "review_count":  info.get("review_count", 0),
        }
        for cat in CATEGORIES:
            s = info.get("scores", {}).get(cat, {})
            row[f"{cat}_score"]     = s.get("score")
            row[f"{cat}_pos_count"] = s.get("pos_count", s.get("positive", 0))
            row[f"{cat}_neg_count"] = s.get("neg_count", s.get("negative", 0))
            row[f"{cat}_count"]     = s.get("count", row[f"{cat}_pos_count"] + row[f"{cat}_neg_count"])
        rows.append(row)
    return pd.DataFrame(rows)

@st.cache_data
def load_sentences(path):
    if not os.path.exists(path):
        return pd.DataFrame()
    with open(path, "r", encoding="utf-8") as f:
        return pd.DataFrame(json.load(f))

try:
    df = load_scores(SCORE_FILE)
except FileNotFoundError:
    st.error(f"❌ '{SCORE_FILE}' 없음. absa_scorer.py를 먼저 실행하세요.")
    st.stop()

sent_df = load_sentences(SENTENCES_FILE)

# ══════════════════════════════════════════════════════════
# 헤더
# ══════════════════════════════════════════════════════════
st.title("👟 신발 리뷰 다차원 만족도 스코어보드")
st.caption("LLM(gpt-4o-mini) 기반 Aspect-Level 감성 분석 | 점수 범위: 0 ~ 10점")

with st.expander("ℹ️ 점수 계산 방식 및 기준 안내"):
    st.markdown("""
    **1. 점수 계산 방법**
    - 각 속성에 대한 리뷰 문장을 LLM이 긍정(Positive) 또는 부정(Negative)으로 분류합니다.
    - **속성별 만족도 점수 (10점 만점) = (긍정 수 / 전체 수) × 10**
    - 해당 속성에 대한 리뷰가 없으면 `N/A`로 표시됩니다.

    **2. 점수 기준표**
    - 🟢 **7.0 ~ 10.0점** : 긍정 우세 (우수)
    - 🟡 **4.0 ~ 6.9점** : 긍정·부정 혼재 (보통)
    - 🔴 **0.0 ~ 3.9점** : 부정 우세 (미흡)
    - ⚪ **N/A** : 관련 리뷰 없음
    """)

st.divider()

c1, c2, c3, c4 = st.columns(4)
c1.metric("총 상품 수",  f"{len(df):,}개")
c2.metric("브랜드 수",   f"{df['brand'].nunique()}개")
c3.metric("평균 별점",   f"{df['avg_rating'].mean():.2f} ⭐")
c4.metric("총 리뷰 수",  f"{int(df['review_count'].sum()):,}건")
st.divider()

# ══════════════════════════════════════════════════════════
# 섹션 1: 상품 선택 + 레이더 차트 + 속성 점수 카드
# ══════════════════════════════════════════════════════════
st.subheader("📊 상품별 속성 만족도")

brands = sorted(df["brand"].dropna().unique().tolist())
col_search, col_brand = st.columns([3, 1])
with col_brand:
    brand_filter = st.selectbox("브랜드로 좁히기", ["전체"] + brands, key="brand_filter")
with col_search:
    search_query = st.text_input("상품명 검색", placeholder="예: Classic Clog, Air Max ...")

display_df = df.copy()
if brand_filter != "전체":
    display_df = display_df[display_df["brand"] == brand_filter]
if search_query:
    display_df = display_df[
        display_df["product_title"].str.contains(search_query, case=False, na=False)
    ]

if display_df.empty:
    st.warning("조건에 맞는 상품이 없습니다.")
    st.stop()

product_options = {
    f"[{r['brand']}] {r['product_title'][:55]}  (리뷰 {r['review_count']}건 / ⭐{r['avg_rating']})": r["asin"]
    for _, r in display_df.iterrows()
}
selected_label = st.selectbox("상품 선택", list(product_options.keys()))
selected_asin  = product_options[selected_label]
prod           = display_df[display_df["asin"] == selected_asin].iloc[0]

# 문장 데이터에서 긍정/부정 카운트 계산
prod_sent = pd.DataFrame()
if not sent_df.empty:
    prod_sent = sent_df[sent_df["asin"] == str(selected_asin)]

radar_col, score_col = st.columns([3, 2])

with radar_col:
    scores_clean = [
        prod.get(f"{cat}_score") if pd.notna(prod.get(f"{cat}_score")) else 0
        for cat in CATEGORIES
    ]
    labels      = [CAT_KR[cat] for cat in CATEGORIES]
    brand_color = COLOR_MAP.get(prod["brand"], "#6366F1")

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores_clean + [scores_clean[0]],
        theta=labels + [labels[0]],
        fill="toself",
        fillcolor="rgba(99,110,250,0.2)",
        line=dict(color=brand_color, width=2.5),
        name=prod["product_title"][:30],
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 10], tickfont=dict(size=11))),
        showlegend=False,
        margin=dict(t=30, b=30, l=20, r=20),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

with score_col:
    st.markdown(f"**{prod['product_title'][:50]}**")
    st.markdown(f"브랜드: `{prod['brand']}` | ⭐ {prod['avg_rating']} | 리뷰 {prod['review_count']}건")
    st.markdown("---")

    for cat in CATEGORIES:
        score = prod.get(f"{cat}_score")

        if not prod_sent.empty:
            cat_sent  = prod_sent[prod_sent["category"] == cat]
            pos_count = len(cat_sent[cat_sent["sentiment"] == "positive"])
            neg_count = len(cat_sent[cat_sent["sentiment"] == "negative"])
        else:
            pos_count = int(prod.get(f"{cat}_pos_count", 0) or 0)
            neg_count = int(prod.get(f"{cat}_neg_count", 0) or 0)

        emoji = CAT_EMOJI[cat]

        if pd.notna(score):
            filled = int(score / 10 * 20)
            bar    = "█" * filled + "░" * (20 - filled)
            icon   = "🔴" if score < 4 else ("🟡" if score < 7 else "🟢")
            st.markdown(
                f"{icon} {emoji} **{CAT_KR[cat]}** &nbsp; `{score:.1f} / 10` "
                f"&nbsp; 👍{pos_count} 👎{neg_count}"
            )
            st.markdown(f"`{bar}`")
        else:
            st.markdown(f"⚪ {emoji} **{CAT_KR[cat]}** &nbsp; `N/A`")

st.divider()

# ══════════════════════════════════════════════════════════
# 섹션 2: 속성 버튼 클릭 → 관련 문장 표시
# ══════════════════════════════════════════════════════════
st.subheader("🔍 속성별 리뷰 문장 드릴다운")

if sent_df.empty:
    st.info(f"'{SENTENCES_FILE}' 없음.")
elif prod_sent.empty:
    st.warning("해당 상품의 문장 데이터가 없습니다.")
else:
    st.markdown("**속성 선택 (클릭하면 관련 문장이 아래에 나타납니다)**")
    btn_cols = st.columns(5)

    for i, cat in enumerate(CATEGORIES):
        cat_sent  = prod_sent[prod_sent["category"] == cat]
        pos_count = len(cat_sent[cat_sent["sentiment"] == "positive"])
        neg_count = len(cat_sent[cat_sent["sentiment"] == "negative"])
        score     = prod.get(f"{cat}_score")

        if pd.notna(score):
            score_str = f"{score:.1f}점"
            icon      = "🟢" if score >= 7 else ("🟡" if score >= 4 else "🔴")
        else:
            score_str = "N/A"
            icon      = "⚪"

        with btn_cols[i]:
            if st.button(
                f"{CAT_EMOJI[cat]} {CAT_KR[cat]}\n{icon} {score_str}\n👍{pos_count} 👎{neg_count}",
                key=f"btn_{cat}",
                use_container_width=True,
            ):
                st.session_state["selected_cat"] = cat

    # 버튼을 한 번도 누르지 않았으면 안내 문구만 표시
    if "selected_cat" not in st.session_state:
        st.markdown("")
        st.info("위 속성 버튼을 클릭하면 관련 리뷰 문장이 표시됩니다.")
    else:
        current_cat = st.session_state["selected_cat"]
        cat_sent_df = prod_sent[prod_sent["category"] == current_cat]

        st.markdown(
            f"---\n#### {CAT_EMOJI[current_cat]} {CAT_KR[current_cat]} "
            f"관련 문장 ({len(cat_sent_df)}건)"
        )

        pos_df = cat_sent_df[cat_sent_df["sentiment"] == "positive"]
        neg_df = cat_sent_df[cat_sent_df["sentiment"] == "negative"]

        pos_tab, neg_tab = st.tabs([
            f"👍 긍정 ({len(pos_df)}건)",
            f"👎 부정 ({len(neg_df)}건)",
        ])

        with pos_tab:
            if pos_df.empty:
                st.info("긍정 문장이 없습니다.")
            else:
                ev_col = "evidence" if "evidence" in pos_df.columns else "sentence_en"
                for _, row in pos_df.iterrows():
                    evidence = row.get(ev_col, "") or ""
                    st.markdown(
                        f"<div style='background:#f0fdf4;border-left:4px solid #22c55e;"
                        f"padding:10px 14px;border-radius:6px;margin-bottom:8px'>"
                        f"✅ {evidence}</div>",
                        unsafe_allow_html=True,
                    )

        with neg_tab:
            if neg_df.empty:
                st.info("부정 문장이 없습니다.")
            else:
                ev_col = "evidence" if "evidence" in neg_df.columns else "sentence_en"
                for _, row in neg_df.iterrows():
                    evidence = row.get(ev_col, "") or ""
                    st.markdown(
                        f"<div style='background:#fef2f2;border-left:4px solid #ef4444;"
                        f"padding:10px 14px;border-radius:6px;margin-bottom:8px'>"
                        f"❌ {evidence}</div>",
                        unsafe_allow_html=True,
                    )

st.divider()

# ══════════════════════════════════════════════════════════
# 섹션 3: 전체 데이터 테이블
# ══════════════════════════════════════════════════════════
with st.expander("📋 전체 데이터 보기"):
    show_cols = ["brand", "product_title", "avg_rating", "review_count"] + \
                [f"{cat}_score" for cat in CATEGORIES]
    show_df = df[show_cols].copy()
    show_df.columns = (
        ["브랜드", "상품명", "평균 별점", "리뷰 수"] +
        [f"{CAT_KR[cat]} 점수" for cat in CATEGORIES]
    )
    show_df["상품명"] = show_df["상품명"].str[:50]
    st.dataframe(show_df.reset_index(drop=True), use_container_width=True)