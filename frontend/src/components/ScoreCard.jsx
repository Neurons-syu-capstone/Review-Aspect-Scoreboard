const CAT_KR    = { comfort:"착용감", design:"디자인", size:"사이즈", durability:"내구성", price:"가격" };
const CAT_EMOJI = { comfort:"🦶", design:"🎨", size:"📏", durability:"🔩", price:"💰" };

function getIcon(score) {
  if (score === null || score === undefined) return "⚪";
  if (score >= 7) return "🟢";
  if (score >= 4) return "🟡";
  return "🔴";
}

export default function ScoreCard({ category, data, onClick, isSelected }) {
  const { score, pos_count, neg_count } = data;

  return (
    <button
      onClick={() => onClick(category)}
      style={{
        display:       "flex",
        flexDirection: "column",
        gap:           6,
        padding:       "14px 16px",
        borderRadius:  12,
        border:        isSelected ? "2px solid #6366f1" : "2px solid #e5e7eb",
        background:    isSelected ? "#eef2ff" : "#fff",
        cursor:        "pointer",
        textAlign:     "left",
        transition:    "all 0.15s",
        boxShadow:     isSelected ? "0 0 0 3px rgba(99,102,241,0.15)" : "none",
        width:         "100%",
      }}
    >
      {/* 속성명 */}
      <div style={{ display:"flex", alignItems:"center", gap:6 }}>
        <span style={{ fontSize:18 }}>{CAT_EMOJI[category]}</span>
        <span style={{ fontWeight:700, fontSize:14, color:"#111827" }}>
          {CAT_KR[category]}
        </span>
      </div>

      {/* 점수 */}
      <div style={{ display:"flex", alignItems:"center", gap:6 }}>
        <span style={{ fontSize:13 }}>{getIcon(score)}</span>
        <span style={{ fontSize:20, fontWeight:800, color:"#1f2937" }}>
          {score !== null && score !== undefined ? score.toFixed(1) : "N/A"}
        </span>
        {score !== null && score !== undefined && (
          <span style={{ fontSize:12, color:"#9ca3af" }}>/ 10</span>
        )}
      </div>

      {/* 점수 바 */}
      {score !== null && score !== undefined && (
        <div style={{
          height:       6,
          borderRadius: 99,
          background:   "#f3f4f6",
          overflow:     "hidden",
        }}>
          <div style={{
            height:     "100%",
            width:      `${score * 10}%`,
            borderRadius: 99,
            background: score >= 7 ? "#22c55e" : score >= 4 ? "#f59e0b" : "#ef4444",
            transition: "width 0.4s ease",
          }} />
        </div>
      )}

      {/* 긍정/부정 수 */}
      <div style={{ fontSize:12, color:"#6b7280" }}>
        👍 {pos_count ?? 0} &nbsp; 👎 {neg_count ?? 0}
      </div>
    </button>
  );
}
