import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";

export const BenchComp = ({ study = "study", technique = "technique" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = (frame / Math.max(1, fps)).toFixed(2);
  const scale = Math.min(1, 0.85 + 0.15 * Math.min(1, frame / Math.max(1, fps)));

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: "#eef3f7",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Segoe UI, Arial, sans-serif",
        padding: 64,
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          backgroundColor: "#ffffff",
          border: "4px solid #1e293b",
          borderRadius: 20,
          padding: "40px 52px",
          boxShadow: "0 14px 36px rgba(15,23,42,0.14)",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: 44, fontWeight: 800, color: "#0f172a" }}>{technique}</div>
        <div style={{ fontSize: 26, color: "#475569", marginTop: 14 }}>
          {study} · Clay/CAD React Schematic · t={t}s
        </div>
      </div>
    </div>
  );
};
