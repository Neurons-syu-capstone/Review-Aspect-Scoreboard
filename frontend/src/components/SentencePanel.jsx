import { useState, useEffect } from "react";
import { fetchSentences } from "../api/scoreboardApi";

const CAT_KR    = { comfort:"착용감", design:"디자인", size:"사이즈", durability:"내구성", price:"가격" };
const CAT_EMOJI = { comfort:"🦶", design:"🎨", size:"📏", durability:"🔩", price:"💰" };

export default function SentencePanel({ asin, category }) {
  const [sentences, setSentences] = useState([]);
  const [tab, setTab]             = useState("positive");
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);

  useEffect(() => {
    if (!asin || !category) return;
    setLoading(true);
    setError(null);

    fetchSentences(asin, { category })
      .then(setSentences)
      .catch(() => setError("문장 데이터를 불러오지 못했습니다."))
      .finally(() => setLoading(false));
  }, [asin, category]);

  const positive = sentences.filter(s => s.sentiment === "positive");
  const negative = sentences.filter(s => s.sentiment === "negative");
  const current  = tab === "positive" ? positive : negative;

  if (!category) return (
    <div style={panelStyle}>
      <p style={{ color:"#9ca3af", textAlign:"center", padding:"40px 0" }}>
        위 속성 카드를 클릭하면 관련 리뷰 문장이 표시됩니다.
      </p>
    </div>
  );

  return (
    <div style={panelStyle}>
      {/* 헤더 */}
      <div style={{ marginBottom:16 }}>
        <h3 style={{ margin:0, fontSize:16, fontWeight:700, color:"#111827" }}>
          {CAT_EMOJI[category]} {CAT_KR[category]} 관련 문장
          <span style={{ marginLeft:8, fontSize:13, color:"#6b7280", fontWeight:400 }}>
            ({sentences.length}건)
          </span>
        </h3>
      </div>

      {/* 탭 */}
      <div style={{ display:"flex", gap:8, marginBottom:16 }}>
        {[
          { key:"positive", label:`👍 긍정`, count: positive.length },
          { key:"negative", label:`👎 부정`, count: negative.length },
        ].map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            style={{
              padding:      "6px 16px",
              borderRadius: 99,
              border:       "none",
              cursor:       "pointer",
              fontSize:     13,
              fontWeight:   600,
              background:   tab === key
                ? (key === "positive" ? "#dcfce7" : "#fee2e2")
                : "#f3f4f6",
              color: tab === key
                ? (key === "positive" ? "#15803d" : "#b91c1c")
                : "#6b7280",
              transition: "all 0.15s",
            }}
          >
            {label} ({count})
          </button>
        ))}
      </div>

      {/* 문장 목록 */}
      {loading && (
        <p style={{ color:"#9ca3af", textAlign:"center" }}>불러오는 중...</p>
      )}
      {error && (
        <p style={{ color:"#ef4444", textAlign:"center" }}>{error}</p>
      )}
      {!loading && !error && (
        <div style={{ display:"flex", flexDirection:"column", gap:8, maxHeight:400, overflowY:"auto" }}>
          {current.length === 0 ? (
            <p style={{ color:"#9ca3af", textAlign:"center", padding:"20px 0" }}>
              {tab === "positive" ? "긍정" : "부정"} 문장이 없습니다.
            </p>
          ) : (
            current.map((s, i) => (
              <div
                key={i}
                style={{
                  padding:      "10px 14px",
                  borderRadius: 8,
                  fontSize:     14,
                  lineHeight:   1.6,
                  borderLeft:   `4px solid ${tab === "positive" ? "#22c55e" : "#ef4444"}`,
                  background:   tab === "positive" ? "#f0fdf4" : "#fef2f2",
                  color:        "#1f2937",
                }}
              >
                {tab === "positive" ? "✅" : "❌"} {s.evidence}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

const panelStyle = {
  padding:      24,
  borderRadius: 16,
  background:   "#f9fafb",
  border:       "1px solid #e5e7eb",
  minHeight:    200,
};
