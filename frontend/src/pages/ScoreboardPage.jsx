import { useState, useEffect } from "react";
import { fetchProducts, fetchBrands } from "../api/scoreboardApi";
import RadarChart    from "../components/RadarChart";
import ScoreCard     from "../components/ScoreCard";
import SentencePanel from "../components/SentencePanel";

function InfoBanner() {
  const [open, setOpen] = useState(false);
  return (
    <div style={{
      background:   "#fff",
      borderBottom: "1px solid #e5e7eb",
      padding:      "0 32px",
    }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display:    "flex",
          alignItems: "center",
          gap:        8,
          padding:    "10px 0",
          border:     "none",
          background: "none",
          cursor:     "pointer",
          fontSize:   13,
          color:      "#6b7280",
          fontWeight: 500,
          width:      "100%",
          textAlign:  "left",
        }}
      >
        <span style={{
          display:      "inline-flex",
          alignItems:   "center",
          justifyContent: "center",
          width:        18,
          height:       18,
          borderRadius: 99,
          background:   "#6366f1",
          color:        "#fff",
          fontSize:     11,
          fontWeight:   700,
          flexShrink:   0,
        }}>i</span>
        점수 계산 방식 및 기준 안내
        <span style={{ marginLeft:"auto", fontSize:12 }}>{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div style={{
          padding:    "0 0 16px 26px",
          fontSize:   13,
          color:      "#374151",
          lineHeight: 1.8,
        }}>
          <p style={{ fontWeight:700, marginBottom:6 }}>1. 점수 계산 방법</p>
          <ul style={{ paddingLeft:16, marginBottom:12 }}>
            <li>각 속성에 대한 리뷰 문장을 LLM이 긍정(Positive) 또는 부정(Negative)으로 분류합니다.</li>
            <li><strong>속성별 만족도 점수 (10점 만점) = (긍정 수 / 전체 수) × 10</strong></li>
            <li>해당 속성에 대한 리뷰가 없으면 <code style={{ background:"#f3f4f6", padding:"1px 6px", borderRadius:4 }}>N/A</code> 로 표시됩니다.</li>
          </ul>
          <p style={{ fontWeight:700, marginBottom:6 }}>2. 점수 기준표</p>
          <ul style={{ paddingLeft:16 }}>
            <li>🟢 <strong>7.0 ~ 10.0점</strong> : 긍정 우세 (우수)</li>
            <li>🟡 <strong>4.0 ~ 6.9점</strong> : 긍정·부정 혼재 (보통)</li>
            <li>🔴 <strong>0.0 ~ 3.9점</strong> : 부정 우세 (미흡)</li>
            <li>⚪ <strong>N/A</strong> : 관련 리뷰 없음</li>
          </ul>
        </div>
      )}
    </div>
  );
}

const CATEGORIES = ["comfort", "design", "size", "durability", "price"];

const BRAND_COLORS = {
  Skechers: "#0057A8", Nike: "#FF6B35", adidas: "#1A1A1A",
  Crocs: "#F6C700",    ASICS: "#003DA5", Merrell: "#4A7C3F",
  PUMA: "#E31837",     KEEN: "#F4A100", Clarks: "#8B6914",
  "NINE WEST": "#C71585",
};

export default function ScoreboardPage() {
  const [brands,          setBrands]         = useState([]);
  const [products,        setProducts]       = useState([]);
  const [selectedBrand,   setSelectedBrand]  = useState("");
  const [searchQuery,     setSearchQuery]    = useState("");
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [selectedCat,     setSelectedCat]    = useState(null);
  const [loading,         setLoading]        = useState(false);

  // 브랜드 목록 로드
  useEffect(() => {
    fetchBrands().then(setBrands).catch(console.error);
  }, []);

  // 상품 목록 로드
  useEffect(() => {
    setSelectedProduct(null);
    setSelectedCat(null);
    setLoading(true);
    fetchProducts({
      brand:  selectedBrand || null,
      search: searchQuery   || null,
    })
      .then(setProducts)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [selectedBrand, searchQuery]);

  // 상품 선택 시 카테고리 초기화
  const handleSelectProduct = (product) => {
    setSelectedProduct(product);
    setSelectedCat(null);
  };

  return (
    <div style={{ height:"100vh", display:"flex", flexDirection:"column", background:"#f8fafc", fontFamily:"'Pretendard', sans-serif" }}>

      {/* 헤더 */}
      <header style={{
        background:   "#fff",
        borderBottom: "1px solid #e5e7eb",
        padding:      "0 40px",
        height:       64,
        display:      "flex",
        alignItems:   "center",
        gap:          12,
        position:     "sticky",
        top:          0,
        zIndex:       100,
        boxShadow:    "0 1px 3px rgba(0,0,0,0.06)",
      }}>
        <span style={{ fontSize:24 }}>👟</span>
        <span style={{ fontSize:18, fontWeight:800, color:"#111827" }}>
          신발 리뷰 다차원 만족도 스코어보드
        </span>
        <span style={{
          marginLeft:   "auto",
          fontSize:     12,
          color:        "#9ca3af",
          background:   "#f3f4f6",
          padding:      "4px 10px",
          borderRadius: 99,
        }}>
          LLM(gpt-4o-mini) · Aspect-Level 감성 분석
        </span>
      </header>

      {/* 점수 계산 방식 안내 */}
      <InfoBanner />

      <div style={{ display:"flex", flex:1, minHeight:0 }}>

        {/* 왼쪽 사이드바: 상품 목록 */}
        <aside style={{
          width:        320,
          minWidth:     320,
          background:   "#fff",
          borderRight:  "1px solid #e5e7eb",
          display:      "flex",
          flexDirection:"column",
          overflowY:    "hidden",
        }}>
          {/* 필터 */}
          <div style={{ padding:"16px 16px 0", borderBottom:"1px solid #f3f4f6" }}>
            <input
              type="text"
              placeholder="상품명 검색..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              style={inputStyle}
            />
            <select
              value={selectedBrand}
              onChange={e => setSelectedBrand(e.target.value)}
              style={{ ...inputStyle, marginTop:8 }}
            >
              <option value="">전체 브랜드</option>
              {brands.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
            <p style={{ fontSize:12, color:"#9ca3af", margin:"8px 0 12px" }}>
              {loading ? "불러오는 중..." : `${products.length}개 상품`}
            </p>
          </div>

          {/* 상품 리스트 */}
          <div style={{ overflowY:"auto", flex:1 }}>
            {products.map(p => (
              <div
                key={p.asin}
                onClick={() => handleSelectProduct(p)}
                style={{
                  padding:    "12px 16px",
                  cursor:     "pointer",
                  borderBottom: "1px solid #f9fafb",
                  background: selectedProduct?.asin === p.asin ? "#eef2ff" : "#fff",
                  borderLeft: selectedProduct?.asin === p.asin
                    ? "3px solid #6366f1" : "3px solid transparent",
                  transition: "all 0.1s",
                }}
              >
                <div style={{ fontSize:12, color:"#9ca3af", marginBottom:2 }}>
                  <span style={{
                    background:   BRAND_COLORS[p.brand] || "#e5e7eb",
                    color:        "#fff",
                    padding:      "1px 8px",
                    borderRadius: 99,
                    fontSize:     11,
                    fontWeight:   600,
                  }}>
                    {p.brand}
                  </span>
                </div>
                <div style={{ fontSize:13, fontWeight:600, color:"#1f2937", marginTop:4, lineHeight:1.4 }}>
                  {p.product_title.slice(0, 50)}{p.product_title.length > 50 ? "..." : ""}
                </div>
                <div style={{ fontSize:12, color:"#6b7280", marginTop:4 }}>
                  ⭐ {p.avg_rating?.toFixed(2)} · 리뷰 {p.review_count}건
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* 메인 영역 */}
        <main style={{ flex:1, overflowY:"auto", padding:"28px 32px" }}>
          {!selectedProduct ? (
            <div style={{ display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", height:"100%", color:"#9ca3af" }}>
              <span style={{ fontSize:48 }}>👈</span>
              <p style={{ fontSize:16, marginTop:12 }}>왼쪽에서 상품을 선택하세요</p>
            </div>
          ) : (
            <>
              {/* 상품 헤더 */}
              <div style={{ marginBottom:24 }}>
                <div style={{ fontSize:12, color:"#9ca3af", marginBottom:4 }}>
                  <span style={{
                    background:   BRAND_COLORS[selectedProduct.brand] || "#e5e7eb",
                    color:        "#fff",
                    padding:      "2px 10px",
                    borderRadius: 99,
                    fontSize:     12,
                    fontWeight:   600,
                  }}>
                    {selectedProduct.brand}
                  </span>
                </div>
                <h2 style={{ margin:"6px 0 4px", fontSize:20, fontWeight:800, color:"#111827" }}>
                  {selectedProduct.product_title}
                </h2>
                <p style={{ margin:0, fontSize:14, color:"#6b7280" }}>
                  ⭐ {selectedProduct.avg_rating?.toFixed(2)} &nbsp;·&nbsp; 리뷰 {selectedProduct.review_count}건
                </p>
              </div>

              {/* 레이더 차트 + 점수 카드 */}
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:24, marginBottom:24 }}>
                {/* 레이더 차트 */}
                <div style={cardStyle}>
                  <h3 style={cardTitleStyle}>속성별 만족도</h3>
                  <RadarChart
                    scores={selectedProduct.scores}
                    brandColor={BRAND_COLORS[selectedProduct.brand] || "#6366f1"}
                  />
                </div>

                {/* 점수 카드 5개 */}
                <div style={cardStyle}>
                  <h3 style={cardTitleStyle}>속성 점수 (클릭하면 관련 문장 표시)</h3>
                  <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10 }}>
                    {CATEGORIES.map(cat => (
                      <ScoreCard
                        key={cat}
                        category={cat}
                        data={selectedProduct.scores[cat] || { score: null, pos_count: 0, neg_count: 0 }}
                        onClick={setSelectedCat}
                        isSelected={selectedCat === cat}
                      />
                    ))}
                  </div>
                </div>
              </div>

              {/* 문장 드릴다운 */}
              <SentencePanel
                asin={selectedProduct.asin}
                category={selectedCat}
              />
            </>
          )}
        </main>
      </div>
    </div>
  );
}

const inputStyle = {
  width:        "100%",
  padding:      "8px 12px",
  borderRadius: 8,
  border:       "1px solid #e5e7eb",
  fontSize:     13,
  outline:      "none",
  boxSizing:    "border-box",
  background:   "#f9fafb",
};

const cardStyle = {
  background:   "#fff",
  borderRadius: 16,
  padding:      "20px 24px",
  border:       "1px solid #e5e7eb",
  boxShadow:    "0 1px 3px rgba(0,0,0,0.04)",
};

const cardTitleStyle = {
  margin:     "0 0 16px",
  fontSize:   14,
  fontWeight: 700,
  color:      "#374151",
};
