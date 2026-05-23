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
import plotly.express as px
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
            row[f"{cat}_score"] = s.get("score")
            
            # JSON 키 이름이 다를 경우를 대비해 여러 키를 확인합니다.
            row[f"{cat}_pos_count"] = s.get("pos_count", s.get("positive", s.get("positive_count", 0)))
            row[f"{cat}_neg_count"] = s.get("neg_count", s.get("negative", s.get("negative_count", 0)))
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
    st.error(f"❌ '{SCORE_FILE}' 없음. llm_scoring.py를 먼저 실행하세요.")
    st.stop()

sent_df = load_sentences(SENTENCES_FILE)

# ══════════════════════════════════════════════════════════
# 헤더 및 안내
# ══════════════════════════════════════════════════════════
st.title("👟 신발 리뷰 다차원 만족도 스코어보드")
st.caption("LLM(gpt-4o-mini) 기반 Aspect-Level 감성 분석 | 점수 범위: 0 ~ 10점")

with st.expander("ℹ️ 점수 계산 방식 및 기준 안내"):
    st.markdown("""
    **1. 점수 계산 방법**
    * 각 속성(착용감, 디자인 등)에 대한 리뷰 문장을 LLM이 긍정(Positive) 또는 부정(Negative)으로 분류합니다.
    * **속성별 만족도 점수 (10점 만점) = (긍정 리뷰 수 / 전체 리뷰 수) × 10**
    * 해당 속성에 대한 리뷰가 없는 경우 점수는 `N/A`로 표시되며 집계에서 제외됩니다.

    **2. 점수 기준표**
    * 🟢 **7.0점 ~ 10.0점**: 긍정적 반응 우세 (우수)
    * 🟡 **4.0점 ~ 6.9점**: 긍정 및 부정 반응 혼재 (보통)
    * 🔴 **0.0점 ~ 3.9점**: 부정적 반응 우세 (미흡)
    * ⚪ **N/A**: 관련 리뷰 없음
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

radar_col, score_col = st.columns([3, 2])

with radar_col:
    scores_clean = [prod.get(f"{cat}_score") if pd.notna(prod.get(f"{cat}_score")) else 0 for cat in CATEGORIES]
    labels       = [CAT_KR[cat] for cat in CATEGORIES]
    brand_color  = COLOR_MAP.get(prod["brand"], "#6366F1")

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
    
    # 확실한 긍정/부정 카운트를 위해 문장 데이터(sent_df)에서 직접 계산합니다.
    prod_sent = pd.DataFrame()
    if not sent_df.empty:
        prod_sent = sent_df[sent_df["asin"] == str(selected_asin)]
        
    for cat in CATEGORIES:
        score = prod.get(f"{cat}_score")
        
        # 문장 데이터가 존재하면 직접 세고, 없으면 JSON 데이터를 가져옵니다.
        if not prod_sent.empty:
            cat_sent  = prod_sent[prod_sent["category"] == cat]
            pos_count = len(cat_sent[cat_sent["sentiment"] == "positive"])
            neg_count = len(cat_sent[cat_sent["sentiment"] == "negative"])
        else:
            pos_count = int(prod.get(f"{cat}_pos_count", 0) if pd.notna(prod.get(f"{cat}_pos_count")) else 0)
            neg_count = int(prod.get(f"{cat}_neg_count", 0) if pd.notna(prod.get(f"{cat}_neg_count")) else 0)
            
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
# 섹션 2: 속성 버튼 → 긍정/부정 문장 드릴다운
# ══════════════════════════════════════════════════════════
st.subheader("🔍 속성별 리뷰 문장 드릴다운")

if sent_df.empty:
    st.info(f"'{SENTENCES_FILE}' 없음.")
else:
    drill_asin = selected_asin
    prod_sent  = sent_df[sent_df["asin"] == str(drill_asin)]

    if prod_sent.empty:
        st.warning("해당 상품의 문장 데이터가 없습니다.")
    else:
        st.markdown("**속성 선택 (클릭하세요)**")
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

        if "selected_cat" not in st.session_state:
            st.session_state["selected_cat"] = CATEGORIES[0]

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
                    evidence = row.get(ev_col, "") or row.get("sentence_en", "")
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
                    evidence = row.get(ev_col, "") or row.get("sentence_en", "")
                    st.markdown(
                        f"<div style='background:#fef2f2;border-left:4px solid #ef4444;"
                        f"padding:10px 14px;border-radius:6px;margin-bottom:8px'>"
                        f"❌ {evidence}</div>",
                        unsafe_allow_html=True,
                    )

st.divider()

# ══════════════════════════════════════════════════════════
# 섹션 3: 브랜드별 속성 평균 레이더
# ══════════════════════════════════════════════════════════
st.subheader("🏷️ 브랜드별 속성 평균 비교")

brand_avg = (
    df.groupby("brand")[[f"{cat}_score" for cat in CATEGORIES]]
    .mean().round(2).reset_index()
)

fig2 = go.Figure()
for _, row in brand_avg.iterrows():
    brand  = row["brand"]
    vals   = [row.get(f"{cat}_score") if pd.notna(row.get(f"{cat}_score")) else 0 for cat in CATEGORIES]
    labels = [CAT_KR[cat] for cat in CATEGORIES]
    color  = COLOR_MAP.get(brand, "#888888")
    
    fig2.add_trace(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name=brand,
        line=dict(color=color, width=2),
        opacity=0.65,
    ))

fig2.update_layout(
    polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
    height=500,
    margin=dict(t=40, b=60),
    legend=dict(orientation="h", yanchor="bottom", y=-0.3),
)
st.plotly_chart(fig2, use_container_width=True)
st.divider()

# ══════════════════════════════════════════════════════════
# 섹션 4: 브랜드 × 속성 히트맵
# ══════════════════════════════════════════════════════════
st.subheader("🗺️ 브랜드 × 속성 히트맵")

heatmap_data = brand_avg.set_index("brand")[[f"{cat}_score" for cat in CATEGORIES]]
heatmap_data.columns = [CAT_KR[cat] for cat in CATEGORIES]

fig3 = px.imshow(
    heatmap_data,
    text_auto=".1f",
    color_continuous_scale="RdYlGn",
    zmin=0, zmax=10,
    aspect="auto",
    labels=dict(color="점수"),
)
fig3.update_layout(height=400, margin=dict(t=20, b=20))
st.plotly_chart(fig3, use_container_width=True)
st.divider()

# ══════════════════════════════════════════════════════════
# 섹션 5: 속성별 TOP 5 / BOTTOM 5
# ══════════════════════════════════════════════════════════
st.subheader("🏆 속성별 TOP 5 / BOTTOM 5")

tabs = st.tabs([f"{CAT_EMOJI[cat]} {CAT_KR[cat]}" for cat in CATEGORIES])

for tab, cat in zip(tabs, CATEGORIES):
    with tab:
        top_col, bot_col = st.columns(2)
        with top_col:
            st.markdown("**👍 TOP 5**")
            top5 = (
                df[df[f"{cat}_score"].notna()]
                .sort_values(f"{cat}_score", ascending=False)
                .head(5)[["brand", "product_title", f"{cat}_score",
                           f"{cat}_pos_count", f"{cat}_neg_count"]]
                .reset_index(drop=True)
            )
            top5.index += 1
            top5.columns = ["브랜드", "상품명", "점수", "👍긍정", "👎부정"]
            top5["상품명"] = top5["상품명"].str[:35]
            st.dataframe(top5, use_container_width=True)

        with bot_col:
            st.markdown("**👎 BOTTOM 5**")
            bot5 = (
                df[df[f"{cat}_score"].notna()]
                .sort_values(f"{cat}_score", ascending=True)
                .head(5)[["brand", "product_title", f"{cat}_score",
                           f"{cat}_pos_count", f"{cat}_neg_count"]]
                .reset_index(drop=True)
            )
            bot5.index += 1
            bot5.columns = ["브랜드", "상품명", "점수", "👍긍정", "👎부정"]
            bot5["상품명"] = bot5["상품명"].str[:35]
            st.dataframe(bot5, use_container_width=True)

st.divider()

# ══════════════════════════════════════════════════════════
# 섹션 6: 별점 vs 속성 점수 산점도
# ══════════════════════════════════════════════════════════
st.subheader("🔵 별점 vs 속성 점수 산점도")

cat_select = st.selectbox(
    "속성 선택",
    CATEGORIES,
    format_func=lambda x: f"{CAT_EMOJI[x]} {CAT_KR[x]}",
    key="scatter_cat",
)

scatter_df = df[
    df[f"{cat_select}_score"].notna() &
    df["avg_rating"].notna()
].copy()

fig4 = px.scatter(
    scatter_df,
    x="avg_rating",
    y=f"{cat_select}_score",
    color="brand",
    color_discrete_map=COLOR_MAP,
    hover_data={"product_title": True, "review_count": True},
    labels={
        "avg_rating":           "평균 별점",
        f"{cat_select}_score":  f"{CAT_KR[cat_select]} 점수",
        "brand":                "브랜드",
    },
    opacity=0.75,
)
fig4.update_layout(height=420, margin=dict(t=20, b=20))
st.plotly_chart(fig4, use_container_width=True)
st.divider()

# ══════════════════════════════════════════════════════════
# 섹션 7: 전체 데이터 테이블
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