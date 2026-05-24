import {
  Radar, RadarChart as RechartsRadar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip
} from "recharts";

const CAT_KR = {
  comfort: "착용감", design: "디자인",
  size: "사이즈", durability: "내구성", price: "가격",
};

export default function RadarChart({ scores, brandColor = "#6366f1" }) {
  const data = Object.entries(scores).map(([cat, s]) => ({
    category: CAT_KR[cat] ?? cat,
    score:    s.score ?? 0,
    fullMark: 10,
  }));

  return (
    <ResponsiveContainer width="100%" height={320}>
      <RechartsRadar data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="#e5e7eb" />
        <PolarAngleAxis
          dataKey="category"
          tick={{ fill: "#374151", fontSize: 13, fontWeight: 600 }}
        />
        <PolarRadiusAxis domain={[0, 10]} tick={false} axisLine={false} />
        <Tooltip
          formatter={(value) => [`${value?.toFixed(1)} / 10`, "점수"]}
          contentStyle={{ borderRadius: 8, fontSize: 13 }}
        />
        <Radar
          name="만족도"
          dataKey="score"
          stroke={brandColor}
          fill={brandColor}
          fillOpacity={0.25}
          strokeWidth={2.5}
        />
      </RechartsRadar>
    </ResponsiveContainer>
  );
}
